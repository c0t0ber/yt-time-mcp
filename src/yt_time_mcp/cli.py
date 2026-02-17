from __future__ import annotations

import argparse
import json
from datetime import date, datetime
from pathlib import Path

from .parser import parse_raw_entries
from .youtrack_api import YouTrackClient


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="yt-time-cli", description="YouTrack time tracking helper")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("parse", help="parse raw text")
    p.add_argument("--text", help="raw text")
    p.add_argument("--file", help="path to file with raw text")
    p.add_argument("--reference-date", help="YYYY-MM-DD")

    a = sub.add_parser("apply", help="parse and write raw text")
    a.add_argument("--text", help="raw text")
    a.add_argument("--file", help="path to file with raw text")
    a.add_argument("--reference-date", help="YYYY-MM-DD")
    a.add_argument("--dry-run", action="store_true")

    r = sub.add_parser("report", help="daily report")
    r.add_argument("--start-date", required=True)
    r.add_argument("--end-date", required=True)
    r.add_argument("--author", default="me")

    return parser


def _read_text(args: argparse.Namespace) -> str:
    if args.text:
        return args.text
    if args.file:
        return Path(args.file).read_text(encoding="utf-8")
    raise SystemExit("Provide --text or --file")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.cmd in {"parse", "apply"}:
        raw_text = _read_text(args)
        ref = _parse_date(args.reference_date) or date.today()
        entries = parse_raw_entries(raw_text, reference_date=ref)

        if args.cmd == "parse" or args.dry_run:
            print(
                json.dumps(
                    {
                        "count": len(entries),
                        "total_minutes": sum(e.minutes for e in entries),
                        "entries": [
                            {
                                "issue": e.issue_id,
                                "date": e.date.isoformat(),
                                "minutes": e.minutes,
                                "text": e.text,
                                "source_line": e.source_line,
                            }
                            for e in entries
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return

        client = YouTrackClient.from_env_or_auth_file()
        created = []
        for e in entries:
            created.append(client.log_work_item(e.issue_id, e.date, e.minutes, e.text))

        print(json.dumps({"created": len(created), "items": created}, ensure_ascii=False, indent=2))
        return

    if args.cmd == "report":
        client = YouTrackClient.from_env_or_auth_file()
        items = client.list_work_items(
            author=args.author,
            start_date=_parse_date(args.start_date),
            end_date=_parse_date(args.end_date),
        )
        print(json.dumps(items, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
