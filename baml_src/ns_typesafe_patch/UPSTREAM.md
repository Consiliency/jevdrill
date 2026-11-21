# Pinned TypeSafe client patch

Derived from [BoundaryML/baml, baml-language-0.20.1](https://github.com/BoundaryML/baml/tree/baml-language-0.20.1/baml_language/crates/baml_builtins2/baml_std/typesafeai), licensed under Apache-2.0. The full license is in `LICENSE` and ships in the Python package as `BAML_TYPESAFE_LICENSE`.

Original SHA-256 digests:

- `client.baml`: `16037c676b8cb05ededc0493572fbbe4132227e2c76a8a170f5e4d4834b4b538`
- `ns_internal/jev.baml`: `02dfddea40678d582d3fb4bf069705acb394ecb183832e9090c038437d56d8c3`

Local changes: namespace relocation; nullable, independently validated counters; numeric observation callback before answer decoding; standard BAML usage only when both counters are known; internal `Plan.state` renamed `task_state` to satisfy the vocabulary lint (the wire key remains `state`). Request construction, reflection traversal and answer decoding retain the pinned implementation. Answer structure is validated after the observation callback so malformed answers do not erase known usage.

`ObserveCandidate` uses this client. The original upstream client remains available for parity controls. Production calls keep BAML transport, timeouts, parsing and disabled wire capture. No HTTP proxy or second provider call is introduced.

Remove this copy after a reviewed upstream version preserves partial counters and passes the request, score-boundary, failure, privacy, timeout and cancellation tests in `tests/contracts/test_jev_boundary.py`. A numeric-success test alone is insufficient. Do not update this copy independently of its source bindings and parity evidence.
