from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import Footer

from bashmage.storage import Command
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
        Binding("q", "quit_clean", "Quit"),
    ]

    def __init__(self, commands: list[Command]) -> None:
        super().__init__()
        self._commands = commands
        self._highlighted: Command | None = commands[0] if commands else None

    def compose(self) -> ComposeResult:
        yield SearchBar()
        with Horizontal(id="main"):
            yield CommandList(self._commands)
            yield DetailPanel()
        yield Footer()

    def on_search_bar_changed(self, event: SearchBar.Changed) -> None:
        self.query_one(CommandList).filter(event.value)

    def on_command_list_highlighted(self, event: CommandList.Highlighted) -> None:
        self._highlighted = event.command
        self.query_one(DetailPanel).show(event.command)

    async def on_command_list_selected(self, event: CommandList.Selected) -> None:
        await self._activate(event.command)

    def action_list_up(self) -> None:
        from textual.widgets import ListView
        self.query_one(ListView).action_cursor_up()

    def action_list_down(self) -> None:
        from textual.widgets import ListView
        self.query_one(ListView).action_cursor_down()

    async def action_select_command(self) -> None:
        if self._highlighted is not None:
            await self._activate(self._highlighted)

    def action_clear_search(self) -> None:
        self.query_one(SearchBar).clear()

    def action_quit_clean(self) -> None:
        self.exit(None)

    async def _activate(self, command: Command) -> None:
        if command.placeholders:
            result = await self.push_screen_wait(PlaceholderModal(command))
            if result is not None:
                self.exit(result)
        else:
            self.exit(command.command)
