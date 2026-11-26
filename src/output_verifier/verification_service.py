"""Orchestrate discovery, matching, comparison, and report row creation."""

from __future__ import annotations

import logging
from collections import defaultdict

from output_verifier.comparators.csv_comparator import CsvComparator
from output_verifier.comparators.delimited_text_comparator import DelimitedTextComparator
from output_verifier.comparators.fixed_width_comparator import FixedWidthComparator
from output_verifier.comparators.mbi_comparator import MbiComparator
from output_verifier.comparators.xml_comparator import XmlComparator
from output_verifier.constants import (
    ExitCode,
    FileFormat,
    IGNORE_MARKER_FILENAME,
    OutputType,
    RunType,
    VerificationStatus,
    get_solution_profile,
)
from output_verifier.file_matcher import match_files_for_output
from output_verifier.folder_discovery import build_scenario_inventory, has_empty_ignore_marker
from output_verifier.models import (
    ComparisonOptions,
    ComparisonResult,
    DiscoveredOutput,
    MatchedFilePair,
    ReportRow,
    ResolvedConfig,
)

LOGGER = logging.getLogger(__name__)


class VerificationService:
    """Run end-to-end expected-vs-actual output verification."""

    def __init__(self, config: ResolvedConfig) -> None:
        self._config = config
        self._profile = get_solution_profile(config.solution_type, config.tpa_id)
        self._xml_comparator = XmlComparator()
        self._csv_comparator = CsvComparator()
        self._mbi_comparator = MbiComparator()
        self._delimited_text_comparator = DelimitedTextComparator()
        self._fixed_width_comparator = FixedWidthComparator()

    def run(self) -> tuple[list[ReportRow], ExitCode]:
        """Execute verification and return report rows plus comparison exit code."""
        LOGGER.info(
            "Starting verification. solution=%s type=%s expected=%s actual=%s",
            self._config.solution_type.value,
            self._config.tpa_id.value,
            self._config.expected_parent_folder,
            self._config.actual_parent_folder,
        )

        inventory = build_scenario_inventory(
            self._config.expected_parent_folder,
            self._config.actual_parent_folder,
            self._config.solution_type,
            self._config.tpa_id,
            self._config.run_folders,
        )
        LOGGER.info("Scenario discovery count: %s", len(inventory))

        detail_rows: list[ReportRow] = []
        for discovered in inventory:
            detail_rows.extend(self._verify_discovered_output(discovered))

        report_rows = self._aggregate_run_folder_rows(detail_rows)
        has_failures = any(row.status == VerificationStatus.FAILED for row in report_rows)
        exit_code = ExitCode.COMPARISON_FAILURE if has_failures else ExitCode.SUCCESS
        LOGGER.info(
            "Verification complete. rows=%s passed=%s failed=%s not_verified=%s exit_code=%s",
            len(report_rows),
            sum(1 for row in report_rows if row.status == VerificationStatus.PASSED),
            sum(1 for row in report_rows if row.status == VerificationStatus.FAILED),
            sum(1 for row in report_rows if row.status == VerificationStatus.NOT_VERIFIED),
            exit_code.value,
        )
        return report_rows, exit_code

    def _verify_discovered_output(self, discovered: DiscoveredOutput) -> list[ReportRow]:
        scenario_key = discovered.scenario_key
        LOGGER.info(
            "Processing scenario=%s run=%s output=%s",
            scenario_key.scenario_path,
            scenario_key.run_type,
            scenario_key.output_type.value,
        )

        if discovered.expected_folder is None and discovered.actual_folder is not None:
            return [
                self._scenario_row(
                    discovered,
                    status=VerificationStatus.FAILED,
                    issue="Unexpected scenario exists only in Actual Outputs",
                )
            ]

        if discovered.expected_folder is not None and discovered.actual_folder is None:
            return [
                self._scenario_row(
                    discovered,
                    status=VerificationStatus.FAILED,
                    issue="Expected scenario missing in Actual Outputs",
                )
            ]

        if has_empty_ignore_marker(discovered.expected_folder):
            expected_marker = self._relative_path(
                scenario_key.run_type,
                scenario_key.output_type.value,
                IGNORE_MARKER_FILENAME,
            )
            if discovered.actual_files:
                actual_paths = "\n".join(
                    self._relative_path(
                        scenario_key.run_type,
                        scenario_key.output_type.value,
                        path.name,
                    )
                    for path in discovered.actual_files
                )
                LOGGER.info(
                    "Failing scenario: empty %s in Expected but Actual has files. "
                    "scenario=%s run=%s output=%s files=%s",
                    IGNORE_MARKER_FILENAME,
                    scenario_key.scenario_path,
                    scenario_key.run_type,
                    scenario_key.output_type.value,
                    actual_paths,
                )
                return [
                    ReportRow(
                        solution_type=self._config.solution_type.value,
                        verification_type=self._config.tpa_id.value,
                        scenario=scenario_key.display_scenario(),
                        run_type=scenario_key.run_type,
                        output_type=self._output_type_label(
                            scenario_key.run_type, scenario_key.output_type.value
                        ),
                        expected_file=expected_marker,
                        actual_file=actual_paths,
                        status=VerificationStatus.FAILED,
                        issue=(
                            f"Expected empty {expected_marker} but Actual folder "
                            f"contains file(s):\n{actual_paths}"
                        ),
                    )
                ]
            LOGGER.info(
                "Passing scenario via empty %s in Expected and no Actual files. "
                "scenario=%s run=%s output=%s",
                IGNORE_MARKER_FILENAME,
                scenario_key.scenario_path,
                scenario_key.run_type,
                scenario_key.output_type.value,
            )
            return [
                ReportRow(
                    solution_type=self._config.solution_type.value,
                    verification_type=self._config.tpa_id.value,
                    scenario=scenario_key.display_scenario(),
                    run_type=scenario_key.run_type,
                    output_type=self._output_type_label(
                        scenario_key.run_type, scenario_key.output_type.value
                    ),
                    expected_file=expected_marker,
                    actual_file="",
                    status=VerificationStatus.PASSED,
                    issue=(
                        f"Output ignored via empty {expected_marker} "
                        "(no Actual files)"
                    ),
                )
            ]

        if not discovered.expected_files and not discovered.actual_files:
            return [
                self._scenario_row(
                    discovered,
                    status=VerificationStatus.NOT_VERIFIED,
                    issue="No files available for verification",
                )
            ]

        pairs = match_files_for_output(discovered, self._profile)
        return self._rows_from_matched_pairs(pairs)

    def _rows_from_matched_pairs(self, pairs: list[MatchedFilePair]) -> list[ReportRow]:
        rows: list[ReportRow] = []
        identity_expected_counts: dict[str, int] = defaultdict(int)
        identity_actual_counts: dict[str, int] = defaultdict(int)
        for pair in pairs:
            if pair.expected_file is not None:
                identity_expected_counts[pair.normalized_identity] += 1
            if pair.actual_file is not None:
                identity_actual_counts[pair.normalized_identity] += 1

        reported_count_mismatch: set[str] = set()
        for pair in pairs:
            expected_count = identity_expected_counts[pair.normalized_identity]
            actual_count = identity_actual_counts[pair.normalized_identity]
            if (
                expected_count != actual_count
                and pair.normalized_identity not in reported_count_mismatch
            ):
                reported_count_mismatch.add(pair.normalized_identity)
                output_label = self._output_type_label(
                    pair.scenario_key.run_type, pair.scenario_key.output_type.value
                )
                rows.append(
                    self._file_row(
                        pair,
                        status=VerificationStatus.FAILED,
                        issue=(
                            f"{output_label}: File count mismatch. "
                            f"Expected: {expected_count}, Actual: {actual_count}"
                        ),
                        expected_name="",
                        actual_name="",
                    )
                )
            rows.append(self._compare_pair(pair))
        return rows

    @classmethod
    def _aggregate_run_folder_rows(cls, rows: list[ReportRow]) -> list[ReportRow]:
        """
        Collapse detail rows into one Excel row per Scenario + Run Type.

        Hold results are rolled into the matching current row.
        """
        if not rows:
            return []

        grouped: dict[tuple[str, str], list[ReportRow]] = defaultdict(list)
        for row in rows:
            grouped[(row.scenario, cls._effective_run_type(row.run_type))].append(row)

        aggregated: list[ReportRow] = []
        for (scenario, run_type), group in sorted(
            grouped.items(), key=lambda item: (item[0][0].lower(), item[0][1])
        ):
            aggregated.append(cls._merge_run_group(scenario, run_type, group))
        return aggregated

    @classmethod
    def _merge_run_group(
        cls,
        scenario: str,
        run_type: str,
        rows: list[ReportRow],
    ) -> ReportRow:
        output_types: list[str] = []
        seen_outputs: set[str] = set()
        expected_names: list[str] = []
        actual_names: list[str] = []
        seen_expected: set[str] = set()
        seen_actual: set[str] = set()

        for row in rows:
            if row.output_type and row.output_type not in seen_outputs:
                seen_outputs.add(row.output_type)
                output_types.append(row.output_type)
            for name in cls._split_multiline(row.expected_file):
                if name not in seen_expected:
                    seen_expected.add(name)
                    expected_names.append(name)
            for name in cls._split_multiline(row.actual_file):
                if name not in seen_actual:
                    seen_actual.add(name)
                    actual_names.append(name)

        failed_rows = [row for row in rows if row.status == VerificationStatus.FAILED]
        passed_rows = [row for row in rows if row.status == VerificationStatus.PASSED]
        not_verified_rows = [
            row for row in rows if row.status == VerificationStatus.NOT_VERIFIED
        ]

        if failed_rows:
            status = VerificationStatus.FAILED
            issue_parts: list[str] = []
            for row in failed_rows:
                if row.expected_file or row.actual_file:
                    header = (
                        f"Expected: {row.expected_file or '(none)'}\n"
                        f"Actual: {row.actual_file or '(none)'}"
                    )
                    issue_parts.append(
                        f"{header}\n{row.issue}" if row.issue else header
                    )
                elif row.issue:
                    issue_parts.append(row.issue)
            issue = "\n\n".join(issue_parts)
        elif passed_rows:
            status = VerificationStatus.PASSED
            # Keep informational Passed issues (e.g. ignore.txt marker).
            issue = "\n\n".join(row.issue for row in passed_rows if row.issue)
        elif not_verified_rows:
            status = VerificationStatus.NOT_VERIFIED
            issue = "\n\n".join(row.issue for row in not_verified_rows if row.issue)
        else:
            status = VerificationStatus.NOT_VERIFIED
            issue = "No files available for verification"

        first = rows[0]
        return ReportRow(
            solution_type=first.solution_type,
            verification_type=first.verification_type,
            scenario=scenario,
            run_type=run_type,
            output_type="\n".join(output_types),
            expected_file="\n".join(expected_names),
            actual_file="\n".join(actual_names),
            status=status,
            issue=issue,
        )

    @staticmethod
    def _split_multiline(value: str) -> list[str]:
        if not value:
            return []
        return [part for part in value.splitlines() if part]

    @staticmethod
    def _effective_run_type(run_type: str) -> str:
        if run_type == RunType.HOLD.value:
            return RunType.CURRENT.value
        return run_type

    @staticmethod
    def _output_type_label(run_type: str, output_type: str) -> str:
        if run_type == RunType.HOLD.value:
            return f"{OutputType.LH1.value}\\Hold"
        return output_type

    @classmethod
    def _relative_path(cls, run_type: str, output_type: str, filename: str) -> str:
        base = cls._output_type_label(run_type, output_type)
        if not filename:
            return base
        if not base:
            return filename
        return f"{base}\\{filename}"

    def _compare_pair(self, pair: MatchedFilePair) -> ReportRow:
        expected_name = pair.expected_file.name if pair.expected_file else ""
        actual_name = pair.actual_file.name if pair.actual_file else ""
        expected_path = self._relative_path(
            pair.scenario_key.run_type,
            pair.scenario_key.output_type.value,
            expected_name,
        )
        actual_path = self._relative_path(
            pair.scenario_key.run_type,
            pair.scenario_key.output_type.value,
            actual_name,
        )

        if pair.expected_file is None and pair.actual_file is not None:
            issue = (
                "Unsupported or invalid filename pattern"
                if not pair.is_valid_pattern
                else "Unexpected actual file"
            )
            return self._file_row(
                pair,
                status=VerificationStatus.FAILED,
                issue=issue,
                expected_name="",
                actual_name=actual_path,
            )

        if pair.expected_file is not None and pair.actual_file is None:
            issue = (
                "Unsupported or invalid filename pattern"
                if not pair.is_valid_pattern
                else "Expected file missing"
            )
            return self._file_row(
                pair,
                status=VerificationStatus.FAILED,
                issue=issue,
                expected_name=expected_path,
                actual_name="",
            )

        assert pair.expected_file is not None and pair.actual_file is not None
        if not pair.is_valid_pattern:
            return self._file_row(
                pair,
                status=VerificationStatus.FAILED,
                issue="Unsupported or invalid filename pattern",
                expected_name=expected_path,
                actual_name=actual_path,
            )

        LOGGER.info(
            "Comparing expected=%s actual=%s format=%s",
            expected_path,
            actual_path,
            pair.file_format,
        )
        comparison = self._compare_content(pair)
        issue_text = self._build_issue_text(comparison)
        LOGGER.info("Comparison result for %s: %s", expected_path, comparison.status.value)
        return self._file_row(
            pair,
            status=comparison.status,
            issue=issue_text,
            expected_name=expected_path,
            actual_name=actual_path,
        )

    @staticmethod
    def _build_issue_text(comparison: ComparisonResult) -> str:
        """Combine summary issue and difference details into one Issue value."""
        parts: list[str] = []
        if comparison.issue:
            parts.append(comparison.issue)
        for index, difference in enumerate(comparison.differences, start=1):
            parts.append(f"Difference {index}: {difference.description}")
        return "\n".join(parts)

    def _compare_content(self, pair: MatchedFilePair) -> ComparisonResult:
        assert pair.expected_file is not None and pair.actual_file is not None
        options = self._build_comparison_options(pair)

        if pair.file_format == FileFormat.XML:
            return self._xml_comparator.compare(pair.expected_file, pair.actual_file, options)
        if pair.file_format == FileFormat.CSV:
            return self._csv_comparator.compare(pair.expected_file, pair.actual_file, options)
        if pair.file_format == FileFormat.MBI:
            return self._mbi_comparator.compare(pair.expected_file, pair.actual_file, options)
        if pair.file_format == FileFormat.DELIMITED_TEXT:
            return self._delimited_text_comparator.compare(
                pair.expected_file,
                pair.actual_file,
                options,
            )
        if pair.file_format == FileFormat.FIXED_WIDTH:
            return self._fixed_width_comparator.compare(
                pair.expected_file,
                pair.actual_file,
                options,
            )

        return ComparisonResult(
            status=VerificationStatus.FAILED,
            issue="Unsupported or invalid filename pattern",
        )

    def _build_comparison_options(self, pair: MatchedFilePair) -> ComparisonOptions:
        ignore_rules = self._config.ignore_rules
        ignore_key = pair.ignore_rule_key or ""
        solution = self._config.solution_type
        verification = self._config.tpa_id

        if pair.file_format == FileFormat.XML:
            return ComparisonOptions(
                ignored_xml_paths=ignore_rules.xml_paths_for(solution, verification, ignore_key)
            )
        if pair.file_format == FileFormat.CSV:
            return ComparisonOptions(
                ignored_csv_columns=ignore_rules.csv_columns_for(
                    solution, verification, ignore_key
                )
            )
        if pair.file_format == FileFormat.MBI:
            return ComparisonOptions(
                ignored_mbi_field_positions=ignore_rules.field_positions_for(
                    solution, verification, ignore_key
                )
            )
        if pair.file_format == FileFormat.DELIMITED_TEXT:
            if pair.has_header:
                return ComparisonOptions(
                    delimiter=pair.delimiter or ",",
                    has_header=True,
                    ignored_columns=ignore_rules.csv_columns_for(
                        solution, verification, ignore_key
                    ),
                    compare_trailing_empty_fields=pair.compare_trailing_empty_fields,
                )
            return ComparisonOptions(
                delimiter=pair.delimiter or ",",
                has_header=False,
                ignored_field_positions=ignore_rules.field_positions_for(
                    solution, verification, ignore_key
                ),
                compare_trailing_empty_fields=pair.compare_trailing_empty_fields,
            )
        if pair.file_format == FileFormat.FIXED_WIDTH:
            return ComparisonOptions(
                ignored_character_ranges=ignore_rules.character_ranges_for(
                    solution, verification, ignore_key
                )
            )
        return ComparisonOptions()

    def _scenario_row(
        self,
        discovered: DiscoveredOutput,
        *,
        status: VerificationStatus,
        issue: str,
    ) -> ReportRow:
        key = discovered.scenario_key
        return ReportRow(
            solution_type=self._config.solution_type.value,
            verification_type=self._config.tpa_id.value,
            scenario=key.display_scenario(),
            run_type=key.run_type,
            output_type=self._output_type_label(key.run_type, key.output_type.value),
            expected_file="",
            actual_file="",
            status=status,
            issue=issue,
        )

    def _file_row(
        self,
        pair: MatchedFilePair,
        *,
        status: VerificationStatus,
        issue: str,
        expected_name: str,
        actual_name: str,
    ) -> ReportRow:
        key = pair.scenario_key
        return ReportRow(
            solution_type=self._config.solution_type.value,
            verification_type=self._config.tpa_id.value,
            scenario=key.display_scenario(),
            run_type=key.run_type,
            output_type=self._output_type_label(key.run_type, key.output_type.value),
            expected_file=expected_name,
            actual_file=actual_name,
            status=status,
            issue=issue,
        )
