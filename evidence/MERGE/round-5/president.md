# President's ruling: Consiliency/jevdrill#1 — BLOCK_MERGE

I'm the separate board president (owner-authorized manual Opus 5.5 CLI), not a fifth seat.

**Binding**
- HEAD `23192913282a8e3bcc10a9a262df346791789945`; delta base `6fe946126d59131a01c85d6d5ce145641f9af51b`; PR base `f67ad654ff224d6b343ab366260d9184150d822f`.
- Manifest `250b0e2f30239bab4787a93c7bff65e64d02b7163a380b1c9ce1ae2e90b2ce51`, 772 files.

**Verdict: do not merge. There are three independent grounds:**
1. A credential-disclosure blocker under M2 is still open. All four round-5 seats reproduced it by actually running the leak.
2. The full current suite did not pass: 1157 tests, **7 errors**.
3. All four round-5 seats voted DISAGREE, so the precondition that every seat agree is not met.

## 1. Blocker: credentials still reach judges and retained artifacts (M2)

**What it violates:**
- `docs/route-readiness.md:56-57`: credentials are sanitized before submission or persistence.
- `plans/phase-plan-v1-ROUTE.md:220-222`.
- `docs/jevdrill-spec.md:394`: do not collect secrets.

**How a leak travels:**
- `redact` (`src/jevdrill/context.py:62-82`) is the only sanitizer, for both routing (`application.py:578, 664`) and discovery (`application.py:104, 119-123`).
- Anything it misses goes to the judge (`application.py:812-830`; discovery `302-308`).
- It is also written to raw artifacts when raw retention is on (`application.py:951-960`; discovery `218-236`).

**(a) Leaks the seats reproduced by running them** (actual DevelopmentJudge over loopback). I traced each one in the source and agree:

| Seat | Leak | Receipt |
|---|---|---|
| Correctness | `Authorization: "p" \r\n\tS` and `api_key: p \r\n\tS`; also duplicate JSON members such as `{"name":"X-API-Key","value":"S","value":"[redacted]"}` | `/tmp/jevdrill-r5-correctness-review/receipt.json` `52fd6e52819549d0bf3e1081636b4bf3b775ca2ef2923291ad1b0f68ded79a8b` |
| Alternative | Trailing whitespace before a folded continuation | `/tmp/jevdrill-r5-alternative-boundary-Rtlpbo/receipt.json` `5ef3578462e66246affeb665b2cc4e832ba3d1567714dbc1222d7069ddc0bc9f` |
| Astra | Trailing whitespace; `password: correct horse S`; an Authorization record wrapped inside a JSON string | `/tmp/jevdrill-r5-redteam-qXzC7q/receipt.json` |
| Grok | `{"name":"Authorization","Name":"Content-Type","value":"Negotiate S"}`; a header name with a trailing space, `"Authorization "` | `/tmp/jevdrill-r5-grok-loopback-receipt.json` `407c1e29273582bcd16c4124cad993c797d3b86bed9dbca24ac7200d2631eacd` |

Why each one gets through:
- **Trailing whitespace:** a continuation line (`:27`) is only picked up if a line break comes immediately after the quoted value (`:30`) or the unquoted value pattern `[^\s,;}]+` (`:34`). A space in between ends the match.
- **Multi-word passwords:** that same unquoted pattern stops at the first space.
- **Duplicate members:** Python's JSON decoder keeps only the last copy of a repeated key. If the cleaned result then equals the decoded one, `:75-79` puts the original bytes back, including the discarded secret. Note that the CLI's own envelope parser already rejects duplicate keys (`cli.py:36-42`).
- **`name`/`Name` collision:** the lookup map at `:42` keeps whichever key last normalizes to `name`.
- **Trailing space in the header name:** the name is never trimmed before it is checked against the set.
- **JSON inside a JSON string:** decoding only starts at `{` or `[` (`:66`), so an escaped record inside a string is never decoded.

**(b) Further leaks I found by reading the code.** These are static traces only: this session denied Python, so I did not execute them.
- `{"key":"X-API-Key","value":"S"}` and `{"key":"Authorization","value":"Negotiate S"}` (Postman v2 header format). The code only links a label to a value when the label sits under a member literally named `name` (`:42-47`).
- `[["X-API-Key","S"]]`: header pairs written as arrays are never linked at all.
- `{"name":"client_secret","value":"S"}` and `{"name":"X-Goog-Api-Key","value":"S"}`. The 7-entry name set (`:16-26`) is narrower than the free-text matcher (`:33`), which already redacts `client_secret: S`, `{"client_secret":"S"}` and `X-Goog-Api-Key: S`.
- YAML `- name: X-API-Key\n  value: S`, the Python literal `{'name':'X-API-Key','value':'S'}`, and `headers["X-API-Key"] = "S"`.

Probe for the root to run (I have not run it):
```python
from jevdrill.context import redact
for t in ['{"key":"X-API-Key","value":"SYNTHETIC"}', '[["X-API-Key","SYNTHETIC"]]',
          '{"name":"client_secret","value":"SYNTHETIC"}', '- name: X-API-Key\n  value: SYNTHETIC',
          'headers["X-API-Key"] = "SYNTHETIC"']:
    print("SYNTHETIC" in redact(t), repr(t))  # expected: True on every line
```

**Root cause.** Every leak above, run or traced, comes from two design facts:
- Linking a label to its value depends on exact names: the label must be under `name`, it must be in a fixed 7-entry set, and only a member called `value` is masked.
- The code restores the original bytes whenever the decoded form looks unchanged, even when decoding lost or skipped content.

This class has reopened in every round since round 1, so adding more patterns will not close it.

**Minimal repair, stated as a testable requirement:**
1. Use one credential-label test everywhere, with the free-text matcher's substring behaviour, after trimming and normalizing case and separators.
2. Decode without losing anything: keep member pairs, never restore original bytes when duplicates exist, and also decode JSON that is stored inside strings.
3. Inside any decoded object or array, if any key or string element is a credential label, redact every sibling value, whatever the member names or order.
4. A labeled free-text value runs through trailing spaces, multi-word unquoted text and folded continuation lines. An unindented ordinary next line is kept.
5. Other structured formats (YAML, Python literals, code assignments) are either handled or the request fails closed before submission and retention.
6. Back it with one generated test: labels × formats × the six input boundaries, asserting the secret appears on neither the judge wire nor retained bytes. Keep the existing ordinary-text tests that must pass through unchanged.

**What this means for the owner under the cap rule.** The feature that carries this leak is sending supplied free text to judges, plus optional raw retention. Removing it would gut ROUTE, so the change stops here for the owner. There are two ways forward:
- Fund the structural repair above, followed by a fresh board review.
- Ratify an explicit, enumerated sanitization contract that discloses the remaining exposure. That changes the criterion, and only the owner can do it.

Narrowing the documentation while the leaking path stays in place would amount to waiving the defect.

## 2. Unmet merge condition: the full suite did not pass (M3)

**Result:** `/tmp/jevdrill-merge-r5-full.xml` (SHA-256 `de9b6bfa…`, as reported by Grok): 1157 tests, 0 failures, **7 errors**, 0 skips, 524.28 s.
- The test count reconciles exactly: 952 at round 4 plus 205 added by this delta's test expansion (route 14→68, context 8→35, discovery 12→136). Nothing was dropped.

**What failed:** all 7 are setup errors from one HOST companion fixture.
- Its child tests `test_paired_baseline[fixed_default-2..5]` hit "JEV Drill CLI exceeded deadline". When the route command was launched, only 0.12–0.76 s of the companion's 5 s budget remained.
- The companion spent the rest of the budget before launching the route command, including its own `notices` CLI call.
- The other 28 child tests in that run passed.
- Grok measured `redact` at 0.84 ms on the route fixture.

**My reading:** this looks like load from the seats running tests at the same time. I don't attribute it to the delta, but I can't rule that out either. Astra's round-5 report also calls it "not a clean full-suite pass."

**Required:** a clean full-suite rerun on the exact head.

**Other checks:**
- Targeted run: 318 passed.
- CI on the exact head: 9/9 succeeded according to `round-5/ci-binding.json`, which matches the run IDs Astra and Grok cite. I did not query GitHub myself.

## 3. Secondary issues (not blocking; same function; new in this delta)

**Deeply nested input crashes the CLI.** Sufficiently deep nesting of `[` or `{` (well inside the 1,000,000-byte input limit) raises `RecursionError` in the JSON decoder.
- `:71` only catches `JSONDecodeError`, and `cli.py:211-227` has no handler for `RuntimeError`.
- The CLI therefore exits with code 1 and a traceback, which is outside the documented exit codes 0/2/3/4 (`docs/route-readiness.md:32-34`).
- It fails before anything is written to storage (route `:578`, discovery `:104`), so nothing is disclosed or corrupted.

**Quadratic copying.** `text[start.start():]` copies the rest of the text for every bracket, so a pathological input costs O(n × brackets).

**Fix:** call `decoder.raw_decode(text, start.start())` with an absolute index instead of slicing, and treat `RecursionError` as "not JSON" or fail closed with `ContractError`.

## 4. Round-4 dissents (all DISAGREE on 6fe9461)

| Seat | Round-4 finding | Ruling now |
|---|---|---|
| Astra | Authorization name/value records (escaped Bearer/Basic folds, Negotiate, Digest) | Reported forms are fixed. The name/value linking class is still open (§1). |
| Grok | Quoted value then fold, bare CR, NBSP/VT indent, split api_key/password/secret/access_token | Reported forms are fixed. A blank line ending a header matches HTTP folding rules; I agree it is not a blocker. Trailing-whitespace variants are still open. |
| Correctness | X-API-Key and Digest name/value records | Fixed for records labeled with `name`. Linking is still incomplete. |
| Alternative | token/Digest/X-API-Key name/value records; whitespace-only continuation lines | Reported forms are fixed. |

## 5. Earlier criteria and the other merge criteria (M1, M4, M5)

This delta touches only `context.py`, tests and evidence. The following earlier repairs are unchanged:
- removal of spending ceilings for injected judges, and the model/counter checks before calls
- provider and privacy authority checks
- blocking new admissions after a portable recovery
- worker-byte deletion and cleanup of imported tombstones
- the discovery retention lifecycle
- downstream test selection and duration summation
- SDK publication and LF checkout

All four round-4 seats closed these at 6fe9461, and all four round-5 seats re-closed them at this head by running tests. I re-read the relevant gates in the current source (`application.py:160-164, 283-296, 770-780, 802-811`).

Grok's observation that `hard_constraints.spending_ceiling` caps execution, not judge overhead, is not a blocker; I concur.

The portable-v1 omissions (experiment ledger, raw discovery artifacts) remain documented fail-closed limits. I did not use the unratified study questions (F6/F7/D2/D4/D6) to widen scope.

For M4, the delta adds only synthetic sentinels and evidence markdown. The Alternative seat's scans flagged nothing; I did not rerun them.

## 6. What I checked, and the limits

**Permissions.** This session allowed only read-only commands inside the candidate root. Denied:
- `sha256sum -c` against the manifest in /tmp
- computing the manifest file's own digest
- any Python or pytest (one attempt, not retried)

So I executed no tests or probes, and my own findings in §1(b) and §3 are static traces.

**Binding, checked before and after:**
- HEAD unchanged at `2319291…`.
- `git status --porcelain --untracked-files=all` empty.
- 772 tracked files.
- 12 files re-hashed — the 10 delta files plus `application.py` and `cli.py` — match their manifest entries exactly.
- All four round-5 seats report that `sha256sum -c` passed before and after against `250b0e2f…`.

**Reading.**
- Read in full: all round-4 and round-5 seat reports, the round-4 and round-5 responses, the cap-reduction disposition, the ROUTE readiness doc and the relevant spec/plan sections.
- Searched rather than read in full: the round 1–3 and cap-reduction reports and responses, for the history of the credential class.
- Not read in full: `docs/experiment-interfaces.md`.

**Actions not taken:** no source, index or evidence edits; no GitHub comments; no live providers, secrets, raw streams, studies, grants or holdouts.

**Requirements for any future approval:**
- a repair that meets the requirement in §1
- all four fresh seats AGREE
- a clean full suite
- all nine checks pass on the exact head
- the head and manifest are unchanged at merge

BLOCK_MERGE
