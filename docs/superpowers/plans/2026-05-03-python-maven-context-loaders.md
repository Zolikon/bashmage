# Python and Maven Context Loaders Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Python (uv/pip) and Maven context loaders to bashmage so it surfaces relevant commands when invoked in Python or Java Maven projects.

**Architecture:** Two new modules `context/python.py` and `context/maven.py`, each with `detect(cwd) → bool` and `load(cwd) → list[Command]`, registered in `context/__init__.py`. Python loader selects manager by lock file presence and reads dynamic tasks from `pyproject.toml`; Maven loader returns a fixed set of lifecycle commands.

**Tech Stack:** Python 3.12, `tomllib` (stdlib), `pathlib`, `pytest`

---

### Task 1: Python detect function

**Files:**
- Create: `tests/test_context_python.py`
- Create: `src/bashmage/context/python.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_context_python.py`:

```python
from pathlib import Path
from bashmage.context.python import detect, load


def test_detect_returns_false_when_no_python_files(tmp_path):
    assert detect(tmp_path) is False


def test_detect_returns_true_when_pyproject_toml_exists(tmp_path):
    (tmp_path / "pyproject.toml").write_text("")
    assert detect(tmp_path) is True


def test_detect_returns_true_when_requirements_txt_exists(tmp_path):
    (tmp_path / "requirements.txt").write_text("")
    assert detect(tmp_path) is True


def test_detect_returns_true_when_both_files_exist(tmp_path):
    (tmp_path / "pyproject.toml").write_text("")
    (tmp_path / "requirements.txt").write_text("")
    assert detect(tmp_path) is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_context_python.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'bashmage.context.python'`

- [ ] **Step 3: Create `src/bashmage/context/python.py` with detect**

```python
import tomllib
from pathlib import Path
from bashmage.storage import Command


def detect(cwd: Path) -> bool:
    return (cwd / "pyproject.toml").exists() or (cwd / "requirements.txt").exists()


def load(cwd: Path) -> list[Command]:
    return []
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_context_python.py -v`
Expected: 4 PASSED

- [ ] **Step 5: Commit**

```bash
git add tests/test_context_python.py src/bashmage/context/python.py
git commit -m "feat: add Python context loader with detect function"
```

---

### Task 2: Python standard commands (uv and pip)

**Files:**
- Modify: `tests/test_context_python.py`
- Modify: `src/bashmage/context/python.py`

- [ ] **Step 1: Add failing tests for all standard command cases**

Append to `tests/test_context_python.py`:

```python
def test_load_returns_empty_when_no_python_files(tmp_path):
    assert load(tmp_path) == []


def test_load_uv_standard_commands_when_uv_lock_present(tmp_path):
    (tmp_path / "pyproject.toml").write_text("")
    (tmp_path / "uv.lock").write_text("")
    cmds = load(tmp_path)
    names = {c.name for c in cmds}
    assert {"uv-sync", "uv-run", "uv-add", "uv-lock"}.issubset(names)


def test_load_uv_commands_have_correct_commands(tmp_path):
    (tmp_path / "pyproject.toml").write_text("")
    (tmp_path / "uv.lock").write_text("")
    cmd_map = {c.name: c.command for c in load(tmp_path)}
    assert cmd_map["uv-sync"] == "uv sync"
    assert cmd_map["uv-lock"] == "uv lock"
    assert cmd_map["uv-run"] == "uv run {command}"
    assert cmd_map["uv-add"] == "uv add {package}"


def test_load_uv_commands_have_local_and_uv_tags(tmp_path):
    (tmp_path / "pyproject.toml").write_text("")
    (tmp_path / "uv.lock").write_text("")
    for cmd in load(tmp_path):
        assert "local" in cmd.tags
        assert "uv" in cmd.tags


def test_load_pip_install_editable_when_pyproject_without_uv_lock(tmp_path):
    (tmp_path / "pyproject.toml").write_text("")
    cmds = load(tmp_path)
    assert len(cmds) == 1
    assert cmds[0].name == "pip-install"
    assert cmds[0].command == "pip install -e ."


def test_load_pip_install_has_local_and_pip_tags(tmp_path):
    (tmp_path / "pyproject.toml").write_text("")
    cmds = load(tmp_path)
    assert "pip" in cmds[0].tags
    assert "local" in cmds[0].tags


def test_load_pip_requirements_when_only_requirements_txt(tmp_path):
    (tmp_path / "requirements.txt").write_text("")
    cmds = load(tmp_path)
    assert len(cmds) == 1
    assert cmds[0].name == "pip-install-requirements"
    assert cmds[0].command == "pip install -r requirements.txt"


def test_load_pyproject_takes_precedence_when_both_files_present(tmp_path):
    (tmp_path / "pyproject.toml").write_text("")
    (tmp_path / "requirements.txt").write_text("")
    cmds = load(tmp_path)
    names = {c.name for c in cmds}
    assert "pip-install" in names
    assert "pip-install-requirements" not in names
```

- [ ] **Step 2: Run tests to verify new tests fail**

Run: `pytest tests/test_context_python.py -v`
Expected: 4 existing PASSED, 8 new FAILED

- [ ] **Step 3: Implement standard commands in `load`**

Replace `src/bashmage/context/python.py` with:

```python
import tomllib
from pathlib import Path
from bashmage.storage import Command


def detect(cwd: Path) -> bool:
    return (cwd / "pyproject.toml").exists() or (cwd / "requirements.txt").exists()


def load(cwd: Path) -> list[Command]:
    pyproject = cwd / "pyproject.toml"
    requirements = cwd / "requirements.txt"

    if pyproject.exists():
        try:
            data = tomllib.loads(pyproject.read_text())
        except Exception:
            data = {}

        if (cwd / "uv.lock").exists():
            manager = "uv"
            standard = [
                Command(name="uv-sync", description="Install project dependencies", command="uv sync", tags=["local", "uv"]),
                Command(name="uv-run", description="Run a command in the project environment", command="uv run {command}", tags=["local", "uv"]),
                Command(name="uv-add", description="Add a dependency", command="uv add {package}", tags=["local", "uv"]),
                Command(name="uv-lock", description="Update the lockfile", command="uv lock", tags=["local", "uv"]),
            ]
        else:
            manager = "pip"
            standard = [
                Command(name="pip-install", description="Install project in editable mode", command="pip install -e .", tags=["local", "pip"]),
            ]

        return standard

    if requirements.exists():
        return [
            Command(name="pip-install-requirements", description="Install dependencies from requirements.txt", command="pip install -r requirements.txt", tags=["local", "pip"]),
        ]

    return []
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_context_python.py -v`
Expected: 12 PASSED

- [ ] **Step 5: Commit**

```bash
git add tests/test_context_python.py src/bashmage/context/python.py
git commit -m "feat: add uv and pip standard commands to Python context loader"
```

---

### Task 3: Python taskipy dynamic tasks

**Files:**
- Modify: `tests/test_context_python.py`
- Modify: `src/bashmage/context/python.py`

- [ ] **Step 1: Add failing tests for taskipy**

Append to `tests/test_context_python.py`:

```python
def test_load_taskipy_tasks_appear_alongside_standard_commands(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[tool.taskipy.tasks]\ntest = "pytest"\nlint = "ruff check ."\n'
    )
    (tmp_path / "uv.lock").write_text("")
    names = {c.name for c in load(tmp_path)}
    assert "uv-sync" in names
    assert "test" in names
    assert "lint" in names


def test_load_taskipy_task_command_uses_task_prefix(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[tool.taskipy.tasks]\nbuild = "webpack"\n')
    task_cmd = next(c for c in load(tmp_path) if c.name == "build")
    assert task_cmd.command == "task build"


def test_load_taskipy_task_description_is_shell_command_string(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[tool.taskipy.tasks]\ntest = "pytest -v"\n')
    task_cmd = next(c for c in load(tmp_path) if c.name == "test")
    assert task_cmd.description == "pytest -v"


def test_load_taskipy_tasks_have_local_tag(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[tool.taskipy.tasks]\ntest = "pytest"\n')
    task_cmd = next(c for c in load(tmp_path) if c.name == "test")
    assert "local" in task_cmd.tags
```

- [ ] **Step 2: Run tests to verify new tests fail**

Run: `pytest tests/test_context_python.py -v`
Expected: 12 existing PASSED, 4 new FAILED

- [ ] **Step 3: Add `_load_tasks` helper and wire into `load`**

Replace `src/bashmage/context/python.py` with:

```python
import tomllib
from pathlib import Path
from bashmage.storage import Command


def detect(cwd: Path) -> bool:
    return (cwd / "pyproject.toml").exists() or (cwd / "requirements.txt").exists()


def load(cwd: Path) -> list[Command]:
    pyproject = cwd / "pyproject.toml"
    requirements = cwd / "requirements.txt"

    if pyproject.exists():
        try:
            data = tomllib.loads(pyproject.read_text())
        except Exception:
            data = {}

        if (cwd / "uv.lock").exists():
            manager = "uv"
            standard = [
                Command(name="uv-sync", description="Install project dependencies", command="uv sync", tags=["local", "uv"]),
                Command(name="uv-run", description="Run a command in the project environment", command="uv run {command}", tags=["local", "uv"]),
                Command(name="uv-add", description="Add a dependency", command="uv add {package}", tags=["local", "uv"]),
                Command(name="uv-lock", description="Update the lockfile", command="uv lock", tags=["local", "uv"]),
            ]
        else:
            manager = "pip"
            standard = [
                Command(name="pip-install", description="Install project in editable mode", command="pip install -e .", tags=["local", "pip"]),
            ]

        return standard + _load_tasks(data, manager)

    if requirements.exists():
        return [
            Command(name="pip-install-requirements", description="Install dependencies from requirements.txt", command="pip install -r requirements.txt", tags=["local", "pip"]),
        ]

    return []


def _load_tasks(data: dict, manager: str) -> list[Command]:
    tool = data.get("tool", {})

    taskipy_tasks = tool.get("taskipy", {}).get("tasks", {})
    if taskipy_tasks:
        return [
            Command(name=name, description=cmd, command=f"task {name}", tags=["local", manager])
            for name, cmd in taskipy_tasks.items()
        ]

    return []
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_context_python.py -v`
Expected: 16 PASSED

- [ ] **Step 5: Commit**

```bash
git add tests/test_context_python.py src/bashmage/context/python.py
git commit -m "feat: add taskipy dynamic task loading to Python context loader"
```

---

### Task 4: Python poe dynamic tasks

**Files:**
- Modify: `tests/test_context_python.py`
- Modify: `src/bashmage/context/python.py`

- [ ] **Step 1: Add failing tests for poe**

Append to `tests/test_context_python.py`:

```python
def test_load_poe_tasks_when_string_value(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[tool.poe.tasks]\ntest = "pytest"\n')
    task_cmd = next(c for c in load(tmp_path) if c.name == "test")
    assert task_cmd.command == "poe test"
    assert task_cmd.description == "pytest"


def test_load_poe_tasks_when_dict_with_help(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[tool.poe.tasks.build]\ncmd = "webpack"\nhelp = "Build the project"\n'
    )
    task_cmd = next(c for c in load(tmp_path) if c.name == "build")
    assert task_cmd.command == "poe build"
    assert task_cmd.description == "Build the project"


def test_load_poe_tasks_when_dict_without_help_falls_back_to_cmd(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[tool.poe.tasks.lint]\ncmd = "ruff check ."\n'
    )
    task_cmd = next(c for c in load(tmp_path) if c.name == "lint")
    assert task_cmd.command == "poe lint"
    assert task_cmd.description == "ruff check ."


def test_load_poe_skips_task_when_no_string_or_cmd(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[tool.poe.tasks.weird]\nsequence = ["step1", "step2"]\n'
    )
    names = {c.name for c in load(tmp_path)}
    assert "weird" not in names


def test_load_taskipy_takes_precedence_over_poe(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[tool.taskipy.tasks]\ntest = "pytest"\n\n[tool.poe.tasks]\nlint = "ruff check ."\n'
    )
    names = {c.name for c in load(tmp_path)}
    assert "test" in names
    assert "lint" not in names
```

- [ ] **Step 2: Run tests to verify new tests fail**

Run: `pytest tests/test_context_python.py -v`
Expected: 16 existing PASSED, 5 new FAILED

- [ ] **Step 3: Add poe support to `_load_tasks`**

Replace only the `_load_tasks` function in `src/bashmage/context/python.py` (everything before it stays the same):

```python
def _load_tasks(data: dict, manager: str) -> list[Command]:
    tool = data.get("tool", {})

    taskipy_tasks = tool.get("taskipy", {}).get("tasks", {})
    if taskipy_tasks:
        return [
            Command(name=name, description=cmd, command=f"task {name}", tags=["local", manager])
            for name, cmd in taskipy_tasks.items()
        ]

    poe_tasks = tool.get("poe", {}).get("tasks", {})
    if poe_tasks:
        commands = []
        for name, value in poe_tasks.items():
            if isinstance(value, str):
                description = value
            elif isinstance(value, dict):
                description = value.get("help") or value.get("cmd")
                if description is None:
                    continue
            else:
                continue
            commands.append(Command(name=name, description=description, command=f"poe {name}", tags=["local", manager]))
        return commands

    return []
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_context_python.py -v`
Expected: 21 PASSED

- [ ] **Step 5: Commit**

```bash
git add tests/test_context_python.py src/bashmage/context/python.py
git commit -m "feat: add poethepoet dynamic task loading to Python context loader"
```

---

### Task 5: Maven loader

**Files:**
- Create: `tests/test_context_maven.py`
- Create: `src/bashmage/context/maven.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_context_maven.py`:

```python
from pathlib import Path
from bashmage.context.maven import detect, load


def test_detect_returns_false_when_no_pom_xml(tmp_path):
    assert detect(tmp_path) is False


def test_detect_returns_true_when_pom_xml_exists(tmp_path):
    (tmp_path / "pom.xml").write_text("<project/>")
    assert detect(tmp_path) is True


def test_load_returns_empty_when_no_pom_xml(tmp_path):
    assert load(tmp_path) == []


def test_load_returns_six_commands(tmp_path):
    (tmp_path / "pom.xml").write_text("<project/>")
    assert len(load(tmp_path)) == 6


def test_load_commands_have_local_and_maven_tags(tmp_path):
    (tmp_path / "pom.xml").write_text("<project/>")
    for cmd in load(tmp_path):
        assert "local" in cmd.tags
        assert "maven" in cmd.tags


def test_load_contains_clean_command(tmp_path):
    (tmp_path / "pom.xml").write_text("<project/>")
    cmd_map = {c.name: c.command for c in load(tmp_path)}
    assert cmd_map["clean"] == "mvn clean"


def test_load_contains_compile_command(tmp_path):
    (tmp_path / "pom.xml").write_text("<project/>")
    cmd_map = {c.name: c.command for c in load(tmp_path)}
    assert cmd_map["compile"] == "mvn compile"


def test_load_contains_test_command(tmp_path):
    (tmp_path / "pom.xml").write_text("<project/>")
    cmd_map = {c.name: c.command for c in load(tmp_path)}
    assert cmd_map["test"] == "mvn test"


def test_load_contains_package_command(tmp_path):
    (tmp_path / "pom.xml").write_text("<project/>")
    cmd_map = {c.name: c.command for c in load(tmp_path)}
    assert cmd_map["package"] == "mvn package"


def test_load_contains_install_command(tmp_path):
    (tmp_path / "pom.xml").write_text("<project/>")
    cmd_map = {c.name: c.command for c in load(tmp_path)}
    assert cmd_map["install"] == "mvn install"


def test_load_contains_clean_install_command(tmp_path):
    (tmp_path / "pom.xml").write_text("<project/>")
    cmd_map = {c.name: c.command for c in load(tmp_path)}
    assert cmd_map["clean-install"] == "mvn clean install"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_context_maven.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'bashmage.context.maven'`

- [ ] **Step 3: Create `src/bashmage/context/maven.py`**

```python
from pathlib import Path
from bashmage.storage import Command

_COMMANDS = [
    Command(name="clean", description="Remove build artifacts", command="mvn clean", tags=["local", "maven"]),
    Command(name="compile", description="Compile source code", command="mvn compile", tags=["local", "maven"]),
    Command(name="test", description="Run tests", command="mvn test", tags=["local", "maven"]),
    Command(name="package", description="Build JAR/WAR", command="mvn package", tags=["local", "maven"]),
    Command(name="install", description="Install to local repository", command="mvn install", tags=["local", "maven"]),
    Command(name="clean-install", description="Clean, build, and install", command="mvn clean install", tags=["local", "maven"]),
]


def detect(cwd: Path) -> bool:
    return (cwd / "pom.xml").exists()


def load(cwd: Path) -> list[Command]:
    if not detect(cwd):
        return []
    return list(_COMMANDS)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_context_maven.py -v`
Expected: 11 PASSED

- [ ] **Step 5: Commit**

```bash
git add tests/test_context_maven.py src/bashmage/context/maven.py
git commit -m "feat: add Maven context loader"
```

---

### Task 6: Register loaders and integration tests

**Files:**
- Modify: `src/bashmage/context/__init__.py`
- Modify: `tests/test_context.py`

- [ ] **Step 1: Add failing integration tests**

Append to `tests/test_context.py`:

```python
def test_returns_python_uv_commands_for_uv_project(tmp_path):
    (tmp_path / "pyproject.toml").write_text("")
    (tmp_path / "uv.lock").write_text("")
    names = {c.name for c in load_context_commands(tmp_path)}
    assert "uv-sync" in names


def test_returns_python_pip_commands_for_pip_project(tmp_path):
    (tmp_path / "requirements.txt").write_text("")
    names = {c.name for c in load_context_commands(tmp_path)}
    assert "pip-install-requirements" in names


def test_returns_maven_commands_for_java_project(tmp_path):
    (tmp_path / "pom.xml").write_text("<project/>")
    names = {c.name for c in load_context_commands(tmp_path)}
    assert "clean" in names
    assert "test" in names
    assert "package" in names
```

- [ ] **Step 2: Run tests to verify new tests fail**

Run: `pytest tests/test_context.py -v`
Expected: 3 existing PASSED, 3 new FAILED

- [ ] **Step 3: Update `src/bashmage/context/__init__.py`**

```python
from collections.abc import Callable
from pathlib import Path

from bashmage.context import maven, node, python
from bashmage.storage import Command

_LOADERS: list[tuple[
    Callable[[Path], bool],
    Callable[[Path], list[Command]],
]] = [
    (node.detect, node.load),
    (python.detect, python.load),
    (maven.detect, maven.load),
]


def load_context_commands(cwd: Path) -> list[Command]:
    commands: list[Command] = []
    for detect_fn, load_fn in _LOADERS:
        try:
            if detect_fn(cwd):
                commands.extend(load_fn(cwd))
        except Exception:
            pass
    return commands
```

- [ ] **Step 4: Run the full test suite**

Run: `pytest tests/ -v`
Expected: all tests PASSED

- [ ] **Step 5: Commit**

```bash
git add src/bashmage/context/__init__.py tests/test_context.py
git commit -m "feat: register Python and Maven loaders in context registry"
```
