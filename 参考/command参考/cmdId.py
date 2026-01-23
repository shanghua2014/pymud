import asyncio, random, traceback

from pymud import IConfig, Command, Trigger, Session
from pymud.extras import DotDict

from ..common import MONEY, FOODS, DRINKS, SELLS, SELLS_DESC, TRASH
from ..common import Inventory, word2number

class CmdID(Command, IConfig):
    "执行PKUXKX中的id命令"

    def __init__(self, session, *args, **kwargs):
        kwargs.setdefault('id', 'cmd_id')
        super().__init__(session, r"^id(?:\shere)?$", *args, **kwargs)

        self._objs = [
            Trigger(session, id = "id_item", patterns = r'^(\S+)\s+=\s(\S.+)$', onSuccess = self.item, group = "idcmd") 
        ]

        self.items_id = dict()

    def __unload__(self):
        self.session.delObjects(self._objs)

    def item(self, name, line, wildcards):
        ch_name = wildcards[0]

        en_ids  = list()
        en_id   = wildcards[1]
        if ',' in en_id:
            ids = en_id.split(',')
            for id in ids:
                en_ids.append(id.strip())

        else:
            en_ids.append(en_id)

        self.items_id[ch_name] = en_ids
        #self.info(f"捕获一行ID，物品名称为：{ch_name}，共有{len(en_ids)}个ID，分别为：{', '.join(en_ids)}")

    async def execute(self, cmd, *args, **kwargs):
        await super().execute(cmd, *args, **kwargs)
        self.items_id.clear()
        self.session.writeline(cmd)
        self.session.writeline("")
        await asyncio.sleep(1)
        if cmd == "id":
            self.info(f"共获取{len(self.items_id.keys())}项物品的ID")
        elif cmd == "id here":
            self.info(f"共获取{len(self.items_id.keys())}个人物的ID")

        name = kwargs.get("name", None)
        if name: 
            if name in self.items_id.keys():
                #result = random.choice(self.items_id[name])
                result = self.items_id[name][0]
                self.info(f"你要获取{name}的ID，它一共有{len(self.items_id[name])}个，取第一个为{result}")
                return result
            else:
                self.info(f"你要获取{name}的ID，但没有找到该物品/人物，将返回None")
                return None
        else:
            return self.items_id