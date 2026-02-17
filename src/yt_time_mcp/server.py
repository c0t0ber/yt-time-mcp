from __future__ import annotations

import os
from datetime import date, datetime
from typing import Any

from mcp.server.fastmcp import FastMCP

from .youtrack_api import YouTrackClient, YouTrackError

mcp = FastMCP("youtrack-time-mcp")


def _parse_date(value: str | None, *, default: date | None = None) -> date:
    if not value:
        if default is None:
            raise ValueError("date is required")
        return default
    return datetime.strptime(value, "%Y-%m-%d").date()


def _is_read_only_mode() -> bool:
    raw = os.getenv("YOUTRACK_TIME_MCP_READ_ONLY", "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


@mcp.tool()
def log_time(issue_id: str, date_str: str, minutes: int, text: str = "") -> dict[str, Any]:
    """Create one YouTrack work item.

    issue_id: issue key like SPS-578
    date_str: YYYY-MM-DD
    minutes: integer minutes to log
    """
    client = YouTrackClient.from_env_or_auth_file()
    entry_date = _parse_date(date_str)
    if _is_read_only_mode():
        raise ValueError("read-only mode is enabled (YOUTRACK_TIME_MCP_READ_ONLY=true), log_time is disabled")
    if minutes <= 0:
        raise ValueError("minutes must be > 0")
    created = client.log_work_item(issue_id=issue_id, entry_date=entry_date, minutes=minutes, text=text)
    return {
        "created": created,
        "minutes": minutes,
        "hours": round(minutes / 60, 2),
    }


@mcp.tool()
def time_report(
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
    except (YouTrackError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
