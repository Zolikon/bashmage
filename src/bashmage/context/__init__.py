from collections.abc import Callable
from pathlib import Path

from bashmage.context import node
from bashmage.storage import Command

_LOADERS: list[tuple[
    Callable[[Path], bool],
    Callable[[Path], list[Command]],
]] = [
    (node.detect, node.load),
    # future: (python.detect, python.load)
]


def load_context_commands(cwd: Path) -> list[Command]:
    commands: list[Command] = []
    for detect_fn, load_fn in _LOADERS:
        if detect_fn(cwd):
            commands.extend(load_fn(cwd))
    return commands
