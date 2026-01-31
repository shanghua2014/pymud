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
        self.session.enableGroup("des", False)

    @trigger(r'^\s{4}[^\|~/_\s这里](.*(?:\s.+)?\(\w+\s\w+\))$', group="npcs")
    def npcs(self, name, line, wildcards):
        """提取NPC信息"""
        npc = line.strip()
        self._npc+=npc+","

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
        room_id = None
        if not results:
            # 房间不存在，插入新记录
            insert_sql = """
            INSERT INTO """+self.session.vars['char_profile']['city']+""" (rname,desc,npc, dir) 
            VALUES (?, ?, ?, ?)
            """
            self.db.insert_data(insert_sql, (self._rname, self._desc, self._npc, self._dir), debug=True)
            
            # 获取新插入房间的ID
            results = self.db.select_data(f"SELECT id FROM {city} WHERE rname = ? AND desc = ?", (self._rname, self._desc))
            if results:
                room_id = results[0]['id']
        else:
            room_id = results[0]['id']
        
        # 保存当前房间ID到session
        if room_id:
            self.session.current_room_id = room_id
            self.session.current_room_name = self._rname
            self.session.current_room_desc = self._desc
            
            # 如果有上一个房间且不在同一房间，则建立连接关系
            last_room_id = getattr(self.session, 'last_room_id', None)
            if last_room_id and last_room_id != room_id:
                # 从移动方向获取方向信息
                last_direction = getattr(self.session, 'last_move_direction', 'unknown')
                if last_direction != 'unknown':
                    # 添加双向连接
                    self.db.add_room_connection(last_room_id, room_id, last_direction)
                    
                    # 尝试添加反向连接（基于方向映射）
                    reverse_direction_map = {
                        'north': 'south', 'south': 'north',
                        'east': 'west', 'west': 'east',
                        'northeast': 'southwest', 'southwest': 'northeast',
                        'northwest': 'southeast', 'southeast': 'northwest',
                        'up': 'down', 'down': 'up'
                    }
                    reverse_direction = reverse_direction_map.get(last_direction, 'unknown')
                    if reverse_direction != 'unknown':
                        self.db.add_room_connection(room_id, last_room_id, reverse_direction)
            
            # 更新上一个房间ID
            self.session.last_room_id = room_id
        
        return self.SUCCESS