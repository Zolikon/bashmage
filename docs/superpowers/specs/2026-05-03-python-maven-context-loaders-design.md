# Python and Maven Context Loaders

## Overview

Extend bashmage's context detection with two new loaders: Python (uv/pip) and Java Maven. Both follow the existing `detect` / `load` module pattern and are registered in `context/__init__.py`.

## Python Loader (`context/python.py`)

### Detection

Returns `True` if `pyproject.toml` or `requirements.txt` exists in `cwd`.

### Manager selection

| Condition | Manager | Standard commands |
|---|---|---|
| `pyproject.toml` + `uv.lock` present | `uv` | `uv sync`, `uv run`, `uv add`, `uv lock` |
| `pyproject.toml` present, no `uv.lock` | `pip` | `pip install -e .` |
| only `requirements.txt` present | `pip` | `pip install -r requirements.txt` |

### Dynamic tasks

When `pyproject.toml` is present, parse it with `tomllib` and check in order:
1. `[tool.taskipy.tasks]` — emit `task <name>` for each entry; task value (always a string) is the description
2. `[tool.poe.tasks]` — emit `poe <name>` for each entry; if value is a string use it as description; if value is a dict use `help` key as description (falling back to `cmd`); skip entries that are neither
3. Neither present — no dynamic commands

When both `pyproject.toml` and `requirements.txt` exist, `pyproject.toml` takes precedence for manager selection and dynamic tasks.

Tags for all commands: `["local", manager]`.

## Maven Loader (`context/maven.py`)

### Detection

Returns `True` if `pom.xml` exists in `cwd`.

### Commands

Fixed set of standard lifecycle phases — no `pom.xml` parsing:

| name | command | description |
|---|---|---|
| clean | `mvn clean` | Remove build artifacts |
| compile | `mvn compile` | Compile source code |
| test | `mvn test` | Run tests |
| package | `mvn package` | Build JAR/WAR |
| install | `mvn install` | Install to local repository |
| clean-install | `mvn clean install` | Clean, build, and install |

Tags: `["local", "maven"]`.

## Registry (`context/__init__.py`)

Add both loaders to `_LOADERS`. Remove the `# future` comment.

```python
_LOADERS = [
    (node.detect, node.load),
    (python.detect, python.load),
    (maven.detect, maven.load),
]
```

## Error handling

Existing `try/except Exception: pass` guard in `load_context_commands` covers all loaders — no additional handling needed.

## Testing

Each loader gets its own test file (`test_context_python.py`, `test_context_maven.py`) following the same pattern as `test_context_node.py`. Integration tests in `test_context.py` cover detection routing.
