"""YAML configuration loading and resolution."""

from __future__ import annotations

import copy
import logging
from pathlib import Path
from typing import Any

import yaml

from output_verifier.config import (
    ConfigurationError,
    ensure_creatable_directory,
    parse_verification_type,
    require_existing_directory,
    validate_hex_color,
    validate_log_level,
    validate_mbi_field_positions,
    validate_non_negative_integer,
    validate_positive_integer,
    validate_solution_type,
    validate_string_list,
    validate_timestamp_format,
    validate_xpath_list,
)
from output_verifier.models import (
    IgnoreRulesConfig,
    LoggingConfig,
    ReportConfig,
    ResolvedConfig,
)

LOGGER = logging.getLogger(__name__)

DEFAULT_REPORT: dict[str, Any] = {
    "output_folder": "./reports",
    "base_file_name": "VerificationReport",
    "include_verification_type": True,
    "include_timestamp": True,
    "timestamp_format": "%Y%m%d%H%M%S",
    "status_colors": {
        "passed": "#C6EFCE",
        "failed": "#FFC7CE",
        "not_verified": "#FFEB9C",
    },
}

DEFAULT_LOGGING: dict[str, Any] = {
    "level": "INFO",
    "log_to_console": True,
    "log_to_file": True,
    "output_folder": "./logs",
    "max_bytes": 10485760,
    "backup_count": 5,
}


def load_yaml_file(config_path: Path) -> dict[str, Any]:
    """Load a YAML configuration file into a dictionary."""
    if not config_path.exists():
        raise ConfigurationError(f"Configuration file not found: {config_path}")
    try:
        with config_path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
    except yaml.YAMLError as error:
        raise ConfigurationError(f"Invalid YAML in {config_path}: {error}") from error
    except OSError as error:
        raise ConfigurationError(f"Unable to read configuration file {config_path}: {error}") from error

    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ConfigurationError("Configuration root must be a YAML mapping/object.")
    return data


def _merge_section(defaults: dict[str, Any], overrides: dict[str, Any] | None) -> dict[str, Any]:
    merged = copy.deepcopy(defaults)
    if not overrides:
        return merged
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            nested = copy.deepcopy(merged[key])
            nested.update(value)
            merged[key] = nested
        else:
            merged[key] = value
    return merged


def build_resolved_config(
    yaml_data: dict[str, Any],
    *,
    config_path: Path | None = None,
    verification_type_override: str | None = None,
    expected_parent_folder_override: str | None = None,
    actual_parent_folder_override: str | None = None,
    report_output_folder_override: str | None = None,
    log_level_override: str | None = None,
    validate_parent_folders: bool = True,
) -> ResolvedConfig:
    """Build a resolved configuration model from YAML and CLI overrides."""
    data = copy.deepcopy(yaml_data)

    solution_type = validate_solution_type(data.get("solution_type", "ClaimsXO"))

    verification_type_raw = (
        verification_type_override
        if verification_type_override is not None
        else data.get("verification_type")
    )
    if not verification_type_raw:
        raise ConfigurationError("verification_type is required.")
    verification_type = parse_verification_type(str(verification_type_raw))

    expected_raw = (
        expected_parent_folder_override
        if expected_parent_folder_override is not None
        else data.get("expected_parent_folder", "")
    )
    actual_raw = (
        actual_parent_folder_override
        if actual_parent_folder_override is not None
        else data.get("actual_parent_folder", "")
    )
    if not str(expected_raw).strip():
        raise ConfigurationError(
            "expected_parent_folder is required (YAML or --expected-parent-folder)."
        )
    if not str(actual_raw).strip():
        raise ConfigurationError(
            "actual_parent_folder is required (YAML or --actual-parent-folder)."
        )

    expected_parent = Path(str(expected_raw))
    actual_parent = Path(str(actual_raw))
    if validate_parent_folders:
        expected_parent = require_existing_directory("expected_parent_folder", expected_parent)
        actual_parent = require_existing_directory("actual_parent_folder", actual_parent)

    report_section = _merge_section(DEFAULT_REPORT, data.get("report"))
    if report_output_folder_override is not None:
        report_section["output_folder"] = report_output_folder_override

    logging_section = _merge_section(DEFAULT_LOGGING, data.get("logging"))
    if log_level_override is not None:
        logging_section["level"] = log_level_override

    status_colors_raw = report_section.get("status_colors", {})
    if not isinstance(status_colors_raw, dict):
        raise ConfigurationError("report.status_colors must be a mapping.")
    status_colors = {
        "passed": validate_hex_color("passed", status_colors_raw.get("passed", "#C6EFCE")),
        "failed": validate_hex_color("failed", status_colors_raw.get("failed", "#FFC7CE")),
        "not_verified": validate_hex_color(
            "not_verified", status_colors_raw.get("not_verified", "#FFEB9C")
        ),
    }

    report_output_folder = ensure_creatable_directory(
        "report.output_folder",
        Path(str(report_section["output_folder"])),
    )

    log_to_file = bool(logging_section.get("log_to_file", True))
    log_output_folder = Path(str(logging_section.get("output_folder", "./logs")))
    if log_to_file:
        log_output_folder = ensure_creatable_directory("logging.output_folder", log_output_folder)

    ignore_rules_raw = data.get("ignore_rules") or {}
    if not isinstance(ignore_rules_raw, dict):
        raise ConfigurationError("ignore_rules must be a mapping.")

    gdi_rules = ignore_rules_raw.get("GDI") or {}
    hsab_rules = ignore_rules_raw.get("HSAB") or {}
    if not isinstance(gdi_rules, dict):
        raise ConfigurationError("ignore_rules.GDI must be a mapping.")
    if not isinstance(hsab_rules, dict):
        raise ConfigurationError("ignore_rules.HSAB must be a mapping.")

    gdi_lh1_xml_paths = validate_xpath_list(
        "ignore_rules.GDI.lh1_xml_paths",
        validate_string_list("ignore_rules.GDI.lh1_xml_paths", gdi_rules.get("lh1_xml_paths")),
    )
    hsab_wex_xml_paths = validate_xpath_list(
        "ignore_rules.HSAB.wex_xml_paths",
        validate_string_list("ignore_rules.HSAB.wex_xml_paths", hsab_rules.get("wex_xml_paths")),
    )
    manual_csv_columns = validate_string_list(
        "ignore_rules.GDI.manual_csv_columns",
        gdi_rules.get("manual_csv_columns"),
    )
    patient_manual_csv_columns = validate_string_list(
        "ignore_rules.GDI.patient_manual_csv_columns",
        gdi_rules.get("patient_manual_csv_columns"),
    )
    mbi_positions_raw = gdi_rules.get("mbi_field_positions")
    mbi_field_positions = validate_mbi_field_positions(mbi_positions_raw)
    if isinstance(mbi_positions_raw, list):
        unique_count = len(set(mbi_positions_raw))
        if unique_count < len(mbi_positions_raw):
            LOGGER.warning(
                "Duplicate MBI ignored field positions were de-duplicated: %s",
                mbi_positions_raw,
            )

    resolved = ResolvedConfig(
        solution_type=solution_type,
        verification_type=verification_type,
        expected_parent_folder=expected_parent.resolve()
        if expected_parent.exists()
        else expected_parent,
        actual_parent_folder=actual_parent.resolve() if actual_parent.exists() else actual_parent,
        report=ReportConfig(
            output_folder=report_output_folder,
            base_file_name=str(report_section.get("base_file_name", "VerificationReport")),
            include_verification_type=bool(report_section.get("include_verification_type", True)),
            include_timestamp=bool(report_section.get("include_timestamp", True)),
            timestamp_format=validate_timestamp_format(
                report_section.get("timestamp_format", "%Y%m%d%H%M%S")
            ),
            status_colors=status_colors,
        ),
        logging=LoggingConfig(
            level=validate_log_level(logging_section.get("level", "INFO")),
            log_to_console=bool(logging_section.get("log_to_console", True)),
            log_to_file=log_to_file,
            output_folder=log_output_folder.resolve()
            if log_output_folder.exists()
            else log_output_folder,
            max_bytes=validate_positive_integer(
                "logging.max_bytes",
                logging_section.get("max_bytes", 10485760),
            ),
            backup_count=validate_non_negative_integer(
                "logging.backup_count",
                logging_section.get("backup_count", 5),
            ),
        ),
        ignore_rules=IgnoreRulesConfig(
            gdi_lh1_xml_paths=gdi_lh1_xml_paths,
            gdi_manual_csv_columns=manual_csv_columns,
            gdi_patient_manual_csv_columns=patient_manual_csv_columns,
            gdi_mbi_field_positions=mbi_field_positions,
            hsab_wex_xml_paths=hsab_wex_xml_paths,
        ),
        config_path=config_path,
    )
    return resolved


def load_resolved_config(
    config_path: Path,
    *,
    verification_type_override: str | None = None,
    expected_parent_folder_override: str | None = None,
    actual_parent_folder_override: str | None = None,
    report_output_folder_override: str | None = None,
    log_level_override: str | None = None,
    validate_parent_folders: bool = True,
) -> ResolvedConfig:
    """Load YAML from disk and resolve configuration with CLI overrides."""
    yaml_data = load_yaml_file(config_path)
    return build_resolved_config(
        yaml_data,
        config_path=config_path,
        verification_type_override=verification_type_override,
        expected_parent_folder_override=expected_parent_folder_override,
        actual_parent_folder_override=actual_parent_folder_override,
        report_output_folder_override=report_output_folder_override,
        log_level_override=log_level_override,
        validate_parent_folders=validate_parent_folders,
    )
