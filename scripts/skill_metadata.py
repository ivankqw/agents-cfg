#!/usr/bin/env python3
"""Constrain imported skill metadata after a restore or update."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Iterable

EXPLICIT_USE_DESCRIPTIONS = {
    "cyclomatic-complexity": (
        "Use only when the user explicitly names cyclomatic complexity or asks "
        "to use the cyclomatic-complexity skill. Do not invoke it for ordinary "
        "refactoring, simplification, cleanup, or code review requests."
    ),
    "ponytail-audit": (
        "Use only when the user explicitly names Ponytail audit or asks to use "
        "the ponytail-audit skill. Do not invoke it for ordinary audit, "
        "cleanup, or simplification requests."
    ),
    "ponytail-debt": (
        "Use only when the user explicitly names Ponytail debt or asks to use "
        "the ponytail-debt skill. Do not invoke it for ordinary debt, "
        "shortcut, or cleanup requests."
    ),
    "ponytail-gain": (
        "Use only when the user explicitly names Ponytail gain or asks to use "
        "the ponytail-gain skill. Treat benchmark figures as upstream sourced "
        "data, not current-repository measurements."
    ),
    "ponytail-help": (
        "Use only when the user explicitly names Ponytail help or asks to use "
        "the ponytail-help skill. Do not invoke it for ordinary help or "
        "discovery requests."
    ),
    "ponytail-review": (
        "Use only when the user explicitly names Ponytail review or asks to use "
        "the ponytail-review skill. Do not invoke it for ordinary review, "
        "refactoring, or simplification requests."
    ),
}


def split_frontmatter(text: str) -> tuple[list[str], str]:
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise ValueError("missing opening frontmatter boundary")
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return lines[1:index], "".join(lines[index + 1 :])
    raise ValueError("missing closing frontmatter boundary")


def description_range(lines: list[str]) -> tuple[int, int] | None:
    for start, line in enumerate(lines):
        if not line.startswith("description:"):
            continue
        end = start + 1
        while end < len(lines):
            candidate = lines[end]
            if candidate.startswith((" ", "\t")):
                end += 1
                continue
            break
        return start, end
    return None


def replace_description(text: str, description: str) -> str:
    frontmatter_lines, body = split_frontmatter(text)
    updated_lines = list(frontmatter_lines)
    description_line = f"description: {json.dumps(description)}\n"
    rng = description_range(updated_lines)
    if rng is None:
        updated_lines.append(description_line)
    else:
        start, end = rng
        updated_lines[start:end] = [description_line]
    return "---\n" + "".join(updated_lines) + "---\n" + body


def skill_file(root: pathlib.Path, name: str) -> pathlib.Path:
    return root / name / "SKILL.md"


def apply_overrides(root: pathlib.Path) -> list[str]:
    results: list[str] = []
    for name, description in EXPLICIT_USE_DESCRIPTIONS.items():
        path = skill_file(root, name)
        if not path.exists():
            results.append(f"skip {name}: not installed")
            continue
        original = path.read_text()
        updated = replace_description(original, description)
        if updated == original:
            results.append(f"{name}: already constrained")
            continue
        path.write_text(updated)
        results.append(f"{name}: constrained")
    return results


def check_overrides(root: pathlib.Path) -> list[str]:
    mismatches: list[str] = []
    for name, description in EXPLICIT_USE_DESCRIPTIONS.items():
        path = skill_file(root, name)
        if not path.exists():
            continue
        actual = replace_description(path.read_text(), description)
        if actual != path.read_text():
            mismatches.append(name)
    return mismatches


def emit(lines: Iterable[str]) -> None:
    for line in lines:
        print(f"  {line}")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("apply", "check"))
    parser.add_argument("root")
    args = parser.parse_args(argv)
    root = pathlib.Path(args.root)

    if args.command == "apply":
        emit(apply_overrides(root))
        return 0

    mismatches = check_overrides(root)
    if mismatches:
        emit(f"{name}: broad or mismatched description" for name in mismatches)
        return 1
    emit(f"{name}: explicit-use description" for name in EXPLICIT_USE_DESCRIPTIONS)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
