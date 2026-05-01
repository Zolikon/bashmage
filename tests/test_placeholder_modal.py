import pytest
from textual.app import App, ComposeResult
from textual.widgets import Input

from bashmage.storage import Command
from bashmage.widgets.placeholder_modal import PlaceholderModal


class _ModalApp(App):
    def __init__(self, command: Command) -> None:
        super().__init__()
        self._command = command
        self.result: str | None = "NOT_SET"

    def on_mount(self) -> None:
        self.push_screen(PlaceholderModal(self._command), self._on_modal_done)

    def _on_modal_done(self, result: str | None) -> None:
        self.result = result
        self.exit(result)


async def test_placeholder_modal_confirm_returns_filled_command():
    cmd = Command("kill-port", "Kill port", "kill -9 $(lsof -t -i:{port})")
    app = _ModalApp(cmd)
    async with app.run_test() as pilot:
        await pilot.pause()
        # Query from the active modal screen, not from the app's default screen
        port_input = app.screen.query_one("#input-port", Input)
        port_input.value = "3000"
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
    assert app.result == "kill -9 $(lsof -t -i:3000)"


async def test_placeholder_modal_empty_field_blocks_confirm():
    cmd = Command("kill-port", "Kill port", "kill -9 $(lsof -t -i:{port})")
    app = _ModalApp(cmd)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        # Modal is still on screen because the empty field blocked dismissal
        assert app.result == "NOT_SET"


async def test_placeholder_modal_escape_returns_none():
    cmd = Command("kill-port", "Kill port", "kill -9 $(lsof -t -i:{port})")
    app = _ModalApp(cmd)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
    assert app.result is None
