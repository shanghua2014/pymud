# 修改后的完整代码
import asyncio
import re
import time
from pymud import IConfig, GMCPTrigger, Trigger

import platform

from fullme_ui import open_fullme_window, close_fullme_window, is_fullme_window_open

"""
GMCP频道：
北侠命令: tune gmcp、
        set raw_data_format 2  设置 hp * 输出格式
        tune gmcp format raw/pretty 设置中/英文格式
        〔GMCP〕GMCP.Combat: [{"jing_wound":0,"qi_damage":97,"eff_jing_pct":100,"qi_wound":96,"eff_qi_pct":81,"jing_pct":100,"jing_damage":0,"name":"流氓头","qi_pct":55,"id":"liumang tou#4336421"}]
        ( 地痞似乎十分疲惫，看来需要好好休息了。)『地痞(damage:+97 气血:50%/91%)』
        ( 地痞似乎十分疲惫，看来需要好好休息了。)『地痞(damage:+97 气血:50%/91%)』
"""


class BaseTriggers(IConfig):
    def __init__(self, session, *args, **kwargs):
        self.session = session
        self.ws = session.application.get_globals("ws_client")

        # 初始化profile，确保它是一个字典
        self.profile = self.session.getVariable("char_profile")
        if self.profile is None:
            self.profile = {}
            self.session.setVariable("char_profile", self.profile)

        self._gmcp_status = [
            GMCPTrigger(
                self.session, "GMCP.Status", group="sys", onSuccess=self.on_all, keepEval=True
            ),
            # GMCPTrigger(
            #     self.session, "GMCP.raw_hp", group="sys", onSuccess=self.on_all, keepEval=True
            # ),
        # 〔GMCP〕GMCP.Buff: {"is_end": "false", "name": "加力", "effect2": "躲闪+15", "last_time": 120,
        #                   "effect1": "攻击命中+15"}
        #     GMCPTrigger(
        #         self.session, "GMCP.Buff", group="sys", onSuccess=self.on_buff
        #     ),
            GMCPTrigger(
                self.session, "GMCP.Move", group="sys", onSuccess=self.on_move
            ),
            Trigger(self.session, r"^[> ]?目前权限：\(player\)",
                    onSuccess=self.tri_init_vars, group="sys", keepEval=True
                    ),
            Trigger(self.session, r"^[> ]?重新连线完毕。",
                    onSuccess=self.tri_init_vars, group="sys", keepEval=True
                    ),
            Trigger(self.session, r"^http://fullme.pkuxkx.net/robot.php.+$",
                    group="sys", onSuccess=self.tri_get_fullme,
                    ),
            Trigger(
                self.session, r"^[> ]?你突然感到精神一振，浑身似乎又充满了力量！$",
                group="sys", onSuccess=self.tri_over_fullme, keepEval=True
            ),
            Trigger(
                self.session, r"^[> ]?太遗憾了。$",
                group="sys", onSuccess=self.tri_over_fullme, keepEval=True
            ),
            Trigger(
                self.session, r"^[> ]?你刚刚用过这个命令不久，还要(\d+)分钟(\d+)秒才能再用。$",
                group="sys", onSuccess=self.tri_restore_fullme
            ),
            Trigger(
                self.session, r"^[> ]?请注意，你的活跃度已经偏低.+",
                group="sys", onSuccess=self.tri_warnning_fullme
            ),
            # │ 【真气】 0       / 0
            Trigger(
                self.session, r"^\s*│\s?【真气】\s?(\d+)\s+/\s?(\d+)\s+\[.*│$",
                group="sys", onSuccess=self.tri_vigour_qi
            ),
            Trigger(
                self.session, fr"^.+\(\w+\)告诉你：【{re.escape(self.session.vars['char_profile']['名字'])}\(\w+\)】目前在【(\w+)的(\w+)】,快去摁死它吧!$",
                group="sys", onSuccess=self.tri_get_city
            )
        ]
        if 'potential' not in self.profile:
            self._gmcp_status.append(
                Trigger(self.session, fr"^│.*│【经验】\s?(\S+)\s+│$",group="sys", onSuccess=self.tri_get_potential)
            )

    def tri_get_potential(self, id, line, wildcards):
        potential = wildcards[0]
        self.session.vars['char_profile']['potential'] = potential

    def tri_get_city(self, id, line, wildcards):
        city, room = wildcards
        self.session.vars['char_profile']['city'] = city
        # 地图功能已移除，仅记录城市信息
        try:
            self.session.info(f"已记录城市信息: {city}")
        except Exception:
            pass

    # 获取真气值
    def tri_vigour_qi(self, id, line, wildcards):
        current, max = wildcards
        self.session.vars['char_profile']['vigour/qi'] = int(current)
        self.session.vars['char_profile']['vigour/max_qi'] = int(max)

    def tri_open_fullme(self):
        self.session.exec('fullme')

    # fullme_time字段校正
    def tri_restore_fullme(self, id, line, wildcards):
        minutes, seconds = wildcards
        self.session.vars['char_profile']['fullme_time'] = int(minutes) * 60 + int(seconds)

    # fullme警告，该输命令了
    def tri_warnning_fullme(self, id, line, wildcards):
        self.session.vars['char_profile']['fullme_time'] = 0

    # fullmeCD结束
    def tri_over_fullme(self, id, line, wildcards):
        self.session.vars["char_profile"]['fullme_time'] = 900
        self.tri_open_fullme()
        # 关闭Fullme验证码窗口
        try:
            if is_fullme_window_open():
                close_fullme_window()
        except Exception as e:
            self.session.error(f"关闭Fullme窗口时出错: {e}")

    # fullme获取url
    def tri_get_fullme(self, id, line, wildcards):
        # 只有 Windows 系统才调用 fullme_ui 模块打开验证码窗口
        if platform.system() != "Windows":
            return
        try:
            # 使用获取到的验证码URL打开窗口
            open_fullme_window(line)
        except ImportError as e:
            self.session.error(f"导入fullme_ui模块失败: {e}")
        except Exception as e:
            self.session.error(f"打开Fullme窗口失败: {e}")

    def on_all(self, id, line, wildcards):
        # 确保profile是字典
        # if self.profile is None:
        #     self.profile = {}
        #     self.session.setVariable("char_profile", self.profile)

        for key, value in wildcards.items():
            self.profile[key] = value
        self.session.setVariable("char_profile", self.profile)

    def on_change(self, id, line, wildcards):
        '''
        GMCP.raw_hp [{"qi":{"effective":604,"current":604,"max":604},"combat_exp":{"current":57104},"vigour/qi":{"current":0},"neili":{"current":1090,"max":1090},"jingli":{"current":1006,"max":1006},"food":{"current":102},"water":{"current":226},"jing":{"effective":435,"current":435,"max":435}}]
        '''
        pass

    def on_move(self, id, line, wildcards):
        '''
        〔GMCP〕GMCP.Move: [{"result":"true","dir":["north","south","east","west"],"short":"三清殿"}]
        〔GMCP〕GMCP.Move: [{"result":"true","dir":["north","south","east","west","up"],"short":"中央广场"}]
        〔GMCP〕GMCP.Move: [{"result":"true","dir":["east","westup","southeast","west","northdown"],"short":"青石大道"}]
        〔GMCP〕GMCP.Move: [{"result":"false"}]
        '''
        info = wildcards[0]
        try:
            if info.get("result") == "true":
                # 保存原始移动信息到 session 变量
                self.session.setVariable("move", info)
                # 将移动事件转发给地图录制器，使用 map_recorder 的 on_move 处理并保存到 json
                try:
                    # map_recorder.on_move 接受相同的触发器签名 (id, line, wildcards)
                    self.map_recorder.on_move(id, line, wildcards)
                except Exception as e:
                    # self.session.error(f"地图录制器处理移动事件失败: {e}")
                    pass
            else:
                self.session.setVariable("move", '移动失败')
        except Exception as e:
            self.session.error(f"on_move 处理失败: {e}")
        pass

    def on_buff(self, id, line, wildcards):
        '''
        〔GMCP〕GMCP.Buff: {"is_end": "false", "name": "加力", "effect2": "躲闪+15", "last_time": 120,
                          "effect1": "攻击命中+15"}
        '''
        info = wildcards[0]
        if info["is_end"] == "true":
            # 删除buff字段
            del self.session.vars['char_profile']["buff"]
        else:
            self.session.vars['char_profile']["buff"] = {"last_time": info["last_time"]}
            effect = []
            effect.append(f'命中+{info["effect1"].split("+")[1]}')
            effect.append(f'躲闪+{info["effect2"].split("+")[1]}')
            self.session.vars['char_profile']["effect"] = effect
        pass

    def tri_init_vars(self, id, line, wildcards):
        # self.initStatus()
        pass

    def initStatus(self):
        # 创建异步任务，2秒后发送"score -family"命令
        asyncio.create_task(self.delayed_score())

    async def delayed_score(self):
        """异步延迟2秒后发送命令"""
        try:
            await self.session.exec_async(" ")
            await asyncio.sleep(2)
            await self.session.exec_async("score")
            await asyncio.sleep(3)
            await self.session.exec_async("hp")
            await self.session.exec_async(f"pp {self.session.vars['id']}")
        except Exception as e:
            self.session.error(f"发送score -family命令时出错: {e}")

    def __unload__(self):
        self.session.delObject(self._gmcp_status)
