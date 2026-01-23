import traceback, re, asyncio
from pymud import Command, Trigger, SimpleTrigger, SimpleCommand, IConfig

from ..common import MOVE_PAUSE

class CmdWalkPause(SimpleCommand, IConfig):
    WALK_PAUSE_CMDS = ("zou tiesuo", r"ride\s\S+", r"qu\s\S+", "guo qiao", "sheng bridge", "climb stiff")

    def __init__(self, session, *args, **kwargs):
        kwargs.setdefault('id', 'cmd_walkpause')

        self._tris = [
            Trigger(session, s, group = "walkpause") for s in MOVE_PAUSE   
        ]
        self._tri_che = Trigger(session,  r'^[> ]*大车停稳了下来，你可以下车\(xia\)了。$', group = "walkpause", onSuccess = self._onArrived)
        self._tri_light = SimpleTrigger(session, r'^[> ]*一盏很普通的照明灯，看起来似乎没有什么特别。', '#wa 500;l light', group = "walkpause")

        avai_cmds = r"^({0})$".format("|".join(self.WALK_PAUSE_CMDS))
        super().__init__(session, avai_cmds, self._tris, timeout = 30, *args, **kwargs)

    def __unload__(self):
        self.session.delObjects(self._tris)
        self.session.delObject(self._tri_che)

    def _onArrived(self, name, line, wildcards):
        # 要为_onArrived增加对xia之后的判断，以支持惯性导航的寻路
        self.session.writeline("xia")
    
    def _atYajian(self, name, line, wildcards):
        self.session.writeline("climb yafeng")

    def onSuccess(self, *args, **kwargs):
        #为walk_pause增加Move的惯性导航的寻路支持
        return self.session.cmds.cmd_move.update_ins_location(self._executed_cmd, self.session.vars.room)
    
    async def execute(self, cmd, *args, **kwargs):
        return await super().execute(cmd, *args, **kwargs)
