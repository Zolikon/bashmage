# AI Command Generation — Design Spec

**Date:** 2026-05-26
**Status:** Approved

---

## Overview

BashMage gains an AI command generation mode powered by a locally running Ollama LLM. The user types a natural language query prefixed with `?` in the search bar and presses Enter; the LLM generates the appropriate bash command; the user reviews and accepts it. Once accepted, the command flows through the existing placeholder-fill and stdout-output path unchanged.

The feature is opt-in: it only activates when an `[ai]` section is present in `commands.toml`. Users without the section experience no change in behaviour.

---

## Architecture

### New files

```
src/bashmage/
├── ollama.py                        # OllamaClient — sync HTTP call to Ollama API
└── widgets/
    └── ai_result_modal.py           # AIResultModal — loading → result modal
```

### Changed files

```
src/bashmage/
├── storage.py      # AIConfig dataclass + load_ai_config()
├── app.py          # detect ? prefix, push AIResultModal, wire dismiss callback
└── __main__.py     # load AI config, pass to BashMageApp
```

All other files (`SearchBar`, `CommandList`, `DetailPanel`, `PlaceholderModal`, `Command`, `_activate()`) are untouched. The AI result feeds into `_activate()` exactly like a command selected from the list.

---

## Config Layer

`AIConfig` lives in `storage.py` alongside command loading — both read from the same `commands.toml`.

```toml
# ~/.config/bashmage/commands.toml

[ai]
model = "llama3.2"
base_url = "http://localhost:11434"   # optional, this is the default
```

```python
@dataclass
class AIConfig:
    model: str
    base_url: str = "http://localhost:11434"

def load_ai_config() -> AIConfig | None:
    if not CONFIG_PATH.exists():
        return None
    data = tomllib.loads(CONFIG_PATH.read_text())
    ai = data.get("ai")
    if ai is None:
        return None
    return AIConfig(model=ai["model"], base_url=ai.get("base_url", "http://localhost:11434"))
```

**Feature gate:** if `[ai]` is absent, `load_ai_config()` returns `None`. `BashMageApp` receives `None` and `?` is treated as a normal search query — the feature does not exist for that user.

---

## Search Bar + App Wiring

`SearchBar` itself is unchanged. All `?` detection happens in `BashMageApp`.

### `on_search_bar_changed`

When query starts with `?` and AI is configured: skip `CommandList.filter()` and call a new `CommandList.show_ai_hint()` that renders a single dimmed placeholder item `"✨ press Enter to generate with AI"`. Normal query → normal filter as today.

### `action_select_command`

```python
def action_select_command(self) -> None:
    query = self.query_one(SearchBar).value
    if self._ai_config is not None and query.startswith("?"):
        natural = query[1:].strip()
        if natural:
            self.push_screen(AIResultModal(natural, self._ai_config), self._on_ai_result)
        return
    cmd = self.query_one(CommandList).get_highlighted_command()
    if cmd is not None:
        self._activate(cmd)

def _on_ai_result(self, command: Command | None) -> None:
    if command is not None:
        self._activate(command)
```

### `BashMageApp.__init__`

Gains one new parameter: `ai_config: AIConfig | None = None`.

### `__main__.py`

```python
ai_config = load_ai_config()
result = _run_app(BashMageApp(commands, initial_query=query or "", ai_config=ai_config))
```

---

## Ollama Client

`src/bashmage/ollama.py` — pure stdlib, no new dependencies.

```
POST {base_url}/api/generate
Content-Type: application/json

{"model": "...", "prompt": "...", "system": "...", "stream": false}
```

**System prompt instructs the LLM to:**
- Output the command only — no explanation, no markdown, no code fences
- Use `{placeholder}` syntax for values the user needs to supply (e.g. `{host}`, `{port}`, `{file}`)
- Multi-line commands are acceptable (backslash continuation or shell operators)
- Keep commands practical and idiomatic

**Key decisions:**
- `stream: false` — full command before display prevents showing commands with broken placeholder syntax mid-stream
- 60s timeout — local LLMs can be slow on first token
- `OllamaError` dataclass exception — caught by the modal and shown directly to the user

**Error cases handled:**
- Connection refused / Ollama not running → `OllamaError` with human-readable message
- Timeout → `OllamaError`
- Unexpected response shape → `OllamaError`

---

## AIResultModal

`src/bashmage/widgets/ai_result_modal.py` — a `ModalScreen[Command | None]` with three visual states.

### States

**Loading** (on mount, while worker runs):
```
┌──────────────────────────────────────┐
│  ✨ AI-generated command              │
│                                      │
│           ◐ loading...               │
│                                      │
└──────────────────────────────────────┘
```

**Result** (worker succeeded):
```
┌──────────────────────────────────────┐
│  ✨ AI-generated command              │
│                                      │
│  docker ps -a \                      │
│    --format '{{.Names}}\t{{.Ports}}' │
│    | grep {port}                     │
│                                      │
│        [Esc cancel]  [Enter accept ✓]│
└──────────────────────────────────────┘
```

**Error** (worker failed):
```
┌──────────────────────────────────────┐
│  ✨ AI-generated command              │
│                                      │
│  ✗ Cannot reach Ollama at            │
│    http://localhost:11434            │
│                                      │
│                        [Esc close]   │
└──────────────────────────────────────┘
```

### Lifecycle

1. `on_mount` → `self.run_worker(self._fetch, thread=True)`
2. `_fetch()` runs in worker thread → calls `OllamaClient.generate(query)`
3. `on_worker_state_changed` → `_show_result(text)` or `_show_error(msg)`
4. User presses Enter → `dismiss(Command(name="ai-generated", description=query, command=text))`
5. User presses Esc → `dismiss(None)`

### Dismiss protocol

Dismisses with `Command | None`. The `Command` has:
- `name = "ai-generated"`
- `description = <natural language query>`
- `command = <LLM output>`

`BashMageApp._on_ai_result` receives it and calls `_activate(command)`, which checks `.placeholders` and either pushes `PlaceholderModal` or exits. No changes to that flow.

### Multi-line support

`Static` renders `\n` naturally. LLM output with newlines or `\\\n` continuation displays correctly without special handling. `Command.placeholders` and `Command.fill()` both operate on the full multi-line string.

---

## Full User Flow

```
User types: ?find all docker containers using port 8080
User presses: Enter
  ↓
BashMageApp detects ? prefix → pushes AIResultModal("find all docker containers using port 8080")
  ↓
Modal mounts → Textual worker fires → OllamaClient.generate(prompt) blocks in thread
  ↓  (LLM responds)
Modal transitions to result state:
  docker ps -a --format '{{.Names}}\t{{.Ports}}' | grep {port}
  ↓
User presses Enter
  ↓
Modal dismisses with Command(command="...{port}...")
  ↓
BashMageApp._activate(cmd) → detects {port} placeholder → pushes PlaceholderModal
  ↓
User fills in port=8080 → PlaceholderModal dismisses with filled string
  ↓
BashMageApp.exit("docker ps -a --format '{{.Names}}\t{{.Ports}}' | grep 8080")
  ↓
Shell captures stdout → puts command on readline buffer
```

---

## Query Constraints

- Maximum query length: 1000 characters (enforced in `SearchBar` or `AIResultModal` — a `maxlength` on the search input or a guard in `action_select_command`)
- Empty query after `?` strip: no-op (Enter does nothing)

---

## Out of Scope

- Streaming token-by-token display (can be added later without design changes)
- Saving AI-generated commands back to `commands.toml`
- Multiple LLM runners (only Ollama supported)
- Retry on error from within the modal
- Context injection (cwd, detected project type) into the prompt
