import traceback, asyncio
from pymud import Command, Trigger, IConfig

class CmdCrossRiver(Command, IConfig):
    def __init__(self, session, *args, **kwargs):
        kwargs.setdefault("id", "cmd_crossriver")
        super().__init__(session, "^(changjiang|jiang|huanghe|dongtinghu|lake)$", *args, **kwargs)

        kwargs = {"keepEval": True, "group": "river"}
        self._tris = {
            "boat"      : Trigger(session, r'^[> ]*一叶扁舟缓缓地驶了过来，艄公将一块踏脚板搭上堤岸，以便乘客|^[> ]*岸边一只渡船上的艄公说道：正等着你呢，上来吧|^[> ]*渡船缓缓靠岸，船上的船工摆出跳板，方便客人上下船。', onSuccess = self.onBoat, enabled = False, **kwargs),
            "wait"      : Trigger(session, r'^[> ]*只听得江面上隐隐传来：“别急嘛，这儿正忙着呐……”', onSuccess = self.onWait, **kwargs),
            "money"     : Trigger(session, r'^[> ]*艄公一把拉住你，你还没付钱呢？', onSuccess = self.onMoney, **kwargs),
            "arrive"    : Trigger(session, r'^[> ]*艄公说.+随即把一块踏脚板搭上堤岸|^[> ]*船工放下跳板，招呼大家下船了。', **kwargs),             
            "out"       : Trigger(session, r'^[> ]*艄公要继续做生意了，所有人被赶下了渡船。', **kwargs)
        }

        self._boat_arrived = False
        self._noMoney = False
        self.hubiao_processing = False

    def __unload__(self):
        self.session.delObjects(self._tris)

    def onBoat(self, id, line, widlcards):
        self._boat_arrived = True
        if self.hubiao_processing:
            self.session.writeline("gan che to enter")
        else:
            self.session.writeline("enter")
        self._tris["boat"].enabled = False
        self._tris["arrive"].enabled = True
        self._tris["out"].enabled = True

    def onWait(self, id, line, wildcards):
        self._boat_arrived = False

    def onMoney(self, id, line, wildcards):
        self._noMoney = True

    async def execute(self, cmd, *args, **kwargs):
        try:
            self.reset()
            self.hubiao_processing  = kwargs.get("hubiao", False)

            river = "jiang"
            if (cmd == "changjiang") or (cmd == "jiang") or (cmd == "长江"):
                river = "jiang"
            elif (cmd == "huanghe") or (cmd == "黄河"):
                river = "huanghe"
            # 以下是往西南，定时坐船的
            elif (cmd == "river") or (cmd == "river"):
                river = "river"
            elif (cmd == "hu") or (cmd == "dongtinghu"):
                river = "hu"
            else:
                self._onFailure(cmd)
                return self.FAILURE

            self._boat_arrived = False
            self._noMoney = False

            self._tris["boat"].enabled = True
            
            awts = [self.create_task(self._tris["arrive"].triggered()), self.create_task(self._tris["out"].triggered())]

            await asyncio.sleep(0.1)

            while not self._boat_arrived:
                if river != "river":
                    self.session.writeline("yell boat")
                await asyncio.sleep(3)
            
            if self._noMoney:
                self._onFailure("nomoney")
                return self.FAILURE
            
            done, pending = await asyncio.wait(awts, return_when = "FIRST_COMPLETED")

            tasks_pending = list(pending)
            for t in tasks_pending:
                self.remove_task(t)

            task_out = self.create_task(self.session.tris.tri_room.triggered())
            await asyncio.sleep(0.1)

            tasks_done = list(done)
            if len(tasks_done) > 0:
                task = tasks_done[0]
                _, name, line, wildcards = task.result()

                if name == self._tris["arrive"].id:
                    if self.hubiao_processing:
                        self.session.writeline("gan che to out")
                    else:
                        self.session.writeline("out")
                else:
                    self.session.writeline("look")

            state = await task_out
            await asyncio.sleep(0.5)

            # 将cmd_room信息传递到cmd_move，以实现惯导系统跟踪，传递的命令类似为cross_river(changjiang)
            self.session.cmds.cmd_move.update_ins_location(f"cross_river({river})", state.wildcards[0])
            
            return self.SUCCESS
        
        except Exception as e:
            self.error(f"异步执行中遇到异常, {e}, 类型为 {type(e)}")
            self.error(f"异常追踪为： {traceback.format_exc()}")
