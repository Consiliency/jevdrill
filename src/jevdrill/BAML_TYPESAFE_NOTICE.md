# Third-party attribution

The generated BAML program includes modified TypeSafe client code from BoundaryML/baml, tag baml-language-0.20.1, under Apache-2.0. See the accompanying `BAML_TYPESAFE_LICENSE`.

Source: https://github.com/BoundaryML/baml/tree/baml-language-0.20.1/baml_language/crates/baml_builtins2/baml_std/typesafeai

JEV Drill modifications relocate the namespace, preserve partial token counts, and report sanitized observations before answer decoding. Request construction and answer semantics retain the pinned implementation. Source provenance and removal criteria are recorded in `baml_src/ns_typesafe_patch/UPSTREAM.md` in the source repository.
