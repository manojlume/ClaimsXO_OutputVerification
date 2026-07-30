"""Discover scenario and output folders under Expected and Actual roots."""

from __future__ import annotations

import logging
from pathlib import Path

from output_verifier.constants import (
    OUTPUT_TYPE_CANONICAL,
    SUPPORTED_RUN_FOLDERS,
    SolutionProfile,
    SolutionType,
    VerificationType,
    get_solution_profile,
)
from output_verifier.models import DiscoveredOutput, ScenarioKey
from output_verifier.utilities.filename_utils import has_supported_extension

LOGGER = logging.getLogger(__name__)


def _canonicalize_run_type(folder_name: str) -> str | None:
    lowered = folder_name.lower()
    if lowered in SUPPORTED_RUN_FOLDERS:
        return lowered
    return None


def _canonicalize_output_type(folder_name: str, profile: SolutionProfile):
    lowered = folder_name.lower()
    if lowered not in profile.supported_output_folder_names():
        return None
    return OUTPUT_TYPE_CANONICAL.get(lowered)


def _collect_direct_files(
    folder: Path,
    supported_extensions: frozenset[str],
) -> tuple[Path, ...]:
    files: list[Path] = []
    try:
        for entry in sorted(folder.iterdir(), key=lambda item: item.name.lower()):
            if entry.is_file() and has_supported_extension(entry.name, supported_extensions):
                files.append(entry)
    except OSError as error:
        LOGGER.error("Unable to read output folder %s: %s", folder, error)
    return tuple(files)


def discover_output_locations(
    root: Path,
    solution_type: SolutionType,
    verification_type: VerificationType,
) -> dict[ScenarioKey, Path]:
    """
    Recursively discover supported scenario/run/output folders under a root.

    Whenever a supported run folder is found, the relative path before that
    run folder is treated as the scenario path. Only supported output folders
    directly under the run folder are considered.
    """
    profile = get_solution_profile(solution_type, verification_type)
    discovered: dict[ScenarioKey, Path] = {}

    if not root.exists():
        LOGGER.error("Root folder does not exist: %s", root)
        return discovered

    for current_path in root.rglob("*"):
        if not current_path.is_dir():
            continue

        run_type = _canonicalize_run_type(current_path.name)
        if run_type is None:
            continue

        try:
            relative_to_root = current_path.relative_to(root)
        except ValueError:
            continue

        parts = relative_to_root.parts
        if len(parts) < 2:
            scenario_path = ""
        else:
            scenario_path = "\\".join(parts[:-1])

        for child in current_path.iterdir():
            if not child.is_dir():
                continue
            output_type = _canonicalize_output_type(child.name, profile)
            if output_type is None:
                continue

            scenario_key = ScenarioKey(
                scenario_path=scenario_path,
                run_type=run_type,
                output_type=output_type,
            )
            if scenario_key in discovered:
                LOGGER.warning(
                    "Duplicate scenario location for %s; keeping first path %s, ignoring %s",
                    scenario_key,
                    discovered[scenario_key],
                    child,
                )
                continue
            discovered[scenario_key] = child
            LOGGER.debug(
                "Discovered %s/%s output folder: scenario=%s run=%s output=%s path=%s",
                solution_type.value,
                verification_type.value,
                scenario_path,
                run_type,
                output_type.value,
                child,
            )

    LOGGER.info(
        "Discovered %s supported output locations under %s",
        len(discovered),
        root,
    )
    return discovered


def build_scenario_inventory(
    expected_root: Path,
    actual_root: Path,
    solution_type: SolutionType,
    verification_type: VerificationType,
) -> list[DiscoveredOutput]:
    """Build a union inventory of Expected and Actual scenario output folders."""
    profile = get_solution_profile(solution_type, verification_type)
    expected_map = discover_output_locations(expected_root, solution_type, verification_type)
    actual_map = discover_output_locations(actual_root, solution_type, verification_type)

    all_keys = sorted(
        set(expected_map.keys()) | set(actual_map.keys()),
        key=lambda key: (key.scenario_path.lower(), key.run_type, key.output_type.value),
    )

    inventory: list[DiscoveredOutput] = []
    for scenario_key in all_keys:
        expected_folder = expected_map.get(scenario_key)
        actual_folder = actual_map.get(scenario_key)
        expected_files = (
            _collect_direct_files(expected_folder, profile.supported_extensions)
            if expected_folder
            else ()
        )
        actual_files = (
            _collect_direct_files(actual_folder, profile.supported_extensions)
            if actual_folder
            else ()
        )
        inventory.append(
            DiscoveredOutput(
                scenario_key=scenario_key,
                expected_folder=expected_folder,
                actual_folder=actual_folder,
                expected_files=expected_files,
                actual_files=actual_files,
            )
        )

    LOGGER.info(
        "Scenario inventory size: %s (expected=%s actual=%s)",
        len(inventory),
        len(expected_map),
        len(actual_map),
    )
    return inventory
