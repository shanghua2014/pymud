import json
from utils.websocket import connect_to_ws
from pymud import PyMudApp, Session
import threading
import time

# 导入新的UI文件
from external_ui import load_external_ui

PLUGIN_NAME = "websocket服务"

PLUGIN_DESC = {
    "VERSION": "1.0.0",
    "AUTHOR": "MrZhao",
    "RELEASE_DATE": "2025-03-26",
    "DESCRIPTION": "通过socket为客户端提供消息服务"
}

WEBSOCKET_URI = "ws://127.0.0.1:5556"


class WSServer:
    def __init__(self, app) -> None:
        self.app = app
        self.session = None
        self.ws = None
        self.running = False
        self.app.set_status(f"插件 {PLUGIN_NAME} 已加载!")
        # 初始化UI相关变量
        self.ui_thread = None
        self.main_window = None
        self.ui = None

    def start_connection(self, session):
        self.session = session
        self.running = True
        # 启动连接线程
        self.conn_thread = threading.Thread(target=self._connection_loop)
        self.conn_thread.daemon = True
        self.conn_thread.start()

    def _connection_loop(self):
        self.session.info("开始连接WebSocket")
        while self.running:
            try:
                self.ws = connect_to_ws()

                # 心跳线程
                heartbeat_thread = threading.Thread(target=self._heartbeat)
                heartbeat_thread.daemon = True
                heartbeat_thread.start()

                # 消息接收循环
                while self.running:
                    try:
                        response = self.ws.recv()
                        if type(response).__name__ == "str":
                            response = json.loads(response)
                            if response['type'] == 'web':
                                self.session.exec(response['cmd'])
                                self.app.set_status(f"消息: {response['cmd']}")
                    except Exception as e:
                        self.app.set_status(f"接收错误: {e}")
                        break

            except Exception as e:
                self.app.set_status(f"连接失败: {e}")
                time.sleep(5)  # 重连间隔
            finally:
                if self.ws:
                    self.ws.close()

    def _heartbeat(self):
        while self.running and self.ws:
            try:
                time.sleep(30)  # 每30秒发送心跳
                self.ws.ping()
            except Exception as e:
                self.app.set_status(f"心跳发送失败: {e}")
                break

    def close(self):
        self.running = False
        if self.ws:
            self.ws.close()


# 插件入口函数
def PLUGIN_PYMUD_START(app: PyMudApp) -> None:
    """应用启动时调用的插件入口函数"""
    # 创建WSServer实例
    ws_server = WSServer(app)
    app.set_globals("ws", ws_server)




def PLUGIN_SESSION_CREATE(session: Session) -> None:
    """会话创建时调用的函数"""
    ws_server = session.application.get_globals("ws")
    ws_server.start_connection(session)
    # 开启新线程加载UI
    ui_thread = threading.Thread(target=load_external_ui, daemon=True, name="PyMUD_WebSocket_UI_Thread")
    ui_thread.start()


def PLUGIN_SESSION_DESTROY(session: Session) -> None:
    """会话销毁时调用的函数"""
    pass