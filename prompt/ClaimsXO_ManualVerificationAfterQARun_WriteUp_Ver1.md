You are a senior QA Automation Engineer and senior Python developer.

I want to create a complete Python-based output verification utility for the ClaimsXO project.

Project name:
output-verifier

Python package name:
output_verifier

Main command:
python -m output_verifier --config config/config.yaml

Executable name later:
output-verifier.exe

Important coding standards:

* Keep code simple, readable, and production-grade.
* Follow Clean Code principles by Robert C. Martin.
* Do not over-engineer.
* Use meaningful and self-explaining names.
* Do not use short or abbreviated variable names, function names, class names, or file names.
* Use type hints.
* Use dataclasses where suitable.
* Use enums for fixed values.
* Use pathlib instead of manual string path joining.
* Keep each class and function focused on one responsibility.
* Avoid deeply nested code.
* Avoid duplicate logic.
* Do not use global mutable state.
* Do not hard-code user-specific paths.
* Do not suppress exceptions without logging.
* Do not print from library modules; use logging.
* Only CLI/console summary may use print.
* Add simple English docstrings for every public class and public function.
* Add comments only where the reason is not obvious.
* Add useful logging at INFO, DEBUG, WARNING, and ERROR levels.
* Do not log full file content.
* Do not remove or weaken logging.
* Add meaningful pytest tests.
* Do not leave TODO placeholders for core functionality.

Use requirements.txt approach:

* Do not create pyproject.toml.
* Do not create setup.py.
* Use requirements.txt and requirements-dev.txt.
* README must explain how to run with PYTHONPATH=src.

Technology requirements:

* Python 3.14.5
* PyYAML
* openpyxl
* lxml
* Python standard csv module
* Python standard argparse module
* Python standard logging module with RotatingFileHandler
* pytest
* PyInstaller for output-verifier.exe

Create this structure:

output-verifier/
│
├── src/
│   └── output_verifier/
│       ├── **init**.py
│       ├── **main**.py
│       ├── cli.py
│       ├── config.py
│       ├── config_loader.py
│       ├── constants.py
│       ├── models.py
│       ├── logging_setup.py
│       ├── folder_discovery.py
│       ├── file_matcher.py
│       ├── verification_service.py
│       ├── comparators/
│       │   ├── **init**.py
│       │   ├── base_comparator.py
│       │   ├── xml_comparator.py
│       │   ├── csv_comparator.py
│       │   └── mbi_comparator.py
│       ├── reporting/
│       │   ├── **init**.py
│       │   └── excel_reporter.py
│       └── utilities/
│           ├── **init**.py
│           ├── filename_utils.py
│           └── path_utils.py
│
├── tests/
│   ├── test_config_loader.py
│   ├── test_folder_discovery.py
│   ├── test_file_matcher.py
│   ├── test_xml_comparator.py
│   ├── test_csv_comparator.py
│   ├── test_mbi_comparator.py
│   ├── test_excel_reporter.py
│   └── test_verification_service.py
│
├── config/
│   └── config.yaml
│
├── requirements.txt
├── requirements-dev.txt
├── output-verifier.spec
├── build-exe.cmd
├── run-output-verifier.cmd
├── .gitignore
└── README.md

Business context:
ClaimsXO supports multiple TPAs. First version must support:

* GDI
* HSAB

The QA regression run is already complete. This utility compares Expected Output files against Actual Output files.

The utility must:

1. Discover all supported scenarios.
2. Build scenario inventory from both Expected and Actual folders.
3. Match expected and actual output files.
4. Compare filenames after ignoring dynamic datetime portion.
5. Compare file content using format-specific logic.
6. Apply configured ignore rules.
7. Generate an Excel verification report.
8. Print a console summary.
9. Return correct process exit code.

Folder structure:
The expected and actual parent folders contain scenario folders in this logical format:

Scenarios<scenario_path><run_type><output_type>

scenario_path can have one or more nested folders.

Examples:
Scenarios\test_58545\current\LH1
Scenarios\test_aggregation\3\pre\LH1
Scenarios\test_PTP\CtCare\AddressMissing\hold\manual
Scenarios\test_tickets\test_ticket_81500\Regen\prepre\ALG

Report values for:
Scenarios\test_aggregation\3\pre\LH1

should be:
Scenario: test_aggregation\3
Run Type: pre
Output Type: LH1

Supported run folders:

* current
* pre
* prepre
* hold

Run-folder matching must be case-insensitive.
Report run type in lower case.

Supported output folders:
For GDI:

* LH1
* manual
* ALG

For HSAB:

* WEX

Output-folder matching must be case-insensitive.
Report output type using standard names:

* LH1
* manual
* ALG
* WEX

File discovery rules:

* Recursively scan Expected and Actual parent folders.
* Whenever a supported run folder is found, treat the relative path before the run folder as the scenario path.
* Look only for supported output folders directly under the run folder.
* Read only files directly under a supported output folder.
* Do not recursively compare arbitrary subfolders below an output folder.
* Ignore unrelated folders.
* Ignore unsupported file extensions.
* Supported extensions are .xml, .csv, and .mbi.
* Extension matching must be case-insensitive.
* Preserve original filename in the report.
* If a file has a supported extension but invalid supported filename pattern, report it as Failed with issue:
  Unsupported or invalid filename pattern

Build scenario inventory from the union of Expected and Actual:

* Expected-only scenario must be reported.
* Actual-only scenario must be reported.
* If same scenario/run/output exists in both but neither has supported files, report NotVerified.

Supported GDI files:

1. GDI LH1 XML files
   Output folder:
   LH1

Supported filename patterns:

* GDI_LH1_<datetime>.xml
* GDI_LH1_MMS_<datetime>.xml
* GDI_LH1_FLORES_<datetime>.xml
* GDI_LH1_HNE_<datetime>.xml
* GDI_REGEN_LH1_<datetime>.xml

Datetime is exactly 14 digits:
yyyyMMddHHmmss

Keep these filename patterns in Python code, not YAML.

2. GDI manual CSV files
   Output folder:
   manual

Supported filename patterns:

* GDI_MANUAL_<datetime>.csv
* GDI_MANUAL_PATIENT_<datetime>.csv

Both files:

* Have header row.
* May contain commas inside quoted values.
* May contain double quotes.
* May contain empty values.
* May contain leading or trailing spaces.
* Expected CSV header defines the expected layout.
* Do not hard-code expected CSV columns.
* Do not list all columns in YAML.

3. GDI MBI file
   Output folder:
   ALG

Supported filename pattern:
LumeLight.ClaimFeed.<datetime>.mbi

Datetime is exactly 14 digits:
yyyyMMddHHmmss

MBI rules:

* Delimiter is |
* No header row.
* No trailer row.
* Blank fields may appear as ||
* Leading and trailing spaces inside fields are significant.
* A trailing delimiter is significant.
* Record order matters.
* Field order matters.
* Duplicate records must remain in their original positions.

Supported HSAB files:

Output folder:
WEX

Supported filename patterns:

* HB1_HSAB_CLAIMS_<datetime>.xml
* HB2_HSAB_CLAIMS_<datetime>.xml

Datetime is exactly 14 digits:
yyyyMMddHHmmss

HB1 and HB2:

* Are stored in same WEX folder.
* Have same XML format.
* Use same XML comparator.
* Use same configured HSAB WEX ignored XML paths.
* HB1 must not match HB2.
* HB2 must not match HB1.

Filename matching rule:
Do not compare full filenames directly.
Datetime can differ between Expected and Actual.

Create a normalized filename identity by replacing the 14-digit datetime with <datetime>.

Examples:
GDI_LH1_20260730110000.xml
becomes:
GDI_LH1_<datetime>.xml

GDI_MANUAL_PATIENT_20260730110000.csv
becomes:
GDI_MANUAL_PATIENT_<datetime>.csv

LumeLight.ClaimFeed.20260730110000.mbi
becomes:
LumeLight.ClaimFeed.<datetime>.mbi

HB1_HSAB_CLAIMS_20260730110000.xml
becomes:
HB1_HSAB_CLAIMS_<datetime>.xml

Files must be grouped and matched by normalized filename identity.

Important:

* GDI_MANUAL_<datetime>.csv must not match GDI_MANUAL_PATIENT_<datetime>.csv.
* HB1_HSAB_CLAIMS_<datetime>.xml must not match HB2_HSAB_CLAIMS_<datetime>.xml.
* Sort expected and actual files by original filename inside each identity group.
* If multiple files exist with same identity, compare by position after sorting.
* Report count mismatches.
* Create missing or unexpected file rows for unmatched files.

Record order assumption:
Assume record order is same in expected and actual.
Do not sort records inside files.
Do not create key-based matching.
Do not create multiset comparison.
Compare records by position.

XML comparison:
Use lxml.
Do not compare XML as plain text.

XML rules:

* Parse Expected XML and Actual XML.
* Ignore indentation differences.
* Ignore line-ending differences.
* Ignore attribute-order differences.
* Preserve element order.
* Preserve repeated-element order.
* Preserve meaningful text.
* Do not trim meaningful text values automatically.
* Compare element names exactly.
* Compare attribute names exactly.
* Compare attribute values exactly.
* Compare text values exactly.
* Compare child element count.
* Compare attribute count after ignored paths are applied.
* Attribute order must not matter.
* Element order must matter.
* XML namespaces must be supported.
* Do not silently remove namespaces from comparison.
* Namespace URI differences should remain meaningful unless explicitly ignored.
* Support ignored XML elements and attributes using configured XPath values.
* Apply ignore paths to both Expected and Actual before comparison.
* Invalid XPath syntax is a configuration/system error and should return exit code 2.
* Configured path not found in a specific XML file should not fail comparison. Log warning or debug.

XML differences:
Report first two differences only.
Each difference should include:

* XPath or generated node path
* Difference type
* Expected value
* Actual value

Possible difference types:

* Element missing
* Unexpected element
* Element name mismatch
* Text mismatch
* Attribute missing
* Unexpected attribute
* Attribute value mismatch
* Child count mismatch

CSV comparison:
Use Python standard csv module.
Do not compare CSV as plain text.
Do not manually split by commas.

CSV parser must handle:

* Header row
* Commas inside quoted fields
* Escaped double quotes
* Empty fields
* Quoted empty values
* Leading spaces
* Trailing spaces
* Windows and Unix line endings

CSV comparison rules:

* Compare header column count.
* Compare header names.
* Compare header order.
* Compare data row count.
* Compare row order.
* Compare field count for each row.
* Compare field values by position.
* Compare all values as strings.
* Do not parse or normalize dates, numbers, decimals, or booleans.
* Do not trim values.
* Row numbering should be Excel-style:
  Header = row 1
  First data row = row 2

Ignored CSV columns:
Configured in YAML:
ignore_rules:
GDI:
manual_csv_columns: []
patient_manual_csv_columns: []

Mapping:
GDI_MANUAL_<datetime>.csv uses manual_csv_columns.
GDI_MANUAL_PATIENT_<datetime>.csv uses patient_manual_csv_columns.

No columns are ignored by default.

When ignored columns are configured:

* Match configured column by exact header name.
* Column matching is case-sensitive.
* Remove that column from both Expected and Actual before comparison.
* Preserve order of remaining columns.
* If configured column does not exist, log warning.
* Do not silently ignore misspelled ignored column names.

CSV differences:
Report first two differences only.
Examples:
Header column 4 mismatch, Expected: EmployeeSSN, Actual: EmployeeId
Row count mismatch. Expected: 20, Actual: 19
Row: 5, Column: ClaimNumber, Expected: ABC123, Actual: ABC124
Row: 6, column count mismatch. Expected: 27, Actual: 26

MBI comparison:
Use Python csv parser with delimiter | or another delimiter-safe parser.
Do not use simple string split if it loses delimiter behavior.
Trailing delimiter is significant and must be preserved.

MBI parsing rules:

* Delimiter: |
* No header.
* No trailer.
* Record order matters.
* Field order matters.
* Blank fields matter.
* Leading spaces matter.
* Trailing spaces matter.
* Trailing delimiter matters.
* Duplicate records remain in original positions.
* Blank lines must not be silently discarded unless documented.

These are different:
A|B|C
A|B|C|

The second record has an additional empty field.

MBI comparison:

* Compare record count.
* Compare corresponding record by line number.
* Compare field count for each record.
* Compare fields by one-based position.
* Compare field values exactly.
* Do not trim.
* Do not normalize.

Ignored MBI fields:
Configured in YAML:
ignore_rules:
GDI:
mbi_field_positions: []

Use one-based field positions.
Validate:

* Must be positive integers.
* Zero is invalid.
* Negative values are invalid.
* Duplicates may be de-duplicated with warning.
* Invalid positions are configuration errors and should return exit code 2.

MBI differences:
Report first two differences only.
Examples:
Record count mismatch. Expected: 10, Actual: 9
Record: 4, field count mismatch. Expected: 19, Actual: 18
Record: 4, Field: 7, Expected: APPROVED, Actual: DENIED

Missing, unexpected, and empty scenarios:
Build scenario list from union of Expected and Actual.

If Expected scenario exists but Actual scenario is missing:
Status: Failed
Issue: Expected scenario missing in Actual Outputs

If Actual scenario exists but Expected scenario is missing:
Status: Failed
Issue: Unexpected scenario exists only in Actual Outputs

If Expected file exists but Actual file is missing:
Status: Failed
Issue: Expected file missing

If Actual file exists but Expected file is missing:
Status: Failed
Issue: Unexpected actual file

If both contain no supported files for same scenario/run/output:
Status: NotVerified
Issue: No files available for verification

When normalized filename group count differs:
Status: Failed
Issue: File count mismatch. Expected: X, Actual: Y

Also create file-specific missing or unexpected rows for unmatched files.
Avoid duplicate or confusing report rows.

Supported statuses:
Use exactly:

* Passed
* Failed
* NotVerified

Passed only when:

* Expected file is found.
* Actual file is found.
* Normalized filename identity matches.
* Content matches after applying configured ignore rules.

Failed for:

* Expected scenario missing.
* Unexpected actual scenario.
* Expected output folder missing.
* Unexpected output folder where it contains supported output.
* Expected file missing.
* Unexpected actual file.
* File count mismatch.
* Invalid supported filename pattern.
* Filename type mismatch.
* XML content mismatch.
* CSV content mismatch.
* MBI content mismatch.
* Invalid XML, CSV, or MBI content preventing comparison.

NotVerified only when:

* Both Expected and Actual contain no supported output files for that scenario/run/output.

Exit codes:

* 0 = No Failed records. Passed and NotVerified are allowed.
* 1 = One or more comparison failures.
* 2 = Configuration, system, logging, invalid XPath, invalid ignored MBI position, or report-generation error.

Parsing failure behavior:
If one specific file is malformed:

* Create Failed report row for that file.
* Put parsing error in Issue.
* Continue processing other files where possible.
* Final exit code should be 1.

System error behavior:
Return exit code 2 for:

* YAML cannot be loaded.
* Required configuration missing.
* Unsupported verification type.
* Expected root cannot be accessed.
* Actual root cannot be accessed.
* Report cannot be created.
* Logging cannot be initialized.
* Invalid ignored XPath syntax.
* Invalid MBI ignored-field configuration.
* Unexpected unhandled system error.

Excel report:
Use openpyxl.

Report filename:
<base_file_name>*<verification_type>*<timestamp>.xlsx

Example:
VerificationReport_GDI_20260730113045.xlsx

Report settings come from YAML.

Worksheet name:

* GDI Verification
* HSAB Verification

Required report columns:

1. Verification Type
2. Scenario
3. Run Type
4. Output Type
5. Expected File
6. Actual File
7. Status
8. Issue
9. Difference 1
10. Difference 2

Formatting:

* Bold header row.
* Freeze top row.
* Auto-filter.
* Sensible column widths.
* Wrapped text for Issue and Difference columns.
* Vertical top alignment.
* Status background colors from YAML.
* Add Summary worksheet with:

  * Verification type
  * Execution start time
  * Execution end time
  * Expected root
  * Actual root
  * Total report rows
  * Passed count
  * Failed count
  * NotVerified count
  * Report path
  * Exit code

YAML config:
Create config/config.yaml like this:

solution_type: ClaimsXO

verification_type: GDI
expected_parent_folder: ""
actual_parent_folder: ""

report:
output_folder: "./reports"
base_file_name: "VerificationReport"
include_verification_type: true
include_timestamp: true
timestamp_format: "%Y%m%d%H%M%S"
status_colors:
passed: "#C6EFCE"
failed: "#FFC7CE"
not_verified: "#FFEB9C"

logging:
level: INFO
log_to_console: true
log_to_file: true
output_folder: "./logs"
max_bytes: 10485760
backup_count: 5

ignore_rules:
GDI:
lh1_xml_paths:
- "/LH1StandardClaimsExchange/@CreatedDateTime"
manual_csv_columns: []
patient_manual_csv_columns: []
mbi_field_positions: []

HSAB:
wex_xml_paths: []

Important YAML rule:
Keep stable application rules in Python code, not YAML.
The following must remain in Python code:

* Supported TPAs.
* Supported output folders.
* Supported extensions.
* Filename patterns.
* Datetime format.
* Run folder names.
* File format mappings.
* XML comparison behavior.
* CSV parsing behavior.
* MBI delimiter.
* Record-order behavior.

Configuration validation:
Validate:

* solution_type must be ClaimsXO.
* verification_type must be GDI or HSAB.
* Parent folders must come from YAML or command line.
* Parent folders must exist and be readable.
* Report output folder must be creatable.
* Log folder must be creatable when file logging is enabled.
* Timestamp format must be valid.
* Status colors must be valid #RRGGBB hex colors.
* Log level must be valid.
* max_bytes must be positive integer.
* backup_count must be zero or positive integer.
* XML path lists must contain strings.
* CSV ignored columns must contain strings.
* MBI ignored positions must contain positive integers.
* Invalid XPath syntax should be detected as configuration error.

Configuration precedence:
Command-line argument overrides YAML value.
YAML value overrides application default.
Do not mutate original YAML dictionary unexpectedly.
Build a resolved configuration model.

CLI:
Support:

python -m output_verifier ^
--config "config\config.yaml" ^
--verification-type "GDI" ^
--expected-parent-folder "H:\ExpectedOutputs" ^
--actual-parent-folder "H:\ActualOutputs"

Also support:
--report-output-folder
--log-level

CLI must:

* Display clear help.
* Validate arguments.
* Print user-friendly errors.
* Avoid Python stack traces for expected user errors.
* Log full exception details to log file when possible.

Console summary:
At the end, print:

Verification Type : GDI
Compared Files    : 125
Passed            : 117
Failed            : 5
Not Verified      : 3
Report            : H:\Reports\VerificationReport_GDI_20260730113045.xlsx
Exit Code          : 1

Print summary even when comparison failures occur.
For system error, print concise error and exit code 2.

Logging:
Use Python logging with console and rotating file handlers.

Log:

* Application start.
* Application version.
* Resolved configuration.
* Verification type.
* Expected root.
* Actual root.
* Report path.
* Scenario discovery count.
* Current scenario.
* Current run type.
* Current output type.
* Expected file.
* Actual file.
* Comparison result.
* Warnings.
* Parsing failures.
* System errors.
* Summary counts.
* Exit code.
* Application end.

Do not log complete sensitive file content.
For field differences, log only small values required for troubleshooting.
Mask or truncate very long values.

Data models:
Use dataclasses and enums.

Suggested dataclasses:

* ResolvedConfig
* ReportConfig
* LoggingConfig
* IgnoreRulesConfig
* ScenarioKey
* ScenarioLocation
* DiscoveredOutput
* FileIdentity
* MatchedFilePair
* ComparisonOptions
* ComparisonDifference
* ComparisonResult
* ReportRow
* ExecutionSummary

Suggested enums:

* VerificationType
* OutputType
* VerificationStatus
* FileFormat
* ExitCode

Comparator design:
Create common comparator interface in comparators/base_comparator.py.

Example:
class FileComparator(Protocol):
def compare(
self,
expected_path: Path,
actual_path: Path,
options: ComparisonOptions,
) -> ComparisonResult:
...

Implement:

* XmlComparator
* CsvComparator
* MbiComparator

Do not put format-specific comparison logic inside folder_discovery.py or excel_reporter.py.

Internal TPA profile registry:
Keep mappings in code.

Use a simple registry such as:
TPA_PROFILES = {
VerificationType.GDI: GDI_PROFILE,
VerificationType.HSAB: HSAB_PROFILE,
}

Do not create a complex plugin framework.

GDI profile:

* LH1 folder, XML comparator, GDI.lh1_xml_paths.
* manual folder:

  * GDI_MANUAL_<datetime>.csv uses CSV comparator and GDI.manual_csv_columns.
  * GDI_MANUAL_PATIENT_<datetime>.csv uses CSV comparator and GDI.patient_manual_csv_columns.
* ALG folder:

  * LumeLight.ClaimFeed.<datetime>.mbi uses MBI comparator and GDI.mbi_field_positions.

HSAB profile:

* WEX folder, XML comparator, HSAB.wex_xml_paths.
* HB1_HSAB_CLAIMS_<datetime>.xml
* HB2_HSAB_CLAIMS_<datetime>.xml

Unit tests:
Create meaningful pytest tests. Do not create placeholder tests.

Configuration tests:

* Valid YAML
* Missing YAML
* Invalid YAML
* CLI override
* Missing required path
* Unsupported verification type
* Invalid log level
* Invalid color
* Invalid MBI position
* Invalid XPath syntax

Folder discovery tests:

* Single-level scenario
* Multi-level scenario
* current
* pre
* prepre
* hold
* Unknown folders ignored
* Unsupported files ignored
* Expected-only scenario
* Actual-only scenario
* Empty scenario
* Case-insensitive folder recognition

File matching tests:

* Datetime differs but pattern matches
* HB1 does not match HB2
* GDI_MANUAL does not match GDI_MANUAL_PATIENT
* Multiple files with same pattern
* Expected count greater than Actual
* Actual count greater than Expected
* Invalid filename pattern
* Sorting behavior

XML tests:

* Equal XML
* Different indentation
* Different line endings
* Different attribute order
* Different element order
* Different attribute value
* Different text value
* Ignored attribute
* Ignored element
* Default namespace
* Malformed XML
* First two differences only

CSV tests:

* Equal CSV
* Header mismatch
* Header-order mismatch
* Row-count mismatch
* Row-order mismatch
* Field mismatch
* Comma inside quoted field
* Escaped quote
* Leading-space difference
* Trailing-space difference
* Ignored column
* Malformed CSV
* First two differences only

MBI tests:

* Equal MBI
* Record-count mismatch
* Record-order mismatch
* Field mismatch
* Field-count mismatch
* Empty field using ||
* Trailing delimiter difference
* Leading-space difference
* Trailing-space difference
* Ignored field position
* Duplicate records by position
* First two differences only

Verification service tests:

* Passed result
* Failed result
* NotVerified result
* Expected file missing
* Unexpected file
* Expected-only scenario
* Actual-only scenario
* Mixed Passed, Failed, and NotVerified
* Correct exit code

PyInstaller:
Create:

* output-verifier.spec
* build-exe.cmd

Executable name:
output-verifier.exe

build-exe.cmd should:

1. Create or use virtual environment.
2. Install dependencies.
3. Run pytest.
4. Stop if tests fail.
5. Build executable using PyInstaller.
6. Put output in dist folder.
7. Print generated executable path.

README:
Create complete README with:

* Utility purpose
* Supported TPAs
* Supported output files
* Folder structure
* YAML configuration
* Ignore-rule examples
* Command-line examples
* Exit codes
* Excel report details
* Logging details
* Development setup
* Test execution
* EXE build steps
* Troubleshooting
* Known limitations
* How to add a future TPA
* Windows CMD examples

requirements.txt:
PyYAML
openpyxl
lxml

requirements-dev.txt:
-r requirements.txt
pytest
pyinstaller

Implementation sequence:
Please implement in this order:

1. Create project structure.
2. Implement constants and enums.
3. Implement dataclass models.
4. Implement YAML config loading.
5. Implement CLI config overrides.
6. Implement config validation.
7. Implement logging setup.
8. Implement internal GDI and HSAB TPA profiles.
9. Implement folder discovery.
10. Implement filename recognition and normalized identity matching.
11. Implement XML comparator.
12. Implement CSV comparator.
13. Implement MBI comparator.
14. Implement verification service orchestration.
15. Implement Excel reporter.
16. Implement console summary and exit codes.
17. Add unit tests.
18. Run all tests and fix failures.
19. Add PyInstaller spec.
20. Add CMD scripts.
21. Add README.
22. Review complete solution against requirements.

Important delivery rules:

* Do not stop after skeleton.
* Do not leave TODO placeholders for core functionality.
* Do not claim tests pass unless pytest has actually been executed.
* Keep code simple and understandable.
* If a requirement is difficult or ambiguous, implement the simplest maintainable behavior and document the decision clearly.
