import os
import sys
import json
import subprocess

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import hop2


@pytest.fixture
def db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "hop2.db")
    monkeypatch.setattr(hop2, "DB_PATH", db_path)
    monkeypatch.setattr(hop2, "DB_DIR", str(tmp_path))
    hop2.init_db()
    return db_path


def test_add_directory_create_and_update(db, tmp_path, capsys):
    d1 = tmp_path / "a"
    d1.mkdir()
    assert hop2.add_directory("work", str(d1)) == 0
    assert "Created" in capsys.readouterr().out

    d2 = tmp_path / "b"
    d2.mkdir()
    assert hop2.add_directory("work", str(d2)) == 0
    assert "Updated" in capsys.readouterr().out
    assert hop2.get_directory("work", bump=False) == str(d2)


def test_add_directory_rejects_reserved_word(db, tmp_path):
    assert hop2.add_directory("list", str(tmp_path)) == 1


def test_add_directory_rejects_missing_path(db, tmp_path):
    missing = str(tmp_path / "does-not-exist")
    assert hop2.add_directory("ghost", missing) == 1


def test_add_command_create_and_update(db, capsys):
    assert hop2.add_command("gs", ["git", "status"]) == 0
    assert "Created command" in capsys.readouterr().out

    assert hop2.add_command("gs", ["git", "status", "-s"]) == 0
    assert "Updated command" in capsys.readouterr().out
    assert hop2.get_command("gs") == "git status -s"


def test_get_directory_increments_uses_only_when_bumping(db, tmp_path):
    d = tmp_path / "x"
    d.mkdir()
    hop2.add_directory("x", str(d))

    hop2.get_directory("x", bump=False)
    with hop2.get_conn() as conn:
        row = conn.execute("SELECT uses FROM directories WHERE alias='x'").fetchone()
    assert row[0] == 0

    hop2.get_directory("x")
    hop2.get_directory("x")
    with hop2.get_conn() as conn:
        row = conn.execute("SELECT uses FROM directories WHERE alias='x'").fetchone()
    assert row[0] == 2


def test_get_command_increments_uses(db):
    hop2.add_command("cc", ["echo", "hi"])
    hop2.get_command("cc")
    with hop2.get_conn() as conn:
        row = conn.execute("SELECT uses FROM commands WHERE alias='cc'").fetchone()
    assert row[0] == 1


def test_remove_shortcut_dir_cmd_and_missing(db, tmp_path):
    d = tmp_path / "z"
    d.mkdir()
    hop2.add_directory("z", str(d))
    hop2.add_command("cc", ["echo", "hi"])

    assert hop2.remove_shortcut("z") == 0
    assert hop2.remove_shortcut("cc") == 0
    assert hop2.remove_shortcut("nope") == 1


def test_backup_restore_roundtrip_v2(db, tmp_path, monkeypatch):
    d = tmp_path / "proj"
    d.mkdir()
    hop2.add_directory("proj", str(d))
    hop2.add_command("gs", ["git", "status"])

    backup_file = str(tmp_path / "backup.json")
    assert hop2.backup_data(backup_file) == 0

    with open(backup_file) as f:
        payload = json.load(f)
    assert payload["version"] == "2.0"

    # Restore into a fresh database.
    monkeypatch.setattr(hop2, "DB_PATH", str(tmp_path / "hop2_new.db"))
    monkeypatch.setattr("builtins.input", lambda _: "y")

    assert hop2.restore_data(backup_file) == 0
    assert hop2.get_directory("proj", bump=False) == str(d)
    assert hop2.get_command("gs") == "git status"


def test_restore_v1_flat_format(db, tmp_path, monkeypatch):
    flat = {
        "directories": [{"alias": "old", "path": str(tmp_path), "created_at": "t", "uses": 3}],
        "commands": [{"alias": "oc", "command": "echo hi", "created_at": "t", "uses": 1}],
    }
    backup_file = tmp_path / "old_backup.json"
    backup_file.write_text(json.dumps(flat))

    monkeypatch.setattr("builtins.input", lambda _: "y")
    assert hop2.restore_data(str(backup_file)) == 0
    assert hop2.get_directory("old", bump=False) == str(tmp_path)
    assert hop2.get_command("oc") == "echo hi"


def test_backup_overwrite_declined_leaves_file_untouched(db, tmp_path, monkeypatch):
    f = tmp_path / "b.json"
    f.write_text("existing")

    monkeypatch.setattr("builtins.input", lambda _: "n")
    assert hop2.backup_data(str(f)) == 1
    assert f.read_text() == "existing"


def test_no_unicode_crash_on_piped_stdout(tmp_path):
    """Regression test: emoji output must not raise UnicodeEncodeError even
    when stdout is piped and the interpreter starts in a non-UTF-8 encoding
    (as happens by default on Windows)."""
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    script = os.path.join(repo_root, "hop2.py")
    target_dir = tmp_path / "d"
    target_dir.mkdir()

    env = dict(os.environ)
    env["HOP2_DB"] = str(tmp_path / "hop2.db")
    env["PYTHONIOENCODING"] = "cp1252"

    result = subprocess.run(
        [sys.executable, script, "add", "testdir", str(target_dir)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    assert result.returncode == 0
    assert b"UnicodeEncodeError" not in result.stderr
    assert "✅".encode("utf-8") in result.stdout
