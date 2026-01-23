import os, pathlib
from pymud import IConfig, Session

class MyConfig(IConfig):
    def __init__(self, session: Session, *args, **kwargs):
        reload = kwargs.get("reload", False)
        
        self.session = session
        mods = list()

        mods.append("script.common")
        mods.append("script.map.map")

        cur_dir = os.path.dirname(__file__)
        self.session.info(cur_dir)
        root_dir = os.path.join(cur_dir, "script")
        
        dir = os.path.join(root_dir, "commands")
        if os.path.exists(dir):
            for file in os.listdir(dir):
                if file.endswith(".py") and (not file.startswith("__")):
                    mods.append(f"script.commands.{file[:-3]}")

        mods.append(f"script.jobs.job")
        mods.append(f"script.jobs.jobManager")
        dir = os.path.join(root_dir, "jobs")
        if os.path.exists(dir):
            for file in os.listdir(dir):
                if file.endswith(".py") and (not file.startswith("__")) and (file != "jobManager.py") and (file != "job.py"):
                    mods.append(f"script.jobs.{file[:-3]}")

        mods.append("script.main")
        session.load_module(mods)

        if reload:
            session.reload_module(mods)
            
        self.mods = mods

    def __unload__(self):
        self.session.unload_module(self.mods)
                

