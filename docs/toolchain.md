# Toolchain

The implementation targets CPython 3.14 (`requires-python >=3.14`), following the owner decision of November 19, 2026 to move the organization to Python 3.14. The contract foundation was first verified on CPython 3.13, the minor used by the isolated BAML proof; that evidence is retained under `evidence/CONTRACT/history/python-3.13`. Other Python minors remain unsupported until their complete compatibility matrix is recorded.

Use `uv sync --locked` and `npm ci`. Runtime dependencies and developer tools are locked in `uv.lock`; Node is a development-only cross-language schema consumer. There is no routing command until ROUTE implements it.

BAML compiler and bridge must both be 0.20.1. Set `BAML_CLI` to the verified compiler executable; generation checks reject a different version. Generated package imports currently initialize the bridge. This dependency is explicit, not a runtime-free contract claim. Generated files and schema exports are checked in; never edit them manually.

The CONTRACT gate requires native Linux, macOS and Windows results for Python 3.14; see `evidence/CONTRACT/platforms`. The earlier 3.13 matrix passed on Linux x86_64/Python 3.13.15, macOS arm64/Python 3.13.7 and Windows AMD64/Python 3.13.15 and is historical evidence only. This establishes the contract foundation's tested matrix, not support for unimplemented storage, scheduling or host features. A workflow file, wheel availability or mocked OS name is not platform verification.

Use a per-user workspace `TMPDIR` on hosts with constrained `/tmp` quotas. The verifier creates its own pytest temporary directory. Text inputs use UTF-8 explicitly and generated schema bytes use LF line endings on every platform.
