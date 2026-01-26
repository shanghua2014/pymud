import re
import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, List, Optional
from pymud import IConfig, GMCPTrigger, Trigger

@dataclass
class Room:
    """房间数据结构"""
    room_id: str
    name: str
    exits: Dict[str, str]  # {"north": "room_id", ...}
    discovered_at: str = ""
    
    def __post_init__(self):
        if not self.discovered_at:
            self.discovered_at = datetime.now().isoformat()

class MapRecorder(IConfig):
    """地图录制器 - 记录MUD地图信息"""
    
    def __init__(self, session, *args, **kwargs):
        self.session = session
        self.rooms: Dict[str, Room] = {}
        self.current_room_id: Optional[str] = None

        # 地图数据目录
        self.map_dir = os.path.expanduser("~/github/pymud/data")
        os.makedirs(self.map_dir, exist_ok=True)

        # 从 profile 中读取城市名（key 根据你的实现调整）
        profile = self.session.getVariable("char_profile") or {}
        self.city_name = profile.get("city") or profile.get("所在城市") or "default"

        # 安全化城市名并生成文件路径
        self.map_data_file = self._map_file_path(self.city_name)
        self.position_file = os.path.join(self.map_dir, f"map_position_{self._sanitize(self.city_name)}.json")

        # 加载已有地图数据
        self.load_map()

        # 注册GMCP Move触发器
        self._triggers = [
            GMCPTrigger(
                self.session, "GMCP.Move",
                group="map_recorder",
                onSuccess=self.on_move,
                keepEval=True
            ),
        ]

    def _sanitize(self, name: str) -> str:
        """把城市名转换为文件名友好的字符串"""
        if not name:
            return "default"
        s = name.strip().lower()
        # 去掉非字母数字和中文，替换空白为下划线
        s = re.sub(r'\s+', '_', s)
        s = re.sub(r'[\\/:"*?<>|]+', '', s)
        # 只保留常见安全字符（中英文数字及下划线和短横）
        s = re.sub(r'[^\w\u4e00-\u9fff\-_.]', '', s)
        return s or "default"

    def _map_file_path(self, city_name: str) -> str:
        fname = f"map_data_{self._sanitize(city_name)}.json"
        return os.path.join(self.map_dir, fname)

    def set_city(self, city_name: str):
        """手动设置城市名并切换到对应文件；如果文件存在则加载（不覆盖）"""
        self.city_name = city_name or "default"
        self.map_data_file = self._map_file_path(self.city_name)
        self.position_file = os.path.join(self.map_dir, f"map_position_{self._sanitize(self.city_name)}.json")
        # 如果已有文件则加载并合并，不立即覆盖
        if os.path.exists(self.map_data_file):
            try:
                with open(self.map_data_file, 'r', encoding='utf-8') as f:
                    disk = json.load(f)
                # 合并磁盘数据（磁盘优先，不覆盖已有键）
                for rid, info in disk.items():
                    if rid not in self.rooms:
                        self.rooms[rid] = Room(**info)
                self.session.info(f"已加载并合并地图文件: {self.map_data_file}")
            except Exception as e:
                self.session.error(f"加载城市地图失败: {e}")
        else:
            # 新城市，立即保存空地图以创建文件（可选）
            self.save_map()

    def on_move(self, id, line, wildcards):
        """处理房间移动事件"""
        try:
            move_info = wildcards[0]
            if move_info.get("result") == "true":
                room_name = move_info.get("short", "Unknown")
                exits = move_info.get("dir", [])
                
                # 生成房间ID（使用房间名称作为ID）
                room_id = self._generate_room_id(room_name)
                
                # 添加房间
                self.add_room(room_id, room_name, exits)
                
                # 更新当前位置
                self.set_current_room(room_id)
                
                # 自动保存
                self.save_map()
                
                self.session.info(f"📍 已记录房间: {room_name} (ID: {room_id})")
        except Exception as e:
            self.session.error(f"地图录制错误: {e}")
    
    def _generate_room_id(self, room_name: str) -> str:
        """生成房间ID - 只使用房间中文名（保持纯中文，不带时间戳或其它数据）"""
        # 统一去除首尾空白
        room_name = room_name.strip()
        # 直接使用房间名称作为ID（若已存在则复用）
        return room_name

    def add_room(self, room_id: str, name: str, exits: List[str]):
        """添加或更新房间（房间ID 为纯中文名称）"""
        # 使用房间名称作为ID（调用者应传入已处理的 name）
        rid = room_id
        if rid not in self.rooms:
            self.rooms[rid] = Room(
                room_id=rid,
                name=name,
                exits={}
            )

        # 更新出口（将出口方向记录为键，目标待后续关联）
        for direction in exits:
            if direction not in self.rooms[rid].exits:
                self.rooms[rid].exits[direction] = ""  # 等待关联
    
    def set_current_room(self, room_id: str):
        """设置当前房间"""
        self.current_room_id = room_id
        # 保存当前位置
        self._save_position()
    
    def _save_position(self):
        """保存当前位置信息"""
        position_data = {
            "current_room_id": self.current_room_id,
            "timestamp": datetime.now().isoformat()
        }
        try:
            with open(self.position_file, 'w', encoding='utf-8') as f:
                json.dump(position_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.session.error(f"保存位置失败: {e}")
    
    def save_map(self):
        """导出地图数据为JSON（使用基于城市名的文件名）"""
        try:
            map_data = { room_id: asdict(room) for room_id, room in self.rooms.items() }
            with open(self.map_data_file, 'w', encoding='utf-8') as f:
                json.dump(map_data, f, ensure_ascii=False, indent=2)
            self.session.debug(f"地图已保存: {len(self.rooms)} 个房间 -> {self.map_data_file}")
        except Exception as e:
            self.session.error(f"保存地图失败: {e}")
    
    def load_map(self):
        """从基于城市名的文件加载地图数据"""
        if not os.path.exists(self.map_data_file):
            self.session.info(f"未找到地图数据文件: {self.map_data_file}")
            return
        try:
            with open(self.map_data_file, 'r', encoding='utf-8') as f:
                map_data = json.load(f)
            for room_id, room_info in map_data.items():
                self.rooms[room_id] = Room(**room_info)
            self.session.info(f"✅ 已加载地图数据: {len(self.rooms)} 个房间 ({self.map_data_file})")
        except Exception as e:
            self.session.error(f"加载地图失败: {e}")
    
    def get_room_info(self, room_id: str) -> Optional[Room]:
        """获取房间信息"""
        return self.rooms.get(room_id)
    
    def get_all_rooms(self) -> Dict[str, Room]:
        """获取所有房间"""
        return self.rooms.copy()
    
    def export_to_html(self, filepath: str = None):
        """导出地图为HTML可视化"""
        if filepath is None:
            filepath = os.path.expanduser("~/github/pymud/data/map_visual.html")
        
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>MUD地图</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .room { border: 1px solid #ccc; padding: 10px; margin: 10px 0; border-radius: 5px; }
                .room-name { font-weight: bold; color: #0066cc; }
                .exits { color: #666; font-size: 0.9em; }
            </style>
        </head>
        <body>
            <h1>MUD地图记录</h1>
            <p>总房间数: """ + str(len(self.rooms)) + """</p>
        """
        
        for room_id, room in self.rooms.items():
            html_content += f"""
            <div class="room">
                <div class="room-name">📍 {room.name}</div>
                <div class="exits">出口: {', '.join(room.exits.keys()) if room.exits else '无'}</div>
                <div style="font-size: 0.8em; color: #999;">ID: {room_id}</div>
            </div>
            """
        
        html_content += """
        </body>
        </html>
        """
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
            self.session.info(f"✅ 地图已导出为HTML: {filepath}")
        except Exception as e:
            self.session.error(f"导出HTML失败: {e}")
    
    def __unload__(self):
        """卸载时保存数据"""
        self.save_map()
        self.session.delObject(self._triggers)