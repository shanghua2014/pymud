"""
插件名称：chathook
使用webhook技术与Synology Chat进行交互的插件脚本。
公开函数定义：
def sendMessage(msg: str):  将消息 msg 通过webhook发送到Synology Chat中。
脚本使用示例：
self.session.plugins["chathook"].sendMessage("This is a test message")
"""
# 上述声明内容会在#plugin chathook时自动打印

from pymud import PyMudApp, Session, Trigger
from functools import partial
import requests, json

# 插件唯一名称
PLUGIN_NAME    = "chathook"

# 插件有关描述信息
PLUGIN_DESC = {
    "VERSION" : "1.0.0",
    "AUTHOR"  : "newstart",
    "RELEASE_DATE"  : "2023-12-21",
    "DESCRIPTION" : "基于PYMUD的一个北侠webhook插件，将站点内聊天有关信息通过webhook发送到其他应用中"
}

# 为不要与自行写的脚本重复，插件中使用的触发器、命令等，命名请注意区分，或者不指定id
TRIGGER_ID  = "plugins_chathook"
WEBHOOK_URL = "https://please.change.to.your.domain.and.your.url/"

def sendMessage(msg: str):
    "发送消息到webhook端"
    data = {"payload": json.dumps({"text": msg})}
    resp = requests.post(WEBHOOK_URL, data)
    info = resp.json()
    success = info.get("success")
    error   = info.get("error")
    if success:
        return 0, 'send message ok!'
    else:
        return error['code'], error['errors']

def ontri_chat(session, name, line, wildcards):
    code, msg = sendMessage(line)
    if code != 0:
        session.info(f"Send message fail with error code: {code}, error message: {msg}", f"PLUGIN {PLUGIN_NAME}")

def PLUGIN_PYMUD_START(app: PyMudApp):
    "PYMUD自动读取并加载插件时自动调用的函数， app为APP本体。该函数仅会在程序运行时，自动加载一次"
    app.set_status(f"插件{PLUGIN_NAME}已加载!")

def PLUGIN_SESSION_CREATE(session: Session):
    "在会话中加载插件时自动调用的函数， session为加载插件的会话。该函数在每一个会话创建时均被自动加载一次"
    # 为确保插件的触发器不影响自己的脚本也不被自己的脚本影响，建议将keepEval设置为True，priority设置为小于100
    tri = Trigger(session, id = TRIGGER_ID, patterns = r'^【.+】.+$', group = PLUGIN_NAME, onSuccess = partial(ontri_chat, session), keepEval = True, priority = 80)
    session.addTrigger(tri)
    session.info(f"插件{PLUGIN_NAME}已被本会话加载(这里改了：), 已成功向本会话中添加触发器 {TRIGGER_ID} !!!")

def PLUGIN_SESSION_DESTROY(session: Session):
    "在会话中卸载插件时自动调用的函数， session为卸载插件的会话。卸载在每一个会话关闭时均被自动运行一次。"
    session.delTrigger(session.tris[TRIGGER_ID])