from pymud import Command, IConfig, exception, trigger
import re


class CmdMove(Command, IConfig):
    def __init__(self, session, *args, **kwargs):
        kwargs.setdefault("id", "cmd_move")        
        super().__init__(session, patterns=r"^(?:n|s|e|w|ne|nw|se|sw|u|d|north|south|east|west|northeast|northwest|southeast|southwest|up|down|go\s+\w+)$", **kwargs)
        self.db = self.session.application.get_globals('db')
        self.current_room_id = None
        self.last_room_id = None
        
        # 移动方向映射
        self.direction_map = {
            'n': 'north', 'north': 'north',
            's': 'south', 'south': 'south',
            'e': 'east', 'east': 'east',
            'w': 'west', 'west': 'west',
            'ne': 'northeast', 'northeast': 'northeast',
            'nw': 'northwest', 'northwest': 'northwest',
            'se': 'southeast', 'southeast': 'southeast',
            'sw': 'southwest', 'southwest': 'southwest',
            'u': 'up', 'up': 'up',
            'd': 'down', 'down': 'down'
        }

    def reset(self):
        pass

    @exception
    async def execute(self, cmd="n", *args, **kwargs):
        # 记录移动前的房间ID
        if hasattr(self.session, 'current_room_id'):
            self.last_room_id = getattr(self.session, 'current_room_id', None)
        
        # 执行移动命令
        await self.session.exec(cmd)
        
        # 等待一段时间让房间信息更新
        await self.session.sleep(0.5)
        
        return self.SUCCESS


class CmdMap(Command, IConfig):
    def __init__(self, session, *args, **kwargs):
        kwargs.setdefault("id", "cmd_map")        
        super().__init__(session, patterns=r"^(?:map|connections)$", **kwargs)
        self.db = self.session.application.get_globals('db')

    def reset(self):
        pass

    @exception
    async def execute(self, cmd="map", *args, **kwargs):
        # 获取当前城市和房间信息
        city = self.session.vars.get('char_profile', {}).get('city', '扬州')
        
        # 尝试获取当前房间ID
        current_room_id = getattr(self.session, 'current_room_id', None)
        
        if current_room_id:
            # 获取房间连接信息
            connections = self.db.get_room_connections(current_room_id)
            
            if connections:
                self.session.info(f"=== 房间 {current_room_id} 的连接 ===")
                for conn in connections:
                    self.session.info(f"  {conn['direction']} -> 房间ID: {conn['to_room_id']}, 名称: {conn['rname'][:30]}...")
            else:
                self.session.info("当前房间没有已记录的连接")
        else:
            self.session.info("当前房间ID未知，请先执行look命令")
        
        return self.SUCCESS