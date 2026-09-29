# CONTRACT readiness

The foundation passes native Linux, macOS and Windows verification: 119 product tests per platform, plus 55 Linux research regressions. All three manifests identify the same source digest. The phase remains open because the required closeout audit rejects 15 ignored paths, including pre-existing review logs and BAML/build outputs.

Run `BAML_CLI=/path/to/baml-cli uv run python scripts/verify_contract_phase.py`. The runner executes boundary, generator, vocabulary, import, evaluation, type, lint, format and package checks, and Linux research regressions. It records input digests and native platform metadata, then requires matching Linux/macOS/Windows results for Python 3.13. `--local-only` permits a local job to succeed while the aggregate still reports missing platforms. `--reduce-only` checks collected manifests without rerunning jobs.

Evidence paths are `evidence/CONTRACT/platforms/*.json` and `evidence/CONTRACT/verification.json`. A workflow definition is not a run. Manifests require trusted collection; metadata validation cannot cryptographically establish that a person has not fabricated evidence. Historical research tests depend on Unix `fcntl` and run only on Linux; public product checks run on all three platforms.

Next: preserve the research workspace and establish an initial curated commit for a clean execution worktree, then rerun closeout before ROUTE planning. No commit or push has been made. Complete telemetry/adapter integration remains later work. The 228 source mappings prove inventory integrity, not implementation completeness. Numeric quality floors and regression tolerances remain pending calibration and authority before holdout exposure or policy promotion.
