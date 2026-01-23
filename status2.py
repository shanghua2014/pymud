''' 
新手任务：打铁、抄书、分药 
注释为：*** 显示内容无意义，但必须存在
'''
import functools, asyncio, cn2an, sys, os, random
#导入当前文件的上层目录到
sys.path.append('..')
#加入当前目录
sys.path.append(os.getcwd())

from pymud import Alias, Trigger, SimpleCommand, SimpleTrigger, SimpleAlias, Timer
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType
from prompt_toolkit.formatted_text import to_formatted_text, HTML
from settings import Settings
from pkg_confirm import confirm
from pkg_tool import tool

# backPath = tool.Tool('#4 ne;#2 sw;w;n;#2 s;#2 u;d;#3 n;u').reversPath()
# print(backPath)

class Configuration:
    

    def __init__(self, session, *args, **kwargs):
        self.iseat = 0
        # 工作次数：每10次吃喝
        self.jobCount = 0
        self.jobTotal = 0
        self.jobExp = 0
        self.jobQn = 0
        # 工作种类：区分买包子的路径 (typePY:配药，typeDT:打铁)
        self.jobType = 'typeDT'
        self.chihe = 'drink shui dai;eat baozi'
        # 返回路径
        self.backPath = ''
        self.session = session
        self._aliases = {}
        self._triggers = {}
        # self._commands = {}
        self._timers = {}

        self._initAliases()
        self._initTriggers()
        # self._initCommands()
        self._initTimers()
        self.session.info('\x1b[1;36m=== 新手任务 ===')
        

    # 别名
    def _initAliases(self):
        self._aliases["alia_dt_job"] = SimpleAlias(self.session, 
            r"^dt$", "ask tie jiang about job", 
            group="newbie_job"
        )
        self._aliases["alia_py_job"] = SimpleAlias(self.session, 
            r"^py$", "ask yizhi about job", 
            group="newbie_job"
        )
        self._aliases["alia_ch_job"] = SimpleAlias(self.session, 
            r"^cs$", "ask zhu xi about job", 
            group="newbie_job"
        )
        self._aliases["alia_ld_job"] = SimpleAlias(self.session, 
            r"^ld$", "ask yao chun about liandan", 
            group="newbie_job"
        )
        self._aliases["alia_yc_job"] = SimpleAlias(self.session, 
            r"^yc$", "ask xiao tong about 药材", 
            group="newbie_job"
        )
        self.session.addAliases(self._aliases)

    # 触发
    def _initTriggers(self):
        this = self.session
        self._triggers["tri_py_1"] = SimpleTrigger(self.session,
            r"^平一指对你说道：好，你就帮我配药\(peiyao\)吧！喏，就这几味。|^平一指对你说道：让你干的活你干完了么？",
            "#wa 2000;peiyao",
            group="tri_py", id="tri_py_1"
        )
        self._triggers["tri_py_2"] = Trigger(self.session,
            r"^平一指看了你配的药，点头道：不错，不错！这是给你的报酬！",
            group="tri_py", id="tri_py_2",
            onSuccess = self._onTriggerStartJob
        )
        self._triggers["tri_py_3"] = Trigger(self.session,
            r"^平一指对你说道：让你干这活，也太屈就你了吧。|^平一指对你说道：我这已经有.+在干活了，你等等吧。",
            group="tri_py", id="tri_py_3",
            onSuccess = self._onTriggerPYOver
        )
        self._triggers["tri_ch_1"] = SimpleTrigger(self.session,
            r"^朱熹对你说道：.+\(copy\)",
            "copy",
            group="tri_cs", id="tri_ch_1"
        )
        self._triggers["tri_ch_2"] = SimpleTrigger(self.session,
            r"^你把书籍抄好，将纸上墨吹干，装订成册，递给朱熹。",
            "#wa 2000;cs",
            group="tri_cs", id="tri_ch_2"
        )
        self._triggers["tri_ch_3"] = Trigger(self.session,
            r"^朱熹对你说道：大侠你也来抄书？真是屈就您了，慢走啊！",
            group="tri_cs", id="tri_ch_3",
            onSuccess = self._onTriggerCSOver
        )
        self._triggers["tri_dt_1"] = SimpleTrigger(self.session,
            r"^铁匠对你说道：.+\(dapi\)",
            "#wa 1000;dapi",
            group="tri_dt", id="tri_dt_1"
        )
        self._triggers["tri_dt_1_1"] = SimpleTrigger(self.session,
            r"^铁匠对你说道：.+\(cuihuo\)",
            "#wa 1000;cuihuo",
            group="tri_dt", id="tri_dt_1_1"
        )
        self._triggers["tri_dt_1_2"] = SimpleTrigger(self.session,
            r"^铁匠对你说道：.+\(gu\)",
            "#wa 1000;gu",
            group="tri_dt", id="tri_dt_1_2"
        )
        self._triggers["tri_dt_2"] = Trigger(self.session,
            r"^铁匠对你道：这是给你的工钱。",
            group="tri_dt", id="tri_dt_2",
            onSuccess = self._onTriggerStartJob
        )
        self._triggers["tri_dt_2_1"] = SimpleTrigger(self.session,
            r"^铁匠对你说道：你还是歇会儿吧！要是出了人命我可承担不起。",
            "#wa 3000;dt",
            group="tri_dt", id="tri_dt_2_1",
        )
        self._triggers["tri_dt_3"] = Trigger(self.session,
            r"^铁匠对你说道：让您老干这个未免屈尊了吧？",
            group="tri_dt", id="tri_dt_3",
            onSuccess = self._onTriggerDTOver
        )
        self._triggers["tri_dt_chihe"] = Trigger(self.session,
            r"^.+你身上没有这样东西，附近也没有。",
            group="tri_job_chihe", id="tri_dt_chihe",
            onSuccess = self._onTriggerBuyBaozi
        )
        self._triggers["tri_dt_chihe2"] = Trigger(self.session,
            r"^你从店小二那里买下了一个包子。",
            group="tri_job_chihe", id="tri_dt_chihe2",
            onSuccess = self._onTriggerBackJob
        )
        self._triggers["tri_status1"] = Trigger(self.session,
            r"^通过这次锻炼，你获得了(.+)点经验、(.+)点潜能、",
            group="tri_status", id="tri_status1",
            onSuccess = self._onTriggerStatus
        )
        self._triggers["tri_ld_0"] = SimpleTrigger(self.session,
            r"^姚春对你点了点头，说道：炼丹是考验人的定力修为，心不静则事不成，你去向童子询问「药材」吧。",
            "s;yc",
            group="tri_ld", id="tri_ld_0"
        )
        self._triggers["tri_ld_1"] = Trigger(self.session,
            r"^小童对你说道：好吧，那你去城西的林子里挖几样新鲜的草药来。|^小童对你说道：叫你去采药，还呆在这干嘛！",
            group="tri_ld", id="tri_ld_1",
            onSuccess = self._onTriggerYaocai
        )
        self._triggers["tri_ld_2"] = Trigger(self.session,
            r"^你找了半天，终于发现其中一株草苗与其它的草略有不同，",
            group="tri_ld", id="tri_ld_2",
            onSuccess = self._onTriggerYaocaiB
        )
        self._triggers["tri_ld_3"] = Trigger(self.session,
            r"^.+\[(.+)\]说道：嘿嘿，今天真不巧，让你遇见了本爷，本爷今天要财要命！",
            group="tri_ld", id="tri_ld_3",
            onSuccess = self._onTriggerYaocai2
        )
        self._triggers["tri_ld_4"] = Trigger(self.session,
            patterns=(
                r"^你拿出不知名草药\(cao\s*yao\)给小童。",
                r"^小童\[Xiao\s*tong\]说道：好吧，让我来给你加工。"
            ),
            # 'n;n;#wa 1000;liandan',
            group="tri_ld", id="tri_ld_4",
        )
        self._triggers["tri_ld_5"] = Trigger(self.session,
            r"^正当你昏昏然的时候，一阵刺鼻的气味从炉中冲出，你急忙开炉取药，结果被弄得个灰头土脸。",
            group="tri_ld", id="tri_ld_5",
            onSuccess = self._onTriggerYaocai3
        )
        
        this.status_maker = self.status_window_with_progress_bars

        this.addTriggers(self._triggers)

    # 定时器
    def _initTimers(self):
        self._timers["tim_food"] = self.timerFood = Timer(
            self.session, timeout=6, enabled=False,
            id="tim_food", group="timers",
            onSuccess = self.onTimerFood
        )
        self.session.addTimers(self._timers)


    ''' ========================================== '''
    ''' ==           Timers 自定义函数           == '''
    ''' ========================================== '''
    def onTimerFood(self, name, *args, **kwargs):
        self.timerFood.enabled = False
        self._goOnJob()
        self.jobCount = 0


    ''' ========================================== '''
    ''' ==          Trigger 自定义函数           == '''
    ''' ========================================== '''

    # 采药：返回
    def _onTriggerYaocaiB(self, name, line, wildcards):
        self.session.create_task(self._asyncYaocaiB(wildcards))
    async def _asyncYaocaiB(self, wildcards):
        self.session.writeline(self.backPath)
        asyncio.sleep(1.5)
        self.session.writeline('give cao yao to xiao tong')
        self.backPath = ''
    # 采药3：炼丹失败，重新采药
    def _onTriggerYaocai3(self, name, line, wildcards):
        self.session.writeline('s;s')
        self._onTriggerYaocai(self, name, line, wildcards)
    # 采药2：遇劫匪
    def _onTriggerYaocai2(self, name, line, wildcards):
        self.session.exec(f'kill {wildcards[0]}')
    # 采药
    def _onTriggerYaocai(self, name, line, wildcards):
        num = random.randrange(0,2,1)
        step_0 = random.randrange(1,3,1)
        dirs_0 = ['n;','s;']
        dirs_1 = dirs_0[num]
        goPath = '#2 w;n;#4 w;#{step_0} {dirs_1}'
        self.backPath = tool.Tool(goPath).reversPath()
        self.session.exec(goPath)

    # 结束：抄书任务 -> 炼丹
    def _onTriggerCSOver(self, name, line, wildcards):
        self._triggersSwitch('tri_ld')
        self.session.create_task(self._asyncLiandan(wildcards))
    async def _asyncLiandan(self, wildcards):
        self.session.writeline('s;fly bj')
        await asyncio.sleep(2)
        self.session.exec('s;#4 w')
        await asyncio.sleep(1)
        self.session.exec('#5 s;e;e;n')
        await asyncio.sleep(2)
        self.session.exec('ld')
    # 结束：打铁任务 -> 配药
    def _onTriggerDTOver(self, name, line, wildcards):
        self._triggersSwitch('tri_py')
        self.session.writeline('n;n')
        self.session.exec('py')
    # 结束：配药任务 -> 抄书
    def _onTriggerPYOver(self, name, line, wildcards):
        self._triggersSwitch('tri_cs')
        self.session.writeline('s;w;n')
        self.session.exec('cs')
    # 工作：配药、打铁
    def _onTriggerStartJob(self, name, line, wildcards):
        self.jobCount += 1
        self.jobTotal += 1
        self.session.info(f"\x1b[1;44m\x1b[1;37m完成\x1b[1;33m\x1b[1;4m{self.jobCount}\x1b[1;24m\x1b[1;44m\x1b[1;37m次\x1b[1;31m√")
        self.session.create_task(self._asyncJob(wildcards))
    async def _asyncJob(self, wildcards):
        self.iseat = self.session.getVariable('iseat')
        if self.jobCount>=5 and int(self.iseat)>=1:
            await asyncio.sleep(2)
            self.session.writeline(self.chihe)
            self.timerFood.enabled = True
        self._goOnJob()
    # 开始：工作
    def _startJob(self, name, line, wildcards):
        self._triggersSwitch('tri_dt')
        if self.iseat==0 or not self.iseat:
            self.session.info('假')
            self.session.exec('w;s;e;e;s;dt')
        else:
            self.session.info('真')
        self.session.exec('w;n;e;#wa 2000;buy shui dai;#wa 2000;buy baozi')
    # 状态栏
    def status_window(self):
            formatted_list = list()
            def dtFn(mouse_event: MouseEvent):
                if mouse_event.event_type == MouseEventType.MOUSE_UP:
                    # self.session.exec("inp")
                    self.session.exec("dt")
                    self._triggersSwitch("tri_dt")
                    self.jobType = 'typeDT'
            def pyFn(mouse_event: MouseEvent):
                if mouse_event.event_type == MouseEventType.MOUSE_UP:
                    self.session.exec("py")
                    self._triggersSwitch("tri_py")
                    self.jobType = 'typePY'
            def stopFn(mouse_event: MouseEvent):
                if mouse_event.event_type == MouseEventType.MOUSE_UP:
                    self.session.info('停下')
                    self._triggersSwitch('')
            async def startJobFn(mouse_event: MouseEvent):
                if mouse_event.event_type == MouseEventType.MOUSE_UP:
                    self.session.info('【开始干活】')
                    self.iseat = await confirm.CmdDialogInput.execute(self,'input -chihe')
                    # self.session.setVariable('iseat', iseat)
                    self._startJob(1,2,[3]) # ***
            

            # 方案1：使用空格实现类似相对定位的偏移效果
            # 在按钮前添加空格来模拟相对定位的偏移
            formatted_list.append(("", "    "))  # 向右偏移4个空格
            # formatted_list.append(("bg:#00ff00 italic", "【开始干活】", functools.partial(startJobFn)))
            formatted_list.append(("", "  "))  # 按钮间距
            formatted_list.append(("bg:#ff9900", "【打铁】", functools.partial(dtFn)))
            formatted_list.append(("", "  "))
            formatted_list.append(("bg:#99cc00", "【配药】", functools.partial(pyFn)))
            formatted_list.append(("", "  "))
            formatted_list.append(("bg:#ff3333", "【停止所有机器】", functools.partial(stopFn)))
            
            # 方案2：使用换行和缩进实现垂直相对定位
            formatted_list.append(("", "\n"))
            formatted_list.append(("", "  "))  # 缩进2个空格
            formatted_list.append(("fg:yellow", f"本次连接统计：工作完成次数{self.jobTotal}"))
            formatted_list.append(("", "\n"))
            formatted_list.append(("", "  "))  # 缩进2个空格
            formatted_list.append(("fg:cyan", f"获得经验{self.jobExp}，获得潜能{self.jobQn}"))
            
            # 方案3：使用边框和背景色模拟相对定位的视觉效果
            formatted_list.append(("", "\n\n"))
            formatted_list.append(("bg:#333333 fg:white", "=" * 50))  # 分隔线
            formatted_list.append(("", "\n"))
            formatted_list.append(("bg:#222222 fg:yellow", "  工作状态面板  "))  # 标题栏
            formatted_list.append(("", "\n"))
            formatted_list.append(("bg:#333333 fg:white", "=" * 50))
            formatted_list.append(("", "\n"))

            # 方案4：使用多行布局实现复杂的相对定位效果
            # 第一行：主要按钮
            formatted_list.append(("", "┌─"))
            # formatted_list.append(("bg:#00ff00 bold", "【开始干活】", functools.partial(startJobFn)))
            formatted_list.append(("", "─┐"))
            formatted_list.append(("", "\n"))
            
            # 第二行：功能按钮（相对于第一行偏移）
            formatted_list.append(("", "│ "))
            formatted_list.append(("bg:#ff9900", "【打铁】", functools.partial(dtFn)))
            formatted_list.append(("", " │ "))
            formatted_list.append(("bg:#99cc00", "【配药】", functools.partial(pyFn)))
            formatted_list.append(("", " │ "))
            formatted_list.append(("bg:#ff3333", "【停止】", functools.partial(stopFn)))
            formatted_list.append(("", " │"))
            formatted_list.append(("", "\n"))
            
            # 第三行：统计信息（相对于第二行偏移）
            formatted_list.append(("", "└─"))
            formatted_list.append(("fg:yellow", f"统计：{self.jobTotal}次"))
            formatted_list.append(("", "─┘"))
            formatted_list.append(("", "\n"))

            return formatted_list

    # 买包子
    def _onTriggerBuyBaozi(self, name, line, wildcards):
        self._triggersSwitch('')
        this = self.session
        if self.jobType == 'typePY':
            this.writeline('s')
        else:
            this.writeline('n')
        this.writeline('w;w;n;n;e;buy baozi')

    # 回去工作
    def _onTriggerBackJob(self, name, line, wildcards):
        this = self.session
        this.writeline(self.chihe)
        this.writeline('#wa 1000;w;s;s;e;e')
        if self.jobType == 'typePY':
            self._triggersSwitch('tri_py')
            this.writeline('n')
            this.exec('py')
        else:
            self._triggersSwitch('tri_dt')
            this.writeline('s')
            this.exec('dt')

    ''' ========================================== '''
    ''' ==                公共函数               == '''
    ''' ========================================== '''
    # 统计数据
    def _onTriggerStatus(self, name, line, wildcards):
        self.jobExp += int(cn2an.cn2an(wildcards[0]))
        self.jobQn += int(cn2an.cn2an(wildcards[1]))
    # 继续干活
    def _goOnJob(self):
        if self.jobType=='typeDT':
            self.session.exec("#wa 1000;dt")
        else:
            self.session.exec("#wa 1000;py")
    # 切换触发
    def _triggersSwitch(self, id):
        this = self.session
        self.jobCount = 0
        this.enableGroup("tri_py", False)
        this.enableGroup("tri_cs", False)
        this.enableGroup("tri_dt", False)
        this.enableGroup("tri_ld", False)
        self.timerFood.enabled = False
        if id:
            this.enableGroup(id, True)

    def create_progress_bar_styles(self, current, maximum, barlength=20):
        """创建多种进度条样式
        参数:
            current: 当前值
            maximum: 最大值
            barlength: 进度条长度
        """
        percentage = min(current / maximum, 1.0) if maximum > 0 else 0
        filled_length = int(round(barlength * percentage))
        remaining_length = barlength - filled_length
        
        progress_bars = {}
        
        # 样式1：经典方块进度条 - 使用更小的字符
        progress_bars["classic"] = [
            ("fg:white bg:#0066cc", "■" * filled_length),  # 使用■代替█
            ("fg:white bg:#333333", "□" * remaining_length),  # 使用□代替░
            ("fg:yellow", f" {int(percentage*100)}%")
        ]
        
        # 样式2：渐变色彩进度条
        if filled_length > 0:
            # 根据进度改变颜色：红->橙->黄->绿
            if percentage < 0.25:
                color = "fg:red"
            elif percentage < 0.5:
                color = "fg:#ff6600"
            elif percentage < 0.75:
                color = "fg:yellow"
            else:
                color = "fg:green"
            progress_bars["gradient"] = [
                (color, "■" * filled_length),  # 使用■代替█
                ("fg:#666666", "□" * remaining_length),  # 使用□代替░
                ("fg:cyan", f" {int(percentage*100)}%")
            ]
        else:
            progress_bars["gradient"] = [("fg:#666666", "□" * barlength), ("fg:cyan", " 0%")]
        
        # 样式3：ASCII艺术进度条
        progress_bars["ascii"] = [
            ("fg:green bold", "["),
            ("fg:green", "=" * filled_length),
            ("fg:yellow", ">" if filled_length < barlength else ""),
            ("fg:gray", "-" * max(0, remaining_length - 1)),
            ("fg:green bold", "]"),
            ("fg:white", f" {int(percentage*100)}%")
        ]
        
        # 样式4：圆角进度条 - 使用更小的字符
        progress_bars["rounded"] = [
            ("fg:#00ff00", "["),  # 使用[代替▕
            ("fg:#00ff00 bg:#00aa00", "■" * filled_length),  # 使用■代替█
            ("fg:#666666 bg:#333333", "□" * remaining_length),  # 使用□代替░
            ("fg:#00ff00", "]"),  # 使用]代替▏
            ("fg:yellow", f" {int(percentage*100)}%")
        ]
        
        # 样式5：多状态进度条（类似游戏血条）- 使用更小的字符
        if filled_length > 0:
            # 根据进度显示不同颜色段
            if percentage < 0.3:
                segments = [("fg:red", "■" * filled_length)]  # 使用■代替█
            elif percentage < 0.7:
                segments = [("fg:yellow", "■" * filled_length)]  # 使用■代替█
            else:
                segments = [("fg:green", "■" * filled_length)]  # 使用■代替█
        else:
            segments = []
        
        progress_bars["multistate"] = segments + [
            ("fg:#444444", "□" * remaining_length),  # 使用□代替▒
            ("fg:white", f" {int(percentage*100)}%")
        ]
        
        # 样式6：简约线条进度条
        progress_bars["minimal"] = [
            ("fg:blue", "|"),
            ("fg:cyan", "─" * filled_length),
            ("fg:gray", "·" * remaining_length),
            ("fg:blue", "|"),
            ("fg:white", f" {int(percentage*100)}%")
        ]
        
        return progress_bars

    

    def status_window_with_progress_bars(self):
        def dtFn(mouse_event: MouseEvent):
            if mouse_event.event_type == MouseEventType.MOUSE_UP:
                # self.session.exec("inp")
                self.session.exec("dt")
                self._triggersSwitch("tri_dt")
                self.jobType = 'typeDT'
        def pyFn(mouse_event: MouseEvent):
            if mouse_event.event_type == MouseEventType.MOUSE_UP:
                self.session.exec("py")
                self._triggersSwitch("tri_py")
                self.jobType = 'typePY'
        def stopFn(mouse_event: MouseEvent):
            if mouse_event.event_type == MouseEventType.MOUSE_UP:
                self.session.info('停下')
                self._triggersSwitch('')
        async def startJobFn(mouse_event: MouseEvent):
            if mouse_event.event_type == MouseEventType.MOUSE_UP:
                self.session.info('【开始干活】')
                self.iseat = await confirm.CmdDialogInput.execute(self,'input -chihe')
                # self.session.setVariable('iseat', iseat)
                self._startJob(1,2,[3]) # ***
        """包含多种进度条样式的状态窗口"""
        formatted_list = list()
        
        # 添加按钮
        formatted_list.append(("bg:#00ff00 italic", "【开始干活】", functools.partial(startJobFn)))
        formatted_list.append(("", "  "))
        formatted_list.append(("bg:#ff9900", "【打铁】", functools.partial(dtFn)))
        formatted_list.append(("", "  "))
        formatted_list.append(("bg:#99cc00", "【配药】", functools.partial(pyFn)))
        formatted_list.append(("", "  "))
        formatted_list.append(("bg:#ff3333", "【停止】", functools.partial(stopFn)))
        
        formatted_list.append(("", "\n\n"))
        
        
        # 新的固定50%进度设置
        work_current = 8  # 固定当前值为5
        work_maximum = 10  # 固定最大值为10，这样进度就是50%
        # 显示各种进度条样式（全部显示50%进度）
        progress_styles = self.create_progress_bar_styles(work_current, work_maximum, 15)
        
        # 样式1：经典方块
        # formatted_list.append(("fg:yellow", "经典方块(50%): "))
        # formatted_list.extend(progress_styles["classic"])
        # formatted_list.append(("", "\n"))
        
        # 样式2：渐变色彩
        # formatted_list.append(("fg:yellow", "渐变色彩(50%): "))
        # formatted_list.extend(progress_styles["gradient"])
        # formatted_list.append(("", "\n"))
        
        # 样式3：ASCII艺术
        # formatted_list.append(("fg:yellow", "ASCII艺术(50%): "))
        # formatted_list.extend(progress_styles["ascii"])
        # formatted_list.append(("", "\n"))
        
        # 样式4：圆角进度条
        # formatted_list.append(("fg:yellow", "圆角进度(50%): "))
        # formatted_list.extend(progress_styles["rounded"])
        # formatted_list.append(("", "\n"))
        
        # 样式5：多状态进度条
        # formatted_list.append(("fg:yellow", "多状态条(50%): "))
        formatted_list.extend(progress_styles["multistate"])
        # formatted_list.append(("", "\n"))
        
        # 样式6：简约线条
        # formatted_list.append(("fg:yellow", "简约线条(50%): "))
        # formatted_list.extend(progress_styles["minimal"])
        # formatted_list.append(("", "\n\n"))
        
        # 统计信息（显示固定50%进度）
        formatted_list.append(("fg:cyan", f"工作进度: {work_current}/{work_maximum} (固定50%)"))
        formatted_list.append(("", "\n"))
        formatted_list.append(("fg:magenta", f"总完成: {self.jobTotal} 次"))
        formatted_list.append(("", "\n"))
        formatted_list.append(("fg:green", f"经验: {self.jobExp} 潜能: {self.jobQn}"))
        
        return formatted_list
