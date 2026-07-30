"""Application entry point for python -m output_verifier."""

from __future__ import annotations

import logging
import sys
import traceback
from datetime import datetime

from output_verifier import __version__
from output_verifier.cli import config_path_from_args, parse_arguments
from output_verifier.config import ConfigurationError
from output_verifier.config_loader import load_resolved_config
from output_verifier.constants import APPLICATION_NAME, APPLICATION_VERSION, ExitCode
from output_verifier.logging_setup import setup_logging
from output_verifier.models import ExecutionSummary
from output_verifier.reporting.excel_reporter import ExcelReporter
from output_verifier.utilities.filename_utils import immediate_parent_folder_name
from output_verifier.verification_service import VerificationService

LOGGER = logging.getLogger(__name__)


def print_console_summary(summary: ExecutionSummary) -> None:
    """Print the end-of-run console summary."""
    report_display = str(summary.report_path) if summary.report_path else ""
    print()
    print(f"Solution Type     : {summary.solution_type.value}")
    print(f"Verification Type : {summary.verification_type.value}")
    print(f"Compared Files    : {summary.compared_files_count}")
    print(f"Passed            : {summary.passed_count}")
    print(f"Failed            : {summary.failed_count}")
    print(f"Not Verified      : {summary.not_verified_count}")
    print(f"Report            : {report_display}")
    print(f"Exit Code          : {summary.exit_code}")
    print()


def print_system_error(message: str, exit_code: int = ExitCode.SYSTEM_ERROR.value) -> None:
    """Print a concise system error for the console."""
    print(f"ERROR: {message}", file=sys.stderr)
    print(f"Exit Code          : {exit_code}", file=sys.stderr)


def run(argv: list[str] | None = None) -> int:
    """Run the output verifier and return a process exit code."""
    try:
        arguments = parse_arguments(argv)
    except SystemExit as error:
        code = error.code if isinstance(error.code, int) else ExitCode.SYSTEM_ERROR.value
        return code if code is not None else ExitCode.SYSTEM_ERROR.value

    config_path = config_path_from_args(arguments)
    execution_start = datetime.now()

    solution_override = arguments.solution_type
    if isinstance(solution_override, str):
        # Normalize casing for enum parse (ClaimsXO / EnrollmentXO).
        lowered = solution_override.lower()
        if lowered == "claimsxo":
            solution_override = "ClaimsXO"
        elif lowered == "enrollmentxo":
            solution_override = "EnrollmentXO"

    try:
        resolved = load_resolved_config(
            config_path,
            solution_type_override=solution_override,
            verification_type_override=arguments.verification_type,
            expected_parent_folder_override=arguments.expected_parent_folder,
            actual_parent_folder_override=arguments.actual_parent_folder,
            report_output_folder_override=arguments.report_output_folder,
            log_level_override=arguments.log_level,
            validate_parent_folders=True,
        )
    except ConfigurationError as error:
        print_system_error(str(error))
        return ExitCode.SYSTEM_ERROR.value
    except Exception as error:  # noqa: BLE001
        print_system_error(f"Unexpected configuration error: {error}")
        return ExitCode.SYSTEM_ERROR.value

    immediate_parent = immediate_parent_folder_name(resolved.actual_parent_folder)
    timestamp_token = execution_start.strftime(resolved.report.timestamp_format)

    try:
        setup_logging(
            resolved.logging,
            solution_type=resolved.solution_type,
            verification_type=resolved.verification_type,
            immediate_parent=immediate_parent,
            timestamp_token=timestamp_token,
        )
    except Exception as error:  # noqa: BLE001
        print_system_error(f"Logging cannot be initialized: {error}")
        return ExitCode.SYSTEM_ERROR.value

    LOGGER.info("Application start: %s v%s", APPLICATION_NAME, APPLICATION_VERSION)
    LOGGER.info("Package version: %s", __version__)
    LOGGER.info("Resolved solution_type=%s", resolved.solution_type.value)
    LOGGER.info("Resolved verification_type=%s", resolved.verification_type.value)
    LOGGER.info("Expected root=%s", resolved.expected_parent_folder)
    LOGGER.info("Actual root=%s", resolved.actual_parent_folder)
    LOGGER.info("Immediate actual parent folder=%s", immediate_parent)
    LOGGER.info(
        "Resolved configuration: report_folder=%s log_folder=%s log_level=%s",
        resolved.report.output_folder,
        resolved.logging.output_folder,
        resolved.logging.level,
    )

    summary = ExecutionSummary(
        solution_type=resolved.solution_type,
        verification_type=resolved.verification_type,
        execution_start_time=execution_start,
        execution_end_time=None,
        expected_root=resolved.expected_parent_folder,
        actual_root=resolved.actual_parent_folder,
    )

    try:
        service = VerificationService(resolved)
        report_rows, comparison_exit = service.run()
        summary.report_rows = report_rows
        summary.exit_code = comparison_exit.value

        reporter = ExcelReporter()
        report_path = reporter.write_report(
            resolved.report,
            summary,
            immediate_parent=immediate_parent,
            timestamp=execution_start,
        )
        summary.report_path = report_path
        summary.execution_end_time = datetime.now()
        summary.exit_code = comparison_exit.value

        LOGGER.info("Report path: %s", report_path)
        LOGGER.info(
            "Summary counts: passed=%s failed=%s not_verified=%s exit_code=%s",
            summary.passed_count,
            summary.failed_count,
            summary.not_verified_count,
            summary.exit_code,
        )
        print_console_summary(summary)
        LOGGER.info("Application end.")
        return summary.exit_code

    except ConfigurationError as error:
        LOGGER.error("Configuration/system error during verification: %s", error)
        print_system_error(str(error))
        return ExitCode.SYSTEM_ERROR.value
    except ValueError as error:
        LOGGER.error("System error during verification: %s", error, exc_info=True)
        print_system_error(str(error))
        return ExitCode.SYSTEM_ERROR.value
    except OSError as error:
        LOGGER.error("System I/O error: %s", error, exc_info=True)
        print_system_error(f"System error: {error}")
        return ExitCode.SYSTEM_ERROR.value
    except Exception as error:  # noqa: BLE001
        LOGGER.error("Unhandled system error: %s", error, exc_info=True)
        LOGGER.debug("Traceback:\n%s", traceback.format_exc())
        print_system_error(f"Unexpected system error: {error}")
        return ExitCode.SYSTEM_ERROR.value


def main() -> None:
    """Console script entry point."""
    sys.exit(run())


if __name__ == "__main__":
    main()
