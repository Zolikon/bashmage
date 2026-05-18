# Path-Prefix Filtering for Commands

**Date:** 2026-05-18

## Overview

Add an optional `path` field to global commands that restricts visibility to invocations from directories that are at or below the configured path prefix. Detected (context) commands are unaffected.

## Data Model

Add `path: str | None = None` to the `Command` dataclass in `storage.py`. Parsed from TOML in `_parse_command` the same way `shortcut` is handled — absent key defaults to `None`.

Example TOML:
```toml
[[commands]]
name = "deploy"
path = "~/projects/myapp"
command = "make deploy"
```

Add `filter_by_path(commands: list[Command], cwd: Path) -> list[Command]` to `storage.py`. A command passes the filter when:
- `path` is `None`, OR
- `Path(path).expanduser().resolve()` is an ancestor-or-equal of `cwd` (i.e. `cwd.is_relative_to(resolved_path)`)

`~` expansion is supported. Path comparison is case-sensitive (consistent with filesystem operations).

## Entry Point

In `main()`, apply `filter_by_path` to global commands only, before merging with context commands:

```python
global_commands = filter_by_path(load_commands(), Path.cwd())
context_commands = load_context_commands(Path.cwd())
commands = context_commands + global_commands
```

The filtered list flows into both `BashMageApp` (TUI) and `_find_by_shortcut` (shortcut bypass) automatically — no changes required in either function.

## Matching Semantics

Given CWD `/test/a`:
- No `path` → visible
- `path = "/test"` → visible (ancestor)
- `path = "/test/a"` → visible (exact match)
- `path = "/test2/a"` → hidden (different subtree)
- `path = "/test/b"` → hidden (sibling, not ancestor)

## Tests

New tests in `test_storage.py`:
- `path=None` always passes filter
- Ancestor path passes
- Exact-match path passes
- Non-ancestor path is excluded
- Sibling path is excluded
- `~` expansion resolves correctly
