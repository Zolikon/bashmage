import pytest
import tomllib
from pathlib import Path
from unittest.mock import patch
from bashmage.storage import Command, load_commands, filter_by_path, AIConfig, load_ai_config, AI_CONFIG_PATH


def test_no_placeholders():
    cmd = Command("git-status", "Show status", "git status --short")
    assert cmd.placeholders == []


def test_single_placeholder():
    cmd = Command("kill-port", "Kill port", "kill -9 $(lsof -t -i:{port})")
    assert cmd.placeholders == ["port"]


def test_multiple_placeholders_ordered():
    cmd = Command("pg-dump", "Dump table", "pg_dump -h {host} -U {user} -d {database}")
    assert cmd.placeholders == ["host", "user", "database"]


def test_duplicate_placeholder_deduplicated():
    cmd = Command("repeat", "Repeat", "echo {msg} && echo {msg}")
    assert cmd.placeholders == ["msg"]


def test_fill_single_value():
    cmd = Command("kill-port", "Kill port", "kill -9 $(lsof -t -i:{port})")
    assert cmd.fill({"port": "3000"}) == "kill -9 $(lsof -t -i:3000)"


def test_fill_multiple_values():
    cmd = Command("pg-dump", "Dump", "pg_dump -h {host} -U {user}")
    assert cmd.fill({"host": "localhost", "user": "postgres"}) == "pg_dump -h localhost -U postgres"


def test_fill_leaves_unfilled_placeholders_intact():
    cmd = Command("pg-dump", "Dump", "pg_dump -h {host} -U {user}")
    assert cmd.fill({"host": "localhost"}) == "pg_dump -h localhost -U {user}"


def test_load_commands_from_toml(tmp_path):
    config = tmp_path / "commands.toml"
    config.write_text("""\
[[commands]]
name = "test-cmd"
description = "A test command"
command = "echo hello"
""")
    with patch("bashmage.storage.CONFIG_PATH", config):
        commands = load_commands()
    assert len(commands) == 1
    assert commands[0].name == "test-cmd"
    assert commands[0].command == "echo hello"


def test_load_commands_creates_default_when_missing(tmp_path):
    config = tmp_path / "subdir" / "commands.toml"
    with patch("bashmage.storage.CONFIG_PATH", config):
        commands = load_commands()
    assert config.exists()
    assert len(commands) > 0
    assert all(isinstance(c, Command) for c in commands)


def test_load_commands_invalid_toml(tmp_path):
    config = tmp_path / "commands.toml"
    config.write_text("this is not [ valid toml !!!")
    with patch("bashmage.storage.CONFIG_PATH", config):
        with pytest.raises(tomllib.TOMLDecodeError):
            load_commands()


def test_load_commands_empty_file_returns_empty_list(tmp_path):
    config = tmp_path / "commands.toml"
    config.write_text("")
    with patch("bashmage.storage.CONFIG_PATH", config):
        commands = load_commands()
    assert commands == []


def test_tags_parsed_from_toml(tmp_path):
    config = tmp_path / "commands.toml"
    config.write_text("""\
[[commands]]
name = "git-status"
description = "Show status"
command = "git status"
tags = "git,status"
""")
    with patch("bashmage.storage.CONFIG_PATH", config):
        commands = load_commands()
    assert commands[0].tags == ["git", "status"]


def test_tags_default_to_empty_when_absent(tmp_path):
    config = tmp_path / "commands.toml"
    config.write_text("""\
[[commands]]
name = "git-status"
description = "Show status"
command = "git status"
""")
    with patch("bashmage.storage.CONFIG_PATH", config):
        commands = load_commands()
    assert commands[0].tags == []


def test_shortcut_parsed_from_toml(tmp_path):
    config = tmp_path / "commands.toml"
    config.write_text("""\
[[commands]]
name = "switch-branch"
shortcut = "sw"
description = "Switch git branch"
command = "git checkout {branch}"
tags = "git"
""")
    with patch("bashmage.storage.CONFIG_PATH", config):
        commands = load_commands()
    assert commands[0].shortcut == "sw"


def test_shortcut_defaults_to_none_when_absent(tmp_path):
    config = tmp_path / "commands.toml"
    config.write_text("""\
[[commands]]
name = "git-status"
description = "Show status"
command = "git status"
""")
    with patch("bashmage.storage.CONFIG_PATH", config):
        commands = load_commands()
    assert commands[0].shortcut is None


def test_path_parsed_from_toml(tmp_path):
    config = tmp_path / "commands.toml"
    config.write_text("""\
[[commands]]
name = "deploy"
description = "Deploy app"
command = "make deploy"
path = "~/projects/myapp"
""")
    with patch("bashmage.storage.CONFIG_PATH", config):
        commands = load_commands()
    assert commands[0].path == "~/projects/myapp"


def test_path_defaults_to_none_when_absent(tmp_path):
    config = tmp_path / "commands.toml"
    config.write_text("""\
[[commands]]
name = "git-status"
description = "Show status"
command = "git status"
""")
    with patch("bashmage.storage.CONFIG_PATH", config):
        commands = load_commands()
    assert commands[0].path is None


def _make_cmd(path=None):
    return Command(name="x", description="x", command="echo x", path=path)


def test_filter_no_path_always_passes():
    cmd = _make_cmd(path=None)
    assert filter_by_path([cmd], Path("/any/dir")) == [cmd]


def test_filter_ancestor_path_passes():
    cmd = _make_cmd(path="/test")
    assert filter_by_path([cmd], Path("/test/a")) == [cmd]


def test_filter_exact_match_passes():
    cmd = _make_cmd(path="/test/a")
    assert filter_by_path([cmd], Path("/test/a")) == [cmd]


def test_filter_non_ancestor_excluded():
    cmd = _make_cmd(path="/test2/a")
    assert filter_by_path([cmd], Path("/test/a")) == []


def test_filter_sibling_excluded():
    cmd = _make_cmd(path="/test/b")
    assert filter_by_path([cmd], Path("/test/a")) == []


def test_filter_tilde_expansion():
    home = Path.home()
    cmd = _make_cmd(path="~/projects")
    assert filter_by_path([cmd], home / "projects" / "myapp") == [cmd]


def test_filter_mixed_commands():
    visible_no_path = _make_cmd(path=None)
    visible_ancestor = Command(name="ancestor", description="x", command="echo x", path="/test")
    hidden = Command(name="hidden", description="x", command="echo x", path="/test/b")
    result = filter_by_path([visible_no_path, visible_ancestor, hidden], Path("/test/a"))
    assert visible_no_path in result
    assert visible_ancestor in result
    assert hidden not in result


def test_filter_empty_list():
    assert filter_by_path([], Path("/any/dir")) == []


def test_load_ai_config_returns_none_when_section_absent(tmp_path):
    config = tmp_path / "config.toml"
    config.write_text("[other]\nkey = 'value'\n")
    with patch("bashmage.storage.AI_CONFIG_PATH", config):
        assert load_ai_config() is None


def test_load_ai_config_returns_none_when_file_missing(tmp_path):
    config = tmp_path / "config.toml"
    with patch("bashmage.storage.AI_CONFIG_PATH", config):
        assert load_ai_config() is None


def test_load_ai_config_parses_model(tmp_path):
    config = tmp_path / "config.toml"
    config.write_text('[ai]\nmodel = "llama3.2"\n')
    with patch("bashmage.storage.AI_CONFIG_PATH", config):
        ai = load_ai_config()
    assert ai is not None
    assert ai.model == "llama3.2"


def test_load_ai_config_uses_default_base_url_when_absent(tmp_path):
    config = tmp_path / "config.toml"
    config.write_text('[ai]\nmodel = "llama3.2"\n')
    with patch("bashmage.storage.AI_CONFIG_PATH", config):
        ai = load_ai_config()
    assert ai.base_url == "http://localhost:11434"


def test_load_ai_config_parses_custom_base_url(tmp_path):
    config = tmp_path / "config.toml"
    config.write_text('[ai]\nmodel = "llama3.2"\nbase_url = "http://myhost:9999"\n')
    with patch("bashmage.storage.AI_CONFIG_PATH", config):
        ai = load_ai_config()
    assert ai.base_url == "http://myhost:9999"
