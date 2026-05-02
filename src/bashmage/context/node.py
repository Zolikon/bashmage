from pathlib import Path


def detect(cwd: Path) -> bool:
    return (cwd / "package.json").exists()
