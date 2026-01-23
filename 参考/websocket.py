"""
PyMUD 专用 websocket 插件
version: 2.0.4
author: newstart
release: 2025-08-09
本插件提供了一个web端访问页面，用于与pymud之间双向通信。
使用本插件可以向连接的客户端发送文本和图片消息、发送fullme链接（北侠专用，此时自动解析图片并发送）。

使用帮助：
一、插件安装:
    本插件使用了FastAPI, websocket, 并使用uvicorn作为web服务。使用插件前，请安装以下依赖包:
        pip install uvicorn[standard], fastapi, websockets, aiohttp
    使用时，将插件提供的3个文件， websocket.py, websocket.html, ansi_up.min.js 拷贝到脚本的 plugins 目录下，重新启动 pymud 即可。
    插件正常加载后，使用浏览器访问 http://localhost:8000/?key=pkuxkx 可以看到插件提供的web页面。
    插件正常加载后，在会话中 #plugins 可以看到插件已经加载， #global 可以看到一个名为 "ws" 的全局 namespace 。
    从#global可以看到, ws 全局 namespace 包括1个服务对象 server 和4个函数对象，分别是 connected, sendText, sendFullme, sendOverview。含义如下：
        server: uvicorn.server.Server 类型， websocket服务器的实例，可以不用理会。
        connected: 调用 ws.connected() 返回 True/False, 表示是否有客户端连接到本服务器。
        sendText: 函数原型： ws.sendText(sender: str, text_message: str = "", image_file: str = ""), 向所有连接客户端发送消息。
                 参数 sender 指代发送者，务必使用 session.name 来标识；text_message 是消息文本，image_file是需要发送的图片文件路径，默认为空字符串。
        sendFullme: 函数原型: ws.sendFullme(sender: str, text_message: str = "", fullme_url: str = "", times: int = 3, combine: bool = False), 解析北侠 fullme 链接的图片 times 次，并发送到所有客户端。
                 参数 sender, text_message 作用于 senderText相同， fullme_url 是北侠的Fullme给出的链接， times 是解析并发送的图片次数, combine 是指定图片是否合并发送。
        sendOverview: 函数原型: ws.sendOverview(sender: str, func_overview: callable), 为概览消息提供接口。
                 参数 sender 指代发送者，务必使用 session.name 来标识；func_overview 是一个函数，不接受额外参数，且应返回一个dict字典。
        当没有客户端连接时，调用 sendText 或 sendFullme 函数，会将消息缓存到离线缓冲区，当有客户端连接时，会自动发送缓存的消息。

二、网页使用:
    插件正常加载后，使用浏览器访问 http://localhost:8000/?key=pkuxkx 可以看到插件提供的web页面。
    其中，key个人可以自行修改以保证访问的隐私性，由 WEBSOCKET_PRIVATE_KEY 常量指定，默认使用pkuxkx。
    网页顶部显示所有会话的概览信息，由 sendOverview 函数提供。概览信息会话都可以设置是否挂接（通过checkbox复选框选择），挂接后，网页会显示pymud的有关会话信息。
    当有会话挂接时，网页左侧会显示会话本身的信息，显示内容与pymud会话显示相同。
    网页右边是消息窗口，会显示sendText和sendFullme发送的有关数据。
    网页底部的命令行可以输入命令，插件会将命令发送到pymud的特定会话，会话由下拉框指定。
    命令行支持命令缓存功能，可以上下箭头切换，输入部分字符之后，Tab可以自动补完。
    概览窗口、会话消息窗口中均可以鼠标点击，点击后可自动切换到对应会话，相当于会话下拉框选择切换。

三、脚本使用:
    所有消息发送的sender，建议统一使用 self.session.name , 以支持客户端与服务端的正常交互。
    1. 在脚本中向客户端发送消息，若无客户端连接，不缓存消息：
        ws = self.session.getGlobal("ws")
        if ws and ws.connected():               # 若此处判断客户端连接状态后再调用，则不会缓存消息
            ws.sendText(self.session.name, f"想发送的消息")
    2. 在脚本中解析并向客户端发送Fullme图片4次，若无客户端连接，缓存图片待连接后发送：
        ws = self.session.getGlobal("ws")
        if ws:
            ws.sendFullme(self.session.name, "your message for fullme", fullme_url, 4)
    3. 如果要对Fullme链接自动触发，可以增加 fullme 相关触发器：
        @trigger(r'^http://fullme.pkuxkx.net/robot.php.+$')
        def ontri_fullme(self, id, line, wildcards):
            ws = self.session.getGlobal("ws")
            if ws:                                              # 此处不判断 ws.connected() 是将消息缓存确保最终发送
                ws.sendFullme(self.session.name, line, line, times = 4, combine = True)    # fullme 消息文本设置为页面链接，指定下载4次图片，合并发送
    4. 创建概览信息显式时，在任一脚本中为会话指定一个函数作为概览信息获取函数，插件会自动定期调用并发送。参考下面的写法。
        class MyConfig(IConfig):
            def __init__(self, session, *args, **kwargs):
                ws = self.session.getGlobal("ws")
                if ws and hasattr(ws, "sendOverview"):
                    ws.sendOverview(self.session.name, self.overview)

            def overview(self):
                # dict的key会自动作为表格表头，value会每一个会话显示一行。可以自行定义需要显示的内容
                data = dict()
                data["角色"] = f"{self.session.vars['name']}({self.session.vars['id']})"
                
                # fullme time
                fullme = int(self.session.getVariable('%fullme', 0))
                delta = time.time() - fullme
                data["FULLME"]  = int(delta // 60)
                data["发呆"] = int(self.session.idletime // 60)
                data["位置"] = f'{self.session.vars["city"]} {self.session.vars["room"]}'
                data["任务"] = self.session.cmds["jobmanager"].currentJob
                data["状态"] = self.session.cmds["jobmanager"].currentStatus
                data["持续"] = "开启" if self.session.cmds["jobmanager"].always else "关闭"

                return data
"""

import uvicorn, logging
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import asyncio, re, socket, time
import json, base64, os, mimetypes
from datetime import datetime
from typing import List, Tuple, Union
from aiohttp import web, ClientSession
from aiohttp.web_request import Request
from urllib.parse import urlparse, unquote
from prompt_toolkit.formatted_text import StyleAndTextTuples, to_formatted_text, to_plain_text, ANSI, HTML
from prompt_toolkit.output.vt100 import Vt100_Output
from functools import partial
from pymud import PyMudApp, Session, Trigger, Alias, Command, Settings

FLAG_APP_EXITS = False
WEBSOCKET_PRIVATE_KEY = "pkuxkx"
PORT = 8000

app = FastAPI()

fonts_dir = os.path.join(os.path.dirname(__file__), "fonts")
app.mount("/fonts", StaticFiles(directory = fonts_dir), name = "fonts")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

active_connections: List[WebSocket] = []
connection_lock = asyncio.Lock()

offline_buffer: List[dict] = []

# Convert StyleAndTextTuples to ansi str
def formattedtext_to_ansi(formatted_text: StyleAndTextTuples) -> str:
    """
    将StyleAndTextTuples转换为ANSI格式字符串
    支持ANSI色、256色、24位真彩色，以及256色中的颜色文本代码
    去掉所有颜色代码中的连字符
    """
    
    # 标准ANSI颜色映射（去掉连字符）
    COLOR_MAP = {
        'black': 30, 'red': 31, 'green': 32, 'yellow': 33,
        'blue': 34, 'magenta': 35, 'cyan': 36, 'white': 37,
        'brightblack': 90, 'brightred': 91, 'brightgreen': 92,
        'brightyellow': 93, 'brightblue': 94, 'brightmagenta': 95,
        'brightcyan': 96, 'brightwhite': 97,
        'ansiblack': 30, 'ansired': 31, 'ansigreen': 32, 'ansiyellow': 33,
        'ansiblue': 34, 'ansimagenta': 35, 'ansicyan': 36, 'ansiwhite': 37
    }
    
    # 256色颜色名称映射（去掉连字符）
    COLOR_256_NAMES = {
        'maroon': 1, 'darkred': 1, 'darkgreen': 2, 'darkyellow': 3,
        'darkblue': 4, 'darkmagenta': 5, 'darkcyan': 6, 'lightgray': 7,
        'gray': 8, 'darkgray': 8, 'lightred': 9, 'lightgreen': 10,
        'lightyellow': 11, 'lightblue': 12, 'lightmagenta': 13, 'lightcyan': 14,
        'white': 15, 'grey0': 16, 'navyblue': 17, 'darkblue': 18, 'blue3': 19,
        'blue1': 21, 'darkgreen': 22, 'deepskyblue4': 25, 'dodgerblue3': 26,
        'dodgerblue2': 27, 'green4': 28, 'springgreen4': 29, 'turquoise4': 30,
        'deepskyblue3': 32, 'green3': 34, 'springgreen3': 35, 'cyan3': 36,
        'darkturquoise': 36, 'lightseagreen': 37, 'deepskyblue2': 38,
        'deepskyblue1': 39, 'green1': 40, 'springgreen2': 41, 'cyan2': 42,
        'darkslategray': 47, 'turquoise2': 44, 'green': 46, 'springgreen1': 48,
        'mediumspringgreen': 49, 'cyan1': 50, 'darkred': 52, 'deeppink4': 53,
        'purple4': 55, 'purple3': 56, 'blueviolet': 57, 'orange4': 58,
        'grey53': 59, 'mediumpurple': 60, 'slateblue3': 61, 'royalblue1': 63,
        'chartreuse4': 64, 'darkseagreen': 65, 'paleturquoise4': 66,
        'steelblue': 67, 'steelblue3': 68, 'cornflowerblue': 69,
        'chartreuse3': 76, 'seagreen': 78, 'mediumaquamarine': 79,
        'mediumslateblue': 81, 'slateblue': 87, 'orange': 94, 'lightsalmon': 95,
        'darkorange': 96, 'lightorange': 97, 'yellow': 100, 'lightyellow': 101,
        'greenyellow': 102, 'darkolivegreen': 58, 'yellowgreen': 106,
        'olivedrab': 106, 'lightgoldenrod': 107, 'tan': 108, 'darkkhaki': 108,
        'olive': 100, 'lighthoneydew': 119, 'darkgoldenrod': 130,
        'goldenrod': 136, 'gold1': 142, 'khaki': 143, 'lightgoldenrod1': 144,
        'navajowhite': 144, 'darkolivegreen1': 148, 'darkolivegreen2': 149,
        'lightgoldenrod2': 150, 'lightgoldenrod3': 151, 'lightgoldenrod4': 152,
        'darkgoldenrod1': 154, 'darkgoldenrod2': 155, 'darkgoldenrod3': 156,
        'darkgoldenrod4': 157, 'orange1': 166, 'orange2': 166, 'orange3': 172,
        'orange4': 172, 'red1': 196, 'red2': 160, 'red3': 160, 'red4': 124,
        'deeppink1': 198, 'deeppink2': 162, 'deeppink3': 162, 'deeppink4': 125,
        'magenta1': 201, 'magenta2': 165, 'magenta3': 165, 'magenta4': 125,
        'magenta': 201, 'darkmagenta': 90, 'violet': 135, 'plum': 176,
        'orchid': 170, 'mediumorchid': 134, 'darkorchid': 128, 'purple': 129,
        'mediumpurple': 104, 'thistle': 225, 'azure': 153, 'cyan': 51,
        'aqua': 51, 'turquoise': 80, 'lightcyan': 152, 'lightblue': 153,
        'powderblue': 153, 'skyblue': 153, 'lightskyblue': 153, 'steelblue': 117,
        'aliceblue': 159, 'ghostwhite': 189, 'lavender': 189, 'lightsteelblue': 147,
        'lightcyan': 195, 'paleturquoise': 159, 'beige': 230, 'honeydew': 194,
        'lavenderblush': 225, 'mistyrose': 224, 'whitesmoke': 255, 'gainsboro': 252,
        'lightgrey': 250, 'silver': 250, 'darkgrey': 238, 'grey': 244,
        'dimgrey': 240, 'lightslategrey': 248, 'slategrey': 244, 'darkslategrey': 235,
        'black': 16, 'charcoal': 235, 'darkslategray': 235, 'dimgray': 240
    }
    
    def normalize_color_name(color_name: str) -> str:
        """标准化颜色名称，去掉连字符"""
        return color_name.lower().replace('-', '')
    
    def parse_color(color_str: str, is_bg: bool = False) -> str:
        """解析颜色字符串为ANSI代码"""
        if not color_str:
            return ""
        
        # 处理背景色前缀
        if color_str.startswith('bg:'):
            color_str = color_str[3:]
            is_bg = True

        elif color_str.startswith('fg:'):
            color_str = color_str[3:]
        
        # 24位真彩色 (#RRGGBB)
        if color_str.startswith('#'):
            hex_color = color_str[1:]
            if len(hex_color) == 6:
                try:
                    r = int(hex_color[0:2], 16)
                    g = int(hex_color[2:4], 16)
                    b = int(hex_color[4:6], 16)
                    prefix = 48 if is_bg else 38
                    return f"{prefix};2;{r};{g};{b}"
                except ValueError:
                    return ""
        
        # 256色 (color:xxx)
        if color_str.startswith('color:'):
            try:
                color_num = int(color_str[6:])
                if 0 <= color_num <= 255:
                    prefix = 48 if is_bg else 38
                    return f"{prefix};5;{color_num}"
            except ValueError:
                return ""
        
        # 标准化颜色名称
        normalized = normalize_color_name(color_str)
        
        # 检查256色颜色名称
        if normalized in COLOR_256_NAMES:
            color_num = COLOR_256_NAMES[normalized]
            prefix = 48 if is_bg else 38
            return f"{prefix};5;{color_num}"
        
        # 检查标准ANSI颜色
        if normalized in COLOR_MAP:
            return str(COLOR_MAP[normalized])
        
        return ""
    
    def parse_style(style_str: str) -> List[str]:
        """解析样式字符串为ANSI代码列表"""
        if not style_str:
            return []
        
        codes = []
        styles = style_str.split()
        
        for style in styles:
            # 处理颜色和背景色
            if style.startswith('bg:') or style.startswith('#') or style.startswith('color:'):
                color_code = parse_color(style)
                if color_code:
                    codes.append(color_code)
            else:
                # 标准化样式名称并检查颜色
                normalized = normalize_color_name(style)
                color_code = parse_color(style)
                if color_code:
                    codes.append(color_code)
                elif normalized in COLOR_MAP:
                    codes.append(str(COLOR_MAP[normalized]))
            
            # 处理文本样式
            normalized_style = normalize_color_name(style)
            if normalized_style == 'bold':
                codes.append('1')
            elif normalized_style == 'italic':
                codes.append('3')
            elif normalized_style == 'underline':
                codes.append('4')
            elif normalized_style == 'strike':
                codes.append('9')
            elif normalized_style == 'blink':
                codes.append('5')
            elif normalized_style == 'reverse':
                codes.append('7')
            elif normalized_style == 'hidden':
                codes.append('8')
        
        return codes
    
    if not formatted_text:
        return ""
    
    result = []
    current_codes = set()
    
    for item in formatted_text:
        if len(item) == 2:
            style_str, text = item
        elif len(item) == 3:
            style_str, text, func = item
        else:
            style_str, text = '', ''

        new_codes = set(parse_style(style_str))
        
        # 如果样式发生变化，添加ANSI代码
        if new_codes != current_codes:
            if new_codes:
                # 按数字顺序排序，确保一致性
                sorted_codes = sorted(new_codes, key=lambda x: int(x.split(';')[0]))
                codes_str = ";".join(sorted_codes)
                result.append(f"\033[{codes_str}m")
            else:
                result.append("\033[0m")
            current_codes = new_codes
        
        # 添加文本内容
        if text:
            result.append(text)
    
    # 重置样式
    if current_codes:
        result.append("\033[0m")
    
    return "".join(result) 

def client_connected():
    return len(active_connections) > 0

def send_fullme(sender: str, text_message: str = "", fullme_url: str = "", times: int = 3, combine: bool = False):
    asyncio.ensure_future(loadAndSendFullme(sender, text_message, fullme_url, times, combine))

async def loadAndSendFullme(sender, text_msg: str, fullme_url: str, times: int = 3, combine: bool = False):
    fmadress = fullme_url.split("robot.php?filename=")[-1]
    url = f"http://fullme.pkuxkx.net/robot.php?filename={fmadress}"
    images = []
    client = ClientSession()
    for i in range(0, times):
        async with client.get(url) as response:
            if response.status != 200:
                continue

            text = await response.text()
            matches = re.search(r'src="\.([^"]+\.jpg)"', text)
            if not matches:
                continue

            img_url = "http://fullme.pkuxkx.net" + matches.group(1)
            
            # 解析URL获取文件名
            parsed_url = urlparse(img_url)
            filename = os.path.basename(unquote(parsed_url.path))
            # 创建fullme目录
            fullme_dir = os.path.join(os.path.dirname(__file__), 'fullme')
            os.makedirs(fullme_dir, exist_ok=True)
            # 本地文件路径
            local_img_path = os.path.join(fullme_dir, filename)
            # 下载图片
            try:
                async with ClientSession() as session:
                    async with session.get(img_url) as img_response:
                        if img_response.status == 200:
                            with open(local_img_path, 'wb') as f:
                                f.write(await img_response.read())
                            # 使用本地路径调用
                            if not combine:
                                await send_message_to_clients(sender, text_msg, local_img_path)
                            else:
                                images.append(local_img_path)

            except Exception as e:
                app.pymud.set_status(f"下载图片失败: {e}")
                continue

            await asyncio.sleep(0.5)

    await client.close()

    if combine:
        await send_message_to_clients(sender, text_msg, images)

def send_overview(sender: str, func_for_overview: callable):
    pymudapp = app.pymud
    if isinstance(pymudapp, PyMudApp):
        def onTimeTicker():
            if sender in pymudapp.sessions.keys():
                data = func_for_overview()
                asyncio.create_task(send_json_to_clients({
                    "sender": sender,
                    "action": "overview",
                    "connected": pymudapp.sessions[sender].connected,
                    "hooked": pymudapp.sessions[sender].getVariable("__websocket_hooked__", False),
                    "text": json.dumps(data, ensure_ascii = True)
                }))

        pymudapp.addTimerTickCallback(f"{sender}_overview", onTimeTicker)

def send_message(sender: str, text_message: str = "", img_url: str = "", action = "message"):
    asyncio.ensure_future(send_message_to_clients(sender, text_message, img_url, action))

async def send_message_to_clients(sender: str, text_message: str = "", img_url: Union[List | str] = "", action = "message"):
    """向所有已连接的WebSocket客户端发送消息
    Args:
        sender: 发送者名称
        text_message: 文本消息内容
        img_url: 图像链接信息
    """
    if img_url:
        if isinstance(img_url, str) and os.path.isfile(img_url):
            # 读取并编码图片文件
            with open(img_url, 'rb') as f:
                file_data = f.read()

            # 获取文件MIME类型
            mime_type, _ = mimetypes.guess_type(img_url)
            # 默认为PNG格式如果无法识别
            if not mime_type or not mime_type.startswith('image/'):
                mime_type = 'image/png'

            # 添加MIME类型前缀
            img_data = f"data:{mime_type};base64,{base64.b64encode(file_data).decode('utf-8')}"
            #img_data = base64.b64encode(file_data).decode('utf-8')
        elif isinstance(img_url, List) and len(img_url) > 0:
            img_data = []
            for s_img_url in img_url:
                if os.path.isfile(s_img_url):
                    # 读取并编码图片文件
                    with open(s_img_url, 'rb') as f:
                        file_data = f.read()

                    # 获取文件MIME类型
                    mime_type, _ = mimetypes.guess_type(s_img_url)
                    # 默认为PNG格式如果无法识别
                    if not mime_type or not mime_type.startswith('image/'):
                        mime_type = 'image/png'

                    # 添加MIME类型前缀
                    img_data.append(f"data:{mime_type};base64,{base64.b64encode(file_data).decode('utf-8')}")
        else:
            img_data = ""
    else:
        img_data = ""

    timestamp = datetime.now().isoformat()
    # 构建消息结构
    message = {
        "sender": sender,
        "timestamp": timestamp,
        "action": action,
        "text": text_message,
        "img": img_data
    }
    
    if client_connected():
        await send_json_to_clients(message)
    else:
        offline_buffer.append(message)

async def send_json_to_clients(raw_json: dict):
    """向所有已连接的WebSocket客户端原始JSON消息
    Args:
        raw_json: JSON字典
    """
    timestamp = datetime.now().isoformat()
    if not "timestamp" in raw_json.keys():
        raw_json["timestamp"] = timestamp

    json_message = json.dumps(raw_json)
    
    # 线程安全地获取当前连接列表
    async with connection_lock:
        current_connections = active_connections.copy()
    
    # 向所有连接发送消息
    for connection in current_connections:
        try:
            await connection.send_text(json_message)
        except:
            # 处理发送失败的连接
            async with connection_lock:
                if connection in active_connections:
                    active_connections.remove(connection)

# 添加消息处理函数
async def handle_websocket_message(message: dict):
    pymudapp = getattr(app, "pymud", None)
    if pymudapp and isinstance(pymudapp, PyMudApp):
        sender = message.get('sender')
        action = message.get("action")
        # 系统命令处理
        if sender == "system":
            # 发送给系统的消息
            if action == "change_session":
                session = message.get("session")
                if session in pymudapp.sessions.keys():
                    pymudapp.activate_session(session)

            elif action == "list_sessions":
                for name in pymudapp.sessions.keys():
                    message = {
                        "sender": "system",
                        "action": "add_session",
                        "session": name,
                        "text": "",
                        "img": ""
                    }
                    await send_json_to_clients(message)

            elif action == "command":
                # 当未有任何会话打开时，可以支持#session命令
                text = message.get('text', '')
                if text.startswith('#session'):
                    cmd_tuple = text[1:].split()
                    pymudapp.handle_session(*cmd_tuple[1:])
        
        # 其他消息应为都是发送给会话的消息，直接交由对应的会话执行即可。
        elif sender in pymudapp.sessions.keys():
            if action == "command":
                text = message.get("text" , "")
                session = pymudapp.sessions[sender]
                if isinstance(session, Session):
                    session.exec(f"#wa 1;{text}")

            elif action == "set":
                key = message.get("key", "")
                value = message.get("value", "")
                if key == "data":
                    enabled = True if value else False
                    hookSessionData(pymudapp.sessions[sender], enabled)

            elif action == "get":
                text = message.get("text" , "")
                if text == "status":
                    status_maker = app.pymud.sessions[sender].status_maker
                    if callable(status_maker):
                        status = status_maker()
                        #status = to_plain_text(status)
                        formmated_text = to_formatted_text(status)
                        status = formattedtext_to_ansi(formmated_text)
                        await send_message_to_clients(sender, status, action="status")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    async with connection_lock:
        active_connections.append(websocket)
    
    try:
        # 发送初始连接成功消息
        if len(offline_buffer) > 0:
            text_message = f"成功连接到 PYMUD {Settings.__version__}, websocket 插件版本 {PLUGIN_DESC['VERSION']}。存在缓存消息, 即将发送..."
        else:
            text_message = f"成功连接到 PYMUD {Settings.__version__}, websocket 插件版本 {PLUGIN_DESC['VERSION']}。"
        await send_message_to_clients(
            sender="system",
            text_message = text_message,
            img_url=""
        )

        if len(offline_buffer) > 0:
            for message in offline_buffer:
                await send_json_to_clients(message)
            offline_buffer.clear()

        # 消息处理循环 - 同时处理接收消息和定时发送
        while True:
            try:
                # 等待接收消息，超时10秒
                data = await asyncio.wait_for(websocket.receive_text(), timeout=2)
                message = json.loads(data)

                await handle_websocket_message(message)

                if FLAG_APP_EXITS:
                    break
                    
            except asyncio.TimeoutError:
                # 超时发送空消息保活
                async with connection_lock:
                    current_connections = active_connections.copy()

                if current_connections:
                    await send_message_to_clients(
                        sender="system",
                        text_message="",
                        img_url=""
                    )
                
            except json.JSONDecodeError:
                # 处理JSON解析错误
                await send_message_to_clients(
                    sender="system",
                    text_message="消息格式错误: 无效的JSON",
                    img_url=""
                )
            
    except WebSocketDisconnect:
        async with connection_lock:
            if websocket in active_connections:
                active_connections.remove(websocket)
    
    except Exception as e:
        # 记录未捕获的异常
        app.pymud.set_status(f"WebSocket错误: {str(e)}")

@app.get("/")
async def get(key: str = Query(None)):
    # 验证key参数
    if key != Settings.client.get("WEBSOCKET_PRIVATE_KEY", WEBSOCKET_PRIVATE_KEY):
        raise HTTPException(status_code=404, detail="Not Found")
    # 读取外部HTML文件内容
    html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "websocket.html")
    try:
        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="HTML模板文件未找到")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取HTML文件失败: {str(e)}")

@app.get("/ansi_up.min.js")
async def serve_ansi_up_js():
    file_path = os.path.join(os.path.dirname(__file__), "ansi_up.min.js")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="ansi_up.min.js file not found")
    return FileResponse(file_path, media_type="application/javascript")

async def start_uvicorn(pymudapp):
    from types import SimpleNamespace

    for name in ["uvicorn", "uvicorn.access"]:
        logging.getLogger(name).disabled = True

    # 将pymudapp赋值给app的pymud属性用作后续全局使用
    setattr(app, "pymud", pymudapp)

    ws = SimpleNamespace(
        server=None,
        connected=client_connected,
        sendText=send_message,
        sendFullme=send_fullme,
        sendOverview=send_overview
    )
    pymudapp.set_globals("ws", ws)

    async def try_start_server():
        max_retries = 5
        retry_delay = 1  # 1秒重试间隔
        current_port = PORT
        
        for attempt in range(max_retries):
            # 改进的端口检查函数
            def is_port_available(port):
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    try:
                        s.bind(('0.0.0.0', port))
                        s.close()
                        return True
                    except OSError:
                        return False

            if is_port_available(current_port):
                try:
                    config = uvicorn.Config(app, host="0.0.0.0", port=current_port, 
                                          access_log=False, log_level="error")
                    server = uvicorn.Server(config)
                    ws.server = server  # 更新server引用
                    
                    pymudapp.set_status(f"正在启动WebSocket服务，端口: {current_port}")
                    await server.serve()
                    return  # 成功启动则退出
                except Exception as e:
                    pymudapp.set_status(f"启动WebSocket服务失败: {str(e)}")
                    break
            else:
                pymudapp.set_status(f"端口{current_port}被占用，{retry_delay}秒后重试... (尝试 {attempt + 1}/{max_retries})")
                await asyncio.sleep(retry_delay)
                current_port += 1  # 确保端口号递增

        # 所有重试失败后的处理
        pymudapp.set_status(f"无法找到可用端口(从{PORT}到{current_port-1})，WebSocket服务未启动")
        pymudapp.set_globals("ws", None)

    # 启动重试任务，不阻塞主进程
    asyncio.create_task(try_start_server())


# 插件唯一名称
PLUGIN_NAME    = "websocket"

# 插件有关描述信息
PLUGIN_DESC = {
    "VERSION" : "2.0.4",
    "AUTHOR"  : "newstart",
    "RELEASE_DATE"  : "2025-08-09",
    "DESCRIPTION" : __doc__
}

def PLUGIN_PYMUD_START(app: PyMudApp):
    "PYMUD自动读取并加载插件时自动调用的函数， app为APP本体。该函数仅会在程序运行时，自动加载一次"
    asyncio.create_task(start_uvicorn(app))
    app.set_status(f"插件{PLUGIN_NAME}已加载!")

def sendRawToWs(session, id, line, wildcards):
    info = line.strip()
    if len(info) > 0:
        asyncio.create_task(send_message_to_clients(session.name, info, action = "data"))

func_writetobuffer = None

def hookSessionData(session: Session, enabled = True):
    if not hasattr(session, 'origin_writetobuffer'):
        session.origin_writetobuffer = session.writetobuffer

    cache_str = ""
    def wrapper(data: str, newline = False):
        func_writetobuffer = getattr(session, 'origin_writetobuffer')
        func_writetobuffer(data, newline)
        if client_connected():
            nonlocal cache_str
            cache_str += data
            newline = newline or data.endswith("\n")
            if newline:
                # 发送正文数据
                asyncio.create_task(send_message_to_clients(session.name, cache_str, action = "data"))
                cache_str = ""
                # 发送状态窗口数据
                status_maker = session.status_maker
                if callable(status_maker):
                    status = status_maker()
                    formmated_text = to_formatted_text(status)
                    status = formattedtext_to_ansi(formmated_text)
                    asyncio.create_task(send_message_to_clients(session.name, status, action = "status"))

    if enabled:
        session.writetobuffer = wrapper
        session.setVariable("__websocket_hooked__", True)
    else:
        session.writetobuffer = getattr(session, "origin_writetobuffer")
        session.setVariable("__websocket_hooked__", False)

def PLUGIN_SESSION_CREATE(session: Session):
    "在会话中加载插件时自动调用的函数， session为加载插件的会话。该函数在每一个会话创建时均被自动加载一次"
    message = {
        "sender": "system",
        "action": "add_session",
        "session": session.name,
        "text": "",
        "img": ""
    }
    asyncio.create_task(send_json_to_clients(message))
    # 这个触发器可以让服务器收到的每一行都发送到ws网页中
    Trigger(session, r"^.*$", id = "ws_info", priority = 50, raw = True, keepEval = True, onSuccess = partial(sendRawToWs, session), enabled = False)

def PLUGIN_SESSION_DESTROY(session: Session):
    "在会话中卸载插件时自动调用的函数， session为卸载插件的会话。卸载在每一个会话关闭时均被自动运行一次。"
    message = {
        "sender": "system",
        "action": "remove_session",
        "session": session.name,
        "text": "",
        "img": ""
    }
    asyncio.create_task(send_json_to_clients(message))
    session.delTrigger("ws_info")

    # 会话关闭时，清除状态回调
    session.application.removeTimerTickCallback(f"{session.name}_overview")

def PLUGIN_PYMUD_DESTROY(app: PyMudApp):
    "PYMUD自动卸载插件时自动调用的函数， app为APP本体。该函数仅会在程序运行时，自动卸载一次"
    global FLAG_APP_EXITS
    FLAG_APP_EXITS = True
    ws = app.get_globals("ws")
    if ws and hasattr(ws, "server"):
        server = ws.server
        if isinstance(server, uvicorn.Server) and server.started:
            app.create_background_task(server.shutdown())



