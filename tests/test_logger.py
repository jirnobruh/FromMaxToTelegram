"""
Unit tests for session-based logging and size retention quota.
"""
import logging
from pathlib import Path
import time
import pytest
from src.logger import (
    cleanup_logs_directory,
    get_directory_size_bytes,
    setup_logging,
)


def test_directory_size_calculation(tmp_path: Path):
    d = tmp_path / "logs"
    d.mkdir()
    f1 = d / "f1.log"
    f2 = d / "f2.log"
    f1.write_bytes(b"x" * 1000)
    f2.write_bytes(b"y" * 2500)

    assert get_directory_size_bytes(d) == 3500


def test_cleanup_logs_directory_pruning(tmp_path: Path):
    d = tmp_path / "logs"
    d.mkdir()

    # Create 4 log files with different modification times
    files = []
    for i in range(4):
        f = d / f"log_{i}.log"
        f.write_bytes(b"a" * 1000)
        # Set mtime
        t = time.time() - (100 - i * 10)
        os_time = (t, t)
        import os
        os.utime(f, os_time)
        files.append(f)

    # Total size = 4000 bytes. Limit = 2500 bytes, target_ratio = 0.5 (target 1250)
    # Should delete the oldest files until <= 1250 bytes
    deleted = cleanup_logs_directory(d, max_size_bytes=2500, target_ratio=0.5)

    assert len(deleted) >= 2
    assert files[0] in deleted  # Oldest deleted first
    assert files[1] in deleted
    assert get_directory_size_bytes(d) <= 2000


def test_cleanup_keeps_active_file(tmp_path: Path):
    d = tmp_path / "logs"
    d.mkdir()

    old_file = d / "old.log"
    old_file.write_bytes(b"o" * 3000)
    import os
    os.utime(old_file, (time.time() - 500, time.time() - 500))

    active_file = d / "active.log"
    active_file.write_bytes(b"n" * 3000)

    # Max size = 4000. Total = 6000. Target = 3600 (0.9 ratio)
    deleted = cleanup_logs_directory(d, max_size_bytes=4000, current_file=active_file)

    assert old_file in deleted
    assert active_file not in deleted
    assert active_file.exists()


def test_setup_logging_session_file_creation(tmp_path: Path):
    logs_dir = tmp_path / "test_logs"
    session_file = setup_logging(
        logs_dir=logs_dir,
        log_level="DEBUG",
        max_dir_size_mb=10,
        max_file_size_mb=2,
    )

    assert session_file.exists()
    assert session_file.parent.resolve() == logs_dir.resolve()
    assert session_file.name.startswith("session_")
    assert session_file.name.endswith(".log")

    test_logger = logging.getLogger("test_logger")
    test_logger.info("Hello session log file!")

    # Flush handlers
    for h in logging.getLogger().handlers:
        h.flush()

    content = session_file.read_text(encoding="utf-8")
    assert "Hello session log file!" in content
