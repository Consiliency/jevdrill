# Detailed plan: prepare the next calibration decision

## Task

Prepare a concrete study proposal and verify read-only model/access metadata.
No inference call or renewed spending grant is authorized by this planning step.

## Research summary

The previous study's retained reservations leave insufficient allowance for a
complete pair. Its rates expired October 1. The official deprecation schedule
also retires GPT-4.1 nano on October 23. A fresh model pair needs a new immutable
profile, conformance proof and separately recorded grant; historical results and
allowances remain unchanged.

## Changes

- `evidence/EXPERIMENT/next-calibration-proposal.md`: study scope, candidate
  proposal, measured metrics, grouping/exposure rules, sample limitations and
  explicit new allowance request. No numeric quality tolerance is fabricated.
- `evidence/EXPERIMENT/next-calibration-corpus.json` and
  `next-calibration-controls.json`: 60 purpose-built development cases with
  reference and defective answers, grouping and exposure metadata. Verify trusted
  reference/negative controls in the already inspected restricted Node image and
  existing independent review/documentation evaluators; no model call occurs.
- `evidence/ROADMAP/access-metadata.json`: redacted metadata-only access outcomes
  and official documentation references. Record model visibility, not credentials.
- `.phase-loop/runs/ROADMAP-20261003/model_metadata.py`: one read-only models-list
  probe. Read the already authorized `OpenAI` item's `OPENAI_API_KEY` field in
  `Consiliency Deploy Secrets` with the personal `my` account into process memory.
  Use only GET `/v1/models`; print only selected public model identifiers/status.
  Do not persist the credential, response payload, headers or provider error body.
- `.phase-loop/runs/ROADMAP-20261003/prepare_calibration.py`: create and validate
  the owned development corpus. All answers are handwritten controlled fixtures.
- `plans/manifest.json`, `.dev-skills/handoffs/**`: proposal lifecycle and pointers.

Read allowance: public calibration sources and docs; official model/pricing/
deprecation pages; the exact 1Password account/vault/item/field above for this
read-only probe; named metadata outputs. Existing grants stay hash-only and old
raw provider transcripts/databases are excluded.

## Documentation impact

The proposal states that development calibration is not release or promotion
acceptance and that further policy evaluation uses separately sealed data.

## Dependencies and order

1. Verify current official model metadata and local account/field availability.
2. Prepare the concrete proposal and record unresolved gates.
3. Ask the owner for any new live allowance through the structured ask-user tool.
   Continue independent offline verification while awaiting a reply.

## Verification

- Read-only GET models-list probe with filtered output and no generation.
- Verify reservation arithmetic with Decimal and current full-context rates.
- Confirm proposal retains the no-additional-critical-failures rule and separates
  study enablement from policy promotion and publication.

## Acceptance criteria

- [ ] No generation occurs and credentials never enter logs or artifacts.
- [ ] The owner receives a bounded, reviewable next-study proposal.
- [ ] Historical study authority and results remain unchanged.
