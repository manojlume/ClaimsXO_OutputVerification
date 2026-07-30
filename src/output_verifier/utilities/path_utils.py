"""Path helper utilities."""

from __future__ import annotations

from pathlib import Path


def ensure_directory(path: Path) -> Path:
    """Create a directory if it does not exist and return it."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def is_readable_directory(path: Path) -> bool:
    """Return True when the path exists and is a readable directory."""
    return path.is_dir()


def relative_posix(path: Path, root: Path) -> str:
    """Return a relative path using backslash separators for Windows reports."""
    try:
        relative = path.relative_to(root)
    except ValueError:
        return str(path)
    return str(relative)
