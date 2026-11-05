"""Phase 3 regression tests: SQLite backup and manager state."""
import sqlite3

from app.backup import backup


def test_sqlite_backup_round_trip(tmp_path):
    source = tmp_path / "source.db"
    target = tmp_path / "backup.db"
    with sqlite3.connect(source) as db:
        db.execute("CREATE TABLE sample (value TEXT)")
        db.execute("INSERT INTO sample VALUES ('saved')")
    backup(source, target)
    with sqlite3.connect(target) as db:
        assert db.execute("SELECT value FROM sample").fetchone()[0] == "saved"


def test_backup_rotation(tmp_path):
    from app.scheduled_backup import backup_once
    source = tmp_path / "source.db"
    with sqlite3.connect(source) as db:
        db.execute("CREATE TABLE sample (value INTEGER)")
    destination = tmp_path / "backups"
    for _ in range(3):
        backup_once(source, destination, keep=2)
    assert len(list(destination.glob("meshwx-*.db"))) == 2


def test_scheduled_backup_integrity(tmp_path):
    from app.scheduled_backup import backup_once
    source = tmp_path / "original.db"
    with sqlite3.connect(source) as conn:
        conn.execute("CREATE TABLE payload (text TEXT)")
        conn.execute("INSERT INTO payload VALUES ('safe')")
    saved = backup_once(source, tmp_path / "backups")
    with sqlite3.connect(saved) as conn:
        assert conn.execute("PRAGMA quick_check").fetchone()[0] == "ok"
        assert conn.execute("SELECT text FROM payload").fetchone()[0] == "safe"


def test_scheduled_backup_failure_cleans_up(tmp_path):
    import pytest
    from app.scheduled_backup import backup_once
    target = tmp_path / "backups"
    with pytest.raises(FileNotFoundError):
        backup_once(tmp_path / "missing.db", target)
    assert not list(target.glob("meshwx-*.db"))
