# CLI Argument Routing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When `bashmage` is invoked with a positional argument, either bypass the TUI and output the command directly (exact shortcut match, no placeholders), show only a placeholder modal (exact shortcut match with placeholders), or open the TUI with the search bar pre-filled (no exact match).

**Architecture:** Routing logic lives in `__main__.py` — a helper finds exact shortcut matches, and a shared `_run_app` utility handles the TTY redirect for both the new `PlaceholderApp` and the existing `BashMageApp`. `SearchBar` and `BashMageApp` each gain one optional parameter.

**Tech Stack:** Python 3.11+, Textual (TUI framework), pytest + pytest-asyncio

---

## File Map

| File | Change |
|---|---|
| `src/bashmage/__main__.py` | Add `_find_by_shortcut`, `_run_app`, update `main` routing |
| `src/bashmage/app.py` | Add `initial_query: str = ""` parameter |
| `src/bashmage/widgets/search_bar.py` | Add `initial_value: str = ""` parameter |
| `src/bashmage/app_placeholder.py` | **New** — minimal app that shows only PlaceholderModal |
| `tests/test_cli_routing.py` | **New** — tests for `_find_by_shortcut` |
| `tests/test_app.py` | Add tests for `SearchBar(initial_value=...)` and `BashMageApp(initial_query=...)` |
| `tests/test_app_placeholder.py` | **New** — tests for `PlaceholderApp` |

---

### Task 1: `_find_by_shortcut` helper

**Files:**
- Modify: `src/bashmage/__main__.py`
- Create: `tests/test_cli_routing.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_cli_routing.py`:

```python
from bashmage.__main__ import _find_by_shortcut
from bashmage.storage import Command


COMMANDS = [
    Command("git-status", "Show status", "git status", shortcut="gs"),
    Command("docker-up", "Start docker", "docker compose up -d", shortcut="du"),
    Command("kill-port", "Kill port", "kill -9 $(lsof -t -i:{port})"),
]


def test_find_by_shortcut_returns_matching_command():
    result = _find_by_shortcut(COMMANDS, "gs")
    assert result is not None
    assert result.name == "git-status"


def test_find_by_shortcut_returns_second_match():
    result = _find_by_shortcut(COMMANDS, "du")
    assert result is not None
    assert result.name == "docker-up"


def test_find_by_shortcut_returns_none_when_no_match():
    assert _find_by_shortcut(COMMANDS, "GS") is None


def test_find_by_shortcut_returns_none_for_partial_match():
    assert _find_by_shortcut(COMMANDS, "g") is None


def test_find_by_shortcut_returns_none_when_command_has_no_shortcut():
    assert _find_by_shortcut(COMMANDS, "kill-port") is None


def test_find_by_shortcut_returns_first_on_duplicate_shortcut():
    commands = [
        Command("cmd-a", "First", "echo a", shortcut="x"),
        Command("cmd-b", "Second", "echo b", shortcut="x"),
    ]
    result = _find_by_shortcut(commands, "x")
    assert result is not None
    assert result.name == "cmd-a"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/Zoltan_Pozsonyi/work/bashmage && .venv/bin/pytest tests/test_cli_routing.py -v
```

Expected: ImportError — `_find_by_shortcut` does not exist yet.

- [ ] **Step 3: Add `_find_by_shortcut` to `__main__.py`**

Add after the `_BASH_INIT` string (before `_print_init`), at the top of the function definitions:

```python
def _find_by_shortcut(commands: list, query: str):
    for cmd in commands:
        if cmd.shortcut == query:
            return cmd
    return None
```

Place it after the `_BASH_INIT = """..."""` block and before `def _print_init`.

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/Zoltan_Pozsonyi/work/bashmage && .venv/bin/pytest tests/test_cli_routing.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add tests/test_cli_routing.py src/bashmage/__main__.py
git commit -m "feat: add _find_by_shortcut helper for CLI routing"
```

---

### Task 2: `SearchBar` initial value support

**Files:**
- Modify: `src/bashmage/widgets/search_bar.py`
- Modify: `tests/test_app.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_app.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/Zoltan_Pozsonyi/work/bashmage && .venv/bin/pytest tests/test_app.py::test_search_bar_initial_value_is_shown tests/test_app.py::test_search_bar_no_initial_value_is_empty -v
```

Expected: FAIL — `SearchBar` does not accept `initial_value`.

- [ ] **Step 3: Update `SearchBar`**

Replace the contents of `src/bashmage/widgets/search_bar.py` with:

```python
from textual.app import ComposeResult
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Input


class SearchBar(Widget):
    DEFAULT_CSS = """
    SearchBar {
        height: 3;
        padding: 0 1;
    }
    """

    class Changed(Message):
        def __init__(self, value: str) -> None:
            super().__init__()
            self.value = value

    def __init__(self, initial_value: str = "") -> None:
        super().__init__()
        self._initial_value = initial_value

    def compose(self) -> ComposeResult:
        yield Input(value=self._initial_value, placeholder="search commands...")

    def on_mount(self) -> None:
        self.query_one(Input).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        self.post_message(self.Changed(event.value))

    def clear(self) -> None:
        self.query_one(Input).value = ""
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/Zoltan_Pozsonyi/work/bashmage && .venv/bin/pytest tests/test_app.py -v
```

Expected: all tests pass (existing + 2 new).

- [ ] **Step 5: Commit**

```bash
git add src/bashmage/widgets/search_bar.py tests/test_app.py
git commit -m "feat: add initial_value support to SearchBar"
```

---

### Task 3: `BashMageApp` initial query

**Files:**
- Modify: `src/bashmage/app.py`
- Modify: `tests/test_app.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_app.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/Zoltan_Pozsonyi/work/bashmage && .venv/bin/pytest tests/test_app.py::test_app_initial_query_filters_list tests/test_app.py::test_app_initial_query_prefills_search_bar tests/test_app.py::test_app_no_initial_query_shows_all_commands -v
```

Expected: FAIL — `BashMageApp` does not accept `initial_query`.

- [ ] **Step 3: Update `BashMageApp`**

Replace the contents of `src/bashmage/app.py` with:

```python
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
        Binding("q", "quit_clean", "Quit", show=False),
        Binding("ctrl+q", "quit_clean", "Quit"),
    ]

    def __init__(self, commands: list[Command], initial_query: str = "") -> None:
        super().__init__()
        self._commands = commands
        self._initial_query = initial_query
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
        cmd = self.query_one(CommandList).get_highlighted_command()
        if cmd is not None:
            self._activate(cmd)

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

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/Zoltan_Pozsonyi/work/bashmage && .venv/bin/pytest tests/test_app.py -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/bashmage/app.py tests/test_app.py
git commit -m "feat: add initial_query support to BashMageApp"
```

---

### Task 4: `PlaceholderApp`

**Files:**
- Create: `src/bashmage/app_placeholder.py`
- Create: `tests/test_app_placeholder.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_app_placeholder.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/Zoltan_Pozsonyi/work/bashmage && .venv/bin/pytest tests/test_app_placeholder.py -v
```

Expected: ModuleNotFoundError — `app_placeholder` does not exist.

- [ ] **Step 3: Create `src/bashmage/app_placeholder.py`**

```python
from textual.app import App, ComposeResult

from bashmage.storage import Command
from bashmage.widgets.placeholder_modal import PlaceholderModal


class PlaceholderApp(App[str | None]):
    def __init__(self, command: Command) -> None:
        super().__init__()
        self._command = command

    def compose(self) -> ComposeResult:
        yield from []

    def on_mount(self) -> None:
        self.push_screen(PlaceholderModal(self._command), self.exit)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/Zoltan_Pozsonyi/work/bashmage && .venv/bin/pytest tests/test_app_placeholder.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Run full test suite to check for regressions**

```bash
cd /Users/Zoltan_Pozsonyi/work/bashmage && .venv/bin/pytest -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/bashmage/app_placeholder.py tests/test_app_placeholder.py
git commit -m "feat: add PlaceholderApp for direct shortcut modal"
```

---

### Task 5: Wire routing in `__main__.py`

**Files:**
- Modify: `src/bashmage/__main__.py`

No new unit tests — the routing is a thin glue layer over already-tested components. Run the full suite after wiring.

- [ ] **Step 1: Replace `__main__.py` with the routed version**

Replace the entire contents of `src/bashmage/__main__.py` with:

```python
import os
import sys
from pathlib import Path
from bashmage.app import BashMageApp
from bashmage.context import load_context_commands
from bashmage.storage import Command, load_commands


_ZSH_INIT = """\
# BashMage shell integration (zsh)
# Add to ~/.zshrc:  eval "$(bashmage --init)"
_bashmage_widget() {
  local tmp ret cmd saved_stty
  tmp=$(mktemp) || return
  saved_stty=$(stty -g 2>/dev/null)
  bashmage >"$tmp" </dev/tty
  ret=$?
  [[ -n "$saved_stty" ]] && stty "$saved_stty" 2>/dev/null
  cmd=$(<"$tmp")
  rm -f "$tmp"
  zle reset-prompt
  [[ $ret -eq 0 && -n "$cmd" ]] || return
  BUFFER="$cmd"
  CURSOR=${#BUFFER}
  zle redisplay
}
zle -N _bashmage_widget
bindkey '^b' _bashmage_widget
"""

_BASH_INIT = """\
# BashMage shell integration (bash)
# Add to ~/.bashrc:  eval "$(bashmage --init)"
_bashmage_widget() {
  local cmd
  cmd=$(bashmage)
  [[ $? -eq 0 && -n "$cmd" ]] || return
  READLINE_LINE="$cmd"
  READLINE_POINT=${#cmd}
}
bind -x '"\\C-b": _bashmage_widget'
"""


def _print_init(shell: str | None) -> None:
    if shell is None:
        shell_path = os.environ.get("SHELL", "")
        if "zsh" in shell_path:
            shell = "zsh"
        elif "bash" in shell_path:
            shell = "bash"
        else:
            print(
                "bashmage: cannot detect shell. "
                "Run: bashmage --init bash  or  bashmage --init zsh",
                file=sys.stderr,
            )
            sys.exit(1)

    if shell == "zsh":
        print(_ZSH_INIT, end="")
    elif shell == "bash":
        print(_BASH_INIT, end="")
    else:
        print(f"bashmage: unknown shell '{shell}'. Supported: bash, zsh", file=sys.stderr)
        sys.exit(1)


def _find_by_shortcut(commands: list[Command], query: str) -> Command | None:
    for cmd in commands:
        if cmd.shortcut == query:
            return cmd
    return None


def _run_app(app) -> str | None:
    saved_stdout = sys.stdout
    saved_stderr = sys.stderr
    saved_stdout_fd = None
    try:
        if not sys.stdout.isatty():
            tty_fd = os.open("/dev/tty", os.O_RDWR)
            saved_stdout_fd = os.dup(1)
            os.dup2(tty_fd, 1)
            os.close(tty_fd)
            sys.stdout = open(1, "w", closefd=False)
            sys.stderr = sys.stdout
        return app.run()
    finally:
        sys.stdout = saved_stdout
        sys.stderr = saved_stderr
        if saved_stdout_fd is not None:
            os.dup2(saved_stdout_fd, 1)
            os.close(saved_stdout_fd)


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "--init":
        _print_init(sys.argv[2] if len(sys.argv) > 2 else None)
        return

    try:
        global_commands = load_commands()
    except Exception as e:
        print(f"bashmage: error loading commands: {e}", file=sys.stderr)
        sys.exit(1)

    context_commands = load_context_commands(Path.cwd())
    commands = context_commands + global_commands

    query = sys.argv[1] if len(sys.argv) > 1 else None

    if query is not None:
        match = _find_by_shortcut(commands, query)
        if match is not None and not match.placeholders:
            print(match.command)
            sys.exit(0)
        if match is not None and match.placeholders:
            from bashmage.app_placeholder import PlaceholderApp
            result = _run_app(PlaceholderApp(match))
            if result is not None:
                print(result)
                sys.exit(0)
            sys.exit(1)

    result = _run_app(BashMageApp(commands, initial_query=query or ""))
    if result is not None:
        print(result)
        sys.exit(0)
    sys.exit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the full test suite**

```bash
cd /Users/Zoltan_Pozsonyi/work/bashmage && .venv/bin/pytest -v
```

Expected: all tests pass.

- [ ] **Step 3: Commit**

```bash
git add src/bashmage/__main__.py
git commit -m "feat: route CLI argument to shortcut bypass or prefilled TUI"
```
