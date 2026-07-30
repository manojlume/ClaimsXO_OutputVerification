"""Tests for the MBI comparator."""

from __future__ import annotations

from pathlib import Path

from output_verifier.comparators.mbi_comparator import MbiComparator
from output_verifier.constants import VerificationStatus
from output_verifier.models import ComparisonOptions


def _write(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def test_equal_mbi(tmp_path: Path) -> None:
    content = "A|B|C\nD|E|F\n"
    expected = _write(tmp_path / "e.mbi", content)
    actual = _write(tmp_path / "a.mbi", content)
    result = MbiComparator().compare(expected, actual, ComparisonOptions())
    assert result.status == VerificationStatus.PASSED


def test_record_count_mismatch(tmp_path: Path) -> None:
    expected = _write(tmp_path / "e.mbi", "A|B\nC|D\n")
    actual = _write(tmp_path / "a.mbi", "A|B\n")
    result = MbiComparator().compare(expected, actual, ComparisonOptions())
    assert "Record count mismatch" in result.differences[0].description


def test_record_order_mismatch(tmp_path: Path) -> None:
    expected = _write(tmp_path / "e.mbi", "A|B\nC|D\n")
    actual = _write(tmp_path / "a.mbi", "C|D\nA|B\n")
    result = MbiComparator().compare(expected, actual, ComparisonOptions())
    assert result.status == VerificationStatus.FAILED


def test_field_mismatch(tmp_path: Path) -> None:
    expected = _write(tmp_path / "e.mbi", "A|APPROVED|C\n")
    actual = _write(tmp_path / "a.mbi", "A|DENIED|C\n")
    result = MbiComparator().compare(expected, actual, ComparisonOptions())
    assert "Record: 1, Field: 2" in result.differences[0].description


def test_field_count_mismatch(tmp_path: Path) -> None:
    expected = _write(tmp_path / "e.mbi", "A|B|C\n")
    actual = _write(tmp_path / "a.mbi", "A|B\n")
    result = MbiComparator().compare(expected, actual, ComparisonOptions())
    assert "field count mismatch" in result.differences[0].description


def test_empty_field_using_double_pipe(tmp_path: Path) -> None:
    expected = _write(tmp_path / "e.mbi", "A||C\n")
    actual = _write(tmp_path / "a.mbi", "A||C\n")
    result = MbiComparator().compare(expected, actual, ComparisonOptions())
    assert result.status == VerificationStatus.PASSED


def test_trailing_delimiter_difference(tmp_path: Path) -> None:
    expected = _write(tmp_path / "e.mbi", "A|B|C\n")
    actual = _write(tmp_path / "a.mbi", "A|B|C|\n")
    result = MbiComparator().compare(expected, actual, ComparisonOptions())
    assert result.status == VerificationStatus.FAILED
    assert "field count mismatch" in result.differences[0].description


def test_leading_and_trailing_space_difference(tmp_path: Path) -> None:
    expected = _write(tmp_path / "e.mbi", " A |B| C \n")
    actual = _write(tmp_path / "a.mbi", "A|B|C\n")
    result = MbiComparator().compare(expected, actual, ComparisonOptions())
    assert result.status == VerificationStatus.FAILED


def test_ignored_field_position(tmp_path: Path) -> None:
    expected = _write(tmp_path / "e.mbi", "A|IGNORE1|C\n")
    actual = _write(tmp_path / "a.mbi", "A|IGNORE2|C\n")
    result = MbiComparator().compare(
        expected,
        actual,
        ComparisonOptions(ignored_mbi_field_positions=(2,)),
    )
    assert result.status == VerificationStatus.PASSED


def test_duplicate_records_by_position(tmp_path: Path) -> None:
    expected = _write(tmp_path / "e.mbi", "A|B\nA|B\n")
    actual = _write(tmp_path / "a.mbi", "A|B\nA|B\n")
    result = MbiComparator().compare(expected, actual, ComparisonOptions())
    assert result.status == VerificationStatus.PASSED


def test_first_two_differences_only(tmp_path: Path) -> None:
    expected = _write(tmp_path / "e.mbi", "A|1\nB|2\nC|3\n")
    actual = _write(tmp_path / "a.mbi", "A|9\nB|8\nC|7\n")
    result = MbiComparator().compare(expected, actual, ComparisonOptions())
    assert len(result.differences) == 2
