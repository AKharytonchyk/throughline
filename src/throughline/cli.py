"""Throughline CLI (contracts/cli.md).

Two everyday commands — ``collect`` (gather usage read-only) and ``report`` (build the
dashboard, offline) — plus consent-gated ``hooks`` management and ``config``. No command
makes any network call or starts a daemon.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path


def _load_sessions(cfg):
    from throughline.collector import discover
    from throughline.parser.transcript import parse_transcript

    sessions = []
    for path in discover.list_copied(cfg.transcripts_dir):
        sessions.append(parse_transcript(path, cfg.size_unit))
    return sessions


def cmd_collect(args) -> int:
    from throughline.config import load_config, save_config
    from throughline.collector import discover

    cfg = load_config(args.working_dir)
    if args.transcript_dir:
        cfg.transcript_dir = args.transcript_dir
    save_config(cfg)

    root = Path(cfg.transcript_dir).expanduser()
    if not root.exists():
        print(f"error: transcript directory not found: {root}", file=sys.stderr)
        return 2

    refs = discover.discover_sessions(cfg.transcript_dir, since=args.since, project=args.project)
    print(f"Found {len(refs)} session(s) under {root}")
    if args.dry_run:
        for r in refs[:20]:
            print(f"  would copy: {r.project}/{r.session_id}.jsonl ({r.size_bytes} bytes)")
        return 0

    copied = discover.copy_sessions(refs, cfg.transcripts_dir)
    print(f"Copied {len(copied)} transcript(s) (read-only) into {cfg.transcripts_dir}")

    calls_log = cfg.calls_log
    backups = list(cfg.precompact_dir.glob("*.jsonl")) if cfg.precompact_dir.exists() else []
    if calls_log.exists() or backups:
        print(f"Hook data present: calls-log={'yes' if calls_log.exists() else 'no'}, "
              f"pre-compact backups={len(backups)}")
    else:
        print("No hook data yet (optional: `throughline hooks install` to enable "
              "the essentialness signal).")
    return 0


def cmd_report(args) -> int:
    from throughline.config import load_config, load_interventions, load_price_list
    from throughline.parser.mounted import build_mounted_set
    from throughline.report.aggregate import build_embedded_data
    from throughline.report.render import render_to_file

    cfg = load_config(args.working_dir)
    if args.transcript_dir:
        from throughline.parser.transcript import parse_transcript
        root = Path(args.transcript_dir).expanduser()
        paths = sorted(root.glob("*/*.jsonl")) or sorted(root.glob("*.jsonl"))
        sessions = [parse_transcript(p, cfg.size_unit) for p in paths]
    else:
        sessions = _load_sessions(cfg)
        if not sessions:
            print("error: no collected data. Run `throughline collect` first.", file=sys.stderr)
            return 3

    discovered: set = set()
    for s in sessions:
        discovered |= s.discovered_tools
    mounted = build_mounted_set(cfg.mcp_config_paths, discovered_tools=discovered)
    interventions = load_interventions(cfg)
    price_list = load_price_list(cfg)  # empty unless the user opted in with prices.json (US4)
    initial_filter = None
    if args.project or args.date_from or args.date_to:
        initial_filter = {"project": args.project, "from": args.date_from, "to": args.date_to}
    embedded = build_embedded_data(sessions, mounted, cfg, interventions, initial_filter, price_list)

    out = Path(args.out).expanduser() if args.out else cfg.out_path
    render_to_file(embedded, out)
    print(f"Dashboard written to {out}")
    if args.open:
        import webbrowser
        webbrowser.open(out.resolve().as_uri())
    return 0


def cmd_note(args) -> int:
    from throughline.config import load_config, load_interventions, save_interventions
    import datetime as _dt

    cfg = load_config(args.working_dir)
    items = load_interventions(cfg)
    if args.action == "list":
        if not items:
            print("No interventions recorded.")
        for it in sorted(items, key=lambda i: i["date"]):
            print(f"  {it['date']}  {it['label']}")
        return 0
    if args.action == "add":
        if not args.date or not args.label:
            print("error: `note add` needs --date YYYY-MM-DD and --label", file=sys.stderr)
            return 1
        try:
            _dt.date.fromisoformat(args.date)
        except ValueError:
            print(f"error: bad date {args.date!r} (expected YYYY-MM-DD)", file=sys.stderr)
            return 1
        items.append({"date": args.date, "label": args.label})
        save_interventions(cfg, items)
        print(f"Added: {args.date} {args.label}")
        return 0
    if args.action == "remove":
        kept = [i for i in items if not (i["date"] == args.date
                and (args.label is None or i["label"] == args.label))]
        save_interventions(cfg, kept)
        print(f"Removed {len(items) - len(kept)} note(s).")
        return 0
    return 1


def cmd_hooks(args) -> int:
    from throughline.config import load_config, save_config
    from throughline.collector import hooks_install as hi

    cfg = load_config(args.working_dir)
    settings_path = Path(args.settings).expanduser() if args.settings else hi.default_settings_path()
    hooks_dir = cfg.working / "hooks"

    if args.action == "status":
        st = hi.status_hooks(settings_path, hooks_dir)
        print(json.dumps(st, indent=2))
        return 0

    if args.action == "install":
        if not args.yes:
            if not sys.stdin.isatty():
                print("error: consent required. Re-run with --yes to install hooks into "
                      f"{settings_path}.", file=sys.stderr)
                return 4
            ans = input(f"Install Throughline hooks into {settings_path}? "
                        "This merges into your Claude Code settings (a backup is made "
                        "first). [y/N] ").strip().lower()
            if ans not in ("y", "yes"):
                print("Aborted.")
                return 4
        res = hi.install_hooks(settings_path, hooks_dir, cfg.backups_dir)
        cfg.hooks_opt_in = {"installed": True, "settings_path": str(settings_path)}
        save_config(cfg)
        print(f"Installed hooks (added: {', '.join(res['added']) or 'none new'}). "
              f"Backup: {res['backup']}")
        return 0

    if args.action == "uninstall":
        res = hi.uninstall_hooks(settings_path, hooks_dir)
        cfg.hooks_opt_in = {"installed": False}
        save_config(cfg)
        print(f"Uninstalled hooks (removed from: {', '.join(res['removed']) or 'none'}).")
        return 0
    return 1


def cmd_config(args) -> int:
    from throughline.config import load_config, save_config, Config

    cfg = load_config(args.working_dir)
    if args.set:
        for pair in args.set:
            if "=" not in pair:
                print(f"error: --set expects KEY=VALUE, got {pair!r}", file=sys.stderr)
                return 1
            key, _, val = pair.partition("=")
            key = key.strip()
            if not hasattr(cfg, key):
                print(f"error: unknown config key {key!r}", file=sys.stderr)
                return 1
            cur = getattr(cfg, key)
            setattr(cfg, key, _coerce(val, cur))
        save_config(cfg)
    print(json.dumps(asdict(cfg), indent=2))
    return 0


def _coerce(val: str, current):
    if isinstance(current, bool):
        return val.lower() in ("1", "true", "yes", "on")
    if isinstance(current, int):
        return int(val)
    if isinstance(current, float):
        return float(val)
    return val


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="throughline", description=__doc__)
    p.add_argument("--working-dir", help="override working directory (default ~/.throughline)")
    sub = p.add_subparsers(dest="command", required=True)

    c = sub.add_parser("collect", help="gather Claude Code usage (read-only)")
    c.add_argument("--transcript-dir")
    c.add_argument("--since", help="only sessions modified on/after YYYY-MM-DD")
    c.add_argument("--project", help="filter by project path substring")
    c.add_argument("--all", action="store_true", default=True, help=argparse.SUPPRESS)
    c.add_argument("--dry-run", action="store_true")
    c.set_defaults(func=cmd_collect)

    r = sub.add_parser("report", help="produce the local interactive dashboard (offline)")
    r.add_argument("--out")
    r.add_argument("--transcript-dir", help="report directly from a transcript dir (e.g. fixtures)")
    r.add_argument("--project", help="initial repo/project filter (client can change it live)")
    r.add_argument("--from", dest="date_from", metavar="YYYY-MM-DD", help="initial time-range start")
    r.add_argument("--to", dest="date_to", metavar="YYYY-MM-DD", help="initial time-range end")
    r.add_argument("--open", action="store_true", help="open the dashboard in your browser")
    r.set_defaults(func=cmd_report)

    nt = sub.add_parser("note", help="manage dated intervention notes (markers on trends)")
    nt.add_argument("action", choices=["add", "list", "remove"])
    nt.add_argument("--date", metavar="YYYY-MM-DD")
    nt.add_argument("--label")
    nt.set_defaults(func=cmd_note)

    h = sub.add_parser("hooks", help="manage the opt-in collection hooks")
    h.add_argument("action", choices=["install", "uninstall", "status"])
    h.add_argument("--yes", action="store_true", help="skip the consent prompt (install)")
    h.add_argument("--settings", help="path to Claude Code settings.json")
    h.set_defaults(func=cmd_hooks)

    cf = sub.add_parser("config", help="show or edit configuration")
    cf.add_argument("--set", action="append", metavar="KEY=VALUE")
    cf.add_argument("--show", action="store_true", default=True, help=argparse.SUPPRESS)
    cf.set_defaults(func=cmd_config)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
