# BashMage

A terminal UI for managing and running your personal command library.

Browse, search, and launch shell commands without remembering the exact syntax. Select a command, fill in any placeholders, and the resolved command lands directly in your shell prompt — ready to run or edit.

## Demo

```
┌─────────────────────────────────────────────┐
│  [search...                               ] │
├──────────────────────────┬──────────────────┤
│  git-status              │  COMMAND         │
│  Show working tree...    │  git status      │
│                          │  --short --branch│
│  kill-port               │                  │
│  Kill process on a port  │                  │
│                          │                  │
│  list-ports              │                  │
│  List all listening...   │                  │
├──────────────────────────┴──────────────────┤
│  ↑↓ navigate · Enter select · q quit        │
└─────────────────────────────────────────────┘
```

## Installation

Requires [uv](https://docs.astral.sh/uv/).

```bash
git clone <repo>
cd bashmage
source ./install.sh
```

`install.sh` does three things:
1. Installs the `bashmage` CLI via `uv tool install --editable .`
2. Appends `eval "$(bashmage --init)"` to `~/.zshrc` (skipped if already present)
3. Reloads `~/.zshrc`

After installation, press **Ctrl+B** in any terminal to open BashMage. The selected command is inserted directly into your prompt buffer.

> Run with `source ./install.sh` (not `./install.sh`) so the shell reload takes effect in your current terminal.

## Usage

| Key | Action |
|-----|--------|
| Type anything | Filter commands by name or description |
| `#tag` | Filter by tag (e.g. `#git`) |
| `text #tag` | Combined AND filter |
| `↑` / `↓` | Navigate the list |
| `Enter` | Select command |
| `Esc` | Clear search |
| `q` | Quit without selecting |

### Placeholder commands

Commands containing `{placeholder}` tokens open a fill-in dialog on selection:

```
┌──────────────────────────────────────┐
│  Fill in placeholders                │
│  kill -9 $(lsof -t -i:{port})        │
│                                      │
│  PORT                                │
│  [ 3000                            ] │
│                                      │
│               [Cancel]  [Confirm]    │
└──────────────────────────────────────┘
```

Press **Enter** to advance between fields; **Enter** on the last field confirms. **Esc** cancels and returns to the list.

## Command library

Commands are stored in `~/.config/bashmage/commands.toml`. The file is created automatically on first run with a few example commands.

```toml
[[commands]]
name = "git-status"
description = "Show working tree status"
command = "git status --short --branch"
tags = "git,status"

[[commands]]
name = "kill-port"
description = "Kill process on a port"
command = "kill -9 $(lsof -t -i:{port})"
tags = "network,ports"

[[commands]]
name = "pg-dump-table"
description = "Dump a specific table from PostgreSQL"
command = "pg_dump -h {host} -U {user} -d {database} -t {table} > {file}"
tags = "postgres,database"
```

| Field | Required | Description |
|-------|----------|-------------|
| `name` | yes | Short identifier shown in the list |
| `description` | yes | One-line description shown below the name |
| `command` | yes | Shell command; use `{name}` for placeholders |
| `tags` | no | Comma-separated tags for `#tag` filtering |

Edit the file in any text editor. Changes take effect on the next launch.

## Shell integration

The `--init` flag prints the shell integration snippet:

```bash
bashmage --init        # auto-detects zsh or bash
bashmage --init zsh    # explicit
bashmage --init bash   # explicit
```

Add it to your shell config manually if preferred:

```bash
echo 'eval "$(bashmage --init)"' >> ~/.zshrc
source ~/.zshrc
```

## Development

```bash
# install in editable mode
uv tool install --editable .

# run tests
python -m pytest
```
