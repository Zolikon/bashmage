# BashMage — Design Spec

**Date:** 2026-04-30  
**Status:** Approved

---

## Overview

BashMage is a terminal UI application for managing and launching bash commands. The user browses or searches a personal command library, selects a command, optionally fills in placeholders, and the resolved command is printed to stdout on exit — ready to run or capture with `eval $(bashmage)`.

---

## Architecture

### Project structure

```
bashmage/
├── pyproject.toml
└── src/
    └── bashmage/
        ├── __main__.py        # entry point — runs app, prints command to stdout on exit
        ├── app.py             # Textual App class, layout, keybindings
        ├── storage.py         # TOML loader, Command dataclass, placeholder parsing
        └── widgets/
            ├── search_bar.py  # input widget, drives list filtering
            ├── command_list.py    # left panel — filtered ListView
            └── detail_panel.py   # right panel — command template preview
```

### Tech stack

- **Language:** Python 3.11+
- **TUI framework:** [Textual](https://textual.textualize.io/)
- **Config format:** TOML (`tomllib` stdlib, Python 3.11+)
- **Packaging:** `pyproject.toml`, installable via `pipx install .`
- **Entry point:** `bashmage` CLI command

---

## Data Model

Commands are stored in `~/.config/bashmage/commands.toml`.

```toml
[[commands]]
name = "git-status"
description = "Show working tree status"
command = "git status --short --branch"

[[commands]]
name = "kill-port"
description = "Kill process on a port"
command = "kill -9 $(lsof -t -i:{port})"

[[commands]]
name = "pg-dump-table"
description = "Dump a specific table from a PostgreSQL database"
command = "pg_dump -h {host} -U {user} -d {database} -t {table} > {file}"
```

### Command dataclass

```python
@dataclass
class Command:
    name: str
    description: str
    command: str

    @property
    def placeholders(self) -> list[str]:
        # returns ordered, deduplicated list of {placeholder} names
        return list(dict.fromkeys(re.findall(r'\{(\w+)\}', self.command)))

    def fill(self, values: dict[str, str]) -> str:
        result = self.command
        for key, value in values.items():
            result = result.replace(f'{{{key}}}', value)
        return result
```

---

## TUI Layout

**Layout: Search + Split Preview (option C)**

```
┌─────────────────────────────────────────────┐
│  🔍 [search bar — always visible at top   ] │
├──────────────────────────┬──────────────────┤
│  kill-port               │  COMMAND         │
│  Kill process on a port  │  kill -9 $(lsof  │
│                          │  -t -i:{port})   │
│  git-status              │                  │
│  Show working tree...    │                  │
│                          │                  │
│  pg-dump-table           │                  │
│  Dump a specific table   │                  │
├──────────────────────────┴──────────────────┤
│  ↑↓ navigate · Enter select · q quit        │
└─────────────────────────────────────────────┘
```

- Typing any character focuses the search bar and filters the list in real time
- Search matches by **contains** on both `name` and `description` (case-insensitive)
- `Esc` clears the search and shows the full list
- The right panel updates immediately as the cursor moves through the list

---

## Placeholder Flow

When the user presses `Enter` on a command that contains `{placeholder}` tokens, a **modal dialog** appears over the dimmed main screen.

```
┌──────────────────────────────────┐
│  Fill in placeholders            │
│  kill -9 $(lsof -t -i:{port})    │
│                                  │
│  PORT                            │
│  [ 3000                        ] │
│                                  │
│           [Esc cancel] [Enter ✓] │
└──────────────────────────────────┘
```

- One labeled input field per unique placeholder, in order of appearance in the command string
- `Tab` / `Shift+Tab` moves between fields
- `Enter` confirms — all fields must be non-empty to confirm
- `Esc` dismisses the modal and returns to the list without selecting
- Fields are empty by default; no pre-filled values

---

## Shell Output

When stdout is piped (e.g. inside `eval $(bashmage)`), Textual must not render to stdout — it would corrupt the captured output. The entry point redirects Textual's rendering to `/dev/tty` whenever stdout is not a TTY, preserving stdout for the command string:

```python
# __main__.py (sketch)
import sys, os

output_fd = sys.stdout
if not sys.stdout.isatty():
    tty = open('/dev/tty', 'w')
    sys.stdout = tty
    sys.stderr = tty

app = BashMageApp()
app.run()

sys.stdout = output_fd
if app.selected_command:
    print(app.selected_command)
    sys.exit(0)
else:
    sys.exit(1)
```

After the app exits and the alternate screen is cleared:

- **Command selected:** the resolved command string is printed to stdout, exit code `0`
- **Quit without selecting** (`q` or `Ctrl+C`): nothing printed, exit code `1`

Recommended shell usage:
```bash
eval $(bashmage)
# or capture it
cmd=$(bashmage) && echo "Will run: $cmd"
```

---

## Storage

| Detail | Value |
|--------|-------|
| Config file | `~/.config/bashmage/commands.toml` |
| Created on first run | Yes — with a small set of example commands |
| Edit method | Manually in any text editor |
| Reload | On each app launch (no hot-reload) |

If the config file is missing or malformed TOML, BashMage prints an error to stderr and exits with code `1`.

---

## Error Handling

| Scenario | Behaviour |
|----------|-----------|
| Config file missing | Auto-create with example commands |
| Invalid TOML | Print parse error to stderr, exit 1 |
| No commands in file | Show empty state message in list panel |
| Search yields no results | Show "No matches" in list panel |
| Placeholder field left empty | Disable confirm button, show inline hint |

---

## Out of Scope (for now)

- Adding / editing / deleting commands from within the app
- Categories or tags
- Fuzzy search (contains-match is sufficient)
- Hot-reload of config file
- Command history or favourites
