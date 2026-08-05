"""Reusable fixed-width text comparator."""

from __future__ import annotations

import logging
from pathlib import Path

from output_verifier.constants import MAX_LOGGED_VALUE_LENGTH, MAX_REPORTED_DIFFERENCES, VerificationStatus
from output_verifier.models import (
    ComparisonDifference,
    ComparisonOptions,
    ComparisonResult,
)

LOGGER = logging.getLogger(__name__)

_LONG_VALUE_THRESHOLD = 40
_CONTEXT_SNIPPET = 8


def _truncate(value: str) -> str:
    if len(value) <= MAX_LOGGED_VALUE_LENGTH:
        return value
    return value[:MAX_LOGGED_VALUE_LENGTH] + "...(truncated)"


def _safe_snippet(value: str, start: int, end: int) -> str:
    """Return a short snippet around a mismatch without exposing full records."""
    snippet = value[start:end]
    if len(snippet) > _CONTEXT_SNIPPET:
        snippet = snippet[:_CONTEXT_SNIPPET]
    return _truncate(snippet)


def _read_lines(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8-sig")
    # splitlines() normalizes CRLF/LF and drops a final trailing newline only.
    return text.splitlines()


def _mask_ignored_positions(line: str, ranges: tuple[tuple[int, int], ...]) -> str:
    if not ranges:
        return line
    chars = list(line)
    for start, end in ranges:
        for position in range(start, end + 1):
            index = position - 1
            if 0 <= index < len(chars):
                chars[index] = " "
    return "".join(chars)


def _first_diff_span(expected: str, actual: str) -> tuple[int, int]:
    """Return one-based inclusive start/end of the first continuous mismatch span."""
    limit = min(len(expected), len(actual))
    start = 0
    while start < limit and expected[start] == actual[start]:
        start += 1
    if start >= limit:
        # Length mismatch beyond shared prefix.
        return start + 1, max(len(expected), len(actual))
    end = start
    while end < limit and expected[end] != actual[end]:
        end += 1
    return start + 1, end


class FixedWidthComparator:
    """Compare fixed-width text files line-by-line with exact character semantics."""

    def compare(
        self,
        expected_path: Path,
        actual_path: Path,
        options: ComparisonOptions,
    ) -> ComparisonResult:
        """Compare two fixed-width text files and return up to two differences."""
        try:
            expected_lines = _read_lines(expected_path)
            actual_lines = _read_lines(actual_path)
        except OSError as error:
            LOGGER.error(
                "Unable to read fixed-width files %s / %s: %s",
                expected_path,
                actual_path,
                error,
            )
            return ComparisonResult(
                status=VerificationStatus.FAILED,
                issue=f"Unable to read MDC file: {error}",
            )
        except UnicodeError as error:
            LOGGER.error(
                "Unable to decode fixed-width files %s / %s: %s",
                expected_path,
                actual_path,
                error,
            )
            return ComparisonResult(
                status=VerificationStatus.FAILED,
                issue=f"Unable to read MDC file: {error}",
            )

        differences: list[ComparisonDifference] = []
        if len(expected_lines) != len(actual_lines):
            differences.append(
                ComparisonDifference(
                    description=(
                        f"Line count mismatch. Expected: {len(expected_lines)}, "
                        f"Actual: {len(actual_lines)}"
                    ),
                    expected_value=str(len(expected_lines)),
                    actual_value=str(len(actual_lines)),
                )
            )

        shared = min(len(expected_lines), len(actual_lines))
        ranges = options.ignored_character_ranges
        for index in range(shared):
            if len(differences) >= MAX_REPORTED_DIFFERENCES:
                break

            line_number = index + 1
            expected_raw = expected_lines[index]
            actual_raw = actual_lines[index]
            expected = _mask_ignored_positions(expected_raw, ranges)
            actual = _mask_ignored_positions(actual_raw, ranges)

            if expected == actual:
                continue

            if len(expected) != len(actual):
                differences.append(
                    ComparisonDifference(
                        description=(
                            f"Line: {line_number}, length mismatch. "
                            f"Expected: {len(expected)}, Actual: {len(actual)}"
                        ),
                        expected_value=str(len(expected)),
                        actual_value=str(len(actual)),
                        location=f"line {line_number}",
                    )
                )
                continue

            start, end = _first_diff_span(expected, actual)
            expected_snippet = _safe_snippet(expected, start - 1, end)
            actual_snippet = _safe_snippet(actual, start - 1, end)
            if end > start:
                description = (
                    f"Line: {line_number}, Character Range: {start}-{end}, "
                    f'Expected: "{expected_snippet}", Actual: "{actual_snippet}"'
                )
            else:
                description = (
                    f"Line: {line_number}, Character Position: {start}, "
                    f'Expected: "{expected_snippet}", Actual: "{actual_snippet}"'
                )
            if len(expected_raw) >= _LONG_VALUE_THRESHOLD:
                description += " (context truncated)"

            differences.append(
                ComparisonDifference(
                    description=description,
                    expected_value=expected_snippet,
                    actual_value=actual_snippet,
                    location=f"line {line_number} position {start}",
                )
            )

        if differences:
            LOGGER.info(
                "Fixed-width mismatch for %s vs %s (%s differences reported)",
                expected_path.name,
                actual_path.name,
                len(differences),
            )
            return ComparisonResult(
                status=VerificationStatus.FAILED,
                issue="MDC content mismatch",
                differences=differences[:MAX_REPORTED_DIFFERENCES],
            )

        LOGGER.debug(
            "Fixed-width match for %s vs %s",
            expected_path.name,
            actual_path.name,
        )
        return ComparisonResult(status=VerificationStatus.PASSED)
