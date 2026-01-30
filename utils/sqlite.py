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
        self.logger = logging.getLogger(self.__class__.__name__)

    
    def connect(self) -> bool:
        """连接到数据库"""
        try:
            self.connection = sqlite3.connect(self.db_path)
            self.connection.row_factory = sqlite3.Row  # 允许以字典方式访问行
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
        # 参数安全检查
        if not self._validate_sql_params(query, params):
            self.logger.error("SQL参数验证失败")
            return False
            
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, params)
            self.connection.commit()
            return True
        except sqlite3.Error as e:
            self.logger.error(f"更新操作失败: {e}")
            self.connection.rollback()
            return False
    
    def _validate_sql_params(self, query: str, params: tuple) -> bool:
        """
        验证SQL语句和参数的安全性
        
        Args:
            query: SQL语句
            params: 参数元组
            
        Returns:
            是否通过验证
        """
        # 检查参数数量是否匹配
        param_placeholders = query.count('?')
        if param_placeholders != len(params):
            self.logger.error(f"参数数量不匹配: SQL需要{param_placeholders}个参数，实际提供{len(params)}个")
            return False
        
        # 检查SQL语句是否包含危险操作
        dangerous_keywords = ['DROP', 'DELETE', 'TRUNCATE', 'ALTER']
        upper_query = query.upper()
        for keyword in dangerous_keywords:
            if keyword in upper_query and 'DROP TABLE' not in upper_query:
                # 允许DROP TABLE操作，但需要谨慎
                if keyword != 'DROP' or 'DROP TABLE' not in upper_query:
                    self.logger.warning(f"检测到潜在危险操作: {keyword}")
        
        return True
    
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
    
    # 增删改查四个独立方法 - 支持自定义SQL
    
    def insert_data(self, sql: str, params: tuple = (), debug: bool = False) -> bool:
        """
        执行自定义插入操作（增）
        db.insert_data("INSERT INTO 表名 (字段1, 字段2) VALUES (?, ?)", ("值1", "值2"))
        
        Args:
            sql: 自定义INSERT SQL语句
            params: SQL参数
            debug: 是否打印SQL调试信息
            
        Returns:
            插入是否成功
        """
        if debug:
            self.logger.info(f"SQL: {sql}")
            self.logger.info(f"参数: {params}")
        return self.execute_update(sql, params)
    
    def select_data(self, sql: str, params: tuple = (), debug: bool = False) -> List[Dict[str, Any]]:
        """
        执行自定义查询操作（查）
        results = db.select_data("SELECT * FROM 表名 WHERE 条件 = ?", ("条件值",))
        
        Args:
            sql: 自定义SELECT SQL语句
            params: SQL参数
            debug: 是否打印SQL调试信息
            
        Returns:
            查询结果列表
        """
        if debug:
            self.logger.info(f"SQL: {sql}")
            self.logger.info(f"参数: {params}")
        return self.execute_query(sql, params)
    
    def update_data(self, sql: str, params: tuple = (), debug: bool = False) -> bool:
        """
        执行自定义更新操作（改）
        db.update_data("UPDATE 表名 SET 字段 = ? WHERE id = ?", ("新值", 1))

        Args:
            sql: 自定义UPDATE SQL语句
            params: SQL参数
            debug: 是否打印SQL调试信息
            
        Returns:
            更新是否成功
        """
        if debug:
            self.logger.info(f"SQL: {sql}")
            self.logger.info(f"参数: {params}")
        return self.execute_update(sql, params)
    
    def delete_data(self, sql: str, params: tuple = (), debug: bool = False) -> bool:
        """
        执行自定义删除操作（删）
        db.delete_data("DELETE FROM 表名 WHERE id = ?", (1,))
        
        Args:
            sql: 自定义DELETE SQL语句
            params: SQL参数
            debug: 是否打印SQL调试信息
            
        Returns:
            删除是否成功
        """
        if debug:
            self.logger.info(f"SQL: {sql}")
            self.logger.info(f"参数: {params}")
        return self.execute_update(sql, params)