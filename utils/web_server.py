import os
import threading
import webbrowser
import urllib.parse
import socket
from http.server import HTTPServer, SimpleHTTPRequestHandler
import time
import shutil
from functools import partial

class SilentHTTPRequestHandler(SimpleHTTPRequestHandler):
    """静默的HTTP请求处理器，不输出任何日志"""
    
    def log_message(self, format, *args):
        """覆盖父类方法，不输出任何日志"""
        pass
    
    def log_request(self, code='-', size='-'):
        """覆盖父类方法，不输出请求日志"""
        pass
    
    def copyfile(self, source, outputfile):
        """重写copyfile方法以处理BrokenPipeError"""
        try:
            shutil.copyfileobj(source, outputfile)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            # 忽略客户端断开连接导致的错误
            pass
        except OSError as e:
            if hasattr(e, 'errno') and e.errno == 32:  # Broken pipe
                # 客户端提前断开连接，忽略此错误
                pass
            else:
                raise

class SimpleWebServer:
    """简单的独立Web服务器"""
    
    # 类变量，用于确保单例
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        """单例模式，确保只能创建一个实例"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                # 在 __new__ 中初始化所有实例变量
                cls._instance._is_initialized = False
                cls._instance._server_started = False
                cls._instance.port = 8000
                cls._instance.resource_dir = "resource"
                cls._instance.server = None
                cls._instance.is_running = False
                cls._instance.encoded_line = ""
                cls._instance.shutdown_event = threading.Event()
                cls._instance.server_thread = None
        return cls._instance
    
    def __init__(self, port=8000, resource_dir="resource"):
        """
        初始化Web服务器
        
        Args:
            port: 服务器端口，默认为8000
            resource_dir: 资源目录，默认为resource
        """
        # 防止重复初始化 - 使用线程安全的方式检查
        with self._lock:
            if self._is_initialized:
                return
            # 设置属性
            self.port = port
            self.resource_dir = resource_dir
            self.server = None
            self.is_running = False
            self.encoded_line = ""  # 存储编码后的line参数
            self.shutdown_event = threading.Event()
            self.server_thread = None
            self._is_initialized = True
            self._server_started = False
    
    def set_encoded_line(self, getfm): 
        """设置要编码的line参数"""
        if getfm:
            # 对line进行URL编码
            self.encoded_line = urllib.parse.quote(getfm, safe='')
        else:
            self.encoded_line = ""
        
    def start(self) -> bool:
        """
        启动web服务器（阻塞式运行，需要在外部线程中调用）
        
        Returns:
            启动是否成功
        """
        # 如果服务器已经在运行，直接返回成功
        if self.is_running:
            return True
            
        try:
            # 检查资源目录是否存在
            resource_path = os.path.join(os.path.dirname(__file__), "..", self.resource_dir)
            if not os.path.exists(resource_path):
                return False
            
            # 创建针对特定目录的请求处理器
            handler_class = partial(SilentHTTPRequestHandler, directory=resource_path)
            
            # 创建简单的HTTP服务器，使用静默请求处理器
            self.server = HTTPServer(('localhost', self.port), handler_class)
            
            # 设置SO_REUSEADDR选项，允许端口重用
            self.server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # 直接运行服务器（阻塞式）
            self.is_running = True
            try:
                # 设置服务器超时以便定期检查关闭事件
                self.server.timeout = 0.1  # 更短的超时时间
                
                while not self.shutdown_event.is_set():
                    self.server.handle_request()
                    
            except Exception as e:
                if not self.shutdown_event.is_set():
                    pass  # 忽略错误，不输出
            finally:
                self.is_running = False
                # 确保服务器资源被清理
                try:
                    self.server.shutdown()
                    self.server.server_close()
                except:
                    pass
                return True
            
        except Exception:
            return False
    
    def open_browser(self, getfm=None) -> bool:
        """
        打开浏览器连接到web服务器，添加getfm参数
        
        Args:
            getfm: 要编码的URL参数
            
        Returns:
            打开浏览器是否成功
        """
        try:
            # 如果有line参数，先进行编码
            if getfm:
                self.set_encoded_line(getfm)
            
            # 构建URL，添加getfm参数
            base_url = f"http://localhost:{self.port}/index.html"
            if self.encoded_line:
                url = f"{base_url}?getfm={self.encoded_line}"
            else:
                url = base_url
            
            success = webbrowser.open(url)
            return success
        except Exception:
            return False
    
    def stop(self) -> bool:
        """
        停止web服务器（手动调用时使用）
        
        Returns:
            停止是否成功
        """
        try:
            if self.server and self.is_running:
                # 设置关闭事件
                self.shutdown_event.set()
                
                # 创建一个临时连接来强制唤醒服务器
                try:
                    temp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    temp_socket.settimeout(1)  # 设置超时
                    temp_socket.connect(('localhost', self.port))
                    temp_socket.send(b'GET / HTTP/1.0\r\n\r\n')
                    temp_socket.close()
                except:
                    pass  # 忽略连接错误
                
                # 等待服务器关闭
                max_wait = 3  # 最多等待3秒
                wait_time = 0
                while self.is_running and wait_time < max_wait:
                    time.sleep(0.1)
                    wait_time += 0.1
                
                # 确保服务器资源被清理
                try:
                    self.server.shutdown()
                    self.server.server_close()
                except:
                    pass  # 忽略错误
                
                self.is_running = False
                return True
            return False
        except Exception:
            return False
    
    def get_status(self) -> dict:
        """
        获取服务器状态
        
        Returns:
            服务器状态信息
        """
        base_url = f"http://localhost:{self.port}/index.html"
        if self.encoded_line:
            full_url = f"{base_url}?getfm={self.encoded_line}"
        else:
            full_url = base_url
            
        return {
            "is_running": self.is_running,
            "port": self.port,
            "resource_dir": self.resource_dir,
            "encoded_line": self.encoded_line,
            "url": full_url
        }

def start_web_server(getfm="", port=8000, open_browser=True) -> SimpleWebServer:
    """
    在线程中启动Web服务器的便捷函数，服务器将保持运行直到手动停止
    
    Args:
        getfm: 要编码的URL参数
        port: 服务器端口
        open_browser: 是否自动打开浏览器
        
    Returns:
        SimpleWebServer实例
    """
    # 使用单例模式，确保只能创建一个实例
    web_server = SimpleWebServer(port=port)
    
    # 如果服务器已经在运行，直接返回现有实例并打开浏览器
    if web_server.is_running:
        if open_browser:
            web_server.open_browser(getfm)
        return web_server
    
    # 使用线程锁确保线程安全
    with SimpleWebServer._lock:
        # 如果服务器线程已启动但服务器还未运行，等待启动完成
        if web_server._server_started and not web_server.is_running:
            # 等待服务器启动（最多等待5秒）
            wait_count = 0
            while not web_server.is_running and wait_count < 50:
                time.sleep(0.1)
                wait_count += 1
            
            # 服务器启动成功后打开浏览器
            if web_server.is_running and open_browser:
                web_server.open_browser(getfm)
            return web_server
        
        # 设置编码后的line参数
        if getfm:
            web_server.set_encoded_line(getfm)
        
        # 标记服务器已启动
        web_server._server_started = True
    
    # 在线程中启动服务器
    def run_server():
        try:
            web_server.start()
        finally:
            # 服务器停止后重置标志
            with SimpleWebServer._lock:
                web_server._server_started = False
    
    # 使用守护线程，避免阻塞主程序
    server_thread = threading.Thread(target=run_server, daemon=True)
    web_server.server_thread = server_thread  # 保存线程引用
    server_thread.start()
    
    # 异步检查服务器启动状态，避免阻塞主线程
    def check_server_status():
        wait_count = 0
        while not web_server.is_running and wait_count < 50:  # 5秒内等待服务器启动
            time.sleep(0.1)
            wait_count += 1
        
        # 服务器启动成功后打开浏览器
        if web_server.is_running and open_browser:
            web_server.open_browser(getfm)
    
    # 在单独的守护线程中检查服务器状态
    status_thread = threading.Thread(target=check_server_status, daemon=True)
    status_thread.start()
    
    return web_server

# 新增函数：仅打开浏览器，不启动服务器
def open_web_browser(getfm="", port=8000) -> bool:
    """
    仅打开浏览器连接到web服务器，不启动服务器
    
    Args:
        getfm: 要编码的URL参数
        port: 服务器端口
        
    Returns:
        打开浏览器是否成功
    """
    web_server = SimpleWebServer(port=port)
    return web_server.open_browser(getfm)

# 测试代码
if __name__ == "__main__":
    # 测试1：第一次启动服务器并打开浏览器
    test_url = "https://example.com/fullme/image.jpg?token=abc123"
    server1 = start_web_server(
        getfm=test_url, 
        port=8000, 
        open_browser=True
    )
    
    print("第一次启动完成，等待3秒...")
    time.sleep(3)
    
    # 测试2：第二次调用，只打开浏览器，不启动新服务器
    server2 = start_web_server(
        getfm="https://example.com/fullme/image2.jpg?token=xyz789", 
        port=8000, 
        open_browser=True
    )
    
    print("第二次调用完成，服务器实例相同:", server1 is server2)
    
    # 测试3：仅打开浏览器
    success = open_web_browser(getfm="https://example.com/fullme/image3.jpg?token=123456")
    print("仅打开浏览器:", success)
    
    # 主程序继续运行
    print("Web服务器已启动，主程序继续运行...")
    while True:
        time.sleep(1)