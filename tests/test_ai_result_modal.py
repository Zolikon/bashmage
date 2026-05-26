import time
import pytest
from unittest.mock import MagicMock
from textual.app import App
from textual.widgets import Static

from bashmage.ollama import OllamaClient, OllamaError
from bashmage.storage import Command
from bashmage.widgets.ai_result_modal import AIResultModal


class _ModalApp(App):
    def __init__(self, query: str, client: OllamaClient) -> None:
        super().__init__()
        self._query = query
        self._client = client
        self.result = "NOT_SET"

    def on_mount(self) -> None:
        self.push_screen(AIResultModal(self._query, self._client), self._done)

    def _done(self, r) -> None:
        self.result = r
        self.exit()


async def test_ai_result_modal_shows_loading_on_mount():
    client = MagicMock(spec=OllamaClient)
    client.generate.side_effect = lambda _: time.sleep(10)

    app = _ModalApp("list docker", client)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.screen.query_one("#loading").display is True
        assert app.screen.query_one("#command-preview").display is False
        assert app.screen.query_one("#modal-buttons").display is False
    app.workers.cancel_all()


async def test_ai_result_modal_shows_command_after_generation():
    client = MagicMock(spec=OllamaClient)
    client.generate.return_value = "docker ps -a"

    app = _ModalApp("list docker containers", client)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.pause(0.1)
        await pilot.pause()
        preview = app.screen.query_one("#command-preview", Static)
        assert preview.display is True
        assert "docker ps -a" in str(preview.render())


async def test_ai_result_modal_accept_returns_command_with_correct_fields():
    client = MagicMock(spec=OllamaClient)
    client.generate.return_value = "docker ps -a"

    app = _ModalApp("list docker containers", client)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.pause(0.1)
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()

    assert isinstance(app.result, Command)
    assert app.result.command == "docker ps -a"
    assert app.result.description == "list docker containers"
    assert app.result.name == "ai-generated"


async def test_ai_result_modal_escape_returns_none():
    client = MagicMock(spec=OllamaClient)
    client.generate.return_value = "docker ps -a"

    app = _ModalApp("list docker", client)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()

    assert app.result is None


async def test_ai_result_modal_enter_during_loading_is_noop():
    client = MagicMock(spec=OllamaClient)
    client.generate.side_effect = lambda _: time.sleep(10)

    app = _ModalApp("list docker", client)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        # Modal still on screen — enter was ignored
        assert app.result == "NOT_SET"
    app.workers.cancel_all()


async def test_ai_result_modal_shows_error_message_on_failure():
    client = MagicMock(spec=OllamaClient)
    client.generate.side_effect = OllamaError("Cannot reach Ollama at http://localhost:11434")

    app = _ModalApp("list docker", client)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.pause(0.1)
        await pilot.pause()
        error_widget = app.screen.query_one("#error-msg", Static)
        assert error_widget.display is True
        assert "Cannot reach Ollama" in str(error_widget.render())


async def test_ai_result_modal_error_hides_loading_indicator():
    client = MagicMock(spec=OllamaClient)
    client.generate.side_effect = OllamaError("Cannot reach Ollama")

    app = _ModalApp("list docker", client)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.pause(0.1)
        await pilot.pause()
        assert app.screen.query_one("#loading").display is False


async def test_ai_result_modal_command_with_placeholder_is_preserved():
    client = MagicMock(spec=OllamaClient)
    client.generate.return_value = "docker ps -a | grep {port}"

    app = _ModalApp("find containers on port", client)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.pause(0.1)
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()

    assert app.result.command == "docker ps -a | grep {port}"
    assert app.result.placeholders == ["port"]
