import traceback, re, asyncio
from typing import Any
from dataclasses import dataclass
from pymud import Command, Trigger, IConfig

from ..common import REGX_ROOMNAME, REGX_ROOMEXIT, MudRoom
from ..map.map import DBRoom, DBRoomLink

class CmdLook(Command, IConfig):
    "执行PKUXKX中的Look命令"

    @dataclass
    class State:
        result: int
        room: Any

    def __init__(self, session, *args, **kwargs):
        kwargs.setdefault("id", "cmd_look")
        super().__init__(session, patterns = r"^(?:l|look)(?:\s+(\S.+))?$", **kwargs)

        self.mode_drawing = False

        self.drawings = list()
        self.nodes    = list()
        self.selectedNode = None
        self.nodeName = None

        self._tris = {
            "name"      : Trigger(session, patterns = REGX_ROOMNAME, onSuccess = self.roomname, keepEval = True, group = "room", enabled = False),
            "exits"     : Trigger(session, patterns = REGX_ROOMEXIT, onSuccess = self.roomexits, keepEval = True, group = "room", enabled = False),
            "relation"  : Trigger(session, patterns = r'^[>]*\s{7,}(\S.*)\s*$', onSuccess = self.relation, group = "room", enabled = False),
            "weather"   : Trigger(session, patterns = r'^\s*「(.*)」: (.*)$', onSuccess = self.weather, group = "room", enabled = False),
            "desc"      : Trigger(session, patterns = r'^\s{0,6}[^\|~/_\s].*$', onSuccess = self.description, enabled = False, keepEval = True, group = "room"),
            # 镇江土路边的房子，不要加入数据库，不要匹配
            "house"     : Trigger(session, patterns = r'^\s*炊烟不断地从.+', onSuccess = self.weather, group = "room", enabled = True),
            "node"      : Trigger(session, patterns = r'^\s*你可以看看', onSuccess = self.node, group = "room", enabled = False),
            "extra"     : Trigger(session, patterns = r'^\s*(┌|│|└)', group = "room", enabled = False),
            "empty"     : Trigger(session, patterns = r'^\s*$', onSuccess = self.emptyline, enabled = False, group = "room"),
            "drawline"  : Trigger(session, patterns = r'^\s*(\S.+)\s*$', onSuccess = self.find_drawing, enabled = False, keepEval = True,  group = "room_draw"),
            "objs"      : Trigger(session, patterns = r'\s+([^\(]+)\(([^\)]+)\)\s*(?:<.+>)?$', onSuccess = self.objects, keepEval = True, group = "room", enabled = False),
            "terminate" : Trigger(session, patterns = r'^\S.+', onSuccess = self.terminate, keepEval = True, group = "room", enabled = False),

            "nodestart" : Trigger(session, patterns = r"^(?:\x1b\[2;37;0m)*[┌╭][─]+([^─]+)[─┬]+[┐╮]$", enabled = False, onSuccess = self.nodestart,  group = "node"),
            "item"      : Trigger(session, patterns = r"^(?:\x1b\[2;37;0m)*│(.+)│(?:\x1b\[2;37;0m)*([a-z]+)\x1b.+\│", raw = True, enabled = False, onSuccess = self.nodenormal, group = "node"),
            "select"    : Trigger(session, patterns = r"^(?:\x1b\[2;37;0m)*│(.+)│(?:\x1b\[2;37;0m)*\x1b\[47;1m\x1b\[1;30m([a-z]+)\x1b.+\│", raw = True, enabled = False, onSuccess = self.nodeselected, group = "node"),
            "nodeend"   : Trigger(session, patterns = r"^(?:\x1b\[2;37;0m)*├[─┴]+┤$", enabled = False, group = "node"),

            "place_start"   : Trigger(self.session, r'^纸条上画着：', group = "zhitiao", onSuccess = self.placestart, enabled = False),
            "place_line3"   : Trigger(self.session, r'^\s*([\u4e00-\u9fa5\(\)A-Z]+)[\s━]+([\u4e00-\u9fa5\(\)A-Z]+)[\s━]+([\u4e00-\u9fa5\(\)A-Z]+)\s+', group = "zhitiao", onSuccess = self.place, enabled = False, priority = 95),
            "place_line2"   : Trigger(self.session, r'^\s*([\u4e00-\u9fa5\(\)A-Z]+)[\s━]+([\u4e00-\u9fa5\(\)A-Z]+)\s+', group = "zhitiao", onSuccess = self.place, enabled = False, priority = 97),
            "place_line1"   : Trigger(self.session, r'^[━\s]*([\u4e00-\u9fa5\(\)A-Z]+)[\s━]+', group = "zhitiao", onSuccess = self.place, enabled = False, priority = 99),
            "place_line0"   : Trigger(self.session, r'^\S+：([\u4e00-\u9fa5\(\)A-Z]+).*', group = "zhitiao", onSuccess = self.place, enabled = False, priority = 99),
            "place_end"     : Trigger(self.session, r'^纸条目前还没有物理定义，快去做第一个定义', group = "zhitiao", onSuccess = self.placeend, enabled = False),
        }

        self.reset()

    def __unload__(self):
        self.session.delObjects(self._tris)

    def reset(self):
        self.session.enableGroup("zhitiao", False)
        self.session.enableGroup("room", False)
        self.session.enableGroup("node", False)

        self._roomname = ""
        self._desc = ""
        self._relation = ""
        self.nodeName = None

    def roomname(self, id, line, wildcards):
        self.session.vars.room = wildcards[0]
        self.session.enableGroup("room")
        self._tris["relation"].enabled = False
        self._tris["name"].enabled = False
        self._tris["terminate"].enabled = False

        self._roomname = wildcards[0]
        self._desc = ""
        #self._relation = ""

        if self.mode_drawing:
            self._tris["drawline"].enabled = True

    def roomexits(self, name, line, wildcards):
        self.session.enableGroup("room", False)
        self._tris["objs"].enabled = True
        self._tris["terminate"].enabled = True
        self.session.setVariable("objects", list())

    def objects(self, name, line, wildcards):
        # 此处证实可用，待后续需要时完善内容 TODO
        # self.info(f"获取一行对象，称谓为[{wildcards[0]}], ID为[{wildcards[1]}]")
        objects = self.session.getVariable("objects", list())
        objects.append((wildcards[1].lower(), wildcards[0].split(' ')[-1]))
        self.session.setVariable("objects", objects)
        pass

    def terminate(self, name, line, wildcards):
        self._tris["objs"].enabled = False
        self._tris["terminate"].enabled = False

    def relation(self, name, line, wildcards):
        self._tris["name"].enabled = True
        self._relation += wildcards[0].strip()

    def weather(self, name, line, wildcards):
        self._tris["desc"].enabled = False 

        # 若位于室外，则图画开头一定在天气行之后
        # 加入这个是为了处置在各种城门处，城门画影响判断图片的问题
        if self.mode_drawing:
            self.drawings.clear()

    def node(self, name, line, wildcards):
        self._tris["desc"].enabled = False 

        # 图画开头一定在node之后
        # 加入这个是为了处置在茶馆时，画影响判断图片的问题
        if self.mode_drawing:
            self.drawings.clear()

    def emptyline(self, name, line, wildcards):
        self._tris["desc"].enabled = False 

    def description(self, name, line, wildcards):
        desc = line.strip()
        omit = False

        if  (self._tris["exits"].match(line).result == Trigger.SUCCESS) or    \
            (self._tris["weather"].match(line).result == Trigger.SUCCESS) or   \
            (self._tris["relation"].match(line).result == Trigger.SUCCESS) or   \
            (self._tris["node"].match(line).result == Trigger.SUCCESS) or   \
            (self._tris["extra"].match(line).result == Trigger.SUCCESS) or   \
            (self._tris["name"].match(line).result == Trigger.SUCCESS)  or   \
            (self._tris["house"].match(line).result == Trigger.SUCCESS):

            omit = True

        if omit:
                desc = ""
        else:
            self._tris["relation"].enabled = False

        self._desc += desc

    def find_drawing(self, name, line, wildcards):
        drawing_line = wildcards[0].strip()
        drawings = self.session.vars["_map"].FindPossibleDrawings(drawing_line)

        if len(drawings) > 0:
            self.drawings.append(drawings)

    def nodestart(self, name, line, wildcards):
        #self.info(f"捕获到节点开始标记")
        self.nodeName = wildcards[0]
        self.session.enableGroup("node")
        
    def nodenormal(self, name, line, wildcards):
        if not wildcards[0] == "目的地":
            #self.info(f"找到一个节点，目的地名称为 {wildcards[0].replace(' ', '')}，拼音为{wildcards[1]}")
            self.nodes.append((wildcards[0].replace(' ', ''), wildcards[1], self.nodeName))

    def nodeselected(self, name, line, wildcards):
        #self.info(f"找到一个节点，目的地名称为{wildcards[0].replace(' ', '')}，拼音为{wildcards[1]}")
        self.selectedNode = (wildcards[0].replace(' ', ''), wildcards[1], self.nodeName)
        self.nodes.insert(0, self.selectedNode)

    def placestart(self, id, line, wildcards):
        self._tris["place_line0"].enabled = True
        self._tris["place_line1"].enabled = True
        self._tris["place_line2"].enabled = True
        self._tris["place_line3"].enabled = True
        self._tris["place_end"].enabled = True
        self.zhitiao = {}

    def place(self, id, line, wildcards):
        for item in wildcards:
            if "(" in item:
                roominfo = item.split('(')
                room_name = roominfo[0]
                room_dir  = roominfo[1][:-1].lower()
                self.zhitiao[room_dir] = room_name
            else:
                self.zhitiao["name"] = item

    def placeend(self, id, line, wildcards):
        self._tris["place_line0"].enabled = False
        self._tris["place_line1"].enabled = False
        self._tris["place_line2"].enabled = False
        self._tris["place_line3"].enabled = False
        self._tris["place_end"].enabled = False

    def onSuccess(self, room):
        #return super().onSuccess(*args, **kwargs)
        if room["name"].find("剑心居") >= 0:
            self.session.setVariable("room", "剑心居")
            self.info('通过名称匹配，确认你在剑心居.', "地形匹配")
        else:
            self.session.setVariable("tm_locs", None)

            self.info('捕获一个房间 {0}， 其出口为 {1}， 关联关系为{2}'.format(room["name"], room["exits"], room["relation"]), "地形匹配")
            dbrooms = self.session.vars["_map"].FindRoomsByRoom(room)
            #rooms = self.mapper.FindRoomsByNameAndRelation(room["name"], room["relation"])
            cnt = len(dbrooms)
            # Inertial Navigation System location, 惯性导航系统匹配确定的位置信息
            ins_loc = self.session.getVariable("ins_loc")
            # terrain matching locations. 通过地形匹配确定的位置信息
            tm_locs = list()
            if cnt == 1:
                dbroom = dbrooms[0]
                self.info('地形匹配房间ID：{0}，房间名：{1}，房间所在城市：{2}'.format(dbroom.id, dbroom.name, dbroom.city), "地形匹配")
                tm_loc = {}
                tm_loc["id"]    = dbroom.id
                tm_loc["name"]  = dbroom.name
                tm_loc["city"]  = dbroom.city
                
                links = self.session.vars["_map"].FindRoomLinks_db(dbroom.id)
                self.info(f'该房间共有{len(links)}条路径，分别为：', "地形匹配")
                for link in links:
                    self.info(f'ID = {link.linkid}, {link.path}，链接到：{link.city} {link.name} ({link.linkto})', "路径")
                    path = self.session.cmds.cmd_move.truepath(link.path)
                    if ';' in path:
                        tm_loc["multisteps"] = True
                    else:
                        tm_loc["multisteps"] = False
                    
                    tm_loc[path] = link.linkto

                tm_locs.append(tm_loc)
                self.session.setVariable("tm_locs", tm_locs)
                autoupdate = self.session.getVariable("autoupdate", False)
                if ins_loc:
                    if (ins_loc["id"] != dbroom.id) and (ins_loc["name"] != dbroom.name):
                        self.info("已根据地形匹配系统更新惯导位置", "地形匹配")
                        self.session.setVariable("ins_loc", tm_loc)
                    elif autoupdate and (ins_loc["id"] == dbroom.id) and (len(room["relation"]) > 1):
                        self.session.vars["_map"].UpdateRoom(dbroom.id, room)
                        self.info(f'数据库中房间{room["name"] }(ID = {dbroom.id})内容已更新!', "自动地图更新")
            
            elif cnt > 1:
                self.info('通过地形匹配从数据库中找到{0}个房间.'.format(cnt), "地形匹配")
                
            else:
                self.warning('未从数据库中找到相应房间!', '地形匹配')

                # else:
                # for dbroom in dbrooms:
                #     #if isinstance(dbroom, DBRoom):  
                #     if dbroom and isinstance(dbroom, DBRoom):
                #         tm_loc = {}
                #         tm_loc["id"]    = dbroom.id
                #         tm_loc["name"]  = dbroom.name
                #         tm_loc["city"]  = dbroom.city
                #         # 由于新增的房间、修改的路径等尚未加入缓存，为了防止look报错，此处的路径直接从数据库中获取，而非从缓存中获取
                #         # 修改时间： 230625
                #         #links = self.mapper.FindRoomLinks(dbroom.id)
                #         links = self.session.vars["_map"].FindRoomLinks_db(dbroom.id)
                #         if cnt == 1:
                #             self.info(f'该房间共有{len(links)}条路径，分别为：', "地形匹配")
                #         for link in links:
                #             if (cnt == 1) and isinstance(link, DBRoomLink):
                #                 self.info(f'ID = {link.linkid}, {link.path}，链接到：{link.city} {link.name} ({link.linkto})', "路径")
                            
                #             # 增加 Truepath判定，以支持CmdMove
                #             path = self.session.cmds.cmd_move.truepath(link.path)

                #             if ';' in path:
                #                 tm_loc["multisteps"] = True
                #             else:
                #                 tm_loc["multisteps"] = False
                            
                #             tm_loc[path] = link.linkto
                        
                #         tm_locs.append(tm_loc)

                #         if ins_loc and ins_loc["id"] == dbroom.id:
                #             self.info("惯导系统与地形匹配系统印证确定，当前房间为：{2} {1}(ID={0})".format(dbroom.id, dbroom.name, dbroom.city), "地形匹配")
                            
                #             # 此时，tmlocs仅保留1个正确的房间
                #             tm_locs.clear()
                #             tm_locs.append(tm_loc)
                            
                #             # 增加autoupdate（额外条件：存在relation时，以防止没有fullme时不显示relation还被更新
                #             autoupdate = self.session.getVariable("autoupdate", False)
                #             if autoupdate and (len(room["relation"]) > 1):
                #                 self.session.vars["_map"].UpdateRoom(dbroom.id, room)
                #                 self.info(f'数据库中房间{room["name"] }(ID = {dbroom.id})内容已更新!', "自动地图更新")
                            
                #             break
        
            # tm_locs变量，terrain matching locations. 通过地形匹配确定的位置信息
            #self.session.setVariable("tm_locs", tm_locs)

    async def execute(self, cmd = "look", *args, **kwargs):
        try:
            m = re.match(self.patterns, cmd)
            if m:
                param = m[1]
                if param == "<node>":

                    self.reset()
                    self._tris["nodestart"].enabled = True
                    self.nodes.clear()
                    self.selectedNode = None
                    self.nodeName = None

                    await self.session.waitfor("l <node>", self._tris["nodeend"].triggered())

                    self.session.enableGroup("node", False)

                    self.info(f"节点查找完成，当前节点为{self.nodeName}, 一共包含{len(self.nodes)}个节点，选中目的地为：{self.selectedNode}")
                    if self.selectedNode:
                        return self.State(self.SUCCESS, self.selectedNode)
                    else:
                        return self.State(self.FAILURE, self.nodes)

                elif param == "<drawing>":
                    # look <drawing>，自定义判定，为南国围猎查找图片处理
                    self.reset()
                    self.mode_drawing = True
                    self.drawings.clear()
                    self._tris["name"].enabled = True
                    
                    done, pending = await self.session.waitfor("look", asyncio.wait([self.create_task(self._tris["exits"].triggered())], timeout = 5))
                    self._tris["drawline"].enabled = False

                    if len(done) > 0:
                        if len(self.drawings) > 0:
                            possible_drawings = set(self.drawings[0])
                            for idx in range(1, len(self.drawings)):
                                line_drawing = set(self.drawings[idx])
                                possible_drawings = possible_drawings.intersection(line_drawing)

                            self.info(f"最终判断可能的图片为：{possible_drawings}，类型为{type(possible_drawings)}")
                            if len(possible_drawings) == 1:
                                return self.State(self.SUCCESS, list(possible_drawings))
                            elif len(possible_drawings) == 0:
                                possible_one_drawings = dict()
                                
                                for idx in range(1, len(self.drawings)):
                                    if len(self.drawings[idx]) == 1:
                                        draw = self.drawings[idx][0]
                                        if not draw in possible_one_drawings.keys():
                                            possible_one_drawings[draw] = 1
                                        else:
                                            possible_one_drawings[draw] += 1
                                    else:
                                        continue

                                if len(possible_one_drawings.keys()) == 1:
                                    key, value = possible_one_drawings.popitem()
                                    self.info(f"通过单行判断最可能图片为: {key}, 通过单行匹配出现了 {value} 次唯一结果")
                                    return self.State(self.SUCCESS, list(key))
                                elif len(possible_one_drawings.keys()) > 1:
                                    self.info(f"通过单行判断可能图片有 {len(possible_one_drawings)} 种，分别为: {possible_one_drawings}")
                                    result = list(possible_one_drawings.keys())
                                    result.sort(key = lambda val: possible_one_drawings[val], reverse = True)
                                    if len(result) == 1:
                                        key, value = result.popitem()
                                        return self.State(self.SUCCESS, list(key))
                                    else:
                                        key = possible_one_drawings.keys()
                                        return self.State(self.SUCCESS, list(key))
                                        #return self.State(self.SUCCESS, result)
                                else:
                                    self.drawings.sort(key = len)

                                    item_count = dict()

                                    for item in self.drawings:
                                        for graph in item:
                                            if graph in item_count.keys():
                                                item_count[graph] += 1
                                            else:
                                                item_count[graph] = 1

                                    max_count = max(item_count.values())
                                    max_available = [(item, count) for item, count in item_count.items() if count == max_count]
                                    self.info(f"通过单行判断，最大可能图片有 {len(max_available)} 种，包括： {max_available}")
                                    if len(max_available) == 1:
                                        return self.State(self.SUCCESS, list(max_available[0][0]))
                                    else:
                                        return self.State(self.SUCCESS, max_available)
                                
                                
                            else:
                                return self.State(self.FAILURE, list(possible_drawings))
                    else:
                        self.warning("图片查看检查超时，请手动重试")

                elif param == "paper" or (param == "zhi tiao"):
                    self._tris["place_start"].enabled = True
                    await self.session.waitfor("l zhi tiao", self._tris["place_end"].triggered())

                    self.info(f"纸条信息捕获完毕，信息为: {self.zhitiao}")
                    room = self.session.vars["_map"].FindRoomsByPaperInfo(self.zhitiao)
                    self.info(f"根据纸条信息推测可能房间为: {room}")
                    return room
                
                elif not param:
                    #self.info("normal look")
                    self.mode_drawing = False
                    # self._tris["drawline"].enabled = False
                    # 默认的look房间处理
                    self.reset()
                    room = {}

                    # 输入命令, 中间过程由Trigger直接出发，同步方式完成，无需异步等待, 等待房间出口被触发
                    # name 也要打开，以防止没有fullme时，不显示 relation 导致无法捕获
                    self._tris["name"].enabled = True
                    # 服务器改了，现在relation是第一个
                    self._tris["relation"].enabled = True
                    self._relation = ""

                    done, pending = await self.session.waitfor("look", asyncio.wait([self.create_task(self._tris["exits"].triggered())], timeout = 5))

                    if len(done) > 0:
                        task = tuple(done)[0]
                        state = task.result()

                        room["name"] = self._roomname
                        room["relation"] = self._relation
                        room["description"] = self._desc
                        #if len(state.wildcards) == 1:
                        exits = "{}{}".format(state.wildcards[0] or "", state.wildcards[1] or "")
                        exits = exits.strip()
                        exits = exits.replace('。','').replace(' ', '').replace('、', ';').replace('和', ';')  # 去除句号、空格；将顿号、和转换为;
                        exit_list = exits.split(';')
                        exit_list.sort()
                        room["exits"] = ';'.join(exit_list)
                        #else:
                        #    room["exits"] = ""

                        #self.info(f"捕获一个房间：{room}")

                        self._onSuccess(room)
                        result = self.SUCCESS
                    else:
                        # timeout，同success
                        self._onTimeout()
                        result = self.TIMEOUT
                    
                    self.reset()
                    return self.State(result, room)
        
                else:
                    self.session.writeline(cmd)

        except Exception as e:
            self.error(f"异步执行中遇到异常, {e}, 类型为 {type(e)}")
            self.error(f"异常追踪为： {traceback.format_exc()}")