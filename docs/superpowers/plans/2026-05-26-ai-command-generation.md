# AI Command Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Ollama-backed AI command generation triggered by `?` prefix in the search bar, feeding the result into the existing placeholder and command-output flow.

**Architecture:** `?query` + Enter in `BashMageApp` constructs an `OllamaClient` and pushes `AIResultModal`, which fires a Textual worker thread, displays a spinner then the result, and dismisses with a `Command` object that `_activate()` handles identically to list-selected commands. The feature gates on an `[ai]` section in `commands.toml`; absent config = no change in behaviour.

**Tech Stack:** Python 3.11+ stdlib (`urllib.request`, `json`), Textual TUI framework, Ollama local LLM server (`/api/generate`)

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `src/bashmage/storage.py` | Modify | Add `AIConfig` dataclass + `load_ai_config()` |
| `src/bashmage/ollama.py` | Create | `OllamaClient`, `OllamaError`, system prompt |
| `src/bashmage/widgets/command_list.py` | Modify | Add `show_ai_hint()` method |
| `src/bashmage/widgets/ai_result_modal.py` | Create | `AIResultModal` — loading → result modal |
| `src/bashmage/app.py` | Modify | `ai_config` param, `?` detection, `_on_ai_result` |
| `src/bashmage/__main__.py` | Modify | Load `ai_config`, pass to `BashMageApp` |
| `tests/test_storage.py` | Modify | Add `AIConfig` + `load_ai_config` tests |
| `tests/test_ollama.py` | Create | `OllamaClient` unit tests |
| `tests/test_app.py` | Modify | Add AI-mode tests |
| `tests/test_ai_result_modal.py` | Create | `AIResultModal` widget tests |

---

## Task 1: AIConfig dataclass + load_ai_config()

**Files:**
- Modify: `src/bashmage/storage.py`
- Modify: `tests/test_storage.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_storage.py`:

```python
from bashmage.storage import AIConfig, load_ai_config


def test_load_ai_config_returns_none_when_section_absent(tmp_path):
    config = tmp_path / "commands.toml"
    config.write_text("[[commands]]\nname='x'\ndescription='x'\ncommand='x'\n")
    with patch("bashmage.storage.CONFIG_PATH", config):
        assert load_ai_config() is None


def test_load_ai_config_returns_none_when_file_missing(tmp_path):
    config = tmp_path / "commands.toml"
    with patch("bashmage.storage.CONFIG_PATH", config):
        assert load_ai_config() is None


def test_load_ai_config_parses_model(tmp_path):
    config = tmp_path / "commands.toml"
    config.write_text('[ai]\nmodel = "llama3.2"\n')
    with patch("bashmage.storage.CONFIG_PATH", config):
        ai = load_ai_config()
    assert ai is not None
    assert ai.model == "llama3.2"


def test_load_ai_config_uses_default_base_url_when_absent(tmp_path):
    config = tmp_path / "commands.toml"
    config.write_text('[ai]\nmodel = "llama3.2"\n')
    with patch("bashmage.storage.CONFIG_PATH", config):
        ai = load_ai_config()
    assert ai.base_url == "http://localhost:11434"


def test_load_ai_config_parses_custom_base_url(tmp_path):
    config = tmp_path / "commands.toml"
    config.write_text('[ai]\nmodel = "llama3.2"\nbase_url = "http://myhost:9999"\n')
    with patch("bashmage.storage.CONFIG_PATH", config):
        ai = load_ai_config()
    assert ai.base_url == "http://myhost:9999"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/Zoltan_Pozsonyi/work/bashmage && .venv/bin/pytest tests/test_storage.py::test_load_ai_config_returns_none_when_section_absent tests/test_storage.py::test_load_ai_config_parses_model -v
```

Expected: `ImportError: cannot import name 'AIConfig'`

- [ ] **Step 3: Implement AIConfig and load_ai_config in storage.py**

Add after the existing `Command` dataclass (before `_parse_command`):

```python
@dataclass
class AIConfig:
    model: str
    base_url: str = "http://localhost:11434"


def load_ai_config() -> AIConfig | None:
    if not CONFIG_PATH.exists():
        return None
    data = tomllib.loads(CONFIG_PATH.read_text())
    ai = data.get("ai")
    if ai is None:
        return None
    return AIConfig(
        model=ai["model"],
        base_url=ai.get("base_url", "http://localhost:11434"),
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/Zoltan_Pozsonyi/work/bashmage && .venv/bin/pytest tests/test_storage.py -v
```

Expected: all storage tests PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/Zoltan_Pozsonyi/work/bashmage && git add src/bashmage/storage.py tests/test_storage.py && git commit -m "feat: add AIConfig dataclass and load_ai_config to storage"
```

---

## Task 2: OllamaClient

**Files:**
- Create: `src/bashmage/ollama.py`
- Create: `tests/test_ollama.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_ollama.py`:

```python
import json
import pytest
from unittest.mock import MagicMock, patch
from urllib.error import URLError

from bashmage.ollama import OllamaClient, OllamaError


def _mock_urlopen(response_body: bytes):
    mock_resp = MagicMock()
    mock_resp.read.return_value = response_body
    mock_cm = MagicMock()
    mock_cm.__enter__.return_value = mock_resp
    mock_cm.__exit__.return_value = False
    return mock_cm


def test_generate_returns_stripped_response():
    body = json.dumps({"response": "  docker ps  "}).encode()
    with patch("bashmage.ollama.urllib.request.urlopen", return_value=_mock_urlopen(body)):
        client = OllamaClient("http://localhost:11434", "llama3.2")
        assert client.generate("list docker containers") == "docker ps"


def test_generate_sends_request_to_api_generate_endpoint():
    body = json.dumps({"response": "echo hi"}).encode()
    with patch("bashmage.ollama.urllib.request.urlopen", return_value=_mock_urlopen(body)) as mock_open:
        client = OllamaClient("http://myhost:9999", "mymodel")
        client.generate("say hi")
    req = mock_open.call_args[0][0]
    assert req.full_url == "http://myhost:9999/api/generate"


def test_generate_sends_model_and_prompt_in_payload():
    body = json.dumps({"response": "echo hi"}).encode()
    with patch("bashmage.ollama.urllib.request.urlopen", return_value=_mock_urlopen(body)) as mock_open:
        client = OllamaClient("http://localhost:11434", "llama3.2")
        client.generate("say hi")
    req = mock_open.call_args[0][0]
    payload = json.loads(req.data)
    assert payload["model"] == "llama3.2"
    assert payload["prompt"] == "say hi"
    assert payload["stream"] is False


def test_generate_raises_ollama_error_on_connection_failure():
    with patch("bashmage.ollama.urllib.request.urlopen", side_effect=URLError("Connection refused")):
        client = OllamaClient("http://localhost:11434", "llama3.2")
        with pytest.raises(OllamaError, match="Cannot reach Ollama"):
            client.generate("anything")


def test_generate_raises_ollama_error_on_missing_response_key():
    body = json.dumps({"unexpected": "shape"}).encode()
    with patch("bashmage.ollama.urllib.request.urlopen", return_value=_mock_urlopen(body)):
        client = OllamaClient("http://localhost:11434", "llama3.2")
        with pytest.raises(OllamaError, match="Unexpected response"):
            client.generate("anything")


def test_generate_strips_trailing_slash_from_base_url():
    body = json.dumps({"response": "echo hi"}).encode()
    with patch("bashmage.ollama.urllib.request.urlopen", return_value=_mock_urlopen(body)) as mock_open:
        client = OllamaClient("http://localhost:11434/", "llama3.2")
        client.generate("say hi")
    req = mock_open.call_args[0][0]
    assert req.full_url == "http://localhost:11434/api/generate"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/Zoltan_Pozsonyi/work/bashmage && .venv/bin/pytest tests/test_ollama.py -v
```

Expected: `ModuleNotFoundError: No module named 'bashmage.ollama'`

- [ ] **Step 3: Implement ollama.py**

Create `src/bashmage/ollama.py`:

```python
import json
import urllib.request
import urllib.error


SYSTEM_PROMPT = """\
You are a bash command generator.
Given a description of what the user wants to do, output ONLY the bash command to accomplish it.
Rules:
- Output the command only — no explanation, no markdown, no code fences
- For values the user needs to supply (filenames, ports, hosts, etc.), use {placeholder} syntax, e.g. {host}, {port}, {file}
- Multi-line commands are acceptable; use backslash continuation or shell operators
- Keep commands practical and idiomatic"""


class OllamaError(Exception):
    pass


class OllamaClient:
    def __init__(self, base_url: str, model: str) -> None:
        self._url = f"{base_url.rstrip('/')}/api/generate"
        self._model = model

    def generate(self, prompt: str) -> str:
        payload = json.dumps({
            "model": self._model,
            "prompt": prompt,
            "system": SYSTEM_PROMPT,
            "stream": False,
        }).encode()
        req = urllib.request.Request(
            self._url,
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                body = json.loads(resp.read())
                return body["response"].strip()
        except urllib.error.URLError as e:
            raise OllamaError(f"Cannot reach Ollama at {self._url}: {e.reason}") from e
        except (KeyError, json.JSONDecodeError) as e:
            raise OllamaError(f"Unexpected response from Ollama: {e}") from e
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/Zoltan_Pozsonyi/work/bashmage && .venv/bin/pytest tests/test_ollama.py -v
```

Expected: all 6 tests PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/Zoltan_Pozsonyi/work/bashmage && git add src/bashmage/ollama.py tests/test_ollama.py && git commit -m "feat: add OllamaClient with generate() and OllamaError"
```

---

## Task 3: CommandList.show_ai_hint()

**Files:**
- Modify: `src/bashmage/widgets/command_list.py`
- Modify: `tests/test_app.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_app.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/Zoltan_Pozsonyi/work/bashmage && .venv/bin/pytest tests/test_app.py::test_command_list_show_ai_hint_renders_one_non_command_item tests/test_app.py::test_command_list_show_ai_hint_clears_highlighted_command -v
```

Expected: `AttributeError: 'CommandList' object has no attribute 'show_ai_hint'`

- [ ] **Step 3: Add show_ai_hint() to CommandList**

In `src/bashmage/widgets/command_list.py`, add this method inside the `CommandList` class, after the existing `filter()` method:

```python
def show_ai_hint(self) -> None:
    self._filtered = []
    self._current_command = None
    lv = self.query_one(ListView)
    lv.clear()
    lv.append(ListItem(Label("[dim]✨ press Enter to generate with AI[/dim]")))
    self.post_message(self.Highlighted(None))
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/Zoltan_Pozsonyi/work/bashmage && .venv/bin/pytest tests/test_app.py -v
```

Expected: all app tests PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/Zoltan_Pozsonyi/work/bashmage && git add src/bashmage/widgets/command_list.py tests/test_app.py && git commit -m "feat: add show_ai_hint() to CommandList"
```

---

## Task 4: AIResultModal

**Files:**
- Create: `src/bashmage/widgets/ai_result_modal.py`
- Create: `tests/test_ai_result_modal.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_ai_result_modal.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/Zoltan_Pozsonyi/work/bashmage && .venv/bin/pytest tests/test_ai_result_modal.py -v
```

Expected: `ModuleNotFoundError: No module named 'bashmage.widgets.ai_result_modal'`

- [ ] **Step 3: Implement AIResultModal**

Create `src/bashmage/widgets/ai_result_modal.py`:

```python
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
        self._worker = self.run_worker(self._fetch, thread=True)

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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/Zoltan_Pozsonyi/work/bashmage && .venv/bin/pytest tests/test_ai_result_modal.py -v
```

Expected: all 8 tests PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/Zoltan_Pozsonyi/work/bashmage && git add src/bashmage/widgets/ai_result_modal.py tests/test_ai_result_modal.py && git commit -m "feat: add AIResultModal with loading, result, and error states"
```

---

## Task 5: BashMageApp wiring

**Files:**
- Modify: `src/bashmage/app.py`
- Modify: `tests/test_app.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_app.py`:

```python
from textual.screen import ModalScreen
from unittest.mock import MagicMock, patch
from bashmage.storage import AIConfig
from bashmage.ollama import OllamaClient


_AI_CONFIG = AIConfig(model="llama3.2", base_url="http://localhost:11434")


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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/Zoltan_Pozsonyi/work/bashmage && .venv/bin/pytest tests/test_app.py::test_app_question_prefix_with_ai_config_shows_ai_hint tests/test_app.py::test_app_question_enter_with_ai_config_pushes_modal -v
```

Expected: `TypeError: BashMageApp.__init__() got an unexpected keyword argument 'ai_config'`

- [ ] **Step 3: Modify app.py**

Replace the current `app.py` content with:

```python
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
        query = self.query_one(SearchBar).value
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
```

- [ ] **Step 4: Run all tests to verify they pass**

```bash
cd /Users/Zoltan_Pozsonyi/work/bashmage && .venv/bin/pytest tests/ -v
```

Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/Zoltan_Pozsonyi/work/bashmage && git add src/bashmage/app.py tests/test_app.py && git commit -m "feat: wire AI mode into BashMageApp with ? prefix detection"
```

---

## Task 6: __main__.py wiring

**Files:**
- Modify: `src/bashmage/__main__.py`

No new tests needed — `load_ai_config` and `BashMageApp(ai_config=...)` are already tested. This task wires them together in the entry point.

- [ ] **Step 1: Update imports in __main__.py**

Change the storage import line from:

```python
from bashmage.storage import Command, load_commands, filter_by_path
```

to:

```python
from bashmage.storage import Command, load_commands, filter_by_path, load_ai_config
```

- [ ] **Step 2: Update main() to load ai_config inside the existing try/except**

Change the existing `try` block in `main()` from:

```python
    try:
        global_commands = filter_by_path(load_commands(), Path.cwd())
    except Exception as e:
        print(f"bashmage: error loading commands: {e}", file=sys.stderr)
        sys.exit(1)
```

to:

```python
    try:
        global_commands = filter_by_path(load_commands(), Path.cwd())
        ai_config = load_ai_config()
    except Exception as e:
        print(f"bashmage: error loading commands: {e}", file=sys.stderr)
        sys.exit(1)
```

This ensures a malformed `[ai]` section (e.g. missing `model` key) exits cleanly with an error message rather than an unhandled `KeyError`.

Then change the `BashMageApp` call from:

```python
    result = _run_app(BashMageApp(commands, initial_query=query or ""))
```

to:

```python
    result = _run_app(BashMageApp(commands, initial_query=query or "", ai_config=ai_config))
```

- [ ] **Step 3: Run the full test suite**

```bash
cd /Users/Zoltan_Pozsonyi/work/bashmage && .venv/bin/pytest tests/ -v
```

Expected: all tests PASS

- [ ] **Step 4: Commit**

```bash
cd /Users/Zoltan_Pozsonyi/work/bashmage && git add src/bashmage/__main__.py && git commit -m "feat: load ai_config in main and pass to BashMageApp"
```

---

## Final check

- [ ] **Run full test suite one last time**

```bash
cd /Users/Zoltan_Pozsonyi/work/bashmage && .venv/bin/pytest tests/ -v --tb=short
```

Expected: all tests PASS, zero failures.
