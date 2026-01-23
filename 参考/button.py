from settings import Settings
from prompt_toolkit.widgets import Button
from prompt_toolkit.layout.containers import VSplit

class Configuration:
    def __init__(self, session, *args, **kwargs):
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
                self._startJob(1, 2, [3])

        # 创建按钮
        new_button = Button(text='新按钮', handler=startJobFn)

        # 将按钮添加到右侧
        # 这里假设你使用 VSplit 来布局，将按钮添加到右侧
        layout = VSplit([
            # 这里可以是你原来的内容
            # ... 原有代码 ...
            new_button
        ])

        return layout
