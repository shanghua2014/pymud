import asyncio, re
from pymud import PymudMeta, Session, Trigger, Alias, Command, SimpleCommand, PyMudApp, trigger, alias, timer, exception, async_exception


# 插件唯一名称
PLUGIN_NAME    = "moving"

# 插件有关描述信息
PLUGIN_DESC = {
    "VERSION" : "1.0.0",
    "AUTHOR"  : "newstart",
    "RELEASE_DATE"  : "2025-05-18",
    "DESCRIPTION" : 
    """
    使用Command解决北侠中的移动问题，将90%的移动命令使用Command实现，解决移动命令衔接、过河等问题。
    该插件管理了重试，只用输入一次方向，若行走失败，会自动重试 MAX_RETRY_TIMES 次（默认10），直到成功或者次数到了为止。
    本插件加载后，不影响任何正常脚本的使用，也不需要额外编写代码来执行本脚本内容，直接正常命令输入即可。"""
}

# 以下为插件规范必须的代码，请确保函数名和函数参数拼写一致性
def PLUGIN_PYMUD_START(app: PyMudApp):
    "PYMUD自动读取并加载插件时自动调用的函数， app为APP本体。该函数仅会在程序运行时，自动加载一次"
    pass

def PLUGIN_SESSION_CREATE(session: Session):
    "在会话中加载插件时自动调用的函数， session为加载插件的会话。该函数在每一个会话创建时均被自动加载一次"
    CmdMove(session, id = f"{PLUGIN_NAME}.cmd_move", keepEval = True, priority = 90, timeout = 5, group = PLUGIN_NAME)
    CmdWalkPause(session, id = f"{PLUGIN_NAME}.cmd_walkpause", keepEval = True, priority = 90, group = PLUGIN_NAME)
    CmdCrossRiver(session, id = f"{PLUGIN_NAME}.cmd_crossriver", keepEval = True, priority = 90, group = PLUGIN_NAME)
    

def PLUGIN_SESSION_DESTROY(session: Session):
    "在会话中卸载插件时自动调用的函数， session为卸载插件的会话。卸载在每一个会话关闭时均被自动运行一次。"
    session.delObjects([f"{PLUGIN_NAME}.cmd_move", f"{PLUGIN_NAME}.cmd_walkpause", f"{PLUGIN_NAME}.cmd_crossriver"])

def PLUGIN_PYMUD_DESTROY(app: PyMudApp):
    "PYMUD自动卸载插件时自动调用的函数， app为APP本体。该函数仅会在程序运行时，自动卸载一次"
    pass

### 上述代码为插件规范要求的代码， 请确保函数名和函数参数拼写一致性

# 方向清单
DIRECTIONS = (
    "n","s","w","e","ne","nw","se","sw",
    "u","d","nu","su","wu","eu","nd","sd","wd","ed",
    "north", "south", "west", "east", "northeast", "northwest", "southeast", "southwest", 
    "up", "down","northup","southup","westup","eastup","northdown","southdown","westdown","eastdown", "out",
    r"enter(\s\S+)?", r"zuan(\s\S+)?", r"\d", r"leave(\s\S+)?", r"jump\s(jiang|out)", r"climb(\s(ya|yafeng|up|west|wall|mount))?",
    "sheshui", "tang", "act zuan to mao wu", "wander", "xiaolu", r"cai\s(qinyun|tingxiang|yanziwu)", "row mantuo", "push shaqiu"
    )

# 最大重试次数    
MAX_RETRY_TIMES = 10

# 房间名正则表达式
REGX_ROOMNAME = r'^[>]*(?:\s)?(\S.+)\s-\s*(?:杀戮场)?(?:\[(\S+)\]\s*)*(?:㊣\s*)?[★|☆|∞|\s]*$'

#房间出口匹配正则表达式"
REGX_ROOMEXIT = r'^\s*这里(?:明显|唯一)的(?:出口|方向)(?:是|有)(.*)$|^\s*这里没有任何明显的(?:出路|方向|出口)。|^\s*浓雾中你觉得似乎有出口通往(.+)方向。'

MOVE_FAIL = (
    r'^[> ]*哎哟，你一头撞在墙上，才发现这个方向没有出路。$', 
    r'^[> ]*这个方向没有出路。$',
    r'^[> ]*你正要前行，有人大喝：黄河决堤啦，快跑啊！$',
    r'^[> ]*守军拦住了你的去路，大声喝到：干什么的？要想通过先问问我们守将大人！$',
)

MOVE_RETRY = (
    r'^[> ]*你正忙着呢。$', 
    r'^[> ]*你的动作还没有完成，不能移动。$', 
    r'^[> ]*你还在山中跋涉，一时半会恐怕走不出这(六盘山|藏边群山|滇北群山|西南地绵绵群山)！$', 
    r'^[> ]*你一脚深一脚浅地沿着(\S+)向着(\S+)方走去，虽然不快，但离目标越来越近了。',
    r'^[> ]*你一脚深一脚浅地沿着(\S+)向着(\S+)方走去，跌跌撞撞，几乎在原地打转。',
    r'^[> ]*你小心翼翼往前挪动，遇到艰险难行处，只好放慢脚步。$', 
    r'^[> ]*山路难行，你不小心给拌了一跤。$', 
    r'^[> ]*你忽然不辨方向，不知道该往哪里走了。',
    r'^[> ]*走路太快，你没在意脚下，被.+绊了一下。$',
    r'^[> ]*你不小心被什么东西绊了一下，差点摔个大跟头。$',
    r'^[> ]*青海湖畔美不胜收，你不由停下脚步，欣赏起了风景。$', 
    r'^[> ]*(荒路|沙石地|沙漠中)几乎没有路了，你走不了那么快。$', 
    r'^[> ]*你小心翼翼往前挪动，生怕一不在意就跌落山下。$',
    r'^[> ]*这里山路崎岖，不小心就会滑落，实在不太好走，你不得不放慢脚步。$',
    r'^[> ]*你在小路中仔细对照，寻找往前的路径。',
    r'^[> ]*小路宽度不足以容纳两人并肩行走，你需要小心翼翼地前行。',
    r'^[> ]*道路崎岖难行，一不留神就会滚下山去，你心道：.+',
    r'^[> ]*你在浙闽之间的群山中.+',
    r'^[> ]*山道往上愈发难行，你不得不缓下脚步。',
    r'^[> ]*你沿着.+，一步一步地慢慢前行。',
    r'^[> ]*在这里可没法走那么快。',
    r'^[> ]*你定了定神，仔细观察周围。',
    r'^[> ]*不经过盘查就想离开关城？',
    r'^[> ]*你没看清路就乱走，结果转了一圈又回到原地。',
    r'^[> ]*走在石阶上，你看着身边的悬崖，稍有不慎就是粉身碎骨的下场，不由得靠里侧身，放缓脚步。',
    r'^[> ]*看着四周的淤泥，你谨慎地选择下脚的方位。',
    r'^[> ]*你赶紧擦拭裤脚上的水迹。',
    r'^[> ]*你踏在泥泞的水坑里，深一脚浅一脚地无法快速通行。',
    r'^[> ]*走到最狭窄处不足一尺，你能侧身缓行。',
    r'^[> ]*这里道路艰险难行，已经无法再提速了。',
    r'^[> ]*你的视线被巍峨的恒山吸引，不由放慢了脚步。',
    r'^[> ]*这里险峻异常，稍有不慎就是跌落深渊的下场。',
    r'^[> ]*此去往东是荒郊野岭，盗贼猛兽出没之地，我劝.+',
    r'^[> ]*因为道路变得极陡，你行至此处不得不放慢脚步。',
    r'^[> ]*你沿着溪边，一步一步地离去。',
    r'^[> ]*在栈道上想快也快不起来。',
    r'^[> ]*河滩上乱石遍地，深深浅浅，几乎没法快起来。',
    r'^[> ]*路途更加险峻，兼之视线受阻，你不得不停下仔细观察脚下和前路。',
    r'^[> ]*雪路很滑，你不由得放慢了速度，小心翼翼地行走！',
    r'^[> ]*到了剑门关前，道路更加险峻，除了慢慢登上关城，别无他途。',
    r'^[> ]*这条路上山太困难了，你顿生进退两难之感。',
)

MOVE_PAUSE = (      
    r'^[> ]*一条大瀑布如玉龙悬空，滚滚而下，倾入一座清澈异常的大湖之中.$',
    r'^[> ]*你终于一步步的终于挨到了桥头.$',
    r'^[> ]*突然你突然脚下踏了个空，向下一滑，身子登时堕下了去。$',
    r'^[> ]*到达了目的地.+，你从马车上走了下来。$',
    r'^[> ]*你朝船夫挥了挥手便跨上岸去。$',
    r'^[> ]*六名雪山弟子一齐转动机关，吊桥便又升了起来。',
    r'^[> ]*你从小船上跳了下来，到了.+$',
    # 大理天龙寺大门
    r'^[> ]*包铁大门被打开了。',
    r'^[> ]*包铁大门被人打开了。',
    r'^[> ]*这里包铁大门已经打开了，你还敲什么啊？',
    r'^[> ]*这里包铁大门已经打开了，你还想怎样？',
    # 灵鹫宫百丈涧，相同
    (r'^[> ]*你终于来到了对面，心里的石头终于落地。$', REGX_ROOMNAME),
    # 下面时太湖，pause出来后才出来room标题描述
    r'^[> ]*绿衣少女将小船系在树枝之上，你跨上岸去。$',
    (r'^[> ]*你沿着踏板走了上去。$', REGX_ROOMNAME),
    (r'^[> ]*不知过了多久，船终于靠岸了，你累得满头大汗。$', REGX_ROOMNAME),
    (r'^[> ]*小舟终于划到近岸，你从船上走了出来。$', r'^[> ]*\s*$', REGX_ROOMNAME),
    
)

class CmdMove(Command):
    def __init__(self, session: Session, *args, **kwargs):
        # 将所有移动相关命令拼接为匹配的正则表达式。
        # 当命令行输入命令，或者用exec系列函数调用发送的命令，与本Command的patterns（也就是此处的pattern）匹配时，
        # 会触发该命令的execute函数执行，并将实际输入的命令传入execute的cmd参数
        # 因为移动命令的pattern目前就是这些，因此在代码里将其写死，那么创建CmdMove实例对象是就无需重复指定 patterns
        pattern = r"^({0})$".format("|".join(DIRECTIONS))
        super().__init__(session, patterns = pattern, *args, **kwargs)

        # 所有触发器都相同的公共参数，减少后面创建触发器时的代码输入
        tris_kwargs_default = {
            "enabled"   : False,
            "keepEval"  : True,
            "priority"  : 90,
            "timeout"   : 5,
        }

        # 将所有命令对象放到 _objs 数组中，用于 __unload__ 时卸载
        # 由于在本命令中的触发器全部使用异步模式，因此所有触发器都没有配置 onSuccess 函数，保留默认即可。
        # 因为后续所有的判断也无需使用触发器 id ，因此所有的id 都使用系统自动设置的默认值，不再配置。
        # 异步触发器获取是否触发使用 await tri.triggered() 的方式处理
        self._objs = [
            # 当移动命令成功之后，正常应该收到房间名称，因此将房间名称作为成功的触发匹配。将匹配成功的触发器组名设置为 moving.move.success 用于后续判断
            Trigger(self.session, REGX_ROOMNAME, group = "moving.move.success", **tris_kwargs_default)
        ]

        # 当移动失败(没路，无需重试）之后，可能收到一个表示失败的消息，目前梳理的所有失败消息都在 MOVE_FAIL 定义中列举。将所有这些消息都分别设置为触发器，表示移动失败。将所有移动失败的触发器组名设置为 moving.move.fail 用于后续判断
        # 将创建的所有表示失败的触发器都放入 self._objs 数组，以便后面 __unload__ 能正常卸载
        # 这些触发器也一样，都是用异步模式，因此无需配置 onSuccess 函数
        for s in MOVE_FAIL:
            self._objs.append(Trigger(self.session, patterns = s, group = "moving.move.fail", **tris_kwargs_default))

        # 当移动失败（有路，但由于各种原因未移动成功）之后，可能收到一个表示失败（可以重试）的消息，目前梳理的所有消息都放在 MOVE_RETRY 中。
        # 与上面类似，这种失败的触发器组名设置为 moving.move.retry 一共后续判断。
        for s in MOVE_RETRY:
            self._objs.append(Trigger(self.session, patterns = s, group = "moving.move.retry", **tris_kwargs_default))

    def __unload__(self):
        # 卸载函数中，将所有 _objs 中的对象从会话中移除
        self.session.delObjects(self._objs)

    # 以下内容为该Command的主执行函数。当正常触发了该命令时，pymud会自动调用该函数，并将实际命令通过cmd参数传递到函数中
    # 因此，移动动作的所有处理均放在此函数中。
    # 假设输入一个命令之后，服务器可能的响应有以下几种可能：
    #   1. 该方向有出路，且移动成功，成功走到一个新的房间，因此可以收到服务器的 房间名 一行信息，此时， moving.move.success 组的这个触发器会被触发；
    #   2. 该方向没有出路，移动失败，服务器会返回类似『你一头撞在墙上』的表示失败的信息，此时， moving.move.fail 组中的某一个触发器会被触发；
    #   3. 该方向有出路，但由于busy或其他导致移动失败，服务器会返回类似『你正忙着呢』表示失败（但实际可以走过去）的消息，此时， moving.move.retry 组中的某一个触发器会被触发；
    #   4. 由于角色处于昏迷状态，或者网络延迟原因，等待好长一段时间（此处给定默认值为 self.timeout = 5秒）后，都没有收到上述3中情况的任意反馈，此时，我们认为命令执行超时。
    # 下面的处理，就是在送出命令之后，识别到底是哪一种情况，再根据情况判断后续执行操作。
    # 因为是异步函数，增加一个 async_exception 异常处理的装饰器，在这里如果代码运行错误后，会打印到session中
    @async_exception
    async def execute(self, cmd, *args, **kwargs):  # type: ignore
        # 复位本命令，请保留，暂时无需关注细节
        self.reset()

        # 定义一个重试的次数参数
        retry_times = 0

        # 使能本命令创建的所有触发器。使用 subgroup 参数配置，让所有组名以 moving.move开头的组内的所有对象均开启 enabled
        self.session.enableGroup(group = "moving.move", enabled = True, subgroup = True)

        # 先将结果状态设置为 NOTSET，表示 未设置
        result = self.NOTSET

        # 最多循环 MAX_RETRY_TIMES 次，用于处理 retry 情况
        while retry_times < MAX_RETRY_TIMES:
            # 将所有触发器的异步触发状态 triggered() 生成任务，供异步触发判断使用。有关 tri.triggered() ,可以把鼠标放在下面的 tri.triggered() 上，查看文档字符串帮助
            # 此处使用了 Python 的列表推导语句，简化代码输入
            # 实际内容就是将上面 self._objs 中的每一个触发器，都调用 tri.triggered() 以生成协程对象，再使用 create_task 包裹成任务，供后续使用
            # 相当于这么写的代码：
            # tasklist = []
            # for tri in self._objs:
            #    tasklist.append(self.create_task(tri.triggered()))
            tasklist = [self.create_task(tri.triggered()) for tri in self._objs]
            
            # 下面这一句是关键，表示向服务器发出 cmd 命令，然后等待 tasklist 里涉及的所有触发器中的第一个被触发，或者等待时间达到 timeout 秒
            # self.session.waitfor 是为了简化写法。实际相当于三步命令的整合：
            #    await asyncio.sleep(0.05)     # 将CPU的执行时间从本函数中断0.05秒，暂时不需要关注此处细节
            #    self.session.writeline(cmd)   # 向服务器发送 cmd 命令
            #    done, pending = await asyncio.wait(tasklist, timeout = self.timeout, return_when = "FIRST_COMPLETED")  # 等待 tasklist 中的任务第一个完成（也就是触发器被触发），或者超时。此处 FIRST_COMPLETED 就是指示等待第一个完成后结束
            #    上面有关 asyncio.wait 的详细信息，可以参考 Python 的官方文档， asyncio 库的说明
            done, pending = await self.session.waitfor(cmd, asyncio.wait(tasklist, timeout = self.timeout, return_when = "FIRST_COMPLETED"))    # type: ignore
            # 上述代码执行完毕后，返回两个 set， done表示已完成的任务列表， pending 表示还在等待状态的任务列表
            
            # 当执行到此处时，首先，将所有还在等待状态的任务列表取消掉，因为到这里都还没有被触发，那么这些触发器在本次命令执行过程中不可能再被触发了。
            tasks_pending = list(pending)
            for t in tasks_pending:
                self.remove_task(t)

            # 获取已经完成的任务列表。由于set不能以下标访问内容，因此先转换为 list
            tasks_done = list(done)
            
            # 如果 task_done 里的任务数大于0  （即被触发的触发器数量>0）。根据北侠逻辑，被触发的触发器最多只可能有1个（或者超时的话，就1个都没有）
            if len(tasks_done) > 0:
                # 那么，从完成的任务中取出第1个任务，即为实际被触发的触发器
                task = tasks_done[0]
                # 通过对任务调用 task.result()，可以获取该触发器的触发结果，即 tri.triggered() 的返回结果。结果包括4个数值，分别为 state, id, line, wildcards。
                # 其中，触发器成功触发后，返回的 state 一定为 SUCCESS，因此此处将第一个结果丢弃，仅去后3个结果，即 id, line, wildcards
                # id, line, wildcards三个参数，和 onSuccess 回调时，函数里收到的这三个参数内容完全一致
                # 因此，后面就可以通过对这3个参数的解析，判断到底是哪一个触发器被成功触发了。
                _, id, line, wildcards = task.result()
                # 先通过返回的 id 获取实际被触发的触发器
                tri = self.session.tris[id] 

                # 对触发器进行判断，看是哪一个
                # 如果该触发器的组名为 moving.move.success，表示收到了新的房间标题内容，即移动成功
                # 成功后，就不再执行 while 循环内容了，返回 SUCCESS 状态，并通过 break 中止循环
                if tri.group == "moving.move.success":
                    result = self.SUCCESS
                    break
                    
                # 如果该触发器的组名为 moving.move.fail，表示收到了 MOVE_FAIL 中的某一个内容的触发
                # 因为这种情况表示是该方向没有路，因此 self.error 打印出来该信息，并且返回 FAILURE
                # 没有路，也不需要再执行 while 循环的内容了，直接通过 break 中止循环
                elif tri.group == "moving.move.fail":
                    self.error(f'执行{cmd}，移动失败，错误信息为{line}', '移动插件')
                    result = self.FAILURE
                    break

                # 如果该触发器的组名为 moving.move.retry，表示收到了 MOVE_RETRY 中的某一个内容的触发
                # 因为这种情况表示是该方向有路，但本次移动失败，因此重试次数加一，并延迟2秒，然后会回到 while 循环处，再执行下一轮次
                # 因为有路，也不需要再执行 while 循环的内容了，直接通过 break 中止循环
                elif tri.group == "moving.move.retry":
                    retry_times += 1
                    await asyncio.sleep(2)

            # 如果 task_done 里的任务为0，表示没有任何触发器被触发，此时就是超过了等待的 timeout 时间，表示超时
            # 当超时时，设置 TIMEOUT 标记，然后break中止循环。因为超时后，也不需要重试了。
            else:
                self.warning(f'执行{cmd}超时{self.timeout}秒', '移动插件')  
                result = self.TIMEOUT
                break
        
        # 执行到这里，本次命令全部执行完毕，此时将所以触发器都关掉，减轻对其他命令或触发器判断的干扰
        self.session.enableGroup(f"{PLUGIN_NAME}.move", False)
        # 返回前面设置的的 result 值。此处的返回值，是让本 Command 被其他地方调用时，判断命令执行完后状态的标记
        # 如果其他地方有类似  result = self.session.exec_async("w") 的命令， 返回的 result 就是此处数值
        return result


class CmdWalkPause(SimpleCommand):
    WALK_PAUSE_CMDS = ("zou tiesuo", r"ride(\s\S.+)?", r"qu\s\S+", "guo qiao", "sheng bridge", "climb stiff")

    def __init__(self, session, *args, **kwargs):

        self._tris = [
            Trigger(session, s, priority = 90, keepEval = True, group = f"{PLUGIN_NAME}.walkpause") for s in MOVE_PAUSE    # type: ignore
        ]
    
        self._tris.append(
            Trigger(session,  r'^[> ]*大车停稳了下来，你可以下车\(xia\)了。$', priority = 90, keepEval = True, group = f"{PLUGIN_NAME}.walkpause", onSuccess = self._onArrived)
            )

        avai_cmds = r"^({0})$".format("|".join(self.WALK_PAUSE_CMDS))
        super().__init__(session, avai_cmds, self._tris, timeout = 30, *args, **kwargs)

    def __unload__(self):
        self.session.delObjects(self._tris)

        super().__unload__()

    def _onArrived(self, name, line, wildcards):
        # 要为_onArrived增加对xia之后的判断，以支持惯性导航的寻路
        self.session.writeline("xia")
    

class CmdCrossRiver(Command):
    def __init__(self, session, *args, **kwargs):
        super().__init__(session, "^(changjiang|jiang|huanghe|river|dongtinghu|lake)$", *args, **kwargs)

        kwargs = {"keepEval": True, "group": f"{PLUGIN_NAME}.river"}
        self._tris = {
            "boat"      : Trigger(session, r'^[> ]*一叶扁舟缓缓地驶了过来，艄公将一块踏脚板搭上堤岸，以便乘客|^[> ]*岸边一只渡船上的艄公说道：正等着你呢，上来吧|^[> ]*渡船缓缓靠岸，船上的船工摆出跳板，方便客人上下船。', onSuccess = self.onBoat, enabled = False, **kwargs),
            "wait"      : Trigger(session, r'^[> ]*只听得江面上隐隐传来：“别急嘛，这儿正忙着呐……”', onSuccess = self.onWait, **kwargs),
            "money"     : Trigger(session, r'^[> ]*(艄公|船老大)一把拉住你，你还没付钱呢？', onSuccess = self.onMoney, **kwargs),
            "arrive"    : Trigger(session, r'^[> ]*艄公说.+随即把一块踏脚板搭上堤岸|^[> ]*船工放下跳板，招呼大家下船了。', **kwargs),             
            "out"       : Trigger(session, r'^[> ]*艄公要继续做生意了，所有人被赶下了渡船。', **kwargs),
            "room"      : Trigger(self.session, REGX_ROOMNAME, enabled = True, priority = 80, **kwargs)
        }

        self._boat_arrived = False
        self._noMoney = False

    def __unload__(self):
        self.session.delObjects(self._tris)

    def onBoat(self, id, line, widlcards):
        self._boat_arrived = True
        self.session.writeline("enter")
        self._tris["boat"].enabled = False
        self._tris["arrive"].enabled = True
        self._tris["out"].enabled = True

    def onWait(self, id, line, wildcards):
        self._boat_arrived = False

    def onMoney(self, id, line, wildcards):
        self._noMoney = True

    @async_exception
    async def execute(self, cmd, *args, **kwargs):
        self.reset()

        river = "jiang"
        if (cmd == "changjiang") or (cmd == "jiang") or (cmd == "长江"):
            river = "jiang"
        elif (cmd == "huanghe") or (cmd == "黄河"):
            river = "huanghe"
        # 以下是往西南，定时坐船的，现场等就行
        elif (cmd == "river") or (cmd == "river"):
            river = "river"
        # 这个是洞庭湖
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
            self.error("没钱坐什么船！", "移动插件")
            return self.FAILURE
        
        done, pending = await asyncio.wait(awts, return_when = "FIRST_COMPLETED")

        tasks_pending = list(pending)
        for t in tasks_pending:
            self.remove_task(t)

        task_out = self.create_task(self._tris["room"].triggered())
        await asyncio.sleep(0.1)

        tasks_done = list(done)
        if len(tasks_done) > 0:
            task = tasks_done[0]
            _, name, line, wildcards = task.result()

            if name == self._tris["arrive"].id:
                self.session.writeline("out")
                    
            else:
                self.session.writeline("look")

        await task_out
        await asyncio.sleep(0.5)
        
        return self.SUCCESS

