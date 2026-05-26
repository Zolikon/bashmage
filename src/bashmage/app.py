from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import Footer

from bashmage.ollama import OllamaClient
from bashmage.storage import AIConfig, Command
from bashmage.widgets.ai_result_modal import AIResultModal
from bashmage.widgets.command_list import CommandList
from bashmage.widgets.detail_panel import DetailPanel
from bashmage.widgets.placeholder_modal import PlaceholderModal
from bashmage.widgets.search_bar import SearchBar


class BashMageApp(App[str | None]):
    CSS = """
    Screen {
        layout: vertical;
    }
    #main {
        layout: horizontal;
        height: 1fr;
    }
    """

    BINDINGS = [
        Binding("up", "list_up", "Up", priority=True),
        Binding("down", "list_down", "Down", priority=True),
        Binding("enter", "select_command", "Select", priority=True),
        Binding("escape", "clear_search", "Clear"),
        Binding("q", "quit_clean", "Quit", show=False),
        Binding("ctrl+q", "quit_clean", "Quit"),
    ]

    def __init__(
        self,
        commands: list[Command],
        initial_query: str = "",
        ai_config: AIConfig | None = None,
    ) -> None:
        super().__init__()
        self._commands = commands
        self._initial_query = initial_query
        self._ai_config = ai_config
        self._highlighted: Command | None = commands[0] if commands else None

    def compose(self) -> ComposeResult:
        yield SearchBar(initial_value=self._initial_query)
        with Horizontal(id="main"):
            yield CommandList(self._commands)
            yield DetailPanel()
        yield Footer()

    def on_mount(self) -> None:
        if self._initial_query:
            self.query_one(CommandList).filter(self._initial_query)

    def on_search_bar_changed(self, event: SearchBar.Changed) -> None:
        if self._ai_config is not None and event.value.startswith("?"):
            self.query_one(CommandList).show_ai_hint()
        else:
            self.query_one(CommandList).filter(event.value)

    def on_command_list_highlighted(self, event: CommandList.Highlighted) -> None:
        self._highlighted = event.command
        if event.command is not None:
            self.query_one(DetailPanel).show(event.command)
        else:
            self.query_one(DetailPanel).clear()

    def on_command_list_selected(self, event: CommandList.Selected) -> None:
        self._activate(event.command)

    def action_list_up(self) -> None:
        from textual.widgets import ListView
        self.query_one(ListView).action_cursor_up()

    def action_list_down(self) -> None:
        from textual.widgets import ListView
        self.query_one(ListView).action_cursor_down()

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        from textual.screen import ModalScreen
        if action == "select_command":
            return not isinstance(self.screen, ModalScreen)
        return True

    def action_select_command(self) -> None:
        from textual.widgets import Input
        query = self.query_one(SearchBar).query_one(Input).value
        if self._ai_config is not None and query.startswith("?"):
            natural = query[1:].strip()
            if natural and len(natural) <= 1000:
                client = OllamaClient(self._ai_config.base_url, self._ai_config.model)
                self.push_screen(AIResultModal(natural, client), self._on_ai_result)
            return
        cmd = self.query_one(CommandList).get_highlighted_command()
        if cmd is not None:
            self._activate(cmd)

    def _on_ai_result(self, command: Command | None) -> None:
        if command is not None:
            self._activate(command)

    def action_clear_search(self) -> None:
        self.query_one(SearchBar).clear()

    def action_quit_clean(self) -> None:
        self.exit(None)

    def _activate(self, command: Command) -> None:
        if command.placeholders:
            def on_dismiss(result: str | None) -> None:
                if result is not None:
                    self.exit(result)
            self.push_screen(PlaceholderModal(command), on_dismiss)
        else:
            self.exit(command.command)
