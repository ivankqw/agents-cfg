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

    def write_fake_git(self, fakebin: pathlib.Path, revision: str) -> None:
        git = fakebin / "git"
        git.write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "printf '%s\\n' \"$*\" >> \"$HOME/git.args\"\n"
            "if [ \"$1\" = \"-C\" ] && [ \"$3\" = \"pull\" ] && [ \"$4\" = \"--ff-only\" ]; then\n"
            "  exit 0\n"
            "fi\n"
            "if [ \"$1\" = \"-C\" ] && [ \"$3\" = \"rev-parse\" ] && [ \"$4\" = \"HEAD\" ]; then\n"
            "  printf '%s\\n' \"$FAKE_PSTACK_REVISION\"\n"
            "  exit 0\n"
            "fi\n"
            "if [ \"$1\" = \"-C\" ] && [ \"$3\" = \"status\" ] && [ \"$4\" = \"--porcelain\" ]; then\n"
            "  exit 0\n"
            "fi\n"
            "if [ \"$1\" = \"-C\" ] && [ \"$3\" = \"fetch\" ]; then\n"
            "  exit 0\n"
            "fi\n"
            "if [ \"$1\" = \"-C\" ] && [ \"$3\" = \"cat-file\" ]; then\n"
            "  exit 0\n"
            "fi\n"
            "if [ \"$1\" = \"-C\" ] && [ \"$3\" = \"checkout\" ]; then\n"
            "  exit 0\n"
            "fi\n"
            "printf 'unexpected git args: %s\\n' \"$*\" >&2\n"
            "exit 97\n"
        )
        git.chmod(0o755)
        self.assertEqual(len(revision), 40)

    def create_fake_pstack_checkout(self, root: pathlib.Path) -> pathlib.Path:
        pstack = root / "pstack"
        (pstack / ".git").mkdir(parents=True)
        skill = pstack / "plugins" / "pstack" / "skills" / "architect"
        prompt = pstack / "plugins" / "pstack" / ".codex-plugin" / "prompts"
        skill.mkdir(parents=True)
        prompt.mkdir(parents=True)
        (skill / "SKILL.md").write_text(
            "---\nname: architect\ndescription: pstack architect\n---\n"
        )
        (prompt / "architect.md").write_text("# architect\n")
        return pstack

    def populate_imported_skills(self, root: pathlib.Path) -> None:
        for name, content in FIXTURES.items():
            skill_dir = root / name
            skill_dir.mkdir(parents=True, exist_ok=True)
            (skill_dir / "SKILL.md").write_text(content)

    def write_partial_failure_npx(self, fakebin: pathlib.Path, status: int) -> None:
        npx = fakebin / "npx"
        npx.write_text(
            textwrap.dedent(
                f"""\
                #!/usr/bin/env bash
                set -euo pipefail
                printf '%s\n' "$*" > "$HOME/npx.args"
                mkdir -p "$HOME/.agents/skills/ponytail-review" "$HOME/.agents/skills/wayfinder"
                printf '%s\n' \\
                  '---' \\
                  'name: ponytail-review' \\
                  'description: Use whenever code needs review.' \\
                  '---' \\
                  '' \\
                  '# Ponytail Review' \\
                  > "$HOME/.agents/skills/ponytail-review/SKILL.md"
                printf '%s\n' \\
                  '---' \\
                  'name: wayfinder' \\
                  'description: Find a route through unfamiliar code.' \\
                  'disable-model-invocation: true' \\
                  '---' \\
                  '' \\
                  '# Wayfinder' \\
                  > "$HOME/.agents/skills/wayfinder/SKILL.md"
                exit {status}
                """
            )
        )
        npx.chmod(0o755)

    def base_runtime_env(
        self,
        home: pathlib.Path,
        fakebin: pathlib.Path,
        pstack: pathlib.Path | None = None,
        private: pathlib.Path | None = None,
    ) -> dict[str, str]:
        revision = (ROOT / "pstack-revision.txt").read_text().splitlines()[0]
        env = os.environ.copy()
        env["HOME"] = str(home)
        env["PATH"] = f"{fakebin}{os.pathsep}{env['PATH']}"
        env["PRIVATE_CONFIG"] = str(private or (home.parent / "missing-private"))
        env["PSTACK_DIR"] = str(pstack or (home.parent / "missing-pstack"))
        env["FAKE_PSTACK_REVISION"] = revision
        env["GIT"] = str(fakebin / "git")
        return env

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

    def test_cli_apply_fails_for_missing_root(self) -> None:
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        missing = pathlib.Path(tempdir.name) / "missing-skills-root"

        result = subprocess.run(
            ["python3", str(ROOT / "scripts" / "skill_metadata.py"), "apply", str(missing)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(f"missing skill root: {missing}", result.stderr + result.stdout)

    def test_cli_unlock_fails_for_missing_root(self) -> None:
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        root = pathlib.Path(tempdir.name)
        unlock_file = root / "skills-unlock.txt"
        unlock_file.write_text("wayfinder\n")
        missing = root / "missing-skills-root"

        result = subprocess.run(
            [
                "python3",
                str(ROOT / "scripts" / "skill_metadata.py"),
                "unlock",
                str(unlock_file),
                str(missing),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(f"missing skill root: {missing}", result.stderr + result.stdout)

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

    def test_install_ponytail_refuses_unknown_symlink_collision(self) -> None:
        root = self.create_root()
        source = root / "repo-ponytail"
        source.mkdir()
        (source / "SKILL.md").write_text(REPO_WRAPPER_PONYTAIL)
        private = root / "private-ponytail"
        private.mkdir()
        (private / "SKILL.md").write_text(
            "---\nname: ponytail\ndescription: private local wrapper\n---\n"
        )
        destination = root / "ponytail"
        destination.symlink_to(private)
        disabled_root = self.disabled_root_for(root)

        with self.assertRaisesRegex(RuntimeError, "refusing to retarget ponytail symlink"):
            skill_metadata.install_ponytail(source, destination, disabled_root)

        self.assertTrue(destination.is_symlink())
        self.assertEqual(skill_metadata.symlink_target(destination).resolve(), private.resolve())

    def test_update_wrapper_reapplies_and_checks_metadata_after_npx_update(self) -> None:
        wrapper = ROOT / "bin" / "skills-update"

        text = wrapper.read_text()

        self.assertIn("npx skills update", text)
        self.assertLess(text.index('skill_metadata.py" apply'), text.index('skill_metadata.py" check'))
        self.assertLess(text.index("npx skills update"), text.index("restore_metadata )"))

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

    def test_update_wrapper_refuses_regular_home_skills_lock(self) -> None:
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        home = pathlib.Path(tempdir.name) / "home"
        fakebin = pathlib.Path(tempdir.name) / "bin"
        home.mkdir()
        fakebin.mkdir()
        lock = home / "skills-lock.json"
        lock.write_text("operator-owned lock\n")
        npx = fakebin / "npx"
        npx.write_text(
            "#!/usr/bin/env bash\n"
            "printf '%s\\n' \"$*\" > \"$HOME/npx.args\"\n"
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

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(lock.is_symlink())
        self.assertEqual(lock.read_text(), "operator-owned lock\n")
        self.assertFalse((home / "npx.args").exists())

    def test_update_wrapper_refuses_custom_home_skills_lock_symlink_before_npx(self) -> None:
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        home = pathlib.Path(tempdir.name) / "home"
        fakebin = pathlib.Path(tempdir.name) / "bin"
        home.mkdir()
        fakebin.mkdir()
        custom_lock = pathlib.Path(tempdir.name) / "operator-lock.json"
        custom_lock.write_text("operator symlink lock\n")
        lock = home / "skills-lock.json"
        lock.symlink_to(custom_lock)
        npx = fakebin / "npx"
        npx.write_text(
            "#!/usr/bin/env bash\n"
            "printf '%s\\n' \"$*\" > \"$HOME/npx.args\"\n"
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

        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(lock.is_symlink())
        self.assertEqual(skill_metadata.symlink_target(lock).resolve(), custom_lock.resolve())
        self.assertEqual(custom_lock.read_text(), "operator symlink lock\n")
        self.assertFalse((home / "npx.args").exists())

    def test_update_wrapper_restores_metadata_after_failed_npx_and_preserves_npx_rc(self) -> None:
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        home = pathlib.Path(tempdir.name) / "home"
        shared = home / ".agents" / "skills"
        fakebin = pathlib.Path(tempdir.name) / "bin"
        shared.mkdir(parents=True)
        fakebin.mkdir()
        self.populate_imported_skills(shared)
        skill_metadata.apply_overrides(shared)
        self.write_partial_failure_npx(fakebin, 23)
        env = self.base_runtime_env(home, fakebin)

        result = subprocess.run(
            [str(ROOT / "bin" / "skills-update")],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 23, result.stderr + result.stdout)
        self.assertEqual((home / "npx.args").read_text(), "skills update\n")
        ponytail_review = (shared / "ponytail-review" / "SKILL.md").read_text()
        self.assertIn("Use only when the user explicitly names", ponytail_review)
        wayfinder = (shared / "wayfinder" / "SKILL.md").read_text()
        self.assertNotIn("disable-model-invocation: true", wayfinder)
        self.assertEqual((shared / "ponytail").resolve(), (ROOT / "skills" / "ponytail").resolve())

    def test_update_wrapper_refuses_unknown_ponytail_collision_before_npx(self) -> None:
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        home = pathlib.Path(tempdir.name) / "home"
        shared = home / ".agents" / "skills"
        fakebin = pathlib.Path(tempdir.name) / "bin"
        shared.mkdir(parents=True)
        fakebin.mkdir()
        self.populate_imported_skills(shared)
        ponytail = shared / "ponytail"
        ponytail.mkdir()
        (ponytail / "SKILL.md").write_text(
            "---\nname: ponytail\ndescription: custom local ponytail\n---\n"
        )
        npx = fakebin / "npx"
        npx.write_text(
            "#!/usr/bin/env bash\n"
            "printf '%s\\n' \"$*\" > \"$HOME/npx.args\"\n"
        )
        npx.chmod(0o755)
        env = self.base_runtime_env(home, fakebin)

        result = subprocess.run(
            [str(ROOT / "bin" / "skills-update")],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("refusing to replace non-symlink ponytail path", result.stderr + result.stdout)
        self.assertFalse((home / "npx.args").exists())
        self.assertTrue(ponytail.is_dir())

    def test_update_wrapper_refuses_unknown_legacy_quarantine_before_npx(self) -> None:
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        home = pathlib.Path(tempdir.name) / "home"
        shared = home / ".agents" / "skills"
        fakebin = pathlib.Path(tempdir.name) / "bin"
        shared.mkdir(parents=True)
        fakebin.mkdir()
        self.populate_imported_skills(shared)
        legacy = shared / "ponytail.upstream-disabled"
        legacy.mkdir()
        (legacy / "SKILL.md").write_text(
            "---\nname: ponytail\ndescription: custom local quarantine\n---\n"
        )
        npx = fakebin / "npx"
        npx.write_text(
            "#!/usr/bin/env bash\n"
            "printf '%s\\n' \"$*\" > \"$HOME/npx.args\"\n"
        )
        npx.chmod(0o755)
        env = self.base_runtime_env(home, fakebin)

        result = subprocess.run(
            [str(ROOT / "bin" / "skills-update")],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unknown legacy ponytail quarantine", result.stderr + result.stdout)
        self.assertFalse((home / "npx.args").exists())
        self.assertTrue(legacy.is_dir())

    def test_bootstrap_refuses_regular_home_skills_lock_before_npx(self) -> None:
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        root = pathlib.Path(tempdir.name)
        home = root / "home"
        fakebin = root / "bin"
        home.mkdir()
        fakebin.mkdir()
        (home / "skills-lock.json").write_text("operator lock\n")
        self.write_fake_git(fakebin, (ROOT / "pstack-revision.txt").read_text().splitlines()[0])
        npx = fakebin / "npx"
        npx.write_text("#!/usr/bin/env bash\nprintf '%s\\n' \"$*\" > \"$HOME/npx.args\"\n")
        npx.chmod(0o755)
        pstack = self.create_fake_pstack_checkout(root)
        env = self.base_runtime_env(home, fakebin, pstack=pstack, private=root / "private")
        env["AGENTS_CFG_DIR"] = str(ROOT)

        result = subprocess.run(
            [str(ROOT / "bootstrap.sh")],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("refusing to replace non-symlink skills lock", result.stderr + result.stdout)
        self.assertEqual((home / "skills-lock.json").read_text(), "operator lock\n")
        self.assertFalse((home / "npx.args").exists())

    def test_bootstrap_reaches_pull_for_checkout_without_metadata_script(self) -> None:
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        root = pathlib.Path(tempdir.name)
        home = root / "home"
        checkout = root / "agents-cfg"
        fakebin = root / "bin"
        home.mkdir()
        (checkout / ".git").mkdir(parents=True)
        fakebin.mkdir()
        shutil.copy(ROOT / "skills-lock.json", checkout / "skills-lock.json")
        git = fakebin / "git"
        git.write_text(
            "#!/usr/bin/env bash\n"
            "printf '%s\\n' \"$*\" >> \"$HOME/git.args\"\n"
            "exit 73\n"
        )
        git.chmod(0o755)
        env = self.base_runtime_env(home, fakebin)
        env["AGENTS_CFG_DIR"] = str(checkout)

        result = subprocess.run(
            [str(ROOT / "bootstrap.sh")],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 73, result.stderr + result.stdout)
        self.assertIn(
            "-C " + str(checkout) + " pull --ff-only",
            (home / "git.args").read_text(),
        )
        self.assertNotIn("skill_metadata.py", result.stderr + result.stdout)

    def test_bootstrap_requires_npx_before_shared_mutation(self) -> None:
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        root = pathlib.Path(tempdir.name)
        home = root / "home"
        fakebin = root / "bin"
        home.mkdir()
        fakebin.mkdir()
        (fakebin / "git").symlink_to("/usr/bin/git")
        (fakebin / "python3").symlink_to("/usr/bin/python3")
        (fakebin / "uname").symlink_to("/usr/bin/uname")
        env = os.environ.copy()
        env["HOME"] = str(home)
        env["PATH"] = str(fakebin)

        result = subprocess.run(
            ["/bin/bash", str(ROOT / "bootstrap.sh")],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing prerequisite: npx", result.stderr + result.stdout)
        self.assertFalse((home / "git.args").exists())

    def test_bootstrap_refuses_custom_home_skills_lock_symlink_before_shared_mutation(self) -> None:
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        root = pathlib.Path(tempdir.name)
        home = root / "home"
        fakebin = root / "bin"
        home.mkdir()
        fakebin.mkdir()
        custom_lock = root / "custom-lock.json"
        custom_lock.write_text("operator symlink lock\n")
        (home / "skills-lock.json").symlink_to(custom_lock)
        self.write_fake_git(fakebin, (ROOT / "pstack-revision.txt").read_text().splitlines()[0])
        npx = fakebin / "npx"
        npx.write_text("#!/usr/bin/env bash\nprintf '%s\\n' \"$*\" > \"$HOME/npx.args\"\n")
        npx.chmod(0o755)
        pstack = self.create_fake_pstack_checkout(root)
        env = self.base_runtime_env(home, fakebin, pstack=pstack, private=root / "private")
        env["AGENTS_CFG_DIR"] = str(ROOT)

        result = subprocess.run(
            [str(ROOT / "bootstrap.sh")],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("refusing to retarget skills lock symlink", result.stderr + result.stdout)
        self.assertEqual(
            skill_metadata.symlink_target(home / "skills-lock.json").resolve(),
            custom_lock.resolve(),
        )
        git_args = (
            (home / "git.args").read_text().splitlines()
            if (home / "git.args").exists()
            else []
        )
        self.assertFalse(
            any(
                re.search(r"(?:^| )(?:pull|fetch|checkout)(?: |$)", command)
                for command in git_args
            ),
            git_args,
        )
        self.assertFalse((home / "npx.args").exists())

    def test_bootstrap_uses_shared_install_preflight_before_npx(self) -> None:
        text = (ROOT / "bootstrap.sh").read_text()

        self.assertLess(text.index("preflight_skills_lock"), text.index("pull --ff-only"))
        self.assertLess(text.index("preflight-install"), text.index("npx --yes"))

    def test_bootstrap_runs_operator_state_preflight_before_pstack_mutation(self) -> None:
        text = (ROOT / "bootstrap.sh").read_text()

        self.assertLess(text.index("preflight_skills_lock"), text.index("pull --ff-only"))
        self.assertIn(
            '  preflight_operator_state\n'
            '  echo "== fetching pinned pstack revision"\n'
            '  git -C "$PSTACK_DIR" fetch origin "$PSTACK_REVISION"',
            text,
        )
        self.assertIn(
            '  preflight_operator_state\n'
            '  echo "== cloning pstack into $PSTACK_DIR"\n'
            '  mkdir -p "$(dirname "$PSTACK_DIR")"',
            text,
        )
        self.assertIn(
            'fi\n'
            'preflight_operator_state\n'
            'git -C "$PSTACK_DIR" checkout --detach "$PSTACK_REVISION"',
            text,
        )

    def test_bootstrap_refuses_private_ponytail_before_npx(self) -> None:
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        root = pathlib.Path(tempdir.name)
        home = root / "home"
        shared = home / ".agents" / "skills"
        fakebin = root / "bin"
        private = root / "private"
        private_ponytail = private / "skills" / "ponytail"
        home.mkdir()
        shared.mkdir(parents=True)
        fakebin.mkdir()
        private_ponytail.mkdir(parents=True)
        (private_ponytail / "SKILL.md").write_text(
            "---\nname: ponytail\ndescription: private ponytail\n---\n"
        )
        pstack = self.create_fake_pstack_checkout(root)
        self.write_fake_git(fakebin, (ROOT / "pstack-revision.txt").read_text().splitlines()[0])
        npx = fakebin / "npx"
        npx.write_text("#!/usr/bin/env bash\nprintf '%s\\n' \"$*\" > \"$HOME/npx.args\"\n")
        npx.chmod(0o755)
        env = self.base_runtime_env(home, fakebin, pstack=pstack, private=private)
        env["AGENTS_CFG_DIR"] = str(ROOT)

        result = subprocess.run(
            [str(ROOT / "bootstrap.sh")],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("refusing private ponytail override", result.stderr + result.stdout)
        self.assertFalse((home / "npx.args").exists())

    def test_bootstrap_refuses_unknown_active_ponytail_before_npx(self) -> None:
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        root = pathlib.Path(tempdir.name)
        home = root / "home"
        shared = home / ".agents" / "skills"
        fakebin = root / "bin"
        home.mkdir()
        shared.mkdir(parents=True)
        fakebin.mkdir()
        ponytail = shared / "ponytail"
        ponytail.mkdir()
        (ponytail / "SKILL.md").write_text(
            "---\nname: ponytail\ndescription: custom active ponytail\n---\n"
        )
        pstack = self.create_fake_pstack_checkout(root)
        self.write_fake_git(fakebin, (ROOT / "pstack-revision.txt").read_text().splitlines()[0])
        npx = fakebin / "npx"
        npx.write_text("#!/usr/bin/env bash\nprintf '%s\\n' \"$*\" > \"$HOME/npx.args\"\n")
        npx.chmod(0o755)
        env = self.base_runtime_env(home, fakebin, pstack=pstack)
        env["AGENTS_CFG_DIR"] = str(ROOT)

        result = subprocess.run(
            [str(ROOT / "bootstrap.sh")],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("refusing to replace non-symlink ponytail path", result.stderr + result.stdout)
        self.assertFalse((home / "npx.args").exists())

    def test_bootstrap_refuses_unknown_legacy_quarantine_before_npx(self) -> None:
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        root = pathlib.Path(tempdir.name)
        home = root / "home"
        shared = home / ".agents" / "skills"
        fakebin = root / "bin"
        home.mkdir()
        shared.mkdir(parents=True)
        fakebin.mkdir()
        legacy = shared / "ponytail.upstream-disabled"
        legacy.mkdir()
        (legacy / "SKILL.md").write_text(
            "---\nname: ponytail\ndescription: unknown legacy quarantine\n---\n"
        )
        pstack = self.create_fake_pstack_checkout(root)
        self.write_fake_git(fakebin, (ROOT / "pstack-revision.txt").read_text().splitlines()[0])
        npx = fakebin / "npx"
        npx.write_text("#!/usr/bin/env bash\nprintf '%s\\n' \"$*\" > \"$HOME/npx.args\"\n")
        npx.chmod(0o755)
        env = self.base_runtime_env(home, fakebin, pstack=pstack)
        env["AGENTS_CFG_DIR"] = str(ROOT)

        result = subprocess.run(
            [str(ROOT / "bootstrap.sh")],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unknown legacy ponytail quarantine", result.stderr + result.stdout)
        self.assertFalse((home / "npx.args").exists())

    def test_bootstrap_restores_metadata_after_failed_npx_and_preserves_npx_rc(self) -> None:
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        root = pathlib.Path(tempdir.name)
        home = root / "home"
        shared = home / ".agents" / "skills"
        fakebin = root / "bin"
        home.mkdir()
        shared.mkdir(parents=True)
        fakebin.mkdir()
        self.populate_imported_skills(shared)
        skill_metadata.apply_overrides(shared)
        pstack = self.create_fake_pstack_checkout(root)
        self.write_fake_git(fakebin, (ROOT / "pstack-revision.txt").read_text().splitlines()[0])
        self.write_partial_failure_npx(fakebin, 24)
        env = self.base_runtime_env(home, fakebin, pstack=pstack)
        env["AGENTS_CFG_DIR"] = str(ROOT)

        result = subprocess.run(
            [str(ROOT / "bootstrap.sh")],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 24, result.stderr + result.stdout)
        self.assertEqual((home / "npx.args").read_text(), "--yes skills@latest experimental_install\n")
        ponytail_review = (shared / "ponytail-review" / "SKILL.md").read_text()
        self.assertIn("Use only when the user explicitly names", ponytail_review)
        wayfinder = (shared / "wayfinder" / "SKILL.md").read_text()
        self.assertNotIn("disable-model-invocation: true", wayfinder)
        self.assertEqual((shared / "ponytail").resolve(), (ROOT / "skills" / "ponytail").resolve())

    def test_install_refuses_regular_home_skills_lock_before_any_shared_state(self) -> None:
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        root = pathlib.Path(tempdir.name)
        home = root / "home"
        fakebin = root / "bin"
        home.mkdir()
        fakebin.mkdir()
        (home / "skills-lock.json").write_text("operator lock\n")
        env = self.base_runtime_env(home, fakebin)

        result = subprocess.run(
            [str(ROOT / "install.sh")],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("refusing to replace non-symlink skills lock", result.stderr + result.stdout)
        self.assertEqual((home / "skills-lock.json").read_text(), "operator lock\n")
        self.assertFalse((home / ".agents").exists())

    def test_install_refuses_custom_home_skills_lock_symlink_before_any_shared_state(self) -> None:
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        root = pathlib.Path(tempdir.name)
        home = root / "home"
        fakebin = root / "bin"
        home.mkdir()
        fakebin.mkdir()
        custom_lock = root / "custom-lock.json"
        custom_lock.write_text("operator symlink lock\n")
        (home / "skills-lock.json").symlink_to(custom_lock)
        env = self.base_runtime_env(home, fakebin)

        result = subprocess.run(
            [str(ROOT / "install.sh")],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("refusing to retarget skills lock symlink", result.stderr + result.stdout)
        self.assertEqual(
            skill_metadata.symlink_target(home / "skills-lock.json").resolve(),
            custom_lock.resolve(),
        )
        self.assertFalse((home / ".agents").exists())

    def test_install_refuses_missing_pstack_before_skill_links(self) -> None:
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        root = pathlib.Path(tempdir.name)
        home = root / "home"
        fakebin = root / "bin"
        home.mkdir()
        fakebin.mkdir()
        env = self.base_runtime_env(home, fakebin)

        result = subprocess.run(
            [str(ROOT / "install.sh")],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("pstack checkout is missing", result.stderr + result.stdout)
        self.assertFalse((home / "skills-lock.json").exists())
        self.assertFalse((home / ".agents").exists())

    def test_install_refuses_private_ponytail_before_shared_links(self) -> None:
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        root = pathlib.Path(tempdir.name)
        home = root / "home"
        shared = home / ".agents" / "skills"
        fakebin = root / "bin"
        private = root / "private"
        private_ponytail = private / "skills" / "ponytail"
        fakebin.mkdir()
        shared.mkdir(parents=True)
        self.populate_imported_skills(shared)
        private_ponytail.mkdir(parents=True)
        (private_ponytail / "SKILL.md").write_text(
            "---\nname: ponytail\ndescription: private ponytail\n---\n"
        )
        pstack = self.create_fake_pstack_checkout(root)
        self.write_fake_git(fakebin, (ROOT / "pstack-revision.txt").read_text().splitlines()[0])
        env = self.base_runtime_env(home, fakebin, pstack=pstack, private=private)

        result = subprocess.run(
            [str(ROOT / "install.sh")],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("refusing private ponytail override", result.stderr + result.stdout)
        self.assertFalse((shared / "ponytail").exists())

    def test_install_succeeds_in_temp_home_with_valid_preflight(self) -> None:
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        root = pathlib.Path(tempdir.name)
        home = root / "home"
        shared = home / ".agents" / "skills"
        fakebin = root / "bin"
        fakebin.mkdir()
        shared.mkdir(parents=True)
        self.populate_imported_skills(shared)
        pstack = self.create_fake_pstack_checkout(root)
        self.write_fake_git(fakebin, (ROOT / "pstack-revision.txt").read_text().splitlines()[0])
        env = self.base_runtime_env(home, fakebin, pstack=pstack)

        result = subprocess.run(
            [str(ROOT / "install.sh")],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual((home / "skills-lock.json").resolve(), (ROOT / "skills-lock.json").resolve())
        self.assertEqual((shared / "ponytail").resolve(), (ROOT / "skills" / "ponytail").resolve())
        self.assertFalse((shared / "ponytail.upstream-disabled").exists())

    def test_install_refuses_unknown_legacy_quarantine_before_linking_repo_wrapper(self) -> None:
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        root = pathlib.Path(tempdir.name)
        home = root / "home"
        shared = home / ".agents" / "skills"
        fakebin = root / "bin"
        fakebin.mkdir()
        shared.mkdir(parents=True)
        legacy = shared / "ponytail.upstream-disabled"
        legacy.mkdir()
        (legacy / "SKILL.md").write_text(
            "---\nname: ponytail\ndescription: custom local quarantine\n---\n"
        )
        pstack = self.create_fake_pstack_checkout(root)
        self.write_fake_git(fakebin, (ROOT / "pstack-revision.txt").read_text().splitlines()[0])
        env = self.base_runtime_env(home, fakebin, pstack=pstack)

        result = subprocess.run(
            [str(ROOT / "install.sh")],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unknown legacy ponytail quarantine", result.stderr + result.stdout)
        self.assertTrue(legacy.is_dir())
        self.assertFalse((shared / "ponytail").exists())
        self.assertFalse((shared / "ponytail").is_symlink())

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

    def test_maintaining_names_canonical_unittest_discovery_command(self) -> None:
        text = (ROOT / "MAINTAINING.md").read_text()

        self.assertIn("python3 -m unittest discover -s tests", text)
        self.assertIn("python3 -m unittest -v", text)


if __name__ == "__main__":
    unittest.main()
