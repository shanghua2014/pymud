from prompt_toolkit.layout import AnyContainer, HSplit
from prompt_toolkit.layout.dimension import D
from prompt_toolkit.widgets import TextArea, Label
from pymud.dialogs import BasicDialog, EasternButton
from pymud import Command

class InputDialog(BasicDialog):
    def __init__(self, title = "请输入"):
        self.textInput = TextArea(name = "input", text="", multiline=False, wrap_lines=False, height = 2, dont_extend_height=True, width = D(preferred=10), focus_on_click=True, read_only=False)
        super().__init__(title, True)
        
    def create_body(self) -> AnyContainer:
        body = HSplit([
            Label(" 请输入:"),
            self.textInput
        ])
        return body
    
    def create_buttons(self):
        ok_button = EasternButton(text="确定", handler=self.btn_ok_clicked)
        cancel_button = EasternButton(text="取消", handler=(lambda: self.set_done(False)))
        return [ok_button, cancel_button]
    
    def btn_ok_clicked(self):
        input = self.textInput.text
        self.set_done(input)
        

class CmdDialogInput(Command):
    def __init__(self, session, patterns = r"^input\s*-chihe$", *args, **kwargs):
        super().__init__(session, patterns, *args, **kwargs)

    async def execute(self, cmd, *args, **kwargs):
        input_dialog = InputDialog("是否喜欢我：1是，0否")
        input = await self.session.application.show_dialog_as_float(input_dialog)
        return input

class Configuration:
    def __init__(self, session):
        self.session = session

        cmd_input = CmdDialogInput(session, id = "cmd_inp")
        session.addCommand(cmd_input)