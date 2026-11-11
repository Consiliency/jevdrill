# Round-11 Astra provider failure and root-correlated evidence

This is a root evidence assessment, not a completed Astra review or a vote.
The Astra task terminated FAILED with a provider cybersecurity-risk flag while
returning its result. Its exact error is preserved in `astra-provider-failure.json`.
No final review verdict exists, and no approval is inferred from its partial work.

Binding: HEAD `346e800909dcd59317c41b7cfdf25040ca07919c`; 806 tracked files;
manifest SHA256 `878af684f2df5458c46b87ee986f73219464d78bfb3e0fe13a9cf04772937f34`.
Root independently checked clean status, HEAD and all manifest hashes after reading
the saved evidence. Source/index/tracked evidence remain unchanged.

The saved fake-inline DevelopmentJudge probe used local HTTP and fresh separate
synthetic allowances/databases at all six supplied-context boundaries. Its receipt
is `/mnt/workspace/users/viperjuice/tmp/jevdrill-merge-round11-20261016/reviews/astra/seat-khc5y861/receipt.json`,
SHA256 `612ca947cf41424cc37726abf3f080150b5489d682c61e311fb17001748f5809`.
Input SHA256 is `21e1f89831e6ec2ea2cd6bce3745e9775f3b2ec766eced222283080efdee0139`.
Root read the probe, parsed the receipt and verified its digest. Its 48 inputs
produced 288 boundary executions and 225 HTTP requests. Twenty-eight inputs each
disclosed through all six boundaries: 168 HTTP disclosures, 140 raw-artifact
disclosures and zero reported database sentinel findings. Route attachments were
transmitted but excluded from raw-task artifacts. These counts are distinct from
the prior passing matrix, whose tested inputs lacked these cases.

## Root-confirmed blocker: comment content bypasses computed-record inspection

M2 / EC-ROUTE-4 requires sanitization before submission and persistence.
`docs/route-readiness.md:88` also promises handling/rejection of computed records and
discarding parser-omitted comments. Python tokenization packages a comment's entire
payload into a COMMENT token. The fragment collector at `context.py:370` only examines
OP tokens, and AST parsing at `context.py:393` ignores the comment payload. Mixed prose and
code fences can prevent YAML's comment-discarding path from handling the document.
Computed labels consequently survive the later quoted-fragment fallback.

An exact synthetic form that retains its sentinel is:

```text
Ordinary context.
# {'name': 'Author'+'ization', 'value': 'SYNTHETIC_SENTINEL'}
End notes.
```

Encoded structural members containing such comments can also lose their label
association while leaving a sibling value intact. Root independently reproduced
four saved forms at the direct redactor: prose-comment mapping, fenced formatted
assignment, YAML comment association and JSON comment association. Results are in
`astra-root-corroboration.json`. This confirms a current defect independently of the
missing review verdict. No real credentials or external provider calls were used.

Minimum repair: inspect or reject computed credential content in comments before
mixed-text fallback or scalar rewriting, preserving original sibling associations
until sensitivity is decided. Discarding comment text must not erase a label and
leave an associated value eligible for dispatch/retention. Add the exact cases to
the existing six-boundary matrix with ordinary-comment preservation controls.

The saved verification receipt reports 2,576 focused tests and 144 verifier tests
passing, current full/native evidence validation and unchanged source. Those are
partial reviewer artifacts, not a substitute for a complete final review.

The other three reviews remain pending. Root will not edit source before they
finish, replace the failed seat with a favorable vote, rephrase requests to evade
the provider flag, or waive the blocker. After the combined repair, a new frozen
candidate still requires four fresh usable AGREE reviews and separate presidential
approval. The prior presidential BLOCK_MERGE remains binding.
