import threading
import multiprocessing
import pyautogui
import atexit
import json

from pymud import PyMudApp, Session
from external_ui import run_external_ui_process
from utils.websocket import connect_to_ws

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
        self.ws = None
        self.running = False
        self.heartbeat_thread = None
        self.ui_instance = None  # 存储UI实例引用
        self.ui_queue = None  # 跨进程队列
        # print(f"插件 {PLUGIN_NAME} 已加载!")

    def set_ui_instance(self, ui_instance):
        """设置UI实例引用，用于数据传递"""
        self.ui_instance = ui_instance

    def set_ui_queue(self, queue):
        """设置跨进程队列，用于把状态推送给独立UI进程"""
        self.ui_queue = queue

    def start_connection(self):
        """启动WebSocket连接"""
        try:
            # 使用工具类建立连接
            self.ws = connect_to_ws()
            if self.ws:
                self.running = True
                # print("已连接到WebSocket服务器 127.0.0.1:5556")
                # 启动消息接收线程
                receive_thread = threading.Thread(target=self.receive_messages, daemon=True,
                                                  name="WebSocket_Receive_Thread")
                receive_thread.start()
                # 启动心跳线程
                # self.heartbeat_thread = threading.Thread(target=self.send_heartbeat, daemon=True, name="WebSocket_Heartbeat_Thread")
                # self.heartbeat_thread.start()
            else:
                print("无法连接到WebSocket服务器 127.0.0.1:5556")
        except Exception as e:
            print(f"连接WebSocket服务器出错: {e}")

    def receive_messages(self):
        """接收并处理WebSocket消息"""
        while self.running and self.ws:
            try:
                message = self.ws.recv()
                if message:
                    # print(f"收到WebSocket消息: {message}")
                    # 尝试解析JSON消息
                    try:
                        data = json.loads(message)
                        self.process_message(data)
                    except json.JSONDecodeError:
                        # 不是JSON格式，直接处理
                        print(f"收到非JSON消息: {message}")
            except Exception as e:
                print(f"connect.py接收WebSocket消息出错: {e}")
                self.running = False

    def process_message(self, data):
        """处理解析后的JSON消息"""
        if data.get('type') == 'status':
            # 人物状态数据传递给UI界面
            self.update_ui_with_data(data)

    def update_ui_with_data(self, data):
        """将WebSocket数据更新到UI界面"""
        '''
            收到GMCP子协商数据: GMCP.Status = {"max_qi":604,"qi":604,"name":"邓泽","jingli":1006,"food":0,"eff_jing":435,"id":"shanghua","jing":435,"title":"[1;37m武当派[2;37;0m[32m道长[2;37;0m","family/family_name":"武当派","combat_exp":57104,"vigour/qi":0,"max_jing":435,"level":0,"vigour/yuan":0,"max_jingli":1006,"neili":1090,"water":0,"eff_qi":604,"max_neili":1090}
        '''
        status = data.get('status', {})
        # 优先使用跨进程队列，把数据交给独立的 UI 进程；否则退回到同进程 UI。
        if self.ui_queue:
            try:
                self.ui_queue.put(status, block=False)
            except Exception as e:
                print(f"推送UI队列出错: {e}")
        elif self.ui_instance:
            try:
                # 通过 Qt 信号发到 GUI 线程，避免跨线程直接操作控件
                self.ui_instance.post_status(status)
            except Exception as e:
                print(f"更新UI数据出错: {e}")

    def send_message(self, message):
        """发送消息到WebSocket服务器"""
        if not self.running or not self.ws:
            return

        try:
            self.ws.send(message)
            # print(f"已发送WebSocket消息: {message}")
        except Exception as e:
            print(f"发送WebSocket消息出错: {e}")

    def stop_connection(self):
        """停止WebSocket连接"""
        self.running = False
        if self.ws:
            try:
                self.ws.close()
                print("已断开与WebSocket服务器的连接")
            except Exception as e:
                print(f"关闭WebSocket连接出错: {e}")
        self.ws = None


# 全局客户端实例
ws_client = None
ui_process = None
ui_queue = None


# 插件入口函数
def PLUGIN_PYMUD_START(app: PyMudApp) -> None:
    """应用启动时调用的插件入口函数"""
    global ws_client
    # 创建WebSocket客户端实例
    ws_client = ConnectServer(app)
    app.set_globals("ws_client", ws_client)


def PLUGIN_SESSION_CREATE(session: Session) -> None:
    """会话创建时调用的函数"""
    global ws_client, ui_process, ui_queue
    if ws_client:
        # 启动WebSocket连接
        ws_client.start_connection()

    # 独立进程运行 Qt，避免"QApplication 不在主线程"的警告，同时不阻塞 PyMUD 主线程。
    if ui_process is None or (ui_process and not ui_process.is_alive()):
        ui_queue = multiprocessing.Queue()
        ui_process = multiprocessing.Process(
            target=run_external_ui_process,
            args=(ui_queue,),
            name="ExternalUIProcess",
            daemon=True,
        )
        ui_process.start()
        if ws_client:
            ws_client.set_ui_queue(ui_queue)

    # 自动执行快捷键 ctrl+l，修正UI错位
    try:
        # 使用pyautogui模拟键盘操作：按下Ctrl+L
        pyautogui.keyDown('ctrl')  # 按下Ctrl键
        pyautogui.press('l')  # 按下L键
        pyautogui.keyUp('ctrl')  # 释放Ctrl键
        print("已自动执行快捷键 Ctrl+L (使用键盘模拟)")
    except Exception as e:
        print(f"执行快捷键 Ctrl+L 时出错: {e}")

    # 确保进程退出时清理
    def _cleanup_ui_process():
        global ui_process, ui_queue
        try:
            if ui_queue:
                ui_queue.put({"__exit__": True}, block=False)
        except Exception:
            pass
        if ui_process and ui_process.is_alive():
            ui_process.terminate()
        ui_process = None
        ui_queue = None

    atexit.register(_cleanup_ui_process)


def PLUGIN_SESSION_DESTROY(session: Session) -> None:
    """会话销毁时调用的函数"""
    global ws_client, ui_process, ui_queue
    if ws_client:
        # 停止WebSocket连接
        ws_client.stop_connection()
    try:
        if ui_queue:
            ui_queue.put({"__exit__": True}, block=False)
    except Exception:
        pass
    if ui_process and ui_process.is_alive():
        ui_process.terminate()
    ui_process = None
    ui_queue = None
