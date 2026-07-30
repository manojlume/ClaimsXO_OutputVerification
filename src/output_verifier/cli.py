"""Command-line argument parsing for the output verifier."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

DEFAULT_CONFIG_FILE_NAME = "config.yaml"


def application_directory() -> Path:
    """
    Return the directory that contains the running application.

    For a frozen executable this is the folder that contains output-verifier.exe.
    For source runs this is the current working directory.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path.cwd()


def default_config_path() -> Path:
    """Return the default external config.yaml location."""
    return application_directory() / DEFAULT_CONFIG_FILE_NAME


def build_argument_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="output_verifier",
        description=(
            "ClaimsXO output verification utility. Compares Expected Output files "
            "against Actual Output files after a QA regression run."
        ),
    )
    parser.add_argument(
        "--config",
        default=str(default_config_path()),
        help=(
            "Path to the external YAML configuration file. "
            f"Defaults to {DEFAULT_CONFIG_FILE_NAME} next to the executable "
            f"(or in the current folder for source runs)."
        ),
    )
    parser.add_argument(
        "--verification-type",
        choices=["GDI", "HSAB", "gdi", "hsab"],
        help="Override verification_type from YAML (GDI or HSAB).",
    )
    parser.add_argument(
        "--expected-parent-folder",
        help="Override expected_parent_folder from YAML.",
    )
    parser.add_argument(
        "--actual-parent-folder",
        help="Override actual_parent_folder from YAML.",
    )
    parser.add_argument(
        "--report-output-folder",
        help="Override report.output_folder from YAML.",
    )
    parser.add_argument(
        "--log-level",
        help="Override logging.level from YAML.",
    )
    return parser


def parse_arguments(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = build_argument_parser()
    return parser.parse_args(argv)


def config_path_from_args(arguments: argparse.Namespace) -> Path:
    """Return the configuration path from parsed arguments."""
    return Path(arguments.config)
