import functools
import time
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType
from pkg_confirm import confirm
import os


class Configuration:

    def __init__(self, session, *args, **kwargs):
        self.session = session
        self.session.status_maker = self.status_bar_xue
        self.uinfo = self.session.getVariable('char_profile')
        self.uinfo['max_food'] = 350
        self.uinfo['max_water'] = 350
        if "fullme_time" not in self.uinfo:
            self.uinfo['fullme_time'] = 0  # 初始化为0
        # 倒计时相关状态
        self.fullme_start_time = 0  # 倒计时开始的时间戳
        self.fullme_total_duration = 0  # 倒计时总时长

    def _get_clock_emoji(self, remaining_time):
        """根据剩余时间获取时钟表情符号，每5秒切换一次"""
        clock_emojis = ["🕛", "🕐", "🕑", "🕒", "🕓", "🕔", "🕕", "🕖", "🕗", "🕘", "🕙", "🕚"]
        phase = int(remaining_time / 5) % len(clock_emojis)
        return clock_emojis[phase]

    def _get_time_color(self, remaining_time):
        """根据剩余时间获取颜色"""
        if remaining_time > 100:
            return "fg:green"
        elif remaining_time > 50:
            return "fg:yellow"
        else:
            return "fg:red"

    def _calculate_remaining_time(self, fullme_duration):
        """计算剩余时间"""
        if fullme_duration <= 0:
            return 0

        current_time = time.time()

        # 检测倒计时状态变化
        if self.fullme_start_time == 0 or fullme_duration != self.fullme_total_duration:
            # 新的倒计时开始
            self.fullme_start_time = current_time
            self.fullme_total_duration = fullme_duration

        # 计算剩余时间
        elapsed_time = current_time - self.fullme_start_time
        return max(0, fullme_duration - elapsed_time)

    def _add_status_item(self, formatted_list, label, value, max_value, color_func):
        """添加状态项到列表"""
        progress_styles = self.progress_bar_styles(value, max_value)
        color = color_func(value, max_value)

        # 为每个状态项添加对应的表情符号
        emoji_mapping = {
            "气血": "❤️",
            "内力": "💪",
            "精神": "🧠",
            "精力": "⚡",
            "真气": "🌀",
            "食物": "🍎",
            "饮水": "💧"
        }
        emoji = emoji_mapping.get(label, "")

        formatted_list.append(("fg:green", f" {emoji}{label}："))
        formatted_list.extend(progress_styles["gradient"])
        formatted_list.append(("", "\n"))
        formatted_list.append(("", "         "))
        formatted_list.append((color, f"{value}"))
        formatted_list.append(("fg:green", " / "))
        formatted_list.append(("fg:white", f"{max_value}"))
        formatted_list.append(("", "\n"))

    def opFullmeFn(self, mouse_event: MouseEvent):
        if mouse_event.event_type == MouseEventType.MOUSE_UP:
            self.session.info('fullme')

    async def startJobFn(self, mouse_event: MouseEvent):
        if mouse_event.event_type == MouseEventType.MOUSE_UP:
            self.session.info('【开始干活】')

    def status_bar_xue(self):
        """包含多种进度条样式的状态窗口"""
        formatted_list = list()

        # 头部信息
        formatted_list.extend([
            ("fg:#DC143C", " BUFF：临兵斗者皆阵列在前"),
            ("", "\n"),
            ("", "-------------------------"),
            ("", "\n")
        ])

        # 状态项配置（已包含真气）
        status_items = [
            ("气血", self.uinfo['qi'], self.uinfo['max_qi']),
            ("内力", self.uinfo['neili'], self.uinfo['max_neili']),
            ("精神", self.uinfo['jing'], self.uinfo['max_jing']),
            ("精力", self.uinfo['jingli'], self.uinfo['max_jingli']),
            ("真气", self.uinfo['vigour/qi'], self.uinfo['vigour/max_qi']),
            ("食物", self.uinfo['food'], 350),
            ("饮水", self.uinfo['water'], 350)
        ]

        # 添加状态项
        for label, value, max_value in status_items:
            self._add_status_item(formatted_list, label, value, max_value, self.get_value_color)

        # 潜能和经验（添加表情符号）
        formatted_list.extend([
            ("fg:green", " 💎潜能："),
            ("fg:#00BFFF", f"{self.uinfo['potential']}"),
            ("", "\n"),
            ("fg:green", " ⭐经验："),
            (self.get_value_color(self.uinfo['water'], 350), f"{self.uinfo['combat_exp']}"),
            ("", "\n"),
            ("", "-------------------------"),
            ("", "\n")
        ])

        # 倒计时处理
        fullme_duration = self.uinfo.get('fullme_time', 0)
        remaining_time = self._calculate_remaining_time(fullme_duration)
        
        if remaining_time > 0:
            clock_emoji = self._get_clock_emoji(remaining_time)
            time_color = self._get_time_color(remaining_time)
            
            formatted_list.append(("fg:cyan", "       "))
            formatted_list.append(("fg:cyan", f"{clock_emoji} "))
            formatted_list.append((time_color, f"{int(remaining_time)}"))
            formatted_list.append(("fg:cyan", " 秒"))
            formatted_list.append(("", "\n"))
            formatted_list.append(("", "-------------------------"))
            formatted_list.append(("", "\n"))
        else:
            formatted_list.append(("fg:cyan", "       "))
            formatted_list.append(("fg:cyan", "⏰ FULLME按钮", functools.partial(self.opFullmeFn)))
            formatted_list.append(("", "\n"))
            formatted_list.append(("", "-------------------------"))
            formatted_list.append(("", "\n"))
            self.session.vars['char_profile']['fullme_time'] = 0

        # 底部按钮
        formatted_list.append(("", "\n"))
        formatted_list.append(("", "-------------------------"))
        formatted_list.append(("", "\n"))
        formatted_list.append(("", "    "))
        formatted_list.append(("bg:#76EEC6 fg:red", "|    点我    |", functools.partial(self.startJobFn)))
        formatted_list.append(("", "\n"))
        formatted_list.append(("", "-------------------------"))
        formatted_list.append(("", "\n"))
        
        return formatted_list

    def progress_bar_styles(self, current, maximum=10, barlength=9):
        """创建多种进度条样式
        参数:
            current: 当前值
            maximum: 最大值
            barlength: 进度条长度
        """
        percentage = min(current / maximum, 1.0) if maximum > 0 else 0
        filled_length = int(round(barlength * percentage))
        remaining_length = barlength - filled_length

        progress_bars = {}

        # 样式2：渐变色彩进度条
        if filled_length > 0:
            # 根据进度改变颜色：红->橙->黄->绿
            if percentage < 0.25:
                color = "fg:#800000"
            elif percentage < 0.5:
                color = "fg:#ff6600"
            elif percentage < 0.6:
                color = "fg:red"
            elif percentage < 0.7:
                color = "fg:yellow"
            elif percentage < 0.8:
                color = "fg:#FFD700"
            elif percentage < 0.95:
                color = "fg:#7FFF00"

            else:
                color = "fg:green"
            progress_bars["gradient"] = [
                (color, "■" * filled_length),  # 使用■代替█
                ("fg:#666666", "□" * remaining_length),  # 使用□代替░
                ("fg:cyan", f" {int(percentage * 100)}%")
            ]
        else:
            progress_bars["gradient"] = [
                ("fg:#666666", "□" * barlength),
                ("fg:cyan", f" {int(percentage * 100)}%")
            ]

        return progress_bars

    async def startJobFn(self, mouse_event: MouseEvent):
        if mouse_event.event_type == MouseEventType.MOUSE_UP:
            self.session.info('【把我点开了】')
            self.iseat = await confirm.CmdDialogInput.execute(self, 'input -chihe')
            self.session.info(f'输入成功：{self.iseat}')

    def get_value_color(self, current, maximum):
        """根据当前值与最大值的比例返回相应的颜色样式
        参数:
            current: 当前值
            maximum: 最大值
        返回:
            颜色样式字符串
        """
        if maximum <= 0:
            return "fg:#eeeeee"  # 灰色

        percentage = current / maximum
        # self.session.info(percentage)
        # 根据进度改变颜色：红->橙->黄->绿
        if percentage < 0.25:
            return "fg:#800000"  # 深红色
        elif percentage < 0.5:
            return "fg:#ff6600"  # 橙色
        elif percentage < 0.6:
            return "fg:red"  # 红色
        elif percentage < 0.7:
            return "fg:yellow"  # 黄色
        elif percentage < 0.8:
            return "fg:#FFD700"  # 金色
        elif percentage < 0.95:
            return "fg:#7FFF00"  # 浅绿色
        elif percentage > 1:
            return "fg:cyan"  # 青色
        else:
            return "fg:green"  # 绿色