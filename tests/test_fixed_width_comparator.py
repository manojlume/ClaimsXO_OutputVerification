"""Tests for FixedWidthComparator."""

from __future__ import annotations

from pathlib import Path

from output_verifier.comparators.fixed_width_comparator import FixedWidthComparator
from output_verifier.constants import VerificationStatus
from output_verifier.models import ComparisonOptions


def _write(path: Path, content: str, newline: str | None = None) -> Path:
    if newline is None:
        path.write_text(content, encoding="utf-8")
    else:
        path.write_bytes(content.replace("\n", newline).encode("utf-8"))
    return path


def test_equal_files(tmp_path: Path) -> None:
    content = "ABCDEFG\nHIJKLMN\n"
    expected = _write(tmp_path / "e.txt", content)
    actual = _write(tmp_path / "a.txt", content)
    result = FixedWidthComparator().compare(expected, actual, ComparisonOptions())
    assert result.status == VerificationStatus.PASSED


def test_crlf_versus_lf(tmp_path: Path) -> None:
    expected = _write(tmp_path / "e.txt", "ABC\nDEF\n", newline="\n")
    actual = _write(tmp_path / "a.txt", "ABC\nDEF\n", newline="\r\n")
    result = FixedWidthComparator().compare(expected, actual, ComparisonOptions())
    assert result.status == VerificationStatus.PASSED


def test_final_newline_only_difference(tmp_path: Path) -> None:
    expected = _write(tmp_path / "e.txt", "ABC\nDEF\n")
    actual = _write(tmp_path / "a.txt", "ABC\nDEF")
    result = FixedWidthComparator().compare(expected, actual, ComparisonOptions())
    assert result.status == VerificationStatus.PASSED


def test_line_count_mismatch(tmp_path: Path) -> None:
    expected = _write(tmp_path / "e.txt", "A\nB\nC\n")
    actual = _write(tmp_path / "a.txt", "A\nB\n")
    result = FixedWidthComparator().compare(expected, actual, ComparisonOptions())
    assert result.status == VerificationStatus.FAILED
    assert "Line count mismatch" in result.differences[0].description


def test_line_length_mismatch(tmp_path: Path) -> None:
    expected = _write(tmp_path / "e.txt", "ABCD\n")
    actual = _write(tmp_path / "a.txt", "ABC\n")
    result = FixedWidthComparator().compare(expected, actual, ComparisonOptions())
    assert result.status == VerificationStatus.FAILED
    assert "length mismatch" in result.differences[0].description


def test_character_mismatch(tmp_path: Path) -> None:
    expected = _write(tmp_path / "e.txt", "POSITIVE\n")
    actual = _write(tmp_path / "a.txt", "NEGATIVE\n")
    result = FixedWidthComparator().compare(expected, actual, ComparisonOptions())
    assert result.status == VerificationStatus.FAILED
    assert "Character" in result.differences[0].description


def test_leading_and_trailing_spaces(tmp_path: Path) -> None:
    expected = _write(tmp_path / "e.txt", " ABC \n")
    actual = _write(tmp_path / "a.txt", "ABC  \n")
    result = FixedWidthComparator().compare(expected, actual, ComparisonOptions())
    assert result.status == VerificationStatus.FAILED


def test_blank_line_preserved(tmp_path: Path) -> None:
    expected = _write(tmp_path / "e.txt", "A\n\nB\n")
    actual = _write(tmp_path / "a.txt", "A\nB\n")
    result = FixedWidthComparator().compare(expected, actual, ComparisonOptions())
    assert result.status == VerificationStatus.FAILED
    assert "Line count mismatch" in result.differences[0].description


def test_record_order_matters(tmp_path: Path) -> None:
    expected = _write(tmp_path / "e.txt", "AAA\nBBB\n")
    actual = _write(tmp_path / "a.txt", "BBB\nAAA\n")
    result = FixedWidthComparator().compare(expected, actual, ComparisonOptions())
    assert result.status == VerificationStatus.FAILED


def test_first_two_differences_only(tmp_path: Path) -> None:
    expected = _write(tmp_path / "e.txt", "A\nB\nC\nD\n")
    actual = _write(tmp_path / "a.txt", "X\nY\nZ\nW\n")
    result = FixedWidthComparator().compare(expected, actual, ComparisonOptions())
    assert result.status == VerificationStatus.FAILED
    assert len(result.differences) == 2


def test_sensitive_context_truncated(tmp_path: Path) -> None:
    expected_line = "P" * 193
    actual_line = "N" + ("P" * 192)
    expected = _write(tmp_path / "e.txt", expected_line + "\n")
    actual = _write(tmp_path / "a.txt", actual_line + "\n")
    result = FixedWidthComparator().compare(expected, actual, ComparisonOptions())
    assert result.status == VerificationStatus.FAILED
    description = result.differences[0].description
    assert "193" not in description or "Character" in description
    assert expected_line not in description


def test_ignored_character_ranges(tmp_path: Path) -> None:
    expected = _write(tmp_path / "e.txt", "ABCDEFGH\n")
    actual = _write(tmp_path / "a.txt", "ABXDEFYH\n")
    result = FixedWidthComparator().compare(
        expected,
        actual,
        ComparisonOptions(ignored_character_ranges=((3, 3), (7, 7))),
    )
    assert result.status == VerificationStatus.PASSED
