import traceback
from pymud import Command, Trigger, IConfig
from pymud.extras import DotDict

class CmdSkills(Command, IConfig):
    "执行PKUXKX中的skills/cha命令"

    def __init__(self, session, *args, **kwargs):
        kwargs.setdefault("id", "cmd_skills")
        super().__init__(session, "^(skills|cha)$", *args, **kwargs)
        
        if self.session.getVariable("skills") == None:
            self.session.vars.skills = DotDict()

        self._tris = {
            "start" : Trigger(session, patterns = r'^┌[─]+技能列表\(共.+项\)[─┬]+┐$', onSuccess = self.start, group = "skills"),
            "stop"  : Trigger(session, patterns = r'^└[─┴]+[^└─┴┘]+[─]+┘$', onSuccess = self.stop, group = "skills", keepEval = True, enabled = False),
            "item"  : Trigger(session, patterns = r'^│(?:□|\s*)?(\S+)\s+│(\S+)\s+│\S+\s+│(\d+.\d+)\s+│(\d+|-)\s+│$', onSuccess = self.skill, group = "skills", enabled = False)
        }

    def __unload__(self):
        self.session.delObjects(self._tris)
        self.session.delVariable("skills")

    def reset(self):
        self._tris["start"].enabled = True
        self._tris["stop"].enabled = False
        self._tris["item"].enabled = False

    def start(self, name, line, wildcards):
        self._tris["start"].enabled = False
        self._tris["stop"].enabled = True
        self._tris["item"].enabled = True

    def stop(self, name, line, wildcards):
        self.reset()

    def skill(self, name, line, wildcards):
        #if not en_name == "ID":         # 不要捕获标题行
        ch_name = wildcards[0]
        en_name = wildcards[1]
        level   = float(wildcards[2])
        max_lvl = wildcards[3]
        if max_lvl == "-": max_lvl = 100000
        else: max_lvl = float(max_lvl)
        #self.info(f'捕获技能： {ch_name} ({en_name}), 当前级别为 {level}, 目前经验最大级别为 {max_lvl}')
        # 将技能等级保存为变量
        self.session.vars.skills[en_name] = (level, max_lvl, ch_name)

    async def execute(self, cmd = "skills", *args, **kwargs):
        try:
            self.reset()
            result, id, line, wildcards = await self.session.waitfor(cmd, self.create_task(self._tris["stop"].triggered()))
            self.reset()

            return result
        
        except Exception as e:
            self.error(f"异步执行中遇到异常, {e}, 类型为 {type(e)}")
            self.error(f"异常追踪为： {traceback.format_exc()}")