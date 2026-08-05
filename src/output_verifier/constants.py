"""Application constants and solution/TPA profile definitions."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Pattern


APPLICATION_NAME = "output-verifier"
APPLICATION_VERSION = "1.0.0"
DATETIME_TOKEN = "<datetime>"
RUNTIME_TIMESTAMP_TOKEN = "<runtime_timestamp>"
DATETIME_DIGIT_COUNT = 14
DATETIME_PLACEHOLDER_PATTERN = re.compile(r"\d{14}")

MAX_REPORTED_DIFFERENCES = 2
MAX_LOGGED_VALUE_LENGTH = 200

MBI_DELIMITER = "|"
COMMA_DELIMITER = ","
PIPE_DELIMITER = "|"


class SolutionType(str, Enum):
    """Supported solution types."""

    CLAIMS_XO = "ClaimsXO"
    ENROLLMENT_XO = "EnrollmentXO"


class VerificationType(str, Enum):
    """Supported verification (TPA) types."""

    ABG = "ABG"
    GDI = "GDI"
    HSAB = "HSAB"


class OutputType(str, Enum):
    """Supported output folder types."""

    LH1 = "LH1"
    MANUAL = "manual"
    ALG = "ALG"
    WEX = "WEX"
    ALEGEUS = "alegeus"
    REPORTS = "reports"
    WEX_HEALTH = "WexHealth"
    HSAB_ENROLLMENT_IMPORT = "HSABEnrollmentImport"


class RunType(str, Enum):
    """Supported run folder types."""

    CURRENT = "current"
    PRE = "pre"
    PREPRE = "prepre"
    HOLD = "hold"


class VerificationStatus(str, Enum):
    """Supported verification result statuses."""

    PASSED = "Passed"
    FAILED = "Failed"
    NOT_VERIFIED = "NotVerified"


class FileFormat(str, Enum):
    """Supported file formats for comparison."""

    XML = "xml"
    CSV = "csv"
    MBI = "mbi"
    DELIMITED_TEXT = "delimited_text"


class ExitCode(int, Enum):
    """Process exit codes."""

    SUCCESS = 0
    COMPARISON_FAILURE = 1
    SYSTEM_ERROR = 2


class DifferenceType(str, Enum):
    """XML/content difference categories."""

    ELEMENT_MISSING = "Element missing"
    UNEXPECTED_ELEMENT = "Unexpected element"
    ELEMENT_NAME_MISMATCH = "Element name mismatch"
    TEXT_MISMATCH = "Text mismatch"
    ATTRIBUTE_MISSING = "Attribute missing"
    UNEXPECTED_ATTRIBUTE = "Unexpected attribute"
    ATTRIBUTE_VALUE_MISMATCH = "Attribute value mismatch"
    CHILD_COUNT_MISMATCH = "Child count mismatch"


SUPPORTED_RUN_FOLDERS: frozenset[str] = frozenset(
    value.value.lower() for value in RunType
)

CLAIMS_XO_EXTENSIONS: frozenset[str] = frozenset({".xml", ".csv", ".mbi"})
ENROLLMENT_XO_EXTENSIONS: frozenset[str] = frozenset({".mbi", ".txt", ".csv"})

OUTPUT_TYPE_CANONICAL: dict[str, OutputType] = {
    "lh1": OutputType.LH1,
    "manual": OutputType.MANUAL,
    "alg": OutputType.ALG,
    "wex": OutputType.WEX,
    "alegeus": OutputType.ALEGEUS,
    "reports": OutputType.REPORTS,
    "wexhealth": OutputType.WEX_HEALTH,
    "hsabenrollmentimport": OutputType.HSAB_ENROLLMENT_IMPORT,
}

CLAIMS_XO_VERIFICATION_TYPES: frozenset[VerificationType] = frozenset(
    {VerificationType.GDI, VerificationType.HSAB}
)
ENROLLMENT_XO_VERIFICATION_TYPES: frozenset[VerificationType] = frozenset(
    {VerificationType.ABG, VerificationType.GDI, VerificationType.HSAB}
)

VALID_LOG_LEVELS: frozenset[str] = frozenset(
    {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"}
)
HEX_COLOR_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")


# ClaimsXO filename patterns (14-digit datetime).
GDI_LH1_PATTERNS: tuple[Pattern[str], ...] = (
    re.compile(r"^GDI_LH1_(\d{14})\.xml$", re.IGNORECASE),
    re.compile(r"^GDI_LH1_MMS_(\d{14})\.xml$", re.IGNORECASE),
    re.compile(r"^GDI_LH1_FLORES_(\d{14})\.xml$", re.IGNORECASE),
    re.compile(r"^GDI_LH1_HNE_(\d{14})\.xml$", re.IGNORECASE),
    re.compile(r"^GDI_REGEN_LH1_(\d{14})\.xml$", re.IGNORECASE),
)
GDI_REPROCESS_LH1_PATTERN = re.compile(
    r"^GDI_REPROCESS_LH1_(\d{14})\.xml$", re.IGNORECASE
)
GDI_REPROCESS_LH1_MMS_PATTERN = re.compile(
    r"^GDI_REPROCESS_LH1_MMS_(\d{14})\.xml$", re.IGNORECASE
)
GDI_REPROCESS_LH1_FLORES_PATTERN = re.compile(
    r"^GDI_REPROCESS_LH1_FLORES_(\d{14})\.xml$", re.IGNORECASE
)
GDI_REPROCESS_LH1_HNE_PATTERN = re.compile(
    r"^GDI_REPROCESS_LH1_HNE_(\d{14})\.xml$", re.IGNORECASE
)
GDI_MANUAL_PATTERN = re.compile(r"^GDI_MANUAL_(\d{14})\.csv$", re.IGNORECASE)
GDI_MANUAL_PATIENT_PATTERN = re.compile(
    r"^GDI_MANUAL_PATIENT_(\d{14})\.csv$", re.IGNORECASE
)
GDI_REPROCESS_MANUAL_PATTERN = re.compile(
    r"^GDI_REPROCESS_MANUAL_(\d{14})\.csv$", re.IGNORECASE
)
GDI_REPROCESS_MANUAL_PATIENT_PATTERN = re.compile(
    r"^GDI_REPROCESS_MANUAL_PATIENT_(\d{14})\.csv$", re.IGNORECASE
)
GDI_MBI_PATTERN = re.compile(r"^LumeLight\.ClaimFeed\.(\d{14})\.mbi$", re.IGNORECASE)
HSAB_HB1_PATTERN = re.compile(r"^HB1_HSAB_CLAIMS_(\d{14})\.xml$", re.IGNORECASE)
HSAB_HB2_PATTERN = re.compile(r"^HB2_HSAB_CLAIMS_(\d{14})\.xml$", re.IGNORECASE)

# EnrollmentXO filename patterns (runtime timestamp is a digit run, often 17 digits).
ABG_EXPORT_MBI_PATTERN = re.compile(
    r"^Export_(?P<runtime>\d+)_(?P<rest>Cafeteria_XML_.+)\.mbi$",
    re.IGNORECASE,
)
ABG_EXCEPTION_REPORT_PATTERN = re.compile(
    r"^ExceptionReport_(?P<runtime>\d+)_(?P<rest>Cafeteria_XML_.+)\.csv$",
    re.IGNORECASE,
)
ABG_CHANGE_REPORT_PATTERN = re.compile(
    r"^ChangeReport_(?P<runtime>\d+)_(?P<rest>Cafeteria_XML_.+)\.csv$",
    re.IGNORECASE,
)
ENROLLMENT_GDI_WEXHEALTH_PATTERN = re.compile(
    r"^GDI_WEXHealth_(?P<runtime>\d+)\.txt$",
    re.IGNORECASE,
)
ENROLLMENT_GDI_CHANGE_REPORT_PATTERN = re.compile(
    r"^GDI_ChangeReport_GDI_EN_ALL_(?P<rest>.+)_(?P<runtime>\d+)\.csv$",
    re.IGNORECASE,
)
ENROLLMENT_GDI_EXCEPTION_REPORT_PATTERN = re.compile(
    r"^GDI_ExceptionReport_GDI_EN_ALL_(?P<rest>.+)_(?P<runtime>\d+)\.csv$",
    re.IGNORECASE,
)
ENROLLMENT_HSAB_IMPORT_PATTERN = re.compile(
    r"^(?P<rest>.+)_(?P<runtime>\d+)\.txt$",
    re.IGNORECASE,
)
ENROLLMENT_HSAB_CHANGE_REPORT_PATTERN = re.compile(
    r"^HSAB_ChangeReport_(?P<rest>.+)_(?P<runtime>\d+)\.csv$",
    re.IGNORECASE,
)
ENROLLMENT_HSAB_EXCEPTION_REPORT_PATTERN = re.compile(
    r"^HSAB_ExceptionReport_(?P<rest>.+)_(?P<runtime>\d+)\.csv$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class FilenameRule:
    """Maps a filename pattern to format and ignore-rule key."""

    pattern: Pattern[str]
    normalized_template: str
    file_format: FileFormat
    ignore_rule_key: str
    delimiter: str | None = None
    has_header: bool = False
    compare_trailing_empty_fields: bool = True
    uses_named_identity_groups: bool = False


@dataclass(frozen=True)
class OutputFolderProfile:
    """Profile for one supported output folder under a TPA."""

    output_type: OutputType
    filename_rules: tuple[FilenameRule, ...]


@dataclass(frozen=True)
class SolutionProfile:
    """Internal registry entry for one solution + verification type."""

    solution_type: SolutionType
    verification_type: VerificationType
    output_folders: tuple[OutputFolderProfile, ...]
    supported_extensions: frozenset[str]

    def supported_output_folder_names(self) -> frozenset[str]:
        """Return lower-case supported output folder names."""
        return frozenset(folder.output_type.value.lower() for folder in self.output_folders)

    def find_filename_rule(self, output_type: OutputType, filename: str) -> FilenameRule | None:
        """Return the matching filename rule for an output folder, if any."""
        for folder_profile in self.output_folders:
            if folder_profile.output_type != output_type:
                continue
            for rule in folder_profile.filename_rules:
                if rule.pattern.match(filename):
                    return rule
        return None


# Keep alias name for gradual migration in helper signatures.
TpaProfile = SolutionProfile


def _claims_xml_rule(pattern: Pattern[str], template: str) -> FilenameRule:
    return FilenameRule(
        pattern=pattern,
        normalized_template=template,
        file_format=FileFormat.XML,
        ignore_rule_key="lh1_xml_paths",
    )


CLAIMS_XO_GDI_PROFILE = SolutionProfile(
    solution_type=SolutionType.CLAIMS_XO,
    verification_type=VerificationType.GDI,
    supported_extensions=CLAIMS_XO_EXTENSIONS,
    output_folders=(
        OutputFolderProfile(
            output_type=OutputType.LH1,
            filename_rules=(
                _claims_xml_rule(GDI_LH1_PATTERNS[0], f"GDI_LH1_{DATETIME_TOKEN}.xml"),
                _claims_xml_rule(GDI_LH1_PATTERNS[1], f"GDI_LH1_MMS_{DATETIME_TOKEN}.xml"),
                _claims_xml_rule(GDI_LH1_PATTERNS[2], f"GDI_LH1_FLORES_{DATETIME_TOKEN}.xml"),
                _claims_xml_rule(GDI_LH1_PATTERNS[3], f"GDI_LH1_HNE_{DATETIME_TOKEN}.xml"),
                _claims_xml_rule(GDI_LH1_PATTERNS[4], f"GDI_REGEN_LH1_{DATETIME_TOKEN}.xml"),
                _claims_xml_rule(
                    GDI_REPROCESS_LH1_PATTERN, f"GDI_REPROCESS_LH1_{DATETIME_TOKEN}.xml"
                ),
                _claims_xml_rule(
                    GDI_REPROCESS_LH1_MMS_PATTERN,
                    f"GDI_REPROCESS_LH1_MMS_{DATETIME_TOKEN}.xml",
                ),
                _claims_xml_rule(
                    GDI_REPROCESS_LH1_FLORES_PATTERN,
                    f"GDI_REPROCESS_LH1_FLORES_{DATETIME_TOKEN}.xml",
                ),
                _claims_xml_rule(
                    GDI_REPROCESS_LH1_HNE_PATTERN,
                    f"GDI_REPROCESS_LH1_HNE_{DATETIME_TOKEN}.xml",
                ),
            ),
        ),
        OutputFolderProfile(
            output_type=OutputType.MANUAL,
            filename_rules=(
                FilenameRule(
                    pattern=GDI_MANUAL_PATTERN,
                    normalized_template=f"GDI_MANUAL_{DATETIME_TOKEN}.csv",
                    file_format=FileFormat.CSV,
                    ignore_rule_key="manual_csv_columns",
                    delimiter=COMMA_DELIMITER,
                    has_header=True,
                ),
                FilenameRule(
                    pattern=GDI_MANUAL_PATIENT_PATTERN,
                    normalized_template=f"GDI_MANUAL_PATIENT_{DATETIME_TOKEN}.csv",
                    file_format=FileFormat.CSV,
                    ignore_rule_key="patient_manual_csv_columns",
                    delimiter=COMMA_DELIMITER,
                    has_header=True,
                ),
                FilenameRule(
                    pattern=GDI_REPROCESS_MANUAL_PATTERN,
                    normalized_template=f"GDI_REPROCESS_MANUAL_{DATETIME_TOKEN}.csv",
                    file_format=FileFormat.CSV,
                    ignore_rule_key="manual_csv_columns",
                    delimiter=COMMA_DELIMITER,
                    has_header=True,
                ),
                FilenameRule(
                    pattern=GDI_REPROCESS_MANUAL_PATIENT_PATTERN,
                    normalized_template=f"GDI_REPROCESS_MANUAL_PATIENT_{DATETIME_TOKEN}.csv",
                    file_format=FileFormat.CSV,
                    ignore_rule_key="patient_manual_csv_columns",
                    delimiter=COMMA_DELIMITER,
                    has_header=True,
                ),
            ),
        ),
        OutputFolderProfile(
            output_type=OutputType.ALG,
            filename_rules=(
                FilenameRule(
                    pattern=GDI_MBI_PATTERN,
                    normalized_template=f"LumeLight.ClaimFeed.{DATETIME_TOKEN}.mbi",
                    file_format=FileFormat.MBI,
                    ignore_rule_key="mbi_field_positions",
                    delimiter=MBI_DELIMITER,
                    has_header=False,
                    compare_trailing_empty_fields=True,
                ),
            ),
        ),
    ),
)

CLAIMS_XO_HSAB_PROFILE = SolutionProfile(
    solution_type=SolutionType.CLAIMS_XO,
    verification_type=VerificationType.HSAB,
    supported_extensions=CLAIMS_XO_EXTENSIONS,
    output_folders=(
        OutputFolderProfile(
            output_type=OutputType.WEX,
            filename_rules=(
                FilenameRule(
                    pattern=HSAB_HB1_PATTERN,
                    normalized_template=f"HB1_HSAB_CLAIMS_{DATETIME_TOKEN}.xml",
                    file_format=FileFormat.XML,
                    ignore_rule_key="wex_xml_paths",
                ),
                FilenameRule(
                    pattern=HSAB_HB2_PATTERN,
                    normalized_template=f"HB2_HSAB_CLAIMS_{DATETIME_TOKEN}.xml",
                    file_format=FileFormat.XML,
                    ignore_rule_key="wex_xml_paths",
                ),
            ),
        ),
    ),
)

ENROLLMENT_XO_ABG_PROFILE = SolutionProfile(
    solution_type=SolutionType.ENROLLMENT_XO,
    verification_type=VerificationType.ABG,
    supported_extensions=ENROLLMENT_XO_EXTENSIONS,
    output_folders=(
        OutputFolderProfile(
            output_type=OutputType.ALEGEUS,
            filename_rules=(
                FilenameRule(
                    pattern=ABG_EXPORT_MBI_PATTERN,
                    normalized_template=f"Export_{RUNTIME_TIMESTAMP_TOKEN}_{{rest}}.mbi",
                    file_format=FileFormat.DELIMITED_TEXT,
                    ignore_rule_key="alegeus_mbi_field_positions",
                    delimiter=COMMA_DELIMITER,
                    has_header=False,
                    uses_named_identity_groups=True,
                ),
            ),
        ),
        OutputFolderProfile(
            output_type=OutputType.REPORTS,
            filename_rules=(
                FilenameRule(
                    pattern=ABG_EXCEPTION_REPORT_PATTERN,
                    normalized_template=(
                        f"ExceptionReport_{RUNTIME_TIMESTAMP_TOKEN}_{{rest}}.csv"
                    ),
                    file_format=FileFormat.DELIMITED_TEXT,
                    ignore_rule_key="report_csv_columns",
                    delimiter=COMMA_DELIMITER,
                    has_header=True,
                    uses_named_identity_groups=True,
                ),
                FilenameRule(
                    pattern=ABG_CHANGE_REPORT_PATTERN,
                    normalized_template=(
                        f"ChangeReport_{RUNTIME_TIMESTAMP_TOKEN}_{{rest}}.csv"
                    ),
                    file_format=FileFormat.DELIMITED_TEXT,
                    ignore_rule_key="report_csv_columns",
                    delimiter=COMMA_DELIMITER,
                    has_header=True,
                    uses_named_identity_groups=True,
                ),
            ),
        ),
    ),
)

ENROLLMENT_XO_GDI_PROFILE = SolutionProfile(
    solution_type=SolutionType.ENROLLMENT_XO,
    verification_type=VerificationType.GDI,
    supported_extensions=ENROLLMENT_XO_EXTENSIONS,
    output_folders=(
        OutputFolderProfile(
            output_type=OutputType.WEX_HEALTH,
            filename_rules=(
                FilenameRule(
                    pattern=ENROLLMENT_GDI_WEXHEALTH_PATTERN,
                    normalized_template=f"GDI_WEXHealth_{RUNTIME_TIMESTAMP_TOKEN}.txt",
                    file_format=FileFormat.DELIMITED_TEXT,
                    ignore_rule_key="wexhealth_field_positions",
                    delimiter=PIPE_DELIMITER,
                    has_header=False,
                    compare_trailing_empty_fields=True,
                ),
            ),
        ),
        OutputFolderProfile(
            output_type=OutputType.REPORTS,
            filename_rules=(
                FilenameRule(
                    pattern=ENROLLMENT_GDI_CHANGE_REPORT_PATTERN,
                    normalized_template=(
                        f"GDI_ChangeReport_GDI_EN_ALL_{{rest}}_{RUNTIME_TIMESTAMP_TOKEN}.csv"
                    ),
                    file_format=FileFormat.DELIMITED_TEXT,
                    ignore_rule_key="report_csv_columns",
                    delimiter=COMMA_DELIMITER,
                    has_header=True,
                    uses_named_identity_groups=True,
                ),
                FilenameRule(
                    pattern=ENROLLMENT_GDI_EXCEPTION_REPORT_PATTERN,
                    normalized_template=(
                        f"GDI_ExceptionReport_GDI_EN_ALL_{{rest}}_{RUNTIME_TIMESTAMP_TOKEN}.csv"
                    ),
                    file_format=FileFormat.DELIMITED_TEXT,
                    ignore_rule_key="report_csv_columns",
                    delimiter=COMMA_DELIMITER,
                    has_header=True,
                    uses_named_identity_groups=True,
                ),
            ),
        ),
    ),
)

ENROLLMENT_XO_HSAB_PROFILE = SolutionProfile(
    solution_type=SolutionType.ENROLLMENT_XO,
    verification_type=VerificationType.HSAB,
    supported_extensions=ENROLLMENT_XO_EXTENSIONS,
    output_folders=(
        OutputFolderProfile(
            output_type=OutputType.HSAB_ENROLLMENT_IMPORT,
            filename_rules=(
                FilenameRule(
                    pattern=ENROLLMENT_HSAB_IMPORT_PATTERN,
                    normalized_template=f"{{rest}}_{RUNTIME_TIMESTAMP_TOKEN}.txt",
                    file_format=FileFormat.DELIMITED_TEXT,
                    ignore_rule_key="enrollment_import_field_positions",
                    delimiter=COMMA_DELIMITER,
                    has_header=False,
                    uses_named_identity_groups=True,
                ),
            ),
        ),
        OutputFolderProfile(
            output_type=OutputType.REPORTS,
            filename_rules=(
                FilenameRule(
                    pattern=ENROLLMENT_HSAB_CHANGE_REPORT_PATTERN,
                    normalized_template=(
                        f"HSAB_ChangeReport_{{rest}}_{RUNTIME_TIMESTAMP_TOKEN}.csv"
                    ),
                    file_format=FileFormat.DELIMITED_TEXT,
                    ignore_rule_key="report_csv_columns",
                    delimiter=COMMA_DELIMITER,
                    has_header=True,
                    uses_named_identity_groups=True,
                ),
                FilenameRule(
                    pattern=ENROLLMENT_HSAB_EXCEPTION_REPORT_PATTERN,
                    normalized_template=(
                        f"HSAB_ExceptionReport_{{rest}}_{RUNTIME_TIMESTAMP_TOKEN}.csv"
                    ),
                    file_format=FileFormat.DELIMITED_TEXT,
                    ignore_rule_key="report_csv_columns",
                    delimiter=COMMA_DELIMITER,
                    has_header=True,
                    uses_named_identity_groups=True,
                ),
            ),
        ),
    ),
)

CLAIMS_XO_PROFILES: dict[VerificationType, SolutionProfile] = {
    VerificationType.GDI: CLAIMS_XO_GDI_PROFILE,
    VerificationType.HSAB: CLAIMS_XO_HSAB_PROFILE,
}

ENROLLMENT_XO_PROFILES: dict[VerificationType, SolutionProfile] = {
    VerificationType.ABG: ENROLLMENT_XO_ABG_PROFILE,
    VerificationType.GDI: ENROLLMENT_XO_GDI_PROFILE,
    VerificationType.HSAB: ENROLLMENT_XO_HSAB_PROFILE,
}

SOLUTION_PROFILES: dict[SolutionType, dict[VerificationType, SolutionProfile]] = {
    SolutionType.CLAIMS_XO: CLAIMS_XO_PROFILES,
    SolutionType.ENROLLMENT_XO: ENROLLMENT_XO_PROFILES,
}

# Backward-compatible aliases used by older ClaimsXO call sites during migration.
GDI_PROFILE = CLAIMS_XO_GDI_PROFILE
HSAB_PROFILE = CLAIMS_XO_HSAB_PROFILE
TPA_PROFILES = CLAIMS_XO_PROFILES


def get_solution_profile(
    solution_type: SolutionType,
    verification_type: VerificationType,
) -> SolutionProfile:
    """Return the profile for a solution and verification type pair."""
    solution_map = SOLUTION_PROFILES.get(solution_type)
    if solution_map is None:
        raise ValueError(f"Unsupported solution type: {solution_type}")
    try:
        return solution_map[verification_type]
    except KeyError as error:
        raise ValueError(
            f"Unsupported verification type {verification_type.value} "
            f"for solution {solution_type.value}."
        ) from error


def get_tpa_profile(verification_type: VerificationType) -> SolutionProfile:
    """Return ClaimsXO profile for a verification type (legacy helper)."""
    return get_solution_profile(SolutionType.CLAIMS_XO, verification_type)


def allowed_verification_types(solution_type: SolutionType) -> frozenset[VerificationType]:
    """Return verification types allowed for a solution."""
    if solution_type == SolutionType.CLAIMS_XO:
        return CLAIMS_XO_VERIFICATION_TYPES
    if solution_type == SolutionType.ENROLLMENT_XO:
        return ENROLLMENT_XO_VERIFICATION_TYPES
    return frozenset()
