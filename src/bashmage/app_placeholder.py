from textual.app import App

from bashmage.storage import Command
from bashmage.widgets.placeholder_modal import PlaceholderModal


class PlaceholderApp(App[str | None]):
    def __init__(self, command: Command) -> None:
        super().__init__()
        self._command = command

    def on_mount(self) -> None:
        self.push_screen(PlaceholderModal(self._command), self.exit)
