# Command Shortcuts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an optional `shortcut` field to commands that participates in normal search and is displayed as `[sw]` next to the command name in the list.

**Architecture:** Add `shortcut: str | None = None` to the `Command` dataclass and parse it from TOML; extend the `matches()` filter to check the shortcut field; update `CommandItem.compose()` to render `name [shortcut]` when a shortcut exists.

**Tech Stack:** Python 3.12, Textual (TUI framework), TOML config, pytest + pytest-asyncio for tests.

---

### Task 1: Add `shortcut` field to `Command` and parse it from TOML

**Files:**
- Modify: `src/bashmage/storage.py`
- Test: `tests/test_storage.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_storage.py`:

```python
def test_shortcut_parsed_from_toml(tmp_path):
    config = tmp_path / "commands.toml"
    config.write_text("""\
[[commands]]
name = "switch-branch"
shortcut = "sw"
description = "Switch git branch"
command = "git checkout {branch}"
tags = "git"
""")
    with patch("bashmage.storage.CONFIG_PATH", config):
        commands = load_commands()
    assert commands[0].shortcut == "sw"


def test_shortcut_defaults_to_none_when_absent(tmp_path):
    config = tmp_path / "commands.toml"
    config.write_text("""\
[[commands]]
name = "git-status"
description = "Show status"
command = "git status"
""")
    with patch("bashmage.storage.CONFIG_PATH", config):
        commands = load_commands()
    assert commands[0].shortcut is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_storage.py::test_shortcut_parsed_from_toml tests/test_storage.py::test_shortcut_defaults_to_none_when_absent -v
```

Expected: FAIL — `Command.__init__() got an unexpected keyword argument 'shortcut'` (or similar).

- [ ] **Step 3: Add `shortcut` field to `Command` and update `_parse_command`**

In `src/bashmage/storage.py`, replace the `Command` dataclass with:

```python
@dataclass
class Command:
    name: str
    description: str
    command: str
    tags: list[str] = field(default_factory=list)
    shortcut: str | None = None
```

Replace `_parse_command` with:

```python
def _parse_command(raw: dict) -> Command:
    tags_str = raw.pop("tags", "")
    tags = [t for t in (t.strip() for t in tags_str.split(",")) if t] if tags_str else []
    shortcut = raw.pop("shortcut", None)
    return Command(**raw, tags=tags, shortcut=shortcut)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_storage.py -v
```

Expected: ALL PASS.

- [ ] **Step 5: Commit**

```bash
git add src/bashmage/storage.py tests/test_storage.py
git commit -m "feat: add optional shortcut field to Command"
```

---

### Task 2: Include shortcut in search filter

**Files:**
- Modify: `src/bashmage/widgets/command_list.py`
- Test: `tests/test_app.py`

- [ ] **Step 1: Write the failing tests**

At the top of `tests/test_app.py`, after the existing `COMMANDS` list, add:

```python
COMMANDS_WITH_SHORTCUTS = [
    Command("git-status", "Show working tree status", "git status --short", tags=["git"], shortcut="gs"),
    Command("docker-up", "Start docker services", "docker compose up -d", tags=["docker"], shortcut="du"),
    Command("kill-port", "Kill process on a port", "kill -9 $(lsof -t -i:{port})", tags=["network", "ports"]),
]


class _ShortcutListApp(App):
    def compose(self) -> ComposeResult:
        yield CommandList(COMMANDS_WITH_SHORTCUTS)
```

Then append these tests:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_app.py::test_command_list_filter_matches_shortcut tests/test_app.py::test_command_list_filter_matches_second_shortcut -v
```

Expected: FAIL — `gs` matches zero items because the shortcut field is not checked in `matches()`.

- [ ] **Step 3: Update `matches()` in `CommandList.filter()`**

In `src/bashmage/widgets/command_list.py`, replace the `matches()` inner function inside `filter()`:

```python
def matches(c: Command) -> bool:
    for t in text_tokens:
        if (
            t not in c.name.lower()
            and t not in c.description.lower()
            and (c.shortcut is None or t not in c.shortcut.lower())
        ):
            return False
    for t in tag_tokens:
        if not any(t in tag.lower() for tag in c.tags):
            return False
    return True
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_app.py -v
```

Expected: ALL PASS.

- [ ] **Step 5: Commit**

```bash
git add src/bashmage/widgets/command_list.py tests/test_app.py
git commit -m "feat: include shortcut field in search filter"
```

---

### Task 3: Display shortcut in command list

**Files:**
- Modify: `src/bashmage/widgets/command_list.py`
- Test: `tests/test_app.py`

- [ ] **Step 1: Write the failing tests**

First, add `Label` to the imports at the top of `tests/test_app.py` — change the existing `Input` import line to:

```python
from textual.widgets import Input, Label
```

Then append to `tests/test_app.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_app.py::test_command_item_renders_shortcut_after_name tests/test_app.py::test_command_item_no_shortcut_renders_name_only -v
```

Expected: `test_command_item_renders_shortcut_after_name` FAIL — `[sw]` not found in rendered output.

- [ ] **Step 3: Update `CommandItem.compose()` to show the shortcut**

In `src/bashmage/widgets/command_list.py`, replace `CommandItem.compose()`:

```python
def compose(self) -> ComposeResult:
    name_part = (
        f"{self.command.name} [bold][[{self.command.shortcut}]][/bold]"
        if self.command.shortcut
        else self.command.name
    )
    yield Label(f"{name_part}\n[dim]{self.command.description}[/dim]")
```

Note: `[[` and `]]` are Rich markup escape sequences that render as literal `[` and `]`.

- [ ] **Step 4: Run all tests to verify they pass**

```bash
pytest tests/ -v
```

Expected: ALL PASS.

- [ ] **Step 5: Commit**

```bash
git add src/bashmage/widgets/command_list.py tests/test_app.py
git commit -m "feat: display shortcut in bold brackets next to command name"
```
