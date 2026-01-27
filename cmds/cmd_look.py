from pymud import Command, IConfig, exception, trigger

class CmdLook(Command, IConfig):
    def __init__(self, session, *args, **kwargs):
        kwargs.setdefault("id", "cmd_look")        
        super().__init__(session, patterns = r"^(?:l|look)$", *args, **kwargs)
        self.reset()
        self._desc = ""

    @trigger(r"^[>]*(?:\s)?([\u4e00-\u9fa5].+)\s-\s*(?:杀戮场)?(?:\[(\S+)\]\s*)*(?:㊣\s*)?[★|☆|∞|\s]*$",group = "title")
    def title(self, name, line, wildcards):
        desc = line.strip()
        self._desc += desc
        self.session.enableGroup("title", False)

    @trigger(r'^\s{4}[^\|~/_\s].*$', group = "desc", id="cmd.look.desc")
    def desc(self, name, line, wildcards):
        desc = line.strip()
        self._desc += desc
        self.session.enableGroup("desc", False)

    @exception
    async def execute(self, cmd = "look", *args, **kwargs):
        self.reset()
        await self.session.waitfor(cmd, self.session.tris["cmd.look.desc"].triggered())
        self.session.info(self._desc)
        return self.SUCCESS