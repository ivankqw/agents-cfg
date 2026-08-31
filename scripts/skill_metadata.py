#!/usr/bin/env python3
"""Constrain imported skill metadata after a restore or update."""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import shutil
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

UPSTREAM_MAIN_PONYTAIL_ANCHORS = (
    "name: ponytail",
    'argument-hint: "[lite|full|ultra]"',
    "Supports intensity levels: lite, full (default), ultra.",
    "Use on ANY",
)


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


def symlink_target(path: pathlib.Path) -> pathlib.Path:
    target = pathlib.Path(os.readlink(path))
    if not target.is_absolute():
        target = path.parent / target
    return target


def looks_like_upstream_main_ponytail(path: pathlib.Path) -> bool:
    skill = path / "SKILL.md"
    if not skill.is_file():
        return False
    text = skill.read_text()
    return all(anchor in text for anchor in UPSTREAM_MAIN_PONYTAIL_ANCHORS)


def quarantine_path(path: pathlib.Path) -> pathlib.Path:
    stem = path.with_name(path.name + ".upstream-disabled")
    if not stem.exists():
        return stem
    index = 1
    while True:
        candidate = path.with_name(f"{path.name}.upstream-disabled.{index}")
        if not candidate.exists():
            return candidate
        index += 1


def install_ponytail(source: pathlib.Path, destination: pathlib.Path) -> list[str]:
    if not source.exists():
        raise FileNotFoundError(f"missing ponytail source: {source}")

    if destination.is_symlink():
        current_target = symlink_target(destination).resolve(strict=False)
        desired_target = source.resolve(strict=False)
        if current_target == desired_target:
            return [f"ponytail: already linked to {source}"]
        destination.unlink()
        destination.symlink_to(source)
        return [f"ponytail: retargeted symlink to {source}"]

    if not destination.exists():
        destination.symlink_to(source)
        return [f"ponytail: linked {destination} -> {source}"]

    if destination.is_dir() and looks_like_upstream_main_ponytail(destination):
        archived = quarantine_path(destination)
        shutil.move(str(destination), str(archived))
        destination.symlink_to(source)
        return [
            f"ponytail: quarantined broad upstream skill to {archived}",
            f"ponytail: linked {destination} -> {source}",
        ]

    raise RuntimeError(
        "refusing to replace non-symlink ponytail path "
        f"{destination}. Move it aside, or replace it with the repo wrapper at {source}."
    )


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
    parser.add_argument("command", choices=("apply", "check", "install-ponytail"))
    parser.add_argument("path1")
    parser.add_argument("path2", nargs="?")
    args = parser.parse_args(argv)

    if args.command == "install-ponytail":
        if args.path2 is None:
            parser.error("install-ponytail requires source and destination")
        emit(install_ponytail(pathlib.Path(args.path1), pathlib.Path(args.path2)))
        return 0

    root = pathlib.Path(args.path1)

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
