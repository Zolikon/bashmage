import re
import tomllib
from dataclasses import dataclass
from pathlib import Path


CONFIG_PATH = Path.home() / ".config" / "bashmage" / "commands.toml"

DEFAULT_COMMANDS = """\
[[commands]]
name = "git-status"
description = "Show working tree status"
command = "git status --short --branch"

[[commands]]
name = "kill-port"
description = "Kill process on a port"
command = "kill -9 $(lsof -t -i:{port})"

[[commands]]
name = "list-ports"
description = "List all listening ports"
command = "lsof -i -P -n | grep LISTEN"
"""


@dataclass
class Command:
    name: str
    description: str
    command: str

    @property
    def placeholders(self) -> list[str]:
        return list(dict.fromkeys(re.findall(r'\{(\w+)\}', self.command)))

    def fill(self, values: dict[str, str]) -> str:
        result = self.command
        for key, value in values.items():
            result = result.replace(f'{{{key}}}', value)
        return result


def load_commands() -> list[Command]:
    if not CONFIG_PATH.exists():
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(DEFAULT_COMMANDS)
    data = tomllib.loads(CONFIG_PATH.read_text())
    return [Command(**c) for c in data.get("commands", [])]
