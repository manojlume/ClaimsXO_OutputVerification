You are a senior QA Automation Engineer and senior Python developer.

We already have an existing Python output-verifier utility for ClaimsXO. Now we need to enhance the existing codebase to support another solution type called EnrollmentXO.

Important: Do not rewrite the whole application from scratch. Extend the existing architecture cleanly.

Project name:
output-verifier

Python package name:
output_verifier

Run command:
python -m output_verifier --config config/config.yaml

Executable name later:
output-verifier.exe

Important coding standards:

* Keep code simple, readable, and production-grade.
* Follow Clean Code principles by Robert C. Martin.
* Do not over-engineer.
* Use meaningful and self-explaining names.
* Do not use short or abbreviated variable names, function names, class names, or file names.
* Use pathlib.
* Use type hints.
* Use dataclasses where suitable.
* Use enums for fixed values.
* Keep each function focused on one responsibility.
* Avoid deeply nested code.
* Avoid duplicate logic.
* Do not use global mutable state.
* Do not hard-code user-specific paths.
* Do not suppress exceptions without logging.
* Do not print from library modules. Use logging.
* Only CLI console summary may use print.
* Add simple English docstrings for every public class and public function.
* Add useful logging at INFO, DEBUG, WARNING, and ERROR levels.
* Do not remove or weaken existing logging.
* Add or update meaningful pytest tests.
* Use requirements.txt approach.
* Do not create pyproject.toml.
* Do not create setup.py.

Main goal:
Add EnrollmentXO support to the existing output-verifier utility in the same clean style as ClaimsXO.

The application must support:

solution_type: ClaimsXO
verification_type: GDI or HSAB

solution_type: EnrollmentXO
verification_type: ABG or GDI or HSAB

Do not mix EnrollmentXO rules directly into ClaimsXO profiles. Add solution-level profile support.

============================================================
PART 1: UPDATE YAML STRUCTURE FOR CLAIMSXO AND ENROLLMENTXO
===========================================================

Currently ClaimsXO YAML uses this old structure:

ignore_rules:
GDI:
lh1_xml_paths:
- "/LH1StandardClaimsExchange/@CreatedDateTime"
- "/LH1StandardClaimsExchange/@FileDateTime"
- "//*[local-name()='CustomProperties'][@KeyName='CXC ID']/@KeyValue"
manual_csv_columns:
- "FileDate"
- "CXCId"
patient_manual_csv_columns:
- "FileDate"
mbi_field_positions: [19]
HSAB:
wex_xml_paths: []

This structure is no longer enough because EnrollmentXO also has GDI and HSAB. The keys GDI and HSAB are ambiguous unless they are grouped under solution_type.

Required new YAML structure:

solution_type: ClaimsXO
verification_type: GDI

expected_parent_folder: ""
actual_parent_folder: ""

report:
output_folder: "./reports"
base_file_name: "VerificationReport"
include_solution_type: true
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
ClaimsXO:
GDI:
lh1_xml_paths:
- "/LH1StandardClaimsExchange/@CreatedDateTime"
- "/LH1StandardClaimsExchange/@FileDateTime"
- "//*[local-name()='CustomProperties'][@KeyName='CXC ID']/@KeyValue"
manual_csv_columns:
- "FileDate"
- "CXCId"
patient_manual_csv_columns:
- "FileDate"
mbi_field_positions:
- 19

```
HSAB:
  wex_xml_paths: []
```

EnrollmentXO:
ABG:
alegeus_mbi_field_positions: []
report_csv_columns: []

```
GDI:
  wexhealth_field_positions: []
  report_csv_columns: []

HSAB:
  enrollment_import_field_positions: []
  report_csv_columns: []
```

Implementation requirements for YAML/config:

1. Add SolutionType enum with:

   * ClaimsXO
   * EnrollmentXO

2. Keep VerificationType enum with:

   * ABG
   * GDI
   * HSAB

3. Update config model to include:

   * solution_type
   * verification_type
   * expected_parent_folder
   * actual_parent_folder
   * report
   * logging
   * ignore_rules

4. Update ignore-rule parsing so it reads using this path:
   ignore_rules[solution_type][verification_type]

5. Do not read ClaimsXO rules directly from:
   ignore_rules[GDI]
   ignore_rules[HSAB]

6. Keep temporary backward compatibility for old ClaimsXO YAML if it already exists:

   * If ignore_rules has GDI or HSAB directly under it, still load it.
   * Log a WARNING:
     "Old ignore_rules structure is deprecated. Please move rules under ignore_rules.ClaimsXO."

7. Update config/config.yaml example to show both ClaimsXO and EnrollmentXO sections.

8. Update README to explain the new solution_type based YAML.

9. Add or update tests:

   * ClaimsXO GDI ignore rules load from ignore_rules.ClaimsXO.GDI
   * ClaimsXO HSAB ignore rules load from ignore_rules.ClaimsXO.HSAB
   * EnrollmentXO ABG ignore rules load from ignore_rules.EnrollmentXO.ABG
   * EnrollmentXO GDI ignore rules load from ignore_rules.EnrollmentXO.GDI
   * EnrollmentXO HSAB ignore rules load from ignore_rules.EnrollmentXO.HSAB
   * Old ClaimsXO ignore_rules.GDI still works temporarily with warning
   * Invalid solution_type fails with exit code 2
   * Invalid verification_type for solution fails with exit code 2

============================================================
PART 2: ADD SOLUTION-LEVEL PROFILE REGISTRY
===========================================

Add a simple internal registry. Do not create a complex plugin framework.

Required design:

SOLUTION_PROFILES = {
SolutionType.CLAIMS_XO: CLAIMS_XO_PROFILES,
SolutionType.ENROLLMENT_XO: ENROLLMENT_XO_PROFILES,
}

CLAIMS_XO_PROFILES = {
VerificationType.GDI: CLAIMS_XO_GDI_PROFILE,
VerificationType.HSAB: CLAIMS_XO_HSAB_PROFILE,
}

ENROLLMENT_XO_PROFILES = {
VerificationType.ABG: ENROLLMENT_XO_ABG_PROFILE,
VerificationType.GDI: ENROLLMENT_XO_GDI_PROFILE,
VerificationType.HSAB: ENROLLMENT_XO_HSAB_PROFILE,
}

If the current code already has TPA profile registry, extend it to include solution_type cleanly.

The verification service should select the correct profile using both:

* solution_type
* verification_type

Do not infer solution type from folder names.

============================================================
PART 3: ENROLLMENTXO FOLDER DISCOVERY RULES
===========================================

EnrollmentXO uses the same scenario/run/output folder concept as ClaimsXO.

Logical structure:

<scenario_path><run_type><output_folder>

scenario_path can have one or more nested folders.

Supported run folders:

* current
* pre
* prepre
* hold

Run folder matching must be case-insensitive.
Report run type in lower case.

Build scenario inventory from the union of Expected and Actual roots:

* Expected-only scenario should be reported as Failed.
* Actual-only scenario should be reported as Failed.
* If both expected and actual scenario/run/output exist but no supported files exist, report NotVerified.

EnrollmentXO supported output folders:

For ABG:

* alegeus
* reports

For GDI:

* WexHealth
* reports

For HSAB:

* HSABEnrollmentImport
* reports

Output-folder matching must be case-insensitive.
Report standard output folder names exactly as:

* alegeus
* reports
* WexHealth
* HSABEnrollmentImport

Only process files directly inside supported output folders.
Do not recursively compare arbitrary subfolders below output folders.
Ignore unsupported folders.
Ignore unsupported extensions.

Supported EnrollmentXO extensions:

* .mbi
* .txt
* .csv

Extension matching must be case-insensitive.
Preserve original filename in report.

If a file has a supported extension but does not match any supported filename pattern for that output folder, report Failed with issue:
Unsupported or invalid filename pattern

============================================================
PART 4: COMMON DELIMITED TEXT COMPARATOR
========================================

Important design decision:
Use one common DelimitedTextComparator for EnrollmentXO delimited text files.

Do not create separate comparators like:

* AbgMbiComparator
* GdiWexHealthComparator
* HsabEnrollmentComparator

Instead, create or update one reusable comparator:

DelimitedTextComparator

It should support:

* delimiter
* has_header
* ignored_field_positions
* ignored_columns
* compare_trailing_empty_fields

Use it for:

* ABG alegeus .mbi files with comma delimiter, no header
* GDI WexHealth .txt files with pipe delimiter, no header
* HSAB HSABEnrollmentImport .txt files with comma delimiter, no header
* reports .csv files with comma delimiter, header row

Rules for DelimitedTextComparator:

* Use Python standard csv module where practical.
* Do not manually split by comma.
* Record order matters.
* Field order matters.
* Duplicate records remain in original positions.
* Do not sort records inside files.
* Do not trim field values.
* Do not normalize dates.
* Do not normalize numbers.
* Do not normalize decimals.
* Do not normalize booleans.
* Compare values as strings.
* Empty fields matter.
* Leading spaces matter.
* Trailing spaces matter.
* For pipe-delimited files, trailing delimiter must be significant.
* Report first two differences only.

For files with header:

* Compare header column count.
* Compare header names.
* Compare header order.
* Compare data row count.
* Compare row order.
* Compare field count for each row.
* Compare values by position.
* Ignored columns should be configurable.
* Ignored column matching should be exact and case-sensitive.
* If configured ignored column does not exist, log a WARNING.

For files without header:

* Compare record count.
* Compare corresponding record by line number.
* Compare field count for each record.
* Compare fields by one-based field position.
* Ignored field positions should be configurable.
* Ignored field positions are one-based.
* Validate ignored field positions:

  * Must be positive integer
  * Zero is invalid
  * Negative is invalid
  * Duplicate values can be de-duplicated with warning
  * Invalid values are configuration errors and return exit code 2

Difference examples:

For header files:
Header column 4 mismatch. Expected: EmployeeSSN, Actual: EmployeeId
Row count mismatch. Expected: 20, Actual: 19
Row: 5, Column: ClaimNumber, Expected: ABC123, Actual: ABC124
Row: 6, column count mismatch. Expected: 27, Actual: 26

For no-header files:
Record count mismatch. Expected: 10, Actual: 9
Record: 4, field count mismatch. Expected: 19, Actual: 18
Record: 4, Field: 7, Expected: APPROVED, Actual: DENIED

Keep existing ClaimsXO comparators working. If ClaimsXO already has MBI comparator, do not break it. But if possible, reuse DelimitedTextComparator safely only when behavior matches.

============================================================
PART 5: ENROLLMENTXO ABG PROFILE
================================

EnrollmentXO ABG output folders:

* alegeus
* reports

ABG alegeus output:
Folder:
alegeus

Supported extension:
.mbi

Comparator:
DelimitedTextComparator

Delimiter:
comma

Has header:
false

Rules:

* Record order matters.
* Field order matters.
* Empty fields matter.
* Leading and trailing spaces matter.
* Duplicate records remain in original positions.
* Do not trim values.
* Do not normalize values.

Supported filename patterns:

1. Export_<runtime_timestamp>*Cafeteria_XML*<business_date>_<sequence_or_suffix>.mbi

Examples:
Export_20260730141107524_Cafeteria_XML_20210301_0002.mbi
Export_20260730142252620_Cafeteria_XML_20210301_0045_after.mbi
Export_20260730142239297_Cafeteria_XML_20210301_0045_before.mbi
Export_20260730142047429_Cafeteria_XML_20210301_0016_2.mbi

The runtime timestamp immediately after Export_ is dynamic and must be ignored during filename matching.
The business date, sequence, before/after suffix, and _2 suffix must remain part of normalized identity.

Normalize:
Export_20260730141107524_Cafeteria_XML_20210301_0002.mbi

to:
Export_<runtime_timestamp>_Cafeteria_XML_20210301_0002.mbi

ABG reports output:
Folder:
reports

Supported extension:
.csv

Comparator:
DelimitedTextComparator

Delimiter:
comma

Has header:
true

Supported filename patterns:

1. ExceptionReport_<runtime_timestamp>*Cafeteria_XML*<business_date>_<sequence_or_suffix>.csv
2. ChangeReport_<runtime_timestamp>*Cafeteria_XML*<business_date>_<sequence_or_suffix>.csv

Examples:
ExceptionReport_20260730141402865_Cafeteria_XML_20210301_0036.csv
ChangeReport_20260730142250614_Cafeteria_XML_20210301_0045_after.csv

Normalize:
ExceptionReport_20260730141402865_Cafeteria_XML_20210301_0036.csv

to:
ExceptionReport_<runtime_timestamp>_Cafeteria_XML_20210301_0036.csv

ABG ignore rules from YAML:
ignore_rules:
EnrollmentXO:
ABG:
alegeus_mbi_field_positions: []
report_csv_columns: []

============================================================
PART 6: ENROLLMENTXO GDI PROFILE
================================

EnrollmentXO GDI output folders:

* WexHealth
* reports

GDI WexHealth output:
Folder:
WexHealth

Supported extension:
.txt

Comparator:
DelimitedTextComparator

Delimiter:
pipe |

Has header:
false

Rules:

* Record order matters.
* Field order matters.
* Empty fields matter.
* Leading and trailing spaces matter.
* Trailing delimiter matters.
* Duplicate records remain in original positions.
* Do not trim values.
* Do not normalize values.

Supported filename pattern:
GDI_WEXHealth_<runtime_timestamp>.txt

Example:
GDI_WEXHealth_20240710125335036.txt

Normalize:
GDI_WEXHealth_20240710125335036.txt

to:
GDI_WEXHealth_<runtime_timestamp>.txt

GDI reports output:
Folder:
reports

Supported extension:
.csv

Comparator:
DelimitedTextComparator

Delimiter:
comma

Has header:
true

Supported filename patterns:

1. GDI_ChangeReport_GDI_EN_ALL_<source_date>*<optional_suffix>*<runtime_timestamp>.csv
2. GDI_ExceptionReport_GDI_EN_ALL_<source_date>*<optional_suffix>*<runtime_timestamp>.csv

Examples:
GDI_ChangeReport_GDI_EN_ALL_12122022_after_20240710125331939.csv
GDI_ChangeReport_GDI_EN_ALL_12122022_after1_20240710125443922.csv
GDI_ExceptionReport_GDI_EN_ALL_12122022_after_20240710125520447.csv
GDI_ExceptionReport_GDI_EN_ALL_12122022_20240710130006075.csv

Only the final runtime timestamp before .csv is dynamic.
Keep source date and optional suffix such as after or after1 as part of normalized identity.

Normalize:
GDI_ChangeReport_GDI_EN_ALL_12122022_after_20240710125331939.csv

to:
GDI_ChangeReport_GDI_EN_ALL_12122022_after_<runtime_timestamp>.csv

Normalize:
GDI_ExceptionReport_GDI_EN_ALL_12122022_20240710130006075.csv

to:
GDI_ExceptionReport_GDI_EN_ALL_12122022_<runtime_timestamp>.csv

GDI ignore rules from YAML:
ignore_rules:
EnrollmentXO:
GDI:
wexhealth_field_positions: []
report_csv_columns: []

============================================================
PART 7: ENROLLMENTXO HSAB PROFILE
=================================

EnrollmentXO HSAB output folders:

* HSABEnrollmentImport
* reports

HSABEnrollmentImport output:
Folder:
HSABEnrollmentImport

Supported extension:
.txt

Comparator:
DelimitedTextComparator

Delimiter:
comma

Has header:
false

Rules:

* Record order matters.
* Field order matters.
* Empty fields matter.
* Leading and trailing spaces matter.
* Duplicate records remain in original positions.
* Do not trim values.
* Do not normalize values.

Supported filename pattern: <prefix>_<runtime_timestamp>.txt

The file can contain spaces or retry suffixes before the final runtime timestamp.

Examples:
202162_PROD_WUT584_CollectiveHealth_394332_HSAB_Eligibility_20240101_061701_20260728230014069.txt
202162_PROD_WUT584_CollectiveHealth_394332_HSAB_Eligibility_20240101_0618 2R_20260728230043096.txt
202162_PROD_WUT584_CollectiveHealth_394332_HSAB_Eligibility_20240101_0617_1R_20260728230028777.txt

Only the final runtime timestamp before .txt is dynamic.
Everything before the final runtime timestamp remains part of normalized identity.

Normalize:
202162_PROD_WUT584_CollectiveHealth_394332_HSAB_Eligibility_20240101_061701_20260728230014069.txt

to:
202162_PROD_WUT584_CollectiveHealth_394332_HSAB_Eligibility_20240101_061701_<runtime_timestamp>.txt

HSAB reports output:
Folder:
reports

Supported extension:
.csv

Comparator:
DelimitedTextComparator

Delimiter:
comma

Has header:
true

Supported filename patterns:

1. HSAB_ChangeReport_<prefix>_<runtime_timestamp>.csv
2. HSAB_ExceptionReport_<prefix>_<runtime_timestamp>.csv

Examples:
HSAB_ChangeReport_PROD_WUT584_CollectiveHealth_394332_HSAB_Eligibility_20240101_061701_20260728230012020.csv
HSAB_ExceptionReport_PROD_UOM488_HSAB_FSAEligibility_20231212_013508_20260728230551464.csv

Only the final runtime timestamp before .csv is dynamic.
Everything before it remains part of normalized identity.

Normalize:
HSAB_ChangeReport_PROD_WUT584_CollectiveHealth_394332_HSAB_Eligibility_20240101_061701_20260728230012020.csv

to:
HSAB_ChangeReport_PROD_WUT584_CollectiveHealth_394332_HSAB_Eligibility_20240101_061701_<runtime_timestamp>.csv

HSAB ignore rules from YAML:
ignore_rules:
EnrollmentXO:
HSAB:
enrollment_import_field_positions: []
report_csv_columns: []

============================================================
PART 8: FILE MATCHING RULES
===========================

Do not compare complete filenames directly.
Runtime timestamp can differ between Expected and Actual.

Each supported filename pattern must produce a normalized filename identity.

Match expected and actual files only when normalized identity is the same.

If multiple files have same normalized identity:

1. Sort expected files by original filename.
2. Sort actual files by original filename.
3. Compare by position after sorting.
4. Report count mismatch if counts differ.
5. Create missing or unexpected file rows for unmatched files.

Invalid supported-extension files:
If a file has extension .mbi, .txt, or .csv but does not match any supported pattern for the output folder, report:
Status: Failed
Issue: Unsupported or invalid filename pattern

Do not silently ignore these files.

============================================================
PART 9: REPORT CHANGES
======================

Current ClaimsXO report may have columns like:
Verification Type, Scenario, Run Type, Output Type, Expected File, Actual File, Status, Issue, Difference 1, Difference 2

Update report to include Solution Type.

Required columns:

1. Solution Type
2. Verification Type
3. Scenario
4. Run Type
5. Output Type
6. Expected File
7. Actual File
8. Status
9. Issue
10. Difference 1
11. Difference 2

Worksheet name should include solution type and verification type.

Examples:
ClaimsXO GDI Verification
ClaimsXO HSAB Verification
EnrollmentXO ABG Verification
EnrollmentXO GDI Verification
EnrollmentXO HSAB Verification

Report filename:
<base_file_name>*<solution_type>*<verification_type>_<timestamp>.xlsx

Examples:
VerificationReport_ClaimsXO_GDI_20260730153000.xlsx
VerificationReport_EnrollmentXO_ABG_20260730153000.xlsx

Use YAML:
report:
include_solution_type: true
include_verification_type: true
include_timestamp: true

Do not hard-code report file name.

============================================================
PART 10: EXIT CODE RULES
========================

Keep the same exit code behavior:

0 = no Failed rows. Passed and NotVerified are allowed.
1 = one or more comparison failures.
2 = configuration, system, logging, invalid ignore-rule, or report-generation error.

If one file is malformed:

* Create Failed report row.
* Continue where possible.
* Final exit code should be 1.

If config is invalid:

* Return exit code 2.

============================================================
PART 11: TEST REQUIREMENTS
==========================

Add or update meaningful pytest tests.

Configuration tests:

* New YAML structure loads ClaimsXO GDI rules.
* New YAML structure loads ClaimsXO HSAB rules.
* New YAML structure loads EnrollmentXO ABG rules.
* New YAML structure loads EnrollmentXO GDI rules.
* New YAML structure loads EnrollmentXO HSAB rules.
* Old ClaimsXO ignore_rules.GDI structure still works temporarily with warning.
* Invalid solution_type fails.
* Invalid verification_type for EnrollmentXO fails.
* Invalid ignored field position fails.

Folder discovery tests:

* EnrollmentXO ABG discovers alegeus folder.
* EnrollmentXO ABG discovers reports folder.
* EnrollmentXO GDI discovers WexHealth folder.
* EnrollmentXO GDI discovers reports folder.
* EnrollmentXO HSAB discovers HSABEnrollmentImport folder.
* EnrollmentXO HSAB discovers reports folder.
* Nested scenario paths are handled.
* current and pre run folders are handled.
* Case-insensitive output folder matching works.
* Empty scenario/run/output returns NotVerified.

Filename identity tests:

* ABG Export runtime timestamp is ignored.
* ABG ExceptionReport runtime timestamp is ignored.
* ABG ChangeReport runtime timestamp is ignored.
* GDI WEXHealth runtime timestamp is ignored.
* GDI ChangeReport final timestamp is ignored.
* GDI ExceptionReport final timestamp is ignored.
* HSAB import final timestamp is ignored.
* HSAB ChangeReport final timestamp is ignored.
* HSAB ExceptionReport final timestamp is ignored.
* Different identities do not match.
* Invalid filename pattern is reported.

Delimited comparator tests:

* ABG comma-delimited .mbi equal.
* ABG comma-delimited .mbi field mismatch.
* GDI pipe-delimited .txt equal.
* GDI pipe-delimited .txt field mismatch.
* GDI pipe-delimited trailing delimiter difference.
* HSAB comma-delimited .txt equal.
* HSAB comma-delimited .txt field mismatch.
* CSV report equal.
* CSV report header mismatch.
* CSV report row mismatch.
* CSV ignored column works.
* First two differences only.

Verification service tests:

* EnrollmentXO ABG Passed result.
* EnrollmentXO GDI Passed result.
* EnrollmentXO HSAB Passed result.
* Expected file missing.
* Unexpected actual file.
* Expected-only scenario.
* Actual-only scenario.
* NotVerified empty scenario.
* Mixed Passed, Failed, and NotVerified.
* Correct exit code.

Report tests:

* Report contains Solution Type column.
* Worksheet name includes solution and verification type.
* Report filename includes solution type, verification type, and timestamp.
* ClaimsXO report still works.
* EnrollmentXO report works.

============================================================
PART 12: README UPDATE
======================

Update README to include:

1. Supported solution types:

   * ClaimsXO
   * EnrollmentXO

2. ClaimsXO supported TPAs:

   * GDI
   * HSAB

3. EnrollmentXO supported TPAs:

   * ABG
   * GDI
   * HSAB

4. EnrollmentXO folder structure:
   <scenario_path><run_type><output_folder>

5. EnrollmentXO output folders:
   ABG:

   * alegeus
   * reports

   GDI:

   * WexHealth
   * reports

   HSAB:

   * HSABEnrollmentImport
   * reports

6. YAML examples for:

   * ClaimsXO GDI
   * ClaimsXO HSAB
   * EnrollmentXO ABG
   * EnrollmentXO GDI
   * EnrollmentXO HSAB

7. Explain that ignore_rules are now grouped by solution_type and verification_type.

8. Explain that old ClaimsXO ignore_rules.GDI format is deprecated.

9. Explain common DelimitedTextComparator behavior.

10. Explain command examples:

python -m output_verifier --config config/config.yaml --solution-type EnrollmentXO --verification-type ABG --expected-parent-folder "H:\Expected" --actual-parent-folder "H:\Actual"

python -m output_verifier --config config/config.yaml --solution-type ClaimsXO --verification-type GDI --expected-parent-folder "H:\Expected" --actual-parent-folder "H:\Actual"

============================================================
PART 13: FINAL CHECKS
=====================

After implementation:

1. Run pytest.
2. Fix all test failures.
3. Confirm no pyproject.toml or setup.py was created.
4. Confirm package name is still output_verifier.
5. Confirm ClaimsXO existing behavior still works.
6. Confirm EnrollmentXO ABG, GDI, HSAB profiles work.
7. Confirm logging is still present.
8. Confirm report generation still works.
9. Confirm exit codes still work.
10. Confirm README is updated.

Do not leave TODO placeholders for core logic.
Do not claim tests pass unless pytest has actually been executed.
Keep the code simple and easy to understand.
