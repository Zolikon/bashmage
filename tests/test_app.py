import pytest
from textual.app import App, ComposeResult
from textual.widgets import Input
from bashmage.widgets.search_bar import SearchBar


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
