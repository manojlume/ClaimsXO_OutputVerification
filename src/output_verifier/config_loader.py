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
    parse_solution_type,
    parse_verification_type,
    require_existing_directory,
    validate_character_ranges,
    validate_field_positions,
    validate_hex_color,
    validate_log_level,
    validate_non_negative_integer,
    validate_positive_integer,
    validate_solution_verification_pair,
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
    "include_solution_type": True,
    "include_tpa_id": True,
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


def _yaml_tpa_id(data: dict[str, Any]) -> Any:
    if "tpa_id" in data:
        return data.get("tpa_id")
    if "verification_type" in data:
        LOGGER.warning("YAML key verification_type is deprecated. Use tpa_id.")
        return data.get("verification_type")
    return None


def _report_include_tpa_id(report_section: dict[str, Any]) -> bool:
    if "include_tpa_id" in report_section:
        return bool(report_section.get("include_tpa_id"))
    if "include_verification_type" in report_section:
        LOGGER.warning(
            "YAML key report.include_verification_type is deprecated. Use include_tpa_id."
        )
        return bool(report_section.get("include_verification_type"))
    return True


def _as_mapping(value: Any, field_name: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ConfigurationError(f"{field_name} must be a mapping.")
    return value


def _warn_duplicate_positions(field_name: str, raw_value: Any, unique_positions: tuple[int, ...]) -> None:
    if isinstance(raw_value, list) and len(set(raw_value)) < len(raw_value):
        LOGGER.warning(
            "Duplicate ignored field positions in %s were de-duplicated: %s -> %s",
            field_name,
            raw_value,
            list(unique_positions),
        )


def _parse_ignore_rules(ignore_rules_raw: dict[str, Any]) -> IgnoreRulesConfig:
    claims_section = _as_mapping(ignore_rules_raw.get("ClaimsXO"), "ignore_rules.ClaimsXO")
    enrollment_section = _as_mapping(
        ignore_rules_raw.get("EnrollmentXO"),
        "ignore_rules.EnrollmentXO",
    )
    transaction_section = _as_mapping(
        ignore_rules_raw.get("TransactionXO"),
        "ignore_rules.TransactionXO",
    )

    # Temporary backward compatibility for old ClaimsXO top-level GDI/HSAB keys.
    legacy_gdi = ignore_rules_raw.get("GDI")
    legacy_hsab = ignore_rules_raw.get("HSAB")
    if legacy_gdi is not None or legacy_hsab is not None:
        LOGGER.warning(
            "Old ignore_rules structure is deprecated. "
            "Please move rules under ignore_rules.ClaimsXO."
        )
        if not claims_section:
            claims_section = {}
        if legacy_gdi is not None and "GDI" not in claims_section:
            claims_section["GDI"] = legacy_gdi
        if legacy_hsab is not None and "HSAB" not in claims_section:
            claims_section["HSAB"] = legacy_hsab

    claims_gdi = _as_mapping(claims_section.get("GDI"), "ignore_rules.ClaimsXO.GDI")
    claims_hsab = _as_mapping(claims_section.get("HSAB"), "ignore_rules.ClaimsXO.HSAB")
    enrollment_abg = _as_mapping(enrollment_section.get("ABG"), "ignore_rules.EnrollmentXO.ABG")
    enrollment_gdi = _as_mapping(enrollment_section.get("GDI"), "ignore_rules.EnrollmentXO.GDI")
    enrollment_hsab = _as_mapping(enrollment_section.get("HSAB"), "ignore_rules.EnrollmentXO.HSAB")
    transaction_hsab = _as_mapping(
        transaction_section.get("HSAB"),
        "ignore_rules.TransactionXO.HSAB",
    )

    claims_gdi_mbi_raw = claims_gdi.get("mbi_field_positions")
    claims_gdi_mbi = validate_field_positions(
        "ignore_rules.ClaimsXO.GDI.mbi_field_positions",
        claims_gdi_mbi_raw,
    )
    _warn_duplicate_positions(
        "ignore_rules.ClaimsXO.GDI.mbi_field_positions",
        claims_gdi_mbi_raw,
        claims_gdi_mbi,
    )

    abg_mbi_raw = enrollment_abg.get("alegeus_mbi_field_positions")
    abg_mbi = validate_field_positions(
        "ignore_rules.EnrollmentXO.ABG.alegeus_mbi_field_positions",
        abg_mbi_raw,
    )
    _warn_duplicate_positions(
        "ignore_rules.EnrollmentXO.ABG.alegeus_mbi_field_positions",
        abg_mbi_raw,
        abg_mbi,
    )

    gdi_wex_raw = enrollment_gdi.get("wexhealth_field_positions")
    gdi_wex = validate_field_positions(
        "ignore_rules.EnrollmentXO.GDI.wexhealth_field_positions",
        gdi_wex_raw,
    )
    _warn_duplicate_positions(
        "ignore_rules.EnrollmentXO.GDI.wexhealth_field_positions",
        gdi_wex_raw,
        gdi_wex,
    )

    hsab_import_raw = enrollment_hsab.get("enrollment_import_field_positions")
    hsab_import = validate_field_positions(
        "ignore_rules.EnrollmentXO.HSAB.enrollment_import_field_positions",
        hsab_import_raw,
    )
    _warn_duplicate_positions(
        "ignore_rules.EnrollmentXO.HSAB.enrollment_import_field_positions",
        hsab_import_raw,
        hsab_import,
    )

    mdc_ranges = validate_character_ranges(
        "ignore_rules.TransactionXO.HSAB.mdc_ignored_character_ranges",
        transaction_hsab.get("mdc_ignored_character_ranges"),
    )

    return IgnoreRulesConfig(
        claims_gdi_lh1_xml_paths=validate_xpath_list(
            "ignore_rules.ClaimsXO.GDI.lh1_xml_paths",
            validate_string_list(
                "ignore_rules.ClaimsXO.GDI.lh1_xml_paths",
                claims_gdi.get("lh1_xml_paths"),
            ),
        ),
        claims_gdi_manual_csv_columns=validate_string_list(
            "ignore_rules.ClaimsXO.GDI.manual_csv_columns",
            claims_gdi.get("manual_csv_columns"),
        ),
        claims_gdi_patient_manual_csv_columns=validate_string_list(
            "ignore_rules.ClaimsXO.GDI.patient_manual_csv_columns",
            claims_gdi.get("patient_manual_csv_columns"),
        ),
        claims_gdi_mbi_field_positions=claims_gdi_mbi,
        claims_hsab_wex_xml_paths=validate_xpath_list(
            "ignore_rules.ClaimsXO.HSAB.wex_xml_paths",
            validate_string_list(
                "ignore_rules.ClaimsXO.HSAB.wex_xml_paths",
                claims_hsab.get("wex_xml_paths"),
            ),
        ),
        enrollment_abg_alegeus_mbi_field_positions=abg_mbi,
        enrollment_abg_report_csv_columns=validate_string_list(
            "ignore_rules.EnrollmentXO.ABG.report_csv_columns",
            enrollment_abg.get("report_csv_columns"),
        ),
        enrollment_gdi_wexhealth_field_positions=gdi_wex,
        enrollment_gdi_report_csv_columns=validate_string_list(
            "ignore_rules.EnrollmentXO.GDI.report_csv_columns",
            enrollment_gdi.get("report_csv_columns"),
        ),
        enrollment_hsab_enrollment_import_field_positions=hsab_import,
        enrollment_hsab_report_csv_columns=validate_string_list(
            "ignore_rules.EnrollmentXO.HSAB.report_csv_columns",
            enrollment_hsab.get("report_csv_columns"),
        ),
        transaction_hsab_mdc_ignored_character_ranges=mdc_ranges,
        transaction_hsab_exception_dup_acct_csv_columns=validate_string_list(
            "ignore_rules.TransactionXO.HSAB.exception_dup_acct_csv_columns",
            transaction_hsab.get("exception_dup_acct_csv_columns"),
        ),
        transaction_hsab_exception_utp_csv_columns=validate_string_list(
            "ignore_rules.TransactionXO.HSAB.exception_utp_csv_columns",
            transaction_hsab.get("exception_utp_csv_columns"),
        ),
    )


def build_resolved_config(
    yaml_data: dict[str, Any],
    *,
    config_path: Path | None = None,
    solution_type_override: str | None = None,
    tpa_id_override: str | None = None,
    expected_parent_folder_override: str | None = None,
    actual_parent_folder_override: str | None = None,
    report_output_folder_override: str | None = None,
    log_level_override: str | None = None,
    validate_parent_folders: bool = True,
) -> ResolvedConfig:
    """Build a resolved configuration model from YAML and CLI overrides."""
    data = copy.deepcopy(yaml_data)

    solution_raw = (
        solution_type_override
        if solution_type_override is not None
        else data.get("solution_type", "ClaimsXO")
    )
    solution_type = parse_solution_type(solution_raw)

    tpa_id_raw = (
        tpa_id_override if tpa_id_override is not None else _yaml_tpa_id(data)
    )
    if not tpa_id_raw:
        raise ConfigurationError("tpa_id is required.")
    tpa_id = parse_verification_type(str(tpa_id_raw))
    validate_solution_verification_pair(solution_type, tpa_id)

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
    ignore_rules = _parse_ignore_rules(ignore_rules_raw)

    return ResolvedConfig(
        solution_type=solution_type,
        tpa_id=tpa_id,
        expected_parent_folder=expected_parent.resolve()
        if expected_parent.exists()
        else expected_parent,
        actual_parent_folder=actual_parent.resolve() if actual_parent.exists() else actual_parent,
        report=ReportConfig(
            output_folder=report_output_folder,
            base_file_name=str(report_section.get("base_file_name", "VerificationReport")),
            include_solution_type=bool(report_section.get("include_solution_type", True)),
            include_tpa_id=_report_include_tpa_id(report_section),
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
        ignore_rules=ignore_rules,
        config_path=config_path,
    )


def load_resolved_config(
    config_path: Path,
    *,
    solution_type_override: str | None = None,
    tpa_id_override: str | None = None,
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
        solution_type_override=solution_type_override,
        tpa_id_override=tpa_id_override,
        expected_parent_folder_override=expected_parent_folder_override,
        actual_parent_folder_override=actual_parent_folder_override,
        report_output_folder_override=report_output_folder_override,
        log_level_override=log_level_override,
        validate_parent_folders=validate_parent_folders,
    )
