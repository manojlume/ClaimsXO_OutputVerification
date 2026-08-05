"""Configuration tests for TransactionXO–HSAB."""

from __future__ import annotations

from pathlib import Path

import pytest

from output_verifier.config import ConfigurationError, validate_character_ranges
from output_verifier.config_loader import build_resolved_config
from output_verifier.constants import SolutionType, VerificationType


def _paths(tmp_path: Path) -> tuple[Path, Path]:
    expected = tmp_path / "expected"
    actual = tmp_path / "actual"
    expected.mkdir()
    actual.mkdir()
    return expected, actual


def _base(expected: Path, actual: Path) -> dict:
    return {
        "solution_type": "TransactionXO",
        "verification_type": "HSAB",
        "expected_parent_folder": str(expected),
        "actual_parent_folder": str(actual),
        "report": {
            "output_folder": str(expected.parent / "reports"),
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
            "output_folder": str(expected.parent / "logs"),
            "max_bytes": 10485760,
            "backup_count": 5,
        },
        "ignore_rules": {
            "TransactionXO": {
                "HSAB": {
                    "mdc_ignored_character_ranges": ["20-27", "45"],
                    "exception_dup_acct_csv_columns": ["Amount"],
                    "exception_utp_csv_columns": ["SSN"],
                }
            }
        },
    }


def test_transaction_hsab_accepted(tmp_path: Path) -> None:
    expected, actual = _paths(tmp_path)
    resolved = build_resolved_config(_base(expected, actual))
    assert resolved.solution_type == SolutionType.TRANSACTION_XO
    assert resolved.verification_type == VerificationType.HSAB
    assert resolved.ignore_rules.transaction_hsab_mdc_ignored_character_ranges == (
        (20, 27),
        (45, 45),
    )
    assert resolved.ignore_rules.transaction_hsab_exception_dup_acct_csv_columns == ("Amount",)
    assert resolved.ignore_rules.transaction_hsab_exception_utp_csv_columns == ("SSN",)


def test_transaction_unsupported_gdi_rejected(tmp_path: Path) -> None:
    expected, actual = _paths(tmp_path)
    data = _base(expected, actual)
    data["verification_type"] = "GDI"
    with pytest.raises(ConfigurationError, match="Unsupported verification type"):
        build_resolved_config(data)


def test_cli_override_solution_type(tmp_path: Path) -> None:
    expected, actual = _paths(tmp_path)
    data = _base(expected, actual)
    data["solution_type"] = "ClaimsXO"
    data["verification_type"] = "GDI"
    resolved = build_resolved_config(
        data,
        solution_type_override="TransactionXO",
        verification_type_override="HSAB",
    )
    assert resolved.solution_type == SolutionType.TRANSACTION_XO
    assert resolved.verification_type == VerificationType.HSAB


def test_invalid_character_ranges() -> None:
    with pytest.raises(ConfigurationError):
        validate_character_ranges("mdc_ignored_character_ranges", ["20-"])
    with pytest.raises(ConfigurationError):
        validate_character_ranges("mdc_ignored_character_ranges", ["0"])
    with pytest.raises(ConfigurationError):
        validate_character_ranges("mdc_ignored_character_ranges", ["27-20"])


def test_claimsxo_still_loads(tmp_path: Path) -> None:
    expected, actual = _paths(tmp_path)
    data = _base(expected, actual)
    data["solution_type"] = "ClaimsXO"
    data["verification_type"] = "GDI"
    data["ignore_rules"] = {
        "ClaimsXO": {
            "GDI": {
                "lh1_xml_paths": [],
                "manual_csv_columns": [],
                "patient_manual_csv_columns": [],
                "mbi_field_positions": [],
            }
        }
    }
    resolved = build_resolved_config(data)
    assert resolved.solution_type == SolutionType.CLAIMS_XO
