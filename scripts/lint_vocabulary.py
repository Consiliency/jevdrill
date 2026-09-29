"""Lint known aliases, public field spellings and declared application module names."""
import argparse
import ast
import json
from pathlib import Path
import re

import yaml


def check(root):
    registry = yaml.safe_load((root / "docs/vocabulary.yaml").read_text(encoding="utf-8"))
    scope = registry["usage_scope"]
    forbidden = set(scope["forbidden_public_fields"])
    forbidden.update(alias for row in registry["concepts"] for alias in row.get("forbidden_public_aliases", []))
    errors = []
    concepts = [row["id"] for row in registry["concepts"]]
    if len(concepts) != len(set(concepts)):
        errors.append("duplicate concept identifiers")
    for row in registry["concepts"]:
        if row["owner"] not in registry["modules"] or row["identifier"] != row["id"]:
            errors.append(f"invalid concept ownership/spelling: {row['id']}")
    for base in scope["code"]:
        for file in (root / base).rglob("*"):
            if file.suffix not in {".py", ".baml"} or any(
                file.is_relative_to(root / exclusion) for exclusion in scope["excluded"]
            ):
                continue
            if file.stem in registry["naming"]["forbid_module_names"]:
                errors.append(f"forbidden module: {file.relative_to(root)}")
            if file.suffix == ".py":
                nodes = ast.walk(ast.parse(file.read_text(encoding="utf-8")))
                fields = [node.target.id for node in nodes if isinstance(node, ast.AnnAssign)
                          and isinstance(node.target, ast.Name)]
            else:
                declarations = re.findall(r"\bclass\s+\w+\s*\{([^}]+)\}", file.read_text(encoding="utf-8"))
                fields = [field for body in declarations
                          for field in re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*:", body)]
            for field in fields:
                if field in forbidden or not re.fullmatch(r"[a-z][a-z0-9_]*", field):
                    errors.append(f"invalid field: {file.relative_to(root)}:{field}")
    for path in scope["docs"]:
        file = root / path
        if not file.exists():
            continue  # A later lane may own a not-yet-created document.
        for alias in forbidden - {"state", "configuration"}:
            if re.search(r"\b" + re.escape(alias) + r"\b", file.read_text(encoding="utf-8")):
                errors.append(f"forbidden public alias: {path}:{alias}")
    return errors


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    errors = check(args.root)
    print(json.dumps({"passed": not errors, "errors": errors}))
    raise SystemExit(bool(errors))
