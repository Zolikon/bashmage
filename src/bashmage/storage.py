import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path


CONFIG_PATH = Path.home() / ".config" / "bashmage" / "commands.toml"

DEFAULT_COMMANDS = """\
[[commands]]
name = "list-files"
description = "List all files with details"
command = "ls -la"
tags = "files,listing"

[[commands]]
name = "find-file"
description = "Find file by name"
command = 'find . -name "{name}"'
tags = "files,search"

[[commands]]
name = "grep-text"
description = "Search text recursively in directory"
command = 'grep -r "{pattern}" .'
tags = "search,text"

[[commands]]
name = "find-process"
description = "Find running process by name"
command = "ps aux | grep {process}"
tags = "process,system"

[[commands]]
name = "disk-usage"
description = "Show disk usage for all mounts"
command = "df -h"
tags = "disk,system"

[[commands]]
name = "dir-sizes"
description = "Show sizes of items in directory"
command = "du -sh {path}/*"
tags = "disk,files"

[[commands]]
name = "tail-log"
description = "Follow a log file in real time"
command = "tail -f {file}"
tags = "logs,monitoring"

[[commands]]
name = "http-get"
description = "HTTP GET request"
command = "curl -s {url}"
tags = "network,http"

[[commands]]
name = "make-executable"
description = "Make file executable"
command = "chmod +x {file}"
tags = "files,permissions"

[[commands]]
name = "extract-tar"
description = "Extract a tar.gz archive"
command = "tar -xzf {archive}"
tags = "archive,files"

[[commands]]
name = "create-tar"
description = "Create a tar.gz archive"
command = "tar -czf {archive}.tar.gz {dir}"
tags = "archive,files"

[[commands]]
name = "ssh-connect"
description = "Connect to remote host via SSH"
command = "ssh {user}@{host}"
tags = "network,remote"

[[commands]]
name = "copy-remote"
description = "Copy file to remote host"
command = "scp {file} {user}@{host}:{path}"
tags = "network,remote"

[[commands]]
name = "download-file"
description = "Download file from URL"
command = "wget {url}"
tags = "network,download"

[[commands]]
name = "count-lines"
description = "Count lines in a file"
command = "wc -l {file}"
tags = "text,files"

[[commands]]
name = "find-replace"
description = "Find and replace text in file"
command = "sed -i 's/{old}/{new}/g' {file}"
tags = "text,files"

[[commands]]
name = "env-grep"
description = "Find environment variable by name"
command = "env | grep {var}"
tags = "environment,system"

[[commands]]
name = "make-dir"
description = "Create nested directories"
command = "mkdir -p {path}"
tags = "files,directories"

[[commands]]
name = "kill-port"
description = "Kill process listening on a port"
command = "kill -9 $(lsof -t -i:{port})"
tags = "network,ports"

[[commands]]
name = "list-ports"
description = "List all listening ports"
command = "lsof -i -P -n | grep LISTEN"
tags = "network,ports"
"""


@dataclass
class Command:
    name: str
    description: str
    command: str
    tags: list[str] = field(default_factory=list)
    shortcut: str | None = None
    path: str | None = None

    @property
    def placeholders(self) -> list[str]:
        return list(dict.fromkeys(re.findall(r'\{(\w+)\}', self.command)))

    def fill(self, values: dict[str, str]) -> str:
        result = self.command
        for key, value in values.items():
            result = result.replace(f'{{{key}}}', value)
        return result


def _parse_command(raw: dict) -> Command:
    tags_str = raw.pop("tags", "")
    tags = [t for t in (t.strip() for t in tags_str.split(",")) if t] if tags_str else []
    shortcut = raw.pop("shortcut", None)
    path = raw.pop("path", None)
    return Command(**raw, tags=tags, shortcut=shortcut, path=path)


def load_commands() -> list[Command]:
    if not CONFIG_PATH.exists():
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(DEFAULT_COMMANDS)
    data = tomllib.loads(CONFIG_PATH.read_text())
    return [_parse_command(dict(c)) for c in data.get("commands", [])]
