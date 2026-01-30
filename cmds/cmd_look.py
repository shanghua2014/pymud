from pymud import Command, IConfig, exception, trigger


class CmdLook(Command, IConfig):
    def __init__(self, session, *args, **kwargs):
        kwargs.setdefault("id", "cmd_look")        
        super().__init__(session, patterns = r"^(?:l|look)(?:\s+(\S.+))?$", **kwargs)
        self.db = self.session.application.get_globals('db')
        self.reset()
        

    def reset(self):
        self.session.info("重置数据")
        self._desc = ""
        self._rname = ""
        self._npc = ""
        self._dir = ""
        self.session.enableGroup("rname", True)
        self.session.enableGroup("des", True)


    @trigger(r"^[>]*(?:\s)?([\u4e00-\u9fa5].+)\s-\s*(?:杀戮场)?(?:\[(\S+)\]\s*)*(?:㊣\s*)?([★|☆|∞|\s])*$",group = "rname")
    def rname(self, name, line, wildcards):
        """提取房间名称"""
        self._rname = line.strip()
        # self.session.info(f"发现房间名称: {self._rname}")
        if "铺" in self._rname or "店" in self._rname or "房" in self._rname:
            self.session.exec("list")

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
        self._npc+=(npc+",")

    @exception
    async def execute(self, cmd="look", *args, **kwargs):
        # 执行look命令并等待响应
        self.reset()
        await self.session.waitfor(cmd, self.session.tris["cmd.look.desc"].triggered())

        city = self.session.vars['char_profile']['city']
        dirt = self.session.vars['move']['dir']
        for i in dirt:
            self._dir  += i+","
        # 查询房间是否已存在
        results = self.db.select_data(f"SELECT id FROM {city} WHERE rname = ? AND desc = ?", (self._rname, self._desc))
        if not results:
            # 房间不存在，插入新记录
            insert_sql = """
            INSERT INTO goods (rname,desc,npc, dir) 
            VALUES (?, ?, ?, ?)
            """
            self.db.insert_data(insert_sql, (self._rname, self._desc, self._npc, self._dir), debug=True)
            self.session.info(f"添加房间标题: {self._rname}")
            self.session.info(f"添加房间描述: {self._desc}")
        
        return self.SUCCESS