# CoachSphere MCP Server — Setup Guide

Connect CoachSphere's 10 analytics tools to Claude Desktop in 3 steps.

---

## Step 1 — Install the MCP library

Open a terminal in the `coachsphere/mcp/` folder and run:

```bash
pip install "mcp[cli]"
```

---

## Step 2 — Add to Claude Desktop config

Open Claude Desktop → **Settings → Developer → Edit Config**.

This opens a file called `claude_desktop_config.json`. Add the `coachsphere` block inside `mcpServers`:

```json
{
  "mcpServers": {
    "coachsphere": {
      "command": "python",
      "args": [
        "C:\\Users\\User\\OneDrive\\Desktop\\DE\\Job\\coachsphere\\mcp\\server.py"
      ]
    }
  }
}
```

Save the file, then **restart Claude Desktop**.

---

## Step 3 — Verify it's connected

In Claude Desktop, you should see a 🔧 tools icon in the chat bar.
Click it — you should see all 10 CoachSphere tools listed.

Try asking:
> *"Who are the top 5 reps by coaching effectiveness in June 2024?"*

Claude will call `get_top_performers` and return real data from your SQLite database.

---

## The 10 Tools

| Tool | What it does |
|---|---|
| `get_top_performers` | Top 5 reps by coaching effectiveness for a given month |
| `get_team_summary` | Team-level engagement + effectiveness scores |
| `get_quota_attainment` | Avg quota %, win rate, total deals by team |
| `get_session_stats` | Sessions scheduled, completed, completion rate |
| `get_skill_improvement` | Top 10 most improved reps by skill |
| `get_rep_profile` | Full 6-month history for a specific rep |
| `get_top_by_metric` | Rank reps by any metric (deals, win rate, etc.) |
| `compare_skill_progression` | Skill trends across teams over time |
| `identify_underperforming_segments` | Teams below platform average |
| `explain_metric_definition` | How any KPI is defined and calculated |

---

## How it works

```
Claude Desktop  →  MCP protocol (stdio)  →  server.py  →  SQLite (coachsphere.db)
```

The server starts automatically when Claude Desktop launches — no separate process needed.
The database is auto-generated the first time if it doesn't exist.

---

## Troubleshooting

**"Tools not showing up"** — restart Claude Desktop after saving the config.

**"Database not found"** — the server will auto-run `generate_data.py` and `apply_metrics.py`
on first start. If this fails, run them manually:
```bash
cd coachsphere/
python data/generate_data.py
python metrics/apply_metrics.py
```

**Python not on PATH** — replace `"command": "python"` with the full path to your Python executable,
e.g. `"command": "C:\\Python312\\python.exe"`.
