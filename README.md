# yt-time-mcp

MCP server for YouTrack time tracking with reliable direct API writes (without buggy third-party connector behavior).

## What it does

- Accepts raw text like `SPS-578 пятница 6ч`.
- Parses issue id, date and duration.
- Writes work items directly to YouTrack API.
- Has dry-run mode before writing.
- Generates per-day report with deficit vs 8h/day.

## Install (uvx, no local setup)

Run directly from GitHub:

```bash
uvx --from git+https://github.com/c0t0ber/yt-time-mcp yt-time-cli --help
```

## Install (local dev)

```bash
cd yt-time-mcp
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

## Auth

Option 1 (recommended if you already use YouTrack MCP auth file):

- `~/.youtrack-mcp-auth.json`

Option 2 (env vars):

```bash
export YOUTRACK_BASE_URL="https://newtrack.spectrum.int"
export YOUTRACK_TOKEN="perm:..."
```

## Raw text format examples

```text
SPS-578 пятница 6ч
SPS-578 понедельник 5h
SPS-652 2026-02-13 2:30
SPS-578 13.02 2ч 30м
SPS-578 пн 2ч; вт 3ч
```

Notes:

- If weekday is provided (`пн`, `пятница`), parser resolves it to the nearest past weekday relative to `reference_date` (or today).
- If issue id/date is omitted in next chunk, previous value is reused.

## CLI usage

Dry-run parse:

```bash
yt-time-cli parse --text "SPS-578 пятница 6ч"
```

Apply from file:

```bash
yt-time-cli apply --file entries.txt --reference-date 2026-02-17
```

Apply with safety preview:

```bash
yt-time-cli apply --file entries.txt --reference-date 2026-02-17 --dry-run
```

## MCP tools

Server name: `youtrack-time-mcp`

Exposed tools:

- `parse_time_text(raw_text, reference_date?)`
- `add_time(issue_id, date_str, duration, text="")`
- `add_time_from_text(raw_text, dry_run=true, reference_date?, note_prefix="")`
- `daily_report(start_date, end_date, target_hours_per_day=8.0, author="me")`
- `healthcheck()`

Run server:

```bash
yt-time-mcp
```

## MCP client config example (stdio + uvx)

```json
{
  "mcpServers": {
    "youtrack-time": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/c0t0ber/yt-time-mcp",
        "yt-time-mcp"
      ],
      "env": {
        "YOUTRACK_BASE_URL": "https://newtrack.spectrum.int",
        "YOUTRACK_TOKEN": "perm:..."
      }
    }
  }
}
```

Optional pin to tag/commit:

```json
"args": ["--from", "git+https://github.com/c0t0ber/yt-time-mcp@<tag-or-commit>", "yt-time-mcp"]
```

## Publish to GitHub

```bash
cd yt-time-mcp
git init
git add .
git commit -m "feat: initial YouTrack time-tracking MCP server"
gh repo create yt-time-mcp --public --source=. --remote=origin --push
```

If `gh` is not logged in, run:

```bash
gh auth login
```
