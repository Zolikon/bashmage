import json
from pathlib import Path
from bashmage.context.node import detect, load


def test_detect_returns_false_when_no_package_json(tmp_path):
    assert detect(tmp_path) is False


def test_detect_returns_true_when_package_json_exists(tmp_path):
    (tmp_path / "package.json").write_text("{}")
    assert detect(tmp_path) is True


def test_load_returns_empty_when_no_package_json(tmp_path):
    assert load(tmp_path) == []


def test_load_returns_empty_when_package_json_invalid_json(tmp_path):
    (tmp_path / "package.json").write_text("not json {{{")
    assert load(tmp_path) == []


def test_load_returns_empty_when_no_scripts_key(tmp_path):
    (tmp_path / "package.json").write_text('{"name": "my-app"}')
    assert load(tmp_path) == []


def test_load_returns_empty_when_scripts_is_empty(tmp_path):
    (tmp_path / "package.json").write_text('{"scripts": {}}')
    assert load(tmp_path) == []


def test_load_defaults_to_npm_when_no_lock_file(tmp_path):
    pkg = {"scripts": {"lint": "eslint ."}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    cmds = load(tmp_path)
    assert len(cmds) == 1
    assert cmds[0].command == "npm run lint"
    assert cmds[0].tags == ["local", "npm"]


def test_load_uses_npm_when_package_lock_present(tmp_path):
    pkg = {"scripts": {"build": "webpack"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    (tmp_path / "package-lock.json").write_text("{}")
    cmds = load(tmp_path)
    assert cmds[0].command == "npm run build"
    assert cmds[0].tags == ["local", "npm"]


def test_load_uses_yarn_when_yarn_lock_present(tmp_path):
    pkg = {"scripts": {"test": "jest"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    (tmp_path / "yarn.lock").write_text("")
    cmds = load(tmp_path)
    assert cmds[0].command == "yarn test"
    assert cmds[0].tags == ["local", "yarn"]


def test_load_yarn_takes_precedence_over_npm(tmp_path):
    pkg = {"scripts": {"start": "node server.js"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    (tmp_path / "yarn.lock").write_text("")
    (tmp_path / "package-lock.json").write_text("{}")
    cmds = load(tmp_path)
    assert cmds[0].command == "yarn start"
    assert cmds[0].tags == ["local", "yarn"]


def test_load_script_key_becomes_name(tmp_path):
    pkg = {"scripts": {"build": "webpack"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    cmds = load(tmp_path)
    assert cmds[0].name == "build"


def test_load_script_value_becomes_description(tmp_path):
    pkg = {"scripts": {"build": "webpack --config webpack.config.js"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    cmds = load(tmp_path)
    assert cmds[0].description == "webpack --config webpack.config.js"


def test_load_multiple_scripts_returns_all(tmp_path):
    pkg = {"scripts": {"build": "webpack", "test": "jest", "lint": "eslint ."}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    cmds = load(tmp_path)
    assert len(cmds) == 3
    names = {c.name for c in cmds}
    assert names == {"build", "test", "lint"}


def test_load_shortcut_is_none(tmp_path):
    pkg = {"scripts": {"build": "webpack"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    cmds = load(tmp_path)
    assert cmds[0].shortcut is None
