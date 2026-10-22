"""Tests for YAML configuration loading and validation."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from output_verifier.config import ConfigurationError
from output_verifier.config_loader import build_resolved_config, load_resolved_config, load_yaml_file
from output_verifier.constants import VerificationType


def _write_config(path: Path, data: dict) -> Path:
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


def _base_config(expected: Path, actual: Path) -> dict:
    return {
        "solution_type": "ClaimsXO",
        "tpa_id": "GDI",
        "expected_parent_folder": str(expected),
        "actual_parent_folder": str(actual),
        "report": {
            "output_folder": str(expected.parent / "reports"),
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
            "output_folder": str(expected.parent / "logs"),
            "max_bytes": 10485760,
            "backup_count": 5,
        },
        "ignore_rules": {
            "GDI": {
                "lh1_xml_paths": ["/Root/@CreatedDateTime"],
                "manual_csv_columns": [],
                "patient_manual_csv_columns": [],
                "mbi_field_positions": [],
            },
            "HSAB": {"wex_xml_paths": []},
        },
    }


def test_valid_yaml(tmp_path: Path) -> None:
    expected = tmp_path / "expected"
    actual = tmp_path / "actual"
    expected.mkdir()
    actual.mkdir()
    config_file = _write_config(tmp_path / "config.yaml", _base_config(expected, actual))

    resolved = load_resolved_config(config_file, validate_parent_folders=True)

    assert resolved.tpa_id == VerificationType.GDI
    assert resolved.expected_parent_folder == expected.resolve()
    assert resolved.actual_parent_folder == actual.resolve()


def test_missing_yaml(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError, match="not found"):
        load_yaml_file(tmp_path / "missing.yaml")


def test_invalid_yaml(tmp_path: Path) -> None:
    config_file = tmp_path / "bad.yaml"
    config_file.write_text("verification_type: [unterminated", encoding="utf-8")
    with pytest.raises(ConfigurationError, match="Invalid YAML"):
        load_yaml_file(config_file)


def test_cli_override(tmp_path: Path) -> None:
    expected = tmp_path / "expected"
    actual = tmp_path / "actual"
    expected.mkdir()
    actual.mkdir()
    other_expected = tmp_path / "other_expected"
    other_expected.mkdir()
    data = _base_config(expected, actual)

    resolved = build_resolved_config(
        data,
        tpa_id_override="HSAB",
        expected_parent_folder_override=str(other_expected),
        log_level_override="DEBUG",
    )

    assert resolved.tpa_id == VerificationType.HSAB
    assert resolved.expected_parent_folder == other_expected.resolve()
    assert resolved.logging.level == "DEBUG"


def test_missing_required_path(tmp_path: Path) -> None:
    data = _base_config(tmp_path / "missing", tmp_path / "actual")
    (tmp_path / "actual").mkdir()
    with pytest.raises(ConfigurationError, match="expected_parent_folder"):
        build_resolved_config(data)


def test_unsupported_verification_type(tmp_path: Path) -> None:
    expected = tmp_path / "expected"
    actual = tmp_path / "actual"
    expected.mkdir()
    actual.mkdir()
    data = _base_config(expected, actual)
    data["tpa_id"] = "UNKNOWN"
    with pytest.raises(ConfigurationError, match="Unsupported tpa_id"):
        build_resolved_config(data)


def test_invalid_log_level(tmp_path: Path) -> None:
    expected = tmp_path / "expected"
    actual = tmp_path / "actual"
    expected.mkdir()
    actual.mkdir()
    data = _base_config(expected, actual)
    data["logging"]["level"] = "VERBOSE"
    with pytest.raises(ConfigurationError, match="Invalid log level"):
        build_resolved_config(data)


def test_invalid_color(tmp_path: Path) -> None:
    expected = tmp_path / "expected"
    actual = tmp_path / "actual"
    expected.mkdir()
    actual.mkdir()
    data = _base_config(expected, actual)
    data["report"]["status_colors"]["passed"] = "green"
    with pytest.raises(ConfigurationError, match="hex color"):
        build_resolved_config(data)


def test_invalid_mbi_position(tmp_path: Path) -> None:
    expected = tmp_path / "expected"
    actual = tmp_path / "actual"
    expected.mkdir()
    actual.mkdir()
    data = _base_config(expected, actual)
    data["ignore_rules"]["GDI"]["mbi_field_positions"] = [0]
    with pytest.raises(ConfigurationError, match="Invalid ignored field position"):
        build_resolved_config(data)


def test_run_folders_comma_separated(tmp_path: Path) -> None:
    expected = tmp_path / "expected"
    actual = tmp_path / "actual"
    expected.mkdir()
    actual.mkdir()
    data = _base_config(expected, actual)
    data["run_folders"] = "Current, pre"
    resolved = build_resolved_config(data)
    assert resolved.run_folders == ("current", "pre")


def test_empty_run_folders_means_all(tmp_path: Path) -> None:
    expected = tmp_path / "expected"
    actual = tmp_path / "actual"
    expected.mkdir()
    actual.mkdir()
    data = _base_config(expected, actual)
    data["run_folders"] = ""
    resolved = build_resolved_config(data)
    assert resolved.run_folders == ()


def test_unsupported_run_folder(tmp_path: Path) -> None:
    expected = tmp_path / "expected"
    actual = tmp_path / "actual"
    expected.mkdir()
    actual.mkdir()
    data = _base_config(expected, actual)
    data["run_folders"] = "current, draft"
    with pytest.raises(ConfigurationError, match="Unsupported run folder"):
        build_resolved_config(data)


def test_invalid_xpath_syntax(tmp_path: Path) -> None:
    expected = tmp_path / "expected"
    actual = tmp_path / "actual"
    expected.mkdir()
    actual.mkdir()
    data = _base_config(expected, actual)
    data["ignore_rules"]["GDI"]["lh1_xml_paths"] = ["//["]
    with pytest.raises(ConfigurationError, match="Invalid XPath"):
        build_resolved_config(data)


def test_legacy_verification_type_yaml_still_loads(tmp_path: Path) -> None:
    expected = tmp_path / "expected"
    actual = tmp_path / "actual"
    expected.mkdir()
    actual.mkdir()
    data = _base_config(expected, actual)
    data.pop("tpa_id")
    data["verification_type"] = "HSAB"
    data["report"].pop("include_tpa_id")
    data["report"]["include_verification_type"] = True
    resolved = build_resolved_config(data)
    assert resolved.tpa_id == VerificationType.HSAB
    assert resolved.report.include_tpa_id is True
