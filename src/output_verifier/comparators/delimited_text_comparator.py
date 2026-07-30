"""Reusable delimited-text comparator for EnrollmentXO (and similar) files."""

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


def _read_records(path: Path, delimiter: str) -> list[list[str]]:
    records: list[list[str]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle, delimiter=delimiter, quoting=csv.QUOTE_MINIMAL)
        for row in reader:
            records.append(list(row))
    return records


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


def _remove_ignored_fields(
    records: list[list[str]],
    ignored_positions: tuple[int, ...],
) -> list[list[str]]:
    if not ignored_positions:
        return records
    zero_based = {position - 1 for position in ignored_positions}
    return [
        [value for index, value in enumerate(record) if index not in zero_based]
        for record in records
    ]


class DelimitedTextComparator:
    """Compare delimited text files with or without a header row."""

    def compare(
        self,
        expected_path: Path,
        actual_path: Path,
        options: ComparisonOptions,
    ) -> ComparisonResult:
        """Compare two delimited files and return the first differences found."""
        try:
            expected_records = _read_records(expected_path, options.delimiter)
            actual_records = _read_records(actual_path, options.delimiter)
        except csv.Error as error:
            LOGGER.error(
                "Malformed delimited file while comparing %s and %s: %s",
                expected_path,
                actual_path,
                error,
            )
            return ComparisonResult(
                status=VerificationStatus.FAILED,
                issue=f"Delimited text parsing error: {error}",
            )
        except OSError as error:
            LOGGER.error(
                "Unable to read delimited files %s / %s: %s",
                expected_path,
                actual_path,
                error,
            )
            return ComparisonResult(
                status=VerificationStatus.FAILED,
                issue=f"Unable to read delimited file: {error}",
            )

        if options.has_header:
            return self._compare_with_header(expected_records, actual_records, options)
        return self._compare_without_header(expected_records, actual_records, options)

    def _compare_with_header(
        self,
        expected_rows: list[list[str]],
        actual_rows: list[list[str]],
        options: ComparisonOptions,
    ) -> ComparisonResult:
        ignored_columns = options.ignored_columns or options.ignored_csv_columns
        expected_rows = _remove_ignored_columns(expected_rows, ignored_columns, "expected")
        actual_rows = _remove_ignored_columns(actual_rows, ignored_columns, "actual")
        differences: list[ComparisonDifference] = []

        if not expected_rows and not actual_rows:
            return ComparisonResult(status=VerificationStatus.PASSED)

        if not expected_rows or not actual_rows:
            differences.append(
                ComparisonDifference(
                    description=(
                        f"Row count mismatch. Expected: {len(expected_rows)}, "
                        f"Actual: {len(actual_rows)}"
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
                                f"Header column {column_index} mismatch. "
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
                        f"Row count mismatch. Expected: {len(expected_rows)}, "
                        f"Actual: {len(actual_rows)}"
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

            for column_index, (expected_value, actual_value) in enumerate(zip(expected_row, actual_row)):
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

        if differences:
            return ComparisonResult(
                status=VerificationStatus.FAILED,
                issue="CSV content mismatch",
                differences=differences[:MAX_REPORTED_DIFFERENCES],
            )
        return ComparisonResult(status=VerificationStatus.PASSED)

    def _compare_without_header(
        self,
        expected_records: list[list[str]],
        actual_records: list[list[str]],
        options: ComparisonOptions,
    ) -> ComparisonResult:
        ignored_positions = (
            options.ignored_field_positions or options.ignored_mbi_field_positions
        )
        expected_records = _remove_ignored_fields(expected_records, ignored_positions)
        actual_records = _remove_ignored_fields(actual_records, ignored_positions)
        differences: list[ComparisonDifference] = []

        if len(expected_records) != len(actual_records):
            differences.append(
                ComparisonDifference(
                    description=(
                        f"Record count mismatch. Expected: {len(expected_records)}, "
                        f"Actual: {len(actual_records)}"
                    ),
                    expected_value=str(len(expected_records)),
                    actual_value=str(len(actual_records)),
                )
            )

        pair_count = min(len(expected_records), len(actual_records))
        for record_index in range(pair_count):
            if len(differences) >= MAX_REPORTED_DIFFERENCES:
                break
            expected_record = expected_records[record_index]
            actual_record = actual_records[record_index]
            record_number = record_index + 1
            if len(expected_record) != len(actual_record):
                differences.append(
                    ComparisonDifference(
                        description=(
                            f"Record: {record_number}, field count mismatch. "
                            f"Expected: {len(expected_record)}, Actual: {len(actual_record)}"
                        ),
                        expected_value=str(len(expected_record)),
                        actual_value=str(len(actual_record)),
                        location=f"record {record_number}",
                    )
                )
                continue

            for field_index, (expected_value, actual_value) in enumerate(
                zip(expected_record, actual_record), start=1
            ):
                if expected_value != actual_value:
                    differences.append(
                        ComparisonDifference(
                            description=(
                                f"Record: {record_number}, Field: {field_index}, "
                                f"Expected: {_truncate(expected_value)}, "
                                f"Actual: {_truncate(actual_value)}"
                            ),
                            expected_value=expected_value,
                            actual_value=actual_value,
                            location=f"record {record_number} field {field_index}",
                        )
                    )
                    break

        if differences:
            return ComparisonResult(
                status=VerificationStatus.FAILED,
                issue="Delimited text content mismatch",
                differences=differences[:MAX_REPORTED_DIFFERENCES],
            )
        return ComparisonResult(status=VerificationStatus.PASSED)
