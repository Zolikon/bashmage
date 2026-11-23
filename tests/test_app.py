import pytest
from textual.app import App, ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Input, Label, Static
from unittest.mock import MagicMock, patch
from bashmage.widgets.search_bar import SearchBar
from textual.widgets import ListView
from bashmage.storage import AIConfig, Command
from bashmage.widgets.command_list import CommandItem, CommandList
from bashmage.widgets.detail_panel import DetailPanel
from bashmage.app import BashMageApp
from bashmage.ollama import OllamaClient


_AI_CONFIG = AIConfig(model="llama3.2", base_url="http://localhost:11434")


COMMANDS = [
    Command(
        "git-status",
        "Show working tree status",
        "git status --short",
        tags=["git", "status"],
    ),
    Command(
        "docker-up", "Start docker services", "docker compose up -d", tags=["docker"]
    ),
    Command(
        "kill-port",
        "Kill process on a port",
        "kill -9 $(lsof -t -i:{port})",
        tags=["network", "ports"],
    ),
]

COMMANDS_WITH_SHORTCUTS = [
    Command(
        "git-status",
        "Show working tree status",
        "git status --short",
        tags=["git"],
        shortcut="gs",
    ),
    Command(
        "docker-up",
        "Start docker services",
        "docker compose up -d",
        tags=["docker"],
        shortcut="du",
    ),
    Command(
        "kill-port",
        "Kill process on a port",
        "kill -9 $(lsof -t -i:{port})",
        tags=["network", "ports"],
    ),
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
    cmd = Command(
        "switch-branch", "Switch git branch", "git checkout {branch}", shortcut="sw"
    )

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


async def test_search_bar_initial_value_is_shown():
    class _App(App):
        def compose(self) -> ComposeResult:
            yield SearchBar(initial_value="git")

    app = _App()
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.query_one(Input).value == "git"


async def test_search_bar_no_initial_value_is_empty():
    class _App(App):
        def compose(self) -> ComposeResult:
            yield SearchBar()

    app = _App()
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.query_one(Input).value == ""


async def test_app_initial_query_filters_list():
    commands = [
        Command("git-status", "Show status", "git status"),
        Command("docker-up", "Start docker", "docker compose up -d"),
    ]
    app = BashMageApp(commands, initial_query="git")
    async with app.run_test() as pilot:
        await pilot.pause()
        items = app.query_one(ListView).children
        assert len(items) == 1


async def test_app_initial_query_prefills_search_bar():
    commands = [
        Command("git-status", "Show status", "git status"),
        Command("docker-up", "Start docker", "docker compose up -d"),
    ]
    app = BashMageApp(commands, initial_query="git")
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.query_one(Input).value == "git"


async def test_app_no_initial_query_shows_all_commands():
    commands = [
        Command("git-status", "Show status", "git status"),
        Command("docker-up", "Start docker", "docker compose up -d"),
    ]
    app = BashMageApp(commands)
    async with app.run_test() as pilot:
        await pilot.pause()
        items = app.query_one(ListView).children
        assert len(items) == 2


async def test_command_list_show_ai_hint_renders_one_non_command_item():
    app = _ListApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.query_one(CommandList).show_ai_hint()
        await pilot.pause()
        lv = app.query_one(ListView)
        assert len(lv.children) == 1
        assert not isinstance(lv.children[0], CommandItem)


async def test_command_list_show_ai_hint_clears_highlighted_command():
    app = _ListApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.query_one(CommandList).show_ai_hint()
        await pilot.pause()
        assert app.query_one(CommandList).get_highlighted_command() is None


async def test_app_question_prefix_with_ai_config_shows_ai_hint():
    app = BashMageApp(_SAMPLE_COMMANDS, ai_config=_AI_CONFIG)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("?")
        await pilot.pause()
        items = app.query(CommandItem)
        assert len(items) == 0
        lv = app.query_one(ListView)
        assert len(lv.children) == 1


async def test_app_question_prefix_without_ai_config_filters_normally():
    app = BashMageApp(_SAMPLE_COMMANDS)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("?")
        await pilot.pause()
        items = app.query(CommandItem)
        assert len(items) == 0
        lv = app.query_one(ListView)
        assert len(lv.children) == 1
        assert not isinstance(lv.children[0], CommandItem)


async def test_app_question_enter_with_ai_config_pushes_modal():
    with patch.object(OllamaClient, "generate", return_value="docker ps"):
        app = BashMageApp(_SAMPLE_COMMANDS, ai_config=_AI_CONFIG)
        async with app.run_test() as pilot:
            await pilot.pause()
            for ch in "?list docker":
                await pilot.press(ch)
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()
            assert isinstance(app.screen, ModalScreen)
            app.workers.cancel_all()
            await pilot.pause()


async def test_app_question_enter_empty_query_is_noop():
    app = BashMageApp(_SAMPLE_COMMANDS, ai_config=_AI_CONFIG)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("?")
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        assert not isinstance(app.screen, ModalScreen)


async def test_app_question_enter_query_over_1000_chars_is_noop():
    app = BashMageApp(_SAMPLE_COMMANDS, ai_config=_AI_CONFIG)
    long_query = "?" + "x" * 1001
    async with app.run_test() as pilot:
        await pilot.pause()
        app.query_one(SearchBar).query_one(Input).value = long_query
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        assert not isinstance(app.screen, ModalScreen)


async def test_app_shows_model_info_when_ai_configured():
    app = BashMageApp(_SAMPLE_COMMANDS, ai_config=_AI_CONFIG)
    async with app.run_test() as pilot:
        await pilot.pause()
        info = app.query_one("#ai-model-info", Static)
        assert "llama3.2" in str(info.render())


async def test_app_no_model_info_without_ai_config():
    app = BashMageApp(_SAMPLE_COMMANDS)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert len(list(app.query("#ai-model-info"))) == 0


async def test_app_ai_result_with_placeholder_pushes_placeholder_modal():
    from bashmage.widgets.placeholder_modal import PlaceholderModal

    with patch.object(OllamaClient, "generate", return_value="docker ps | grep {port}"):
        app = BashMageApp(_SAMPLE_COMMANDS, ai_config=_AI_CONFIG)
        async with app.run_test() as pilot:
            await pilot.pause()
            for ch in "?find containers":
                await pilot.press(ch)
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()
            await pilot.pause(0.1)
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()
            assert isinstance(app.screen, PlaceholderModal)
            app.workers.cancel_all()
            await pilot.pause()
