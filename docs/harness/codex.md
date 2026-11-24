# pstack in Codex

The `huyingx` marketplace provides one `pstack` plugin containing the existing pstack skills.

## Install

Once the plugin files are pushed to the default branch of [`huyingx/pstack`](https://github.com/huyingx/pstack), run:

```bash
codex plugin marketplace add huyingx/pstack
codex plugin add pstack@huyingx
codex plugin list --marketplace huyingx
```

The last command lists the marketplace's plugins and their installation status. To use a different published branch or tag, replace the first command with:

```bash
codex plugin marketplace add huyingx/pstack --ref <branch-or-tag>
```

For a local checkout, use its absolute path instead of the remote repository:

```bash
codex plugin marketplace add /absolute/path/to/pstack
codex plugin add pstack@huyingx
codex plugin list --marketplace huyingx
```

Replace the path or branch placeholder with your checkout path or published ref.

Open a new Codex chat or CLI session after installation to load the plugin's skills.

## Use the skills

Type `$` in Codex and select a skill provided by pstack. Start with [poteto-mode](../../skills/poteto-mode/SKILL.md) for a task that needs the full workflow, or [setup-pstack](../../skills/setup-pstack/SKILL.md) to choose available models and a reasoning budget.

`setup-pstack` writes `~/.agents/pstack-models.md`. The pstack skills read it when choosing models. The [Harness section](../../skills/poteto-mode/SKILL.md#harness) already maps Cursor tools and model settings to Codex; use the tools and models available in the current session.

Most pstack skills run only when selected. Their bundled `agents/openai.yaml` files preserve that behavior in Codex. `setup-pstack` can also respond to a request to configure pstack models.

For selected skills through the skills CLI, use `npx skills add huyingx/pstack` as described in the [README](../../README.md#individual-skills).

## Packaging and checks

The repository root is the plugin package. Codex reads the existing portable `plugin.json` and discovers `skills/` automatically. `.agents/plugins/marketplace.json` points to that root, so skills keep access to their bundled references and sibling skills. This follows the [current Codex packaging format](https://developers.openai.com/plugins/build/plugins), using the same marketplace-and-plugin installation flow as [mattpocock/skills](https://github.com/mattpocock/skills).

From the repository root, run:

```bash
python3 mirror-assets/codex-policy.py --check
python3 -m unittest discover -s tests -p 'test_*.py'
python3 tests/codex_plugin_smoke.py
```

The smoke check installs this checkout with temporary Codex configuration and queries the installed plugin's skills without making model calls. It checks the complete skill set and the packaged invocation policies. Verified with Codex CLI 0.159.0. The project terms are defined in the [glossary](../../GLOSSARY.md).
