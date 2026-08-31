from __future__ import annotations

import pathlib
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

    def test_check_fails_for_broad_descriptions(self) -> None:
        root = self.create_root()

        self.assertEqual(
            sorted(skill_metadata.check_overrides(root)),
            sorted(FIXTURES),
        )

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


if __name__ == "__main__":
    unittest.main()
