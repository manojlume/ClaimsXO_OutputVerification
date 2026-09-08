"""Tests for DelimitedTextComparator and EnrollmentXO verification service."""

from __future__ import annotations

from pathlib import Path

from output_verifier.comparators.delimited_text_comparator import DelimitedTextComparator
from output_verifier.config_loader import build_resolved_config
from output_verifier.constants import ExitCode, VerificationStatus
from output_verifier.models import ComparisonOptions
from output_verifier.verification_service import VerificationService


def _write(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def _touch(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _enrollment_config(tmp_path: Path, expected: Path, actual: Path, verification_type: str):
    data = {
        "solution_type": "EnrollmentXO",
        "tpa_id": verification_type,
        "expected_parent_folder": str(expected),
        "actual_parent_folder": str(actual),
        "report": {
            "output_folder": str(tmp_path / "reports"),
            "base_file_name": "VerificationReport",
            "include_solution_type": True,
            "include_tpa_id": True,
            "include_timestamp": True,
            "timestamp_format": "%Y%m%d%H%M%S",
            "status_colors": {
                "passed": "#C6EFCE",
                "failed": "#FFC7CE",
                "not_verified": "#FFEB9C",
            },
        },
        "logging": {
            "level": "INFO",
            "log_to_console": False,
            "log_to_file": False,
            "output_folder": str(tmp_path / "logs"),
            "max_bytes": 10485760,
            "backup_count": 5,
        },
        "ignore_rules": {
            "EnrollmentXO": {
                "ABG": {"alegeus_mbi_field_positions": [], "report_csv_columns": []},
                "GDI": {"wexhealth_field_positions": [], "report_csv_columns": []},
                "HSAB": {
                    "enrollment_import_field_positions": [],
                    "report_csv_columns": [],
                },
            }
        },
    }
    return build_resolved_config(data)


def test_comma_mbi_equal(tmp_path: Path) -> None:
    content = "A,B,C\nD,E,F\n"
    expected = _write(tmp_path / "e.mbi", content)
    actual = _write(tmp_path / "a.mbi", content)
    result = DelimitedTextComparator().compare(
        expected,
        actual,
        ComparisonOptions(delimiter=",", has_header=False),
    )
    assert result.status == VerificationStatus.PASSED


def test_pipe_trailing_delimiter_difference(tmp_path: Path) -> None:
    expected = _write(tmp_path / "e.txt", "A|B|C\n")
    actual = _write(tmp_path / "a.txt", "A|B|C|\n")
    result = DelimitedTextComparator().compare(
        expected,
        actual,
        ComparisonOptions(delimiter="|", has_header=False, compare_trailing_empty_fields=True),
    )
    assert result.status == VerificationStatus.FAILED
    assert "field count mismatch" in result.differences[0].description


def test_csv_ignored_column(tmp_path: Path) -> None:
    expected = _write(tmp_path / "e.csv", "Id,Timestamp,Value\n1,T1,A\n")
    actual = _write(tmp_path / "a.csv", "Id,Timestamp,Value\n1,T2,A\n")
    result = DelimitedTextComparator().compare(
        expected,
        actual,
        ComparisonOptions(
            delimiter=",",
            has_header=True,
            ignored_columns=("Timestamp",),
        ),
    )
    assert result.status == VerificationStatus.PASSED


def test_first_two_differences_only(tmp_path: Path) -> None:
    expected = _write(tmp_path / "e.txt", "A|1\nB|2\nC|3\n")
    actual = _write(tmp_path / "a.txt", "A|9\nB|8\nC|7\n")
    result = DelimitedTextComparator().compare(
        expected,
        actual,
        ComparisonOptions(delimiter="|", has_header=False),
    )
    assert len(result.differences) == 2


def test_enrollment_abg_passed(tmp_path: Path) -> None:
    expected = tmp_path / "expected"
    actual = tmp_path / "actual"
    content = "A,B,C\n"
    _touch(
        expected / "s1" / "current" / "alegeus" / "Export_111_Cafeteria_XML_20210301_0002.mbi",
        content,
    )
    _touch(
        actual / "s1" / "current" / "alegeus" / "Export_999_Cafeteria_XML_20210301_0002.mbi",
        content,
    )
    rows, exit_code = VerificationService(
        _enrollment_config(tmp_path, expected, actual, "ABG")
    ).run()
    assert exit_code == ExitCode.SUCCESS
    assert any(row.status == VerificationStatus.PASSED for row in rows)


def test_enrollment_gdi_passed(tmp_path: Path) -> None:
    expected = tmp_path / "expected"
    actual = tmp_path / "actual"
    content = "A|B|C\n"
    _touch(expected / "s1" / "current" / "WexHealth" / "GDI_WEXHealth_111.txt", content)
    _touch(actual / "s1" / "current" / "WexHealth" / "GDI_WEXHealth_222.txt", content)
    rows, exit_code = VerificationService(
        _enrollment_config(tmp_path, expected, actual, "GDI")
    ).run()
    assert exit_code == ExitCode.SUCCESS
    assert any(row.status == VerificationStatus.PASSED for row in rows)


def test_enrollment_not_verified_empty(tmp_path: Path) -> None:
    expected = tmp_path / "expected"
    actual = tmp_path / "actual"
    (expected / "s1" / "current" / "alegeus").mkdir(parents=True)
    (actual / "s1" / "current" / "alegeus").mkdir(parents=True)
    rows, exit_code = VerificationService(
        _enrollment_config(tmp_path, expected, actual, "ABG")
    ).run()
    assert exit_code == ExitCode.SUCCESS
    assert rows[0].status == VerificationStatus.NOT_VERIFIED
