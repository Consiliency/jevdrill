**Do not merge Consiliency/jevdrill#1 at `ff858a3eb0da2b710fb38897c6040072224ea0f9`.** This full-diff integration/packaging review found four blockers.

1. **P1 — Required generated modules are missing from Git (M1, M3).**
   [SDK initialization:55](/mnt/workspace/worktrees/viperjuice/jevdrill-implementation-reviewed/src/baml_sdk/__init__.py:55) unconditionally imports `typesafe_patch`, but its four generated files—the `.py` and `.pyi` initializers for `typesafe_patch` and `typesafe_patch/internal`—are ignored and untracked. GitHub’s [EXPERIMENT run](https://github.com/Consiliency/jevdrill/actions/runs/38314432015) fails with `ModuleNotFoundError: No module named 'baml_sdk.typesafe_patch'`; CONTRACT fails similarly. Local builds conceal the omission because Hatch includes ignored files.
   **Minimal repair:** track those four pinned generated outputs and verify imports, generation, and package installation from a clean checkout.

2. **P1 — ROUTE ignores the provider restriction before judgment dispatch (M2).**
   [Application dispatch authorization:742](/mnt/workspace/worktrees/viperjuice/jevdrill-implementation-reviewed/src/jevdrill/application.py:742) checks cloud permission and `local_only`, but not `hard_constraints.allowed_providers`. With `allowed_providers=["local"]`, a local candidate needing judgment still reaches the production TypeSafe BAML function. With configured credentials, this can transmit task/context data to a prohibited provider. Discovery already enforces the restriction at [application.py:159](/mnt/workspace/worktrees/viperjuice/jevdrill-implementation-reviewed/src/jevdrill/application.py:159).
   **Reproduction:** intercepting the production BAML function yielded one dispatch and `ready` for the prohibited-provider case; the local-only control yielded zero dispatches. No live call occurred.
   **Minimal repair:** enforce the judgment provider restriction before dispatch and add allowed/denied controls. This is inherited D5, but it concretely violates M2 and cannot remain merely a study-design question.

3. **P2 — ROUTE CI lacks its required companion environment (M3).**
   [route.yml:31](/mnt/workspace/worktrees/viperjuice/jevdrill-implementation-reviewed/.github/workflows/route.yml:31) invokes a collector whose [pytest command:128](/mnt/workspace/worktrees/viperjuice/jevdrill-implementation-reviewed/scripts/verify_route_phase.py:128) runs the expanded default suite. That suite requires an installed companion, but this workflow neither installs nor configures one. Removing the companion environment reproduced `Explicit HOST companion checkout is required` in `tests/conformance/test_notices.py`. This remains after repairing the SDK omission.
   **Minimal repair:** supply the content-bound companion and required environment before collection, preserving the required assertions.

4. **P2 — Windows checkouts invalidate native source receipts (M3).**
   [ROUTE checkout:19](/mnt/workspace/worktrees/viperjuice/jevdrill-implementation-reviewed/.github/workflows/route.yml:19), [HOST checkout:25](/mnt/workspace/worktrees/viperjuice/jevdrill-implementation-reviewed/.github/workflows/host.yml:25), and [LEARN checkout:25](/mnt/workspace/worktrees/viperjuice/jevdrill-implementation-reviewed/.github/workflows/learn.yml:25) omit CONTRACT’s `core.autocrlf=false` setup. No tracked attributes enforce LF. For the same 401 tracked ROUTE inputs, my LF and CRLF calculations exactly reproduced the [Linux and Windows CI receipt](https://github.com/Consiliency/jevdrill/actions/runs/38314431424) digests, respectively. They therefore cannot satisfy matching-source reduction.
   **Minimal repair:** establish LF checkout behavior before all relevant checkouts, then recollect the native matrix.

Nonblocking documentation cleanup: [toolchain.md:5](/mnt/workspace/worktrees/viperjuice/jevdrill-implementation-reviewed/docs/toolchain.md:5) still says routing does not exist; ROUTE/HOST readiness still instruct replanning already implemented downstream phases. EXPERIMENT correctly remains blocked on empirical acceptance.

I found no additional demonstrated merge blocker from F6/F7/D2/D4/D6. Those study-validation/design concerns remain unratified; this assessment grants no collection, calibration, promotion, or runtime-adoption authority.

Validation actually performed:

- **127 tests passed:** package installation/build, CLI, and ROUTE/HOST/LEARN/EXPERIMENT verifier tests.
- Generation comparison passed: **147 outputs, 78 schemas**, `write=false`.
- Read-only reduction of supplied native CONTRACT receipts returned no errors: **322 tests, zero skips per platform**, matching local digest `1aa527…081bc`. Those local inputs include the four untracked files.
- Companion-environment failure and provider-restriction violation reproduced independently.
- Before/after manifest checks passed; manifest SHA-256 remained `af6899774b59bf66168f79f7771f593d638cd2c1cc32e74ada8349c065df82fa`. HEAD and tracked worktree remained unchanged.
- No source/evidence/index edits, GitHub comments, credential access, live provider calls, or study execution. I did not assume the parent’s pending 858-test run succeeded or independently rerun native platforms.

DISAGREE
