# Path-Prefix Filtering Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an optional `path` field to global commands that restricts visibility to invocations from directories at or below the configured prefix.

**Architecture:** Add `path: str | None` to `Command`, add `filter_by_path(commands, cwd)` to `storage.py`, apply it to global commands in `main()` before merging with context commands. Context (detected) commands are never filtered.

**Tech Stack:** Python 3.11+, `pathlib.Path`, pytest, TOML config at `~/.config/bashmage/commands.toml`

---

## File Map

- Modify: `src/bashmage/storage.py` — add `path` field to `Command`, update `_parse_command`, add `filter_by_path`
- Modify: `src/bashmage/__main__.py` — import `filter_by_path`, apply to global commands in `main()`
- Modify: `tests/test_storage.py` — add tests for `path` parsing and `filter_by_path`
- Modify: `tests/test_cli_routing.py` — add wiring test for `main()`

---

### Task 1: Add `path` field to `Command` and parse it from TOML

**Files:**
- Modify: `src/bashmage/storage.py`
- Modify: `tests/test_storage.py`

- [ ] **Step 1: Write failing tests**

Add to the bottom of `tests/test_storage.py`:

```python
def test_path_parsed_from_toml(tmp_path):
    config = tmp_path / "commands.toml"
    config.write_text("""\
[[commands]]
name = "deploy"
description = "Deploy app"
command = "make deploy"
path = "~/projects/myapp"
""")
    with patch("bashmage.storage.CONFIG_PATH", config):
        commands = load_commands()
    assert commands[0].path == "~/projects/myapp"


def test_path_defaults_to_none_when_absent(tmp_path):
    config = tmp_path / "commands.toml"
    config.write_text("""\
[[commands]]
name = "git-status"
description = "Show status"
command = "git status"
""")
    with patch("bashmage.storage.CONFIG_PATH", config):
        commands = load_commands()
    assert commands[0].path is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/Zoltan_Pozsonyi/work/bashmage
.venv/bin/pytest tests/test_storage.py::test_path_parsed_from_toml tests/test_storage.py::test_path_defaults_to_none_when_absent -v
```

Expected: FAIL — `Command.__init__() got an unexpected keyword argument 'path'` (or similar)

- [ ] **Step 3: Add `path` to `Command` and `_parse_command`**

In `src/bashmage/storage.py`, update the `Command` dataclass (around line 133) to add `path`:

```python
@dataclass
class Command:
    name: str
    description: str
    command: str
    tags: list[str] = field(default_factory=list)
    shortcut: str | None = None
    path: str | None = None
```

Update `_parse_command` (around line 151) to extract `path` the same way as `shortcut`:

```python
def _parse_command(raw: dict) -> Command:
    tags_str = raw.pop("tags", "")
    tags = [t for t in (t.strip() for t in tags_str.split(",")) if t] if tags_str else []
    shortcut = raw.pop("shortcut", None)
    path = raw.pop("path", None)
    return Command(**raw, tags=tags, shortcut=shortcut, path=path)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/pytest tests/test_storage.py::test_path_parsed_from_toml tests/test_storage.py::test_path_defaults_to_none_when_absent -v
```

Expected: PASS

- [ ] **Step 5: Run full test suite to check for regressions**

```bash
.venv/bin/pytest -v
```

Expected: all tests pass

- [ ] **Step 6: Commit**

```bash
git add src/bashmage/storage.py tests/test_storage.py
git commit -m "feat: add path field to Command dataclass and parse from TOML"
```

---

### Task 2: Add `filter_by_path()` to `storage.py`

**Files:**
- Modify: `src/bashmage/storage.py`
- Modify: `tests/test_storage.py`

- [ ] **Step 1: Write failing tests**

Add to the bottom of `tests/test_storage.py`. Note: `filter_by_path` is not yet imported — add it to the import line at the top: `from bashmage.storage import Command, load_commands, filter_by_path`.

```python
def _make_cmd(path=None):
    return Command(name="x", description="x", command="echo x", path=path)


def test_filter_no_path_always_passes():
    cmd = _make_cmd(path=None)
    assert filter_by_path([cmd], Path("/any/dir")) == [cmd]


def test_filter_ancestor_path_passes():
    cmd = _make_cmd(path="/test")
    assert filter_by_path([cmd], Path("/test/a")) == [cmd]


def test_filter_exact_match_passes():
    cmd = _make_cmd(path="/test/a")
    assert filter_by_path([cmd], Path("/test/a")) == [cmd]


def test_filter_non_ancestor_excluded():
    cmd = _make_cmd(path="/test2/a")
    assert filter_by_path([cmd], Path("/test/a")) == []


def test_filter_sibling_excluded():
    cmd = _make_cmd(path="/test/b")
    assert filter_by_path([cmd], Path("/test/a")) == []


def test_filter_tilde_expansion():
    home = Path.home()
    cmd = _make_cmd(path="~/projects")
    assert filter_by_path([cmd], home / "projects" / "myapp") == [cmd]


def test_filter_mixed_commands():
    visible_no_path = _make_cmd(path=None)
    visible_ancestor = _make_cmd(path="/test")
    visible_ancestor.name = "ancestor"
    hidden = _make_cmd(path="/test/b")
    hidden.name = "hidden"
    result = filter_by_path([visible_no_path, visible_ancestor, hidden], Path("/test/a"))
    assert visible_no_path in result
    assert visible_ancestor in result
    assert hidden not in result
```

Also add `from pathlib import Path` to the imports in `tests/test_storage.py` if not already present.

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/bin/pytest tests/test_storage.py::test_filter_no_path_always_passes tests/test_storage.py::test_filter_ancestor_path_passes -v
```

Expected: FAIL — `ImportError: cannot import name 'filter_by_path'`

- [ ] **Step 3: Implement `filter_by_path` in `storage.py`**

Add after `_parse_command` and before `load_commands` in `src/bashmage/storage.py`:

```python
def filter_by_path(commands: list[Command], cwd: Path) -> list[Command]:
    def matches(cmd: Command) -> bool:
        if cmd.path is None:
            return True
        return cwd.is_relative_to(Path(cmd.path).expanduser())
    return [cmd for cmd in commands if matches(cmd)]
```

Make sure `Path` is already imported at the top — it is (`from pathlib import Path`).

- [ ] **Step 4: Run the new tests**

```bash
.venv/bin/pytest tests/test_storage.py::test_filter_no_path_always_passes tests/test_storage.py::test_filter_ancestor_path_passes tests/test_storage.py::test_filter_exact_match_passes tests/test_storage.py::test_filter_non_ancestor_excluded tests/test_storage.py::test_filter_sibling_excluded tests/test_storage.py::test_filter_tilde_expansion tests/test_storage.py::test_filter_mixed_commands -v
```

Expected: all 7 PASS

- [ ] **Step 5: Run full test suite**

```bash
.venv/bin/pytest -v
```

Expected: all tests pass

- [ ] **Step 6: Commit**

```bash
git add src/bashmage/storage.py tests/test_storage.py
git commit -m "feat: add filter_by_path to filter commands by cwd prefix"
```

---

### Task 3: Wire `filter_by_path` into `main()`

**Files:**
- Modify: `src/bashmage/__main__.py`
- Modify: `tests/test_cli_routing.py`

- [ ] **Step 1: Write failing test**

Add to `tests/test_cli_routing.py`. The existing imports are `from bashmage.__main__ import _find_by_shortcut` and `from bashmage.storage import Command` — add `import sys` and `from unittest.mock import patch`.

```python
import sys
from unittest.mock import patch


def test_main_filters_global_commands_by_path():
    from bashmage.__main__ import main

    global_cmds = [
        Command("visible", "No path restriction", "echo visible"),
        Command("hidden", "Wrong path restriction", "echo hidden", path="/nonexistent/unlikely/path"),
    ]

    captured = []

    def fake_run_app(app):
        captured.extend(app._commands)
        return None

    with (
        patch("bashmage.__main__.load_commands", return_value=global_cmds),
        patch("bashmage.__main__.load_context_commands", return_value=[]),
        patch("bashmage.__main__._run_app", fake_run_app),
        patch.object(sys, "argv", ["bashmage"]),
    ):
        try:
            main()
        except SystemExit:
            pass

    names = [c.name for c in captured]
    assert "visible" in names
    assert "hidden" not in names
```

- [ ] **Step 2: Run test to verify it fails**

```bash
.venv/bin/pytest tests/test_cli_routing.py::test_main_filters_global_commands_by_path -v
```

Expected: FAIL — `"hidden" in names` (filter not applied yet, so hidden command passes through)

- [ ] **Step 3: Update `main()` to apply `filter_by_path`**

In `src/bashmage/__main__.py`, update the import from `bashmage.storage`:

```python
from bashmage.storage import Command, load_commands, filter_by_path
```

Then update the command loading block in `main()` (around line 120) from:

```python
    try:
        global_commands = load_commands()
    except Exception as e:
        print(f"bashmage: error loading commands: {e}", file=sys.stderr)
        sys.exit(1)

    context_commands = load_context_commands(Path.cwd())
    commands = context_commands + global_commands
```

to:

```python
    try:
        global_commands = filter_by_path(load_commands(), Path.cwd())
    except Exception as e:
        print(f"bashmage: error loading commands: {e}", file=sys.stderr)
        sys.exit(1)

    context_commands = load_context_commands(Path.cwd())
    commands = context_commands + global_commands
```

- [ ] **Step 4: Run the new test**

```bash
.venv/bin/pytest tests/test_cli_routing.py::test_main_filters_global_commands_by_path -v
```

Expected: PASS

- [ ] **Step 5: Run full test suite**

```bash
.venv/bin/pytest -v
```

Expected: all tests pass

- [ ] **Step 6: Commit**

```bash
git add src/bashmage/__main__.py tests/test_cli_routing.py
git commit -m "feat: apply path-prefix filter to global commands in main"
```
