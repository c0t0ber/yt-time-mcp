from __future__ import annotations

import argparse
import json
from datetime import datetime

from .youtrack_api import YouTrackClient


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="yt-time-cli", description="YouTrack time tracking helper")
    sub = parser.add_subparsers(dest="cmd", required=True)

    l = sub.add_parser("log", help="log one work item")
    l.add_argument("--issue-id", required=True)
    l.add_argument("--date", required=True, help="YYYY-MM-DD")
    l.add_argument("--minutes", required=True, type=int)
    l.add_argument("--text", default="")

    r = sub.add_parser("report", help="daily report")
    r.add_argument("--start-date", required=True)
    r.add_argument("--end-date", required=True)
    r.add_argument("--author", default="me")
    r.add_argument("--target-hours-per-day", type=float, default=8.0)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    client = YouTrackClient.from_env_or_auth_file()

    if args.cmd == "log":
        if args.minutes <= 0:
            raise SystemExit("--minutes must be > 0")
        created = client.log_work_item(
            issue_id=args.issue_id,
            entry_date=_parse_date(args.date),
            minutes=args.minutes,
            text=args.text,
        )
        print(json.dumps({"created": created}, ensure_ascii=False, indent=2))
        return

    if args.cmd == "report":
        items = client.list_work_items(
            author=args.author,
            start_date=_parse_date(args.start_date),
            end_date=_parse_date(args.end_date),
        )
        by_day: dict[str, int] = {}
        for item in items:
            day = datetime.utcfromtimestamp(item["date"] / 1000).date().isoformat()
            by_day[day] = by_day.get(day, 0) + int(item["duration"]["minutes"])

        start = _parse_date(args.start_date)
        end = _parse_date(args.end_date)
        target_minutes = int(round(args.target_hours_per_day * 60))
        days = []
        cursor = start
        total_minutes = 0
        while cursor <= end:
            key = cursor.isoformat()
            minutes = by_day.get(key, 0)
            total_minutes += minutes
            days.append(
                {
                    "date": key,
                    "minutes": minutes,
                    "hours": round(minutes / 60, 2),
                    "delta_minutes": minutes - target_minutes,
                    "delta_hours": round((minutes - target_minutes) / 60, 2),
                }
            )
            cursor = cursor.fromordinal(cursor.toordinal() + 1)

        print(
            json.dumps(
                {
                    "start_date": start.isoformat(),
                    "end_date": end.isoformat(),
                    "target_hours_per_day": args.target_hours_per_day,
                    "total_minutes": total_minutes,
                    "total_hours": round(total_minutes / 60, 2),
                    "days": days,
                },
                ensure_ascii=False,
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
