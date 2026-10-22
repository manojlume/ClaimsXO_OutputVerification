"""Tests for scenario and output folder discovery."""

from __future__ import annotations

from pathlib import Path

from output_verifier.constants import OutputType, SolutionType, VerificationType
from output_verifier.folder_discovery import build_scenario_inventory, discover_output_locations


def _touch(path: Path, content: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_single_level_scenario(tmp_path: Path) -> None:
    root = tmp_path / "Scenarios"
    _touch(root / "test_58545" / "current" / "LH1" / "GDI_LH1_20260730110000.xml")

    discovered = discover_output_locations(root, SolutionType.CLAIMS_XO, VerificationType.GDI)

    assert len(discovered) == 1
    key = next(iter(discovered))
    assert key.scenario_path == "test_58545"
    assert key.run_type == "current"
    assert key.output_type == OutputType.LH1


def test_multi_level_scenario(tmp_path: Path) -> None:
    root = tmp_path / "Scenarios"
    _touch(root / "test_aggregation" / "3" / "pre" / "LH1" / "GDI_LH1_20260730110000.xml")

    discovered = discover_output_locations(root, SolutionType.CLAIMS_XO, VerificationType.GDI)
    key = next(iter(discovered))
    assert key.scenario_path == "test_aggregation\\3"
    assert key.run_type == "pre"
    assert key.output_type == OutputType.LH1


def test_all_supported_run_types(tmp_path: Path) -> None:
    root = tmp_path / "Scenarios"
    for index, run_type in enumerate(("current", "pre", "prepre", "hold")):
        _touch(
            root / "runs" / run_type / "LH1" / f"GDI_LH1_2026073011000{index}.xml",
            "<a/>",
        )

    discovered = discover_output_locations(root, SolutionType.CLAIMS_XO, VerificationType.GDI)
    assert {key.run_type for key in discovered} == {"current", "pre", "prepre", "hold"}


def test_run_folders_limit_discovery(tmp_path: Path) -> None:
    root = tmp_path / "Scenarios"
    _touch(root / "s1" / "current" / "LH1" / "GDI_LH1_20260730110000.xml")
    _touch(root / "s1" / "pre" / "LH1" / "GDI_LH1_20260730110001.xml")
    _touch(root / "s1" / "hold" / "LH1" / "GDI_LH1_20260730110002.xml")

    discovered = discover_output_locations(
        root,
        SolutionType.CLAIMS_XO,
        VerificationType.GDI,
        ("current", "pre"),
    )
    assert {key.run_type for key in discovered} == {"current", "pre"}


def test_unknown_folders_and_unsupported_files_ignored(tmp_path: Path) -> None:
    root = tmp_path / "Scenarios"
    _touch(root / "s1" / "current" / "LH1" / "GDI_LH1_20260730110000.xml")
    _touch(root / "s1" / "current" / "LH1" / "readme.txt")
    _touch(root / "s1" / "current" / "OTHER" / "file.xml")
    _touch(root / "s1" / "draft" / "LH1" / "GDI_LH1_20260730110001.xml")

    inventory = build_scenario_inventory(root, root, SolutionType.CLAIMS_XO, VerificationType.GDI)
    assert len(inventory) == 1
    assert len(inventory[0].expected_files) == 1
    assert inventory[0].expected_files[0].name.endswith(".xml")


def test_expected_only_and_actual_only(tmp_path: Path) -> None:
    expected = tmp_path / "expected"
    actual = tmp_path / "actual"
    _touch(expected / "only_expected" / "current" / "LH1" / "GDI_LH1_20260730110000.xml")
    _touch(actual / "only_actual" / "current" / "LH1" / "GDI_LH1_20260730110000.xml")

    inventory = build_scenario_inventory(expected, actual, SolutionType.CLAIMS_XO, VerificationType.GDI)
    assert len(inventory) == 2
    by_scenario = {item.scenario_key.scenario_path: item for item in inventory}
    assert by_scenario["only_expected"].actual_folder is None
    assert by_scenario["only_actual"].expected_folder is None


def test_empty_scenario(tmp_path: Path) -> None:
    expected = tmp_path / "expected"
    actual = tmp_path / "actual"
    (expected / "empty" / "current" / "LH1").mkdir(parents=True)
    (actual / "empty" / "current" / "LH1").mkdir(parents=True)

    inventory = build_scenario_inventory(expected, actual, SolutionType.CLAIMS_XO, VerificationType.GDI)
    assert len(inventory) == 1
    assert inventory[0].expected_files == ()
    assert inventory[0].actual_files == ()


def test_empty_run_folder_on_both_sides_is_inventoried(tmp_path: Path) -> None:
    expected = tmp_path / "expected"
    actual = tmp_path / "actual"
    (expected / "test_tickets" / "test_ticket_81243" / "current").mkdir(parents=True)
    (actual / "test_tickets" / "test_ticket_81243" / "current").mkdir(parents=True)

    inventory = build_scenario_inventory(
        expected, actual, SolutionType.CLAIMS_XO, VerificationType.GDI
    )
    assert len(inventory) == 1
    item = inventory[0]
    assert item.scenario_key.scenario_path == "test_tickets\\test_ticket_81243"
    assert item.scenario_key.run_type == "current"
    assert item.scenario_key.output_type == OutputType.NONE
    assert item.expected_files == ()
    assert item.actual_files == ()


def test_empty_run_folder_on_one_side_is_not_inventoried(tmp_path: Path) -> None:
    expected = tmp_path / "expected"
    actual = tmp_path / "actual"
    (expected / "test_tickets" / "test_ticket_81243" / "current").mkdir(parents=True)
    actual.mkdir()

    inventory = build_scenario_inventory(
        expected, actual, SolutionType.CLAIMS_XO, VerificationType.GDI
    )
    assert inventory == []


def test_case_insensitive_folder_recognition(tmp_path: Path) -> None:
    root = tmp_path / "Scenarios"
    _touch(root / "s1" / "CURRENT" / "lh1" / "GDI_LH1_20260730110000.xml")

    discovered = discover_output_locations(root, SolutionType.CLAIMS_XO, VerificationType.GDI)
    key = next(iter(discovered))
    assert key.run_type == "current"
    assert key.output_type == OutputType.LH1


def test_hsab_wex_discovery(tmp_path: Path) -> None:
    root = tmp_path / "Scenarios"
    _touch(root / "s1" / "current" / "WEX" / "HB1_HSAB_CLAIMS_20260730110000.xml")

    discovered = discover_output_locations(root, SolutionType.CLAIMS_XO, VerificationType.HSAB)
    key = next(iter(discovered))
    assert key.output_type == OutputType.WEX
