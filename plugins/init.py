import os

from pymud import PyMudApp, Session

PLUGIN_NAME = "WebSocket客户端"
PLUGIN_DESC = {
    "VERSION": "1.0.0",
    "AUTHOR": "AI Assistant",
    "RELEASE_DATE": "2025-03-26",
    "DESCRIPTION": "连接到WebSocket服务器并处理消息"
}


class ConnectServer:
    def __init__(self, app: PyMudApp):
        self.app = app


# 插件入口函数
def PLUGIN_PYMUD_START(app: PyMudApp) -> None:
    """应用启动时调用的插件入口函数"""


def PLUGIN_SESSION_CREATE(session: Session) -> None:
    """应用启动时调用的插件入口函数"""
    pass


def PLUGIN_SESSION_DESTROY(session: Session) -> None:
    """会话销毁时调用的函数"""
    # 检测根目录pymud.log文件的大小，超过1M就删除
    log_file_path = os.path.join(os.path.dirname(__file__), "..", "pymud.log")
    log_file_path = os.path.abspath(log_file_path)
    
    try:
        if os.path.exists(log_file_path):
            file_size = os.path.getsize(log_file_path)
            # 1MB = 1024 * 1024 bytes
            if file_size > 1024 * 1024:
                os.remove(log_file_path)
                # print(f"日志文件大小超过1MB({file_size} bytes)，已删除: {log_file_path}")
            else:
                print(f"日志文件大小: {file_size} bytes，未超过限制")
        else:
            print(f"日志文件不存在: {log_file_path}")
    except Exception as e:
        print(f"检测或删除日志文件时出错: {e}")