"""CSV file comparator using the standard csv module."""

from __future__ import annotations

import csv
import logging
from pathlib import Path

from output_verifier.constants import MAX_LOGGED_VALUE_LENGTH, MAX_REPORTED_DIFFERENCES, VerificationStatus
from output_verifier.models import (
    ComparisonDifference,
    ComparisonOptions,
    ComparisonResult,
)

LOGGER = logging.getLogger(__name__)


def _truncate(value: str) -> str:
    if len(value) <= MAX_LOGGED_VALUE_LENGTH:
        return value
    return value[:MAX_LOGGED_VALUE_LENGTH] + "...(truncated)"


def _read_csv_rows(path: Path) -> list[list[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        return [list(row) for row in reader]


def _remove_ignored_columns(
    rows: list[list[str]],
    ignored_columns: tuple[str, ...],
    side: str,
) -> list[list[str]]:
    if not rows or not ignored_columns:
        return rows

    header = rows[0]
    indexes_to_remove: list[int] = []
    for column_name in ignored_columns:
        if column_name not in header:
            LOGGER.warning(
                "Configured ignored CSV column %r not found in %s header.",
                column_name,
                side,
            )
            continue
        indexes_to_remove.append(header.index(column_name))

    if not indexes_to_remove:
        return rows

    remove_set = set(indexes_to_remove)

    def filter_row(row: list[str]) -> list[str]:
        return [value for index, value in enumerate(row) if index not in remove_set]

    return [filter_row(row) for row in rows]


class CsvComparator:
    """Compare CSV files by header and positional row values."""

    def compare(
        self,
        expected_path: Path,
        actual_path: Path,
        options: ComparisonOptions,
    ) -> ComparisonResult:
        """Compare two CSV files and return the first differences found."""
        try:
            expected_rows = _read_csv_rows(expected_path)
            actual_rows = _read_csv_rows(actual_path)
        except csv.Error as error:
            LOGGER.error("Malformed CSV while comparing %s and %s: %s", expected_path, actual_path, error)
            return ComparisonResult(
                status=VerificationStatus.FAILED,
                issue=f"CSV parsing error: {error}",
            )
        except OSError as error:
            LOGGER.error("Unable to read CSV files %s / %s: %s", expected_path, actual_path, error)
            return ComparisonResult(
                status=VerificationStatus.FAILED,
                issue=f"Unable to read CSV file: {error}",
            )

        expected_rows = _remove_ignored_columns(
            expected_rows, options.ignored_csv_columns, "expected"
        )
        actual_rows = _remove_ignored_columns(
            actual_rows, options.ignored_csv_columns, "actual"
        )

        differences: list[ComparisonDifference] = []

        if not expected_rows and not actual_rows:
            return ComparisonResult(status=VerificationStatus.PASSED)

        if not expected_rows or not actual_rows:
            differences.append(
                ComparisonDifference(
                    description=(
                        f"Row count mismatch. Expected: {len(expected_rows)}, Actual: {len(actual_rows)}"
                    ),
                    expected_value=str(len(expected_rows)),
                    actual_value=str(len(actual_rows)),
                )
            )
            return ComparisonResult(
                status=VerificationStatus.FAILED,
                issue="CSV content mismatch",
                differences=differences,
            )

        expected_header = expected_rows[0]
        actual_header = actual_rows[0]

        if len(expected_header) != len(actual_header):
            differences.append(
                ComparisonDifference(
                    description=(
                        f"Header column count mismatch. Expected: {len(expected_header)}, "
                        f"Actual: {len(actual_header)}"
                    ),
                    expected_value=str(len(expected_header)),
                    actual_value=str(len(actual_header)),
                    location="row 1",
                )
            )
        else:
            for column_index, (expected_name, actual_name) in enumerate(
                zip(expected_header, actual_header), start=1
            ):
                if expected_name != actual_name:
                    differences.append(
                        ComparisonDifference(
                            description=(
                                f"Header column {column_index} mismatch, "
                                f"Expected: {expected_name}, Actual: {actual_name}"
                            ),
                            expected_value=expected_name,
                            actual_value=actual_name,
                            location=f"row 1 column {column_index}",
                        )
                    )
                    if len(differences) >= MAX_REPORTED_DIFFERENCES:
                        break

        if len(differences) >= MAX_REPORTED_DIFFERENCES:
            return ComparisonResult(
                status=VerificationStatus.FAILED,
                issue="CSV content mismatch",
                differences=differences[:MAX_REPORTED_DIFFERENCES],
            )

        if len(expected_rows) != len(actual_rows):
            differences.append(
                ComparisonDifference(
                    description=(
                        f"Row count mismatch. Expected: {len(expected_rows)}, Actual: {len(actual_rows)}"
                    ),
                    expected_value=str(len(expected_rows)),
                    actual_value=str(len(actual_rows)),
                )
            )
            if len(differences) >= MAX_REPORTED_DIFFERENCES:
                return ComparisonResult(
                    status=VerificationStatus.FAILED,
                    issue="CSV content mismatch",
                    differences=differences[:MAX_REPORTED_DIFFERENCES],
                )

        pair_count = min(len(expected_rows), len(actual_rows))
        # Skip header row for value comparison when both have headers.
        for row_index in range(1, pair_count):
            if len(differences) >= MAX_REPORTED_DIFFERENCES:
                break
            expected_row = expected_rows[row_index]
            actual_row = actual_rows[row_index]
            excel_row_number = row_index + 1

            if len(expected_row) != len(actual_row):
                differences.append(
                    ComparisonDifference(
                        description=(
                            f"Row: {excel_row_number}, column count mismatch. "
                            f"Expected: {len(expected_row)}, Actual: {len(actual_row)}"
                        ),
                        expected_value=str(len(expected_row)),
                        actual_value=str(len(actual_row)),
                        location=f"row {excel_row_number}",
                    )
                )
                continue

            for column_index, (expected_value, actual_value) in enumerate(
                zip(expected_row, actual_row)
            ):
                if expected_value != actual_value:
                    column_name = (
                        expected_header[column_index]
                        if column_index < len(expected_header)
                        else str(column_index + 1)
                    )
                    differences.append(
                        ComparisonDifference(
                            description=(
                                f"Row: {excel_row_number}, Column: {column_name}, "
                                f"Expected: {_truncate(expected_value)}, "
                                f"Actual: {_truncate(actual_value)}"
                            ),
                            expected_value=expected_value,
                            actual_value=actual_value,
                            location=f"row {excel_row_number} column {column_name}",
                        )
                    )
                    break
            if len(differences) >= MAX_REPORTED_DIFFERENCES:
                break

        if differences:
            LOGGER.info(
                "CSV mismatch for %s vs %s (%s differences reported)",
                expected_path.name,
                actual_path.name,
                len(differences),
            )
            return ComparisonResult(
                status=VerificationStatus.FAILED,
                issue="CSV content mismatch",
                differences=differences[:MAX_REPORTED_DIFFERENCES],
            )

        LOGGER.debug("CSV match for %s vs %s", expected_path.name, actual_path.name)
        return ComparisonResult(status=VerificationStatus.PASSED)
