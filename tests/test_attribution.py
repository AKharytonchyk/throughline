import unittest

from throughline.parser.attribution import attribute, detect_cli_wrapped_mcp


class TestAttribution(unittest.TestCase):
    def test_mcp_name(self):
        a = attribute("mcp__acme__getSprint", {})
        self.assertEqual((a.bucket, a.server, a.tool), ("mcp", "acme", "getSprint"))

    def test_mcp_tool_with_underscores(self):
        a = attribute("mcp__acme-mcp__slack__slack_send_message", {})
        self.assertEqual(a.server, "acme-mcp")
        self.assertEqual(a.tool, "slack__slack_send_message")

    def test_builtin(self):
        self.assertEqual(attribute("Read", {}).bucket, "builtin")

    def test_cli_wrapped_mcp_reattributed(self):
        a = attribute("Bash", {"command": "mcp-cli tools-call @acme --tool doThing"})
        self.assertEqual(a.bucket, "mcp")
        self.assertEqual(a.server, "acme")
        self.assertEqual(a.tool, "doThing")
        self.assertEqual(a.cli_wrapped_from, "Bash")

    def test_plain_bash_not_wrapped(self):
        a = attribute("Bash", {"command": "ls -la && git status"})
        self.assertEqual(a.bucket, "builtin")
        self.assertIsNone(detect_cli_wrapped_mcp("ls -la && git status"))


if __name__ == "__main__":
    unittest.main()
