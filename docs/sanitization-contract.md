# JEV Drill: what the credential check does and does not do

Status: Drafted by the review board; owner ratification pending

JEV Drill checks every piece of text in a request before it sends anything to the judgment provider or writes anything to local storage.†

**What is refused.** A request is refused when any piece of its text contains:
- one of the names `authorization`, `api key`, `access token`, `password` or `secret`, followed later in the same paragraph by `:`, `=`, `<-` or `->`. Letter case does not matter, the two-word names may be joined by a space, `_`, `-` or nothing, and the name may sit inside a longer one such as `DB_PASSWORD` or `X-API-Key`;
- `Bearer` or `Basic` followed by a token, at the start of a line or directly after a quotation mark;
- the first line of a PEM private key.

The check also sees these through `\x` and `\u` escapes, `%XX` codes, HTML numeric codes, invisible characters and full-width letters.

**What you see.** The whole request is refused before anything is sent.† The command line returns `invalid_input` and does not say which text caused it. JEV Drill never edits text: it passes unchanged or the request is refused.

**What is not detected.** These pass the check. They reach the judgment provider and, when raw-task retention is on, local storage, exports and archives.
- Other names: `token`, `GITHUB_TOKEN`, `passwd`, `credential`, `private_key`, `auth`, cookies.
- Secrets with no name: bare API tokens, key ids, connection strings such as `postgres://user:pass@host`.
- A listed name with none of the four signs after it: "the password is X", `--password X`, a `.netrc` line, a pair such as `["X-API-Key", "X"]`, a value written before its name, or a blank line between name and sign.
- A name built from pieces (`'pass' + 'word'`) or hidden by another encoding, such as base64.

**Also know.**
- Ordinary text can be refused: a sentence that mentions `password` and later has a colon or a web address, or a line that begins "Basic …". In two small samples the check refused 5 of 30 developer texts and none of 36 evaluation tasks. The rate on real tasks is not measured.
- Anyone who can put text into a request can cause a refusal.
- JEV Drill stores a SHA-256 fingerprint of each accepted request as received.†
- Text JEV Drill reads from its own local stores (admitted guidance, development cases) is not checked again.‡
- This check is a safety net. The main controls are path exclusions for credential files, raw-task retention (off unless you turn it on), and `local_only` and the allowed-provider list, which keep text away from the judgment provider altogether.

† How the application uses the check; confirmed in the S5 review. ‡ Confirmed in the S4 review. A sentence found wrong comes back to the owner.
