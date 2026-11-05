"""Scheduled SQLite backups for MeshWX.

Configure MESHWX_BACKUP_DB and MESHWX_BACKUP_DIR. The database is copied
using SQLite's online backup API, then old backups are pruned. No restore is
attempted while MeshWX is running.
"""
from __future__ import annotations

import asyncio
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .backup import backup

logger = logging.getLogger("mesh_wx.backup")


def backup_once(db_path: Path, directory: Path, keep: int = 7) -> Path:
    if not 1 <= keep <= 365:
        raise ValueError("keep must be between 1 and 365")
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / ("meshwx-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f") + ".db")
    try:
        backup(db_path, destination)
        with sqlite3.connect(destination) as connection:
            result = connection.execute("PRAGMA quick_check").fetchone()[0]
        if result != "ok":
            raise RuntimeError("SQLite backup integrity check failed")
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    for stale in sorted(directory.glob("meshwx-*.db"), reverse=True)[keep:]:
        stale.unlink()
    return destination


async def daily_backup_loop(db_path: Path, directory: Path, keep: int = 7) -> None:
    while True:
        try:
            saved = await asyncio.to_thread(backup_once, db_path, directory, keep)
            logger.info("database backup saved: %s", saved)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("automatic database backup failed")
        await asyncio.sleep(24 * 60 * 60)
