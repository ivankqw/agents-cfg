from __future__ import annotations

import json
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
IDENTITY = {
    "name": "impstack",
    "version": "1.0.0",
    "description": "impstack, imperfect operator.",
    "author": {"name": "Ivan Koh"},
    "homepage": "https://github.com/ivankqw/impstack",
    "repository": "https://github.com/ivankqw/impstack",
    "license": "MIT",
    "keywords": ["agent-plugin", "claude-code", "codex"],
}


def read_json(path: pathlib.Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise AssertionError(f"{path} must contain a JSON object")
    return value


class PluginManifestTests(unittest.TestCase):
    def test_all_manifests_are_valid_json(self) -> None:
        for path in (
            ROOT / "plugin.json",
            ROOT / "mcp.json",
            ROOT / ".claude-plugin" / "plugin.json",
        ):
            read_json(path)

    def test_plugin_identity_matches_between_manifests(self) -> None:
        root = read_json(ROOT / "plugin.json")
        claude = read_json(ROOT / ".claude-plugin" / "plugin.json")

        for field, expected in IDENTITY.items():
            self.assertEqual(root.get(field), expected, field)
            self.assertEqual(claude.get(field), expected, field)

    def test_root_manifest_uses_only_portable_fields(self) -> None:
        manifest = read_json(ROOT / "plugin.json")
        self.assertEqual(
            set(manifest),
            set(IDENTITY) | {"$schema"},
        )
        self.assertEqual(
            manifest["$schema"],
            "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
        )

    def test_mcp_manifest_has_exact_fixed_catalog_without_executor(self) -> None:
        manifest = read_json(ROOT / "mcp.json")
        catalog = read_json(ROOT / "mcp" / "servers.json")
        expected_servers = {
            server["name"]: {
                "type": "streamable-http",
                "url": server["url"],
            }
            for server in catalog["servers"]
            if "url" in server
        }

        self.assertEqual(
            manifest.get("$schema"),
            "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json",
        )
        self.assertEqual(manifest.get("mcpServers"), expected_servers)
        self.assertNotIn("executor", manifest["mcpServers"])

    def test_claude_manifest_declares_existing_component_paths_without_hooks(self) -> None:
        manifest = read_json(ROOT / ".claude-plugin" / "plugin.json")

        self.assertEqual(manifest.get("skills"), "./skills/")
        self.assertEqual(manifest.get("agents"), "./agents/")
        self.assertTrue((ROOT / "skills").is_dir())
        self.assertTrue((ROOT / "agents").is_dir())
        self.assertFalse((ROOT / "hooks" / "hooks.json").exists())
        self.assertNotIn("hooks", manifest)

    def test_each_immediate_skill_folder_has_matching_frontmatter_name(self) -> None:
        skill_dirs = sorted(path for path in (ROOT / "skills").iterdir() if path.is_dir())
        self.assertTrue(skill_dirs)

        for skill_dir in skill_dirs:
            skill_file = skill_dir / "SKILL.md"
            self.assertTrue(skill_file.is_file(), skill_dir.name)
            lines = skill_file.read_text(encoding="utf-8").splitlines()
            self.assertGreaterEqual(len(lines), 3, skill_file)
            self.assertEqual(lines[0], "---", skill_file)
            try:
                end = lines.index("---", 1)
            except ValueError:
                self.fail(f"{skill_file} has no closing frontmatter delimiter")
            names = [
                line.partition(":")[2].strip()
                for line in lines[1:end]
                if line.startswith("name:")
            ]
            self.assertEqual(names, [skill_dir.name], skill_file)


if __name__ == "__main__":
    unittest.main()
