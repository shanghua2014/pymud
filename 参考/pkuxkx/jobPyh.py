import asyncio, cn2an
from pymud import Trigger, IConfig
from .job import Job

class JobPiaoliu(Job, IConfig):
    "鄱阳湖漂流"

    JOB_ID   = "41"
    JOB_KEY  = ["pyh", "piaoliu"]
    JOB_NAME = "鄱阳湖寻宝"
    JOB_LOCATION = "江州鄱阳湖边"
    RESET_LOCATION = "江州鄱阳湖边"
    
    def __init__(self, session, *args, **kwargs):
        kwargs.setdefault("id", "job_pyh")
        super().__init__(session, *args, **kwargs)

        self._triggers = {
            "pyh_start"   : Trigger(self.session, r'^[> ]*钓鱼人在你的耳边悄声说道：船已经准备好了，你上船后须得如此如此，这般这般。', id = "pyh_start", group = "job_pyh"),
            "pyh_piaoliu" : Trigger(self.session, r'^[> ]*小船已经顺流漂出了(\S+)里开外了。', id = "pyh_piaoliu", group = "job_pyh"),
            "pyh_ting"    : Trigger(self.session, r'^[> ]*你手忙脚乱的把小船停了下来。', id = "pyh_ting", group = "job_pyh"),
            "pyh_hua"     : Trigger(self.session, r'^[> ]*小船被你向(\S+)划出了(\S+)里了。', id = "pyh_hua", group = "job_pyh"),
            "pyh_huafail" : Trigger(self.session, r'^[> ]*你还没杀光水贼呢，哪有空划桨？', id = "pyh_huafail", group = "job_pyh"),
            "pyh_dalao"   : Trigger(self.session, r'^[> ]*你把锚缓缓放下，立刻开始着手准备打捞\(dalao\)宝物。|^[> ]*你决定再接再厉，越挫越勇\(dalao\)。', id = "pyh_dalao", group = "job_pyh"),
            "pyh_done"    : Trigger(self.session, r'^[> ]*也许你可以返航了。可以使用hua\sback命令。', id = "pyh_done", group = "job_pyh"),
            "pyh_exitfb"  : Trigger(self.session, r'^[> ]*既然任务已经完成，可以离开副本.+', id = "pyh_exitfb", group = "job_pyh"),
            "pyh_exit"    : Trigger(self.session, r'^[> ]*你退出了鄱阳湖。', id = "pyh_exit", group = "job_pyh")
        }

    def __unload__(self):
        self.session.delObjects(self._triggers)

    def showInfo(self, key=None, *args):
        self.info(f'任务信息：{self.JOB_NAME} 任务')
        self.info(f'当前状态：{self.status}')
        self.info(f'漂流要求: {self.getParam("steps_piao")}')
        self.info(f'划船要求：{self.getParam("dir_hua")} {self.getParam("steps_hua")}')

    async def start(self, key=None, *args, **kwargs):
        await super().start(key, *args, **kwargs)
        # 1. 跑到地方
        self.status = "待接任务"
        state = await self.create_task(self.session.exec_async(f"rt {self.JOB_LOCATION}"))
        if state.result == self.SUCCESS:
            self.session.writeline("ask ren about 寻宝")
            await self.create_task(self._triggers["pyh_start"].triggered())
            self.status = "待人工输入要求"

    async def piaoliu(self):
        "漂流中"
        arrived = False

        self.session.writeline("shang boat")
        await asyncio.sleep(5)
        self.session.writeline("jie sheng")

        while not arrived:
            state, id, line, wildcards = await self.create_task(self._triggers["pyh_piaoliu"].triggered())
            self.status = f"已漂 {wildcards[0]} 里"
            if wildcards[0] == self.getParam("steps_piao_ch"):
                arrived = True
                self.session.writeline("ting")

        await asyncio.sleep(5)
        await self.create_task(self.notbusy())
        await self.create_task(self.hua())

    async def hua(self):
        "划船中"
        arrived = False
        dir = self.getParam("dir_hua")

        while not arrived:
            done, pending = await self.session.waitfor(f"hua {dir}", asyncio.wait([self.create_task(self._triggers[key].triggered()) for key in ("pyh_hua", "pyh_huafail")], return_when = "FIRST_COMPLETED"))
            
            for t in list(pending):
                self.remove_task(t)

            task_hua = list(done)[0]
            state, id, line, wildcards = task_hua.result()
            if id == "pyh_hua":
                self.status = f"漂{self.getParam('steps_piao_ch')}里后又向{dir}划了{wildcards[1]}里"
            
                await self.create_task(self.notbusy())

                if wildcards[1] == self.getParam("steps_hua_ch"):
                    arrived = True
                    self.session.writeline("xiamao")

            else:
                await self.create_task(self.notbusy())

        await self.create_task(self.dalao())
            
    async def dalao(self):
        finish = False
        self.status = "打捞中"

        while not finish:
            await self.create_task(self.notbusy())
            done, pending = await self.session.waitfor("dalao", asyncio.wait([self.create_task(self._triggers[key].triggered()) for key in ("pyh_dalao", "pyh_done")], return_when = "FIRST_COMPLETED"))
            tasks_done = list(done)

            for task in list(pending):
                self.remove_task(task, "其他任务已完成。")

            if  len(tasks_done) == 1:
                task = tasks_done[0]
                state, id, line, wildcards = task.result()
                if id == "pyh_done":
                    finish = True

        await self.create_task(self.notbusy())
        
        await self.finish()
        
    async def other(self, key, param, *args, **kwargs):
        if " "in param:
            params = param.split()
            self.setParam("steps_piao", params[0])
            self.setParam("dir_hua", params[1])
            self.setParam("steps_hua", params[2])
            self.setParam("steps_piao_ch", cn2an.an2cn(params[0]))
            self.setParam("steps_hua_ch", cn2an.an2cn(params[2]))

            await self.create_task(self.piaoliu())

    async def finish(self, success = True, *args, **kwargs):
        if success:
            self.status = "成功返回中"
        else:
            self.status = "失败返回中"
        
        self.session.writeline("hua back")
        await self.create_task(self._triggers["pyh_exitfb"].triggered())
        await self.create_task(self.notbusy())
        self.session.writeline(f"leave {self.session.vars.id}")

        await asyncio.sleep(5)
        await self.create_task(self.notbusy())
        self.session.writeline("give ren xiang")
        await asyncio.sleep(3)
        self.session.writeline("pack gem")

        self.status = "初始化"
        await asyncio.sleep(1)
        await self.create_task(self.session.exec_async('liaoshang'))

        self.jobevent.set()
        self.info('任务事件已设置，可以继续了')

        await super().finish(success, *args, **kwargs)