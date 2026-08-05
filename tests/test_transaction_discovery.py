"""Folder discovery tests for TransactionXO–HSAB."""

from __future__ import annotations

from pathlib import Path

from output_verifier.constants import OutputType, SolutionType, VerificationType
from output_verifier.folder_discovery import build_scenario_inventory, discover_output_locations


def _touch(path: Path, content: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_discovers_mdc_and_exceptions(tmp_path: Path) -> None:
    root = tmp_path / "root"
    _touch(root / "test_case" / "current" / "MDC" / "HSB_EN_2026062401_Converted.txt")
    _touch(
        root
        / "test_case"
        / "current"
        / "MDCExceptions"
        / "HSB_EN_2026062401_AllScenarios_ExceptionDupAcct_20260805103159.csv"
    )
    locations = discover_output_locations(
        root,
        SolutionType.TRANSACTION_XO,
        VerificationType.HSAB,
    )
    assert len(locations) == 2
    output_types = {key.output_type for key in locations}
    assert output_types == {OutputType.MDC, OutputType.MDC_EXCEPTIONS}


def test_nested_scenario_path(tmp_path: Path) -> None:
    root = tmp_path / "root"
    _touch(
        root / "suite" / "nested" / "current" / "MDC" / "HSB_EN_ABC_Converted.txt",
    )
    locations = discover_output_locations(
        root,
        SolutionType.TRANSACTION_XO,
        VerificationType.HSAB,
    )
    keys = list(locations)
    assert len(keys) == 1
    assert keys[0].scenario_path.replace("/", "\\") in {
        "suite\\nested",
        "suite/nested",
    }
    assert keys[0].run_type == "current"


def test_case_insensitive_folders(tmp_path: Path) -> None:
    root = tmp_path / "root"
    _touch(root / "s1" / "CURRENT" / "mdc" / "HSB_EN_1_Converted.txt")
    locations = discover_output_locations(
        root,
        SolutionType.TRANSACTION_XO,
        VerificationType.HSAB,
    )
    assert len(locations) == 1
    key = next(iter(locations))
    assert key.output_type == OutputType.MDC
    assert key.run_type == "current"


def test_unsupported_folder_ignored(tmp_path: Path) -> None:
    root = tmp_path / "root"
    _touch(root / "s1" / "current" / "Other" / "HSB_EN_1_Converted.txt")
    locations = discover_output_locations(
        root,
        SolutionType.TRANSACTION_XO,
        VerificationType.HSAB,
    )
    assert locations == {}


def test_inventory_expected_and_actual_only(tmp_path: Path) -> None:
    expected = tmp_path / "expected"
    actual = tmp_path / "actual"
    _touch(expected / "only_e" / "current" / "MDC" / "HSB_EN_1_Converted.txt")
    _touch(actual / "only_a" / "current" / "MDC" / "HSB_EN_2_Converted.txt")
    inventory = build_scenario_inventory(
        expected,
        actual,
        SolutionType.TRANSACTION_XO,
        VerificationType.HSAB,
    )
    assert len(inventory) == 2
    by_scenario = {item.scenario_key.scenario_path: item for item in inventory}
    assert by_scenario["only_e"].actual_folder is None
    assert by_scenario["only_a"].expected_folder is None


def test_empty_mdc_folder(tmp_path: Path) -> None:
    expected = tmp_path / "expected"
    actual = tmp_path / "actual"
    (expected / "s1" / "current" / "MDC").mkdir(parents=True)
    (actual / "s1" / "current" / "MDC").mkdir(parents=True)
    inventory = build_scenario_inventory(
        expected,
        actual,
        SolutionType.TRANSACTION_XO,
        VerificationType.HSAB,
    )
    assert len(inventory) == 1
    assert inventory[0].expected_files == ()
    assert inventory[0].actual_files == ()
