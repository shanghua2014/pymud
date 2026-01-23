import asyncio, re, traceback

from pymud import Session, Command, DotDict

from ..commands.cmdLifeMisc import MONEY_REMAIN

class Job(Command):
    "PKUXKX任务的定制类"

    _help = """
        统一任务的标准操作，假定任务起始为task，则：
        task start: 开始任务
        task done:  任务成功完成
        task fail:  任务失败完成
        task continue: 从中断处继续任务
        task: 显示task有关信息

        统一提供共通接口，比如 notbusy
    """

    JOB_ID   = "UNDEFINED"
    JOB_KEY  = "UNDEFINED"
    JOB_NAME = "UNDEFINED"
    JOB_LOCATION = "UNDEFINED"
    RESET_LOCATION = "UNDEFINED"

    def __init__(self, session: Session, *args, **kwargs):
        if isinstance(self.JOB_KEY, list):
            cmd = "|".join(self.JOB_KEY)
        else:
            cmd = self.JOB_KEY

        patterns = r"^({0})(?:\s+(.+))?$".format(cmd)
        super().__init__(session, patterns, *args, **kwargs)

        var_job_id = f"job_{self.JOB_ID}"
        if not self.session.getVariable(var_job_id):
            self.session.setVariable(var_job_id, DotDict())

        self._jobinfo = self.session.vars[var_job_id]
        self.jobevent = asyncio.Event()
        self.done_callback = None

        self.setParam("JOBNAME", self.JOB_NAME)

        from .jobManager import JobManager
        jobmanager = self.session.cmds["jobmanager"]
        if isinstance(jobmanager, JobManager) and not isinstance(self, JobManager):
            jobmanager.registerJob(self)

    def clear(self):
        "清空所有上一次任务有关信息，恢复到初始状态。子类应继承并覆盖本方法"
        pass

    @property
    def status(self):
        "任务状态"
        return self.getParam("status", "初始化")
    
    @status.setter
    def status(self, value):
        if value != self.getParam("status"):
            self.setParam("status", value)
            hooked = self.session.getGlobal("hooked")
            if hooked:
                msg = f"{self.session.vars.name}({self.session.vars.id}): {self.JOB_NAME} 状态变更为 {value} ."
                hook = self.session.getGlobal("hook")
                hook.sendMessage(msg)

    @property
    def always(self):
        "一直做任务状态"
        return self.getParam("always", False)
    
    @always.setter
    def always(self, val: bool):
        "一直做任务状态"
        self.setParam("always", val)

    def info(self, inf, title = None):
        "覆盖session.info，默认加上jobName属性作为标题"
        self.session.info(inf, title or self.JOB_NAME)

    def warning(self, inf, title = None):
        "覆盖session.warning，默认加上jobName属性作为标题"
        self.session.warning(inf, title or self.JOB_NAME)

    def error(self, inf, title = None):
        "覆盖session.error，默认加上jobName属性作为标题"
        self.session.error(inf, title or self.JOB_NAME)

    def showInfo(self, key = None, *args):
        "显示任务相关信息"
        self.info(f"{self._jobinfo}")

    def setParam(self, param, value):
        "设置任务专有参数"
        self._jobinfo[param] = value

    def getParam(self, param, default = None):
        "获取任务专有参数"
        return self._jobinfo.get(param, default)

    def reset(self):
        "复位任务执行"
        super().reset()

    async def start(self, key = None, *args, **kwargs):
        "开始执行任务"
        self.clear()
        self.done_callback = kwargs.get("done_callback", None)
        
    async def finish(self, success = True, *args, **kwargs):
        "完成执行任务"
        if asyncio.iscoroutine(self.done_callback) or asyncio.iscoroutinefunction(self.done_callback):
            await self.create_task(self.done_callback())
        elif callable(self.done_callback):
            self.done_callback()

    async def resume(self, *args, **kwargs):
        "从中断处重新开始"
        pass

    async def other(self, key, param, *args, **kwargs):
        "其他未处理命令"
        pass

    async def after_done(self, *args, **kwargs):
        # 疗伤放在每个任务完成之后
        # await self.session.exec_async("liaoshang")
        await self.session.exec_async('feed')
        sells = self.session.getVariable("sells")
        if isinstance(sells, list) and len(sells) > 0:
            await self.session.exec_async('rt pawnshop;sellall')

        cash = self.session.getVariable("cash", 0)
        if cash > MONEY_REMAIN * 100:
            await self.session.exec_async('rt bank;convertall;savegold')
            await asyncio.sleep(1)

        await self.session.exec_async(f'rt {self.RESET_LOCATION}')
        await self.session.exec_async('dzt')
        self.session.writeline("exert recover")
        # 自动hp 仅在 always 状态下，此处执行
        self.session.exec("hp")
        self.info("后处理恢复结束，可以继续了")

    async def notbusy(self):
        await asyncio.sleep(0.5)

        while True:
            await asyncio.sleep(0.5)
            isfighting = self.session.getVariable("is_fighting", "1")
            isbusy = self.session.getVariable("is_busy", 1)
            
            if (isfighting == False) and (isbusy == False):
                break

        await asyncio.sleep(0.2)

    async def execute(self, cmd, *args, **kwargs):
        try:    
            m = re.match(self.patterns, cmd)
            
            if m:
                key   = m[1]
                param = m[2]

                if param is None:
                    self.showInfo(key)

                elif param == "help":
                    self.info(self._help)

                elif param == "always":
                    self.always = not self.always
                    if self.always:
                        self.info("已打开一直做任务选项。")
                    else:
                        self.info("已关闭一直做任务选项。")

                elif param == "start":
                    self.event.clear()
                    await self.create_task(self.start(key = key, *args, **kwargs))

                elif param == "continue":
                    await self.create_task(self.resume(key = key, *args, **kwargs))

                elif param == "done":
                    await self.create_task(self.finish(success = True, key = key, *args, **kwargs))
                    self.event.set()
                
                elif param == "fail":
                    await self.create_task(self.finish(success = False, key = key, *args, **kwargs))
                    self.event.set()

                elif param == "reset":
                    self.info("任务被手动重置！")
                    self.reset()
                    self.event.set()

                else:
                    await self.create_task(self.other(key, param, *args, **kwargs))

        except Exception as e:
            self.error(f"异步执行中遇到异常, {e}, 类型为 {type(e)}")
            self.error(f"异常追踪为： {traceback.format_exc()}")