import os
import threading
import webbrowser
import urllib.parse
from http.server import HTTPServer, SimpleHTTPRequestHandler
import time
import signal
import sys
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
    
    def __init__(self, port=8000, resource_dir="resource"):
        """
        初始化Web服务器
        
        Args:
            port: 服务器端口，默认为8000
            resource_dir: 资源目录，默认为resource
        """
        self.port = port
        self.resource_dir = resource_dir
        self.server = None
        self.is_running = False
        self.encoded_line = ""  # 存储编码后的line参数
        self.shutdown_event = threading.Event()
        
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
        try:
            # 检查资源目录是否存在
            resource_path = os.path.join(os.path.dirname(__file__), "..", self.resource_dir)
            if not os.path.exists(resource_path):
                return False
            
            # 创建针对特定目录的请求处理器
            handler_class = partial(SilentHTTPRequestHandler, directory=resource_path)
            
            # 创建简单的HTTP服务器，使用静默请求处理器
            self.server = HTTPServer(('localhost', self.port), handler_class)
            
            # 直接运行服务器（阻塞式）
            self.is_running = True
            try:
                # 设置服务器超时以便定期检查关闭事件
                self.server.timeout = 0.5
                
                while not self.shutdown_event.is_set():
                    self.server.handle_request()
                    
            except Exception as e:
                if not self.shutdown_event.is_set():
                    pass  # 忽略错误，不输出
            finally:
                self.is_running = False
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
        停止web服务器
        
        Returns:
            停止是否成功
        """
        try:
            if self.server:
                # 设置关闭事件
                self.shutdown_event.set()
                
                # 等待服务器关闭
                max_wait = 5  # 最多等待5秒
                wait_time = 0
                while self.is_running and wait_time < max_wait:
                    time.sleep(0.1)
                    wait_time += 0.1
                
                # 确保服务器资源被清理
                self.server.shutdown()
                self.server.server_close()
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

def start_web_server_in_thread(getfm="", port=8000, open_browser=True, auto_shutdown_seconds=30) -> SimpleWebServer:
    """
    在线程中启动Web服务器的便捷函数，支持自动关闭
    
    Args:
        getfm: 要编码的URL参数
        port: 服务器端口
        open_browser: 是否自动打开浏览器
        auto_shutdown_seconds: 自动关闭秒数，默认30秒
        
    Returns:
        SimpleWebServer实例
    """
    web_server = SimpleWebServer(port=port)
    
    # 设置编码后的line参数
    if getfm:
        web_server.set_encoded_line(getfm)
    
    # 在线程中启动服务器
    def run_server():
        web_server.start()
    
    # 使用非守护线程，确保资源能被正确清理
    server_thread = threading.Thread(target=run_server, daemon=False)
    web_server.server_thread = server_thread  # 保存线程引用
    server_thread.start()
    
    # 等待服务器启动
    time.sleep(1)
    
    if open_browser:
        web_server.open_browser(getfm)
    
    # 如果设置了自动关闭时间，则启动定时关闭
    if auto_shutdown_seconds > 0:
        def auto_shutdown():
            time.sleep(auto_shutdown_seconds)
            web_server.stop()
            
            # 等待线程结束（最多等待2秒）
            if server_thread.is_alive():
                server_thread.join(timeout=2)
        
        # 启动自动关闭线程
        shutdown_thread = threading.Thread(target=auto_shutdown, daemon=True)
        shutdown_thread.start()
    
    return web_server

# 测试代码
if __name__ == "__main__":
    # 测试带参数的Web服务器，30秒后自动关闭
    test_url = "https://example.com/fullme/image.jpg?token=abc123"
    server = start_web_server_in_thread(
        getfm=test_url, 
        port=8000, 
        open_browser=True, 
        auto_shutdown_seconds=30
    )
    
    if server:
        # 保持主程序运行直到服务器停止
        while server.is_running:
            time.sleep(1)
    else:
        pass