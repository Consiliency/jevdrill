# Toolchain

Initial implementation targets CPython 3.13, the minor used by the isolated BAML proof. Other Python minors remain unsupported until their complete compatibility matrix is recorded; the earlier 3.12–3.14 range was a proposal.

Use `uv sync --locked` and `npm ci`. Runtime dependencies and developer tools are locked in `uv.lock`; Node is a development-only cross-language schema consumer. The installed CLI exposes the implemented routing and discovery commands.

BAML compiler and bridge must both be 0.20.1. Set `BAML_CLI` to the verified compiler executable; generation checks reject a different version. Generated package imports currently initialize the bridge. This dependency is explicit, not a runtime-free contract claim. Generated files and schema exports are checked in; never edit them manually.

Native matrix results now pass on Linux x86_64/Python 3.13.15, macOS arm64/Python 3.13.7 and Windows AMD64/Python 3.13.15. See `evidence/CONTRACT/platforms`. This establishes the contract foundation's tested matrix, not support for unimplemented storage, scheduling or host features. A workflow file, wheel availability or mocked OS name is not platform verification.

Use a per-user workspace `TMPDIR` on hosts with constrained `/tmp` quotas. The verifier creates its own pytest temporary directory. Text inputs use UTF-8 explicitly and generated schema bytes use LF line endings on every platform.
