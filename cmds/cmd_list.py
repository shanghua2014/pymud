from pymud import Command, IConfig, exception, trigger,Trigger

class CmdLook(Command, IConfig):
    def __init__(self, session, *args, **kwargs):
        kwargs.setdefault("id", "cmd_list")        
        super().__init__(session, patterns = r"^(?:list)(?:\s+(\S.+))?$", **kwargs)
        self._goods = []
        self._price=[]
        self.db = self.session.application.get_globals('db')

    @trigger(r'^[╭┌][─]+你可以向.+购买下列物品[─┬]+[┐╮]$', id = "cmd.list.start", group = "cmd.list")
    def start(self, name, line, wildcards):    
        self.session.enableGroup("cmd.list", types = [Trigger])

    @trigger(r'^[╰└][─┴]+[^└─┴┘]+[─]+[┘╯]$', id = "cmd.list.end", group = "cmd.list")
    def stop(self, name, line, wildcards):      
        self.session.enableGroup("cmd.list", enabled = False, types = [Trigger])

    # │没药(Mo yao)                                │一两白银                      │
    @trigger(r'^\s?│(.+\(\w+\s\w+\))\s+│(\S+)\s+│$', group = "cmd.list")
    def getList(self, name, line, wildcards):
        item, price = wildcards
        self._goods.append(item)
        self._price.append(price)

    @exception
    async def execute(self, cmd="list", *args, **kwargs):
        # 执行list命令并等待响应
        self.session.tris["cmd.list.start"].enabled = True
        await self.session.waitfor(cmd, self.session.tris["cmd.list.end"].triggered())
        city = self.session.vars['char_profile']['city']
        short = self.session.vars['move']['short']
        # 循环处理商品数据
        if self._goods and self.db:
            for i, item in enumerate(self._goods):
                gname = item.strip()
                price = self._price[i] if i < len(self._price) else ""
                
                # 查询商品是否已存在
                results = self.db.select_data("SELECT id FROM goods WHERE gname = ?", (gname,))
                
                if not results:
                    # 商品不存在，插入新记录
                    insert_sql = """
                    INSERT INTO goods (city,short,gname, price) 
                    VALUES (?, ?, ?, ?)
                    """
                    self.db.insert_data(insert_sql, (city, short, gname, price), debug=True)
                    self.session.info(f"添加商品: {gname} - {price}")
        
        # 清空临时数据
        self._goods.clear()
        self._price.clear()
        
        return self.SUCCESS