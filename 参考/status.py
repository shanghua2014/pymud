def status_window(self):
        from prompt_toolkit.mouse_events import MouseEvent, MouseEventType
        from settings import Settings
        formatted_list = list()

        (jing, effjing, maxjing, jingli, maxjingli, qi, effqi, maxqi, neili, maxneili) = self.session.getVariables(("jing", "effjing", "maxjing", "jingli", "maxjingli", "qi", "effqi", "maxqi", "neili", "maxneili"))
        ins_loc = self.session.getVariable("ins_loc", None)
        tm_locs = self.session.getVariable("tm_locs", None)
        ins = False
        if isinstance(ins_loc, dict) and (len(ins_loc) >= 1):
            ins = True
            loc = ins_loc

        elif isinstance(tm_locs, list) and (len(tm_locs) == 1):
            ins = True
            loc = tm_locs[0]

        # line 1. char, menpai, deposit, food, water, exp, pot
        formatted_list.append((Settings.styles["title"], "【角色】"))
        formatted_list.append((Settings.styles["value"], "{0}({1})".format(self.session.getVariable('charname'), self.session.getVariable('char'))))
        formatted_list.append(("", " "))
        formatted_list.append((Settings.styles["title"], "【门派】"))
        formatted_list.append((Settings.styles["value"], "{}".format(self.session.getVariable('menpai'))))
        formatted_list.append(("", " "))
        formatted_list.append((Settings.styles["title"], "【存款】"))
        formatted_list.append((Settings.styles["value"], "{}".format(self.session.getVariable('deposit'))))
        formatted_list.append(("", " "))
        formatted_list.append((Settings.styles["title"], "【食物】"))
        
        food = int(self.session.getVariable('food', '0'))
        if food < 100:
            style = Settings.styles["red"]
        elif food < 200:
            style = Settings.styles["yellow"]
        elif food < 350:
            style = Settings.styles["green"]
        else:
            style = Settings.styles["skyblue"]

        formatted_list.append((style, "{}".format(food)))
        formatted_list.append(("", " "))

        formatted_list.append((Settings.styles["title"], "【饮水】"))
        water = int(self.session.getVariable('water', '0'))
        if water < 100:
            style = Settings.styles["red"]
        elif water < 200:
            style = Settings.styles["yellow"]
        elif water < 350:
            style = Settings.styles["green"]
        else:
            style = Settings.styles["skyblue"]
        formatted_list.append((style, "{}".format(water)))
        formatted_list.append(("", " "))
        formatted_list.append((Settings.styles["title"], "【经验】"))
        formatted_list.append((Settings.styles["value"], "{}".format(self.session.getVariable('exp'))))
        formatted_list.append(("", " "))
        formatted_list.append((Settings.styles["title"], "【潜能】"))
        formatted_list.append((Settings.styles["value"], "{}".format(self.session.getVariable('pot'))))
        formatted_list.append(("", " "))
        formatted_list.append((Settings.styles["title"], "【惯导】"))
        if ins:
            formatted_list.append((Settings.styles["skyblue"], "正常"))
            formatted_list.append(("", " "))
            formatted_list.append((Settings.styles["title"], "【位置】"))
            formatted_list.append((Settings.styles["green"], f"{loc['city']} {loc['name']}({loc['id']})"))
        else:
            formatted_list.append((Settings.styles["red"], "丢失"))
            formatted_list.append(("", " "))
            formatted_list.append((Settings.styles["title"], "【位置】"))
            formatted_list.append((Settings.styles["value"], f"{self.session.getVariable('%room')}"))

        # a new-line
        formatted_list.append(("", "\n"))

        # line 2. hp
        if jing != None:
            formatted_list.append((Settings.styles["title"], "【精神】"))
            if int(effjing) < int(maxjing):
                style = Settings.styles["red"]
            elif int(jing) < 0.8 * int(effjing):
                style = Settings.styles["yellow"]
            else:
                style = Settings.styles["green"]
            formatted_list.append((style, "{0}[{1:3.0f}%] / {2}[{3:3.0f}%]".format(jing, 100.0*float(jing)/float(maxjing), effjing, 100.0*float(effjing)/float(maxjing),)))
            formatted_list.append(("", " "))

            formatted_list.append((Settings.styles["title"], "【气血】"))
            if int(effqi) < int(maxqi):
                style = Settings.styles["red"]
            elif int(qi) < 0.8 * int(effqi):
                style = Settings.styles["yellow"]
            else:
                style = Settings.styles["green"]
            formatted_list.append((style, "{0}[{1:3.0f}%] / {2}[{3:3.0f}%]".format(qi, 100.0*float(qi)/float(maxqi), effqi, 100.0*float(effqi)/float(maxqi),)))
            formatted_list.append(("", " "))

            formatted_list.append((Settings.styles["title"], "【精力】"))
            if int(jingli) < 0.6 * int(maxjingli):
                style = Settings.styles["red"]
            elif int(jingli) < 0.8 * int(maxjingli):
                style = Settings.styles["yellow"]
            elif int(jingli) < 1.2 * int(maxjingli):
                style = Settings.styles["green"]   
            else:
                style = Settings.styles["skyblue"]
            formatted_list.append((style, "{0} / {1}[{2:3.0f}%]".format(jingli, maxjingli, 100.0*float(jingli)/float(maxjingli))))
            formatted_list.append(("", " "))

            formatted_list.append((Settings.styles["title"], "【内力】"))
            if int(neili) < 0.6 * int(maxneili):
                style = Settings.styles["red"]
            elif int(neili) < 0.8 * int(maxneili):
                style = Settings.styles["yellow"]
            elif int(neili) < 1.2 * int(maxneili):
                style = Settings.styles["green"]   
            else:
                style = Settings.styles["skyblue"]
            formatted_list.append((style, "{0} / {1}[{2:3.0f}%]".format(neili, maxneili, 100.0*float(neili)/float(maxneili))))
            formatted_list.append(("", " "))

            # a new-line
            formatted_list.append(("", "\n"))

        # line 3. GPS info
        def go_direction(dir, mouse_event: MouseEvent):
            if mouse_event.event_type == MouseEventType.MOUSE_UP:
                self.session.exec_command(dir)
        if ins:
            formatted_list.append((Settings.styles["title"], "【路径】"))
            # formatted_list.append(("", "  "))
            links = self.mapper.FindRoomLinks(loc['id'])
            for link in links:
                dir = link.path
                dir_cmd = dir
                if dir in Configuration.DIRS_ABBR.keys():
                    dir = Configuration.DIRS_ABBR[dir]
                else:
                    m = re.match(r'(\S+)\((.+)\)', dir)
                    if m:
                        dir_cmd = m[2]

                formatted_list.append((Settings.styles["link"], f"{dir}: {link.city} {link.name}({link.linkto})", functools.partial(go_direction, dir_cmd)))
                formatted_list.append(("", " "))
        
        return formatted_list
