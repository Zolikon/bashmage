import pytest
from textual.app import App, ComposeResult
from textual.widgets import Input, Label
from bashmage.widgets.search_bar import SearchBar
from textual.widgets import ListView
from bashmage.storage import Command
from bashmage.widgets.command_list import CommandItem, CommandList
from bashmage.widgets.detail_panel import DetailPanel
from bashmage.app import BashMageApp


COMMANDS = [
    Command("git-status", "Show working tree status", "git status --short", tags=["git", "status"]),
    Command("docker-up", "Start docker services", "docker compose up -d", tags=["docker"]),
    Command("kill-port", "Kill process on a port", "kill -9 $(lsof -t -i:{port})", tags=["network", "ports"]),
]

COMMANDS_WITH_SHORTCUTS = [
    Command("git-status", "Show working tree status", "git status --short", tags=["git"], shortcut="gs"),
    Command("docker-up", "Start docker services", "docker compose up -d", tags=["docker"], shortcut="du"),
    Command("kill-port", "Kill process on a port", "kill -9 $(lsof -t -i:{port})", tags=["network", "ports"]),
]


class _ListApp(App):
    def compose(self) -> ComposeResult:
        yield CommandList(COMMANDS)


class _ShortcutListApp(App):
    def compose(self) -> ComposeResult:
        yield CommandList(COMMANDS_WITH_SHORTCUTS)


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


async def test_command_list_filter_by_tag_exact():
    app = _ListApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.query_one(CommandList).filter("#git")
        await pilot.pause()
        items = app.query_one(ListView).children
        assert len(items) == 1


async def test_command_list_filter_by_tag_partial():
    # "git" matches both tag "git" and tag "gitcommands" if present; here matches tag "git"
    app = _ListApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.query_one(CommandList).filter("#net")
        await pilot.pause()
        items = app.query_one(ListView).children
        assert len(items) == 1  # only kill-port has "network" tag


async def test_command_list_filter_combined_text_and_tag():
    app = _ListApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.query_one(CommandList).filter("status #git")
        await pilot.pause()
        items = app.query_one(ListView).children
        assert len(items) == 1


async def test_command_list_filter_combined_no_match():
    app = _ListApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.query_one(CommandList).filter("status #docker")
        await pilot.pause()
        items = app.query(CommandItem)
        assert len(items) == 0


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


_SAMPLE_COMMANDS = [
    Command("git-status", "Show working tree status", "git status --short"),
    Command("kill-port", "Kill process on a port", "kill -9 $(lsof -t -i:{port})"),
]


async def test_app_renders_search_and_list():
    app = BashMageApp(_SAMPLE_COMMANDS)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.query_one(SearchBar) is not None
        assert app.query_one(CommandList) is not None
        assert app.query_one(DetailPanel) is not None


async def test_app_q_exits_with_none():
    app = BashMageApp(_SAMPLE_COMMANDS)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("q")
        await pilot.pause()
    assert app.return_value is None


async def test_app_enter_on_no_placeholder_command_exits_with_command():
    app = BashMageApp(_SAMPLE_COMMANDS)
    async with app.run_test() as pilot:
        await pilot.pause()
        # git-status is first, no placeholders
        await pilot.press("enter")
        await pilot.pause()
    assert app.return_value == "git status --short"


async def test_app_typing_filters_list():
    app = BashMageApp(_SAMPLE_COMMANDS)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("k", "i", "l", "l")
        await pilot.pause()
        items = app.query_one(ListView).children
        assert len(items) == 1


async def test_app_escape_clears_search():
    app = BashMageApp(_SAMPLE_COMMANDS)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("g", "i", "t")
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
        assert app.query_one(Input).value == ""


async def test_command_list_filter_matches_shortcut():
    app = _ShortcutListApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.query_one(CommandList).filter("gs")
        await pilot.pause()
        items = app.query(CommandItem)
        assert len(items) == 1
        assert items[0].command.shortcut == "gs"


async def test_command_list_filter_matches_second_shortcut():
    app = _ShortcutListApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.query_one(CommandList).filter("du")
        await pilot.pause()
        items = app.query(CommandItem)
        assert len(items) == 1
        assert items[0].command.shortcut == "du"


async def test_command_list_filter_command_without_shortcut_still_matches_by_name():
    app = _ShortcutListApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.query_one(CommandList).filter("kill")
        await pilot.pause()
        items = app.query(CommandItem)
        assert len(items) == 1
        assert items[0].command.name == "kill-port"


async def test_command_item_renders_shortcut_after_name():
    cmd = Command("switch-branch", "Switch git branch", "git checkout {branch}", shortcut="sw")

    class _ItemApp(App):
        def compose(self) -> ComposeResult:
            yield CommandList([cmd])

    app = _ItemApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        label = app.query_one(CommandItem).query_one(Label)
        rendered = str(label.render())
        assert "switch-branch" in rendered
        assert "[sw]" in rendered


async def test_command_item_no_shortcut_renders_name_only():
    cmd = Command("git-status", "Show status", "git status")

    class _ItemApp(App):
        def compose(self) -> ComposeResult:
            yield CommandList([cmd])

    app = _ItemApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        label = app.query_one(CommandItem).query_one(Label)
        rendered = str(label.render())
        assert "git-status" in rendered
        assert "[" not in rendered

