import os
import threading
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler

from pymud import IConfig, Session

from utils.sqlite import DatabaseManager


class SimpleWebServer:
    """简单的独立Web服务器"""
    def __init__(self, port=8000):
        self.port = port
        self.server = None
        self.server_thread = None
        
    def start(self):
        """启动web服务器"""
        try:
            # 切换到resource目录
            resource_path = os.path.join(os.path.dirname(__file__), "resource")
            os.chdir(resource_path)
            
            # 创建简单的HTTP服务器
            self.server = HTTPServer(('localhost', self.port), SimpleHTTPRequestHandler)
            
            # 在后台线程中运行服务器
            def run_server():
                self.server.serve_forever()
            
            self.server_thread = threading.Thread(target=run_server, daemon=True)
            self.server_thread.start()
            
            return True
            
        except Exception as e:
            print(f"❌ 启动Web服务器失败: {e}")
            return False
    
    def open_browser(self):
        """打开浏览器连接到web服务器，直接加载index.html"""
        try:
            # 直接打开resource目录下的index.html页面
            url = f"http://localhost:{self.port}/index.html"
            webbrowser.open(url)
            return True
        except Exception as e:
            print(f"❌ 打开浏览器失败: {e}")
            return False


class MyConfig(IConfig):
    def __init__(self, session: Session, *args, **kwargs):

        # 是否调用 #reload 命令重新加载模块
        reload = kwargs.get("reload", False)

        self.session = session

        # 启动独立的Web服务器（与其他逻辑无关）
        web_server = SimpleWebServer(port=8000)
        if web_server.start():
            # 延迟1秒后打开浏览器，确保服务器已启动
            import time
            time.sleep(1)
            web_server.open_browser()
        else:
            print("⚠️ Web服务器启动失败，但程序继续运行")


        # 初始化数据库连接，使用自定义表名
        self.db = DatabaseManager()
        self.session.application.set_globals('db', self.db)
        if not self.db.connect():
            self.session.error("数据库连接失败！")
            self.session.application.del_globals('db')


        # 将 session.info 赋值给 session.debug 并添加背景色
        def _debug_with_bg(msg, *a, **kw):
            try:
                if isinstance(msg, str):
                    # 黄色背景，红色前景
                    bg_start = "\x1b[43m\x1b[31m"
                    bg_end = "\x1b[0m"
                    msg = f"{bg_start}{msg}{bg_end}"
            except Exception:
                pass
            return self.session.info(msg, *a, **kw)
        self.session.debug = _debug_with_bg

        self.session.info(session)

        mods = list()

        ''' 加载脚本 cmds '''
        cur_dir = os.path.dirname(__file__)
        dir = os.path.join(cur_dir, "cmds")
        if os.path.exists(dir):
            for file in os.listdir(dir):
                if file.endswith(".py") and (not file.startswith("__")):
                    mods.append(f"cmds.{file[:-3]}")

        ''' 加载脚本 script '''
        cur_dir = os.path.dirname(__file__)
        dir = os.path.join(cur_dir, "script")
        if os.path.exists(dir):
            for file in os.listdir(dir):
                if file.endswith(".py") and (not file.startswith("__")):
                    mods.append(f"script.{file[:-3]}")
                    

        session.load_module(mods)

        if reload:
            session.reload_module(mods)

        self.mods = mods

    def __unload__(self):
        self.session.unload_module(self.mods)