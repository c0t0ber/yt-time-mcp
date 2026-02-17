# yt-time-mcp

Minimal MCP server for YouTrack time tracking with direct API writes.

## What it does

- Log time to an issue in minutes.
- Build daily report for a period (with target hours/day delta).
- No raw text parsing in MCP.

## YouTrack compatibility

- Minimum tested YouTrack API version: `2022.1` (from `/api/openapi.json -> info.version`).
- The server uses only these REST endpoints:
  - `GET /api/workItems`
  - `POST /api/issues/{id}/timeTracking/workItems`

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

## Security / read-only mode

- To force safe report-only behavior, enable:

```bash
export YOUTRACK_TIME_MCP_READ_ONLY=true
```

- In read-only mode:
  - `time_report` and `healthcheck` work
  - `log_time` is blocked by server validation

- Recommended token policy:
  - For report-only usage: use a read-only token.
  - For logging usage: use a dedicated least-privilege token that can read work items and create work items only.

## CLI usage

Log time:

```bash
yt-time-cli log --issue-id SPS-578 --date 2026-02-13 --minutes 360 --text "work"
```

Get report:

```bash
yt-time-cli report --start-date 2026-02-11 --end-date 2026-02-17 --author me --target-hours-per-day 8
```

## MCP tools

Server name: `youtrack-time-mcp`

Exposed tools:

- `log_time(issue_id, date_str, minutes, text="")`
- `time_report(start_date, end_date, target_hours_per_day=8.0, author="me")`
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
        "YOUTRACK_TOKEN": "perm:...",
        "YOUTRACK_TIME_MCP_READ_ONLY": "true"
      }
    }
  }
}
```

Optional pin to tag/commit:

```json
"args": ["--from", "git+https://github.com/c0t0ber/yt-time-mcp@<tag-or-commit>", "yt-time-mcp"]
```

## Client setup

### Codex (CLI / IDE extension)

Quick add via CLI:

```bash
codex mcp add youtrack-time -- uvx --from git+https://github.com/c0t0ber/yt-time-mcp yt-time-mcp
```

Or add to `~/.codex/config.toml`:

```toml
[mcp_servers.youtrack_time]
command = "uvx"
args = ["--from", "git+https://github.com/c0t0ber/yt-time-mcp", "yt-time-mcp"]

[mcp_servers.youtrack_time.env]
YOUTRACK_BASE_URL = "https://newtrack.spectrum.int"
YOUTRACK_TOKEN = "perm:..."
YOUTRACK_TIME_MCP_READ_ONLY = "true"
```

### Claude Code

Create `.mcp.json` in the project root:

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
        "YOUTRACK_TOKEN": "perm:...",
        "YOUTRACK_TIME_MCP_READ_ONLY": "true"
      }
    }
  }
}
```

### Cursor

Use either project config `.cursor/mcp.json` or global config `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "youtrack-time": {
      "type": "stdio",
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/c0t0ber/yt-time-mcp",
        "yt-time-mcp"
      ],
      "env": {
        "YOUTRACK_BASE_URL": "https://newtrack.spectrum.int",
        "YOUTRACK_TOKEN": "perm:...",
        "YOUTRACK_TIME_MCP_READ_ONLY": "true"
      }
    }
  }
}
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
