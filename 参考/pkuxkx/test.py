
import functools
from pymud import Alias, Trigger, SimpleCommand, SimpleTrigger, SimpleAlias, Timer
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType
from prompt_toolkit.formatted_text import to_formatted_text, HTML
from prompt_toolkit import print_formatted_text
from settings import Settings

class Configuration:
    def __init__(self, session,*args, **kwargs):
        super().__init__()
        self.session = session
        self._triggers = {}
        
        self.session.info('\x1b[1;36m=== 新手任务 ===')
        self._initTriggers()

    def _initTriggers(self):
        this = self.session
        this.status_maker = self.status_window
        this.addTriggers(self._triggers)


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
                    self.session.info('【开始打工】')
                    # self.iseat = await confirm.CmdDialogInput.execute(self,'input -chihe')
                    # self.session.setVariable('iseat', iseat)
                    self._startJob(1,2,[3]) # ***

            # html = HTML('<aaa>Hello</aaa> <bbb>world</bbb>!')
            # text = to_formatted_text(html, style='class:my_html bg:#00ff00 italic')
            # formatted_list.append((Settings.styles["yellow"], "。。。...\n", functools.partial(startJobFn)))
            # formatted_list.append((Settings.styles["datie"], "【打铁】\n", functools.partial(dtFn)))
            # formatted_list.append((Settings.styles["peiyao"], "【配药】\n", functools.partial(pyFn)))
            # formatted_list.append((Settings.styles["stop"], "【停止所有机器】", functools.partial(stopFn)))
            # formatted_list.append(("", "\n"))
            # formatted_list.append(("", "\n"))
            # formatted_list.append((Settings.styles["stop"], f" 本次连接统计：工作完成次数{self.jobTotal}，获得经验{self.jobExp}，获得潜能{self.jobQn}"))
            return formatted_list