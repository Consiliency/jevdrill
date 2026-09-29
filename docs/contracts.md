# Public contract boundary

Status: draft major version 1, pending the CONTRACT platform gate.

Author fields in `baml_src/contracts.baml`, constraints in `baml_src/boundary.json`, then run `scripts/check_generated_contracts.py --write` with the pinned compiler. Generated Pydantic code lives in `src/baml_sdk`; published JSON schemas live in `schemas`. Never edit these outputs. The compiler fixes its Python import namespace to `baml_sdk`; output directory overrides do not relocate those imports.

Generation comparison validates the compiler manifest and embedded artifact checksum before normalizing complete, length-prefixed authored source filenames from Windows separators to POSIX separators. All remaining bytecode, ABI, build fingerprint and generated code must match. Generated files themselves stay untouched. This narrowly scoped comparison follows the pinned compiler's [ABI 8 artifact encoding](https://github.com/boundaryml/baml/blob/baml-language-0.20.1/baml_language/crates/baml_artifact/src/lib.rs); an ABI change fails closed until reviewed. Negative tests reject corrupt checksums, undeclared paths and changed instruction bytes.

Use `jevdrill.contracts.parse_contract(name, payload)` at every public boundary. It checks JSON portability, strict schemas and named semantic rules before creating an immutable serialized snapshot. Generated Pydantic constructors alone are permissive and are not public input validators. Model and dictionary views are fresh copies. `ContractError` avoids including rejected input values.

The registry terms include `execution_plan`, `execution_run`, `routing_decision`, `measurement`, `settings` and `comparison_experiment`; their exact identifiers and owners are in `vocabulary.yaml`. Five routing outcomes are separate tagged shapes. Only `ready` includes an executable plan. Contract shapes do not establish model availability, spending authority or execution permission.

## Canonical payload digest

Version 1 uses SHA-256 over UTF-8 JSON with no whitespace. Each value is tagged: `["null"]`, `["boolean", value]`, `["string", value]`, `["number", hex]`, `["array", tagged_items]`, or `["object", sorted_key_value_pairs]`. Number hex is the big-endian IEEE-754 double representation; negative zero becomes positive zero. Whole-number magnitudes above 2^53−1, nonfinite numbers and lone Unicode surrogates are rejected. Keys sort by Unicode scalar value, arrays retain order, and strings are not normalized. Money uses decimal strings.

The complete validated payload is hashed, with no implicit field exclusions. Durable idempotency lookup will scope keys by project, producer and operation; HOST must test that same-key/same-digest is duplicate and same-key/different-digest is conflict. The digest helper does not implement durable storage.

## Events and transport

`boundary.json` records execution and experiment transitions. Corrections append a new event referencing the superseded event; self-correction is rejected. Storage must preserve originals, rebuild projections and prevent late events from regressing terminal outcomes. These persistence behaviors belong to HOST/LEARN.

Report acknowledgment variants are accepted, duplicate, conflict and rejected. Durable acknowledgment is reserved for accepted/duplicate after commit. Proposed CLI exits are 0 for typed responses, 2 for invalid input/version, 3 for idempotency conflicts and 4 for transport/storage failure. No routing CLI is implemented yet. Major-version negotiation precedes requests; version 1 accepts no deprecated aliases. Future changes require regenerated fixtures and repeated language/platform checks.

## JEV telemetry

The pinned bridge is tested with a synthetic loopback server. Wire capture is disabled, but upstream events still contain task arguments and response headers. `telemetry.retain_jev_call` retains only numeric timing and usage fields from JEV call events. Other events and all bodies, headers, arguments and provider metadata are discarded. Missing usage stays unknown; separate usage events are not added to the same call's counters. This projection is not yet connected to a production adapter.

Cancellation is tested through the async bridge. The future adapter must preserve cancellation and convert typed provider errors into redacted routing failures. A Python-side provider object currently fails the bridge's interface-union check when passed as a FunctionSpec client override; the tested BAML-side client construction works. Keep client overrides inside BAML until an upstream fix is proven.
