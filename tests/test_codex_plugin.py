"""Check packaging without Codex: python3 -m unittest discover -s tests."""

import json
import re
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]


def frontmatter(path):
    parts = path.read_text().split("---", 2)
    if len(parts) != 3 or parts[0].strip():
        raise ValueError(f"Missing frontmatter: {path}")
    return parts[1]


def skill_name(path):
    match = re.search(r"^name:\s*([a-z0-9-]+)\s*$", frontmatter(path), re.M)
    if not match:
        raise ValueError(f"Missing skill name: {path}")
    return match.group(1)


class CodexPluginTests(unittest.TestCase):
    def test_marketplace_resolves_to_the_portable_plugin(self):
        marketplace = json.loads((REPO / ".agents/plugins/marketplace.json").read_text())
        self.assertEqual(marketplace["name"], "huyingx")
        self.assertEqual(len(marketplace["plugins"]), 1)
        entry = marketplace["plugins"][0]
        self.assertEqual(entry["name"], "pstack")
        self.assertEqual(entry["source"]["source"], "local")
        self.assertTrue(entry["source"]["path"].startswith("./"))
        self.assertEqual((REPO / entry["source"]["path"]).resolve(), REPO)
        self.assertEqual(entry["policy"]["installation"], "AVAILABLE")
        self.assertEqual(entry["policy"]["authentication"], "ON_INSTALL")

    def test_plugin_identity_preserves_the_author_and_version(self):
        plugin = json.loads((REPO / "plugin.json").read_text())
        cursor = json.loads((REPO / ".cursor-plugin/plugin.json").read_text())
        self.assertEqual(plugin["$schema"], "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json")
        self.assertEqual(plugin["name"], "pstack")
        self.assertRegex(plugin["name"], r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
        self.assertEqual(plugin["version"], cursor["version"])
        self.assertEqual(plugin["author"], cursor["author"])
        self.assertEqual(plugin["license"], cursor["license"])
        self.assertEqual(plugin["repository"], "https://github.com/huyingx/pstack")

    def test_all_bundled_skills_have_unique_names_and_explicit_policies(self):
        skills = sorted((REPO / "skills").glob("*/SKILL.md"))
        self.assertTrue(skills, "The plugin must bundle skills")
        names = []
        for path in skills:
            with self.subTest(skill=path.parent.name):
                name = skill_name(path)
                self.assertEqual(name, path.parent.name)
                names.append(name)
                if re.search(r"^disable-model-invocation:\s*true\s*$", frontmatter(path), re.M):
                    policy = (path.parent / "agents/openai.yaml").read_text()
                    self.assertRegex(policy, r"(?m)^policy:\s*$")
                    self.assertRegex(policy, r"(?m)^\s+allow_implicit_invocation:\s*false\s*$")
        self.assertEqual(len(names), len(set(names)))


if __name__ == "__main__":
    unittest.main()
