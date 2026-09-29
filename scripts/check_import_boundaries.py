"""Check application module ownership, direct imports and cycles using Python AST."""
import argparse
import ast
import json
from pathlib import Path

import yaml


def check(root):
    registry = yaml.safe_load((root / "docs/vocabulary.yaml").read_text(encoding="utf-8"))
    rules = registry["import_rules"]
    errors = []
    graph = {}
    package = root / "src/jevdrill"
    for file in package.rglob("*.py"):
        relative = file.relative_to(package)
        if relative.name == "__init__.py":
            continue
        owner = relative.parts[0].removesuffix(".py")
        if owner not in rules:
            errors.append(f"unowned module: {relative}")
            continue
        targets = set()
        for node in ast.walk(ast.parse(file.read_text(encoding="utf-8"), filename=str(relative))):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] == "baml_sdk":
                        targets.add("baml_sdk")
                    if alias.name.startswith("jevdrill."):
                        targets.add(alias.name.split(".")[1])
            elif isinstance(node, ast.ImportFrom):
                if (node.module or "").split(".")[0] == "baml_sdk":
                    targets.add("baml_sdk")
                if node.level:
                    parent = list(relative.parts[:-1])
                    if node.level > len(parent) + 1:
                        errors.append(f"relative import escapes package: {relative}")
                        continue
                    base = parent[:len(parent) - node.level + 1]
                    suffix = node.module.split(".") if node.module else []
                    parts = base + suffix
                    if parts:
                        targets.add(parts[0])
                    else:
                        targets.update(alias.name for alias in node.names)
                elif node.module == "jevdrill":
                    targets.update(alias.name for alias in node.names)
                elif (node.module or "").startswith("jevdrill."):
                    targets.add(node.module.split(".")[1])
        graph.setdefault(owner, set()).update(targets - {owner, "baml_sdk"})
        for target in targets - {owner}:
            if target not in rules[owner]:
                errors.append(f"forbidden import: {owner} -> {target}")
    visiting, visited = set(), set()

    def visit(node):
        if node in visiting:
            errors.append(f"import cycle: {node}")
            return
        if node in visited:
            return
        visiting.add(node)
        for target in graph.get(node, []):
            visit(target)
        visiting.remove(node)
        visited.add(node)

    for node in graph:
        visit(node)
    return errors


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    errors = check(args.root)
    print(json.dumps({"passed": not errors, "errors": errors}))
    raise SystemExit(bool(errors))
