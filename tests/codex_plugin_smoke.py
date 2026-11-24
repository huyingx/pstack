"""Install and discover every skill: python3 tests/codex_plugin_smoke.py.

Requires Codex CLI with plugin support. Uses temporary child-process configuration
and makes no model calls or changes to the user's Codex configuration.
"""

import json
import os
import queue
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path

from test_codex_plugin import REPO, frontmatter, skill_name


PLUGIN_ID = "pstack@huyingx"
TIMEOUT = 90


def command(codex, args, env, cwd):
    result = subprocess.run(
        [codex, *args, "--json"],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=TIMEOUT,
    )
    if result.returncode:
        raise RuntimeError(f"codex {' '.join(args)} failed:\n{result.stderr}")
    return json.loads(result.stdout)


def discover_skills(codex, env, cwd):
    with tempfile.TemporaryFile(mode="w+") as errors:
        process = subprocess.Popen(
            [codex, "app-server", "--stdio"],
            cwd=cwd,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=errors,
            text=True,
        )
        messages = queue.Queue()

        def read_messages():
            for line in process.stdout:
                messages.put(line)
            messages.put(None)

        reader = threading.Thread(target=read_messages, daemon=True)
        reader.start()

        def send(message):
            process.stdin.write(json.dumps(message) + "\n")
            process.stdin.flush()

        def response(request_id):
            deadline = time.monotonic() + TIMEOUT
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError(f"Timed out waiting for app-server request {request_id}")
                try:
                    line = messages.get(timeout=remaining)
                except queue.Empty as error:
                    raise TimeoutError(f"Timed out waiting for app-server request {request_id}") from error
                if line is None:
                    errors.seek(0)
                    raise RuntimeError(f"app-server exited before request {request_id}:\n{errors.read()}")
                message = json.loads(line)
                if message.get("id") == request_id:
                    if "error" in message:
                        raise RuntimeError(f"app-server request {request_id}: {message['error']}")
                    return message["result"]

        try:
            send({
                "id": 1,
                "method": "initialize",
                "params": {
                    "clientInfo": {"name": "pstack-plugin-smoke", "version": "1.0.0"},
                    "capabilities": {"experimentalApi": True},
                },
            })
            response(1)
            send({"method": "initialized"})
            send({
                "id": 2,
                "method": "skills/list",
                "params": {"cwds": [str(REPO)], "forceReload": True},
            })
            return response(2)["data"]
        finally:
            process.stdin.close()
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
            reader.join(timeout=5)
            process.stdout.close()


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def main():
    codex = shutil.which("codex")
    if not codex:
        raise SystemExit("Codex CLI is required for this smoke test.")
    expected = {
        f"pstack:{skill_name(path)}": path
        for path in (REPO / "skills").glob("*/SKILL.md")
    }
    require(expected, "No repository skills found")
    with tempfile.TemporaryDirectory(prefix="pstack-codex-smoke-") as temporary:
        test_root = Path(temporary)
        test_home = test_root / "codex-home"
        test_home.mkdir()
        env = {**os.environ, "CODEX_HOME": str(test_home)}
        marketplace = command(codex, ["plugin", "marketplace", "add", str(REPO)], env, test_root)
        require(marketplace["marketplaceName"] == "huyingx", "Wrong marketplace registered")
        installed = command(codex, ["plugin", "add", PLUGIN_ID], env, test_root)
        require(installed["pluginId"] == PLUGIN_ID, "Wrong plugin installed")
        listing = command(codex, ["plugin", "list", "--marketplace", "huyingx"], env, test_root)
        entries = [entry for entry in listing["installed"] if entry["pluginId"] == PLUGIN_ID]
        require(len(entries) == 1 and entries[0]["enabled"], "Plugin was not installed and enabled")

        data = discover_skills(codex, env, test_root)
        require(len(data) == 1, f"Expected one skill listing, got {len(data)}")
        require(not data[0]["errors"], f"Skill loading errors: {data[0]['errors']}")
        skills = [skill for skill in data[0]["skills"] if skill.get("pluginId") == PLUGIN_ID]
        actual = {skill["name"] for skill in skills}
        require(actual == set(expected), f"Skill mismatch: missing {set(expected) - actual}, extra {actual - set(expected)}")
        require(len(skills) == len(expected), "Duplicate plugin skills were discovered")
        installed_root = Path(installed["installedPath"]).resolve()
        explicit_count = 0
        for skill in skills:
            require(skill["enabled"], f"Disabled plugin skill: {skill['name']}")
            cached_skill = Path(skill["path"]).resolve()
            require(installed_root in cached_skill.parents, f"Skill loaded outside installed plugin: {cached_skill}")
            require(cached_skill.read_bytes() == expected[skill["name"]].read_bytes(), f"Stale installed skill: {skill['name']}")
            if "disable-model-invocation: true" in frontmatter(expected[skill["name"]]):
                policy = cached_skill.parent / "agents/openai.yaml"
                source_policy = expected[skill["name"]].parent / "agents/openai.yaml"
                require(policy.read_bytes() == source_policy.read_bytes(), f"Lost invocation policy: {skill['name']}")
                explicit_count += 1
        print(f"Installed {PLUGIN_ID}; discovered {len(skills)} enabled skills with {explicit_count} explicit-only policies.")


if __name__ == "__main__":
    main()
