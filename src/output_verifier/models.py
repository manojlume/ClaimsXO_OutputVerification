"""Dataclass models used across the verification utility."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from output_verifier.constants import (
    FileFormat,
    OutputType,
    SolutionType,
    VerificationStatus,
    VerificationType,
)


@dataclass(frozen=True)
class ReportConfig:
    """Resolved Excel report settings."""

    output_folder: Path
    base_file_name: str
    include_solution_type: bool
    include_verification_type: bool
    include_timestamp: bool
    timestamp_format: str
    status_colors: dict[str, str]


@dataclass(frozen=True)
class LoggingConfig:
    """Resolved logging settings."""

    level: str
    log_to_console: bool
    log_to_file: bool
    output_folder: Path
    max_bytes: int
    backup_count: int


@dataclass(frozen=True)
class IgnoreRulesConfig:
    """Resolved ignore rules grouped by solution and verification type."""

    claims_gdi_lh1_xml_paths: tuple[str, ...] = ()
    claims_gdi_manual_csv_columns: tuple[str, ...] = ()
    claims_gdi_patient_manual_csv_columns: tuple[str, ...] = ()
    claims_gdi_mbi_field_positions: tuple[int, ...] = ()
    claims_hsab_wex_xml_paths: tuple[str, ...] = ()
    enrollment_abg_alegeus_mbi_field_positions: tuple[int, ...] = ()
    enrollment_abg_report_csv_columns: tuple[str, ...] = ()
    enrollment_gdi_wexhealth_field_positions: tuple[int, ...] = ()
    enrollment_gdi_report_csv_columns: tuple[str, ...] = ()
    enrollment_hsab_enrollment_import_field_positions: tuple[int, ...] = ()
    enrollment_hsab_report_csv_columns: tuple[str, ...] = ()

    def xml_paths_for(
        self,
        solution_type: SolutionType,
        verification_type: VerificationType,
        ignore_rule_key: str,
    ) -> tuple[str, ...]:
        """Return configured XML ignore paths for the active solution profile."""
        if solution_type != SolutionType.CLAIMS_XO:
            return ()
        if verification_type == VerificationType.GDI and ignore_rule_key == "lh1_xml_paths":
            return self.claims_gdi_lh1_xml_paths
        if verification_type == VerificationType.HSAB and ignore_rule_key == "wex_xml_paths":
            return self.claims_hsab_wex_xml_paths
        return ()

    def csv_columns_for(
        self,
        solution_type: SolutionType,
        verification_type: VerificationType,
        ignore_rule_key: str,
    ) -> tuple[str, ...]:
        """Return configured CSV ignore columns for the active profile."""
        if solution_type == SolutionType.CLAIMS_XO and verification_type == VerificationType.GDI:
            if ignore_rule_key == "manual_csv_columns":
                return self.claims_gdi_manual_csv_columns
            if ignore_rule_key == "patient_manual_csv_columns":
                return self.claims_gdi_patient_manual_csv_columns
            return ()
        if solution_type == SolutionType.ENROLLMENT_XO:
            if (
                verification_type == VerificationType.ABG
                and ignore_rule_key == "report_csv_columns"
            ):
                return self.enrollment_abg_report_csv_columns
            if (
                verification_type == VerificationType.GDI
                and ignore_rule_key == "report_csv_columns"
            ):
                return self.enrollment_gdi_report_csv_columns
            if (
                verification_type == VerificationType.HSAB
                and ignore_rule_key == "report_csv_columns"
            ):
                return self.enrollment_hsab_report_csv_columns
        return ()

    def field_positions_for(
        self,
        solution_type: SolutionType,
        verification_type: VerificationType,
        ignore_rule_key: str,
    ) -> tuple[int, ...]:
        """Return configured one-based field positions to ignore."""
        if solution_type == SolutionType.CLAIMS_XO:
            if (
                verification_type == VerificationType.GDI
                and ignore_rule_key == "mbi_field_positions"
            ):
                return self.claims_gdi_mbi_field_positions
            return ()
        if solution_type == SolutionType.ENROLLMENT_XO:
            if (
                verification_type == VerificationType.ABG
                and ignore_rule_key == "alegeus_mbi_field_positions"
            ):
                return self.enrollment_abg_alegeus_mbi_field_positions
            if (
                verification_type == VerificationType.GDI
                and ignore_rule_key == "wexhealth_field_positions"
            ):
                return self.enrollment_gdi_wexhealth_field_positions
            if (
                verification_type == VerificationType.HSAB
                and ignore_rule_key == "enrollment_import_field_positions"
            ):
                return self.enrollment_hsab_enrollment_import_field_positions
        return ()


@dataclass(frozen=True)
class ResolvedConfig:
    """Fully resolved application configuration."""

    solution_type: SolutionType
    verification_type: VerificationType
    expected_parent_folder: Path
    actual_parent_folder: Path
    report: ReportConfig
    logging: LoggingConfig
    ignore_rules: IgnoreRulesConfig
    config_path: Path | None = None


@dataclass(frozen=True)
class ScenarioKey:
    """Unique scenario identity used for inventory and reporting."""

    scenario_path: str
    run_type: str
    output_type: OutputType

    def display_scenario(self) -> str:
        """Return scenario path as shown in the report."""
        return self.scenario_path


@dataclass(frozen=True)
class ScenarioLocation:
    """Physical location of a scenario output folder under Expected or Actual."""

    scenario_key: ScenarioKey
    root_kind: str
    folder_path: Path


@dataclass(frozen=True)
class DiscoveredOutput:
    """One discovered output folder and its directly contained files."""

    scenario_key: ScenarioKey
    expected_folder: Path | None
    actual_folder: Path | None
    expected_files: tuple[Path, ...] = ()
    actual_files: tuple[Path, ...] = ()


@dataclass(frozen=True)
class FileIdentity:
    """Normalized filename identity after datetime/runtime replacement."""

    normalized_name: str
    original_filename: str
    file_path: Path
    file_format: FileFormat | None
    ignore_rule_key: str | None
    is_valid_pattern: bool
    delimiter: str | None = None
    has_header: bool = False
    compare_trailing_empty_fields: bool = True


@dataclass(frozen=True)
class MatchedFilePair:
    """One expected/actual pair matched by normalized identity and sort position."""

    scenario_key: ScenarioKey
    normalized_identity: str
    expected_file: Path | None
    actual_file: Path | None
    file_format: FileFormat | None
    ignore_rule_key: str | None
    is_valid_pattern: bool
    delimiter: str | None = None
    has_header: bool = False
    compare_trailing_empty_fields: bool = True


@dataclass(frozen=True)
class ComparisonOptions:
    """Options passed into format-specific comparators."""

    ignored_xml_paths: tuple[str, ...] = ()
    ignored_csv_columns: tuple[str, ...] = ()
    ignored_mbi_field_positions: tuple[int, ...] = ()
    ignored_field_positions: tuple[int, ...] = ()
    ignored_columns: tuple[str, ...] = ()
    delimiter: str = ","
    has_header: bool = False
    compare_trailing_empty_fields: bool = True


@dataclass(frozen=True)
class ComparisonDifference:
    """A single reported content difference."""

    description: str
    difference_type: str = ""
    expected_value: str = ""
    actual_value: str = ""
    location: str = ""


@dataclass
class ComparisonResult:
    """Result of comparing one expected/actual file pair."""

    status: VerificationStatus
    issue: str = ""
    differences: list[ComparisonDifference] = field(default_factory=list)


@dataclass
class ReportRow:
    """One Excel report row."""

    solution_type: str
    verification_type: str
    scenario: str
    run_type: str
    output_type: str
    expected_file: str
    actual_file: str
    status: VerificationStatus
    issue: str = ""


@dataclass
class ExecutionSummary:
    """End-of-run summary used for console output and Excel Summary sheet."""

    solution_type: SolutionType
    verification_type: VerificationType
    execution_start_time: datetime
    execution_end_time: datetime | None
    expected_root: Path
    actual_root: Path
    report_rows: list[ReportRow] = field(default_factory=list)
    report_path: Path | None = None
    exit_code: int = 0

    @property
    def total_rows(self) -> int:
        """Return total report row count."""
        return len(self.report_rows)

    @property
    def passed_count(self) -> int:
        """Return Passed row count."""
        return sum(1 for row in self.report_rows if row.status == VerificationStatus.PASSED)

    @property
    def failed_count(self) -> int:
        """Return Failed row count."""
        return sum(1 for row in self.report_rows if row.status == VerificationStatus.FAILED)

    @property
    def not_verified_count(self) -> int:
        """Return NotVerified row count."""
        return sum(
            1 for row in self.report_rows if row.status == VerificationStatus.NOT_VERIFIED
        )

    @property
    def compared_files_count(self) -> int:
        """Return rows that represent file-level comparisons or file issues."""
        return sum(
            1
            for row in self.report_rows
            if row.expected_file or row.actual_file or row.status == VerificationStatus.NOT_VERIFIED
        )
