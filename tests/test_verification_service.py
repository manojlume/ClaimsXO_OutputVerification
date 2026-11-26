"""Tests for verification service orchestration and exit codes."""

from __future__ import annotations

from pathlib import Path

from output_verifier.config_loader import build_resolved_config
from output_verifier.constants import ExitCode, VerificationStatus
from output_verifier.verification_service import VerificationService


def _touch(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _config(
    tmp_path: Path,
    expected: Path,
    actual: Path,
    verification_type: str = "GDI",
    run_folders: str | None = None,
):
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
            "HSAB": {
                "wex_xml_paths": [],
                "xofilter_ignored_character_ranges": [],
            },
        },
    }
    if run_folders is not None:
        data["run_folders"] = run_folders
    return build_resolved_config(data)


SAMPLE_XOFILTER_FIXED_WIDTH = (
    "12201000322N12683    TORRE1S             JULIA1          "
    "22050124123124123149                       \n"
    "12201000926N12682    WHITE9              TESSA9          "
    "26010126123127123149                       \n"
)


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


def test_lh1_with_only_hold_is_not_marked_not_verified(tmp_path: Path) -> None:
    expected = tmp_path / "expected"
    actual = tmp_path / "actual"
    xml = "<Root><Item>A</Item></Root>"
    _touch(
        expected / "test_regen" / "current" / "LH1" / "Hold" / "GDI_REGEN_LH1_20260511031103.xml",
        xml,
    )
    _touch(
        actual / "test_regen" / "current" / "LH1" / "Hold" / "GDI_REGEN_LH1_20261021235718.xml",
        xml,
    )

    rows, exit_code = VerificationService(
        _config(tmp_path, expected, actual, run_folders="current, hold")
    ).run()
    assert exit_code == ExitCode.SUCCESS
    assert len(rows) == 1
    assert rows[0].run_type == "current"
    assert rows[0].output_type == "LH1\\Hold"
    assert rows[0].status == VerificationStatus.PASSED
    assert rows[0].expected_file == "LH1\\Hold\\GDI_REGEN_LH1_20260511031103.xml"
    assert rows[0].actual_file == "LH1\\Hold\\GDI_REGEN_LH1_20261021235718.xml"


def test_not_verified_empty(tmp_path: Path) -> None:
    expected = tmp_path / "expected"
    actual = tmp_path / "actual"
    (expected / "s1" / "current" / "LH1").mkdir(parents=True)
    (actual / "s1" / "current" / "LH1").mkdir(parents=True)

    rows, exit_code = VerificationService(_config(tmp_path, expected, actual)).run()
    assert exit_code == ExitCode.SUCCESS
    assert rows[0].status == VerificationStatus.NOT_VERIFIED


def test_empty_ignore_txt_in_expected_and_empty_actual_passes(tmp_path: Path) -> None:
    expected = tmp_path / "expected"
    actual = tmp_path / "actual"
    _touch(expected / "s1" / "current" / "LH1" / "ignore.txt", "")
    (actual / "s1" / "current" / "LH1").mkdir(parents=True)

    rows, exit_code = VerificationService(_config(tmp_path, expected, actual)).run()
    assert exit_code == ExitCode.SUCCESS
    assert len(rows) == 1
    assert rows[0].status == VerificationStatus.PASSED
    assert rows[0].output_type == "LH1"
    assert rows[0].expected_file == "LH1\\ignore.txt"
    assert rows[0].actual_file == ""
    assert "LH1\\ignore.txt" in rows[0].issue


def test_empty_ignore_txt_in_expected_with_actual_ignore_only_passes(tmp_path: Path) -> None:
    expected = tmp_path / "expected"
    actual = tmp_path / "actual"
    _touch(expected / "s1" / "current" / "LH1" / "ignore.txt", "")
    _touch(actual / "s1" / "current" / "LH1" / "IGNORE.TXT", "")

    rows, exit_code = VerificationService(_config(tmp_path, expected, actual)).run()
    assert exit_code == ExitCode.SUCCESS
    assert rows[0].status == VerificationStatus.PASSED


def test_empty_ignore_txt_in_expected_fails_when_actual_has_files(tmp_path: Path) -> None:
    expected = tmp_path / "expected"
    actual = tmp_path / "actual"
    _touch(expected / "s1" / "current" / "LH1" / "ignore.txt", "")
    _touch(
        actual / "s1" / "current" / "LH1" / "GDI_LH1_20260730120000.xml",
        "<Root/>",
    )

    rows, exit_code = VerificationService(_config(tmp_path, expected, actual)).run()
    assert exit_code == ExitCode.COMPARISON_FAILURE
    assert len(rows) == 1
    assert rows[0].status == VerificationStatus.FAILED
    assert rows[0].expected_file == "LH1\\ignore.txt"
    assert "LH1\\GDI_LH1_20260730120000.xml" in rows[0].actual_file
    assert "Actual folder contains file" in rows[0].issue


def test_non_empty_ignore_txt_does_not_auto_pass(tmp_path: Path) -> None:
    expected = tmp_path / "expected"
    actual = tmp_path / "actual"
    _touch(expected / "s1" / "current" / "LH1" / "ignore.txt", "skip")
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
    assert len(rows) == 1
    assert rows[0].status == VerificationStatus.FAILED
    assert "Unexpected actual file" in rows[0].issue


def test_unexpected_file(tmp_path: Path) -> None:
    expected = tmp_path / "expected"
    actual = tmp_path / "actual"
    _touch(expected / "s1" / "current" / "LH1" / "GDI_LH1_20260730110000.xml", "<Root/>")
    _touch(actual / "s1" / "current" / "LH1" / "GDI_LH1_20260730120000.xml", "<Root/>")
    _touch(actual / "s1" / "current" / "LH1" / "GDI_LH1_20260730130000.xml", "<Root/>")

    rows, exit_code = VerificationService(_config(tmp_path, expected, actual)).run()
    assert exit_code == ExitCode.COMPARISON_FAILURE
    assert len(rows) == 1
    assert rows[0].status == VerificationStatus.FAILED
    assert "File count mismatch" in rows[0].issue
    assert "Unexpected actual file" in rows[0].issue


def test_multiple_files_in_same_folder_produce_one_report_row(tmp_path: Path) -> None:
    expected = tmp_path / "expected"
    actual = tmp_path / "actual"
    xml = "<Root><Item>A</Item></Root>"
    _touch(expected / "s1" / "current" / "WEX" / "HB1_HSAB_CLAIMS_20260617010230.xml", xml)
    _touch(expected / "s1" / "current" / "WEX" / "HB2_HSAB_CLAIMS_20260617010230.xml", xml)
    _touch(actual / "s1" / "current" / "WEX" / "HB1_HSAB_CLAIMS_20261103120000.xml", xml)
    _touch(actual / "s1" / "current" / "WEX" / "HB2_HSAB_CLAIMS_20261103120000.xml", xml)

    rows, exit_code = VerificationService(
        _config(tmp_path, expected, actual, verification_type="HSAB")
    ).run()
    assert exit_code == ExitCode.SUCCESS
    assert len(rows) == 1
    assert rows[0].status == VerificationStatus.PASSED
    assert rows[0].run_type == "current"
    assert rows[0].output_type == "WEX"
    assert rows[0].expected_file == (
        "WEX\\HB1_HSAB_CLAIMS_20260617010230.xml\nWEX\\HB2_HSAB_CLAIMS_20260617010230.xml"
    )
    assert rows[0].actual_file == (
        "WEX\\HB1_HSAB_CLAIMS_20261103120000.xml\nWEX\\HB2_HSAB_CLAIMS_20261103120000.xml"
    )
    assert rows[0].issue == ""


def test_multiple_output_subfolders_produce_one_current_row(tmp_path: Path) -> None:
    expected = tmp_path / "expected"
    actual = tmp_path / "actual"
    xml = "<Root><Item>A</Item></Root>"
    csv_header = "FileDate,Name\n"
    _touch(expected / "s1" / "current" / "LH1" / "GDI_LH1_20261019025117.xml", xml)
    _touch(actual / "s1" / "current" / "LH1" / "GDI_LH1_20261125175245.xml", xml)
    _touch(
        expected / "s1" / "current" / "manual" / "GDI_MANUAL_20261019025119.csv",
        csv_header + "2026-01-01,A\n",
    )
    _touch(
        actual / "s1" / "current" / "manual" / "GDI_MANUAL_20261125175247.csv",
        csv_header + "2026-01-01,A\n",
    )
    _touch(
        expected / "s1" / "current" / "manual" / "GDI_MANUAL_PATIENT_20261019025121.csv",
        csv_header + "2026-01-01,B\n",
    )
    _touch(
        actual / "s1" / "current" / "manual" / "GDI_MANUAL_PATIENT_20261125175249.csv",
        csv_header + "2026-01-01,B\n",
    )

    rows, exit_code = VerificationService(_config(tmp_path, expected, actual)).run()
    assert exit_code == ExitCode.SUCCESS
    assert len(rows) == 1
    assert rows[0].run_type == "current"
    assert rows[0].status == VerificationStatus.PASSED
    assert rows[0].output_type == "LH1\nmanual"
    assert "LH1\\GDI_LH1_20261019025117.xml" in rows[0].expected_file
    assert "manual\\GDI_MANUAL_20261019025119.csv" in rows[0].expected_file
    assert "manual\\GDI_MANUAL_PATIENT_20261019025121.csv" in rows[0].expected_file


def test_multiple_files_folder_fails_when_any_file_fails(tmp_path: Path) -> None:
    expected = tmp_path / "expected"
    actual = tmp_path / "actual"
    _touch(
        expected / "s1" / "current" / "WEX" / "HB1_HSAB_CLAIMS_20260617010230.xml",
        "<Root>A</Root>",
    )
    _touch(
        expected / "s1" / "current" / "WEX" / "HB2_HSAB_CLAIMS_20260617010230.xml",
        "<Root>A</Root>",
    )
    _touch(
        actual / "s1" / "current" / "WEX" / "HB1_HSAB_CLAIMS_20261103120000.xml",
        "<Root>A</Root>",
    )
    _touch(
        actual / "s1" / "current" / "WEX" / "HB2_HSAB_CLAIMS_20261103120000.xml",
        "<Root>B</Root>",
    )

    rows, exit_code = VerificationService(
        _config(tmp_path, expected, actual, verification_type="HSAB")
    ).run()
    assert exit_code == ExitCode.COMPARISON_FAILURE
    assert len(rows) == 1
    assert rows[0].status == VerificationStatus.FAILED
    assert "WEX\\HB2_HSAB_CLAIMS_20260617010230.xml" in rows[0].issue
    assert "WEX\\HB2_HSAB_CLAIMS_20261103120000.xml" in rows[0].issue


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


def test_empty_run_folder_on_both_sides_is_not_verified(tmp_path: Path) -> None:
    expected = tmp_path / "expected"
    actual = tmp_path / "actual"
    (expected / "test_tickets" / "test_ticket_81243" / "current").mkdir(parents=True)
    (actual / "test_tickets" / "test_ticket_81243" / "current").mkdir(parents=True)

    rows, exit_code = VerificationService(_config(tmp_path, expected, actual)).run()
    assert exit_code == ExitCode.SUCCESS
    assert len(rows) == 1
    assert rows[0].status == VerificationStatus.NOT_VERIFIED
    assert rows[0].issue == "No files available for verification"
    assert rows[0].scenario == "test_tickets\\test_ticket_81243"
    assert rows[0].run_type == "current"
    assert rows[0].output_type == ""


def test_hsab_xofilter_trigger_fixed_width_passed(tmp_path: Path) -> None:
    expected = tmp_path / "expected"
    actual = tmp_path / "actual"
    _touch(
        expected
        / "s1"
        / "current"
        / "XOFilter"
        / "HCSC-BCBSIL-FSA-Eligibility-File_20260730110000.txt",
        SAMPLE_XOFILTER_FIXED_WIDTH,
    )
    _touch(
        actual
        / "s1"
        / "current"
        / "xofilter"
        / "HCSC-BCBSIL-FSA-Eligibility-File_20260730120000.txt",
        SAMPLE_XOFILTER_FIXED_WIDTH,
    )

    rows, exit_code = VerificationService(
        _config(tmp_path, expected, actual, verification_type="HSAB")
    ).run()
    assert exit_code == ExitCode.SUCCESS
    assert len(rows) == 1
    assert rows[0].output_type == "XOFilter"
    assert rows[0].status == VerificationStatus.PASSED
    assert rows[0].run_type == "current"
    assert rows[0].expected_file.startswith("XOFilter\\")


def test_hsab_xofilter_trigger_eight_digit_date_passed(tmp_path: Path) -> None:
    expected = tmp_path / "expected"
    actual = tmp_path / "actual"
    _touch(
        expected
        / "s1"
        / "current"
        / "XOFilter"
        / "HCSC-BCBSIL-FSA-Eligibility-File_20261018.txt",
        SAMPLE_XOFILTER_FIXED_WIDTH,
    )
    _touch(
        actual
        / "s1"
        / "current"
        / "xofilter"
        / "HCSC-BCBSIL-FSA-Eligibility-File_20261103.txt",
        SAMPLE_XOFILTER_FIXED_WIDTH,
    )

    rows, exit_code = VerificationService(
        _config(tmp_path, expected, actual, verification_type="HSAB")
    ).run()
    assert exit_code == ExitCode.SUCCESS
    assert len(rows) == 1
    assert rows[0].output_type == "XOFilter"
    assert rows[0].status == VerificationStatus.PASSED
    assert rows[0].expected_file == (
        "XOFilter\\HCSC-BCBSIL-FSA-Eligibility-File_20261018.txt"
    )
    assert rows[0].actual_file == (
        "XOFilter\\HCSC-BCBSIL-FSA-Eligibility-File_20261103.txt"
    )
