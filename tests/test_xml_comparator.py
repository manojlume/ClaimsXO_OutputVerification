"""Tests for the XML comparator."""

from __future__ import annotations

from pathlib import Path

from output_verifier.comparators.xml_comparator import XmlComparator
from output_verifier.constants import VerificationStatus
from output_verifier.models import ComparisonOptions


def _write(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def test_equal_xml(tmp_path: Path) -> None:
    expected = _write(tmp_path / "e.xml", "<Root><Item id='1'>A</Item></Root>")
    actual = _write(tmp_path / "a.xml", "<Root><Item id='1'>A</Item></Root>")
    result = XmlComparator().compare(expected, actual, ComparisonOptions())
    assert result.status == VerificationStatus.PASSED


def test_different_indentation_and_line_endings(tmp_path: Path) -> None:
    expected = _write(tmp_path / "e.xml", "<Root>\n  <Item>A</Item>\n</Root>\n")
    actual = _write(tmp_path / "a.xml", "<Root>\r\n<Item>A</Item>\r\n</Root>\r\n")
    result = XmlComparator().compare(expected, actual, ComparisonOptions())
    assert result.status == VerificationStatus.PASSED


def test_different_attribute_order(tmp_path: Path) -> None:
    expected = _write(tmp_path / "e.xml", "<Root a='1' b='2'/>")
    actual = _write(tmp_path / "a.xml", "<Root b='2' a='1'/>")
    result = XmlComparator().compare(expected, actual, ComparisonOptions())
    assert result.status == VerificationStatus.PASSED


def test_different_element_order(tmp_path: Path) -> None:
    expected = _write(tmp_path / "e.xml", "<Root><A/><B/></Root>")
    actual = _write(tmp_path / "a.xml", "<Root><B/><A/></Root>")
    result = XmlComparator().compare(expected, actual, ComparisonOptions())
    assert result.status == VerificationStatus.FAILED
    assert "Element name mismatch" in result.differences[0].description


def test_different_attribute_value(tmp_path: Path) -> None:
    expected = _write(tmp_path / "e.xml", "<Root id='1'/>")
    actual = _write(tmp_path / "a.xml", "<Root id='2'/>")
    result = XmlComparator().compare(expected, actual, ComparisonOptions())
    assert result.status == VerificationStatus.FAILED
    assert "Attribute value mismatch" in result.differences[0].description


def test_different_text_value(tmp_path: Path) -> None:
    expected = _write(tmp_path / "e.xml", "<Root>Hello</Root>")
    actual = _write(tmp_path / "a.xml", "<Root>World</Root>")
    result = XmlComparator().compare(expected, actual, ComparisonOptions())
    assert result.status == VerificationStatus.FAILED
    assert "Text mismatch" in result.differences[0].description


def test_ignored_attribute_with_default_namespace(tmp_path: Path) -> None:
    expected = _write(
        tmp_path / "e.xml",
        '<Root xmlns="http://example.com" CreatedDateTime="1" FileDateTime="1"><Item>A</Item></Root>',
    )
    actual = _write(
        tmp_path / "a.xml",
        '<Root xmlns="http://example.com" CreatedDateTime="2" FileDateTime="9"><Item>A</Item></Root>',
    )
    result = XmlComparator().compare(
        expected,
        actual,
        ComparisonOptions(
            ignored_xml_paths=(
                "/Root/@CreatedDateTime",
                "/Root/@FileDateTime",
            )
        ),
    )
    assert result.status == VerificationStatus.PASSED


def test_ignored_element(tmp_path: Path) -> None:
    expected = _write(tmp_path / "e.xml", "<Root><Meta>1</Meta><Item>A</Item></Root>")
    actual = _write(tmp_path / "a.xml", "<Root><Meta>2</Meta><Item>A</Item></Root>")
    result = XmlComparator().compare(
        expected,
        actual,
        ComparisonOptions(ignored_xml_paths=("/Root/Meta",)),
    )
    assert result.status == VerificationStatus.PASSED


def test_default_namespace(tmp_path: Path) -> None:
    expected = _write(
        tmp_path / "e.xml",
        '<Root xmlns="http://example.com"><Item>A</Item></Root>',
    )
    actual = _write(
        tmp_path / "a.xml",
        '<Root xmlns="http://example.com"><Item>A</Item></Root>',
    )
    result = XmlComparator().compare(expected, actual, ComparisonOptions())
    assert result.status == VerificationStatus.PASSED


def test_malformed_xml(tmp_path: Path) -> None:
    expected = _write(tmp_path / "e.xml", "<Root><Item>A</Item></Root>")
    actual = _write(tmp_path / "a.xml", "<Root><Item>A</Item>")
    result = XmlComparator().compare(expected, actual, ComparisonOptions())
    assert result.status == VerificationStatus.FAILED
    assert "XML parsing error" in result.issue


def test_first_two_differences_only(tmp_path: Path) -> None:
    expected = _write(
        tmp_path / "e.xml",
        "<Root><A>1</A><B>2</B><C>3</C></Root>",
    )
    actual = _write(
        tmp_path / "a.xml",
        "<Root><A>9</A><B>8</B><C>7</C></Root>",
    )
    result = XmlComparator().compare(expected, actual, ComparisonOptions())
    assert result.status == VerificationStatus.FAILED
    assert len(result.differences) == 2
