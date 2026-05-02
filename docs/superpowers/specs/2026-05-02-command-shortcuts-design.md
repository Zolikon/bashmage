# Command Shortcuts

## Overview

Add an optional `shortcut` field to each command in the config. Shortcuts are short, space-free strings (e.g. `sw`) that participate in normal search, letting users find commands faster once they learn their shortcuts.

## Data Model

`Command` dataclass in `storage.py` gets a new optional field:

```python
shortcut: str | None = None
```

`_parse_command` pops `shortcut` from the raw TOML dict before the `**raw` spread, defaulting to `None` if absent. No changes to `DEFAULT_COMMANDS`.

TOML example:

```toml
[[commands]]
name = "switch-branch"
shortcut = "sw"
description = "Switch git branch"
command = "git checkout {branch}"
tags = "git"
```

## Search

In `CommandList.filter()`, the `matches()` function adds a shortcut check alongside `name` and `description` for each text token:

```python
if (
    t not in c.name.lower()
    and t not in c.description.lower()
    and (c.shortcut is None or t not in c.shortcut.lower())
):
    return False
```

Tag tokens (`#word`) are unaffected. No new search syntax is introduced.

## Display

`CommandItem.compose()` renders the shortcut in bold brackets after the command name:

```
switch-branch [sw]
<dim>Switch git branch</dim>
```

Implementation:

```python
name_part = f"{self.command.name} [bold][[{self.command.shortcut}]][/bold]" if self.command.shortcut else self.command.name
Label(f"{name_part}\n[dim]{self.command.description}[/dim]")
```

Commands without a shortcut render unchanged. No changes to the detail panel.

## Files Changed

- `src/bashmage/storage.py` — add `shortcut` field to `Command`, update `_parse_command`
- `src/bashmage/widgets/command_list.py` — update `matches()` in `filter()`, update `CommandItem.compose()`
- `tests/test_storage.py` — add coverage for shortcut parsing (present and absent)
- `tests/test_app.py` — add coverage for shortcut search filtering and display
