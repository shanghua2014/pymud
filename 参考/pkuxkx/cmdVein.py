import traceback, re, asyncio
from pymud import Session, Command, Trigger, IConfig

class CmdVein(Command, IConfig):
    "通脉处理"
    def __init__(self, session, *args, **kwargs):
        kwargs.setdefault("id", "cmd_vein")
        super().__init__(session, r"^(vein)(?:\s+(\S+))?$", *args, **kwargs)
        #> 你现在内力不足，强行通脉，有害无益。
        #> 此次冲穴消耗了(九百一十七)点内力，内力被纳入(云门穴)。
        #> 你的真气在手太阴肺经上云门穴运行受阻，还是尽快想办法把受损的经脉恢复吧。
        
        self._tris = {
            "neili" : Trigger(session, r"^[> ]*你现在内力不足，强行通脉，有害无益。", group = "vein"),
            "done"  : Trigger(session, r"^[> ]*此次冲穴消耗了\S+点内力，内力被纳入\S+。", group = "vein"),
            "block" : Trigger(session, r"^[> ]*你的真气在\S+运行受阻，还是尽快想办法把受损的经脉恢复吧。", group = "vein"),
            "next"  : Trigger(session, r"^[> ]*现在你只能尝试往(\S+)里灌注内力。", group = "vein"),
            "max"   : Trigger(session, r"^[> ]*过多尝试通脉次数，有害无益。今天就到此为止吧。", group = "vein")
        }

        self._halted = False

    def __unload__(self):
        self.session.delObjects(self._tris)

    async def execute(self, cmd, *args, **kwargs):
        try:              
            m = re.match(self.patterns, cmd)
            if m:
                param = m[2]
                if param == "stop":
                    self._halted = True
                    self.info("即将停止通脉，请等待本次通脉完成", "通脉")

                elif param == "start":
                    self.reset()
                    self._halted = False
                    if not self.session.getVariable("vein"):
                        self.session.setVariable("vein", "云门")

                    times = 0
                    while not self._halted:
                        done, pending = await self.session.waitfor(f"vein through {self.session.vars.vein}", asyncio.wait([
                            self.create_task(tri.triggered()) for tri in self._tris.values()
                        ], timeout = 10, return_when = "FIRST_COMPLETED"))

                        for task in list(pending):
                            self.remove_task(task, "其他任务已完成。")
                        
                        tasks_done = list(done)
                        if  len(tasks_done) == 1:
                            task = tasks_done[0]
                            state, name, line, wildcards = task.result()
                            if name == self._tris["done"].id:
                                await asyncio.sleep(0.5)

                            elif name == self._tris["neili"].id:
                                await asyncio.sleep(0.5)
                                await self.session.exec_async("feed")
                                await asyncio.sleep(0.5)
                                
                                await self.session.exec_async("dzt max")
                                await asyncio.sleep(0.5)

                            elif name == self._tris["next"].id:
                                self.info(f"穴道已冲开，更换为{wildcards[0]}继续")
                                self.session.setVariable("vein", wildcards[0])
                                await asyncio.sleep(0.5)

                            elif name == self._tris["max"].id:
                                self.info(f"今日冲穴次数已达上限！")
                                break

                            elif name == self._tris["block"].id:
                                self.warning("通脉过程中经脉受阻，需使用经脉修复药剂！！！", "通脉")
                                break

                        else:
                            self.error("通脉过程中发生错误，请检查", "通脉")

                    self.info("通脉已停止", "通脉")
                    await asyncio.sleep(2)
                    self.session.exec("dzt always")

                # 其他情况直接输出
                else:
                    self.session.writeline(cmd)

        except Exception as e:
            self.error(f"异步执行中遇到异常, {e}, 类型为 {type(e)}")
            self.error(f"异常追踪为： {traceback.format_exc()}")