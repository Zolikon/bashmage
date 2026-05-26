from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, LoadingIndicator, Static
from textual.worker import Worker, WorkerState

from bashmage.ollama import OllamaClient
from bashmage.storage import Command


class AIResultModal(ModalScreen[Command | None]):
    DEFAULT_CSS = """
    AIResultModal {
        align: center middle;
    }
    #modal-container {
        width: 70;
        background: $surface;
        border: solid $primary;
        padding: 1 2;
    }
    #modal-title {
        text-style: bold;
        margin-bottom: 1;
    }
    #command-preview {
        color: $success;
        margin-bottom: 1;
    }
    #error-msg {
        color: $error;
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

    def __init__(self, query: str, client: OllamaClient) -> None:
        super().__init__()
        self._query = query
        self._client = client
        self._generated: Command | None = None
        self._worker: Worker | None = None

    def compose(self) -> ComposeResult:
        with Container(id="modal-container"):
            yield Static("✨ AI-generated command", id="modal-title")
            yield LoadingIndicator(id="loading")
            yield Static("", id="command-preview")
            yield Static("", id="error-msg")
            with Horizontal(id="modal-buttons"):
                yield Button("Cancel", id="cancel", variant="default")
                yield Button("Accept", id="accept", variant="primary")

    def on_mount(self) -> None:
        self.query_one("#command-preview").display = False
        self.query_one("#error-msg").display = False
        self.query_one("#modal-buttons").display = False
        self._worker = self.run_worker(self._fetch, thread=True, exit_on_error=False)

    def _fetch(self) -> str:
        return self._client.generate(self._query)

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        if event.worker is not self._worker:
            return
        if event.worker.state == WorkerState.SUCCESS:
            self._show_result(event.worker.result)
        elif event.worker.state == WorkerState.ERROR:
            self._show_error(str(event.worker.error))

    def _show_result(self, command_text: str) -> None:
        self._generated = Command(
            name="ai-generated",
            description=self._query,
            command=command_text,
        )
        self.query_one("#loading").display = False
        self.query_one("#command-preview", Static).update(command_text)
        self.query_one("#command-preview").display = True
        self.query_one("#modal-buttons").display = True
        self.query_one("#accept", Button).focus()

    def _show_error(self, msg: str) -> None:
        self.query_one("#loading").display = False
        self.query_one("#error-msg", Static).update(f"✗ {msg}")
        self.query_one("#error-msg").display = True
        self.query_one("#modal-buttons").display = True
        self.query_one("#accept", Button).disabled = True
        self.query_one("#cancel", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(None)
        elif event.button.id == "accept":
            self.dismiss(self._generated)

    def action_confirm(self) -> None:
        if self._generated is not None:
            self.dismiss(self._generated)

    def action_cancel(self) -> None:
        self.dismiss(None)
