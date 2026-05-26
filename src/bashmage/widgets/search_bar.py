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

    def __init__(self, initial_value: str = "") -> None:
        super().__init__()
        self._initial_value = initial_value

    def compose(self) -> ComposeResult:
        yield Input(value=self._initial_value, placeholder="search commands...")

    def on_mount(self) -> None:
        self.query_one(Input).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        self.post_message(self.Changed(event.value))

    def clear(self) -> None:
        self.query_one(Input).value = ""

    @property
    def value(self) -> str:
        return self.query_one(Input).value
