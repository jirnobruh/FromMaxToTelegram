"""
Structured session-based logging with directory size retention.
"""
from datetime import datetime
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys
from typing import Optional

DEFAULT_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


def get_directory_size_bytes(directory: Path) -> int:
    """Calculates total size of all files in directory in bytes."""
    if not directory.exists():
        return 0
    total = 0
    for entry in directory.iterdir():
        if entry.is_file():
            try:
                total += entry.stat().st_size
            except OSError:
                pass
    return total


def cleanup_logs_directory(
    directory: Path,
    max_size_bytes: int,
    current_file: Optional[Path] = None,
    target_ratio: float = 0.9,
) -> list[Path]:
    """
    Deletes oldest log files if total size exceeds max_size_bytes until size <= max_size_bytes * target_ratio.
    Never deletes current_file unless it is the only file and exceeds max_size_bytes on its own.
    Returns list of deleted file paths.
    """
    if not directory.exists():
        return []

    total_size = get_directory_size_bytes(directory)
    if total_size <= max_size_bytes:
        return []

    target_size = int(max_size_bytes * target_ratio)
    deleted: list[Path] = []

    # Get all log files sorted by modification time (oldest first)
    log_files = []
    for f in directory.iterdir():
        if f.is_file() and (".log" in f.name or f.suffix == ".log"):
            try:
                log_files.append((f.stat().st_mtime, f.stat().st_size, f))
            except OSError:
                pass

    log_files.sort(key=lambda x: x[0])  # oldest mtime first

    # Delete oldest files (excluding current_file if possible)
    for mtime, fsize, file_path in log_files:
        if total_size <= target_size:
            break
        if current_file and file_path.resolve() == current_file.resolve():
            continue

        try:
            file_path.unlink()
            deleted.append(file_path)
            total_size -= fsize
        except OSError:
            pass

    return deleted


class SessionRotatingFileHandler(RotatingFileHandler):
    """
    Rotating file handler that enforces maximum total directory size after each rotation.
    """

    def __init__(
        self,
        filename: Path | str,
        max_bytes: int,
        backup_count: int,
        logs_dir: Path,
        max_dir_size_bytes: int,
        encoding: str = "utf-8",
    ):
        super().__init__(
            filename=str(filename),
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding=encoding,
        )
        self.logs_dir = Path(logs_dir)
        self.max_dir_size_bytes = max_dir_size_bytes
        self.current_file = Path(filename)

    def doRollover(self) -> None:
        super().doRollover()
        # Enforce directory retention quota
        cleanup_logs_directory(
            directory=self.logs_dir,
            max_size_bytes=self.max_dir_size_bytes,
            current_file=self.current_file,
        )


def setup_logging(
    logs_dir: str | Path = "logs",
    log_level: str = "INFO",
    max_dir_size_mb: int = 1024,
    max_file_size_mb: int = 100,
    log_format: str = DEFAULT_FORMAT,
) -> Path:
    """
    Configures root logger with:
    1. StreamHandler for terminal output (stdout).
    2. Session-based RotatingFileHandler in logs_dir.
    3. Directory-level quota cleanup (<= max_dir_size_mb).
    """
    logs_path = Path(logs_dir)
    logs_path.mkdir(parents=True, exist_ok=True)

    max_dir_size_bytes = max_dir_size_mb * 1024 * 1024
    max_file_size_bytes = max_file_size_mb * 1024 * 1024

    # Run cleanup of previously accumulated logs before opening a new file
    cleanup_logs_directory(logs_path, max_dir_size_bytes)

    # Generate unique session filename with timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    session_log_file = logs_path / f"session_{timestamp}.log"

    root_logger = logging.getLogger()
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    root_logger.setLevel(numeric_level)

    # Remove existing handlers to avoid duplicates
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    formatter = logging.Formatter(log_format)

    # 1. Terminal stdout handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # 2. File handler
    file_handler = SessionRotatingFileHandler(
        filename=session_log_file,
        max_bytes=max_file_size_bytes,
        backup_count=100,
        logs_dir=logs_path,
        max_dir_size_bytes=max_dir_size_bytes,
        encoding="utf-8",
    )
    file_handler.setLevel(numeric_level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # 3. Uncaught exceptions hook
    def uncaught_exception_handler(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        root_logger.critical(
            "Uncaught exception:",
            exc_info=(exc_type, exc_value, exc_traceback),
        )

    sys.excepthook = uncaught_exception_handler

    root_logger.info(f"Logging initialized. Session log file: {session_log_file.resolve()}")
    return session_log_file
