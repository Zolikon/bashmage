from textual.widgets import Input

from bashmage.app_placeholder import PlaceholderApp
from bashmage.storage import Command


async def test_placeholder_app_confirm_returns_filled_command():
    cmd = Command("kill-port", "Kill port", "kill -9 $(lsof -t -i:{port})")
    app = PlaceholderApp(cmd)
    async with app.run_test() as pilot:
        await pilot.pause()
        port_input = app.screen.query_one("#input-port", Input)
        port_input.value = "3000"
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
    assert app.return_value == "kill -9 $(lsof -t -i:3000)"


async def test_placeholder_app_escape_returns_none():
    cmd = Command("kill-port", "Kill port", "kill -9 $(lsof -t -i:{port})")
    app = PlaceholderApp(cmd)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
    assert app.return_value is None


async def test_placeholder_app_cancel_button_returns_none():
    cmd = Command("kill-port", "Kill port", "kill -9 $(lsof -t -i:{port})")
    app = PlaceholderApp(cmd)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.click("#cancel")
        await pilot.pause()
    assert app.return_value is None
