import asyncio, re, traceback, functools

from pymud import Session, Command, IConfig
from .job import Job

from ..commands.cmdJobquery import JobInfo

class JobManager(Job, IConfig):
    "PKUXKX的任务管理类，可以将归一化任务类加入后，统一调度执行"

    _help = """
        统一任务的标准操作，假定任务起始为task，则：
        task start: 开始任务
        task done:  任务成功完成
        task fail:  任务失败完成
        task continue: 从中断处继续任务
        task: 显示task有关信息

    """

    JOB_ID   = "00"
    JOB_KEY  = "job"
    JOB_NAME = "任务管理器"

    def __init__(self, session: Session, *args, **kwargs):
        kwargs.setdefault("id", "jobmanager")
        super().__init__(session, *args, **kwargs)

        self.session.info("start to init jobmanager")
        self.all_jobs = {}          # 所有注册任务字典，key = id
        self._job_keys = {}         # 所有注册任务关键字字典，支持key与id作为关键字
        self._patterns_keys = list()
        self._patterns_keys.append(self.JOB_KEY)
        if not self.session.getVariable("jobs"):
            self.session.setVariable("jobs", [])
        self.jobs = self.session.vars["jobs"]             # 保存加入管理的任务清单(id列表)，

    def showInfo(self, key = None, *args):
        if key == "job":
            self.info("任务管理器状态:")
            self.info(f'持续任务：{"开启" if self.always else "关闭"}')
            self.info("管理任务：{}".format(self.managedJobs))     # self.all_jobs
            self.info("持续范围：{}".format(self.activeJobs))      # self.jobs

            job_id = self.getParam("currentjob")
            if job_id:
                job = self.all_jobs[job_id]
                if isinstance(job, Job):
                    self.info(f'当前任务：{job.JOB_NAME}, 当前任务信息如下：')
                    job.showInfo()
        else:
            job_id = self._job_keys[key]
            job = self.all_jobs[job_id]
            if isinstance(job, Job):
                job.showInfo()

    def registerJob(self, job: Job):
        "注册一个任务到任务管理器"
        self.all_jobs[job.JOB_ID] = job

        # 将id，所有可能的key都加入关键字字典，便于后续搜索任务
        self._job_keys[job.JOB_ID] = job.JOB_ID
        
        if isinstance(job.JOB_KEY, str):
            jobcmd = job.JOB_KEY
            self._patterns_keys.append(job.JOB_KEY)
            self._job_keys[job.JOB_KEY] = job.JOB_ID
    
        elif isinstance(job.JOB_KEY, (list, tuple)):
            jobcmd = "|".join(job.JOB_KEY)
            self._patterns_keys.extend(job.JOB_KEY)
            for key in job.JOB_KEY:
                self._job_keys[key] = job.JOB_ID

        # 接管原任务pattern，重新将其挂接到JobManager
        job.patterns  = r"^job\s({0})(?:\s+(.+))?$".format(jobcmd)
        self.patterns = r"^({0})(?:\s+(.+))?$".format("|".join(self._patterns_keys))

    def registerJobs(self, jobs):
        "注册一组任务到任务管理器"
        if isinstance(jobs, (list, tuple)):
            for job in jobs:
                self.registerJob(job)

        elif isinstance(jobs, dict):
            for job in jobs.values():
                self.registerJob(job)

        elif isinstance(jobs, Job):
            self.registerJob(job)

    @property
    def currentJob(self):
        jobname = "未进行"
        job_id = self.getParam("currentjob")
        if job_id:
            job = self.all_jobs[job_id]
            if isinstance(job, Job):
                jobname = job.JOB_NAME

        return jobname
            
    @property
    def currentStatus(self):
        jobstatus = "未进行"
        job_id = self.getParam("currentjob")
        if job_id:
            job = self.all_jobs[job_id]
            if isinstance(job, Job):
                jobstatus = job.status
        else:
            jobstatus = self.status

        return jobstatus

    @property
    def currentJobInfo(self):
        jobInfo = ""
        job_id = self.getParam("currentjob")
        if job_id:
            job = self.all_jobs[job_id]
            if isinstance(job, Job):
                jobInfo = job.extraInfo

        return jobInfo

    # 所有注册的Job
    @property
    def managedJobs(self):
        jobs = []
        for job in self.all_jobs.values():
            if isinstance(job, Job):
                jobs.append(f"[{job.JOB_ID}]{job.JOB_NAME}")

        return ", ".join(jobs)

    @property
    def activeJobs(self):
        jobs = []
        for id in self.jobs:
            job = self.all_jobs[id]
            if isinstance(job, Job):
                jobs.append(f"[{job.JOB_ID}]{job.JOB_NAME}")

        return ", ".join(jobs)

    async def selectJob(self, *args, **kwargs):
        "从可选任务中选择一个可做的来做"
        ava_jobs = self.session.vars["ava_jobs"]

        min_cooldown_job = min(ava_jobs.values(), key=lambda job: job.cooldown)

        if min_cooldown_job.cooldown == 0:
            self.info(f"现在即可接到下个任务为: {min_cooldown_job.id}, 可以接取")                    
        else:
            self.info(f"需要等待最少冷却时间{min_cooldown_job.cooldown}s接取{min_cooldown_job.id}")                    
            await asyncio.sleep(min_cooldown_job.cooldown+2)
            min_cooldown_job.cando = True

        selected = min_cooldown_job.id

        # selected = None
        # for jobid in self.jobs:
        #     if jobid in ava_jobs.keys():
        #         jobinfo = ava_jobs[jobid]
        #         if isinstance(jobinfo, JobInfo) and jobinfo.cando:
        #             selected = jobid
        #             break

        return selected

    async def start(self, key = "job", *args, **kwargs):
        job_id = None
        if key != "job":
            job_id = self._job_keys[key]
            self.info(f"任务管理器接管成功，进到任务管理的这里来了：）任务id：{job_id}，key：{key}")
        else:
            await self.session.exec_async("jq")
            job_id = await self.selectJob()
            self.info(f"任务管理器选择任务id：{job_id}")

        if job_id:
            job = self.all_jobs[job_id]
            if isinstance(job, Job):
                self.setParam("currentjob", job_id)
                self.status = f"{job.JOB_NAME} 任务中"
                self.info(f"开始运行{job_id}")
                job.jobevent.clear()
                #await self.create_task(job.start(done_callback = functools.partial(asyncio.ensure_future, self.post_handler(job, *args, **kwargs))))
                await self.create_task(job.start(done_callback = functools.partial(self.post_handler, job, *args, **kwargs)))
                #await job.jobevent.wait()
        else:
            self.warning("未选择到可执行任务！等待10s后重试！")
            await asyncio.sleep(10)
            await self.create_task(self.start())

    async def post_handler(self, job: Job, *args, **kwargs):
        self.setParam("currentjob", None)
        self.status = "任务间隙"
        if self.always:
            await self.create_task(job.after_done(*args, **kwargs))
            await asyncio.sleep(1)
            await self.create_task(self.start())

    async def resume(self, *args, **kwargs):
        key = kwargs.get("key", "job")
        if key == "job":
            job_id = self.getParam("currentjob")
        else:
            job_id = self._job_keys[key]

        if job_id:
            job = self.all_jobs[job_id]
            if isinstance(job, Job):
                await self.create_task(job.resume(*args, **kwargs))

    async def finish(self, success=True, *args, **kwargs):
        key = kwargs.get("key", "job")
        if key == "job":
            job_id = self.getParam("currentjob")
        else:
            job_id = self._job_keys[key]

        if job_id:
            job = self.all_jobs[job_id]
            if isinstance(job, Job):
                #self.session.vars.enemies.clear()
                await self.create_task(job.finish(success, *args, **kwargs))

    async def other(self, key, param, *args, **kwargs):
        if key == "job":
            infojobs = []

            if param.startswith("+"):
                jobs = param[1:].split(',')
                for job in jobs:
                    job_id = self._job_keys[job]
                    if job_id not in self.jobs:
                        self.jobs.append(job_id)
                        infojobs.append(f"{self.all_jobs[job_id].JOB_NAME}[{self.all_jobs[job_id].JOB_ID}]")

                self.info(f"成功将以下任务增加到管理清单： {', '.join(infojobs)}")
                

            elif param.startswith("-"):
                jobs = param[1:].split(',')
                for job in jobs:
                    job_id = self._job_keys[job]
                    if job_id in self.jobs:
                        self.jobs.remove(job_id)
                        infojobs.append(f"{self.all_jobs[job_id].JOB_NAME}[{self.all_jobs[job_id].JOB_ID}]")

                self.info(f"成功将以下任务移除到管理清单： {', '.join(infojobs)}")

            elif param.startswith("="):
                self.jobs.clear()
                jobs = param[1:].split(',')
                for job in jobs:
                    job_id = self._job_keys[job]
                    if job_id not in self.jobs:
                        self.jobs.append(job_id)
                        infojobs.append(f"{self.all_jobs[job_id].JOB_NAME}[{self.all_jobs[job_id].JOB_ID}]")

                self.info(f"成功修改任务管理清单为以下任务： {', '.join(infojobs)}")

            elif param == "clear":
                self.jobs.clear()
                self.info(f"已清空管理任务清单")

            else:
                job_id = self.getParam("currentjob")
                if job_id:
                    job = self.all_jobs[job_id]
                    if isinstance(job, Job):
                        if isinstance(job.JOB_KEY, str):
                            key = job.JOB_KEY
                        elif isinstance(job.JOB_KEY, (list, tuple)):
                            key = job.JOB_KEY[0]

                    await self.create_task(job.other(key, param, *args, **kwargs))


        else:
            job_id = self._job_keys[key]
            job = self.all_jobs[job_id]
            if isinstance(job, Job):
                await self.create_task(job.other(key, param, *args, **kwargs))
