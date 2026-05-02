import json
from pathlib import Path

from bashmage.context import load_context_commands


def test_returns_empty_for_unknown_project_type(tmp_path):
    cmds = load_context_commands(tmp_path)
    assert cmds == []


def test_returns_node_commands_for_js_project(tmp_path):
    pkg = {"scripts": {"build": "webpack"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    cmds = load_context_commands(tmp_path)
    assert len(cmds) == 1
    assert cmds[0].name == "build"


def test_node_commands_have_local_tag(tmp_path):
    pkg = {"scripts": {"test": "jest"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    cmds = load_context_commands(tmp_path)
    assert "local" in cmds[0].tags
