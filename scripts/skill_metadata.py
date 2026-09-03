#!/usr/bin/env python3
"""Constrain imported skill metadata after a restore or update."""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import subprocess
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
        "data, not current-repository measurements. Do not invoke it for "
        "ordinary metrics, benchmarking, performance, or reporting requests."
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


def validate_skill_name(path: pathlib.Path, expected: str) -> list[str]:
    if not path.is_file():
        raise FileNotFoundError(f"missing skill file: {path}")
    frontmatter, _ = split_frontmatter(path.read_text())
    names = []
    for line in frontmatter:
        match = re.fullmatch(r"name:[ \t]*(\S(?:.*\S)?)[ \t]*\r?\n?", line)
        if match:
            names.append(match.group(1))
    if names != [expected]:
        actual = ", ".join(names) if names else "missing"
        raise RuntimeError(f"skill name mismatch in {path}: expected {expected}, found {actual}")
    return [f"skill name: {expected}"]


def skill_file(root: pathlib.Path, name: str) -> pathlib.Path:
    return root / name / "SKILL.md"


def symlink_target(path: pathlib.Path) -> pathlib.Path:
    target = pathlib.Path(os.readlink(path))
    if not target.is_absolute():
        target = path.parent / target
    return target


def read_pstack_revision(revision_file: pathlib.Path) -> str:
    lines = revision_file.read_text().splitlines()
    revision = lines[0] if lines else ""
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise RuntimeError(f"invalid pstack revision in {revision_file}")
    return revision


def git_stdout(args: list[str]) -> str:
    if args and args[0] == "git":
        args = [os.environ.get("GIT", "git"), *args[1:]]
    try:
        result = subprocess.run(args, text=True, capture_output=True, check=False)
    except OSError as error:
        raise RuntimeError(f"git command failed: {error}") from error
    if result.returncode != 0:
        output = (result.stderr + result.stdout).strip()
        detail = f": {output}" if output else ""
        raise RuntimeError(f"git command failed{detail}")
    return result.stdout


def validate_pstack_checkout(pstack_dir: pathlib.Path, revision_file: pathlib.Path) -> list[str]:
    revision = read_pstack_revision(revision_file)
    if not (pstack_dir / ".git").is_dir():
        raise RuntimeError(f"pstack checkout is missing: {pstack_dir}")

    actual = git_stdout(["git", "-C", str(pstack_dir), "rev-parse", "HEAD"]).strip()
    if actual != revision:
        raise RuntimeError(f"pstack revision mismatch: expected {revision}, found {actual}")

    status = git_stdout(["git", "-C", str(pstack_dir), "status", "--porcelain"])
    if status:
        raise RuntimeError(f"pstack checkout has local changes; leaving it unchanged: {pstack_dir}")

    if not (pstack_dir / "plugins" / "pstack" / "skills").is_dir() or not (
        pstack_dir / "plugins" / "pstack" / ".codex-plugin" / "prompts"
    ).is_dir():
        raise RuntimeError(f"pstack checkout does not contain the expected plugin layout: {pstack_dir}")

    return [f"pstack: checkout preflight ok at {pstack_dir}"]


def apply_overrides(root: pathlib.Path) -> list[str]:
    if not root.is_dir():
        raise FileNotFoundError(f"missing skill root: {root}")
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


def unlock_skills(unlock_file: pathlib.Path, root: pathlib.Path) -> list[str]:
    if not unlock_file.exists():
        return []
    if not root.is_dir():
        raise FileNotFoundError(f"missing skill root: {root}")
    names = [
        line.strip()
        for line in unlock_file.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]
    results: list[str] = []
    for name in names:
        path = skill_file(root, name)
        if not path.exists():
            results.append(f"skip {name}: not installed")
            continue
        original = path.read_text()
        updated = re.sub(
            r"^disable-model-invocation:[ \t]*true[ \t]*\n",
            "",
            original,
            count=1,
            flags=re.M,
        )
        if updated == original:
            results.append(f"{name}: already unlocked")
            continue
        path.write_text(updated)
        results.append(f"{name}: unlocked")
    return results


def check_overrides(root: pathlib.Path) -> list[str]:
    problems: list[str] = []
    if not root.is_dir():
        return [f"missing skill root: {root}"]
    for name, description in EXPLICIT_USE_DESCRIPTIONS.items():
        path = skill_file(root, name)
        if not path.is_file():
            problems.append(f"{name}: missing expected skill")
            continue
        actual = replace_description(path.read_text(), description)
        if actual != path.read_text():
            problems.append(f"{name}: broad or mismatched description")
    return problems


def emit(lines: Iterable[str]) -> None:
    for line in lines:
        print(f"  {line}")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=(
            "apply",
            "check",
            "preflight-pstack",
            "require-skill-name",
            "unlock",
        ),
    )
    parser.add_argument("paths", nargs="*")
    args = parser.parse_args(argv)

    def require_paths(count: int, usage: str) -> list[pathlib.Path]:
        if len(args.paths) != count:
            parser.error(usage)
        return [pathlib.Path(value) for value in args.paths]

    try:
        if args.command == "preflight-pstack":
            pstack_dir, revision_file = require_paths(
                2, "preflight-pstack requires pstack-dir and revision-file"
            )
            emit(validate_pstack_checkout(pstack_dir, revision_file))
            return 0

        if args.command == "require-skill-name":
            path, expected = require_paths(
                2,
                "require-skill-name requires skill-file and expected-name",
            )
            emit(validate_skill_name(path, str(expected)))
            return 0

        if args.command == "unlock":
            unlock_file, root = require_paths(2, "unlock requires unlock-file and skill-root")
            emit(unlock_skills(unlock_file, root))
            return 0

        (root,) = require_paths(1, f"{args.command} requires skill-root")

        if args.command == "apply":
            emit(apply_overrides(root))
            return 0

        problems = check_overrides(root)
        if problems:
            emit(problems)
            return 1
        emit(f"{name}: explicit-use description" for name in EXPLICIT_USE_DESCRIPTIONS)
        return 0
    except (FileNotFoundError, RuntimeError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
