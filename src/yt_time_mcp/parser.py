from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta

ISSUE_RE = re.compile(r"\b([A-Za-z][A-Za-z0-9_]*-\d+)\b")
ISO_DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
RU_DATE_RE = re.compile(r"\b(\d{1,2})\.(\d{1,2})(?:\.(\d{4}))?\b")
CLOCK_RE = re.compile(r"\b(\d{1,2}):(\d{2})\b")
DURATION_TOKEN_RE = re.compile(
    r"\b(\d+(?:[\.,]\d+)?)\s*(h|hr|hrs|hour|hours|ч|час|часа|часов|m|min|mins|minute|minutes|м|мин|минута|минуты|минут)\b",
    re.IGNORECASE,
)

WEEKDAY_PATTERNS = {
    0: re.compile(r"\b(пн|пон|понед|понедельник(?:а|у|ом|е)?)\b", re.IGNORECASE),
    1: re.compile(r"\b(вт|вто|вторник(?:а|у|ом|е)?)\b", re.IGNORECASE),
    2: re.compile(r"\b(ср|сре|среда|среду|среды|среде)\b", re.IGNORECASE),
    3: re.compile(r"\b(чт|чет|четв|четверг(?:а|у|ом|е)?)\b", re.IGNORECASE),
    4: re.compile(r"\b(пт|пят|пятница|пятницу|пятницы|пятнице)\b", re.IGNORECASE),
    5: re.compile(r"\b(сб|суб|суббота|субботу|субботы|субботе)\b", re.IGNORECASE),
    6: re.compile(r"\b(вс|воск|воскресенье|воскресенья|воскресенью|воскресеньем)\b", re.IGNORECASE),
}


@dataclass
class ParsedEntry:
    issue_id: str
    date: date
    minutes: int
    text: str
    source_line: int


class ParseError(ValueError):
    pass


def parse_date_token(raw: str, reference_date: date) -> date:
    raw = raw.strip()
    iso_match = ISO_DATE_RE.search(raw)
    if iso_match:
        return datetime.strptime(iso_match.group(1), "%Y-%m-%d").date()

    ru_match = RU_DATE_RE.search(raw)
    if ru_match:
        d = int(ru_match.group(1))
        m = int(ru_match.group(2))
        y = int(ru_match.group(3)) if ru_match.group(3) else reference_date.year
        return date(y, m, d)

    for weekday, pattern in WEEKDAY_PATTERNS.items():
        if pattern.search(raw):
            return _resolve_weekday_nearest_past(reference_date, weekday)

    raise ParseError(f"Could not parse date from: {raw!r}")


def parse_duration_minutes(raw: str) -> int:
    raw = raw.strip().lower()
    total = 0

    for h, m in CLOCK_RE.findall(raw):
        total += int(h) * 60 + int(m)

    for value, unit in DURATION_TOKEN_RE.findall(raw):
        v = float(value.replace(",", "."))
        if unit.startswith(("h", "ч", "час")):
            total += int(round(v * 60))
        else:
            total += int(round(v))

    if total <= 0:
        raise ParseError(f"Could not parse duration from: {raw!r}")
    return total


def parse_raw_entries(raw_text: str, reference_date: date | None = None) -> list[ParsedEntry]:
    ref = reference_date or date.today()
    entries: list[ParsedEntry] = []
    last_issue: str | None = None
    last_date: date | None = None

    chunks: list[tuple[int, str]] = []
    for line_no, line in enumerate(raw_text.splitlines(), start=1):
        for part in line.split(";"):
            candidate = part.strip()
            if candidate:
                chunks.append((line_no, candidate))

    for line_no, chunk in chunks:
        issue_match = ISSUE_RE.search(chunk)
        issue_id = issue_match.group(1).upper() if issue_match else last_issue

        try:
            parsed_date = parse_date_token(chunk, reference_date=ref)
        except ParseError:
            parsed_date = last_date

        try:
            minutes = parse_duration_minutes(chunk)
        except ParseError as exc:
            raise ParseError(f"Line {line_no}: {exc}") from exc

        if not issue_id:
            raise ParseError(f"Line {line_no}: issue id is missing")
        if not parsed_date:
            raise ParseError(f"Line {line_no}: date is missing")

        text = _cleanup_comment(chunk, issue_id)
        entries.append(
            ParsedEntry(
                issue_id=issue_id,
                date=parsed_date,
                minutes=minutes,
                text=text,
                source_line=line_no,
            )
        )
        last_issue = issue_id
        last_date = parsed_date

    return entries


def _resolve_weekday_nearest_past(reference: date, target_weekday: int) -> date:
    delta = (reference.weekday() - target_weekday) % 7
    return reference - timedelta(days=delta)


def _cleanup_comment(chunk: str, issue_id: str) -> str:
    text = ISSUE_RE.sub("", chunk)
    text = ISO_DATE_RE.sub("", text)
    text = RU_DATE_RE.sub("", text)
    text = CLOCK_RE.sub("", text)
    text = DURATION_TOKEN_RE.sub("", text)
    for pattern in WEEKDAY_PATTERNS.values():
        text = pattern.sub("", text)
    text = re.sub(r"\s+", " ", text).strip(" -,:;|\t")
    return text
