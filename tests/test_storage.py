import pytest
from bashmage.storage import Command


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
