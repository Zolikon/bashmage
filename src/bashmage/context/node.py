import json
from pathlib import Path

from bashmage.storage import Command


def detect(cwd: Path) -> bool:
    return (cwd / "package.json").exists()


def load(cwd: Path) -> list[Command]:
    try:
        data = json.loads((cwd / "package.json").read_text())
    except Exception:
        return []

    scripts = data.get("scripts", {})
    if not scripts:
        return []

    if (cwd / "yarn.lock").exists():
        manager = "yarn"
        run_prefix = "yarn"
    else:
        manager = "npm"
        run_prefix = "npm run"

    return [
        Command(
            name=key,
            description=value,
            command=f"{run_prefix} {key}",
            tags=["local", manager],
        )
        for key, value in scripts.items()
    ]
