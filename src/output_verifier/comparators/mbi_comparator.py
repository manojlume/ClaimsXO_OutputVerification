"""MBI pipe-delimited file comparator."""

from __future__ import annotations

import csv
import logging
from pathlib import Path

from output_verifier.constants import (
    MAX_LOGGED_VALUE_LENGTH,
    MAX_REPORTED_DIFFERENCES,
    MBI_DELIMITER,
    VerificationStatus,
)
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


def _read_mbi_records(path: Path) -> list[list[str]]:
    """
    Read MBI records using the csv module with pipe delimiter.

    Trailing delimiters are preserved as empty fields. Blank lines are kept
    as a single empty-field record so they are not silently discarded.
    """
    records: list[list[str]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(
            handle,
            delimiter=MBI_DELIMITER,
            quoting=csv.QUOTE_MINIMAL,
        )
        for row in reader:
            records.append(list(row))
    return records


def _remove_ignored_fields(
    records: list[list[str]],
    ignored_positions: tuple[int, ...],
) -> list[list[str]]:
    if not ignored_positions:
        return records

    zero_based = {position - 1 for position in ignored_positions}

    filtered: list[list[str]] = []
    for record in records:
        filtered.append(
            [value for index, value in enumerate(record) if index not in zero_based]
        )
    return filtered


class MbiComparator:
    """Compare MBI pipe-delimited files by positional records and fields."""

    def compare(
        self,
        expected_path: Path,
        actual_path: Path,
        options: ComparisonOptions,
    ) -> ComparisonResult:
        """Compare two MBI files and return the first differences found."""
        try:
            expected_records = _read_mbi_records(expected_path)
            actual_records = _read_mbi_records(actual_path)
        except csv.Error as error:
            LOGGER.error("Malformed MBI while comparing %s and %s: %s", expected_path, actual_path, error)
            return ComparisonResult(
                status=VerificationStatus.FAILED,
                issue=f"MBI parsing error: {error}",
            )
        except OSError as error:
            LOGGER.error("Unable to read MBI files %s / %s: %s", expected_path, actual_path, error)
            return ComparisonResult(
                status=VerificationStatus.FAILED,
                issue=f"Unable to read MBI file: {error}",
            )

        expected_records = _remove_ignored_fields(
            expected_records, options.ignored_mbi_field_positions
        )
        actual_records = _remove_ignored_fields(
            actual_records, options.ignored_mbi_field_positions
        )

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

            if len(differences) >= MAX_REPORTED_DIFFERENCES:
                break

        if differences:
            LOGGER.info(
                "MBI mismatch for %s vs %s (%s differences reported)",
                expected_path.name,
                actual_path.name,
                len(differences),
            )
            return ComparisonResult(
                status=VerificationStatus.FAILED,
                issue="MBI content mismatch",
                differences=differences[:MAX_REPORTED_DIFFERENCES],
            )

        LOGGER.debug("MBI match for %s vs %s", expected_path.name, actual_path.name)
        return ComparisonResult(status=VerificationStatus.PASSED)
