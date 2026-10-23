"""Discover scenario and output folders under Expected and Actual roots."""

from __future__ import annotations

import logging
from pathlib import Path

from output_verifier.constants import (
    OUTPUT_TYPE_CANONICAL,
    SUPPORTED_RUN_FOLDERS,
    OutputType,
    RunType,
    SolutionProfile,
    SolutionType,
    VerificationType,
    get_solution_profile,
)
from output_verifier.models import DiscoveredOutput, ScenarioKey
from output_verifier.utilities.filename_utils import has_supported_extension

LOGGER = logging.getLogger(__name__)

# Hold is not a sibling of current/pre/prepre. It is only current\LH1\Hold.
PEER_RUN_FOLDERS: frozenset[str] = SUPPORTED_RUN_FOLDERS - {RunType.HOLD.value}


def _canonicalize_run_type(folder_name: str, allowed_run_folders: frozenset[str]) -> str | None:
    lowered = folder_name.lower()
    if lowered in allowed_run_folders:
        return lowered
    return None


def _canonicalize_output_type(folder_name: str, profile: SolutionProfile):
    lowered = folder_name.lower()
    if lowered not in profile.supported_output_folder_names():
        return None
    return OUTPUT_TYPE_CANONICAL.get(lowered)


def _find_hold_folder(output_folder: Path) -> Path | None:
    """Return current\\LH1\\Hold when that child folder exists."""
    try:
        for child in output_folder.iterdir():
            if child.is_dir() and child.name.lower() == RunType.HOLD.value:
                return child
    except OSError as error:
        LOGGER.error("Unable to read output folder %s: %s", output_folder, error)
    return None


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
    run_folders: tuple[str, ...] = (),
) -> dict[ScenarioKey, Path]:
    """
    Recursively discover supported scenario/run/output folders under a root.

    Whenever a supported run folder is found, the relative path before that
    run folder is treated as the scenario path. Only supported output folders
    directly under the run folder are considered.
    """
    profile = get_solution_profile(solution_type, verification_type)
    allowed_run_folders = frozenset(run_folders) if run_folders else SUPPORTED_RUN_FOLDERS
    include_hold = RunType.HOLD.value in allowed_run_folders
    peer_allowed = allowed_run_folders & PEER_RUN_FOLDERS
    if include_hold:
        peer_allowed = peer_allowed | {RunType.CURRENT.value}
    discovered: dict[ScenarioKey, Path] = {}

    if not root.exists():
        LOGGER.error("Root folder does not exist: %s", root)
        return discovered

    for current_path in root.rglob("*"):
        if not current_path.is_dir():
            continue

        run_type = _canonicalize_run_type(current_path.name, peer_allowed)
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

            if run_type in allowed_run_folders:
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
                else:
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

            if not (
                include_hold
                and run_type == RunType.CURRENT.value
                and output_type == OutputType.LH1
            ):
                continue
            hold_folder = _find_hold_folder(child)
            if hold_folder is None:
                continue
            hold_key = ScenarioKey(
                scenario_path=scenario_path,
                run_type=RunType.HOLD.value,
                output_type=OutputType.LH1,
            )
            if hold_key in discovered:
                LOGGER.warning(
                    "Duplicate scenario location for %s; keeping first path %s, ignoring %s",
                    hold_key,
                    discovered[hold_key],
                    hold_folder,
                )
                continue
            discovered[hold_key] = hold_folder
            LOGGER.debug(
                "Discovered %s/%s Hold folder: scenario=%s path=%s",
                solution_type.value,
                verification_type.value,
                scenario_path,
                hold_folder,
            )

    LOGGER.info(
        "Discovered %s supported output locations under %s",
        len(discovered),
        root,
    )
    return discovered


def discover_run_locations(
    root: Path,
    run_folders: tuple[str, ...] = (),
) -> dict[tuple[str, str], Path]:
    """Return supported run folders keyed by scenario path and run type."""
    allowed_run_folders = frozenset(run_folders) if run_folders else SUPPORTED_RUN_FOLDERS
    peer_allowed = allowed_run_folders & PEER_RUN_FOLDERS
    discovered: dict[tuple[str, str], Path] = {}
    if not root.exists():
        return discovered

    for current_path in root.rglob("*"):
        if not current_path.is_dir():
            continue
        run_type = _canonicalize_run_type(current_path.name, peer_allowed)
        if run_type is None:
            continue
        try:
            relative_to_root = current_path.relative_to(root)
        except ValueError:
            continue
        parts = relative_to_root.parts
        scenario_path = "" if len(parts) < 2 else "\\".join(parts[:-1])
        key = (scenario_path, run_type)
        if key not in discovered:
            discovered[key] = current_path
    return discovered


def _skip_empty_current_lh1(
    scenario_key: ScenarioKey,
    expected_files: tuple[Path, ...],
    actual_files: tuple[Path, ...],
    hold_scenarios: set[str],
) -> bool:
    """
    current\\LH1 with no direct files is only a container for current\\LH1\\Hold.

    Those files are verified on the hold row. Do not also report the empty LH1
    folder as NotVerified.
    """
    return (
        scenario_key.run_type == RunType.CURRENT.value
        and scenario_key.output_type == OutputType.LH1
        and not expected_files
        and not actual_files
        and scenario_key.scenario_path in hold_scenarios
    )


def build_scenario_inventory(
    expected_root: Path,
    actual_root: Path,
    solution_type: SolutionType,
    verification_type: VerificationType,
    run_folders: tuple[str, ...] = (),
) -> list[DiscoveredOutput]:
    """Build a union inventory of Expected and Actual scenario output folders."""
    profile = get_solution_profile(solution_type, verification_type)
    LOGGER.info(
        "Run folders to compare: %s",
        ", ".join(run_folders) if run_folders else "all supported",
    )
    expected_map = discover_output_locations(
        expected_root, solution_type, verification_type, run_folders
    )
    actual_map = discover_output_locations(
        actual_root, solution_type, verification_type, run_folders
    )

    all_keys = sorted(
        set(expected_map.keys()) | set(actual_map.keys()),
        key=lambda key: (key.scenario_path.lower(), key.run_type, key.output_type.value),
    )
    hold_scenarios = {
        key.scenario_path
        for key in all_keys
        if key.run_type == RunType.HOLD.value and key.output_type == OutputType.LH1
    }

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
        if _skip_empty_current_lh1(scenario_key, expected_files, actual_files, hold_scenarios):
            LOGGER.debug(
                "Skipping empty current LH1 because Hold exists: scenario=%s",
                scenario_key.scenario_path,
            )
            continue
        inventory.append(
            DiscoveredOutput(
                scenario_key=scenario_key,
                expected_folder=expected_folder,
                actual_folder=actual_folder,
                expected_files=expected_files,
                actual_files=actual_files,
            )
        )

    output_runs = {(key.scenario_path, key.run_type) for key in all_keys}
    expected_runs = discover_run_locations(expected_root, run_folders)
    actual_runs = discover_run_locations(actual_root, run_folders)
    for scenario_path, run_type in sorted(set(expected_runs) & set(actual_runs)):
        if (scenario_path, run_type) in output_runs:
            continue
        inventory.append(
            DiscoveredOutput(
                scenario_key=ScenarioKey(
                    scenario_path=scenario_path,
                    run_type=run_type,
                    output_type=OutputType.NONE,
                ),
                expected_folder=expected_runs[(scenario_path, run_type)],
                actual_folder=actual_runs[(scenario_path, run_type)],
            )
        )
    inventory.sort(
        key=lambda item: (
            item.scenario_key.scenario_path.lower(),
            item.scenario_key.run_type,
            item.scenario_key.output_type.value,
        )
    )

    LOGGER.info(
        "Scenario inventory size: %s (expected=%s actual=%s)",
        len(inventory),
        len(expected_map),
        len(actual_map),
    )
    return inventory
