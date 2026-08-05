"""End-to-end TransactionXO–HSAB verification tests."""

from __future__ import annotations

from pathlib import Path

from output_verifier.config_loader import build_resolved_config
from output_verifier.constants import ExitCode, VerificationStatus
from output_verifier.verification_service import VerificationService


def _touch(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _config(tmp_path: Path, expected: Path, actual: Path):
    data = {
        "solution_type": "TransactionXO",
        "verification_type": "HSAB",
        "expected_parent_folder": str(expected),
        "actual_parent_folder": str(actual),
        "report": {
            "output_folder": str(tmp_path / "reports"),
            "base_file_name": "VerificationReport",
            "include_solution_type": True,
            "include_verification_type": True,
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
            "TransactionXO": {
                "HSAB": {
                    "mdc_ignored_character_ranges": [],
                    "exception_dup_acct_csv_columns": [],
                    "exception_utp_csv_columns": [],
                }
            }
        },
    }
    return build_resolved_config(data)


def _seed_all_pass(expected: Path, actual: Path) -> None:
    mdc = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789\n"
    dup = "SSN,Amount,Description,TransactionCode\n111,60.00,Dup,12\n"
    utp = (
        "SSN,Amount,EN transaction\n"
        "222,10.00," + ("X" * 80) + "\n"
    )
    _touch(expected / "test_case" / "current" / "MDC" / "HSB_EN_2026062401_Converted.txt", mdc)
    _touch(actual / "test_case" / "current" / "MDC" / "HSB_EN_9999999999_Converted.txt", mdc)
    _touch(
        expected
        / "test_case"
        / "current"
        / "MDCExceptions"
        / "HSB_EN_2026062401_AllScenarios_ExceptionDupAcct_20260805103159.csv",
        dup,
    )
    _touch(
        actual
        / "test_case"
        / "current"
        / "MDCExceptions"
        / "HSB_EN_2026062499_AllScenarios_ExceptionDupAcct_20260805109999.csv",
        dup,
    )
    _touch(
        expected
        / "test_case"
        / "current"
        / "MDCExceptions"
        / "HSB_EN_2026062401_AllScenarios_ExceptionUTP_20260805103159.csv",
        utp,
    )
    _touch(
        actual
        / "test_case"
        / "current"
        / "MDCExceptions"
        / "HSB_EN_2026062499_AllScenarios_ExceptionUTP_20260805109999.csv",
        utp,
    )


def test_all_three_files_pass(tmp_path: Path) -> None:
    expected = tmp_path / "expected"
    actual = tmp_path / "actual"
    _seed_all_pass(expected, actual)
    rows, exit_code = VerificationService(_config(tmp_path, expected, actual)).run()
    assert exit_code == ExitCode.SUCCESS
    assert all(row.status == VerificationStatus.PASSED for row in rows)
    assert {row.solution_type for row in rows} == {"TransactionXO"}
    assert {row.verification_type for row in rows} == {"HSAB"}


def test_mdc_fails_csv_pass(tmp_path: Path) -> None:
    expected = tmp_path / "expected"
    actual = tmp_path / "actual"
    _seed_all_pass(expected, actual)
    _touch(
        actual / "test_case" / "current" / "MDC" / "HSB_EN_9999999999_Converted.txt",
        "CHANGED_CONTENT_LINE_ONE_____________\n",
    )
    rows, exit_code = VerificationService(_config(tmp_path, expected, actual)).run()
    assert exit_code == ExitCode.COMPARISON_FAILURE
    mdc_rows = [row for row in rows if row.output_type == "MDC"]
    csv_rows = [row for row in rows if row.output_type == "MDCExceptions"]
    assert any(row.status == VerificationStatus.FAILED for row in mdc_rows)
    assert all(row.status == VerificationStatus.PASSED for row in csv_rows)


def test_dup_acct_fails_only(tmp_path: Path) -> None:
    expected = tmp_path / "expected"
    actual = tmp_path / "actual"
    _seed_all_pass(expected, actual)
    bad_dup = "SSN,Amount,Description,TransactionCode\n111,65.00,Dup,12\n"
    _touch(
        actual
        / "test_case"
        / "current"
        / "MDCExceptions"
        / "HSB_EN_2026062499_AllScenarios_ExceptionDupAcct_20260805109999.csv",
        bad_dup,
    )
    rows, exit_code = VerificationService(_config(tmp_path, expected, actual)).run()
    assert exit_code == ExitCode.COMPARISON_FAILURE
    failed = [row for row in rows if row.status == VerificationStatus.FAILED]
    assert len(failed) == 1
    assert "ExceptionDupAcct" in (failed[0].expected_file or failed[0].actual_file)


def test_missing_mdc_file(tmp_path: Path) -> None:
    expected = tmp_path / "expected"
    actual = tmp_path / "actual"
    _seed_all_pass(expected, actual)
    (
        actual / "test_case" / "current" / "MDC" / "HSB_EN_9999999999_Converted.txt"
    ).unlink()
    rows, exit_code = VerificationService(_config(tmp_path, expected, actual)).run()
    assert exit_code == ExitCode.COMPARISON_FAILURE
    assert any(
        row.status == VerificationStatus.FAILED and "missing" in row.issue.lower()
        for row in rows
    )


def test_unexpected_exception_file(tmp_path: Path) -> None:
    expected = tmp_path / "expected"
    actual = tmp_path / "actual"
    _seed_all_pass(expected, actual)
    _touch(
        actual
        / "test_case"
        / "current"
        / "MDCExceptions"
        / "HSB_EN_EXTRA_AllScenarios_ExceptionDupAcct_20260805100000.csv",
        "SSN,Amount,Description,TransactionCode\n333,1.00,X,1\n",
    )
    rows, exit_code = VerificationService(_config(tmp_path, expected, actual)).run()
    assert exit_code == ExitCode.COMPARISON_FAILURE
    assert any("Unexpected" in row.issue or "mismatch" in row.issue.lower() for row in rows)


def test_empty_scenario_not_verified(tmp_path: Path) -> None:
    expected = tmp_path / "expected"
    actual = tmp_path / "actual"
    (expected / "empty" / "current" / "MDC").mkdir(parents=True)
    (actual / "empty" / "current" / "MDC").mkdir(parents=True)
    rows, exit_code = VerificationService(_config(tmp_path, expected, actual)).run()
    assert exit_code == ExitCode.SUCCESS
    assert rows[0].status == VerificationStatus.NOT_VERIFIED
