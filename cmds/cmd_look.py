from pymud import Command, IConfig, exception, trigger

from utils.sqlite import DatabaseManager

class CmdLook(Command, IConfig):
    def __init__(self, session, *args, **kwargs):
        kwargs.setdefault("id", "cmd_look")        
        super().__init__(session, patterns = r"^(?:l|look)(?:\s+(\S.+))?$", **kwargs)
        # self.db = self.application.get_globals('db')
        # self.db = DatabaseManager()
        # if not self.db.connect():
        #     self.session.error("数据库连接失败！")
        self.reset()
        

    def reset(self):
        self.session.info("重置数据")
        self._desc = ""
        self._rname = ""
        self._npc = []
        self.session.enableGroup("rname", True)
        self.session.enableGroup("des", True)


    @trigger(r"^[>]*(?:\s)?([\u4e00-\u9fa5].+)\s-\s*(?:杀戮场)?(?:\[(\S+)\]\s*)*(?:㊣\s*)?[★|☆|∞|\s]*$",group = "rname")
    def rname(self, name, line, wildcards):
        """提取房间名称"""
        self._rname = line.strip()
        # self.session.info(f"发现房间名称: {self._rname}")
        self.session.enableGroup("rname", False)

    @trigger(r'^\s{4}[^\|~/_\s].*$', group="des", id="cmd.look.desc")
    def des(self, name, line, wildcards):
        """提取房间描述"""
        desc = line.strip()
        self._desc = desc
        # self.session.info(f"发现描述: {desc}")
        self.session.enableGroup("des", False)

    @trigger(r'^\s{4}[^\|~/_\s这里](.*(?:\s.+)?\(\w+\s\w+\))$', group="npcs")
    def npcs(self, name, line, wildcards):
        """提取NPC信息"""
        npc = line.strip()
        # self.session.info(f"发现NPC: {npc}")
        self._npc.append(npc)

    @exception
    async def execute(self, cmd="look", *args, **kwargs):
        # 执行look命令并等待响应
        self.reset()
        await self.session.waitfor(cmd, self.session.tris["cmd.look.desc"].triggered())
        self.session.info(f"房间名称: {self._rname}")
        self.session.info(f"房间描述: {self._desc}")
        self.session.info(f"NPC信息: {self._npc}")
        return self.SUCCESS
        