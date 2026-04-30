from textual.app import ComposeResult
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Input


class SearchBar(Widget):
    DEFAULT_CSS = """
    SearchBar {
        height: 3;
        padding: 0 1;
    }
    """

    class Changed(Message):
        def __init__(self, value: str) -> None:
            super().__init__()
            self.value = value

    def compose(self) -> ComposeResult:
        yield Input(placeholder="search commands...")

    def on_mount(self) -> None:
        self.query_one(Input).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        self.post_message(self.Changed(event.value))

    def clear(self) -> None:
        self.query_one(Input).value = ""
