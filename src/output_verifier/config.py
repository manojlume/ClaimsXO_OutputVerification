"""Configuration validation helpers and exceptions."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from lxml import etree

from output_verifier.constants import (
    HEX_COLOR_PATTERN,
    SolutionType,
    VALID_LOG_LEVELS,
    VerificationType,
    allowed_verification_types,
)


class ConfigurationError(Exception):
    """Raised when configuration is invalid or cannot be applied."""


def parse_solution_type(value: Any) -> SolutionType:
    """Parse and validate a solution type string."""
    if not isinstance(value, str) or not value.strip():
        raise ConfigurationError("solution_type is required and must be a string.")
    normalized = value.strip()
    lookup = {item.value.lower(): item for item in SolutionType}
    solution = lookup.get(normalized.lower())
    if solution is None:
        raise ConfigurationError(
            f"Unsupported solution type: {value}. "
            "Supported values: ClaimsXO, EnrollmentXO, TransactionXO."
        )
    return solution


def parse_verification_type(value: str) -> VerificationType:
    """Parse and validate a verification type string."""
    normalized = str(value).strip().upper()
    try:
        return VerificationType(normalized)
    except ValueError as error:
        raise ConfigurationError(
            f"Unsupported verification type: {value}. Supported values: ABG, GDI, HSAB."
        ) from error


def validate_solution_verification_pair(
    solution_type: SolutionType,
    verification_type: VerificationType,
) -> None:
    """Ensure verification type is allowed for the selected solution."""
    allowed = allowed_verification_types(solution_type)
    if verification_type not in allowed:
        allowed_names = ", ".join(sorted(item.value for item in allowed))
        raise ConfigurationError(
            f"Unsupported verification type {verification_type.value} for "
            f"solution {solution_type.value}. Allowed: {allowed_names}."
        )


def validate_hex_color(color_name: str, value: Any) -> str:
    """Validate a #RRGGBB status color."""
    if not isinstance(value, str) or not HEX_COLOR_PATTERN.match(value):
        raise ConfigurationError(
            f"status_colors.{color_name} must be a #RRGGBB hex color, found: {value!r}."
        )
    return value


def validate_log_level(value: Any) -> str:
    """Validate and normalize a logging level name."""
    if not isinstance(value, str):
        raise ConfigurationError(f"logging.level must be a string, found: {value!r}.")
    normalized = value.strip().upper()
    if normalized not in VALID_LOG_LEVELS:
        raise ConfigurationError(
            f"Invalid log level: {value!r}. Valid levels: {', '.join(sorted(VALID_LOG_LEVELS))}."
        )
    return normalized


def validate_positive_integer(field_name: str, value: Any) -> int:
    """Validate that a value is a positive integer."""
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ConfigurationError(f"{field_name} must be a positive integer, found: {value!r}.")
    return value


def validate_non_negative_integer(field_name: str, value: Any) -> int:
    """Validate that a value is zero or a positive integer."""
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ConfigurationError(
            f"{field_name} must be zero or a positive integer, found: {value!r}."
        )
    return value


def validate_timestamp_format(value: Any) -> str:
    """Validate that a timestamp format string is usable by datetime.strftime."""
    if not isinstance(value, str) or not value.strip():
        raise ConfigurationError("report.timestamp_format must be a non-empty string.")
    try:
        datetime.now().strftime(value)
    except (ValueError, TypeError) as error:
        raise ConfigurationError(f"Invalid report.timestamp_format: {value!r}.") from error
    return value


def validate_string_list(field_name: str, value: Any) -> tuple[str, ...]:
    """Validate a YAML list of strings."""
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ConfigurationError(f"{field_name} must be a list of strings.")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise ConfigurationError(f"{field_name} must contain only strings, found: {item!r}.")
        result.append(item)
    return tuple(result)


def validate_field_positions(field_name: str, value: Any) -> tuple[int, ...]:
    """Validate one-based ignore field positions."""
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ConfigurationError(f"{field_name} must be a list of integers.")

    positions: list[int] = []
    seen: set[int] = set()
    for item in value:
        if not isinstance(item, int) or isinstance(item, bool) or item <= 0:
            raise ConfigurationError(
                f"Invalid ignored field position in {field_name}: {item!r}. "
                "Positions must be positive integers (one-based)."
            )
        if item in seen:
            continue
        seen.add(item)
        positions.append(item)
    return tuple(positions)


def validate_mbi_field_positions(value: Any) -> tuple[int, ...]:
    """Validate one-based MBI ignore field positions."""
    return validate_field_positions("ignore_rules.*.mbi_field_positions", value)


def validate_character_ranges(field_name: str, value: Any) -> tuple[tuple[int, int], ...]:
    """
    Validate one-based inclusive character ranges from YAML.

    Accepted forms: "45" or "20-27".
    """
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ConfigurationError(f"{field_name} must be a list of range strings.")

    ranges: list[tuple[int, int]] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ConfigurationError(
                f"Invalid character range in {field_name}: {item!r}. "
                'Use forms like "45" or "20-27".'
            )
        token = item.strip()
        if "-" in token:
            parts = token.split("-", 1)
            if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
                raise ConfigurationError(
                    f"Invalid character range in {field_name}: {item!r}. "
                    'Use forms like "45" or "20-27".'
                )
            start = int(parts[0])
            end = int(parts[1])
        elif token.isdigit():
            start = end = int(token)
        else:
            raise ConfigurationError(
                f"Invalid character range in {field_name}: {item!r}. "
                'Use forms like "45" or "20-27".'
            )
        if start <= 0 or end <= 0 or end < start:
            raise ConfigurationError(
                f"Invalid character range in {field_name}: {item!r}. "
                "Positions must be positive one-based inclusive ranges."
            )
        ranges.append((start, end))
    return tuple(ranges)


def validate_xpath_list(field_name: str, paths: tuple[str, ...]) -> tuple[str, ...]:
    """Validate that configured XPath expressions are syntactically valid."""
    for xpath_expression in paths:
        try:
            etree.XPath(xpath_expression)
        except etree.XPathSyntaxError as error:
            raise ConfigurationError(
                f"Invalid XPath in {field_name}: {xpath_expression!r}. {error}"
            ) from error
    return paths


def require_existing_directory(field_name: str, path: Path) -> Path:
    """Require that a path exists and is a readable directory."""
    if not path.exists():
        raise ConfigurationError(f"{field_name} does not exist: {path}")
    if not path.is_dir():
        raise ConfigurationError(f"{field_name} is not a directory: {path}")
    return path.resolve()


def ensure_creatable_directory(field_name: str, path: Path) -> Path:
    """Ensure a directory exists or can be created."""
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise ConfigurationError(f"Cannot create {field_name}: {path}. {error}") from error
    if not path.is_dir():
        raise ConfigurationError(f"{field_name} is not a directory: {path}")
    return path.resolve()
