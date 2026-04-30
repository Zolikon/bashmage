from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static

from bashmage.storage import Command


class DetailPanel(Widget):
    DEFAULT_CSS = """
    DetailPanel {
        width: 1fr;
        padding: 1 2;
    }
    #command-preview {
        color: $success;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("", id="command-preview")

    def show(self, command: Command) -> None:
        self.query_one("#command-preview", Static).update(command.command)
