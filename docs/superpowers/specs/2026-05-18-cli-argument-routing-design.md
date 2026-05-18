# CLI Argument Routing Design

**Date:** 2026-05-18

## Overview

Add support for a positional argument to the `bashmage` CLI that enables two new behaviours:

1. **Exact shortcut match** — bypass the TUI entirely and deliver the command directly to the shell.
2. **Partial / no match** — open the TUI with the search bar pre-filled with the argument.

## Argument Routing

`__main__.py` inspects `sys.argv` after the existing `--init` guard. If exactly one positional argument is present, it is treated as a query string. After commands are loaded, the routing logic is:

| Condition | Behaviour |
|---|---|
| Exact shortcut match, no placeholders | Print command string, exit 0. No Textual. |
| Exact shortcut match, with placeholders | Run `PlaceholderApp(command)`. Print result on confirm, exit 0. Exit 1 on cancel. |
| No exact shortcut match | Run `BashMageApp(commands, initial_query=query)`. |
| No argument | Existing behaviour — run `BashMageApp(commands)`. |

Shortcut matching is exact and case-sensitive. If multiple commands share the same shortcut, the first in the loaded command list wins.

## Components

### `__main__.py` changes

- Add `_find_by_shortcut(commands, query) -> Command | None` helper.
- Add routing block after the `--init` check using the table above.

### `BashMageApp` changes (`app.py`)

- Accept `initial_query: str = ""` parameter.
- On mount, if `initial_query` is non-empty: set the search bar input value and call `CommandList.filter(initial_query)` so the list is already narrowed when the TUI appears.
- Search bar remains focused and fully editable — behaviour after that point is unchanged.

### `PlaceholderApp` (new: `src/bashmage/app_placeholder.py`)

- Minimal Textual app with a blank screen.
- On mount, immediately pushes `PlaceholderModal(command)`.
- On modal dismiss: exits with the filled result string, or `None` if the user cancelled.
- No search bar, no command list, no footer.

## Edge Cases

- **Multiple commands with the same shortcut** — first match in list order wins.
- **Shortcut matching** — exact, case-sensitive. `bashmage AB` does not match shortcut `ab`.
- **Multi-word argument** — `sys.argv[1]` is a single shell token; quoting is the user's responsibility. `bashmage "cd work"` prefills `cd work` in the search bar.
- **`--init` priority** — the `--init` check runs before shortcut/prefill logic; unaffected.
