"""Additional configuration tests for nested solution ignore_rules."""

from __future__ import annotations

from pathlib import Path

import pytest

from output_verifier.config import ConfigurationError
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
        "solution_type": "ClaimsXO",
        "tpa_id": "GDI",
        "expected_parent_folder": str(expected),
        "actual_parent_folder": str(actual),
        "report": {
            "output_folder": str(expected.parent / "reports"),
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
            "output_folder": str(expected.parent / "logs"),
            "max_bytes": 10485760,
            "backup_count": 5,
        },
        "ignore_rules": {
            "ClaimsXO": {
                "GDI": {
                    "lh1_xml_paths": ["/Root/@CreatedDateTime"],
                    "manual_csv_columns": ["FileDate"],
                    "patient_manual_csv_columns": [],
                    "mbi_field_positions": [19],
                },
                "HSAB": {"wex_xml_paths": ["/Root/@A"]},
            },
            "EnrollmentXO": {
                "ABG": {
                    "alegeus_mbi_field_positions": [2],
                    "report_csv_columns": ["Timestamp"],
                },
                "GDI": {
                    "wexhealth_field_positions": [3],
                    "report_csv_columns": ["RunId"],
                },
                "HSAB": {
                    "enrollment_import_field_positions": [4],
                    "report_csv_columns": ["BatchId"],
                },
            },
        },
    }


def test_nested_claims_gdi_ignore_rules(tmp_path: Path) -> None:
    expected, actual = _paths(tmp_path)
    resolved = build_resolved_config(_base(expected, actual))
    assert resolved.ignore_rules.claims_gdi_lh1_xml_paths == ("/Root/@CreatedDateTime",)
    assert resolved.ignore_rules.claims_gdi_manual_csv_columns == ("FileDate",)
    assert resolved.ignore_rules.claims_gdi_mbi_field_positions == (19,)


def test_nested_claims_hsab_ignore_rules(tmp_path: Path) -> None:
    expected, actual = _paths(tmp_path)
    data = _base(expected, actual)
    data["tpa_id"] = "HSAB"
    resolved = build_resolved_config(data)
    assert resolved.ignore_rules.claims_hsab_wex_xml_paths == ("/Root/@A",)


def test_nested_enrollment_ignore_rules(tmp_path: Path) -> None:
    expected, actual = _paths(tmp_path)
    data = _base(expected, actual)
    data["solution_type"] = "EnrollmentXO"
    data["tpa_id"] = "ABG"
    resolved = build_resolved_config(data)
    assert resolved.solution_type == SolutionType.ENROLLMENT_XO
    assert resolved.tpa_id == VerificationType.ABG
    assert resolved.ignore_rules.enrollment_abg_alegeus_mbi_field_positions == (2,)
    assert resolved.ignore_rules.enrollment_abg_report_csv_columns == ("Timestamp",)
    assert resolved.ignore_rules.enrollment_gdi_wexhealth_field_positions == (3,)
    assert resolved.ignore_rules.enrollment_hsab_enrollment_import_field_positions == (4,)


def test_legacy_ignore_rules_still_load(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    expected, actual = _paths(tmp_path)
    data = _base(expected, actual)
    data["ignore_rules"] = {
        "GDI": {
            "lh1_xml_paths": ["/Legacy/@A"],
            "manual_csv_columns": [],
            "patient_manual_csv_columns": [],
            "mbi_field_positions": [],
        },
        "HSAB": {"wex_xml_paths": []},
    }
    with caplog.at_level("WARNING"):
        resolved = build_resolved_config(data)
    assert resolved.ignore_rules.claims_gdi_lh1_xml_paths == ("/Legacy/@A",)
    assert any("deprecated" in message.lower() for message in caplog.messages)


def test_invalid_solution_type(tmp_path: Path) -> None:
    expected, actual = _paths(tmp_path)
    data = _base(expected, actual)
    data["solution_type"] = "UnknownXO"
    with pytest.raises(ConfigurationError, match="Unsupported solution type"):
        build_resolved_config(data)


def test_invalid_verification_for_enrollment(tmp_path: Path) -> None:
    expected, actual = _paths(tmp_path)
    data = _base(expected, actual)
    data["solution_type"] = "ClaimsXO"
    data["tpa_id"] = "ABG"
    with pytest.raises(ConfigurationError, match="Unsupported tpa_id"):
        build_resolved_config(data)
