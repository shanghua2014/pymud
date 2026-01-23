
import re, functools, time, webbrowser
from wcwidth import wcwidth, wcswidth
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType
from prompt_toolkit.formatted_text import ANSI, HTML, to_formatted_text
from pymud import Settings, IConfig, Trigger, SimpleTrigger, GMCPTrigger, Alias, SimpleAlias, Session, DotDict, Timer

from .common import REGX_ROOMNAME, REGX_ANTIROBOT, REGX_HPBRIEF, AUTO_GETS, DIRS_ABBR, HP_KEYS, JIAN_XIN_JU, SPECIAL, word2number

class CommonConfig(IConfig):
    def __init__(self, session: Session, *args, **kwargs):
        self.session = session

        session.status_maker = self.status_window
        session.event_connected = functools.partial(self.session_event, "connected")
        session.event_disconnected = functools.partial(self.session_event, "disconnected")

        self.session.setVariable("buff", list())
        self.session.setVariable('enemies', DotDict())

        self._objs = [
            Trigger(session, REGX_ROOMNAME, id = "tri_room", priority = 50, keepEval = True, onSuccess = self.ontri_roomname),
            Trigger(self.session, id = 'tri_webpage', patterns = REGX_ANTIROBOT, group = "sys", onSuccess = self.ontri_webpage),
            Trigger(self.session, id = 'tri_hpbrief', patterns = REGX_HPBRIEF, group = "sys", onSuccess = self.ontri_hpbrief),
            Trigger(self.session, id = 'tri_fullme',  patterns = r'^[> ]*也许是上天垂青于你的勤奋和努力吧，一个小时之内你不用担心被判为机器人。', group = "sys", onSuccess = self.ontri_fullme),
            Trigger(self.session, id = "tri_dead",    patterns = r"^[> ]*你死了。$", group = "sys", onSuccess = self.ontri_dead),
            Trigger(self.session ,r'^[> ]*.+记完帐，点了点头：“您在敝商号现有(\S+)。”', onSuccess = self.ontri_cunkuan, group = "sys", id = 'tri_cunqian'),
            SimpleTrigger(self.session ,r'^[> ]*从.+身上.+[◎☆★].+', "pack gem", group = "sys", id = 'tri_gem'),
            SimpleTrigger(self.session ,r'^[> ]*你捡起一颗.+[◎☆★].+', "pack gem", group = "sys", id = 'tri_gem2'),
            SimpleTrigger(self.session ,r'^[> ]*你从\S+身上搜出一颗.+[◎☆★].+', "pack gem", group = "sys", id = 'tri_gem3'),
            Trigger(self.session ,r'^目前权限：\(player\)', onSuccess = functools.partial(self.ontri_login, relogin = False), group = "sys", id = "tri_login"),
            Trigger(self.session, r'^重新连线完毕。', onSuccess = functools.partial(self.ontri_login, relogin = True), group = "sys", id = "tri_relogin"),
            SimpleTrigger(self.session, r"^[> ]*你的GMCP:Status频道已经是打开的。|^[> ]*你打开了GMCP:Status频道。", "#var status_type GMCP", id = "tri_gmcp_status_on"),
            SimpleTrigger(self.session, r"^[> ]*你的GMCP:Status频道已经是关闭的。|^[> ]*你关闭了GMCP:Status频道。", "#var status_type hpbrief", id = "tri_gmcp_status_off"),
            SimpleTrigger(self.session, r"^[> ]*你已经在使用GMCP接收状态信息，如果要使用本命令查看状态，请先输入", "#var status_type GMCP", id = "tri_gmcp_status_on2"),
            
            Alias(self.session, r"^gp(\d+)?\s(.+)$", id = "ali_get", onSuccess = self.onali_getfromcorpse),
            SimpleAlias(self.session, r"^cb\s(\S+)$", "#3 get %1 from @gembox;#wa 250;combine gem;#wa 250;pack gem", id = "ali_combine"),

            GMCPTrigger(self.session, "GMCP.Status", group = "sys", onSuccess = self.ongmcp_status),
            GMCPTrigger(self.session, "GMCP.Buff", group = "sys", onSuccess = self.ongmcp_buff),
            

            #Trigger(session, r"^[> ]*==\s*未完继续.+", id = "tri_more", onSuccess = lambda id, line, wildcards: self.session.writeline("xixi")),
            #Timer(self.session, id = "tm_system", timeout = 1, group = "sys", enabled = True, onSuccess = self.ontimer_system)
        ]

        for id, match in AUTO_GETS.items():
            tri_id = f"auto_{id}"
            self._objs.append(SimpleTrigger(self.session, patterns = match, code = f"get {id}", id = tri_id, enabled = False, group = "autoget"))

    def __unload__(self):
        self.session.delObjects(self._objs)

    def create_status_bar(self, current, effective, maximum, barlength = 20, barstyle = "—"):
        barline = list()
        stylewidth = wcswidth(barstyle)
        filled_length = int(round(barlength * current / maximum / stylewidth))
        # 计算有效健康值部分的长度
        effective_length = int(round(barlength * effective / maximum / stylewidth))

        # 计算剩余部分长度
        remaining_length = barlength - effective_length

        # 构造健康条
        barline.append(("fg:lightcyan", barstyle * filled_length))
        barline.append(("fg:yellow", barstyle * (effective_length - filled_length)))
        barline.append(("fg:red", barstyle * remaining_length))

        return barline

    def status_window(self):
        try:
            formatted_list = list()

            ins_loc = self.session.getVariable("ins_loc", None)
            tm_locs = self.session.getVariable("tm_locs", None)
            ins = False
            if isinstance(ins_loc, dict) and (len(ins_loc) >= 1):
                ins = True
                loc = ins_loc

            elif isinstance(tm_locs, list) and (len(tm_locs) == 1):
                ins = True
                loc = tm_locs[0]

            # line 0. hp bar
            jing = self.session.getVariable("jing", 0)
            effjing = self.session.getVariable("eff_jing", 0)
            maxjing = self.session.getVariable("max_jing", 0)
            jingli = self.session.getVariable("jingli", 0)
            maxjingli = self.session.getVariable("max_jingli", 0)
            qi = self.session.getVariable("qi", 0)
            effqi = self.session.getVariable("eff_qi", 0)
            maxqi = self.session.getVariable("max_qi", 0)
            neili = self.session.getVariable("neili", 0)
            maxneili = self.session.getVariable("max_neili", 0)

            barstyle = "━"
            screenwidth = self.session.application.get_width()
            barlength = screenwidth // 2 - 1
            span = screenwidth - 2 * barlength # - 4 * wcswidth("‖")
            qi_bar = self.create_status_bar(qi, effqi, maxqi, barlength, barstyle)
            jing_bar = self.create_status_bar(jing, effjing, maxjing, barlength, barstyle)
            #formatted_list.append(("", barstyle * (leftmargin - 2)))
            #formatted_list.append(("", "‖"))
            formatted_list.extend(qi_bar)
            #formatted_list.append(("", "‖"))
            formatted_list.append(("", " " * span))
            #formatted_list.append(("", "‖"))
            formatted_list.extend(jing_bar)
            #formatted_list.append(("", "‖"))

            formatted_list.append(("", "\n"))

            # line 1. char, menpai, deposit, food, water, exp, pot
            formatted_list.append((Settings.styles["title"], "【角色】"))
            formatted_list.append((Settings.styles["value"], "{0}({1})".format(self.session.getVariable('name'), self.session.getVariable('id'))))
            formatted_list.append(("", " "))

            # fullme time
            fullme = int(self.session.getVariable('%fullme', 0))
            delta = time.time() - fullme
            formatted_list.append((Settings.styles["title"], "【FULLME】"))
            if delta < 30 * 60:
                style = Settings.styles["value"]
            elif delta < 60 * 60:
                style = Settings.styles["value.worse"]
            else:
                style = Settings.styles["value.worst"]
            if fullme == 0:
                formatted_list.append((Settings.styles["value.worst"], "从未"))
            else:
                formatted_list.append((style, "{}".format(int(delta // 60))))
            formatted_list.append(("", " "))

            
            formatted_list.append((Settings.styles["title"], "【食物】"))
            
            food = int(self.session.getVariable('food', '0'))
            max_food = self.session.getVariable('max_food', 350)
            if food < 100:
                style = Settings.styles["value.worst"]
            elif food < 200:
                style = Settings.styles["value.worse"]
            elif food < max_food:
                style = Settings.styles["value"]
            else:
                style = Settings.styles["value.better"]

            formatted_list.append((style, "{}".format(food)))
            formatted_list.append(("", " "))

            formatted_list.append((Settings.styles["title"], "【饮水】"))
            water = int(self.session.getVariable('water', '0'))
            max_water = self.session.getVariable('max_water', 350)
            if water < 100:
                style = Settings.styles["value.worst"]
            elif water < 200:
                style = Settings.styles["value.worse"]
            elif water < max_water:
                style = Settings.styles["value"]
            else:
                style = Settings.styles["value.better"]
            formatted_list.append((style, "{}".format(water)))
            formatted_list.append(("", " "))
            formatted_list.append((Settings.styles["title"], "【经验】"))
            formatted_list.append((Settings.styles["value"], "{}".format(self.session.getVariable('combat_exp'))))
            formatted_list.append(("", " "))
            formatted_list.append((Settings.styles["title"], "【潜能】"))
            formatted_list.append((Settings.styles["value"], "{}".format(self.session.getVariable('potential'))))
            formatted_list.append(("", " "))

            formatted_list.append((Settings.styles["title"], "【门派】"))
            formatted_list.append((Settings.styles["value"], "{}".format(self.session.getVariable('family/family_name'))))
            formatted_list.append(("", " "))
            formatted_list.append((Settings.styles["title"], "【存款】"))
            formatted_list.append((Settings.styles["value"], "{}".format(self.session.getVariable('deposit'))))
            formatted_list.append(("", " "))
            
            # line 2. hp
            #(jing, effjing, maxjing, jingli, maxjingli, qi, effqi, maxqi, neili, maxneili) = self.session.getVariables(("jing", "eff_jing", "max_jing", "jingli", "max_jingli", "qi", "eff_qi", "max_qi", "neili", "max_neili"))
            jing = self.session.getVariable("jing", 0)
            effjing = self.session.getVariable("eff_jing", 0)
            maxjing = self.session.getVariable("max_jing", 0)
            jingli = self.session.getVariable("jingli", 0)
            maxjingli = self.session.getVariable("max_jingli", 0)
            qi = self.session.getVariable("qi", 0)
            effqi = self.session.getVariable("eff_qi", 0)
            maxqi = self.session.getVariable("max_qi", 0)
            neili = self.session.getVariable("neili", 0)
            maxneili = self.session.getVariable("max_neili", 0)
            #if jing and effjing and maxjing and effqi and maxqi and qi and jingli and maxjingli and neili and maxneili:
            # a new-line
            formatted_list.append(("", "\n"))

            formatted_list.append((Settings.styles["title"], "【精神】"))
            if int(effjing) < int(maxjing):
                style = Settings.styles["value.worst"]
            elif int(jing) < 0.8 * int(effjing):
                style = Settings.styles["value.worse"]
            else:
                style = Settings.styles["value"]
            
            if maxjing == 0: 
                pct1 = pct2 = 0
            else:
                pct1 = 100.0*float(jing)/float(maxjing)
                pct2 = 100.0*float(effjing)/float(maxjing)
            formatted_list.append((style, "{0}[{1:3.0f}%] / {2}[{3:3.0f}%]".format(jing, pct1, effjing, pct2)))

            formatted_list.append(("", " "))

            formatted_list.append((Settings.styles["title"], "【气血】"))
            if int(effqi) < int(maxqi):
                style = Settings.styles["value.worst"]
            elif int(qi) < 0.8 * int(effqi):
                style = Settings.styles["value.worse"]
            else:
                style = Settings.styles["value"]

            if maxqi == 0: 
                pct1 = pct2 = 0
            else:
                pct1 = 100.0*float(qi)/float(maxqi)
                pct2 = 100.0*float(effqi)/float(maxqi)
            formatted_list.append((style, "{0}[{1:3.0f}%] / {2}[{3:3.0f}%]".format(qi, pct1, effqi, pct2)))
            formatted_list.append(("", " "))

            # 内力
            formatted_list.append((Settings.styles["title"], "【内力】"))
            if int(neili) < 0.6 * int(maxneili):
                style = Settings.styles["value.worst"]
            elif int(neili) < 0.8 * int(maxneili):
                style = Settings.styles["value.worse"]
            elif int(neili) < 1.2 * int(maxneili):
                style = Settings.styles["value"]   
            else:
                style = Settings.styles["value.better"]

            if maxneili == 0: 
                pct = 0
            else:
                pct = 100.0*float(neili)/float(maxneili)
            formatted_list.append((style, "{0} / {1}[{2:3.0f}%]".format(neili, maxneili, pct)))
            formatted_list.append(("", " "))

            # 精力
            formatted_list.append((Settings.styles["title"], "【精力】"))
            if int(jingli) < 0.6 * int(maxjingli):
                style = Settings.styles["value.worst"]
            elif int(jingli) < 0.8 * int(maxjingli):
                style = Settings.styles["value.worse"]
            elif int(jingli) < 1.2 * int(maxjingli):
                style = Settings.styles["value"]   
            else:
                style = Settings.styles["value.better"]
            
            if maxjingli == 0: 
                pct = 0
            else:
                pct = 100.0*float(jingli)/float(maxjingli)

            formatted_list.append((style, "{0} / {1}[{2:3.0f}%]".format(jingli, maxjingli, pct)))
            formatted_list.append(("", " "))

            # a new-line
            formatted_list.append(("", "\n"))
            formatted_list.append((Settings.styles["title"], "【任务】"))
            formatted_list.append((Settings.styles["value"], "{}".format(self.session.cmds.jobmanager.currentJob)))
            formatted_list.append(("", " "))
            formatted_list.append((Settings.styles["title"], "【状态】"))
            formatted_list.append((Settings.styles["value"], "{}".format(self.session.cmds.jobmanager.currentStatus)))
            formatted_list.append(("", " "))
            formatted_list.append((Settings.styles["title"], "【持续】"))
            formatted_list.append((Settings.styles["value"], "{}".format("开启" if self.session.cmds.jobmanager.always else "关闭")))
            formatted_list.append(("", " "))
            formatted_list.append((Settings.styles["title"], "【范围】"))
            
            #formatted_list.append((Settings.styles["value"], "{}".format(self.session.cmds.jobmanager.activeJobs)))
            active_jobs_style = to_formatted_text(ANSI(self.session.cmds.jobmanager.activeJobs))
            formatted_list.extend(active_jobs_style)

            # a new-line
            formatted_list.append(("", "\n"))

            # line 3. GPS info
            formatted_list.append((Settings.styles["title"], "【惯导】"))
            if ins:
                formatted_list.append((Settings.styles["value"], "正常"))
                formatted_list.append(("", " "))
                formatted_list.append((Settings.styles["title"], "【位置】"))
                formatted_list.append((Settings.styles["value"], f"{loc['city']} {loc['name']}({loc['id']})"))
            else:
                formatted_list.append((Settings.styles["value.worst"], "丢失"))
                formatted_list.append(("", " "))
                formatted_list.append((Settings.styles["title"], "【位置】"))
                formatted_list.append((Settings.styles["value"], f"{self.session.getVariable('city')} {self.session.getVariable('room')}"))

            if self.session.getVariable("is_busy", False):
                formatted_list.append((Settings.styles["value.worse"], "【忙】"))
            else:
                formatted_list.append((Settings.styles["value"], "【不忙】"))

            if self.session.getVariable("is_fighting", False):
                formatted_list.append((Settings.styles["value.worse"], "【战斗】"))
            else:
                formatted_list.append((Settings.styles["value"], "【空闲】"))

            if self.session.idletime > 60:
                formatted_list.append((Settings.styles["value.worse"], f"【发呆{self.session.idletime // 60:.0f}分钟】"))
            else:
                formatted_list.append((Settings.styles["value"], "【正常】"))

            formatted_list.append((Settings.styles["title"], "【状态】"))
            status = self.session.getVariable("status", list())
            buff = self.session.getVariable("buff", list())

            shown = status.copy()
            shown.extend(buff)

            buff_styled = to_formatted_text(ANSI(f"{' '.join(shown)}"))
            formatted_list.extend(buff_styled)

            # a new-line
            formatted_list.append(("", "\n"))

            def go_direction(dir, mouse_event: MouseEvent):
                if mouse_event.event_type == MouseEventType.MOUSE_UP:
                    self.session.exec_command(dir)
            if ins:
                formatted_list.append((Settings.styles["title"], "【路径】"))
                # formatted_list.append(("", "  "))
                links = self.session.vars["_map"].FindRoomLinks(loc['id'])
                for link in links:
                    dir = link.path
                    dir_cmd = dir
                    if dir in DIRS_ABBR.keys():
                        dir = DIRS_ABBR[dir]
                    else:
                        m = re.match(r'(\S+)\((.+)\)', dir)
                        if m:
                            dir_cmd = m[2]

                    formatted_list.append((Settings.styles["link"], f"{dir}: {link.city} {link.name}({link.linkto})", functools.partial(go_direction, dir_cmd)))
                    formatted_list.append(("", " "))
            
            return formatted_list
    
        except Exception as e:
            return f"{e}"
    
    def session_event(self, event_type, session):
        self.session.setVariable("_menpaiLoaded", False)
        if self.session.getGlobal("hooked"):
            hook = self.session.getGlobal("hook")
            #now = datetime.datetime.now()
            hook.sendMessage(self.session, f"会话发生事件: {event_type}")

    ### GMCP处理函数 ###
    def ongmcp_status(self, name, line, wildcards):
        # GMCP.Status
        # 自己的Status和敌人的Status均会使用GMCP.Status发送
        # 区别在于，敌人的Status会带有id属性。但登录首次自己也会发送id属性，但同时有很多属性，因此增加一个实战经验属性判定
        if isinstance(wildcards, dict):     # 正常情况下，GMCP.Status应该是一个dict
            if ("id" in wildcards.keys()) and (not "combat_exp" in wildcards.keys()):
                # 说明是敌人的，暂时忽略
                #self.session.info(f"GMCP.Status 收到非个人信息： {wildcards}")

                enemies = self.session.getVariable("enemies")
    
                id = wildcards["id"]
                if id in enemies.keys():
                    enemies[id].update(wildcards)
                    
                    # if ('qi' in wildcards.keys()) and (wildcards["qi"] < 0):
                    #     enemies.pop(id, None)
                    #     self.session.setVariable("enemies", enemies)

                    # elif ('jing' in wildcards.keys()) and (wildcards["jing"] < 0):
                    #     enemies.pop(id, None)
                    #     self.session.setVariable("enemies", enemies)

                    # else:

                    enemy = enemies[id]
                    qi = f"气: {enemy.get('qi')}" if 'qi' in enemy.keys() else ""
                    jing = f"精: {enemy.get('jing')}" if 'jing' in enemy.keys() else ""
                    #qi = enemy.get('qi', 'NaN')
                    #jing = enemy.get('jing', 'NaN')
                    self.session.warning(f'{enemy.get("name", "无名氏")}({enemy.get("id_use", "INVALID_ID")}) {qi} {jing}',f'GMCP战斗', "\x1b[36m")

                # else:
                #     id_use = (id.split('#'))[0]
                #     enemy = dict()
                #     enemy.update(wildcards)
                #     enemy['id_use'] = id_use
                #     enemies[id] = enemy
                #     self.session.setVariable("enemies", enemies)

                #     self.session.info(f'{enemy.get("name", "无名氏")}({id}) 进入战斗...', name, "\x1b[36m")
                #     self.session.info(f'{line}', f'{name}')

            else:
                if "id" in wildcards.keys():
                    # 说明是GMCP Status方式，此时hpbrief将不能使用，要设置其实现
                    self.session.setVariable("status_type", "GMCP")

                # 个人信息已处理，因此不用再info出来
                #self.session.info(f"GMCP.Status 收到个人信息： {wildcards}")
                for key, value in wildcards.items():
                    if value == "false": value = False
                    elif value == "true": value = True
                    self.session.setVariable(key, value)

                self.session.cmds.cmd_score.loadCharSpecialInfo()

        self.session.application.app.invalidate()


    def ongmcp_buff(self, name, line, wildcards):
        #[GMCP] GMCP.Buff: {"is_end":"false","name":"枯荣禅功·枯字诀","effect3":"暴击率增加2%","effect2":"一阳指伤害增加35%","last_time":10,"effect1":"六脉神剑伤害增加40%"}
        #[GMCP] GMCP.Buff: {"is_end":"true","name":"枯荣禅功·枯字诀","terminated":"completed"}
        
        if isinstance(wildcards, dict):
            buff = self.session.getVariable("buff", list())
            if wildcards["is_end"] == "false": 
                if not wildcards["name"] in buff:
                    buff.append(wildcards["name"])
            elif wildcards["name"] in buff:
                buff.remove(wildcards["name"])

            self.session.setVariable("buff", buff)
        else:
            self.session.info(line, name)

        self.session.application.app.invalidate()

    

    ### 触发器处理函数 ###
    def ontri_webpage(self, name, line, wildcards):
        "fullme自动打开网页"
        hooked = self.session.getGlobal("hooked", False)
        
        if not hooked:
            webbrowser.open(line)
        else:
            user = self.session.getVariable("chat_hook_user", 5)
            self.session.globals.hook.sendFullme(self.session, line, user = user)

        #self.session.globals.hook.sendMessageToGotify(self.session.vars.id, f"收到图片地址，请查看fullme: {line}", line)
        #self.session.globals.sendMessageToGotify(self.session.vars.id, "请查看fullme链接.", line)

    def ontri_hpbrief(self, name, line, wildcards):
        "hpbrief自动保存属性变量参数"
        self.session.setVariables(HP_KEYS, wildcards)
        is_busy = not wildcards[-1]
        is_fighting = not wildcards[-2]
        self.session.setVariables(['is_busy', 'is_fighting'], [is_busy, is_fighting])

    def ontri_roomname(self, name, line, wildcards):
        "房间名自动保存"
        room = wildcards[0]
        if room.find("剑心居") >= 0:                                # 把剑心居加上，认定为剑心居
            self.session.setVariable("room", "剑心居")
            self.session.setVariable("ins_loc", JIAN_XIN_JU)
        else:
            self.session.setVariable("room", wildcards[0])

            if line.find("大理") >= 0:
                self.session.setVariable("country", "大理")
            elif line.find("大宋") >= 0:
                self.session.setVariable("country", "大宋")
            elif line.find("大元") >= 0:
                self.session.setVariable("country", "大元")
            elif line.find("大夏") >= 0:
                self.session.setVariable("country", "大夏")
            elif line.find("门派") >= 0:
                self.session.setVariable("country", "门派")
            else:
                self.session.setVariable("country", "other")

            if (line.find("城市") >= 0) or (line.find("都城") >= 0):
                self.session.setVariable("area", "city")
            elif line.find("野外") >= 0:
                self.session.setVariable("area", "field")
            elif line.find("村镇") >= 0:
                self.session.setVariable("area", "country")
            else:
                self.session.setVariable("area", "other")

    def ontri_fullme(self, name, line, wildcards):
        "记录fullme成功时间"
        self.session.setVariable("%fullme", time.time())

    def ontri_cunkuan(self, name, line, wildcards):
        "记录存款的黄金数量"
        info = wildcards[0]
        gold_index = info.find("锭黄金")
        gold_str = info[:gold_index]
        gold = word2number(gold_str)
        self.session.setVariable("deposit", f"{gold}黄金")

    def ontri_dead(self, name, line, wildcards):
        "死亡记录"
        self.session.setVariable("dead", True)
        if self.session.getGlobal("hooked"):
            user = self.session.getVariable("chat_hook_user", 5)
            self.session.globals.hook.sendMessage(self.session, "你死了！！！", user = user)

        else:
            self.session.exec("#message 你死了！")

    def ontri_login(self, name, line, wildcards, relogin = False):
        "登录处置"

        self.session.writeline("")
        # 新登录则自动加载特技，激发为正常武功，清理惯导位置
        if not relogin:
            
            char = self.session.getVariable("id")
            if char in SPECIAL:
                sps = SPECIAL[char]
                self.session.info(f"将使用角色特技{sps}")
                for sp in sps:
                    self.session.writeline(f"sp {sp}")

            self.session.exec("enable all")

            self.session.setVariable("ins_loc", None)
            loginroom = self.session.getVariable("loginroom", None)
            if loginroom:

                tm_locs = list()
                dbrooms = self.session.vars["_map"].FindRoomsByCityName(loginroom)
                cnt = len(dbrooms)
                if cnt > 0:
                    for dbroom in dbrooms:
                        #if isinstance(dbroom, DBRoom):  
                        if dbroom:
                            tm_loc = {}
                            tm_loc["id"]    = dbroom.id
                            tm_loc["name"]  = dbroom.name
                            tm_loc["city"]  = dbroom.city

                            links = self.session.vars["_map"].FindRoomLinks_db(dbroom.id)

                            for link in links:

                                # 增加 Truepath判定，以支持CmdMove
                                path = self.session.cmds.cmd_move.truepath(link.path)

                                if ';' in path:
                                    tm_loc["multisteps"] = True
                                else:
                                    tm_loc["multisteps"] = False
                                
                                tm_loc[path] = link.linkto
                            
                            tm_locs.append(tm_loc)

                self.session.setVariable("tm_locs", tm_locs)

    ### 别名处理函数 ###
    def onali_getfromcorpse(self, name, line, wildcards):
        "别名get xxx from corpse xxx"
        index = wildcards[0]
        item  = wildcards[1]

        if index:
            cmd = f"get {item} from corpse {index}"
        else:
            cmd = f"get {item} from corpse"

        self.session.writeline(cmd)

        