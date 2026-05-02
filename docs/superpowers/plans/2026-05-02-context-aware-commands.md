# Context-Aware Commands Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When bashmage opens, detect the project type of `$PWD` and prepend dynamically loaded "local" commands to the global list; first implementation handles Node.js/npm/yarn via `package.json` scripts.

**Architecture:** A new `src/bashmage/context/` package holds a `_LOADERS` registry of `(detect_fn, load_fn)` tuples. `__main__.py` calls `load_context_commands(Path.cwd())`, prepends the result to the global commands, then passes everything to `BashMageApp`. Context loaders are best-effort — any failure silently returns `[]`.

**Tech Stack:** Python 3.11+, stdlib `json` + `pathlib`, pytest with `tmp_path` fixture.

> **Note:** `tests/test_placeholder_modal.py::test_placeholder_modal_empty_field_blocks_confirm` is a pre-existing failure unrelated to this feature. The baseline is 40 passed, 1 failed.

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `src/bashmage/context/__init__.py` | Create | `_LOADERS` registry + `load_context_commands` |
| `src/bashmage/context/node.py` | Create | Node.js `detect` + `load` functions |
| `src/bashmage/__main__.py` | Modify | Call `load_context_commands(Path.cwd())`, prepend result |
| `tests/test_context_node.py` | Create | Unit tests for node loader |
| `tests/test_context.py` | Create | Unit tests for the registry |

---

### Task 1: Node.js `detect` function

**Files:**
- Create: `tests/test_context_node.py`
- Create: `src/bashmage/context/__init__.py`
- Create: `src/bashmage/context/node.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_context_node.py`:

```python
from pathlib import Path
from bashmage.context.node import detect


def test_detect_returns_false_when_no_package_json(tmp_path):
    assert detect(tmp_path) is False


def test_detect_returns_true_when_package_json_exists(tmp_path):
    (tmp_path / "package.json").write_text("{}")
    assert detect(tmp_path) is True
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd /Users/Zoltan_Pozsonyi/work/bashmage
python -m pytest tests/test_context_node.py -v
```

Expected: `ModuleNotFoundError: No module named 'bashmage.context'`

- [ ] **Step 3: Create the package and implement `detect`**

Create `src/bashmage/context/__init__.py` (empty for now):

```python
```

Create `src/bashmage/context/node.py`:

```python
from pathlib import Path


def detect(cwd: Path) -> bool:
    return (cwd / "package.json").exists()
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
python -m pytest tests/test_context_node.py::test_detect_returns_false_when_no_package_json tests/test_context_node.py::test_detect_returns_true_when_package_json_exists -v
```

Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add tests/test_context_node.py src/bashmage/context/__init__.py src/bashmage/context/node.py
git commit -m "feat: add context package with Node.js detect function"
```

---

### Task 2: Node.js `load` function

**Files:**
- Modify: `tests/test_context_node.py`
- Modify: `src/bashmage/context/node.py`

- [ ] **Step 1: Write the failing tests**

Replace `tests/test_context_node.py` with the complete updated file (adds `import json`, `load` import, and all new test functions):

```python
import json
from pathlib import Path
from bashmage.context.node import detect, load


def test_detect_returns_false_when_no_package_json(tmp_path):
    assert detect(tmp_path) is False


def test_detect_returns_true_when_package_json_exists(tmp_path):
    (tmp_path / "package.json").write_text("{}")
    assert detect(tmp_path) is True


def test_load_returns_empty_when_no_package_json(tmp_path):
    assert load(tmp_path) == []


def test_load_returns_empty_when_package_json_invalid_json(tmp_path):
    (tmp_path / "package.json").write_text("not json {{{")
    assert load(tmp_path) == []


def test_load_returns_empty_when_no_scripts_key(tmp_path):
    (tmp_path / "package.json").write_text('{"name": "my-app"}')
    assert load(tmp_path) == []


def test_load_returns_empty_when_scripts_is_empty(tmp_path):
    (tmp_path / "package.json").write_text('{"scripts": {}}')
    assert load(tmp_path) == []


def test_load_defaults_to_npm_when_no_lock_file(tmp_path):
    pkg = {"scripts": {"lint": "eslint ."}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    cmds = load(tmp_path)
    assert len(cmds) == 1
    assert cmds[0].command == "npm run lint"
    assert cmds[0].tags == ["local", "npm"]


def test_load_uses_npm_when_package_lock_present(tmp_path):
    pkg = {"scripts": {"build": "webpack"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    (tmp_path / "package-lock.json").write_text("{}")
    cmds = load(tmp_path)
    assert cmds[0].command == "npm run build"
    assert cmds[0].tags == ["local", "npm"]


def test_load_uses_yarn_when_yarn_lock_present(tmp_path):
    pkg = {"scripts": {"test": "jest"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    (tmp_path / "yarn.lock").write_text("")
    cmds = load(tmp_path)
    assert cmds[0].command == "yarn test"
    assert cmds[0].tags == ["local", "yarn"]


def test_load_yarn_takes_precedence_over_npm(tmp_path):
    pkg = {"scripts": {"start": "node server.js"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    (tmp_path / "yarn.lock").write_text("")
    (tmp_path / "package-lock.json").write_text("{}")
    cmds = load(tmp_path)
    assert cmds[0].command == "yarn start"
    assert cmds[0].tags == ["local", "yarn"]


def test_load_script_key_becomes_name(tmp_path):
    pkg = {"scripts": {"build": "webpack"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    cmds = load(tmp_path)
    assert cmds[0].name == "build"


def test_load_script_value_becomes_description(tmp_path):
    pkg = {"scripts": {"build": "webpack --config webpack.config.js"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    cmds = load(tmp_path)
    assert cmds[0].description == "webpack --config webpack.config.js"


def test_load_multiple_scripts_returns_all(tmp_path):
    pkg = {"scripts": {"build": "webpack", "test": "jest", "lint": "eslint ."}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    cmds = load(tmp_path)
    assert len(cmds) == 3
    names = {c.name for c in cmds}
    assert names == {"build", "test", "lint"}


def test_load_shortcut_is_none(tmp_path):
    pkg = {"scripts": {"build": "webpack"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    cmds = load(tmp_path)
    assert cmds[0].shortcut is None
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
python -m pytest tests/test_context_node.py -v
```

Expected: the new tests fail with `ImportError` or `AttributeError` (no `load` function yet)

- [ ] **Step 3: Implement `load` in `node.py`**

Replace the full content of `src/bashmage/context/node.py`:

```python
import json
from pathlib import Path

from bashmage.storage import Command


def detect(cwd: Path) -> bool:
    return (cwd / "package.json").exists()


def load(cwd: Path) -> list[Command]:
    try:
        data = json.loads((cwd / "package.json").read_text())
    except Exception:
        return []

    scripts = data.get("scripts", {})
    if not scripts:
        return []

    if (cwd / "yarn.lock").exists():
        manager = "yarn"
        run_prefix = "yarn"
    else:
        manager = "npm"
        run_prefix = "npm run"

    return [
        Command(
            name=key,
            description=value,
            command=f"{run_prefix} {key}",
            tags=["local", manager],
        )
        for key, value in scripts.items()
    ]
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
python -m pytest tests/test_context_node.py -v
```

Expected: all 14 tests in this file pass

- [ ] **Step 5: Commit**

```bash
git add tests/test_context_node.py src/bashmage/context/node.py
git commit -m "feat: implement Node.js context loader (detect + load)"
```

---

### Task 3: Context registry

**Files:**
- Create: `tests/test_context.py`
- Modify: `src/bashmage/context/__init__.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_context.py`:

```python
import json
from pathlib import Path

from bashmage.context import load_context_commands


def test_returns_empty_for_unknown_project_type(tmp_path):
    cmds = load_context_commands(tmp_path)
    assert cmds == []


def test_returns_node_commands_for_js_project(tmp_path):
    pkg = {"scripts": {"build": "webpack"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    cmds = load_context_commands(tmp_path)
    assert len(cmds) == 1
    assert cmds[0].name == "build"


def test_node_commands_have_local_tag(tmp_path):
    pkg = {"scripts": {"test": "jest"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    cmds = load_context_commands(tmp_path)
    assert "local" in cmds[0].tags
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
python -m pytest tests/test_context.py -v
```

Expected: `ImportError: cannot import name 'load_context_commands' from 'bashmage.context'`

- [ ] **Step 3: Implement the registry in `context/__init__.py`**

Replace the content of `src/bashmage/context/__init__.py`:

```python
from collections.abc import Callable
from pathlib import Path

from bashmage.context import node
from bashmage.storage import Command

_LOADERS: list[tuple[
    Callable[[Path], bool],
    Callable[[Path], list[Command]],
]] = [
    (node.detect, node.load),
    # future: (python.detect, python.load)
]


def load_context_commands(cwd: Path) -> list[Command]:
    commands: list[Command] = []
    for detect_fn, load_fn in _LOADERS:
        if detect_fn(cwd):
            commands.extend(load_fn(cwd))
    return commands
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
python -m pytest tests/test_context.py tests/test_context_node.py -v
```

Expected: all tests in both files pass

- [ ] **Step 5: Commit**

```bash
git add tests/test_context.py src/bashmage/context/__init__.py
git commit -m "feat: add context loader registry with load_context_commands"
```

---

### Task 4: Wire up `__main__.py`

**Files:**
- Modify: `src/bashmage/__main__.py`

- [ ] **Step 1: Add imports**

At the top of `src/bashmage/__main__.py`, after the existing imports, add:

```python
from pathlib import Path
from bashmage.context import load_context_commands
```

The full imports section becomes:

```python
import os
import sys
from pathlib import Path
from bashmage.app import BashMageApp
from bashmage.context import load_context_commands
from bashmage.storage import load_commands
```

- [ ] **Step 2: Update `main()` to prepend context commands**

Find this block in `main()`:

```python
    try:
        commands = load_commands()
    except Exception as e:
        print(f"bashmage: error loading commands: {e}", file=sys.stderr)
        sys.exit(1)
```

Replace it with:

```python
    try:
        global_commands = load_commands()
    except Exception as e:
        print(f"bashmage: error loading commands: {e}", file=sys.stderr)
        sys.exit(1)

    context_commands = load_context_commands(Path.cwd())
    commands = context_commands + global_commands
```

- [ ] **Step 3: Run the full test suite**

```bash
python -m pytest tests/ -v
```

Expected: same baseline as before — 40 passed, 1 pre-existing failure (`test_placeholder_modal_empty_field_blocks_confirm`). No regressions.

- [ ] **Step 4: Commit**

```bash
git add src/bashmage/__main__.py
git commit -m "feat: prepend context-aware commands in main"
```

---

## Verification

After all tasks, manually test in a JS project directory:

```bash
cd /some/node/project
bashmage
```

Expected: scripts from `package.json` appear at the top of the list with tag `local` and either `npm` or `yarn`. Searching `#local` should filter to only those commands.
