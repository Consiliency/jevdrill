"""Check coverage references and detect source or criterion drift.

This verifies the mapping's integrity, not the semantic adequacy of prose.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re


def source_units(root):
    units = {}
    for name, pattern, prefix in (
        ("specs/jevdrill-design-input.md", r"^### (JD-\d+) —.*$", ""),
        ("docs/jevdrill-spec.md", r"^## (\d+)\. .*$", "DRAFT-"),
    ):
        text = (root / name).read_text(encoding="utf-8")
        headings = list(re.finditer(pattern, text, re.M))
        for index, match in enumerate(headings):
            end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
            section = text[match.end():end].strip()
            identity = prefix + match[1]
            # Each paragraph, list/table block and example is accounted for separately.
            blocks = re.split(r"\n\s*\n", section)
            if prefix:
                for number, block in enumerate(blocks, 1):
                    units[f"{identity}.{number:02}"] = (name, block.strip())
            else:
                units[identity] = (name, section)
    return units


def check(root, document):
    errors = []
    if document.get("schema_version") != 1:
        errors.append("unsupported coverage schema")
    units = source_units(root)
    criteria = dict(re.findall(r"^- \[[ x]\] (EC-[A-Z]+-\d+) — (.*)$",
                               (root / "specs/phase-plans-v1.md").read_text(encoding="utf-8"), re.M))
    seen = set()
    for entry in document.get("requirements", []):
        identity = entry.get("id")
        if identity in seen:
            errors.append(f"duplicate requirement: {identity}")
        seen.add(identity)
        if identity not in units:
            errors.append(f"unknown source requirement: {identity}")
            continue
        source, content = units[identity]
        digest = hashlib.sha256(content.encode()).hexdigest()
        if entry.get("source") != source or entry.get("source_sha256") != digest:
            errors.append(f"stale source: {identity}")
        if not entry.get("owner") or not entry.get("phase"):
            errors.append(f"missing owner/phase: {identity}")
        if entry.get("status") not in {"planned", "superseded", "deferred", "context"}:
            errors.append(f"unsupported completion claim: {identity}")
        if entry.get("status") in {"deferred", "superseded", "context"}:
            if not entry.get("reason"):
                errors.append(f"missing disposition reason: {identity}")
        targets = entry.get("criteria", [])
        if entry.get("status") == "planned" and not targets:
            errors.append(f"no verifying criterion: {identity}")
        for target in targets:
            ec = target.get("id")
            fragment = target.get("required_text", "")
            if ec not in criteria:
                errors.append(f"unknown criterion: {identity}/{ec}")
            elif not fragment or fragment not in criteria[ec]:
                errors.append(f"criterion no longer verifies mapped clause: {identity}/{ec}")
    for missing in sorted(set(units) - seen):
        errors.append(f"unmapped source: {missing}")
    expected = {f"{prefix}{n}" for prefix, count in (("R", 8), ("C", 7), ("P", 7))
                for n in range(1, count + 1)}
    reviews = document.get("review_items", [])
    review_ids = [row.get("id") for row in reviews]
    if set(review_ids) != expected or len(review_ids) != len(expected):
        errors.append("review inventory is incomplete or duplicated")
    for row in reviews:
        if not row.get("owner") or not row.get("phase") or not row.get("resolution"):
            errors.append(f"incomplete review disposition: {row.get('id')}")
        if any(ec not in criteria for ec in row.get("criteria", [])):
            errors.append(f"unknown review criterion: {row.get('id')}")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    document = json.loads((args.root / "evidence/CONTRACT/coverage.json").read_text(encoding="utf-8"))
    errors = check(args.root, document)
    print(json.dumps({"passed": not errors, "errors": errors,
                      "requirements": len(document["requirements"])}))
    return bool(errors)


if __name__ == "__main__":
    raise SystemExit(main())
