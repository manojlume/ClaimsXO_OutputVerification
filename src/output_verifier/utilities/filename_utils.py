"""Filename normalization and recognition helpers."""

from __future__ import annotations

from pathlib import Path

from output_verifier.constants import (
    DATETIME_PLACEHOLDER_PATTERN,
    DATETIME_TOKEN,
    FilenameRule,
    OutputType,
    SolutionProfile,
)


def has_supported_extension(filename: str, supported_extensions: frozenset[str]) -> bool:
    """Return True when the filename extension is supported for the active profile."""
    extension = Path(filename).suffix.lower()
    return extension in supported_extensions


def normalize_filename_identity(filename: str) -> str:
    """Replace the first 14-digit datetime token with the standard placeholder."""
    return DATETIME_PLACEHOLDER_PATTERN.sub(DATETIME_TOKEN, filename, count=1)


def build_normalized_identity_from_rule(rule: FilenameRule, filename: str) -> str:
    """Build normalized identity for a matched filename rule."""
    if not rule.uses_named_identity_groups:
        return rule.normalized_template

    match = rule.pattern.match(filename)
    if match is None:
        return rule.normalized_template

    values = {
        key: value
        for key, value in match.groupdict().items()
        if key != "runtime" and value is not None
    }
    try:
        return rule.normalized_template.format(**values)
    except (KeyError, ValueError):
        return rule.normalized_template


def match_filename_rule(
    profile: SolutionProfile,
    output_type: OutputType,
    filename: str,
) -> FilenameRule | None:
    """Return the matching filename rule for a file under an output folder."""
    return profile.find_filename_rule(output_type, filename)


def is_supported_filename(
    profile: SolutionProfile,
    output_type: OutputType,
    filename: str,
) -> bool:
    """Return True when the filename matches a supported pattern for the output type."""
    return match_filename_rule(profile, output_type, filename) is not None


def immediate_parent_folder_name(folder_path: Path) -> str:
    """Return the immediate parent folder name from an Actual/Expected root path."""
    return folder_path.name


def build_run_artifact_filename(
    *,
    prefix: str,
    solution_type: str,
    verification_type: str,
    immediate_parent: str,
    timestamp: str,
    extension: str,
) -> str:
    """
    Build a run artifact filename.

    Example:
      VerificationReport_ClaimsXO_GDI_20260612_000022_fullrun_20260730133505.xlsx
      VerificationLog_EnrollmentXO_ABG_20260612_000022_fullrun_20260730133505.Log
    """
    extension_with_dot = extension if extension.startswith(".") else f".{extension}"
    return (
        f"{prefix}_{solution_type}_{verification_type}_{immediate_parent}_{timestamp}"
        f"{extension_with_dot}"
    )
