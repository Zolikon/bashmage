from bashmage.__main__ import _find_by_shortcut
from bashmage.storage import Command


COMMANDS = [
    Command("git-status", "Show status", "git status", shortcut="gs"),
    Command("docker-up", "Start docker", "docker compose up -d", shortcut="du"),
    Command("kill-port", "Kill port", "kill -9 $(lsof -t -i:{port})"),
]


def test_find_by_shortcut_returns_matching_command():
    result = _find_by_shortcut(COMMANDS, "gs")
    assert result is not None
    assert result.name == "git-status"


def test_find_by_shortcut_returns_second_match():
    result = _find_by_shortcut(COMMANDS, "du")
    assert result is not None
    assert result.name == "docker-up"


def test_find_by_shortcut_returns_none_when_no_match():
    assert _find_by_shortcut(COMMANDS, "GS") is None


def test_find_by_shortcut_returns_none_for_partial_match():
    assert _find_by_shortcut(COMMANDS, "g") is None


def test_find_by_shortcut_returns_none_when_command_has_no_shortcut():
    assert _find_by_shortcut(COMMANDS, "kill-port") is None


def test_find_by_shortcut_returns_first_on_duplicate_shortcut():
    commands = [
        Command("cmd-a", "First", "echo a", shortcut="x"),
        Command("cmd-b", "Second", "echo b", shortcut="x"),
    ]
    result = _find_by_shortcut(commands, "x")
    assert result is not None
    assert result.name == "cmd-a"
