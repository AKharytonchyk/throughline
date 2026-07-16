import socket
import tempfile
import unittest
from pathlib import Path

from helpers import parse_fixtures, FIX
from throughline.config import Config
from throughline.parser.mounted import build_mounted_set
from throughline.report.aggregate import build_embedded_data
from throughline.report.render import render_to_file


class TestNoNetwork(unittest.TestCase):
    def test_report_pipeline_opens_no_sockets(self):
        orig = socket.socket

        def blocked(*a, **k):
            raise AssertionError("network access attempted (Constitution I: Local-Only)")

        socket.socket = blocked
        try:
            sessions = parse_fixtures()
            cfg = Config(mcp_config_paths=[str(FIX / "mcp_config.json")])
            mounted = build_mounted_set(cfg.mcp_config_paths)
            embedded = build_embedded_data(sessions, mounted, cfg)
            with tempfile.TemporaryDirectory() as d:
                out = render_to_file(embedded, Path(d) / "dash.html")
                html = out.read_text()
            # self-contained: no external/CDN references (inline app.js + data only)
            for needle in ("http://", "https://", "<script src", "cdn."):
                self.assertNotIn(needle, html)
        finally:
            socket.socket = orig


if __name__ == "__main__":
    unittest.main()
