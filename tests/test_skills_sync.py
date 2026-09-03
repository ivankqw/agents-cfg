from __future__ import annotations

import json
import os
import pathlib
import shlex
import shutil
import subprocess
import tempfile
import textwrap
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "skills-sync"


class SkillsSyncTests(unittest.TestCase):
    def make_home(self) -> tuple[tempfile.TemporaryDirectory[str], pathlib.Path]:
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        home = pathlib.Path(tempdir.name) / "home"
        home.mkdir()
        return tempdir, home

    def write_lock(
        self, home: pathlib.Path, skills: dict[str, dict[str, object]]
    ) -> pathlib.Path:
        lock = home / ".agents" / ".skill-lock.json"
        lock.parent.mkdir(parents=True)
        lock.write_text(
            json.dumps(
                {
                    "version": 3,
                    "skills": skills,
                    "dismissed": ["machine-state"],
                    "lastSelectedAgents": ["codex"],
                }
            )
        )
        return lock

    def write_catalog(
        self, repo: pathlib.Path, skills: dict[str, dict[str, str]]
    ) -> pathlib.Path:
        catalog = repo / "skills-catalog.json"
        catalog.write_text(json.dumps({"skills": skills}, indent=2) + "\n")
        return catalog

    def run_cli(
        self,
        repo: pathlib.Path,
        home: pathlib.Path,
        *args: str,
        path: str | None = None,
        env_overrides: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["HOME"] = str(home)
        env["AGENTS_CFG_DIR"] = str(repo)
        env["SHARED_SKILLS"] = str(home / ".agents" / "skills")
        if path is not None:
            env["PATH"] = path
            for name in (
                "NVM_BIN",
                "MISE_DATA_DIR",
                "ASDF_DATA_DIR",
                "HOMEBREW_PREFIX",
            ):
                env.pop(name, None)
        if env_overrides:
            env.update(env_overrides)
        return subprocess.run(
            ["/usr/bin/python3", str(SCRIPT), *args],
            cwd=repo,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    def create_skill(self, home: pathlib.Path, name: str) -> None:
        skill = home / ".agents" / "skills" / name
        skill.mkdir(parents=True, exist_ok=True)
        (skill / "SKILL.md").write_text(f"---\nname: {name}\ndescription: test\n---\n")

    def test_normalize_is_deterministic_and_strips_volatile_fields(self) -> None:
        _, home = self.make_home()
        repo = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(lambda: shutil.rmtree(repo))
        self.write_lock(
            home,
            {
                "zeta": {
                    "updatedAt": "tomorrow",
                    "sourceUrl": "https://example.test/zeta.git",
                    "source": "example/zeta",
                    "computedHash": "machine-two",
                    "sourceType": "github",
                    "skillPath": "skills/zeta/SKILL.md",
                },
                "alpha": {
                    "installedAt": "yesterday",
                    "skillFolderHash": "machine-one",
                    "skillPath": "SKILL.md",
                    "sourceType": "github",
                    "source": "example/alpha",
                    "sourceUrl": "https://example.test/alpha.git",
                },
            },
        )

        first = self.run_cli(repo, home, "normalize")
        first_bytes = (repo / "skills-catalog.json").read_bytes()
        second = self.run_cli(repo, home, "normalize")

        self.assertEqual(first.returncode, 0, first.stderr + first.stdout)
        self.assertEqual(second.returncode, 0, second.stderr + second.stdout)
        self.assertEqual(first_bytes, (repo / "skills-catalog.json").read_bytes())
        self.assertEqual(
            (repo / "skills-catalog.json").read_text(),
            textwrap.dedent(
                """\
                {
                  "skills": {
                    "alpha": {
                      "source": "example/alpha",
                      "sourceType": "github",
                      "sourceUrl": "https://example.test/alpha.git",
                      "skillPath": "SKILL.md"
                    },
                    "zeta": {
                      "source": "example/zeta",
                      "sourceType": "github",
                      "sourceUrl": "https://example.test/zeta.git",
                      "skillPath": "skills/zeta/SKILL.md"
                    }
                  }
                }
                """
            ),
        )

    def test_check_detects_missing_catalog_folder(self) -> None:
        _, home = self.make_home()
        repo = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(lambda: shutil.rmtree(repo))
        self.write_catalog(
            repo,
            {
                "missing": {
                    "source": "example/skills",
                    "sourceType": "github",
                    "sourceUrl": "https://example.test/skills.git",
                    "skillPath": "skills/missing/SKILL.md",
                }
            },
        )
        (home / ".agents" / "skills").mkdir(parents=True)

        result = self.run_cli(repo, home, "check")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing catalog skill: missing", result.stdout)

    def test_check_detects_extra_installer_managed_folder(self) -> None:
        _, home = self.make_home()
        repo = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(lambda: shutil.rmtree(repo))
        self.write_catalog(repo, {})
        self.create_skill(home, "extra")

        result = self.run_cli(repo, home, "check")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("uncatalogued installed skill: extra", result.stdout)

    def test_check_exits_nonzero_for_broken_catalog(self) -> None:
        _, home = self.make_home()
        repo = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(lambda: shutil.rmtree(repo))
        (repo / "skills-catalog.json").write_text('{"skills": {"broken": {}}}\n')
        (home / ".agents" / "skills").mkdir(parents=True)

        result = self.run_cli(repo, home, "check")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("broken catalog entry: broken", result.stderr)

    def test_run_is_idempotent_on_second_pass(self) -> None:
        _, home = self.make_home()
        repo = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(lambda: shutil.rmtree(repo))
        fakebin = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(lambda: shutil.rmtree(fakebin))
        self.write_catalog(repo, {})
        self.write_lock(
            home,
            {
                "alpha": {
                    "source": "example/alpha",
                    "sourceType": "github",
                    "sourceUrl": "https://example.test/alpha.git",
                    "skillPath": "SKILL.md",
                }
            },
        )
        self.create_skill(home, "alpha")
        (repo / "bin").mkdir()
        update = repo / "bin" / "skills-update"
        update.write_text(
            '#!/usr/bin/env bash\nset -euo pipefail\nprintf \'update %s\\n\' "$*" >> "$HOME/actions"\n'
        )
        update.chmod(0o755)
        git = fakebin / "git"
        git.write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            'printf \'git %s\\n\' "$*" >> "$HOME/actions"\n'
        )
        git.chmod(0o755)
        npx = fakebin / "npx"
        npx.write_text("#!/usr/bin/env bash\nexit 0\n")
        npx.chmod(0o755)
        path = f"{fakebin}:/usr/bin:/bin"

        first = self.run_cli(repo, home, "run", "--no-update", "--no-push", path=path)
        second = self.run_cli(repo, home, "run", "--no-update", "--no-push", path=path)

        self.assertEqual(first.returncode, 0, first.stderr + first.stdout)
        self.assertEqual(second.returncode, 0, second.stderr + second.stdout)
        actions = (home / "actions").read_text().splitlines()
        self.assertEqual(sum(" commit " in f" {line} " for line in actions), 1)
        self.assertIn("catalog unchanged", second.stdout)

    def test_install_missing_uses_catalog_source(self) -> None:
        _, home = self.make_home()
        repo = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(lambda: shutil.rmtree(repo))
        fakebin = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(lambda: shutil.rmtree(fakebin))
        self.write_catalog(
            repo,
            {
                "alpha": {
                    "source": "example/alpha",
                    "sourceType": "github",
                    "sourceUrl": "https://example.test/alpha.git",
                    "skillPath": "SKILL.md",
                }
            },
        )
        npx = fakebin / "npx"
        npx.write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            'printf \'%s\\n\' "$*" > "$HOME/npx.args"\n'
            'mkdir -p "$HOME/.agents/skills/alpha"\n'
            "printf '%s\\n' '---' 'name: alpha' 'description: test' '---' "
            '> "$HOME/.agents/skills/alpha/SKILL.md"\n'
        )
        npx.chmod(0o755)

        result = self.run_cli(
            repo,
            home,
            "install-missing",
            path=f"{fakebin}:/usr/bin:/bin",
        )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual(
            (home / "npx.args").read_text(), "skills add example/alpha -g -y\n"
        )
        self.assertTrue((home / ".agents" / "skills" / "alpha" / "SKILL.md").is_file())

    def test_node_resolution_uses_documented_fallback_order(self) -> None:
        _, home = self.make_home()
        repo = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(lambda: shutil.rmtree(repo))
        path_bin = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(lambda: shutil.rmtree(path_bin))
        nvm_bin = home / "custom-nvm" / "bin" / "npx"
        nvm = home / ".nvm" / "versions" / "node" / "v24" / "bin" / "npx"
        mise = (
            home
            / ".local"
            / "share"
            / "mise"
            / "installs"
            / "node"
            / "23"
            / "bin"
            / "npx"
        )
        asdf = home / ".asdf" / "installs" / "nodejs" / "22" / "bin" / "npx"
        bun = home / ".bun" / "bin" / "npx"
        brew = home / "homebrew" / "bin" / "npx"
        path_npx = path_bin / "npx"
        candidates = (path_npx, nvm_bin, nvm, mise, asdf, bun, brew)
        for candidate in candidates:
            candidate.parent.mkdir(parents=True, exist_ok=True)
            candidate.write_text("#!/bin/sh\n")
            candidate.chmod(0o755)

        overrides = {
            "NVM_BIN": str(nvm_bin.parent),
            "HOMEBREW_PREFIX": str(brew.parent.parent),
        }
        for index, expected in enumerate(candidates):
            with self.subTest(expected=expected):
                result = self.run_cli(
                    repo,
                    home,
                    "schedule",
                    path=str(path_bin),
                    env_overrides=overrides,
                )
                self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
                cron = result.stdout.splitlines()[-1]
                scheduled_path = shlex.split(cron)[5].removeprefix("PATH=")
                self.assertEqual(
                    scheduled_path.split(os.pathsep)[0], str(expected.parent)
                )
            expected.unlink()
            if index == 1:
                overrides.pop("NVM_BIN")


if __name__ == "__main__":
    unittest.main()
