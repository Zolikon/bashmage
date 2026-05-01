import pytest
from textual.app import App, ComposeResult
from textual.widgets import Input
from bashmage.widgets.search_bar import SearchBar
from textual.widgets import ListView
from bashmage.storage import Command
from bashmage.widgets.command_list import CommandList
from bashmage.widgets.detail_panel import DetailPanel


COMMANDS = [
    Command("git-status", "Show working tree status", "git status --short"),
    Command("docker-up", "Start docker services", "docker compose up -d"),
    Command("kill-port", "Kill process on a port", "kill -9 $(lsof -t -i:{port})"),
]


class _ListApp(App):
    def compose(self) -> ComposeResult:
        yield CommandList(COMMANDS)


class _SearchApp(App):
    def compose(self) -> ComposeResult:
        yield SearchBar()


async def test_search_bar_input_receives_keystrokes():
    app = _SearchApp()
    async with app.run_test() as pilot:
        await pilot.press("g", "i", "t")
        await pilot.pause()
        assert app.query_one(Input).value == "git"


async def test_search_bar_clear_empties_input():
    app = _SearchApp()
    async with app.run_test() as pilot:
        await pilot.press("g", "i", "t")
        await pilot.pause()
        app.query_one(SearchBar).clear()
        await pilot.pause()
        assert app.query_one(Input).value == ""


async def test_command_list_shows_all_commands_initially():
    app = _ListApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        items = app.query_one(ListView).children
        assert len(items) == 3


async def test_command_list_filter_reduces_items():
    app = _ListApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.query_one(CommandList).filter("git")
        await pilot.pause()
        items = app.query_one(ListView).children
        assert len(items) == 1


async def test_command_list_filter_matches_description():
    app = _ListApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.query_one(CommandList).filter("docker")
        await pilot.pause()
        items = app.query_one(ListView).children
        assert len(items) == 1


async def test_command_list_filter_empty_string_shows_all():
    app = _ListApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.query_one(CommandList).filter("git")
        await pilot.pause()
        app.query_one(CommandList).filter("")
        await pilot.pause()
        items = app.query_one(ListView).children
        assert len(items) == 3


async def test_command_list_highlighted_returns_correct_command():
    highlighted = []

    class _TrackApp(App):
        def compose(self) -> ComposeResult:
            yield CommandList(COMMANDS)

        def on_command_list_highlighted(self, event: CommandList.Highlighted) -> None:
            highlighted.append(event.command)

    app = _TrackApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        assert len(highlighted) > 0
        assert highlighted[-1].name == "git-status"


async def test_command_list_selected_returns_correct_command():
    selected = []

    class _SelectApp(App):
        def compose(self) -> ComposeResult:
            yield CommandList(COMMANDS)

        def on_command_list_selected(self, event: CommandList.Selected) -> None:
            selected.append(event.command)
            self.exit()

    app = _SelectApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
    assert len(selected) == 1
    assert selected[0].name == "git-status"


class _DetailApp(App):
    def compose(self) -> ComposeResult:
        yield DetailPanel()


async def test_detail_panel_show_updates_content():
    cmd = Command("kill-port", "Kill port", "kill -9 $(lsof -t -i:{port})")
    app = _DetailApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.query_one(DetailPanel).show(cmd)
        await pilot.pause()
        from textual.widgets import Static
        content = str(app.query_one("#command-preview", Static).render())
        assert "{port}" in content


