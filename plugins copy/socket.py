import asyncio
import websockets
import json
import threading
from pymud import PyMudApp, Session

PLUGIN_NAME = "WebSocket服务器"

PLUGIN_DESC = {
    "VERSION": "1.0.0",
    "AUTHOR": "AI Assistant",
    "RELEASE_DATE": "2025-03-26",
    "DESCRIPTION": "提供WebSocket服务器功能"
}

# WebSocket服务器配置
WS_HOST = "127.0.0.1"
WS_PORT = 5556


class WebSocketServer:
    def __init__(self, app):
        self.app = app
        self.server = None
        self.clients = set()
        self.running = False
        # print(f"插件 {PLUGIN_NAME} 已加载!")

    async def handle_client(self, websocket):
        """处理客户端连接"""
        # 添加客户端到集合
        self.clients.add(websocket)
        try:
            # print(f"WebSocket客户端已连接: {websocket.remote_address}")
            # 处理客户端消息
            async for message in websocket:
                await self.process_message(websocket, message)
        except Exception as e:
            print(f"WebSocket客户端连接出错: {e}")
        finally:
            # 从集合中移除客户端
            self.clients.remove(websocket)
            print(f"WebSocket客户端已断开: {websocket.remote_address}")

    async def process_message(self, websocket, message):
        """处理收到的消息"""
        try:
            # 解析JSON消息
            data = json.loads(message)
            # print(f"收到WebSocket消息: {data}")

            # 根据消息类型处理
            if data.get('type') == 'command':
                # 执行命令
                cmd = data.get('command', '')
                if cmd:
                    # 这里可以根据需要执行命令，例如发送到当前会话
                    if self.app.current_session:
                        self.app.current_session.exec(cmd)

                # 回复客户端
                await websocket.send(json.dumps({
                    'type': 'response',
                    'status': 'success',
                    'message': f'命令已执行: {cmd}'
                }))
            elif data.get('type') == 'status':
                await websocket.send(json.dumps({
                    'type': 'status',
                    'status': data['status'],
                }))
            else:
                # 未知消息类型
                await websocket.send(json.dumps({
                    'type': 'error',
                    'message': '未知消息类型'
                }))
        except json.JSONDecodeError:
            # 不是JSON格式的消息
            await websocket.send(json.dumps({
                'type': 'error',
                'message': '消息格式错误'
            }))
        except Exception as e:
            print(f"处理WebSocket消息出错: {e}")
            await websocket.send(json.dumps({
                'type': 'error',
                'message': f'处理消息出错: {str(e)}'
            }))

    async def start_server(self):
        """启动WebSocket服务器"""
        try:
            self.running = True
            # 创建并启动服务器
            self.server = await websockets.serve(
                self.handle_client,
                WS_HOST,
                WS_PORT
            )
            # print(f"WebSocket服务器已启动，监听 {WS_HOST}:{WS_PORT}")
            # 保持服务器运行
            await self.server.wait_closed()
        except Exception as e:
            print(f"启动WebSocket服务器出错: {e}")
            self.running = False

    async def stop_server(self):
        """停止WebSocket服务器"""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        self.running = False
        self.clients.clear()
        print("WebSocket服务器已停止")

    def broadcast(self, message):
        """向所有客户端广播消息"""
        if not self.running:
            return

        async def broadcast_async():
            disconnected_clients = []
            for client in self.clients:
                try:
                    await client.send(message)
                except Exception:
                    disconnected_clients.append(client)

            # 移除断开连接的客户端
            for client in disconnected_clients:
                self.clients.remove(client)

        # 在事件循环中运行
        asyncio.run_coroutine_threadsafe(broadcast_async(), self.event_loop)

    def run_event_loop(self):
        """在新线程中运行事件循环"""
        self.event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.event_loop)
        self.event_loop.run_until_complete(self.start_server())


# 全局服务器实例
ws_server = None


# 插件入口函数
def PLUGIN_PYMUD_START(app: PyMudApp) -> None:
    """应用启动时调用的插件入口函数"""
    global ws_server
    # 创建WebSocket服务器实例
    ws_server = WebSocketServer(app)
    app.set_globals("ws", ws_server)

    # 在新线程中启动服务器
    server_thread = threading.Thread(target=ws_server.run_event_loop, daemon=True, name="WebSocket_Server_Thread")
    server_thread.start()


def PLUGIN_SESSION_CREATE(session: Session) -> None:
    """会话创建时调用的函数"""
    pass


def PLUGIN_SESSION_DESTROY(session: Session) -> None:
    """会话销毁时调用的函数"""
    pass