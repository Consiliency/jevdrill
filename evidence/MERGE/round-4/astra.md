**Do not merge Consiliency/jevdrill#1 at `6fe946126d59131a01c85d6d5ce145641f9af51b`.** One P1 credential-disclosure blocker remains under M2.

**Authorization name/value records still bypass sanitization.** The [redactor](/home/viperjuice/workspace/worktrees/jevdrill-implementation-reviewed/src/jevdrill/context.py:16) recognizes direct Authorization assignments and standalone Bearer/Basic text, but does not associate an Authorization header name with its separate value. These synthetic representations survive:

```json
{"name":"Authorization","value":"Bearer\r\n\tSYNTHETIC_TOKEN"}
{"name":"Authorization","value":"Basic\n  SYNTHETIC_TOKEN"}
{"name":"Authorization","value":"Negotiate SYNTHETIC_TOKEN"}
```

A valid JSON name/value record containing Digest authentication likewise preserves its synthetic `response` value.

The escaped newline characters above are ordinary JSON encoding. The standalone scheme matcher expects literal whitespace, while Digest and Negotiate do not match that alternative at all.

**Trigger and consequence:** supply these records in task text, authorized attachments, discovery objectives/context, or descriptions. Application passes the surviving credentials to judgment and persists them when raw retention is enabled. Relevant boundaries are [discovery sanitization](/home/viperjuice/workspace/worktrees/jevdrill-implementation-reviewed/src/jevdrill/application.py:104), [task dispatch](/home/viperjuice/workspace/worktrees/jevdrill-implementation-reviewed/src/jevdrill/application.py:830), and [task retention](/home/viperjuice/workspace/worktrees/jevdrill-implementation-reviewed/src/jevdrill/application.py:952). This violates the existing [sanitization requirement](/home/viperjuice/workspace/worktrees/jevdrill-implementation-reviewed/plans/phase-plan-v1-ROUTE.md:220) and [prohibition on collecting secrets](/home/viperjuice/workspace/worktrees/jevdrill-implementation-reviewed/docs/jevdrill-spec.md:394).

Independent reproduction:

- **42 built-in-adapter cases**, intercepting only the final provider functions: 18 control cases stayed clean; all 24 bypass cases submitted the sentinel. Twenty also retained it in raw artifacts. Route attachments were submitted but were not included in raw-task artifacts.
- **Six actual DevelopmentJudge loopback cases:** escaped-folded Bearer and JSON Digest each reached HTTP bodies and raw artifacts through both routing and discovery. Routing returned `ready`; discovery exhausted its synthetic allowance after three calls—the failure did not prevent disclosure.
- Direct folded Bearer/Digest headers and ordinary JSON name/value Bearer controls were correctly redacted.

Reproducible scripts and receipts: [built-in probe](/tmp/jevdrill-r4-redteam-credentials-bxMALJ/probe.py), [42-case receipt](/tmp/jevdrill-r4-redteam-credentials-bxMALJ/receipt.json), [loopback probe](/tmp/jevdrill-r4-redteam-credentials-bxMALJ/probe_loopback.py), [loopback receipt](/tmp/jevdrill-r4-redteam-credentials-bxMALJ/loopback-receipt.json).

**Minimal repair:** recognize Authorization name/value records, including JSON string escaping, and redact their entire associated value independent of authentication scheme. Add composed representation controls through submission and retention.

Prior objections are adjudicated as follows:

- **Cancelled president’s direct folded-header finding:** repaired for the reported LF/CRLF forms, including multiple Digest continuations and preservation of unindented ordinary context. Cancellation remains no approval; the broader credential boundary remains incomplete.
- **Injected spending ceilings:** closed through explicit scope reduction. Both paths reject every explicit request ceiling before adapter preparation/dispatch, including funded ceilings. Request-bound injected pricing remains deferred. Built-in zero/funded controls pass.
- **Model/counter binding:** closed. Unsupported and mismatched profiles deny before calls; supported pinned controls succeed.
- **Provider/privacy authority, recovery admission blocking, discovery retention, worker-byte deletion, and imported tombstones:** controls pass. Portable-v1 restrictions remain explicit.
- **Downstream control selection and duration arithmetic:** regression controls pass.
- **SDK publication and LF checkout:** repairs remain present. All 147 SDK files are tracked; clean tracked-archive application/patch imports pass.

Verification and limits:

- **188 tests passed**, zero failures/errors/skips: [179 boundary tests](/tmp/jevdrill-r4-redteam-boundaries.xml) and [nine prior-repair controls](/tmp/jevdrill-r4-redteam-prior-repairs.xml).
- Inspected the parent’s [full-suite XML](/tmp/jevdrill-merge-r4-full.xml): **952 passed**, zero failures/errors/skips. I did not rerun that suite.
- Verified all nine jobs succeeded on this exact head: [CONTRACT](https://github.com/Consiliency/jevdrill/actions/runs/38334212419), [ROUTE](https://github.com/Consiliency/jevdrill/actions/runs/38334212400), and [EXPERIMENT](https://github.com/Consiliency/jevdrill/actions/runs/38334212408). I did not independently rerun native hosts or reduce downloaded receipts.
- Before/after manifest checks passed for **767 tracked files**. HEAD and clean source/index status remained unchanged. Manifest SHA-256: `54a4b6f9ea22245f0d3028748d7e1fa53554f7063ce84c6af7897e4d86342586`.

No nested delegation, source/index/tracked-evidence edits, credential-file reads, real providers/studies/grants, GitHub comments, deployment, or adoption. Historical dissents remain historical; this is an independent seat report, not the separate president’s ruling.

DISAGREE
