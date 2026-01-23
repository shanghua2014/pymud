from pymud import Command, Trigger, IConfig, DotDict, exception, trigger

class CmdScore(Command, IConfig):
    def __init__(self, session, *args, **kwargs):
        kwargs.setdefault("id", "cmd_score")        
        super().__init__(session, "^(score|sc)$", *args, **kwargs)
        if self.session.getVariable("char_profile") is None:
            self.session.setVariable("char_profile", {})
        self.profile = self.session.getVariable("char_profile")

    @trigger(r'^[╭┌][─]+人物详情[─┬]+[┐╮]$', id = "cmd.score.start", group = "cmd.score")
    def start(self, name, line, wildcards):    
        self.session.enableGroup("cmd.score", types = [Trigger])


    @trigger(r'^[╰└][─┴]+[^└─┴┘]+[─]+[┘╯]$', id = "cmd.score.end", group = "cmd.score")
    def stop(self, name, line, wildcards):      
        self.session.enableGroup("cmd.score", enabled = False, types = [Trigger])

    @trigger(r'^│\s+(?:(\S+)\s)+(\S+)\((\S+)\)\s*√?\s+│.+│$', "score_info", "cmd.score")        
    def charinfo(self, name, line, wildcards):
        # 更新为只从此行获取角色id和名称信息
        # 添加空值检查，避免NoneType错误
        if len(wildcards) >= 3 and wildcards[1] is not None:
            self.profile["名字"] = wildcards[1]
        else:
            # 如果匹配失败，记录调试信息
            self.session.debug(f"charinfo匹配失败: {line}, wildcards: {wildcards}")

    @trigger(r'^│国籍：\S+\s+户籍：\S+.+│门派：(\S+)(?:\s\S+)*\s+│$', group = "cmd.score")    
    def menpaiinfo(self, name, line, wildcards):
        # 添加空值检查
        if wildcards and wildcards[0] is not None:
            self.profile["门派"] = wildcards[0].rstrip()

    # │上线：扬州客店    签到：暂无          │师承：宋远桥
    @trigger(r'^.*│\s*师承：(\S+)\s+│', group = "cmd.score")
    def masterinfo(self, name, line, wildcards):
        # 添加空值检查
        if wildcards and wildcards[0] is not None:
            self.profile["师承"] = wildcards[0].rstrip()

    # │性别：男性        姻缘：未遇良人      │门忠：76
    @trigger(r'^.*│\s*门忠：(\S+)\s+│', group = "cmd.score")
    def genderinfo(self, name, line, wildcards):
        # 添加空值检查
        if wildcards and wildcards[0] is not None:
            self.profile["门忠"] = wildcards[0].strip()
        
    # │杀生：0人               │职业：                  │存款：60黄金            │
    @trigger(r'^.*│\s*存款：(\S+)\s+│$', group = "cmd.score")
    def bankinfo(self, name, line, wildcards):
        # 添加空值检查
        if wildcards and wildcards[0] is not None:
            self.profile["存款"] = wildcards[0].strip()

    @trigger((r'^.*│\s*道德：(\S+)\s+│'), group = "cmd.score")
    def repuinfo(self, name, line, wildcards):
        self.profile["道德"] = wildcards[0]


    @exception
    async def execute(self, cmd = "score", *args, **kwargs):
        self.reset()
        self.session.tris["cmd.score.start"].enabled = True
        await self.session.waitfor(cmd, self.session.tris["cmd.score.end"].triggered())
        self.session.vars["char_profile"].update(self.profile)
        return self.SUCCESS