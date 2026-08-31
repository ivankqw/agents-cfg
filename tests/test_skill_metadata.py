from __future__ import annotations

import contextlib
import io
import os
import pathlib
import re
import shutil
import subprocess
import tempfile
import textwrap
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(ROOT / "scripts"))
import skill_metadata


FIXTURES = {
    "cyclomatic-complexity": textwrap.dedent(
        """\
        ---
        name: cyclomatic-complexity
        description: Refactor code to reduce cyclomatic complexity so it stays readable, maintainable, and aligned with the long-term vision of the codebase, not just optimized for AI comprehension. Use whenever the user asks to refactor, simplify, clean up, or review code quality; mentions complexity, maintainability, readability, spaghetti code, deeply nested logic, or god functions; or asks to check AI-generated code before merging. Also use proactively after writing any nontrivial function with heavy branching.
        ---

        # Cyclomatic Complexity
        """
    ),
    "ponytail-audit": textwrap.dedent(
        """\
        ---
        name: ponytail-audit
        description: >
          Whole-repo audit for over-engineering. Like ponytail-review, but scans the
          entire codebase instead of a diff: a ranked list of what to delete, simplify,
          or replace with stdlib/native equivalents. Use when the user says "audit this
          codebase", "audit for over-engineering", "what can I delete from this repo",
          "find bloat", "ponytail-audit", or "/ponytail-audit". One-shot report, does
          not apply fixes.
        ---

        ponytail-review, repo-wide.
        """
    ),
    "ponytail-debt": textwrap.dedent(
        """\
        ---
        name: ponytail-debt
        description: >
          Harvest every `ponytail:` comment in the codebase into a debt ledger, so the
          deliberate shortcuts and deferrals ponytail leaves behind get tracked instead
          of rotting into "later means never". Use when the user says "ponytail debt",
          "/ponytail-debt", "what did ponytail defer", "list the shortcuts", "ponytail
          ledger", or "what did we mark to do later". One-shot report, changes nothing.
        ---

        Every deliberate ponytail shortcut is marked with a `ponytail:` comment.
        """
    ),
    "ponytail-gain": textwrap.dedent(
        """\
        ---
        name: ponytail-gain
        description: >
          Show ponytail's measured impact as a compact scoreboard: less code, less
          cost, more speed, from the benchmark medians. One-shot display, not a
          persistent mode, and not a per-repo number. Trigger: /ponytail-gain,
          "ponytail gain", "what does ponytail save", "show ponytail impact",
          "ponytail scoreboard".
        ---

        # Ponytail Gain
        """
    ),
    "ponytail-help": textwrap.dedent(
        """\
        ---
        name: ponytail-help
        description: >
          Quick-reference card for all ponytail modes, skills, and commands.
          One-shot display, not a persistent mode. Trigger: /ponytail-help,
          "ponytail help", "what ponytail commands", "how do I use ponytail".
        ---

        # Ponytail Help
        """
    ),
    "ponytail-review": textwrap.dedent(
        """\
        ---
        name: ponytail-review
        description: >
          Code review focused exclusively on over-engineering. Finds what to delete:
          reinvented standard library, unneeded dependencies, speculative abstractions,
          dead flexibility. One line per finding: location, what to cut, what replaces
          it. Use when the user says "review for over-engineering", "what can we
          delete", "is this over-engineered", "simplify review", or invokes
          /ponytail-review. Complements correctness-focused review, this one only
          hunts complexity.
        ---

        Review diffs for unnecessary complexity.
        """
    ),
}

UPSTREAM_MAIN_PONYTAIL = textwrap.dedent(
    """\
    ---
    name: ponytail
    description: >
      Forces the laziest solution that actually works, simplest, shortest, most
      minimal. Channels a senior dev who has seen everything: question whether the
      task needs to exist at all (YAGNI), reach for the standard library before
      custom code, native platform features before dependencies, one line before
      fifty. Supports intensity levels: lite, full (default), ultra. Use on ANY
      coding task: writing, adding, refactoring, fixing, reviewing, or designing
      code, and choosing libraries or dependencies.
    argument-hint: "[lite|full|ultra]"
    license: MIT
    ---

    # Ponytail
    """
)

REPO_WRAPPER_PONYTAIL = textwrap.dedent(
    """\
    ---
    name: ponytail
    description: Use only when the user explicitly names Ponytail or asks to use the ponytail skill.
    license: MIT
    ---

    # Ponytail
    """
)

EXPECTED_OVERRIDE_NAMES = (
    "cyclomatic-complexity",
    "ponytail-audit",
    "ponytail-debt",
    "ponytail-gain",
    "ponytail-help",
    "ponytail-review",
)


class SkillMetadataTest(unittest.TestCase):
    def create_root(self) -> pathlib.Path:
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        root = pathlib.Path(tempdir.name)
        for name, content in FIXTURES.items():
            skill_dir = root / name
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(content)
        return root

    def disabled_root_for(self, active_root: pathlib.Path) -> pathlib.Path:
        disabled_root = active_root.parent / f"{active_root.name}-skills-disabled"
        self.addCleanup(lambda: shutil.rmtree(disabled_root, ignore_errors=True))
        return disabled_root

    def test_check_fails_for_broad_descriptions(self) -> None:
        root = self.create_root()

        self.assertEqual(
            sorted(skill_metadata.check_overrides(root)),
            sorted(f"{name}: broad or mismatched description" for name in FIXTURES),
        )

    def test_check_fails_for_missing_root(self) -> None:
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        missing = pathlib.Path(tempdir.name) / "misspelled-skills-root"

        self.assertEqual(
            skill_metadata.check_overrides(missing),
            [f"missing skill root: {missing}"],
        )

    def test_check_fails_for_missing_expected_skill(self) -> None:
        root = self.create_root()
        missing = root / "ponytail-review"
        for path in sorted(missing.iterdir()):
            path.unlink()
        missing.rmdir()

        self.assertIn(
            "ponytail-review: missing expected skill",
            skill_metadata.check_overrides(root),
        )

    def test_cli_check_does_not_print_success_for_missing_skill(self) -> None:
        root = self.create_root()
        missing = root / "ponytail-review"
        for path in sorted(missing.iterdir()):
            path.unlink()
        missing.rmdir()
        stdout = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            rc = skill_metadata.main(["check", str(root)])

        self.assertEqual(rc, 1)
        self.assertIn("ponytail-review: missing expected skill", stdout.getvalue())
        self.assertNotIn("explicit-use description", stdout.getvalue())

    def test_override_descriptions_require_explicit_user_invocation_for_every_skill(self) -> None:
        self.assertEqual(
            set(skill_metadata.EXPLICIT_USE_DESCRIPTIONS),
            set(EXPECTED_OVERRIDE_NAMES),
        )
        for name in EXPECTED_OVERRIDE_NAMES:
            description = skill_metadata.EXPLICIT_USE_DESCRIPTIONS[name]
            self.assertIn("Use only when the user explicitly names", description, name)
            self.assertRegex(
                description,
                rf"asks to use (the )?{re.escape(name)} skill",
                name,
            )
            self.assertIn("Do not invoke it for ordinary", description, name)
            self.assertNotIn("Use whenever", description, name)
            self.assertNotIn("Use on ANY", description, name)

    def test_apply_rewrites_descriptions_and_preserves_body(self) -> None:
        root = self.create_root()

        skill_metadata.apply_overrides(root)

        self.assertEqual(skill_metadata.check_overrides(root), [])
        self.assertIn(
            "# Cyclomatic Complexity",
            (root / "cyclomatic-complexity" / "SKILL.md").read_text(),
        )
        self.assertIn(
            "Review diffs for unnecessary complexity.",
            (root / "ponytail-review" / "SKILL.md").read_text(),
        )

    def test_apply_is_idempotent(self) -> None:
        root = self.create_root()

        skill_metadata.apply_overrides(root)
        once = (root / "ponytail-review" / "SKILL.md").read_text()
        skill_metadata.apply_overrides(root)

        self.assertEqual(once, (root / "ponytail-review" / "SKILL.md").read_text())

    def test_install_ponytail_quarantines_known_upstream_collision(self) -> None:
        root = self.create_root()
        source = root / "repo-ponytail"
        source.mkdir()
        (source / "SKILL.md").write_text(REPO_WRAPPER_PONYTAIL)
        destination = root / "ponytail"
        destination.mkdir()
        (destination / "SKILL.md").write_text(UPSTREAM_MAIN_PONYTAIL)
        disabled_root = self.disabled_root_for(root)

        skill_metadata.install_ponytail(source, destination, disabled_root)

        self.assertTrue(destination.is_symlink())
        self.assertEqual(destination.resolve(), source.resolve())
        archived = disabled_root / "ponytail.upstream-disabled"
        self.assertTrue(archived.is_dir())
        self.assertIn("Use on ANY", (archived / "SKILL.md").read_text())
        self.assertEqual(oct(disabled_root.stat().st_mode & 0o777), "0o700")
        self.assertFalse(
            any("upstream-disabled" in str(path.relative_to(root)) for path in root.rglob("SKILL.md"))
        )

    def test_legacy_upstream_quarantine_dirs_move_out_of_active_skill_root(self) -> None:
        root = self.create_root()
        legacy = root / "ponytail.upstream-disabled.7"
        legacy.mkdir()
        (legacy / "SKILL.md").write_text(UPSTREAM_MAIN_PONYTAIL)
        current_source_bytes = b"current source payload\n"
        (legacy / "payload.bin").write_bytes(current_source_bytes)
        disabled_root = self.disabled_root_for(root)

        messages = skill_metadata.migrate_legacy_ponytail_quarantines(root, disabled_root)

        archived = disabled_root / "ponytail.upstream-disabled.7"
        self.assertFalse(legacy.exists())
        self.assertTrue(archived.is_dir())
        self.assertEqual((archived / "payload.bin").read_bytes(), current_source_bytes)
        self.assertIn("Use on ANY", (archived / "SKILL.md").read_text())
        self.assertEqual(
            messages,
            [f"ponytail: moved legacy quarantine {legacy} to {archived}"],
        )
        self.assertFalse(
            any(path.name.startswith("ponytail.upstream-disabled") for path in root.iterdir())
        )

    def test_legacy_quarantine_refuses_unknown_contents(self) -> None:
        root = self.create_root()
        legacy = root / "ponytail.upstream-disabled"
        legacy.mkdir()
        (legacy / "SKILL.md").write_text(
            "---\nname: ponytail\ndescription: custom local content\n---\n"
        )
        disabled_root = self.disabled_root_for(root)

        with self.assertRaisesRegex(RuntimeError, "unknown legacy ponytail quarantine"):
            skill_metadata.migrate_legacy_ponytail_quarantines(root, disabled_root)

        self.assertTrue(legacy.is_dir())
        self.assertFalse(disabled_root.exists())

    def test_install_ponytail_refuses_unknown_collision(self) -> None:
        root = self.create_root()
        source = root / "repo-ponytail"
        source.mkdir()
        (source / "SKILL.md").write_text(REPO_WRAPPER_PONYTAIL)
        destination = root / "ponytail"
        destination.mkdir()
        (destination / "SKILL.md").write_text(
            "---\nname: ponytail\ndescription: custom local content\n---\n"
        )
        disabled_root = self.disabled_root_for(root)

        with self.assertRaisesRegex(RuntimeError, "refusing to replace non-symlink ponytail path"):
            skill_metadata.install_ponytail(source, destination, disabled_root)

        self.assertTrue(destination.is_dir())
        self.assertFalse(destination.is_symlink())

    def test_update_wrapper_reapplies_and_checks_metadata_after_npx_update(self) -> None:
        wrapper = ROOT / "bin" / "skills-update"

        text = wrapper.read_text()

        self.assertIn("npx skills update", text)
        self.assertIsNotNone(
            re.search(
                r"npx skills update.*skill_metadata\.py\" apply.*skill_metadata\.py\" check",
                text,
                re.S,
            )
        )

    def test_update_wrapper_restores_unlocks_after_fake_npx_update(self) -> None:
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        home = pathlib.Path(tempdir.name) / "home"
        shared = home / ".agents" / "skills"
        fakebin = pathlib.Path(tempdir.name) / "bin"
        shared.mkdir(parents=True)
        fakebin.mkdir()
        for name, content in FIXTURES.items():
            skill_dir = shared / name
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(content)
        skill_metadata.apply_overrides(shared)

        npx = fakebin / "npx"
        npx.write_text(
            textwrap.dedent(
                """\
                #!/usr/bin/env bash
                set -euo pipefail
                printf '%s\n' "$*" > "$HOME/npx.args"
                [ "$1" = "skills" ]
                [ "$2" = "update" ]
                mkdir -p "$HOME/.agents/skills/wayfinder"
                printf '%s\n' \\
                  '---' \\
                  'name: wayfinder' \\
                  'description: Find a route through unfamiliar code.' \\
                  'disable-model-invocation: true' \\
                  '---' \\
                  '' \\
                  '# Wayfinder' \\
                  > "$HOME/.agents/skills/wayfinder/SKILL.md"
                """
            )
        )
        npx.chmod(0o755)

        env = os.environ.copy()
        env["HOME"] = str(home)
        env["PATH"] = f"{fakebin}{os.pathsep}{env['PATH']}"

        result = subprocess.run(
            [str(ROOT / "bin" / "skills-update")],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual((home / "npx.args").read_text(), "skills update\n")
        wayfinder = (shared / "wayfinder" / "SKILL.md").read_text()
        self.assertNotIn("disable-model-invocation: true", wayfinder)
        self.assertIn("name: wayfinder", wayfinder)

    def test_install_moves_legacy_quarantines_before_claude_skill_links(self) -> None:
        text = (ROOT / "install.sh").read_text()

        migrate = text.index("migrate-ponytail-quarantine")
        claude_links = text.index('for d in "$SHARED_SKILLS"/*/; do link')

        self.assertLess(migrate, claude_links)

    def test_install_and_update_paths_share_unlock_command(self) -> None:
        install = (ROOT / "install.sh").read_text()
        update = (ROOT / "bin" / "skills-update").read_text()

        self.assertIn('skill_metadata.py" unlock "$AC/skills-unlock.txt" "$SHARED_SKILLS"', install)
        self.assertIn('skill_metadata.py" unlock "$AC/skills-unlock.txt" "$SHARED_SKILLS"', update)


if __name__ == "__main__":
    unittest.main()
