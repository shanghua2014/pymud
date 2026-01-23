import os

from pymud import IConfig, Session


class MyConfig(IConfig):
    def __init__(self, session: Session, *args, **kwargs):
        # 是否调用 #reload 命令重新加载模块
        reload = kwargs.get("reload", False)

        self.session = session
        self.session.info(session)
        self.session.info(self.session.getVariable("charname"))

        mods = list()

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
