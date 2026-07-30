"""Filename normalization and recognition helpers."""

from __future__ import annotations

from pathlib import Path

from output_verifier.constants import (
    DATETIME_PLACEHOLDER_PATTERN,
    DATETIME_TOKEN,
    FilenameRule,
    OutputType,
    SUPPORTED_EXTENSIONS,
    TpaProfile,
)


def has_supported_extension(filename: str) -> bool:
    """Return True when the filename extension is a supported output type."""
    extension = Path(filename).suffix.lower()
    return extension in SUPPORTED_EXTENSIONS


def normalize_filename_identity(filename: str) -> str:
    """Replace the first 14-digit datetime token with the standard placeholder."""
    return DATETIME_PLACEHOLDER_PATTERN.sub(DATETIME_TOKEN, filename, count=1)


def build_normalized_identity_from_rule(rule: FilenameRule) -> str:
    """Return the canonical normalized identity for a filename rule."""
    return rule.normalized_template


def match_filename_rule(
    profile: TpaProfile,
    output_type: OutputType,
    filename: str,
) -> FilenameRule | None:
    """Return the matching filename rule for a file under an output folder."""
    return profile.find_filename_rule(output_type, filename)


def is_supported_filename(
    profile: TpaProfile,
    output_type: OutputType,
    filename: str,
) -> bool:
    """Return True when the filename matches a supported pattern for the output type."""
    return match_filename_rule(profile, output_type, filename) is not None
