import functools, asyncio, cn2an, sys, os, random
#导入当前文件的上层目录到
sys.path.append('..')
#加入当前目录
sys.path.append(os.getcwd())

from pymud import Alias, Trigger, SimpleCommand, SimpleTrigger, SimpleAlias, Timer
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType
from pkg_confirm import confirm
from pymud.settings import Settings

DIRS_ABBR = {
    "e": "east",
    "w": "west",
    "s": "south",
    "n": "north",
    "u": "up",
    "d": "down",
    "se": "southeast",
    "sw": "southwest",
    "ne": "northeast",
    "nw": "northwest",
    "eu": "eastup",
    "wu": "westup",
    "su": "southup",
    "nu": "northup",
    "ed": "eastdown",
    "wd": "westdown",
    "sd": "southdown",
    "nd": "northdown",
    "seu": "southeastup",
    "sed": "southeastdown",
    "neu": "northeastup",
    "ned": "northeastdown",
    "swu": "southwestup",
    "swd": "southwestdown",
    "nwu": "northwestup",
    "nwd": "northwestdown",
}

class Configuration:
    
    def __init__(self, session, *args, **kwargs):
        self.session = session
        self._aliases = {}
        self._triggers = {}
        self.session.status_maker = self.status_bar_xue

        
    def create_progress_bar_styles(self, current, maximum=10, barlength=9):
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
        
        # 样式1：经典方块进度条 - 使用更小的字符
        progress_bars["classic"] = [
            ("fg:white bg:#0066cc", "■" * filled_length),  # 使用■代替█
            ("fg:white bg:#333333", "□" * remaining_length),  # 使用□代替░
            ("fg:yellow", f" {int(percentage*100)}%")
        ]
        
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
                # ("fg:cyan", f" {int(percentage*100)}%")
            ]
        else:
            progress_bars["gradient"] = [("fg:#666666", "□" * barlength)]
        # 样式4：圆角进度条 - 使用更小的字符
        progress_bars["rounded"] = [
            ("fg:#00ff00", "["),  # 使用[代替▕
            ("fg:#00ff00 bg:#00aa00", "■" * filled_length),  # 使用■代替█
            ("fg:#666666 bg:#333333", "□" * remaining_length),  # 使用□代替░
            ("fg:#00ff00", "]"),  # 使用]代替▏
            ("fg:yellow", f" {int(percentage*100)}%")
        ]
        
        return progress_bars


    def status_bar_xue(self):
        """包含多种进度条样式的状态窗口"""
        formatted_list = list()
        count = 33
        frist_count = 14
        second_count = int(count - frist_count)
        uinfo = self.session.getVariable('char_profile')
        move = self.session.getVariable('move')
        # if uinfo['名字'] is None:
        #     formatted_list.append(("fg:#DC143C", "请输入score命令"))
        #     self.session.exec("score")
        # self.session.info(uinfo)
        
        # 新的固定50%进度设置
        progress_styles_xue = self.create_progress_bar_styles(uinfo['qi'],uinfo['max_qi'])
        progress_styles_nei = self.create_progress_bar_styles(uinfo['neili'],uinfo['max_neili'])
        progress_styles_jing = self.create_progress_bar_styles(uinfo['jingli'],uinfo['max_jingli'])
        progress_styles_shen = self.create_progress_bar_styles(uinfo['jing'],uinfo['max_jing'])
        progress_styles_food = self.create_progress_bar_styles(uinfo['food'],350)
        progress_styles_water = self.create_progress_bar_styles(uinfo['water'],350)
        # progress_styles_7= self.create_progress_bar_styles(7)
        # progress_styles_8 = self.create_progress_bar_styles(8)
        # progress_styles_9 = self.create_progress_bar_styles(9)
        # progress_styles_10 = self.create_progress_bar_styles(10)
        
        # 样式2：渐变色彩
        # 第一行，第一列
        formatted_list.append(("fg:#DC143C", "气血"))
        formatted_list.extend(progress_styles_xue["gradient"])
        formatted_list.append(("", " "))
        formatted_list.append(("fg:#00BFFF", "内力"))
        formatted_list.extend(progress_styles_nei["gradient"])
        formatted_list.append(("fg:#00BFFF", " │ "))
        # 第一行，第二列
        formatted_list.append(("fg:#00BFFF", "任务："))
        formatted_list.append(("fg:#00BFFF", "无"))
        formatted_list.append(("", " "))
        formatted_list.append(("fg:#00BFFF", "目标："))
        formatted_list.append(("fg:#00BFFF", "无"))
        for i in (range(second_count-(len("无")+len("无")+13))):
            formatted_list.append(("", "　"))
        formatted_list.append(("fg:#00BFFF", "│ "))
        # 第一行，第三列
        formatted_list.append(("fg:#00BFFF", "房间：量量无量量"))
        for i in (range(second_count-(len("无量量量量")+14))):
            formatted_list.append(("", "　"))
        formatted_list.append(("fg:#00BFFF", " │ "))
        # 第一行，第四列
        formatted_list.append(("fg:#00BFFF", "连线收入"))
        for i in range(7):
            formatted_list.append(("", " "))
        formatted_list.append(("fg:#00BFFF", "│ "))
        # 第一行，第五列
        formatted_list.append(("fg:#00BFFF", "姓名："))
        formatted_list.append(("fg:#00BFFF", uinfo['名字']))
        formatted_list.append(("", " "))
        formatted_list.append(("fg:#00BFFF", "性别："))
        formatted_list.append(("fg:#00BFFF", "男"))
        formatted_list.append(("", " "))
        formatted_list.append(("fg:#00BFFF", "年龄："))
        formatted_list.append(("fg:#00BFFF", "18岁"))
        # 第一行结束
        formatted_list.append(("", "\n"))


        # 第二行，第一列
        formatted_list.append(("fg:#FF00FF", "精神"))
        formatted_list.extend(progress_styles_jing["gradient"])
        formatted_list.append(("", " "))
        formatted_list.append(("fg:#ADFF2F", "精力"))
        formatted_list.extend(progress_styles_shen["gradient"])
        formatted_list.append(("fg:#00BFFF", " │ "))
        # 第二行，第二列
        formatted_list.append(("fg:#00BFFF", "地点："))
        formatted_list.append(("fg:#00BFFF", "无"))
        for i in (range(second_count-(self.getCount("无")+10))):
            formatted_list.append(("", "　"))
        formatted_list.append(("fg:#00BFFF", " │ "))
        # 第二行，第三列
        # formatted_list.append(("", "　"))
        # formatted_list.append(("fg:#00BFFF", "↖ ↑↑ ↑ ↑↓ ↗"))
        formatted_list.append(("fg:#00BFFF", "↖"))
        formatted_list.append(("fg:#00BFFF", " ↖↑"))
        formatted_list.append(("fg:#00BFFF", " ↑↑"))
        formatted_list.append(("fg:#00BFFF", " ↑"))
        formatted_list.append((Settings.styles["link"], " ↑"))
        formatted_list.append(("fg:#00BFFF", " ↑↓"))
        formatted_list.append(("fg:#00BFFF", " ↗"))
        cc = len("↖ ↖↑ ↑↑ ↑ ↑↓ ↗")
        for i in (range(int(17-(cc)))):
            formatted_list.append(("", " "))
        formatted_list.append(("fg:#00BFFF", "│ "))
        # 第二行，第四列
        formatted_list.append(("fg:#00BFFF", "经验："))
        formatted_list.append(("fg:#00BFFF", "333"))
        for i in range(9-len(str(333))):
            formatted_list.append(("", " "))
        formatted_list.append(("fg:#00BFFF", "│ "))
        # 第二行，第五列
        formatted_list.append(("fg:#00BFFF", "门派："))
        formatted_list.append(("fg:#00BFFF", uinfo['family/family_name']))
        formatted_list.append(("fg:#00BFFF", " 师承："))
        formatted_list.append(("fg:#00BFFF", uinfo['师承']))
        formatted_list.append(("fg:#00BFFF", " 门忠："))
        formatted_list.append(("fg:#00BFFF", uinfo['门忠']))
        # 第二行结束
        formatted_list.append(("", "\n"))


        # 第三行，第一列
        formatted_list.append(("fg:#87CEEB", "食物"))
        formatted_list.extend(progress_styles_food["gradient"])
        formatted_list.append(("", " "))
        formatted_list.append(("fg:#D2B48C", "饮水"))
        formatted_list.extend(progress_styles_water["gradient"])
        formatted_list.append(("fg:#00BFFF", " │ "))
        # 第三行，第二列
        formatted_list.append(("fg:#00BFFF", "战斗："))
        if "is_fighting" in uinfo and str(uinfo['is_fighting']) == "false":
            formatted_list.append(("fg:#00BFFF", "否"))
        else:
            formatted_list.append(("fg:#00BFFF", "是"))
        formatted_list.append(("", "　"))
        formatted_list.append(("fg:#00BFFF", "状态："))
        formatted_list.append(("fg:#00BFFF", "无"))
        for i in (range(second_count-(16))):
            formatted_list.append(("", "　"))
        formatted_list.append(("fg:#00BFFF", " │ "))
        # 第三行，第三列
        # formatted_list.append(("", "　"))
        # formatted_list.append(("fg:#00BFFF", "←↑ ← ←↓ ↓→ → ↑→"))
        formatted_list.append(("fg:#00BFFF", "←↑"))
        formatted_list.append(("fg:#00BFFF", " ←"))
        formatted_list.append(("fg:#00BFFF", " ←↓"))
        formatted_list.append(("fg:#00BFFF", " ↓→"))
        formatted_list.append(("fg:#00BFFF", " →"))
        formatted_list.append(("fg:#00BFFF", " ↑→"))
        cc = len("←↑ ← ←↓ ↓→ → ↑→")
        # if cc%2 == 1:
        #     cc = cc+1
        for i in (range(int(17-(cc)))):
            formatted_list.append(("", " "))
        if cc%2 == 1:
            # self.session.info(f'c-{cc}')
            formatted_list.append(("fg:#00BFFF", ""))
            formatted_list.append(("fg:#00BFFF", "│ "))
        else:
            self.session.info(f'c3-{cc}')
            formatted_list.append(("fg:#00BFFF", ""))
            formatted_list.append(("fg:#00BFFF", "│ "))
        # 第三行，第四列
        formatted_list.append(("fg:#00BFFF", "金钱："))
        formatted_list.append(("fg:#00BFFF", "2222"))
        for i in range(9-len(str(2232))):
            formatted_list.append(("", " "))
        formatted_list.append(("fg:#00BFFF", "│ "))
        # 第三行，第五列
        formatted_list.append(("fg:#00BFFF", "道德："))
        formatted_list.append(("fg:#00BFFF", str(uinfo['道德'])))
        formatted_list.append(("fg:#00BFFF", " 存款："))
        formatted_list.append(("fg:#00BFFF", uinfo['存款']))
        # 第三行结束 
        formatted_list.append(("", "\n"))


        # 第四行，第一列
        formatted_list.append(("fg:white", "BUFF："))
        formatted_list.append(("fg:white", "一二三四五六七八"))
        for i in range(frist_count - (len("一二三四五六七八")+5)):
            formatted_list.append(("", "　"))
        
        formatted_list.append(("fg:white", "战"))
        formatted_list.append(("fg:white", "忙"))
        formatted_list.append(("", "│ "))
        # 第四行，第二列
        formatted_list.append(("fg:white", "潜能："))
        formatted_list.append(("fg:white", str(uinfo['potential'])))
        for i in range(second_count - (len(str(uinfo['potential'])))):
            formatted_list.append(("", " "))
        formatted_list.append(("", "│ "))
        # 第四行，第三列
        # formatted_list.append(("", "　"))
        # formatted_list.append(("fg:#00BFFF", "↙ ↓↓ ↓ ↓↑ ↘"))
        formatted_list.append(("fg:#00BFFF", "↙"))
        formatted_list.append(("fg:#00BFFF", " ↓↓"))
        # formatted_list.append(("fg:#00BFFF", " ↓"))
        # formatted_list.append(("fg:#00BFFF", " ↓↑"))
        # formatted_list.append(("fg:#00BFFF", " ↘"))
        cc = len("↙ ↓↓")
        # if cc%2 == 1:
        #     cc = cc+1
        # self.session.info(f'c-{cc}')
        for i in (range(int(17-(cc)))):
            formatted_list.append(("", " "))
        formatted_list.append(("fg:#00BFFF", "│ "))
        # 第四行，第四列
        formatted_list.append(("fg:#00BFFF", "潜能："))
        formatted_list.append(("fg:#00BFFF", "212"))
        for i in range(9-len(str(212))):
            formatted_list.append(("", " "))
        formatted_list.append(("fg:#00BFFF", "│ "))
        # 第四行，第五列
        formatted_list.append(("fg:white", "经验："))
        formatted_list.append(("fg:white", str(uinfo['combat_exp'])))
        for i in range(10-len(str(uinfo['combat_exp']))):
            formatted_list.append(("", " "))
        formatted_list.append(("fg:cyan", "   👉FULLME"))
        formatted_list.append(("", "\n"))

        
        # formatted_list.append(("fg:#ADFF2F", "精"))
        # formatted_list.extend(progress_styles_7["gradient"])
        # formatted_list.append(("", " "))
        # formatted_list.append(("fg:#ADFF2F", "精"))
        # formatted_list.extend(progress_styles_8["gradient"])
        # formatted_list.append(("", " "))
        # formatted_list.append(("fg:#ADFF2F", "精"))
        # formatted_list.extend(progress_styles_9["gradient"])
        # formatted_list.append(("", " "))
        # formatted_list.append(("fg:#ADFF2F", "精"))
        # formatted_list.extend(progress_styles_10["gradient"])
        return formatted_list
                
    
    def getCount(self,str):
        # 判断str中有多少个中文字符，有多少个数字，2个数字算1个，字母算1个
        # 如果数字个数是单数就按双数计算
        chinese_count = 0
        digit_count = 0
        letter_count = 0
        
        for char in str:
            # 判断中文字符（Unicode范围：\u4e00-\u9fff）
            if '\u4e00' <= char <= '\u9fff':
                chinese_count += 1
            # 判断数字
            elif char.isdigit():
                digit_count += 1
            # 判断字母（包括大小写）
            elif char.isalpha():
                letter_count += 1
        
        # 处理数字：2个数字算1个，如果数字个数是单数就按双数计算
        if digit_count > 0:
            # 如果数字个数是单数，向上取整到最近的偶数
            if digit_count % 2 == 1:
                digit_count += 1
            # 2个数字算1个
            digit_count = digit_count // 2
        
        # 总计数 = 中文字符数 + 处理后的数字数 + 字母数
        total_count = chinese_count + digit_count + letter_count
        
        return total_count