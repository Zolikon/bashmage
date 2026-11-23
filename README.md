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
| `?text` | Generate a command with AI (see [AI mode](#ai-mode)) |

### Command-line arguments

```bash
bashmage git        # open the TUI with "git" prefilled in the search
bashmage gs         # if "gs" is a command's shortcut, run it directly
```

If the argument matches a command's `shortcut`, BashMage skips the list. A command without placeholders is printed immediately. A command with placeholders opens the fill-in dialog. Any other argument becomes the initial search query.

The zsh integration also defines the alias `bm` for `bashmage`.

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
| `shortcut` | no | Short alias; `bashmage <shortcut>` runs the command directly |
| `path` | no | Only show the command when the current directory is inside this path (`~` is expanded) |

```toml
[[commands]]
name = "deploy-site"
description = "Deploy the website"
command = "make deploy"
shortcut = "dep"
path = "~/work/site"
```

Edit the file in any text editor. Changes take effect on the next launch.

## Context commands

If the current directory contains a `package.json`, its `scripts` are added to the list automatically, tagged `local` and `npm` (or `yarn` when a `yarn.lock` exists). They are listed before your own commands.

## AI mode

BashMage can generate commands from a plain-language description using a local [Ollama](https://ollama.com) model. Create `~/.config/bashmage/config.toml`:

```toml
[ai]
model = "llama3"
base_url = "http://localhost:11434"   # optional, this is the default
```

When configured, the header shows `✨ using <model>`. Type `?` followed by a description (up to 1000 characters) in the search bar, e.g. `?find files larger than 100MB`, and press **Enter**. Review the generated command and accept it. Placeholders are filled in as usual. Without `config.toml`, AI mode is disabled.

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
