import os
import threading
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler


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
        self.server_thread = None
        self.is_running = False
        
    def start(self) -> bool:
        """
        启动web服务器
        
        Returns:
            启动是否成功
        """
        try:
            # 检查资源目录是否存在
            resource_path = os.path.join(os.path.dirname(__file__), "..", self.resource_dir)
            if not os.path.exists(resource_path):
                print(f"❌ 资源目录不存在: {resource_path}")
                return False
            
            # 切换到resource目录
            os.chdir(resource_path)
            
            # 创建简单的HTTP服务器
            self.server = HTTPServer(('localhost', self.port), SimpleHTTPRequestHandler)
            
            # 在后台线程中运行服务器
            def run_server():
                self.is_running = True
                try:
                    self.server.serve_forever()
                except Exception as e:
                    print(f"❌ Web服务器运行错误: {e}")
                finally:
                    self.is_running = False
            
            self.server_thread = threading.Thread(target=run_server, daemon=True)
            self.server_thread.start()
            
            # 等待服务器启动
            import time
            time.sleep(0.3)
            
            return True
            
        except Exception as e:
            print(f"❌ 启动Web服务器失败: {e}")
            return False
    
    def open_browser(self) -> bool:
        """
        打开浏览器连接到web服务器，直接加载index.html
        
        Returns:
            打开浏览器是否成功
        """
        try:
            # 直接打开resource目录下的index.html页面
            url = f"http://localhost:{self.port}/index.html"
            success = webbrowser.open(url)
            return success
        except Exception as e:
            print(f"❌ 打开浏览器失败: {e}")
            return False
    
    def stop(self) -> bool:
        """
        停止web服务器
        
        Returns:
            停止是否成功
        """
        try:
            if self.server:
                self.server.shutdown()
                self.server.server_close()
                self.is_running = False
                return True
            return False
        except Exception as e:
            print(f"❌ 停止Web服务器失败: {e}")
            return False
    
    def get_status(self) -> dict:
        """
        获取服务器状态
        
        Returns:
            服务器状态信息
        """
        return {
            "is_running": self.is_running,
            "port": self.port,
            "resource_dir": self.resource_dir,
            "url": f"http://localhost:{self.port}/index.html"
        }


def start_web_server(port=8000, open_browser=True) -> SimpleWebServer:
    """
    快速启动Web服务器的便捷函数
    
    Args:
        port: 服务器端口
        open_browser: 是否自动打开浏览器
        
    Returns:
        SimpleWebServer实例
    """
    web_server = SimpleWebServer(port=port)
    if web_server.start():
        if open_browser:
            # 延迟1秒后打开浏览器，确保服务器已启动
            import time
            time.sleep(1)
            web_server.open_browser()
        return web_server
    else:
        print("⚠️ Web服务器启动失败")
        return None


# 测试代码
if __name__ == "__main__":
    # 测试Web服务器
    server = start_web_server(port=8000, open_browser=True)
    
    if server:
        print("Web服务器测试成功！")
        print(f"服务器状态: {server.get_status()}")
        
        # 保持服务器运行一段时间
        import time
        time.sleep(5)
        
        # 停止服务器
        server.stop()
    else:
        print("Web服务器测试失败！")
