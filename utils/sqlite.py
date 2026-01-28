import logging
import sqlite3
from typing import List, Dict, Any, Optional

class DatabaseManager:
    """SQLite数据库管理类"""
    
    def __init__(self, db_path: str = "maps.db", table_name: str = "扬州"):
        """
        初始化数据库连接
        
        Args:
            db_path: 数据库文件路径，默认为当前目录下的maps.db
            table_name: 默认表名，默认为 扬州
        """
        self.db_path = db_path
        self.table_name = table_name
        self.connection = None
        self.logger = logging.getLogger(__name__)
    
    def connect(self) -> bool:
        """连接到数据库"""
        try:
            self.connection = sqlite3.connect(self.db_path)
            self.connection.row_factory = sqlite3.Row  # 允许以字典方式访问行
            self.logger.info(f"成功连接到数据库: {self.db_path}")
            return True
        except sqlite3.Error as e:
            self.logger.error(f"连接数据库失败: {e}")
            return False
    
    def disconnect(self):
        """断开数据库连接"""
        if self.connection:
            self.connection.close()
            self.logger.info("数据库连接已关闭")
    
    def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """
        执行查询语句并返回结果
        
        Args:
            query: SQL查询语句
            params: 查询参数
            
        Returns:
            查询结果列表，每个结果是一个字典
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, params)
            results = [dict(row) for row in cursor.fetchall()]
            return results
        except sqlite3.Error as e:
            self.logger.error(f"查询执行失败: {e}")
            return []
    
    def execute_update(self, query: str, params: tuple = ()) -> bool:
        """
        执行更新操作（INSERT, UPDATE, DELETE）
        
        Args:
            query: SQL更新语句
            params: 更新参数
            
        Returns:
            操作是否成功
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, params)
            self.connection.commit()
            return True
        except sqlite3.Error as e:
            self.logger.error(f"更新操作失败: {e}")
            self.connection.rollback()
            return False
    
    def get_table_info(self, table_name: str = None) -> List[Dict[str, Any]]:
        """
        获取表结构信息
        
        Args:
            table_name: 表名，如果为None则使用默认表名
            
        Returns:
            表结构信息列表
        """
        if table_name is None:
            table_name = self.table_name
        query = f"PRAGMA table_info({table_name})"
        return self.execute_query(query)
    
    def get_all_tables(self) -> List[str]:
        """获取数据库中所有表名"""
        query = "SELECT rname FROM sqlite_master WHERE type='table'"
        results = self.execute_query(query)
        return [row['rname'] for row in results]
    
    # 增删改查四个独立方法
    
    def insert_room(self, rname: str, desc: str, table_name: str = None) -> bool:
        """
        插入新房间记录（增）
        
        Args:
            rname: 房间名称
            desc: 房间描述
            table_name: 表名，如果为None则使用默认表名
            
        Returns:
            插入是否成功
        """
        if table_name is None:
            table_name = self.table_name
        
        # 检查表结构，确定字段名
        table_info = self.get_table_info(table_name)
        if not table_info:
            self.logger.error(f"表 {table_name} 不存在或无法获取表结构")
            return False
        
        # 根据表结构构建INSERT语句
        columns = [col['rname'] for col in table_info]
        
        if 'rname' in columns and 'desc' in columns:
            # 标准表结构：name, desc, npc, goods
            query = f"INSERT INTO {table_name} (rname, desc, npc, goods) VALUES (?, ?, ?, ?)"
            params = (rname, desc, '', '')  # npc和goods设为空字符串
        elif 'rname' in columns and 'desc' in columns:
            # 另一种表结构：room_name, desc, npc, goods
            query = f"INSERT INTO {table_name} (rname, desc, npc, goods) VALUES (?, ?, ?, ?)"
            params = (rname, desc, '', '')  # npc和goods设为空字符串
        else:
            self.logger.error(f"表 {table_name} 结构不兼容，无法插入数据")
            return False
        
        return self.execute_update(query, params)
    
    def select_room(self, rname: str = None, room_id: int = None, table_name: str = None) -> Optional[Dict[str, Any]]:
        """
        查询房间记录（查）
        
        Args:
            rname: 房间名称（模糊匹配）
            room_id: 房间ID（精确匹配）
            table_name: 表名，如果为None则使用默认表名
            
        Returns:
            房间信息字典，如果未找到返回None
        """
        if table_name is None:
            table_name = self.table_name
        
        if room_id is not None:
            # 按ID精确查询
            query = f"SELECT * FROM {table_name} WHERE id = ?"
            results = self.execute_query(query, (room_id,))
        elif rname is not None:
            # 按名称模糊查询
            query = f"SELECT * FROM {table_name} WHERE rname LIKE ? OR rname LIKE ?"
            results = self.execute_query(query, (f"%{rname}%", f"%{rname}%"))
        else:
            self.logger.error("必须提供room_name或room_id参数")
            return None
        
        return results[0] if results else None
    
    def update_room(self, room_id: int, desc: str = None, rname: str = None, table_name: str = None) -> bool:
        """
        更新房间记录（改）
        
        Args:
            room_id: 房间ID
            desc: 新的房间描述
            rname: 新的房间名称
            table_name: 表名，如果为None则使用默认表名
            
        Returns:
            更新是否成功
        """
        if table_name is None:
            table_name = self.table_name
        
        if desc is None and rname is None:
            self.logger.error("必须提供desc或room_name参数")
            return False
        
        # 构建UPDATE语句
        set_parts = []
        params = []
        
        if desc is not None:
            set_parts.append("desc = ?")
            params.append(desc)
        
        if rname is not None:
            set_parts.append("rname = ?")
            params.append(rname)
        
        set_parts.append("updated_at = CURRENT_TIMESTAMP")
        
        query = f"UPDATE {table_name} SET {', '.join(set_parts)} WHERE id = ?"
        params.append(room_id)
        
        return self.execute_update(query, tuple(params))
    
    def delete_room(self, room_id: int = None, rname: str = None, table_name: str = None) -> bool:
        """
        删除房间记录（删）
        
        Args:
            room_id: 房间ID
            rname: 房间名称
            table_name: 表名，如果为None则使用默认表名
            
        Returns:
            删除是否成功
        """
        if table_name is None:
            table_name = self.table_name
        
        if room_id is not None:
            query = f"DELETE FROM {table_name} WHERE id = ?"
            params = (room_id,)
        elif rname is not None:
            query = f"DELETE FROM {table_name} WHERE rname = ? OR rname = ?"
            params = (rname, rname)
        else:
            self.logger.error("必须提供room_id或room_name参数")
            return False
        
        return self.execute_update(query, params)
    
    # 保持向后兼容的方法
    def get_room_info(self, rname: str, table_name: str = None) -> Dict[str, Any]:
        """
        根据房间名称获取房间信息（向后兼容）
        
        Args:
            rname: 房间名称
            table_name: 表名，如果为None则使用默认表名
            
        Returns:
            房间信息字典
        """
        return self.select_room(rname=rname, table_name=table_name)
    
    def save_room_info(self, rname: str, desc: str, table_name: str = None) -> bool:
        """
        保存或更新房间信息（向后兼容）
        
        Args:
            rname: 房间名称
            desc: 房间描述
            table_name: 表名，如果为None则使用默认表名
            
        Returns:
            操作是否成功
        """
        if table_name is None:
            table_name = self.table_name
        
        # 检查房间是否已存在
        existing_room = self.select_room(rname=rname, table_name=table_name)
        
        if existing_room:
            # 更新现有房间
            return self.update_room(existing_room['id'], desc=desc, table_name=table_name)
        else:
            # 添加新房间
            return self.insert_room(rname, desc, table_name=table_name)

# 创建一个简单的测试脚本，用于查看数据库结构
if __name__ == "__main__":
    db = DatabaseManager()
    if db.connect():
        print("数据库连接成功！")
        
        # 查看所有表
        tables = db.get_all_tables()
        print(f"\n数据库中的表: {tables}")
        
        # 查看表结构
        for table in tables:
            print(f"\n{table}表结构:")
            columns = db.get_table_info(table)
            for col in columns:
                print(f"  {col['rname']} ({col['type']})")
        
        # 测试增删改查方法
        print("\n测试增删改查方法:")
        
        # 插入测试数据
        if db.insert_room("测试房间", "这是一个测试房间"):
            print("✓ 插入成功")
        else:
            print("✗ 插入失败")
        
        # 查询测试数据
        room = db.select_room(rname="测试房间")
        if room:
            print(f"✓ 查询成功: {room}")
            
            # 更新测试数据
            if db.update_room(room['id'], desc="更新后的描述"):
                print("✓ 更新成功")
            else:
                print("✗ 更新失败")
            
            # 删除测试数据
            if db.delete_room(room_id=room['id']):
                print("✓ 删除成功")
            else:
                print("✗ 删除失败")
        else:
            print("✗ 查询失败")
        
        db.disconnect()
    else:
        print("数据库连接失败！")