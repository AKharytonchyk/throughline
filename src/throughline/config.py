"""Configuration and working-directory paths.

All tool output lives under the working directory (default ``~/.throughline``). The tool
refuses to write anywhere else (Constitution: Privacy / Local-Only). Config is plain JSON.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path


def _default_transcript_dir() -> str:
    return str(Path.home() / ".claude" / "projects")


def _default_mcp_config_paths() -> list[str]:
    # Offline sources that declare mounted MCP servers (research.md D7b). Read-only.
    return [str(Path.home() / ".claude.json"), ".mcp.json"]


@dataclass
class Config:
    transcript_dir: str = field(default_factory=_default_transcript_dir)
    working_dir: str = field(default_factory=lambda: str(Path.home() / ".throughline"))
    output_path: str = ""  # empty => <working_dir>/out/dashboard.html
    size_unit: str = "chars"  # "chars" | "bytes"
    chars_per_token: float = 4.0  # disclosed factor; used only for the resident estimate
    system_prompt_chars: int = 8000  # estimated system-prompt constant S (resident, D7)
    min_recurrence: int = 2  # a chain must recur at least this many times
    max_ngram: int = 6  # longest chain length mined
    mcp_config_paths: list[str] = field(default_factory=_default_mcp_config_paths)
    hooks_opt_in: dict = field(default_factory=lambda: {"installed": False})
    price_list_path: str = ""  # empty => <working_dir>/prices.json (feature 003, US4; opt-in)

    # ---- path helpers (everything under working_dir) ----
    @property
    def working(self) -> Path:
        return Path(self.working_dir).expanduser()

    @property
    def transcripts_dir(self) -> Path:
        return self.working / "transcripts"

    @property
    def calls_log(self) -> Path:
        return self.working / "calls.log.jsonl"

    @property
    def precompact_dir(self) -> Path:
        return self.working / "backups" / "precompact"

    @property
    def backups_dir(self) -> Path:
        return self.working / "backups"

    @property
    def out_path(self) -> Path:
        if self.output_path:
            return Path(self.output_path).expanduser()
        return self.working / "out" / "dashboard.html"

    @property
    def interventions_path(self) -> Path:
        return self.working / "interventions.json"

    @property
    def prices_path(self) -> Path:
        if self.price_list_path:
            return Path(self.price_list_path).expanduser()
        return self.working / "prices.json"

    def within_working(self, p: Path) -> bool:
        """Guard: is path p inside the working directory?"""
        try:
            Path(p).expanduser().resolve().relative_to(self.working.resolve())
            return True
        except ValueError:
            return False


def config_file(working_dir: str | None = None) -> Path:
    base = Path(working_dir).expanduser() if working_dir else Path.home() / ".throughline"
    return base / "config.json"


def load_config(working_dir: str | None = None) -> Config:
    path = config_file(working_dir)
    if path.exists():
        data = json.loads(path.read_text())
        known = {f for f in Config().__dict__}
        return Config(**{k: v for k, v in data.items() if k in known})
    return Config(working_dir=str(Path(working_dir).expanduser())) if working_dir else Config()


def save_config(cfg: Config) -> Path:
    cfg.working.mkdir(parents=True, exist_ok=True)
    path = config_file(cfg.working_dir)
    path.write_text(json.dumps(asdict(cfg), indent=2) + "\n")
    return path


def load_interventions(cfg: Config) -> list[dict]:
    """Read dated intervention notes ([{date, label}]) from the working dir."""
    p = cfg.interventions_path
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text())
        return [d for d in data if isinstance(d, dict) and "date" in d and "label" in d]
    except (json.JSONDecodeError, OSError):
        return []


def save_interventions(cfg: Config, items: list[dict]) -> Path:
    cfg.working.mkdir(parents=True, exist_ok=True)
    cfg.interventions_path.write_text(json.dumps(items, indent=2) + "\n")
    return cfg.interventions_path


def load_price_list(cfg: Config) -> dict:
    """Read the optional, user-editable per-model price list (feature 003, US4).

    Absent, empty, or malformed ⇒ ``{}`` (⇒ no dollar figure anywhere). Never fetched —
    prices are user-provided only (Local-Only). See contracts/price-list.schema.json.
    """
    p = cfg.prices_path
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text())
    except (json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}
