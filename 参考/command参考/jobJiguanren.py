import asyncio, cn2an
from pymud import Trigger, SimpleTrigger, IConfig

from ..common import word2number
from .job import Job

class JobZhangjinao(Job, IConfig):
    "机关人起源（张金鳌）任务"

    JOB_ID   = "99"
    JOB_KEY  = ["zja", "muren"]
    JOB_NAME = "张金鳌"
    JOB_LOCATION = "linan"
    RESET_LOCATION = "linan"

    def __init__(self, session, *args, **kwargs):
        kwargs.setdefault("id", "job_muren")
        super().__init__(session , *args, **kwargs)

        self._tris = {
            "start"     : Trigger(self.session, r"^[> ]*张金鳌说道：「你去到(\S+)之后缓行\(walk\)(\S+)步当可发现我留下的线索，一切自有分晓。」", id = "jgr_start", group = "jgr"),
            "info"      : SimpleTrigger(self.session, r"^[> ]*你揉揉眼睛仔细一看，这似乎就是张金鏊提到的线索？", "l xian suo", id = "jgr_info", group = "jgr"),
            "xiansuo"   : Trigger(self.session, r"^[> ]*这是一张纸，似乎是张金鏊提到的线索，木人似乎就在(\S+)的(\S+)附近，去拆了它吧。", id = "jgr_xiansuo", group = "jgr"),
            "done"      : Trigger(self.session, r"^[> ]*你获得了一枚机关核心，可以回去交任务了。", id = "jgr_killed", group = "jgr")
        }

    def __unload__(self):
        self.session.delObjects(self._tris)

    def showInfo(self):
        self.info(f"当前张金鳌任务有关信息为：")
        self.info(f'当前状态：{self.status}')
        self.info(f'线索节点: {self.getParam("node")}')
        self.info(f'需走步数: {self.getParam("steps_ch")}步({self.getParam("steps")})')
        self.info(f'木人地址: {self.getParam("loc2")}')
        self.info(f'上次任务完成获得奖励: {self.getParam("award")}')

    async def start(self, key=None, *args, **kwargs):
        "新版JOB归一化任务处理"
        await super().start(key, *args, **kwargs)
        # 1. 跑到地方
        self.status = "待接任务"

        state = await self.create_task(self.session.exec_async(f"rt {self.JOB_LOCATION}"))
        if state.result == self.SUCCESS:
            self.status = "等待张金鳌告诉地址"
            self._tris["start"].enabled = True
            state, name, line, wildcards = await self.session.waitfor("ask zhang about job", self._tris["start"].triggered())
            self.setParam("node", wildcards[0])      # 线索地址(节点)
            self.setParam("steps_ch", wildcards[1]) # 行走步数(中文)
            self.setParam("steps", word2number(wildcards[1]))     # 行走步数(数字)
            await self.create_task(self.findclue(wildcards[0]))

    async def findclue(self, place):
        # 去往线索地址
        self.status = f'查找节点: {place}'
        nodes = self.session.vars["_map"].GetNodeInfo(place)
        if len(nodes) == 1:  # 表明查找到了
            node = nodes[0]
            id, name, city = node[0], node[1], node[2]

            self.status = f"去往线索地址: ({city}{name}(ID = {id}))"
            await self.create_task(self.session.exec_async(f"rt {id}"))
            self.info("即将look <node>查看检查")
            state = await self.create_task(self.session.exec_async("l <node>"))
            if state.result == self.SUCCESS:
                self.status = "节点行走中"
                nodeinfo = state.room
                walk_command = f"walk {nodeinfo[1]} {self.getParam('steps')}"
                self.info(f"即将行走节点{nodeinfo[0]} {self.getParam('steps_ch')} 步 : {walk_command}")
                await asyncio.sleep(1)
                await self.create_task(self.session.exec_async(walk_command))
                
                _, _, _, wildcards = await self.create_task(self._tris["xiansuo"].triggered())
                muren_loc = f"{wildcards[0]}{wildcards[1]}"
                self.setParam("loc2", muren_loc)
                self.info(f"已获取机关人线索，地址：{muren_loc}")
                await self.create_task(self.search(muren_loc))
            else:
                self.warning(f"")
        else:
            self.warning(f"未找到{place}的节点信息")
        
    async def search(self, place):
        self.status = f"寻找木人中 ({place})"
        self.info(f"木人地点为 {place}，即将前往寻找木人")

        result, npcid = await self.create_task(self.session.exec_async(f"bl {place} 木人 mu ren"))
        if result == self.SUCCESS:
            self.status = f"战斗中"
            await asyncio.sleep(1)
            self.session.exec(f"k mu")
            await self.create_task(self._tris["done"].triggered())
            self.info(f"已干掉木人并获得机关核心，即将自动返回")
            await asyncio.sleep(1)
            await self.create_task(self.finish())

    async def finish(self, success=True, *args, **kwargs):
        if success:
            self.status = "成功返回中"
        else:
            self.status = "失败返回中"

        state = await self.create_task(self.session.exec_async(f'rt {self.JOB_LOCATION}'))
        if state.result == self.SUCCESS:
            if success:
                self.session.writeline("give zhang core")
                # state, name, line, wildcards = await self.create_task(self.tri_jiangli.triggered())
                # self.setParam("award", wildcards[0])
            else:
                self.session.writeline("ask zhang about fail")

            self.status = "初始化"

            await asyncio.sleep(2)
            await self.create_task(self.session.exec_async('liaoshang'))

            self.jobevent.set()
            self.info('任务事件已设置，可以继续了')

            await super().finish(success, *args, **kwargs)

    async def resume(self, *args, **kwargs):
        self.status = "寻找木人中"
        loc = self.getParam("loc2")
        self.info(f"木人地点为 {loc}，即将前往寻找木人")
        await self.create_task(self.search(loc))

    async def other(self, key, param, *args, **kwargs):
        if " "in param:
            params = param.split()
            self.setParam("loc", params[0])
            self.setParam("steps", params[1])
            self.setParam("steps_ch", cn2an.an2cn(params[1]))

            await self.create_task(self.findclue(params[0]))

        else:
            #self.status = "寻找木人中"
            self.setParam("loc2", param)
            #self.info(f"木人地点为 {param}，即将前往寻找木人")
            await self.create_task(self.search(param))

