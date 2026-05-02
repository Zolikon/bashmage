# Context-Aware Commands

**Date:** 2026-05-02

## Overview

When bashmage opens, it detects the project type of the current working directory and prepends dynamically loaded "local" commands to the global command list. The first implementation handles Node.js/npm/yarn projects by reading `package.json` scripts.

## Architecture

### Entry point (`__main__.py`)

`main()` gains two lines before constructing `BashMageApp`:

```python
cwd = Path.cwd()
context_cmds = load_context_commands(cwd)
global_cmds  = load_commands()
commands = context_cmds + global_cmds
```

Context commands appear at the top of the list.

### Context package (`src/bashmage/context/`)

`__init__.py` exports `load_context_commands(cwd: Path) -> list[Command]`.

It holds a `_LOADERS` registry — a list of `(detect_fn, load_fn)` tuples:

```python
_LOADERS: list[tuple[
    Callable[[Path], bool],
    Callable[[Path], list[Command]],
]] = [
    (node.detect, node.load),
    # future: (python.detect, python.load)
]
```

`load_context_commands` iterates the registry, calls `load_fn(cwd)` for each loader where `detect_fn(cwd)` is `True`, and returns the concatenated results.

### Node.js loader (`src/bashmage/context/node.py`)

**`detect(cwd: Path) -> bool`**
Returns `True` if `cwd/package.json` exists.

**`load(cwd: Path) -> list[Command]`**
1. Parse `cwd/package.json`. On any error (missing, unreadable, invalid JSON), return `[]`.
2. Extract `scripts` dict. If absent or empty, return `[]`.
3. Determine package manager:
   - `yarn.lock` present → `yarn`
   - `package-lock.json` present → `npm`
   - fallback → `npm`
4. For each `(key, value)` in `scripts`:
   - `name`: `key`
   - `description`: `value` (the raw script string, so the user sees what it runs)
   - `command`: `yarn <key>` or `npm run <key>`
   - `tags`: `["local", "yarn"]` or `["local", "npm"]`
   - `shortcut`: `None`
5. Return the list.

## Error Handling

Context loaders are best-effort. Any failure (file not found, JSON decode error, unexpected structure) returns `[]` silently. A broken project config must never prevent bashmage from opening.

## Extensibility

Adding a new project type:
1. Create `src/bashmage/context/<type>.py` with `detect` and `load` functions.
2. Add `(<type>.detect, <type>.load)` to `_LOADERS` in `context/__init__.py`.

No other files need to change.

## Files Changed

| File | Change |
|------|--------|
| `src/bashmage/__main__.py` | Import `load_context_commands`, call it with `Path.cwd()`, prepend result |
| `src/bashmage/context/__init__.py` | New — exports `load_context_commands`, holds `_LOADERS` registry |
| `src/bashmage/context/node.py` | New — Node.js loader (`detect` + `load`) |
| `tests/test_context_node.py` | New — unit tests for node loader |
