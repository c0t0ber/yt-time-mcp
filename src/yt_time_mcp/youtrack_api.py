from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class YouTrackError(RuntimeError):
    pass


@dataclass
class WorkItem:
    id: str
    issue_id: str
    date: date
    minutes: int
    text: str


class YouTrackClient:
    def __init__(self, base_url: str, token: str, timeout: int = 30) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout

    @classmethod
    def from_env_or_auth_file(cls) -> "YouTrackClient":
        token = os.getenv("YOUTRACK_TOKEN")
        base_url = os.getenv("YOUTRACK_BASE_URL")

        if token and base_url:
            return cls(base_url=base_url, token=token)

        auth_path = Path(os.getenv("YOUTRACK_AUTH_FILE", "~/.youtrack-mcp-auth.json")).expanduser()
        if not auth_path.exists():
            raise YouTrackError(
                "Missing auth: set YOUTRACK_TOKEN + YOUTRACK_BASE_URL or create ~/.youtrack-mcp-auth.json"
            )

        data = json.loads(auth_path.read_text(encoding="utf-8"))
        return cls(base_url=data["baseUrl"], token=data["data"]["token"])

    def log_work_item(self, issue_id: str, entry_date: date, minutes: int, text: str = "") -> dict[str, Any]:
        payload = {
            "date": _date_to_utc_ms(entry_date),
            "duration": {"minutes": int(minutes)},
            "text": text,
        }
        path = f"/api/issues/{issue_id}/timeTracking/workItems"
        params = {
            "fields": "id,date,duration(minutes,presentation),text,issue(idReadable,project(shortName))"
        }
        return self._request_json("POST", path, params=params, payload=payload)

    def delete_work_item(self, issue_id: str, work_item_id: str) -> None:
        path = f"/api/issues/{issue_id}/timeTracking/workItems/{work_item_id}"
        self._request_json("DELETE", path)

    def list_work_items(self, author: str, start_date: date, end_date: date, top: int = 1000) -> list[dict[str, Any]]:
        params = {
            "author": author,
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat(),
            "$top": str(top),
            "fields": "id,date,duration(minutes,presentation),text,issue(idReadable,project(shortName)),author(login)",
        }
        return self._request_json("GET", "/api/workItems", params=params)

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> Any:
        query = f"?{urlencode(params)}" if params else ""
        url = f"{self.base_url}{path}{query}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
        }
        body = None
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        req = Request(url=url, data=body, headers=headers, method=method)

        try:
            with urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8")
                if not raw:
                    return {}
                return json.loads(raw)
        except HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise YouTrackError(f"{method} {url} failed: HTTP {exc.code}: {details}") from exc


def _date_to_utc_ms(value: date) -> int:
    dt = datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)
