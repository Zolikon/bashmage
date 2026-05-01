from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static

from bashmage.storage import Command


class PlaceholderModal(ModalScreen[str | None]):
    DEFAULT_CSS = """
    PlaceholderModal {
        align: center middle;
    }
    #modal-container {
        width: 60;
        background: $surface;
        border: solid $primary;
        padding: 1 2;
    }
    #modal-title {
        text-style: bold;
        margin-bottom: 1;
    }
    #modal-command {
        color: $text-muted;
        margin-bottom: 1;
    }
    #modal-buttons {
        margin-top: 1;
        align-horizontal: right;
    }
    """

    BINDINGS = [
        Binding("enter", "confirm", priority=True),
        Binding("escape", "cancel"),
    ]

    def __init__(self, command: Command) -> None:
        super().__init__()
        self._command = command

    def compose(self) -> ComposeResult:
        with Container(id="modal-container"):
            yield Static("Fill in placeholders", id="modal-title")
            yield Static(self._command.command, id="modal-command")
            for placeholder in self._command.placeholders:
                yield Label(placeholder.upper())
                yield Input(placeholder=placeholder, id=f"input-{placeholder}")
            with Horizontal(id="modal-buttons"):
                yield Button("Cancel", id="cancel", variant="default")
                yield Button("Confirm", id="confirm", variant="primary")

    def on_mount(self) -> None:
        first = self._command.placeholders
        if first:
            self.query_one(f"#input-{first[0]}", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(None)
        elif event.button.id == "confirm":
            self._try_confirm()

    def action_confirm(self) -> None:
        self._try_confirm()

    def action_cancel(self) -> None:
        self.dismiss(None)

    def _try_confirm(self) -> None:
        values: dict[str, str] = {}
        for placeholder in self._command.placeholders:
            widget = self.query_one(f"#input-{placeholder}", Input)
            if not widget.value.strip():
                widget.focus()
                return
            values[placeholder] = widget.value.strip()
        self.dismiss(self._command.fill(values))
