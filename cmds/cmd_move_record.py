from pymud import Command, IConfig, exception, trigger
import re


class CmdMoveRecord(Command, IConfig):
    def __init__(self, session, *args, **kwargs):
        kwargs.setdefault("id", "cmd_move_record")        
        # 匹配所有移动命令
        super().__init__(session, patterns=r"^(?:n|s|e|w|ne|nw|se|sw|u|d|north|south|east|west|northeast|northwest|southeast|southwest|up|down|go\s+\w+)$", **kwargs)
        self.db = self.session.application.get_globals('db')
        
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
        last_room_id = getattr(self.session, 'current_room_id', None)
        if last_room_id:
            self.session.last_room_id = last_room_id
        
        # 解析移动方向
        move_cmd = cmd.split()[-1] if 'go ' in cmd else cmd
        direction = self.direction_map.get(move_cmd, move_cmd)
        self.session.last_move_direction = direction
        
        # 执行移动命令
        await self.session.exec(cmd)
        
        return self.SUCCESS
