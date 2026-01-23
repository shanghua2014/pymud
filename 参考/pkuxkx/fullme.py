import webbrowser
from pymud import Alias, Trigger, SimpleCommand, Timer, SimpleTrigger, SimpleAlias

class Configuration:


    def __init__(self, session, *args, **kwargs):
        super().__init__()
        self.session = session
        self._triggers = {}
        self._commands = {}
        self._initTriggers()
        self._initCommands()


    def _initTriggers(self):
        self._triggers["tri_webpage"] = self.tri_webpage = Trigger(
            self.session,
            id="tri_webpage",
            patterns=r"^http://fullme.pkuxkx.net/robot.php.+$",
            group="sys",
            onSuccess=self.ontri_webpage,
        )
        self._triggers["tri_hp"] = self.tri_hp = Trigger(
            self.session,
            id="tri_hp",
            patterns=(
                r"^[> ]*#(\d+.?\d*[KM]?),(\d+),(\d+),(\d+),(\d+),(\d+)$",
                r"^[> ]*#(\d+),(\d+),(\d+),(\d+),(\d+),(\d+)$",
                r"^[> ]*#(\d+),(\d+),(-?\d+),(-?\d+),(\d+),(\d+)$",
            ),
            group="sys",
            onSuccess=self.ontri_hpbrief,
        )
        self.session.addTriggers(self._triggers)
    def _initCommands(self):
        self._commands["cmd_hpbrief"] = self.cmd_hpbrief = SimpleCommand(
            self.session,
            id="cmd_hpbrief",
            patterns="^hpbrief$",
            succ_tri=self.tri_hp,
            group="status",
            onSuccess=self.oncmd_hpbrief,
        )
        self.session.addCommands(self._commands)

    def ontri_webpage(self, name, line, wildcards):
        webbrowser.open(line)
    def ontri_hpbrief(self, name, line, wildcards):
        self.session.setVariables(self.HP_KEYS, wildcards)
    def oncmd_hpbrief(self, name, cmd, line, wildcards):
        # 为了节省服务器资源，应使用hpbrief来代替hp指令
        # 但是hpbrief指令的数据看起来太麻烦，所以将hpbrief的一串数字输出成类似hp的样式
        # ┌───个人状态────────────────────┬─────────────────────────────┐
        # │【精神】 1502    / 1502     [100%]    │【精力】 4002    / 4002    (+   0)    │
        # │【气血】 2500    / 2500     [100%]    │【内力】 5324    / 5458    (+   0)    │
        # │【真气】 0       / 0        [  0%]    │【禅定】 101%               [正常]    │
        # │【食物】 222     / 400      [缺食]    │【潜能】 36,955                       │
        # │【饮水】 247     / 400      [缺水]    │【经验】 2,341,005                    │
        # ├─────────────────────────────┴─────────────────────────────┤
        # │【状态】 健康、怒                                                             │
        # └────────────────────────────────────────────北大侠客行────────┘
        var1 = self.session.getVariables(
            ("jing", "effjing", "maxjing", "jingli", "maxjingli")
        )
        line0 = ""
        line1 = "【精神】 {0:<8} [{5:3.0f}%] / {1:<8} [{2:3.0f}%]  |【精力】 {3:<8} / {4:<8} [{6:3.0f}%]".format(
            var1[0],
            var1[1],
            100 * float(var1[1]) / float(var1[2]),
            var1[3],
            var1[4],
            100 * float(var1[0]) / float(var1[2]),
            100 * float(var1[3]) / float(var1[4]),
        )
        var2 = self.session.getVariables(("qi", "effqi", "maxqi", "neili", "maxneili"))
        line2 = "【气血】 {0:<8} [{5:3.0f}%] / {1:<8} [{2:3.0f}%]  |【内力】 {3:<8} / {4:<8} [{6:3.0f}%]".format(
            var2[0],
            var2[1],
            100 * float(var2[1]) / float(var2[2]),
            var2[3],
            var2[4],
            100 * float(var2[0]) / float(var2[2]),
            100 * float(var2[3]) / float(var2[4]),
        )
        var3 = self.session.getVariables(
            ("food", "water", "exp", "pot", "fighting", "busy")
        )
        line3 = "【食物】 {0:<4} 【饮水】{1:<4} 【经验】{2:<9} 【潜能】{3:<10}【{4}】【{5}】".format(
            var3[0],
            var3[1],
            var3[2],
            var3[3],
            "未战斗" if var3[4] == "0" else "战斗中",
            "不忙" if var3[5] == "0" else "忙",
        )
        self.session.info(line0, "状态")
        self.session.info(line1, "状态")
        self.session.info(line2, "状态")
        self.session.info(line3, "状态")
