# ClaimsXO / EnrollmentXO Output Verifier — Documentation Index

This folder contains detailed documentation for the **output-verifier** utility based on the current codebase.

| Document | Audience | Contents |
| --- | --- | --- |
| [Developer_Guide.md](Developer_Guide.md) | New developers, maintainers | Architecture, business logic, end-to-end flow, configuration, extending TPAs, testing, packaging |
| [Function_Guide.md](Function_Guide.md) | Developers reading/changing code | Module-by-module API reference for every public class and function |

## Quick context

- **Product**: Expected vs Actual output verification after QA regression
- **Solutions**: ClaimsXO, EnrollmentXO
- **Package**: `output_verifier` under `src/`
- **ClaimsXO TPAs**: GDI, HSAB
- **EnrollmentXO TPAs**: ABG, GDI, HSAB
- **Formats**: XML (lxml), CSV, MBI, DelimitedText
- **Outputs**: Excel report + rotating log file + console summary + exit code

## Recommended reading order for a new developer

1. This index
2. Developer Guide — sections on purpose, architecture, business rules, run flow
3. Function Guide — `verification_service`, `folder_discovery`, `file_matcher`, comparators
4. Developer Guide — configuration, ignore rules, extending TPAs, tests
