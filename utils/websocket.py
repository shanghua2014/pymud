import websockets.sync.client

# 全局变量，用于存储 WebSocket 连接实例
_ws_instance = None

def connect_to_ws():
    global _ws_instance
    WEBSOCKET_URI = "ws://127.0.0.1:5556"
    # if _ws_instance is None:
    try:
        # 同步连接 WebSocket 服务器
        _ws_instance = websockets.sync.client.connect(WEBSOCKET_URI)
    except Exception as e:
        print(f"连接 WebSocket 服务时出错: {e}")
    return _ws_instance


