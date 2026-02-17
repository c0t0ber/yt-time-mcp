from __future__ import annotations

from datetime import date, datetime
from typing import Any

from mcp.server.fastmcp import FastMCP

from .parser import ParseError, ParsedEntry, parse_duration_minutes, parse_raw_entries
from .youtrack_api import YouTrackClient, YouTrackError

mcp = FastMCP("youtrack-time-mcp")


def _parse_date(value: str | None, *, default: date | None = None) -> date:
    if not value:
        if default is None:
            raise ValueError("date is required")
        return default
    return datetime.strptime(value, "%Y-%m-%d").date()


def _entries_preview(entries: list[ParsedEntry]) -> list[dict[str, Any]]:
    return [
        {
            "issue_id": e.issue_id,
            "date": e.date.isoformat(),
            "minutes": e.minutes,
            "hours": round(e.minutes / 60, 2),
            "text": e.text,
            "source_line": e.source_line,
        }
        for e in entries
    ]


@mcp.tool()
def parse_time_text(raw_text: str, reference_date: str | None = None) -> dict[str, Any]:
    """Parse raw text into normalized time entries without writing to YouTrack.

    Expected line examples:
    - SPS-578 пятница 6ч
    - SPS-578 2026-02-16 5h
    - SPS-578 13.02 2:30
    - SPS-578 пн 2ч; вт 3ч
    """
    ref = _parse_date(reference_date, default=date.today())
    entries = parse_raw_entries(raw_text, reference_date=ref)
    return {
        "count": len(entries),
        "total_minutes": sum(e.minutes for e in entries),
        "entries": _entries_preview(entries),
    }


@mcp.tool()
def add_time(issue_id: str, date_str: str, duration: str, text: str = "") -> dict[str, Any]:
    """Add one worklog item to YouTrack.

    duration examples: 6h, 2.5h, 2:30, 150m, 6ч, 2ч 30м
    date format: YYYY-MM-DD
    """
    client = YouTrackClient.from_env_or_auth_file()
    entry_date = _parse_date(date_str)
    minutes = parse_duration_minutes(duration)
    created = client.log_work_item(issue_id=issue_id, entry_date=entry_date, minutes=minutes, text=text)
    return {
        "created": created,
        "minutes": minutes,
        "hours": round(minutes / 60, 2),
    }


@mcp.tool()
def add_time_from_text(
    raw_text: str,
    dry_run: bool = True,
    reference_date: str | None = None,
    note_prefix: str = "",
) -> dict[str, Any]:
    """Parse raw text and add all entries to YouTrack.

    Use dry_run=true first to validate parsing.
    """
    ref = _parse_date(reference_date, default=date.today())
    entries = parse_raw_entries(raw_text, reference_date=ref)

    if dry_run:
        return {
            "dry_run": True,
            "count": len(entries),
            "total_minutes": sum(e.minutes for e in entries),
            "entries": _entries_preview(entries),
        }

    client = YouTrackClient.from_env_or_auth_file()
    created_items: list[dict[str, Any]] = []
    for entry in entries:
        text = f"{note_prefix}{entry.text}".strip()
        created = client.log_work_item(
            issue_id=entry.issue_id,
            entry_date=entry.date,
            minutes=entry.minutes,
            text=text,
        )
        created_items.append(created)

    return {
        "dry_run": False,
        "count": len(created_items),
        "total_minutes": sum(e.minutes for e in entries),
        "created": created_items,
    }


@mcp.tool()
def daily_report(
    start_date: str,
    end_date: str,
    target_hours_per_day: float = 8.0,
    author: str = "me",
) -> dict[str, Any]:
    """Build daily summary and deficit/excess versus target hours per day."""
    client = YouTrackClient.from_env_or_auth_file()
    d1 = _parse_date(start_date)
    d2 = _parse_date(end_date)
    if d2 < d1:
        raise ValueError("end_date must be >= start_date")

    items = client.list_work_items(author=author, start_date=d1, end_date=d2)
    by_day: dict[str, int] = {}
    for item in items:
        day = datetime.utcfromtimestamp(item["date"] / 1000).date().isoformat()
        by_day[day] = by_day.get(day, 0) + int(item["duration"]["minutes"])

    target_minutes = int(round(target_hours_per_day * 60))
    days = []
    cursor = d1
    total_minutes = 0
    while cursor <= d2:
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
        cursor = date.fromordinal(cursor.toordinal() + 1)

    return {
        "start_date": d1.isoformat(),
        "end_date": d2.isoformat(),
        "target_hours_per_day": target_hours_per_day,
        "total_minutes": total_minutes,
        "total_hours": round(total_minutes / 60, 2),
        "days": days,
    }


@mcp.tool()
def healthcheck() -> dict[str, Any]:
    """Check that auth is configured and YouTrack API is reachable."""
    client = YouTrackClient.from_env_or_auth_file()
    today = date.today()
    items = client.list_work_items(author="me", start_date=today, end_date=today, top=1)
    return {"ok": True, "today_items_checked": len(items), "base_url": client.base_url}


def main() -> None:
    try:
        mcp.run(transport="stdio")
    except (YouTrackError, ParseError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
