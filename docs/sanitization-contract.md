# JEV Drill: what the credential check does and does not do

Status: Ratified by the owner on 2026-11-21

JEV Drill checks the text of a request before it sends that text to the judgment provider or writes it to local storage.†

**Which text is checked.** Discovery, report, experiment and policy-lifecycle requests are checked whole. A routing request is checked in its task request, its inventory and its catalog. An analysis request is checked in its objectives and its recorded context. The other parts of those two requests (settings, the catalog query, the judgment policy, the link to a discovery, and the analysis scope) are not checked. None of that is sent to the judgment provider, and it is stored only as fingerprints or as validated identifiers. Maintenance, recovery, notice and policy-evaluation requests are not checked.†

**What is refused.** A request is refused when any piece of its text contains:
- one of the names `authorization`, `api key`, `access token`, `password` or `secret`, followed later in the same paragraph by `:`, `=`, `<-` or `->`. Letter case does not matter, the two-word names may be joined by a space, `_`, `-` or nothing, and the name may sit inside a longer one such as `DB_PASSWORD` or `X-API-Key`;
- `Bearer` or `Basic` followed by a token, at the start of a line or directly after a straight quotation mark (`"` or `'`);
- the first line of a PEM private key.

The check also sees these through `\x` and `\u` escapes, `%XX` codes, HTML numeric codes such as `&#61;`, invisible formatting characters such as zero-width spaces, combining marks, and full-width letters.

**What you see.** When the check refuses text, nothing is sent to the judgment provider and the refused text is not stored.† Usually the whole request is refused before anything is stored: the command line returns `invalid_input` and does not say which text caused it. One case is different. If the refused text is in a routing request's inventory or catalog, the command line answers `routing_failed` with the code `credential-like material`. That failed decision is stored, and so is the task text if raw-task retention is on.† JEV Drill never edits text: it passes unchanged or it is refused.

**What is not detected.** These pass the check. They reach the judgment provider and, when raw-task retention is on, local storage, exports and archives.
- Other names: `token`, `GITHUB_TOKEN`, `passwd`, `credential`, `private_key`, `auth`, cookies.
- Secrets with no name: bare API tokens, key ids, connection strings such as `postgres://user:pass@host`.
- A listed name with none of the four signs after it: "the password is X", `--password X`, a `.netrc` line, a pair such as `["X-API-Key", "X"]`, a value written before its name, or a blank line between name and sign.
- A name built from pieces (`'pass' + 'word'`) or hidden by another encoding, such as base64.

**Also know.**
- Ordinary text can be refused: a sentence that mentions `password` and later has a colon or a web address, or a line that begins "Basic …". In two small samples the check refused 5 of 30 developer texts and none of 36 evaluation tasks. The rate on real tasks is not measured.
- Text whose escapes are nested more than four deep, or that has a long run of backslashes, is refused whatever else it contains.
- Anyone who can put text into a request can cause a refusal.
- JEV Drill stores SHA-256 fingerprints of the requests it answers. It fingerprints the whole request as received, and also parts of it, such as each description, the attachments with their text, and the settings. It does so whether or not raw-task retention is on, and also for a routing request whose inventory or catalog was refused.†
- Development cases and guidance that the host program registers for experiments are not checked. They are sent to the experiment's model provider as registered.‡
- Importing a backup or restoring an archive writes the saved text back to local storage as it was saved. It is not checked, and it is written back even if raw retention is now off.‡
- Text JEV Drill reads back from its own local stores is not checked again, with two exceptions. A routing request linked to a discovery takes that discovery's stored required guidance, and a completed maintenance run passes the stored objectives of the last analysis to a new analysis. Both are checked like request text. If stored text now fails the check, for example after an upgrade changes the check, the linked routing request is refused, and the maintenance run answers `invalid_input` although its maintenance work is done.†
- This check is a safety net. The main controls are path exclusions for credential files, raw-task retention (off unless you turn it on), and `local_only` and the allowed-provider list, which keep text away from the judgment provider altogether.

† How the application uses the check; confirmed in the S5 review. ‡ Confirmed in the S4 review. A sentence found wrong comes back to the owner.
