# Where the review record of Consiliency/jevdrill#1 is

Consiliency/jevdrill#1, "Implement ROUTE discovery and offline HOST, LEARN, EXPERIMENT runtimes", was closed on 2026-11-22 without merging. A stack of smaller pull requests replaced it, each reviewed afresh under [the split plan](../plans/pr1-stack-split-20261119.md). This page says where the record of #1 is, what it does not establish, and which parts of it are not public. It adds no acceptance claim.

## What is public

| What | Where |
| --- | --- |
| The pull request | <https://github.com/Consiliency/jevdrill/pull/1>: 76 commits, 484 files. It has one comment, the closing note. Its review rounds were never posted to GitHub. |
| Its final commit | Tag `pr1-final-record`, commit `94475ba294d79a3eb2944e838bab408c91019683`. The branch `codex/implementation-reviewed` is kept at the same commit. |
| Whole-PR review rounds 1 to 21 | `evidence/MERGE/round-1` to `round-21` at the tag: the seats' reviews, the author's responses and, in some rounds, a president's ruling. There is no index. `evidence/MERGE/round-5/president.md` is the BLOCK_MERGE ruling on credentials that the split plan cites. |
| The review of the judgment-version fix | `evidence/EXPERIMENT/fix-review-20261011/round-1` to `round-3` at the tag. |
| The October 2026 phase reports | `evidence/CONTRACT`, `evidence/ROUTE`, `evidence/HOST`, `evidence/LEARN` and `evidence/EXPERIMENT` at the tag: closeouts, verdicts, Python 3.13 receipts under `history/python-3.13/`, and the proposal, approval and stopped-run records of the one development study. |
| The stack that replaced it | Consiliency/jevdrill#12, #18, #27, #44, #54, #66, #76 and #85. Each description summarises its review and the rulings on it. |

To read a file of the record: `git fetch origin tag pr1-final-record`, then for example `git show pr1-final-record:evidence/MERGE/round-5/president.md`. Or browse <https://github.com/Consiliency/jevdrill/tree/pr1-final-record/evidence>.

## What the record at the tag does not establish

- **Nothing for `main`.** The plan says evidence is not merged as new acceptance. What is verified on `main` is in [roadmap status](roadmap-status.md).
- **The HOST and LEARN verdicts there say `passed`.** They were reduced from receipts made on 2026-10-09, on Python 3.13, on machines that are not CI runners, with host-integration code for agent-harness that was not published. No HOST or LEARN receipt on Python 3.14 exists.
- **The EXPERIMENT verdict there says `blocked`,** by design: the quality tolerances (Q-12, Q-13) and an authorized study are missing. The one study authority expired on 2026-10-15.
- **Round 5's block was not lifted inside #1.** On `main` it is resolved by [the credential check](sanitization-contract.md) and its tests, reviewed in Consiliency/jevdrill#27 and Consiliency/jevdrill#54.
- The records at the tag contain names and local paths of the machines they were made on.

## What is not public

- **Rounds 22 to 43.** The tree at the tag stops at round 21.
- **Rounds 38 to 43** (repairs, bounded proofs and reviews) are kept in the project's private archive and are not published. The last, R43, was a bounded proof of the test suite on Python 3.14 on one Linux machine. It made no HOST or LEARN receipt.
- **Rounds 22 to 37** were not located. The split plan records that the original review history was lost and could not be recovered ("R32").
- **The stack's own review records** (charters, seat reviews and rulings) are in the same private archive. Backlog issues that cite `stack-reviews/…` refer to it.
