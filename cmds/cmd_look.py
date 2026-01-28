from pymud import Command, IConfig, exception, trigger
from utils.sqlite import DatabaseManager

class CmdLook(Command, IConfig):
    def __init__(self, session, *args, **kwargs):
        kwargs.setdefault("id", "cmd_look")        
        super().__init__(session, patterns = r"^(?:l|look)$", *args, **kwargs)
        self.reset()
        self._desc = ""
        self._room_name = ""
        
        # 初始化数据库连接，使用自定义表名
        self.db = DatabaseManager()
        if not self.db.connect():
            self.session.error("数据库连接失败！")


    @trigger(r"^[>]*(?:\s)?([\u4e00-\u9fa5].+)\s-\s*(?:杀戮场)?(?:\[(\S+)\]\s*)*(?:㊣\s*)?[★|☆|∞|\s]*$", group="rname")
    def rname(self, name, line, wildcards):
        """提取房间名称"""
        self._room_name = line.strip()
        self.session.enableGroup("rname", False)

    @trigger(r'^\s{4}[^\|~/_\s].*$', group="desc", id="cmd.look.desc")
    def desc(self, name, line, wildcards):
        """提取房间描述"""
        desc = line.strip()
        self._desc += desc
        self.session.enableGroup("desc", False)

    @exception
    async def execute(self, cmd="look", *args, **kwargs):
        """执行look命令并保存到数据库"""
        self.reset()
        
        try:
            # 执行look命令并等待响应
            await self.session.waitfor(cmd, self.session.tris["cmd.look.desc"].triggered())
            
            # 显示房间信息
            if self._desc:
                self.session.info(self._desc)
            else:
                self.session.warning("未获取到房间描述信息")
            
            # 将房间信息保存到数据库
            if self._room_name and self._desc:
                # 获取表名（从session变量中获取城市名）
                table_name = self.session.vars.get('profile', {}).get('city', 'yangzhou')
                
                # 使用新的增删改查方法
                # 1. 先查询房间是否已存在
                existing_room = self.db.select_room(room_name=self._room_name, table_name=table_name)
                
                if existing_room:
                    # 2. 如果房间已存在，更新房间描述
                    room_id = existing_room.get('id')
                    if room_id:
                        if self.db.update_room(room_id, description=self._desc, table_name=table_name):
                            self.session.info(f"房间信息已更新到数据库: {self._room_name} (ID: {room_id})")
                        else:
                            self.session.error(f"房间信息更新失败: {self._room_name}")
                    else:
                        self.session.error(f"无法获取房间ID: {self._room_name}")
                else:
                    # 3. 如果房间不存在，插入新房间
                    if self.db.insert_room(self._room_name, self._desc, table_name=table_name):
                        self.session.info(f"房间信息已保存到数据库: {self._room_name}")
                    else:
                        self.session.error(f"房间信息保存失败: {self._room_name}")
            else:
                if not self._room_name:
                    self.session.warning("未获取到房间名称")
                if not self._desc:
                    self.session.warning("未获取到房间描述")
        
        except Exception as e:
            self.session.error(f"执行look命令时发生错误: {str(e)}")
            return self.FAILURE
        
        return self.SUCCESS