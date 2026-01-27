import os

from pymud import IConfig, Session


class MyConfig(IConfig):
    def __init__(self, session: Session, *args, **kwargs):
        # 是否调用 #reload 命令重新加载模块
        reload = kwargs.get("reload", False)

        self.session = session

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
        self.session.info(self.session.getVariable("charname"))

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
