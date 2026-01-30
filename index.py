import os

from pymud import IConfig, Session

from utils.sqlite import DatabaseManager
from utils.web_server import start_web_server


class MyConfig(IConfig):
    def __init__(self, session: Session, *args, **kwargs):

        # 是否调用 #reload 命令重新加载模块
        reload = kwargs.get("reload", False)

        self.session = session

        # 启动独立的Web服务器（与其他逻辑无关）
        # start_web_server()


        # 初始化数据库连接，使用自定义表名
        self.db = DatabaseManager()
        self.session.application.set_globals('db', self.db)
        if not self.db.connect():
            self.session.error("数据库连接失败！")
            self.session.application.del_globals('db')


        # 将 session.info 赋值给 session.debug、session.error 并添加背景色
        def _debug_with_bg(msg, *a, **kw):
            if isinstance(msg, str):
                # 黄色背景，红色前景
                bg_start = "\x1b[43m\x1b[31m"
                bg_end = "\x1b[0m"
                msg = f"{bg_start}{msg}{bg_end}"
            return self.session.info(msg, *a, **kw)
        self.session.debug = _debug_with_bg
        def _error_with_bg(msg, *a, **kw):
            if isinstance(msg, str):
                # 黄色背景，红色前景
                bg_start = "\x1b[43m\x1b[31m"
                bg_end = "\x1b[0m"
                msg = f"{bg_start}{msg}{bg_end}"
            return self.session.info(msg, *a, **kw)
        self.session.error = _error_with_bg

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
        # 停止Web服务器
        web_server = self.session.application.get_globals('web_server')
        if web_server:
            web_server.stop()
            self.session.application.del_globals('web_server')
        
        self.session.unload_module(self.mods)