"""Tests for verification service orchestration and exit codes."""

from __future__ import annotations

from pathlib import Path

from output_verifier.config_loader import build_resolved_config
from output_verifier.constants import ExitCode, VerificationStatus
from output_verifier.verification_service import VerificationService


def _touch(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _config(tmp_path: Path, expected: Path, actual: Path, verification_type: str = "GDI"):
    data = {
        "solution_type": "ClaimsXO",
        "tpa_id": verification_type,
        "expected_parent_folder": str(expected),
        "actual_parent_folder": str(actual),
        "report": {
            "output_folder": str(tmp_path / "reports"),
            "base_file_name": "VerificationReport",
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
            "GDI": {
                "lh1_xml_paths": [],
                "manual_csv_columns": [],
                "patient_manual_csv_columns": [],
                "mbi_field_positions": [],
            },
            "HSAB": {"wex_xml_paths": []},
        },
    }
    return build_resolved_config(data)


def test_passed_result(tmp_path: Path) -> None:
    expected = tmp_path / "expected"
    actual = tmp_path / "actual"
    xml = "<Root><Item>A</Item></Root>"
    _touch(expected / "s1" / "current" / "LH1" / "GDI_LH1_20260730110000.xml", xml)
    _touch(actual / "s1" / "current" / "LH1" / "GDI_LH1_20260730120000.xml", xml)

    rows, exit_code = VerificationService(_config(tmp_path, expected, actual)).run()
    assert exit_code == ExitCode.SUCCESS
    assert any(row.status == VerificationStatus.PASSED for row in rows)


def test_failed_content_mismatch(tmp_path: Path) -> None:
    expected = tmp_path / "expected"
    actual = tmp_path / "actual"
    _touch(expected / "s1" / "current" / "LH1" / "GDI_LH1_20260730110000.xml", "<Root>A</Root>")
    _touch(actual / "s1" / "current" / "LH1" / "GDI_LH1_20260730120000.xml", "<Root>B</Root>")

    rows, exit_code = VerificationService(_config(tmp_path, expected, actual)).run()
    assert exit_code == ExitCode.COMPARISON_FAILURE
    assert any(row.status == VerificationStatus.FAILED for row in rows)


def test_not_verified_empty(tmp_path: Path) -> None:
    expected = tmp_path / "expected"
    actual = tmp_path / "actual"
    (expected / "s1" / "current" / "LH1").mkdir(parents=True)
    (actual / "s1" / "current" / "LH1").mkdir(parents=True)

    rows, exit_code = VerificationService(_config(tmp_path, expected, actual)).run()
    assert exit_code == ExitCode.SUCCESS
    assert rows[0].status == VerificationStatus.NOT_VERIFIED


def test_expected_file_missing(tmp_path: Path) -> None:
    expected = tmp_path / "expected"
    actual = tmp_path / "actual"
    (expected / "s1" / "current" / "LH1").mkdir(parents=True)
    _touch(
        actual / "s1" / "current" / "LH1" / "GDI_LH1_20260730120000.xml",
        "<Root/>",
    )

    rows, exit_code = VerificationService(_config(tmp_path, expected, actual)).run()
    assert exit_code == ExitCode.COMPARISON_FAILURE
    assert any(row.issue == "Unexpected actual file" for row in rows)


def test_unexpected_file(tmp_path: Path) -> None:
    expected = tmp_path / "expected"
    actual = tmp_path / "actual"
    _touch(expected / "s1" / "current" / "LH1" / "GDI_LH1_20260730110000.xml", "<Root/>")
    _touch(actual / "s1" / "current" / "LH1" / "GDI_LH1_20260730120000.xml", "<Root/>")
    _touch(actual / "s1" / "current" / "LH1" / "GDI_LH1_20260730130000.xml", "<Root/>")

    rows, exit_code = VerificationService(_config(tmp_path, expected, actual)).run()
    assert exit_code == ExitCode.COMPARISON_FAILURE
    assert any("File count mismatch" in row.issue for row in rows)
    assert any(row.issue == "Unexpected actual file" for row in rows)


def test_expected_only_scenario(tmp_path: Path) -> None:
    expected = tmp_path / "expected"
    actual = tmp_path / "actual"
    actual.mkdir()
    _touch(expected / "s1" / "current" / "LH1" / "GDI_LH1_20260730110000.xml", "<Root/>")

    rows, exit_code = VerificationService(_config(tmp_path, expected, actual)).run()
    assert exit_code == ExitCode.COMPARISON_FAILURE
    assert rows[0].issue == "Expected scenario missing in Actual Outputs"


def test_actual_only_scenario(tmp_path: Path) -> None:
    expected = tmp_path / "expected"
    actual = tmp_path / "actual"
    expected.mkdir()
    _touch(actual / "s1" / "current" / "LH1" / "GDI_LH1_20260730110000.xml", "<Root/>")

    rows, exit_code = VerificationService(_config(tmp_path, expected, actual)).run()
    assert exit_code == ExitCode.COMPARISON_FAILURE
    assert rows[0].issue == "Unexpected scenario exists only in Actual Outputs"


def test_mixed_statuses(tmp_path: Path) -> None:
    expected = tmp_path / "expected"
    actual = tmp_path / "actual"
    _touch(expected / "pass" / "current" / "LH1" / "GDI_LH1_20260730110000.xml", "<Root>A</Root>")
    _touch(actual / "pass" / "current" / "LH1" / "GDI_LH1_20260730120000.xml", "<Root>A</Root>")
    _touch(expected / "fail" / "current" / "LH1" / "GDI_LH1_20260730110000.xml", "<Root>A</Root>")
    _touch(actual / "fail" / "current" / "LH1" / "GDI_LH1_20260730120000.xml", "<Root>B</Root>")
    (expected / "empty" / "current" / "LH1").mkdir(parents=True)
    (actual / "empty" / "current" / "LH1").mkdir(parents=True)

    rows, exit_code = VerificationService(_config(tmp_path, expected, actual)).run()
    statuses = {row.status for row in rows}
    assert VerificationStatus.PASSED in statuses
    assert VerificationStatus.FAILED in statuses
    assert VerificationStatus.NOT_VERIFIED in statuses
    assert exit_code == ExitCode.COMPARISON_FAILURE
