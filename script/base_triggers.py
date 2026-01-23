# 修改后的完整代码
import asyncio
from pymud import IConfig, GMCPTrigger, Trigger

"""
GMCP频道：
北侠命令: tune gmcp、
        set raw_data_format 2  设置 hp * 输出格式
        tune gmcp format raw/pretty 设置中/英文格式
"""


class GMCPChannel(IConfig):
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
                self.session, "GMCP.Status", group="sys", onSuccess=self.on_all
            ),
            # GMCPTrigger(
            #     self.session, "GMCP.raw_hp", group="sys", onSuccess=self.on_change
            # ),
            
            GMCPTrigger(
                self.session, "GMCP.Move", group="sys", onSuccess=self.on_move
            ),
            Trigger(self.session, r"^目前权限：\(player\)",
                onSuccess=self.tri_init_vars, group="sys", id="tri_init_vars",keepEval=True
            ),
            Trigger(self.session, r"^重新连线完毕。",
                onSuccess=self.tri_init_vars, group="sys", id="tri_init_vars2",keepEval=True
            ),
            # Trigger(self.session, r"^http://fullme.pkuxkx.net/robot.php.+$",
            #         id="tri_get_fullme", group="sys", onSuccess=self.tri_get_fullme,
            #         ),
            Trigger(
                self.session, r"^你突然感到精神一振，浑身似乎又充满了力量！",
                id="tri_over_fullme", group="sys", onSuccess=self.tri_over_fullme
            ),
            Trigger(
                self.session, r"^你刚刚用过这个命令不久，还要(\d+)分钟(\d+)秒才能再用。$",
                id="tri_restore_fullme", group="sys", onSuccess=self.tri_restore_fullme
            ),
            Trigger(
                self.session, r"^[> ]?请注意，你的活跃度已经偏低.+",
                id="tri_restore_fullme2", group="sys", onSuccess=self.tri_restore_fullme2
            )
        ]

    # 校正fullme_time
    def tri_restore_fullme(self, id, line, wildcards):
        minutes, seconds = wildcards
        self.session.vars['char_profile']['fullme_time'] = int(minutes) * 60 + int(seconds)
        pass
    def tri_restore_fullme2(self, id, line, wildcards):
        self.session.vars['char_profile']['fullme_time'] = 0
        pass

    def tri_over_fullme(self, id, line, wildcards):
        self.session.info("你重新获得了满力状态")
        self.session.vars["char_profile"]['fullme_time'] = 900
        pass


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
        # 确保profile是字典
        # if self.profile is None:
        #     self.profile = {}
        #     self.session.setVariable("char_profile", self.profile)
        # for key, value in wildcards[0].items():
        #     self.session.info(f"{key}: {value}")
        #     self.profile[key] = value
        # # 更新session中的变量
        # self.session.setVariable("char_profile", self.profile)
        self.session.vars("char_profile").update(wildcards[0])

    def on_move(self, id, line, wildcards):
        '''
        〔GMCP〕GMCP.Move: [{"result":"true","dir":["north","south","east","west"],"short":"三清殿"}]
        〔GMCP〕GMCP.Move: [{"result":"true","dir":["north","south","east","west","up"],"short":"中央广场"}]
        〔GMCP〕GMCP.Move: [{"result":"true","dir":["east","westup","southeast","west","northdown"],"short":"青石大道"}]
        〔GMCP〕GMCP.Move: [{"result":"false"}]
        '''
        info = wildcards[0]
        if info["result"] == "true":
            self.session.setVariable("move", info)
        else:
            self.session.setVariable("move", '移动失败')
        pass

    def tri_init_vars(self, id, line, wildcards):
        self.initStatus()
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
        except Exception as e:
            self.session.error(f"发送score -family命令时出错: {e}")

    def __unload__(self):
        self.session.delObject(self._gmcp_status)