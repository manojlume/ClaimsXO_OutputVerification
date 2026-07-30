"""Tests for the CSV comparator."""

from __future__ import annotations

from pathlib import Path

from output_verifier.comparators.csv_comparator import CsvComparator
from output_verifier.constants import VerificationStatus
from output_verifier.models import ComparisonOptions


def _write(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def test_equal_csv(tmp_path: Path) -> None:
    content = "Name,ClaimNumber\nAlice,ABC123\n"
    expected = _write(tmp_path / "e.csv", content)
    actual = _write(tmp_path / "a.csv", content)
    result = CsvComparator().compare(expected, actual, ComparisonOptions())
    assert result.status == VerificationStatus.PASSED


def test_header_mismatch(tmp_path: Path) -> None:
    expected = _write(tmp_path / "e.csv", "EmployeeSSN,ClaimNumber\n1,A\n")
    actual = _write(tmp_path / "a.csv", "EmployeeId,ClaimNumber\n1,A\n")
    result = CsvComparator().compare(expected, actual, ComparisonOptions())
    assert result.status == VerificationStatus.FAILED
    assert "Header column 1 mismatch" in result.differences[0].description


def test_header_order_mismatch(tmp_path: Path) -> None:
    expected = _write(tmp_path / "e.csv", "A,B\n1,2\n")
    actual = _write(tmp_path / "a.csv", "B,A\n2,1\n")
    result = CsvComparator().compare(expected, actual, ComparisonOptions())
    assert result.status == VerificationStatus.FAILED


def test_row_count_mismatch(tmp_path: Path) -> None:
    expected = _write(tmp_path / "e.csv", "A\n1\n2\n")
    actual = _write(tmp_path / "a.csv", "A\n1\n")
    result = CsvComparator().compare(expected, actual, ComparisonOptions())
    assert "Row count mismatch" in result.differences[0].description


def test_row_order_mismatch(tmp_path: Path) -> None:
    expected = _write(tmp_path / "e.csv", "A\n1\n2\n")
    actual = _write(tmp_path / "a.csv", "A\n2\n1\n")
    result = CsvComparator().compare(expected, actual, ComparisonOptions())
    assert result.status == VerificationStatus.FAILED


def test_field_mismatch(tmp_path: Path) -> None:
    expected = _write(tmp_path / "e.csv", "ClaimNumber\nABC123\n")
    actual = _write(tmp_path / "a.csv", "ClaimNumber\nABC124\n")
    result = CsvComparator().compare(expected, actual, ComparisonOptions())
    assert "Row: 2, Column: ClaimNumber" in result.differences[0].description


def test_comma_inside_quoted_field(tmp_path: Path) -> None:
    expected = _write(tmp_path / "e.csv", 'Name,City\n"Smith, John",Dallas\n')
    actual = _write(tmp_path / "a.csv", 'Name,City\n"Smith, John",Dallas\n')
    result = CsvComparator().compare(expected, actual, ComparisonOptions())
    assert result.status == VerificationStatus.PASSED


def test_escaped_quote(tmp_path: Path) -> None:
    expected = _write(tmp_path / "e.csv", 'Name\n"He said ""Hi"""\n')
    actual = _write(tmp_path / "a.csv", 'Name\n"He said ""Hi"""\n')
    result = CsvComparator().compare(expected, actual, ComparisonOptions())
    assert result.status == VerificationStatus.PASSED


def test_leading_and_trailing_space_difference(tmp_path: Path) -> None:
    expected = _write(tmp_path / "e.csv", "A\n value \n")
    actual = _write(tmp_path / "a.csv", "A\nvalue\n")
    result = CsvComparator().compare(expected, actual, ComparisonOptions())
    assert result.status == VerificationStatus.FAILED


def test_ignored_column(tmp_path: Path) -> None:
    expected = _write(tmp_path / "e.csv", "Id,Timestamp,Value\n1,T1,A\n")
    actual = _write(tmp_path / "a.csv", "Id,Timestamp,Value\n1,T2,A\n")
    result = CsvComparator().compare(
        expected,
        actual,
        ComparisonOptions(ignored_csv_columns=("Timestamp",)),
    )
    assert result.status == VerificationStatus.PASSED


def test_first_two_differences_only(tmp_path: Path) -> None:
    expected = _write(tmp_path / "e.csv", "A,B,C\n1,2,3\n4,5,6\n")
    actual = _write(tmp_path / "a.csv", "A,B,C\n9,8,7\nx,y,z\n")
    result = CsvComparator().compare(expected, actual, ComparisonOptions())
    assert len(result.differences) == 2
