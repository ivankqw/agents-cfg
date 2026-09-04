from __future__ import annotations

import contextlib
import hashlib
import io
import json
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


TEST_SYSTEM_PATH = os.pathsep.join(("/usr/bin", "/bin"))


def hermetic_test_path(fakebin: pathlib.Path) -> str:
    path = os.pathsep.join((str(fakebin), TEST_SYSTEM_PATH))
    for command in ("claude", "codex", "opencode"):
        resolved = shutil.which(command, path=path)
        if resolved is None:
            continue
        if not pathlib.Path(resolved).resolve().is_relative_to(fakebin.resolve()):
            raise RuntimeError(f"test PATH resolves real {command}: {resolved}")
    return path


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

EXPECTED_OVERRIDE_NAMES = (
    "cyclomatic-complexity",
    "ponytail-audit",
    "ponytail-debt",
    "ponytail-gain",
    "ponytail-help",
    "ponytail-review",
)

EXPECTED_INSTALL_STEPS = (
    "preflight",
    "skills",
    "skill-triggers",
    "skill-unlock",
    "agents-hooks",
    "bin",
    "instructions",
    "mcp",
    "codex-settings",
    "validate",
)

EXPECTED_INSTALL_BANNERS = {
    "preflight": ("preflight",),
    "skills": ("preflight", "skills"),
    "skill-triggers": (
        "preflight",
        "constraining explicit-use third-party skill triggers",
    ),
    "skill-unlock": ("preflight", "unlocking skills listed in skills-unlock.txt"),
    "agents-hooks": ("preflight", "agents / hooks"),
    "bin": ("preflight", "bin"),
    "instructions": ("preflight", "instruction files"),
    "mcp": (
        "preflight",
        "mcp servers (keys from env; nothing secret is stored in this repo)",
    ),
    "codex-settings": ("preflight", "Codex settings"),
    "validate": ("preflight", "validating third-party skill catalog"),
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
        catalog = json.loads((ROOT / "skills-catalog.json").read_text())["skills"]
        for name in catalog:
            skill_dir = root / name
            skill_dir.mkdir(parents=True, exist_ok=True)
            (skill_dir / "SKILL.md").write_text(
                f"---\nname: {name}\ndescription: Imported test skill.\n---\n"
            )
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

    def write_herdr_restore_npx(self, fakebin: pathlib.Path) -> None:
        npx = fakebin / "npx"
        npx.write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "printf '%s\\n' \"$*\" > \"$HOME/npx.args\"\n"
            "case \"$FAKE_HERDR_STATE\" in\n"
            "  valid)\n"
            "    mkdir -p \"$HOME/.agents/skills/herdr\"\n"
            "    printf '%s\\n' '---' 'name: herdr' 'description: Herdr.' '---' "
            "> \"$HOME/.agents/skills/herdr/SKILL.md\"\n"
            "    ;;\n"
            "  missing) ;;\n"
            "  decoy)\n"
            "    mkdir -p \"$HOME/.agents/skills/herdr\"\n"
            "    printf '%s\\n' '---' 'name: not-herdr' 'description: Decoy.' '---' "
            "> \"$HOME/decoy-skill.md\"\n"
            "    ln -s \"$HOME/decoy-skill.md\" \"$HOME/.agents/skills/herdr/SKILL.md\"\n"
            "    ;;\n"
            "  *) exit 98 ;;\n"
            "esac\n"
        )
        npx.chmod(0o755)

    def write_fake_mcp_clis(self, fakebin: pathlib.Path) -> None:
        for name in ("claude", "codex"):
            executable = fakebin / name
            executable.write_text(
                "#!/usr/bin/env bash\n"
                "set -euo pipefail\n"
                "if [ \"$1 $2\" = \"mcp get\" ]; then\n"
                "  echo 'server not found' >&2\n"
                "  exit 1\n"
                "fi\n"
                f"printf '%s\\n' \"$*\" >> \"$HOME/{name}-mcp.args\"\n"
            )
            executable.chmod(0o755)

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
        env["PATH"] = hermetic_test_path(fakebin)
        env["PRIVATE_CONFIG"] = str(private or (home.parent / "missing-private"))
        env["PSTACK_DIR"] = str(pstack or (home.parent / "missing-pstack"))
        env["FAKE_PSTACK_REVISION"] = revision
        env["GIT"] = str(fakebin / "git")
        return env

    def create_valid_install_fixture(
        self, root: pathlib.Path, *, home_name: str = "home"
    ) -> tuple[pathlib.Path, dict[str, str]]:
        home = root / home_name
        fakebin = root / "bin"
        home.mkdir()
        fakebin.mkdir(exist_ok=True)
        shared = home / ".agents" / "skills"
        shared.mkdir(parents=True)
        self.populate_imported_skills(shared)
        pstack = (
            self.create_fake_pstack_checkout(root)
            if not (root / "pstack").exists()
            else root / "pstack"
        )
        self.write_fake_git(fakebin, (ROOT / "pstack-revision.txt").read_text().splitlines()[0])
        npx = fakebin / "npx"
        npx.write_text("#!/usr/bin/env bash\nexit 0\n")
        npx.chmod(0o755)
        node = fakebin / "node"
        node.write_text("#!/usr/bin/env bash\nexit 0\n")
        node.chmod(0o755)
        self.write_fake_mcp_clis(fakebin)
        env = self.base_runtime_env(home, fakebin, pstack=pstack)
        env["CONTEXT7_API_KEY"] = "test-token"
        env["EXECUTOR_MCP_URL"] = "https://executor.example/mcp"
        return home, env

    def test_preflight_fails_early_with_all_node_search_locations(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            home = root / "home"
            fakebin = root / "bin"
            home.mkdir()
            fakebin.mkdir()
            for command in ("bash", "dirname", "python3", "uname"):
                source = shutil.which(command, path=TEST_SYSTEM_PATH)
                self.assertIsNotNone(source)
                (fakebin / command).symlink_to(source)
            pstack = self.create_fake_pstack_checkout(root)
            self.write_fake_git(fakebin, (ROOT / "pstack-revision.txt").read_text().strip())
            env = self.base_runtime_env(home, fakebin, pstack=pstack)
            env["PATH"] = str(fakebin)
            env.update(
                NVM_BIN=str(root / "nvm-bin"),
                MISE_DATA_DIR=str(root / "mise"),
                ASDF_DATA_DIR=str(root / "asdf"),
                HOMEBREW_PREFIX=str(root / "brew"),
            )

            result = subprocess.run(
                [str(ROOT / "install.sh"), "preflight"],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            for location in (
                env["PATH"],
                str(root / "nvm-bin" / "node"),
                str(root / "mise" / "installs" / "node" / "*/bin/node"),
                str(root / "asdf" / "installs" / "nodejs" / "*/bin/node"),
                str(root / "brew" / "bin" / "node"),
            ):
                self.assertIn(location, result.stderr)
            self.assertFalse((home / ".claude").exists())

    def test_preflight_names_every_command_disabled_without_bun(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home, env = self.create_valid_install_fixture(pathlib.Path(temp))

            result = subprocess.run(
                [str(ROOT / "install.sh"), "preflight"], cwd=ROOT, env=env,
                text=True, capture_output=True, check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            pstack = pathlib.Path(env["PSTACK_DIR"]).resolve()
            self.assertIn(
                str(pstack / "plugins/pstack/skills/poteto-mode/scripts/watch-pr/watch-pr"),
                result.stdout,
            )
            self.assertIn(
                "bun " + str(pstack / "plugins/pstack/skills/poteto-mode/scripts/orch/orch.ts"),
                result.stdout,
            )

    def test_preflight_requires_a_harness_unless_explicitly_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            _, env = self.create_valid_install_fixture(root)
            for harness in ("claude", "codex"):
                (root / "bin" / harness).unlink()

            rejected = subprocess.run(
                [str(ROOT / "install.sh"), "preflight"], cwd=ROOT, env=env,
                text=True, capture_output=True, check=False,
            )
            allowed = subprocess.run(
                [str(ROOT / "install.sh"), "--no-harness", "preflight"],
                cwd=ROOT, env=env, text=True, capture_output=True, check=False,
            )

            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("claude, codex, or opencode", rejected.stderr)
            self.assertEqual(allowed.returncode, 0, allowed.stderr + allowed.stdout)
            self.assertIn("detected harnesses: none (--no-harness)", allowed.stdout)

    def test_mcp_reports_genuine_registration_errors(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            _, env = self.create_valid_install_fixture(root)
            (root / "bin" / "codex").unlink()
            claude = root / "bin" / "claude"
            claude.write_text(
                "#!/usr/bin/env bash\n"
                "if [ \"$1 $2\" = \"mcp get\" ]; then echo 'server not found' >&2; exit 1; fi\n"
                "echo 'configuration write failed' >&2\n"
                "exit 23\n"
            )

            result = subprocess.run(
                [str(ROOT / "install.sh"), "mcp"], cwd=ROOT, env=env,
                text=True, capture_output=True, check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("error context7 for Claude: configuration write failed", result.stderr)

    def test_install_propagates_explicit_skill_state_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            _, env = self.create_valid_install_fixture(root)
            shared = root / "custom-state" / "skills"
            lock = root / "custom-state" / "lock.json"
            shared.mkdir(parents=True)
            self.populate_imported_skills(shared)
            env["SHARED_SKILLS"] = str(shared)
            env["SKILLS_LOCK_FILE"] = str(lock)

            result = subprocess.run(
                [str(ROOT / "install.sh"), "skills"], cwd=ROOT, env=env,
                text=True, capture_output=True, check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertTrue((shared / "architect").is_symlink())
            self.assertFalse((pathlib.Path(env["HOME"]) / ".agents/skills/architect").is_symlink())

    def test_instruction_step_backs_up_and_refuses_operator_edits(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            home, env = self.create_valid_install_fixture(root)
            claude_file = home / ".claude" / "CLAUDE.md"
            codex_file = home / "AGENTS.md"
            claude_file.parent.mkdir(parents=True)
            claude_file.write_text("operator Claude instructions\n")
            codex_file.write_text("operator Codex instructions\n")

            result = subprocess.run(
                [str(ROOT / "install.sh"), "instructions"], cwd=ROOT, env=env,
                text=True, capture_output=True, check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(claude_file.read_text(), "operator Claude instructions\n")
            self.assertEqual(codex_file.read_text(), "operator Codex instructions\n")
            self.assertEqual(len(tuple(claude_file.parent.glob("CLAUDE.md.impstack-backup.*"))), 1)
            self.assertEqual(len(tuple(home.glob("AGENTS.md.impstack-backup.*"))), 1)
            self.assertIn("--- existing:", result.stdout)
            self.assertIn("use --force", result.stderr)

    def test_instruction_step_is_a_checked_noop_and_force_keeps_backup(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            home, env = self.create_valid_install_fixture(root)
            command = [str(ROOT / "install.sh"), "instructions"]
            first = subprocess.run(command, cwd=ROOT, env=env, text=True, capture_output=True)
            self.assertEqual(first.returncode, 0, first.stderr + first.stdout)
            targets = (home / ".claude/CLAUDE.md", home / "AGENTS.md")
            before = [(path.read_bytes(), path.stat().st_ino, path.stat().st_mtime_ns) for path in targets]
            for path in targets:
                marker, body = path.read_bytes().split(b"\n", 1)
                digest = re.search(rb"sha256=([0-9a-f]{64})", marker)
                self.assertIsNotNone(digest)
                self.assertEqual(digest.group(1).decode(), hashlib.sha256(body).hexdigest())

            second = subprocess.run(command, cwd=ROOT, env=env, text=True, capture_output=True)
            self.assertEqual(second.returncode, 0, second.stderr + second.stdout)
            self.assertEqual(before, [(path.read_bytes(), path.stat().st_ino, path.stat().st_mtime_ns) for path in targets])

            targets[0].write_text("operator replacement\n")
            forced = subprocess.run(
                [str(ROOT / "install.sh"), "--force", "instructions"],
                cwd=ROOT, env=env, text=True, capture_output=True,
            )
            self.assertEqual(forced.returncode, 0, forced.stderr + forced.stdout)
            self.assertEqual(len(tuple(targets[0].parent.glob("CLAUDE.md.impstack-backup.*"))), 1)
            for index in range(6):
                targets[0].write_text(f"operator replacement {index}\n")
                forced = subprocess.run(
                    [str(ROOT / "install.sh"), "--force", "instructions"],
                    cwd=ROOT, env=env, text=True, capture_output=True,
                )
                self.assertEqual(forced.returncode, 0, forced.stderr + forced.stdout)
            self.assertEqual(len(tuple(targets[0].parent.glob("CLAUDE.md.impstack-backup.*"))), 5)

    @staticmethod
    def normalize_home(value: str | bytes, home: pathlib.Path) -> str | bytes:
        if isinstance(value, bytes):
            return value.replace(os.fsencode(str(home)), b"<HOME>")
        return value.replace(str(home), "<HOME>")

    def snapshot_home(
        self, home: pathlib.Path
    ) -> dict[str, tuple[str, str | bytes | int]]:
        snapshot: dict[str, tuple[str, str | bytes | int]] = {
            ".": ("directory", "")
        }

        def visit(directory: pathlib.Path) -> None:
            with os.scandir(directory) as entries:
                for entry in entries:
                    path = pathlib.Path(entry.path)
                    relative = path.relative_to(home).as_posix()
                    if entry.is_symlink():
                        snapshot[relative] = (
                            "symlink",
                            self.normalize_home(os.readlink(path), home),
                        )
                    elif entry.is_dir(follow_symlinks=False):
                        snapshot[relative] = ("directory", "")
                        visit(path)
                    elif entry.is_file(follow_symlinks=False):
                        snapshot[relative] = ("file", path.read_bytes())
                    else:
                        snapshot[relative] = (
                            "other",
                            entry.stat(follow_symlinks=False).st_mode,
                        )

        visit(home)
        return snapshot

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

    def test_update_wrapper_reapplies_and_checks_metadata_after_npx_update(self) -> None:
        wrapper = ROOT / "bin" / "skills-update"

        text = wrapper.read_text()

        self.assertIn('"$NPX" --yes skills update -g', text)
        self.assertLess(text.index('skill_metadata.py" apply'), text.index('skill_metadata.py" check'))
        self.assertLess(text.index('"$NPX" --yes skills update -g'), text.index("restore_metadata )"))

    def test_update_wrapper_restores_unlocks_after_fake_npx_update(self) -> None:
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        home = pathlib.Path(tempdir.name) / "home"
        shared = home / ".agents" / "skills"
        fakebin = pathlib.Path(tempdir.name) / "bin"
        shared.mkdir(parents=True)
        fakebin.mkdir()
        self.populate_imported_skills(shared)
        skill_metadata.apply_overrides(shared)

        npx = fakebin / "npx"
        npx.write_text(
            textwrap.dedent(
                """\
                #!/usr/bin/env bash
                set -euo pipefail
                printf '%s\n' "$*" > "$HOME/npx.args"
                [ "$1" = "--yes" ]
                [ "$2" = "skills" ]
                [ "$3" = "update" ]
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
        env["PATH"] = hermetic_test_path(fakebin)

        result = subprocess.run(
            [str(ROOT / "bin" / "skills-update")],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual((home / "npx.args").read_text(), "--yes skills update -g\n")
        wayfinder = (shared / "wayfinder" / "SKILL.md").read_text()
        self.assertNotIn("disable-model-invocation: true", wayfinder)
        self.assertIn("name: wayfinder", wayfinder)

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
        self.assertEqual((home / "npx.args").read_text(), "--yes skills update -g\n")
        ponytail_review = (shared / "ponytail-review" / "SKILL.md").read_text()
        self.assertIn("Use only when the user explicitly names", ponytail_review)
        wayfinder = (shared / "wayfinder" / "SKILL.md").read_text()
        self.assertNotIn("disable-model-invocation: true", wayfinder)

    def test_bootstrap_leaves_regular_home_skills_lock_unchanged(self) -> None:
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        root = pathlib.Path(tempdir.name)
        home = root / "home"
        fakebin = root / "bin"
        home.mkdir()
        fakebin.mkdir()
        (home / "skills-lock.json").write_text("operator lock\n")
        shared = home / ".agents" / "skills"
        shared.mkdir(parents=True)
        self.populate_imported_skills(shared)
        self.write_fake_git(fakebin, (ROOT / "pstack-revision.txt").read_text().splitlines()[0])
        npx = fakebin / "npx"
        npx.write_text("#!/usr/bin/env bash\nprintf '%s\\n' \"$*\" > \"$HOME/npx.args\"\n")
        npx.chmod(0o755)
        pstack = self.create_fake_pstack_checkout(root)
        env = self.base_runtime_env(home, fakebin, pstack=pstack, private=root / "private")
        env["IMPSTACK_DIR"] = str(ROOT)

        result = subprocess.run(
            [str(ROOT / "bootstrap.sh"), "--no-harness"],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual((home / "skills-lock.json").read_text(), "operator lock\n")
        self.assertFalse((home / "npx.args").exists())

    def test_bootstrap_reaches_pull_for_checkout_without_metadata_script(self) -> None:
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        root = pathlib.Path(tempdir.name)
        home = root / "home"
        checkout = root / "impstack"
        fakebin = root / "bin"
        home.mkdir()
        (checkout / ".git").mkdir(parents=True)
        fakebin.mkdir()
        git = fakebin / "git"
        git.write_text(
            "#!/usr/bin/env bash\n"
            "printf '%s\\n' \"$*\" >> \"$HOME/git.args\"\n"
            "exit 73\n"
        )
        git.chmod(0o755)
        env = self.base_runtime_env(home, fakebin)
        env["IMPSTACK_DIR"] = str(checkout)

        result = subprocess.run(
            [str(ROOT / "bootstrap.sh"), "--no-harness"],
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

    def test_bootstrap_delegates_npx_resolution_to_skills_sync(self) -> None:
        text = (ROOT / "bootstrap.sh").read_text()

        self.assertIn('for c in git python3; do', text)
        self.assertNotIn('for c in git python3 npx; do', text)

    def test_bootstrap_leaves_custom_home_skills_lock_symlink_unchanged(self) -> None:
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
        shared = home / ".agents" / "skills"
        shared.mkdir(parents=True)
        self.populate_imported_skills(shared)
        self.write_fake_git(fakebin, (ROOT / "pstack-revision.txt").read_text().splitlines()[0])
        npx = fakebin / "npx"
        npx.write_text("#!/usr/bin/env bash\nprintf '%s\\n' \"$*\" > \"$HOME/npx.args\"\n")
        npx.chmod(0o755)
        pstack = self.create_fake_pstack_checkout(root)
        env = self.base_runtime_env(home, fakebin, pstack=pstack, private=root / "private")
        env["IMPSTACK_DIR"] = str(ROOT)

        result = subprocess.run(
            [str(ROOT / "bootstrap.sh"), "--no-harness"],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual(
            skill_metadata.symlink_target(home / "skills-lock.json").resolve(),
            custom_lock.resolve(),
        )
        git_args = (
            (home / "git.args").read_text().splitlines()
            if (home / "git.args").exists()
            else []
        )
        self.assertTrue(any(" pull --ff-only" in command for command in git_args), git_args)
        self.assertFalse((home / "npx.args").exists())

    def test_bootstrap_uses_shared_install_preflight_before_npx(self) -> None:
        text = (ROOT / "bootstrap.sh").read_text()

        self.assertLess(text.index("preflight-pstack"), text.index('"$DEST/install.sh"'))

    def test_bootstrap_requires_restored_herdr_skill(self) -> None:
        for state, expected_rc in (("valid", 0), ("missing", 1), ("decoy", 1)):
            with self.subTest(state=state), tempfile.TemporaryDirectory() as temp:
                root = pathlib.Path(temp)
                home = root / "home"
                shared = home / ".agents" / "skills"
                fakebin = root / "bin"
                shared.mkdir(parents=True)
                fakebin.mkdir()
                self.populate_imported_skills(shared)
                skill_metadata.apply_overrides(shared)
                shutil.rmtree(shared / "herdr")
                pstack = self.create_fake_pstack_checkout(root)
                self.write_fake_git(
                    fakebin,
                    (ROOT / "pstack-revision.txt").read_text().splitlines()[0],
                )
                self.write_herdr_restore_npx(fakebin)
                self.write_fake_mcp_clis(fakebin)
                env = self.base_runtime_env(home, fakebin, pstack=pstack)
                env["IMPSTACK_DIR"] = str(ROOT)
                env["FAKE_HERDR_STATE"] = state
                env["CONTEXT7_API_KEY"] = "test-token"
                env["EXECUTOR_MCP_URL"] = "https://executor.example/mcp"

                result = subprocess.run(
                    [str(ROOT / "bootstrap.sh")],
                    cwd=ROOT,
                    env=env,
                    text=True,
                    capture_output=True,
                    check=False,
                )

                output = result.stderr + result.stdout
                self.assertEqual(
                    (home / "claude-mcp.args").read_text(),
                    "mcp add --scope user --transport http context7 https://mcp.context7.com/mcp "
                    "--header CONTEXT7_API_KEY: test-token\n"
                    "mcp add --scope user --transport http exa https://mcp.exa.ai/mcp\n"
                    "mcp add --scope user --transport http linear-server https://mcp.linear.app/mcp\n"
                    "mcp add --scope user --transport http executor https://executor.example/mcp\n",
                )
                self.assertEqual(
                    (home / "codex-mcp.args").read_text(),
                    "mcp add exa --url https://mcp.exa.ai/mcp\n"
                    "mcp add linear-server --url https://mcp.linear.app/mcp\n"
                    "mcp add executor --url https://executor.example/mcp\n",
                )
                self.assertEqual(result.returncode, expected_rc, output)
                if state == "missing":
                    self.assertIn("missing catalog skill: herdr", output)
                elif expected_rc:
                    self.assertIn("Herdr restore failed", output)
                else:
                    self.assertIn("== done", output)

        catalog = json.loads((ROOT / "skills-catalog.json").read_text())
        self.assertEqual(catalog["skills"]["herdr"]["source"], "herdrdev/herdr")

    def test_bootstrap_uses_install_for_catalog_restore(self) -> None:
        text = (ROOT / "bootstrap.sh").read_text()

        self.assertIn('"$DEST/install.sh"', text)
        self.assertNotIn("experimental_install", text)

    def test_install_leaves_regular_home_skills_lock_unchanged(self) -> None:
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        root = pathlib.Path(tempdir.name)
        home = root / "home"
        fakebin = root / "bin"
        home.mkdir()
        fakebin.mkdir()
        (home / "skills-lock.json").write_text("operator lock\n")
        shared = home / ".agents" / "skills"
        shared.mkdir(parents=True)
        self.populate_imported_skills(shared)
        pstack = self.create_fake_pstack_checkout(root)
        self.write_fake_git(fakebin, (ROOT / "pstack-revision.txt").read_text().splitlines()[0])
        npx = fakebin / "npx"
        npx.write_text("#!/usr/bin/env bash\nexit 0\n")
        npx.chmod(0o755)
        env = self.base_runtime_env(home, fakebin, pstack=pstack)

        result = subprocess.run(
            [str(ROOT / "install.sh"), "--no-harness"],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual((home / "skills-lock.json").read_text(), "operator lock\n")

    def test_install_leaves_custom_home_skills_lock_symlink_unchanged(self) -> None:
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
        shared = home / ".agents" / "skills"
        shared.mkdir(parents=True)
        self.populate_imported_skills(shared)
        pstack = self.create_fake_pstack_checkout(root)
        self.write_fake_git(fakebin, (ROOT / "pstack-revision.txt").read_text().splitlines()[0])
        npx = fakebin / "npx"
        npx.write_text("#!/usr/bin/env bash\nexit 0\n")
        npx.chmod(0o755)
        env = self.base_runtime_env(home, fakebin, pstack=pstack)

        result = subprocess.run(
            [str(ROOT / "install.sh"), "--no-harness"],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual(
            skill_metadata.symlink_target(home / "skills-lock.json").resolve(),
            custom_lock.resolve(),
        )

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
            [str(ROOT / "install.sh"), "--no-harness"],
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
        npx = fakebin / "npx"
        npx.write_text("#!/usr/bin/env bash\nexit 0\n")
        npx.chmod(0o755)
        self.write_fake_mcp_clis(fakebin)
        env = self.base_runtime_env(home, fakebin, pstack=pstack)
        env["CONTEXT7_API_KEY"] = "test-token"
        env["EXECUTOR_MCP_URL"] = "https://executor.example/mcp"

        result = subprocess.run(
            [str(ROOT / "install.sh")],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertFalse((home / "skills-lock.json").exists())
        claude_args = (home / "claude-mcp.args").read_text()
        self.assertIn(
            "mcp add --scope user --transport http context7 https://mcp.context7.com/mcp "
            "--header CONTEXT7_API_KEY: test-token",
            claude_args,
        )
        self.assertIn(
            "mcp add --scope user --transport http executor https://executor.example/mcp",
            claude_args,
        )
        codex_args = (home / "codex-mcp.args").read_text()
        self.assertIn("mcp add exa --url https://mcp.exa.ai/mcp", codex_args)
        self.assertIn(
            "mcp add executor --url https://executor.example/mcp",
            codex_args,
        )
        self.assertNotIn("context7", codex_args)
        self.assertIn(
            "unsupported context7 for Codex: header CONTEXT7_API_KEY is not bearer auth",
            result.stdout,
        )

    def test_install_matches_original_in_distinct_isolated_homes(self) -> None:
        original_bytes = subprocess.run(
            ["git", "show", "origin/main:install.sh"],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        ).stdout
        with tempfile.NamedTemporaryFile(
            dir=ROOT, prefix=".install-original-", suffix=".sh", delete=False
        ) as original_file:
            original_path = pathlib.Path(original_file.name)
            original_file.write(original_bytes)
        self.addCleanup(original_path.unlink, missing_ok=True)
        original_path.chmod(0o755)

        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            original_home, original_env = self.create_valid_install_fixture(
                root, home_name="original-home"
            )
            new_home, new_env = self.create_valid_install_fixture(
                root, home_name="new-home"
            )

            original_result = subprocess.run(
                [str(original_path)],
                cwd=ROOT,
                env=original_env,
                text=False,
                capture_output=True,
                check=False,
            )
            new_result = subprocess.run(
                [str(ROOT / "install.sh")],
                cwd=ROOT,
                env=new_env,
                text=False,
                capture_output=True,
                check=False,
            )

            self.assertEqual(original_result.returncode, 0, original_result.stderr)
            self.assertEqual(new_result.returncode, 0, new_result.stderr)
            self.assertEqual(
                self.normalize_home(original_result.stderr, original_home),
                self.normalize_home(new_result.stderr, new_home),
            )
            original_snapshot = self.snapshot_home(original_home)
            new_snapshot = self.snapshot_home(new_home)
            managed = {".claude/CLAUDE.md", "AGENTS.md"}
            self.assertEqual(
                {key: value for key, value in original_snapshot.items() if key not in managed},
                {key: value for key, value in new_snapshot.items() if key not in managed},
            )
            original_claude = original_snapshot[".claude/CLAUDE.md"][1]
            new_claude = new_snapshot[".claude/CLAUDE.md"][1]
            self.assertEqual(new_claude.split(b"\n", 1)[1], original_claude)
            original_codex = original_snapshot["AGENTS.md"][1]
            new_codex = new_snapshot["AGENTS.md"][1]
            self.assertEqual(new_codex.split(b"\n", 1)[1], original_codex.split(b"\n\n", 1)[1])

    def test_install_lists_exact_step_names(self) -> None:
        result = subprocess.run(
            [str(ROOT / "install.sh"), "--list"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual(result.stderr, "")
        self.assertEqual(tuple(result.stdout.splitlines()), EXPECTED_INSTALL_STEPS)

    def test_install_help_says_named_steps_run_preflight_first(self) -> None:
        result = subprocess.run(
            [str(ROOT / "install.sh"), "--help"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("A single step always runs preflight first.", result.stdout)

    def test_each_install_step_runs_alone_in_a_fresh_home(self) -> None:
        for step in EXPECTED_INSTALL_STEPS:
            with self.subTest(step=step), tempfile.TemporaryDirectory() as temp:
                root = pathlib.Path(temp)
                _, env = self.create_valid_install_fixture(root)
                result = subprocess.run(
                    [str(ROOT / "install.sh"), step],
                    cwd=ROOT,
                    env=env,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
                self.assertEqual(
                    tuple(
                        line[3:]
                        for line in result.stdout.splitlines()
                        if line.startswith("== ")
                    ),
                    EXPECTED_INSTALL_BANNERS[step],
                )

    def test_install_skill_unlock_fails_when_every_requested_skill_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            home, env = self.create_valid_install_fixture(root)
            unlock_names = tuple(
                line
                for line in (ROOT / "skills-unlock.txt").read_text().splitlines()
                if line and not line.startswith("#")
            )
            for name in unlock_names:
                shutil.rmtree(home / ".agents" / "skills" / name)

            result = subprocess.run(
                [str(ROOT / "install.sh"), "skill-unlock"],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("run the skills step first", result.stderr + result.stdout)

    def test_install_skill_unlock_warns_when_some_requested_skills_are_missing(self) -> None:
        for missing_names in (
            ("wayfinder",),
            ("wayfinder", "grill-with-docs"),
        ):
            with self.subTest(missing_names=missing_names):
                with tempfile.TemporaryDirectory() as temp:
                    root = pathlib.Path(temp)
                    home, env = self.create_valid_install_fixture(root)
                    for name in missing_names:
                        shutil.rmtree(home / ".agents" / "skills" / name)

                    result = subprocess.run(
                        [str(ROOT / "install.sh"), "skill-unlock"],
                        cwd=ROOT,
                        env=env,
                        text=True,
                        capture_output=True,
                        check=False,
                    )

                    self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
                    for name in missing_names:
                        self.assertIn(f"skip {name}: not installed", result.stdout)

    def test_install_rejects_unknown_step_and_prints_valid_names(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            _, env = self.create_valid_install_fixture(root)
            result = subprocess.run(
                [str(ROOT / "install.sh"), "not-a-real-step"],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            output = result.stderr + result.stdout
            for step in EXPECTED_INSTALL_STEPS:
                self.assertIn(step, output)

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
