from pathlib import Path
from bashmage.context.node import detect


def test_detect_returns_false_when_no_package_json(tmp_path):
    assert detect(tmp_path) is False


def test_detect_returns_true_when_package_json_exists(tmp_path):
    (tmp_path / "package.json").write_text("{}")
    assert detect(tmp_path) is True
