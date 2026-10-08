# Initial pointer review: unusable

Command: `phase-loop advisor-board plans/route-drill-review-brief.md --landing-tier plan --pointer-brief --json`.

The runtime reported `seat_pointer_brief_unreadable` for Claude and Gemini.
All four seats then returned DEGRADED with `HARDEN review staged tree does not
match authorization`; zero grounded reviews were delivered. The president
required repairing review delivery and rerunning the board. These results do
not count as plan approval or a substantive review round.

Repair: use the same runtime board primitive and subscription routes with a
focused, immutable inline plan/source bundle and `stage_review_tree=False`.
No live tree is exposed. Reviewer isolation, subscription authentication and
the president requirement remain enabled. The 55,346-byte initial focused
bundle and its source digests are retained under `round1/`.
