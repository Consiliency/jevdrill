# CONTRACT implementation decisions

Status: implementation decisions pending phase verification; not a contract freeze.

The user selected public Consiliency/jevdrill as the Git home. Initialization is complete; no source publication or canonical adoption is implied.

## Source coverage

`evidence/CONTRACT/coverage.json` accounts for every JD decision and every paragraph/list/table/example block in all 25 draft sections. Review R/C/P items link to amended criteria. Source digests and exact criterion text detect drift. The checker verifies reference integrity; semantic adequacy still requires review. No mapping is evidence that a requirement is implemented.

Original stage ordering is superseded by JD-046/JD-062/JD-065. Automatic objective recommendation, skill rewriting, additional provider/host adapters and direct MCP/API exposure remain later scope. The CLI and first agent-harness adapter remain in scope. Historical research counts are context, never target acceptance values.

## Contract construction

BAML is the authored field/type authority. Generated Python remains untouched. A deterministic boundary layer derives strict schema from generated models and supplements it using authored metadata in `baml_src/boundary.json`; this metadata references fields rather than restating their types. All declared fields are required, including nullable fields, unless explicitly marked omittable. Unsupported metadata paths fail generation.

Public JSON is validated before generated Pydantic parsing. Unknown fields, nonfinite values, wrong scalar types and invalid semantic combinations are rejected. Python and Node consume the same schemas and fixtures; semantic rules travel with them. Public models are immutable after parsing. Nested values must not permit mutation to change a recorded plan unnoticed; canonical hashes revalidate before use.

Report acknowledgments distinguish accepted, duplicate, conflict and rejected. Only accepted/duplicate acknowledge durable storage. Corrections append linked events. Completion is not acceptance; host preference is never a test result. Terminal execution state cannot regress when earlier events arrive.

CLI version 1 uses exit codes 0 for a handled typed response, 2 for invalid input/version, 3 for conflicting idempotency reuse, 4 for transport/storage failure preventing a normal response. JSON status is authoritative. The host starts the total deadline before process launch; cancellation must not authorize execution from a partial response. Retrying an uncertain commit uses the original key.

Breaking contract changes require a major version. Version 1 initially has no deprecated field aliases. Adapters negotiate supported major versions before use. Every amended contract adds positive/negative fixtures and repeats Python/Node parity and the OS matrix, including named validators.

## Open questions

Q-01/Q-03: contract implementation owns exact event/adapter shapes and cancellation behavior, blocking CONTRACT freeze. Q-04: toolchain implementation owns platform/version proof, blocking CONTRACT freeze. Q-05: vocabulary implementation owns deterministic scope enforcement, blocking CONTRACT freeze.

Q-06/Q-07: routing/costing implementation owns provider inventory, token bounds and budgets, blocking ROUTE acceptance. No enabled model or spending authority is inferred. Q-08: catalog implementation starts with no optional resources automatically enabled; user admission remains explicit and blocks only use of that resource.

Q-09/Q-10: storage/privacy implementation owns storage recovery and archive details; ROUTE supplies collection exclusions, opt-out and deletion before storing real tasks, LEARN supplies archival. Q-11: experiment implementation owns isolation and budgets before EXPERIMENT execution. Missing limits disable experiments.

Q-12/Q-13: evaluation implementation and the user own consequential quality floors, regression margins and empirical calibration. Schemas permit explicit thresholds; no live release-holdout evaluation or policy promotion is permitted until thresholds are recorded before exposure. This does not block offline boundary tests or synthetic metric fixtures.

Q-14: Git-home choice is resolved; governance implementation still owns adoption/representation proofs before PREPARE. No canonical adoption is performed here.
