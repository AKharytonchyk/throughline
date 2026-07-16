import json
import tempfile
import unittest
from pathlib import Path

from throughline.collector import hooks_install as hi

EXISTING = {
    "model": "some-model",
    "hooks": {
        "PostToolUse": [
            {"matcher": "*", "hooks": [{"type": "command", "command": "echo existing-hook"}]}
        ]
    },
}


class TestHooksInstall(unittest.TestCase):
    def _setup(self, d):
        settings = Path(d) / "settings.json"
        settings.write_text(json.dumps(EXISTING, indent=2))
        return settings, Path(d) / "hooks", Path(d) / "backups"

    def test_install_merges_and_preserves_existing(self):
        with tempfile.TemporaryDirectory() as d:
            settings, hooks_dir, backups = self._setup(d)
            res = hi.install_hooks(settings, hooks_dir, backups)
            self.assertTrue(res["installed"])
            data = json.loads(settings.read_text())
            self.assertEqual(data["model"], "some-model")  # untouched
            ptu = data["hooks"]["PostToolUse"]
            cmds = [h["command"] for g in ptu for h in g["hooks"]]
            self.assertIn("echo existing-hook", cmds)  # existing preserved
            self.assertTrue(any(str(hooks_dir) in c for c in cmds))  # ours added
            self.assertIn("PreCompact", data["hooks"])  # ours added
            self.assertTrue(Path(res["backup"]).exists())  # backed up first
            # hook scripts copied under the working dir
            self.assertTrue((hooks_dir / "post_tool_use.py").exists())
            self.assertTrue((hooks_dir / "pre_compact.py").exists())

    def test_uninstall_removes_only_ours(self):
        with tempfile.TemporaryDirectory() as d:
            settings, hooks_dir, backups = self._setup(d)
            hi.install_hooks(settings, hooks_dir, backups)
            hi.uninstall_hooks(settings, hooks_dir)
            data = json.loads(settings.read_text())
            self.assertEqual(data["model"], "some-model")
            ptu = data["hooks"]["PostToolUse"]
            cmds = [h["command"] for g in ptu for h in g["hooks"]]
            self.assertEqual(cmds, ["echo existing-hook"])  # only existing remains
            self.assertNotIn("PreCompact", data["hooks"])  # ours removed entirely

    def test_status_reflects_state(self):
        with tempfile.TemporaryDirectory() as d:
            settings, hooks_dir, backups = self._setup(d)
            self.assertFalse(hi.status_hooks(settings, hooks_dir)["installed"])
            hi.install_hooks(settings, hooks_dir, backups)
            self.assertTrue(hi.status_hooks(settings, hooks_dir)["installed"])


if __name__ == "__main__":
    unittest.main()
