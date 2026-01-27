import os
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

# 简化 MapRecorder 为存根，地图功能已禁用

@dataclass
class Room:
    room_id: str = ''
    name: str = ''
    exits: Dict[str, str] = field(default_factory=dict)
    long_desc: str = ''
    area: str = ''
    raw_text: str = ''
    npcs: List[str] = field(default_factory=list)
    discovered_at: str = ''

class MapRecorder:
    def __init__(self, session, *args, **kwargs):
        self.session = session
        self.rooms: Dict[str, Room] = {}
        self.current_room_id: Optional[str] = None
        # data 目录仍确保存在
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        self.map_dir = os.path.join(project_root, 'data')
        os.makedirs(self.map_dir, exist_ok=True)

    def set_city(self, city_name: str):
        # 地图功能已禁用
        return

    def on_move(self, id, line, wildcards):
        return

    def add_room(self, *args, **kwargs):
        return

    def set_current_room(self, *args, **kwargs):
        return

    def save_map(self):
        return

    def get_room_info(self, room_id: str):
        return None

    def _generate_room_id(self, room_name: str) -> str:
        return room_name