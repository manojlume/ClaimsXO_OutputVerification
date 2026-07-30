"""Common comparator interface."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from output_verifier.models import ComparisonOptions, ComparisonResult


class FileComparator(Protocol):
    """Protocol for format-specific file comparators."""

    def compare(
        self,
        expected_path: Path,
        actual_path: Path,
        options: ComparisonOptions,
    ) -> ComparisonResult:
        """Compare expected and actual files and return a comparison result."""
        ...
