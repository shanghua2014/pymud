import webbrowser, asyncio, time, functools
from pymud import Alias, Trigger, SimpleCommand, Timer, SimpleTrigger, SimpleAlias
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType
from settings import Settings

class Configuration:
    youkunyiKey = ("here", "name", "hulu", "jianghu")
    score = ("sex",)
    ttt = ("t1",)
    # print("总数：", youkunyiKey.__len__())
    # for k, v in enumerate(youkunyiKey):
    #     time.sleep(0.5)
    #     # print(k, v)
    #     print('abc:---'+v)


    def __init__(self, session) -> None:
        self.session = session
        self._triggers = {}
        self._commands = {}
        self._timers = {}

        self._initTriggers()
        self._initCommands()

    def _initTriggers(self):
        this = self.session
        this.status_maker = self.status_window

        # 关闭触发 #py self.enableGroup('grouo1', False)
        self._triggers["tri_jq_1"] = SimpleTrigger(self.session,
            r"^[> ]*你可以用jobquery命令",
            "jq", group="wmg", id="tri_jq_1",
        )
        self._triggers["tri_jq_2"] = SimpleTrigger(self.session,
            r"^[> ]*拿着刻有.+的葫芦去柳秀山庄一问究竟",
            "#wa 1000;climb up", group="wmg", id="tri_jq_2",
        )
        self._triggers["tri_jq_3"] = SimpleTrigger(self.session,
            r"^[> ]*你.+爬了上来",
            "#wa 300;#3 n;#wa 1000;knock gate", group="wmg", id="tri_jq_3",
        )
        self._triggers["tri_jq_4"] = SimpleTrigger(self.session,
            r"^[> ]*你轻轻地敲了敲门，只听吱地一声，一个小丫鬟将门打开了一道缝，露出脑袋，转着乌黑的大眼睛，笑嘻嘻打量着你",
            "ask yahuan about 葫芦", group="wmg", id="tri_jq_4",
        )
        self._triggers["tri_jq_5"] = SimpleTrigger(self.session,
            r"^[> ]*丫鬟见你手中的葫芦，惊诧地「咦？」了一声",
            "knock gate", group="wmg", id="tri_jq_5",
        )
        self._triggers["tri_jq_5_1"] = SimpleTrigger(self.session,
            r"^[> ]*丫鬟说道：「这位小姑娘，你回来啦，快请进吧！」",
            "#3 n", group="wmg", id="tri_jq_5_1",
        )
        self._triggers["tri_jq_6"] = SimpleTrigger(self.session,
            r"^[> ]*.+示意你赶紧把葫芦给这位庄主",
            "give hulu to you kunyi", group="wmg", id="tri_jq_6",
        )
        # test 向游鲲翼依次打听，here、name、葫芦、闯荡江湖
        self._triggers["tri_jq_7"] = Trigger(self.session,
            patterns=(r"^[> ]*向游鲲翼依次打听，(\w+)、(\w+)、(.+)、(.+)"), group="wmg", id="tri_jq_7",
            onSuccess=self.onTriggerAsk,
        )
        # test 使用follow a shu命令跟随丫鬟阿姝，然后她会带你熟悉一下山庄
        self._triggers["tri_jq_8_1"] = SimpleTrigger(self.session,
            r"^[> ]*使用.+命令跟随丫鬟阿姝，然后她会带你熟悉一下山庄",
            "follow a shu", group="wmg", id="tri_jq_8_1",
        )
        self._triggers["tri_jq_8_2"] = SimpleTrigger(self.session,
            r"^[> ]*把脏衣服脱了，在浴室洗个澡",
            "follow none;remove all;bath", group="wmg", id="tri_jq_8_2",
        )
        self._triggers["tri_jq_8_3"] = SimpleTrigger(self.session,
            r"^[> ]*洗完穿上衣服，向游鲲翼打听闯荡江湖",
            "#wa 1000;wear all;s;w;ask you kunyi about 闯荡江湖", group="wmg", id="tri_jq_8_3",
        )
        self._triggers["tri_jq_9"] = SimpleTrigger(self.session,
            r"^[> ]*尚武堂找武师比武，fight wushi",
            "#wa 500;n;fight wushi", group="wmg", id="tri_jq_9",
        )
        self._triggers["tri_jq_10"] = SimpleTrigger(self.session,
            r"^[> ]*回到厢房睡一觉补充体力",
            "score", group="wmg", id="tri_jq_10",
        )
        # │ 性别：男性        姻缘：未遇良人      │ 师承：宋远桥                          │
        self._triggers["tri_jq_sex"] = self.tri_jq_sex = Trigger(self.session,
            patterns=(r"^[> ]*│\s*性别：(\S+)\s+"), 
            group="wmg_get_sex", id="tri_jq_sex",
            onSuccess=self.onTriggerSex,
        )
        self._triggers["tri_jq_11"] = SimpleTrigger(self.session,
            r"^[> ]*你气色恢复，虽然被武师打败了，仍有闯荡江湖，行侠仗义的雄心",
            "#wa 1000;w;ask you kunyi about 闯荡江湖", group="wmg", id="tri_jq_11",
        )
        # self._triggers["tri_jq_12"] = SimpleTrigger(self.session,
        #     r"^[> ]*到票号把钱都给取出来",
        #     "#2 s;open gate;s;e;qu 1gold", group="wmg", id="tri_jq_12",
        # )
        self._triggers["tri_jq_13"] = SimpleTrigger(self.session,
            r"^[> ]*使用localmaps命令查看票号的位置",
            "#py self.enableGroup('tri_jq_get_map', true);lm", group="wmg", id="tri_jq_13",
        )
        '''
        [42;1m[1;37m◆柳秀山庄地图◆[2;37;0m
        [46;1m[1;37m◆武当山地图－桃园◆[2;37;0m
        '''
        # 测试颜色触发 #test %copy
        self._triggers["tri_jq_get_map"] = Trigger(self.session, 
            patterns = r"\x1b\[42;1m\x1b\[1;37m◆\s*(\S.+)◆\x1b\[2;37;0m|^\x1b\[46;1m\x1b\[1;37m◆\s*(\S.+)◆\x1b\[2;37;0m",
            group="wmg", id="tri_jq_get_map",
            onSuccess = self.onTriggerGetMap,
            raw = True
        )
        self._triggers["tri_jq_15"] = SimpleTrigger(self.session,
            r"^[> ]*去药铺买药\(buy\s+yao\)",
            "w;s;s;ne;buy yao;#wa 1000;eat yao", group="wmg", id="tri_jq_15",
        )
        self._triggers["tri_jq_16"] = Trigger(self.session,
            r"^[> ]*你的伤治好了！快回到游庄主处，让他指导你闯荡江湖吧！",
            group="wmg", id="tri_jq_16",
            onSuccess = self.onTriggerGetMap,
        )
        self._triggers["tri_async1"] = Trigger(self.session,
            patterns = r"这是天(\S+)",
            group="wmg", id="tri_async1",
            onSuccess = self.onTriggerAwaitOpenDoor,
        )
        self._triggers["tri_async_test"] = SimpleCommand(self.session,
            r"^[> ]*测试结束", "say over",
            group="wmg", id="tri_async_test"
        )
        this.addTriggers(self._triggers)

    def _initCommands(self):
        self._commands["cmd_score"] = SimpleCommand(self.session, id="cmd_score",
            patterns="^score$",
            succ_tri=self.tri_jq_sex, group="wmg_get_sex",
            onSuccess=self.onCmdScore,
        )
        self.session.addCommands(self._commands)

    # ========================   CMDFn   ======================== #
    def onCmdScore(self):
        var1 = self.session.getVariables(("sex",))

    # ======================== TriggerFn ======================== #
    def _initTimers(self):
        self._timers["tm_test"] = Timer(
            self.session, timeout=2, 
            id="tm_test", group="mytim", 
            oneShot=True,
            onSuccess=self.onTimer
        )
        self.session.addTimers(self._timers)

    def onTimer(self, name, *args, **kwargs):
        self.session.info("执行1次打印本信息", "定时器测试")
    def status_window(self):
        formatted_list = list()

        async def abccc(mouse_event: MouseEvent):
            if mouse_event.event_type == MouseEventType.MOUSE_UP:
                self.session.info('点击事件')
                self._initTimers()
                # self.session.exec("inp")
        async def abccc2(mouse_event: MouseEvent):
            if mouse_event.event_type == MouseEventType.MOUSE_UP:
                self.session.info('点击事件2')
                self.session.enableGroup("mytim", False) 
                # self._timers["tm_test"].enabled = False

        formatted_list.append((Settings.styles["title"], "【角色】", functools.partial(abccc)))
        formatted_list.append((Settings.styles["title"], "【停止定时器】", functools.partial(abccc2)))
        return formatted_list

    def onTriggerAwaitOpenDoor(self, name, cmd, line, wildcards):
        # "sw;n;n;n;knock gate", #test 这是天青色
        ttt = this.setVariables(self.ttt, wildcards)
        #py {self.info("\x1b[1;36m这是天青色")}
        self.session.info('\x1b[1;36m{ttt}')
        # self.session.create_task(self.asyncOpenDoor)
    # async def asyncOpenDoor(self):
    #     self.session.writeline("sw;n;n;n;knock gate")
    #     while True:
    #         await asyncio.sleep(1)
    #         self.session.info('\x1b[1;36m=== 等待触发执行 ===')
    #         await self._triggers["tri_async_test"].triggered()
    #         self.session.warning("=== 触发结束 ===")
    #         break
            

    def onTriggerGetMap(self, name, line, wildcards):
        self.session.writeline("#wa 1000;s;s;open gate;s;e;#wa 1000;qu 1 gold")
        self.session.enableGroup('tri_jq_get_map', False)

    def onTriggerSex(self, name, line, wildcards):
        # 保存变量
        this = self.session
        this.setVariables(self.score, wildcards)
        sex = this.getVariables(("sex",))[0]
        if sex == "男性":
            this.writeline("say 男")
            this.writeline("w;sleep")
        else:
            this.writeline("e;sleep")
        this.enableGroup('wmg_get_sex', False)

    
    def onTriggerAsk(self, name, line, wildcards):
        this = self.session
        this.setVariables(self.youkunyiKey, wildcards)
        this.create_task(self.asyncAsk(this.getVariables(self.youkunyiKey)))
    async def asyncAsk(self, youkunyi):
        for i in youkunyi:
            await asyncio.sleep(1)
            self.session.info("ask youkunyi about " + i)