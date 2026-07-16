import unittest

from helpers import FIX
from throughline.parser.mounted import build_mounted_set, read_mcp_servers


class TestMounted(unittest.TestCase):
    def setUp(self):
        self.cfg_paths = [str(FIX / "mcp_config.json")]

    def test_reads_mcp_servers_from_config(self):
        servers = read_mcp_servers(self.cfg_paths)
        self.assertEqual(servers, {"acme", "playwright"})

    def test_mounted_set_includes_builtins_and_servers(self):
        mounted = build_mounted_set(self.cfg_paths)
        keys = {(m.bucket, m.server, m.name) for m in mounted}
        self.assertIn(("builtin", None, "Bash"), keys)
        self.assertIn(("mcp", "playwright", "mcp:playwright"), keys)

    def test_mcp_coverage_is_server_granularity(self):
        mounted = build_mounted_set(self.cfg_paths)
        mcp = [m for m in mounted if m.bucket == "mcp"]
        self.assertTrue(mcp)
        self.assertTrue(all(m.granularity == "server" for m in mcp))

    def test_discovered_tools_give_mcp_tool_granularity(self):
        mounted = build_mounted_set(self.cfg_paths, discovered_tools={
            "Bash", "mcp__acme__getSprint", "mcp__playwright__browser_navigate"})
        names = {m.name for m in mounted}
        self.assertIn("mcp:acme/getSprint", names)
        self.assertIn("mcp:playwright/browser_navigate", names)
        # discovered MCP tools are tool-level, and cover the config servers (no server dup)
        self.assertNotIn("mcp:acme", names)
        self.assertNotIn("mcp:playwright", names)


if __name__ == "__main__":
    unittest.main()
