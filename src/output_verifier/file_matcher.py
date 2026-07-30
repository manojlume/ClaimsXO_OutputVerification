"""Match expected and actual files by normalized filename identity."""

from __future__ import annotations

import logging
from collections import defaultdict
from pathlib import Path

from output_verifier.constants import SolutionProfile
from output_verifier.models import DiscoveredOutput, FileIdentity, MatchedFilePair
from output_verifier.utilities.filename_utils import (
    build_normalized_identity_from_rule,
    match_filename_rule,
    normalize_filename_identity,
)

LOGGER = logging.getLogger(__name__)


def classify_file(
    file_path: Path,
    discovered: DiscoveredOutput,
    profile: SolutionProfile,
) -> FileIdentity:
    """Classify a file into a normalized identity and optional format rule."""
    filename = file_path.name
    rule = match_filename_rule(profile, discovered.scenario_key.output_type, filename)
    if rule is None:
        return FileIdentity(
            normalized_name=normalize_filename_identity(filename),
            original_filename=filename,
            file_path=file_path,
            file_format=None,
            ignore_rule_key=None,
            is_valid_pattern=False,
        )
    return FileIdentity(
        normalized_name=build_normalized_identity_from_rule(rule, filename),
        original_filename=filename,
        file_path=file_path,
        file_format=rule.file_format,
        ignore_rule_key=rule.ignore_rule_key,
        is_valid_pattern=True,
        delimiter=rule.delimiter,
        has_header=rule.has_header,
        compare_trailing_empty_fields=rule.compare_trailing_empty_fields,
    )


def match_files_for_output(
    discovered: DiscoveredOutput,
    profile: SolutionProfile,
) -> list[MatchedFilePair]:
    """
    Match expected and actual files for one scenario/run/output location.

    Files are grouped by normalized filename identity, sorted by original
    filename, and paired by position within each identity group.
    """
    expected_identities = [
        classify_file(path, discovered, profile) for path in discovered.expected_files
    ]
    actual_identities = [
        classify_file(path, discovered, profile) for path in discovered.actual_files
    ]

    expected_groups: dict[str, list[FileIdentity]] = defaultdict(list)
    actual_groups: dict[str, list[FileIdentity]] = defaultdict(list)

    for identity in expected_identities:
        expected_groups[identity.normalized_name].append(identity)
    for identity in actual_identities:
        actual_groups[identity.normalized_name].append(identity)

    for group in expected_groups.values():
        group.sort(key=lambda item: item.original_filename.lower())
    for group in actual_groups.values():
        group.sort(key=lambda item: item.original_filename.lower())

    all_identities = sorted(set(expected_groups.keys()) | set(actual_groups.keys()))
    pairs: list[MatchedFilePair] = []

    for normalized_name in all_identities:
        expected_list = expected_groups.get(normalized_name, [])
        actual_list = actual_groups.get(normalized_name, [])
        pair_count = max(len(expected_list), len(actual_list))

        for index in range(pair_count):
            expected_item = expected_list[index] if index < len(expected_list) else None
            actual_item = actual_list[index] if index < len(actual_list) else None
            reference = expected_item or actual_item
            assert reference is not None

            pairs.append(
                MatchedFilePair(
                    scenario_key=discovered.scenario_key,
                    normalized_identity=normalized_name,
                    expected_file=expected_item.file_path if expected_item else None,
                    actual_file=actual_item.file_path if actual_item else None,
                    file_format=reference.file_format,
                    ignore_rule_key=reference.ignore_rule_key,
                    is_valid_pattern=reference.is_valid_pattern,
                    delimiter=reference.delimiter,
                    has_header=reference.has_header,
                    compare_trailing_empty_fields=reference.compare_trailing_empty_fields,
                )
            )

            LOGGER.debug(
                "Matched identity=%s expected=%s actual=%s valid=%s",
                normalized_name,
                expected_item.original_filename if expected_item else None,
                actual_item.original_filename if actual_item else None,
                reference.is_valid_pattern,
            )

    return pairs
