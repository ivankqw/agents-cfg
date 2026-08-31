#!/usr/bin/env python3
"""Constrain imported skill metadata after a restore or update."""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import shutil
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


def validate_lock(repo_lock: pathlib.Path, home_lock: pathlib.Path) -> list[str]:
    if not repo_lock.is_file():
        raise FileNotFoundError(f"missing repo skills lock: {repo_lock}")
    desired = repo_lock.resolve(strict=False)
    if home_lock.is_symlink():
        current = symlink_target(home_lock).resolve(strict=False)
        if current != desired:
            raise RuntimeError(
                f"refusing to retarget skills lock symlink: {home_lock} -> {os.readlink(home_lock)}"
            )
        return [f"skills-lock: already points to {repo_lock}"]
    if home_lock.exists():
        raise RuntimeError(f"refusing to replace non-symlink skills lock: {home_lock}")
    return [f"skills-lock: available at {home_lock}"]


def install_lock(repo_lock: pathlib.Path, home_lock: pathlib.Path) -> list[str]:
    validate_lock(repo_lock, home_lock)
    if home_lock.is_symlink():
        home_lock.unlink()
    home_lock.symlink_to(repo_lock)
    return [f"skills-lock: linked {home_lock} -> {repo_lock}"]


def looks_like_upstream_main_ponytail(path: pathlib.Path) -> bool:
    skill = path / "SKILL.md"
    if not skill.is_file():
        return False
    text = skill.read_text()
    return all(anchor in text for anchor in UPSTREAM_MAIN_PONYTAIL_ANCHORS)


def ensure_disabled_root(path: pathlib.Path) -> None:
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.chmod(0o700)


def quarantine_path(disabled_root: pathlib.Path, name: str) -> pathlib.Path:
    ensure_disabled_root(disabled_root)
    stem = disabled_root / f"{name}.upstream-disabled"
    if not stem.exists():
        return stem
    index = 1
    while True:
        candidate = disabled_root / f"{name}.upstream-disabled.{index}"
        if not candidate.exists():
            return candidate
        index += 1


def legacy_quarantine_path(disabled_root: pathlib.Path, name: str) -> pathlib.Path:
    ensure_disabled_root(disabled_root)
    candidate = disabled_root / name
    if not candidate.exists():
        return candidate
    index = 1
    while True:
        candidate = disabled_root / f"{name}.{index}"
        if not candidate.exists():
            return candidate
        index += 1


def migrate_legacy_ponytail_quarantines(
    active_root: pathlib.Path, disabled_root: pathlib.Path
) -> list[str]:
    validate_legacy_ponytail_quarantines(active_root)

    if not active_root.is_dir():
        raise FileNotFoundError(f"missing active skill root: {active_root}")

    results: list[str] = []
    candidates = sorted(
        path
        for path in active_root.iterdir()
        if path.name == "ponytail.upstream-disabled"
        or path.name.startswith("ponytail.upstream-disabled.")
    )
    for path in candidates:
        archived = legacy_quarantine_path(disabled_root, path.name)
        shutil.move(str(path), str(archived))
        results.append(f"ponytail: moved legacy quarantine {path} to {archived}")
    return results


def validate_legacy_ponytail_quarantines(
    active_root: pathlib.Path, missing_ok: bool = False
) -> list[str]:
    if not active_root.is_dir():
        if missing_ok:
            return [f"ponytail: no active skill root at {active_root}"]
        raise FileNotFoundError(f"missing active skill root: {active_root}")

    candidates = sorted(
        path
        for path in active_root.iterdir()
        if path.name == "ponytail.upstream-disabled"
        or path.name.startswith("ponytail.upstream-disabled.")
    )
    for path in candidates:
        if not path.is_dir() or path.is_symlink() or not looks_like_upstream_main_ponytail(path):
            raise RuntimeError(
                "unknown legacy ponytail quarantine "
                f"{path}. Move it aside manually before install can link Claude skills."
            )
    return [f"ponytail: legacy quarantine preflight ok in {active_root}"]


def validate_ponytail_install(source: pathlib.Path, destination: pathlib.Path) -> list[str]:
    if not source.exists():
        raise FileNotFoundError(f"missing ponytail source: {source}")

    if destination.is_symlink():
        current_target = symlink_target(destination).resolve(strict=False)
        desired_target = source.resolve(strict=False)
        if current_target == desired_target:
            return [f"ponytail: symlink preflight ok at {destination}"]
        raise RuntimeError(
            "refusing to retarget ponytail symlink "
            f"{destination} -> {symlink_target(destination)}. "
            f"Move it aside manually before linking the repo wrapper at {source}."
        )

    if not destination.exists():
        return [f"ponytail: destination available at {destination}"]

    if destination.is_dir() and looks_like_upstream_main_ponytail(destination):
        return [f"ponytail: known upstream collision at {destination}"]

    raise RuntimeError(
        "refusing to replace non-symlink ponytail path "
        f"{destination}. Move it aside, or replace it with the repo wrapper at {source}."
    )


def validate_ponytail_preflight(source: pathlib.Path, active_root: pathlib.Path) -> list[str]:
    results = validate_legacy_ponytail_quarantines(active_root, missing_ok=True)
    results.extend(validate_ponytail_install(source, active_root / "ponytail"))
    return results


def validate_no_private_ponytail(private_root: pathlib.Path) -> list[str]:
    private_ponytail = private_root / "skills" / "ponytail"
    if os.path.lexists(private_ponytail):
        raise RuntimeError(
            "refusing private ponytail override "
            f"{private_ponytail}. Move it aside; the repo wrapper owns the ponytail skill."
        )
    return [f"ponytail: no private override at {private_ponytail}"]


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


def validate_install_preflight(
    repo_lock: pathlib.Path,
    home_lock: pathlib.Path,
    pstack_dir: pathlib.Path,
    pstack_revision_file: pathlib.Path,
    active_root: pathlib.Path,
    ponytail_source: pathlib.Path,
    private_root: pathlib.Path,
) -> list[str]:
    results = validate_lock(repo_lock, home_lock)
    results.extend(validate_pstack_checkout(pstack_dir, pstack_revision_file))
    results.extend(validate_ponytail_preflight(ponytail_source, active_root))
    results.extend(validate_no_private_ponytail(private_root))
    return results


def validate_operator_state_preflight(
    repo_lock: pathlib.Path,
    home_lock: pathlib.Path,
    active_root: pathlib.Path,
    ponytail_source: pathlib.Path,
    private_root: pathlib.Path,
) -> list[str]:
    results = validate_lock(repo_lock, home_lock)
    results.extend(validate_ponytail_preflight(ponytail_source, active_root))
    results.extend(validate_no_private_ponytail(private_root))
    return results


def install_ponytail(
    source: pathlib.Path, destination: pathlib.Path, disabled_root: pathlib.Path
) -> list[str]:
    validate_ponytail_install(source, destination)

    if destination.is_symlink():
        return [f"ponytail: already linked to {source}"]

    if not destination.exists():
        destination.symlink_to(source)
        return [f"ponytail: linked {destination} -> {source}"]

    if destination.is_dir() and looks_like_upstream_main_ponytail(destination):
        archived = quarantine_path(disabled_root, destination.name)
        shutil.move(str(destination), str(archived))
        destination.symlink_to(source)
        return [
            f"ponytail: quarantined broad upstream skill to {archived}",
            f"ponytail: linked {destination} -> {source}",
        ]

    raise RuntimeError("unreachable ponytail install state")


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
            "install-lock",
            "install-ponytail",
            "migrate-ponytail-quarantine",
            "preflight-install",
            "preflight-lock",
            "preflight-operator-state",
            "preflight-ponytail",
            "preflight-private-ponytail",
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
        if args.command == "preflight-lock":
            repo_lock, home_lock = require_paths(2, "preflight-lock requires repo-lock and home-lock")
            emit(validate_lock(repo_lock, home_lock))
            return 0

        if args.command == "install-lock":
            repo_lock, home_lock = require_paths(2, "install-lock requires repo-lock and home-lock")
            emit(install_lock(repo_lock, home_lock))
            return 0

        if args.command == "preflight-ponytail":
            source, active_root = require_paths(2, "preflight-ponytail requires source and active-root")
            emit(validate_ponytail_preflight(source, active_root))
            return 0

        if args.command == "preflight-private-ponytail":
            (private_root,) = require_paths(1, "preflight-private-ponytail requires private-root")
            emit(validate_no_private_ponytail(private_root))
            return 0

        if args.command == "preflight-install":
            (
                repo_lock,
                home_lock,
                pstack_dir,
                pstack_revision_file,
                active_root,
                ponytail_source,
                private_root,
            ) = require_paths(
                7,
                "preflight-install requires repo-lock, home-lock, pstack-dir, "
                "revision-file, active-root, ponytail-source, and private-root",
            )
            emit(
                validate_install_preflight(
                    repo_lock,
                    home_lock,
                    pstack_dir,
                    pstack_revision_file,
                    active_root,
                    ponytail_source,
                    private_root,
                )
            )
            return 0

        if args.command == "preflight-operator-state":
            (
                repo_lock,
                home_lock,
                active_root,
                ponytail_source,
                private_root,
            ) = require_paths(
                5,
                "preflight-operator-state requires repo-lock, home-lock, active-root, "
                "ponytail-source, and private-root",
            )
            emit(
                validate_operator_state_preflight(
                    repo_lock,
                    home_lock,
                    active_root,
                    ponytail_source,
                    private_root,
                )
            )
            return 0

        if args.command == "install-ponytail":
            source, destination, disabled_root = require_paths(
                3, "install-ponytail requires source, destination, and disabled-root"
            )
            emit(install_ponytail(source, destination, disabled_root))
            return 0

        if args.command == "migrate-ponytail-quarantine":
            active_root, disabled_root = require_paths(
                2, "migrate-ponytail-quarantine requires active-root and disabled-root"
            )
            emit(migrate_legacy_ponytail_quarantines(active_root, disabled_root))
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
