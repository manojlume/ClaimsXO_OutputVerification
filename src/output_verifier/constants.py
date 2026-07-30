"""Application constants and TPA profile definitions."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Pattern


APPLICATION_NAME = "output-verifier"
APPLICATION_VERSION = "1.0.0"
SOLUTION_TYPE = "ClaimsXO"
DATETIME_TOKEN = "<datetime>"
DATETIME_DIGIT_COUNT = 14
DATETIME_PLACEHOLDER_PATTERN = re.compile(r"\d{14}")

MAX_REPORTED_DIFFERENCES = 2
MAX_LOGGED_VALUE_LENGTH = 200


class VerificationType(str, Enum):
    """Supported verification (TPA) types."""

    GDI = "GDI"
    HSAB = "HSAB"


class OutputType(str, Enum):
    """Supported output folder types."""

    LH1 = "LH1"
    MANUAL = "manual"
    ALG = "ALG"
    WEX = "WEX"


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

SUPPORTED_EXTENSIONS: frozenset[str] = frozenset({".xml", ".csv", ".mbi"})

GDI_OUTPUT_TYPES: frozenset[str] = frozenset(
    {OutputType.LH1.value.lower(), OutputType.MANUAL.value.lower(), OutputType.ALG.value.lower()}
)

HSAB_OUTPUT_TYPES: frozenset[str] = frozenset({OutputType.WEX.value.lower()})

OUTPUT_TYPE_CANONICAL: dict[str, OutputType] = {
    "lh1": OutputType.LH1,
    "manual": OutputType.MANUAL,
    "alg": OutputType.ALG,
    "wex": OutputType.WEX,
}


# Filename patterns keep the 14-digit datetime as a capture group.
GDI_LH1_PATTERNS: tuple[Pattern[str], ...] = (
    re.compile(r"^GDI_LH1_(\d{14})\.xml$", re.IGNORECASE),
    re.compile(r"^GDI_LH1_MMS_(\d{14})\.xml$", re.IGNORECASE),
    re.compile(r"^GDI_LH1_FLORES_(\d{14})\.xml$", re.IGNORECASE),
    re.compile(r"^GDI_LH1_HNE_(\d{14})\.xml$", re.IGNORECASE),
    re.compile(r"^GDI_REGEN_LH1_(\d{14})\.xml$", re.IGNORECASE),
)

GDI_MANUAL_PATTERN = re.compile(r"^GDI_MANUAL_(\d{14})\.csv$", re.IGNORECASE)
GDI_MANUAL_PATIENT_PATTERN = re.compile(
    r"^GDI_MANUAL_PATIENT_(\d{14})\.csv$", re.IGNORECASE
)
GDI_MBI_PATTERN = re.compile(r"^LumeLight\.ClaimFeed\.(\d{14})\.mbi$", re.IGNORECASE)

HSAB_HB1_PATTERN = re.compile(r"^HB1_HSAB_CLAIMS_(\d{14})\.xml$", re.IGNORECASE)
HSAB_HB2_PATTERN = re.compile(r"^HB2_HSAB_CLAIMS_(\d{14})\.xml$", re.IGNORECASE)

MBI_DELIMITER = "|"

VALID_LOG_LEVELS: frozenset[str] = frozenset(
    {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"}
)

HEX_COLOR_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")


@dataclass(frozen=True)
class FilenameRule:
    """Maps a filename pattern to format and ignore-rule key."""

    pattern: Pattern[str]
    normalized_template: str
    file_format: FileFormat
    ignore_rule_key: str


@dataclass(frozen=True)
class OutputFolderProfile:
    """Profile for one supported output folder under a TPA."""

    output_type: OutputType
    filename_rules: tuple[FilenameRule, ...]


@dataclass(frozen=True)
class TpaProfile:
    """Internal registry entry for a supported TPA."""

    verification_type: VerificationType
    output_folders: tuple[OutputFolderProfile, ...]

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


GDI_PROFILE = TpaProfile(
    verification_type=VerificationType.GDI,
    output_folders=(
        OutputFolderProfile(
            output_type=OutputType.LH1,
            filename_rules=(
                FilenameRule(
                    pattern=GDI_LH1_PATTERNS[0],
                    normalized_template=f"GDI_LH1_{DATETIME_TOKEN}.xml",
                    file_format=FileFormat.XML,
                    ignore_rule_key="lh1_xml_paths",
                ),
                FilenameRule(
                    pattern=GDI_LH1_PATTERNS[1],
                    normalized_template=f"GDI_LH1_MMS_{DATETIME_TOKEN}.xml",
                    file_format=FileFormat.XML,
                    ignore_rule_key="lh1_xml_paths",
                ),
                FilenameRule(
                    pattern=GDI_LH1_PATTERNS[2],
                    normalized_template=f"GDI_LH1_FLORES_{DATETIME_TOKEN}.xml",
                    file_format=FileFormat.XML,
                    ignore_rule_key="lh1_xml_paths",
                ),
                FilenameRule(
                    pattern=GDI_LH1_PATTERNS[3],
                    normalized_template=f"GDI_LH1_HNE_{DATETIME_TOKEN}.xml",
                    file_format=FileFormat.XML,
                    ignore_rule_key="lh1_xml_paths",
                ),
                FilenameRule(
                    pattern=GDI_LH1_PATTERNS[4],
                    normalized_template=f"GDI_REGEN_LH1_{DATETIME_TOKEN}.xml",
                    file_format=FileFormat.XML,
                    ignore_rule_key="lh1_xml_paths",
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
                ),
                FilenameRule(
                    pattern=GDI_MANUAL_PATIENT_PATTERN,
                    normalized_template=f"GDI_MANUAL_PATIENT_{DATETIME_TOKEN}.csv",
                    file_format=FileFormat.CSV,
                    ignore_rule_key="patient_manual_csv_columns",
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
                ),
            ),
        ),
    ),
)

HSAB_PROFILE = TpaProfile(
    verification_type=VerificationType.HSAB,
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

TPA_PROFILES: dict[VerificationType, TpaProfile] = {
    VerificationType.GDI: GDI_PROFILE,
    VerificationType.HSAB: HSAB_PROFILE,
}


def get_tpa_profile(verification_type: VerificationType) -> TpaProfile:
    """Return the TPA profile for a verification type."""
    try:
        return TPA_PROFILES[verification_type]
    except KeyError as error:
        raise ValueError(f"Unsupported verification type: {verification_type}") from error
