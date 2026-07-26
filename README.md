# CoachSphere Analytics Platform

> Fictional AI Sales Coaching Platform — Internal Analytics Layer  
> Built as a portfolio project demonstrating enterprise data engineering, metrics layers, MCP tool integration, and interactive AI-powered dashboards.

---

## What This Is

CoachSphere is a fictional B2B SaaS company that coaches enterprise sales teams using AI-driven role-play sessions, real-time feedback, and skill assessments. This repository contains the **internal analytics and metrics layer** — the data backbone that answers the questions product and business teams keep asking.

**Inspired by:** Retorio — AI coaching platforms for enterprise sales.

---

## Architecture

```
Data Source (Python / Faker)
        │
        ▼
SQLite Database (coachsphere.db)
  ├── users
  ├── coaching_sessions
  ├── skill_assessments
  ├── session_feedback
  ├── business_metrics
  └── metric_definitions
        │
        ▼
Metrics Layer (SQL Views — version controlled)
  ├── v_session_engagement        ← engagement_score v1.2
  ├── v_skill_progression         ← skill_progression_rate v1.1
  ├── v_communication_quality     ← communication_quality_score v1.0
  ├── v_business_impact           ← business_impact_index v1.3
  ├── v_coaching_effectiveness    ← coaching_effectiveness_score v2.0
  └── v_team_summary              ← team-level rollup
        │
        ├──────────────────────────────────┐
        ▼                                  ▼
Streamlit Dashboard (Plotly)       MCP Server (FastMCP)
  ├── 📊 Overview KPIs               10 analytics tools exposed
  ├── 👥 Team Analytics              via Model Context Protocol
  ├── 🧠 Skill Progression           ← Claude Desktop connects here
  ├── 📅 Session Insights
  ├── 🔍 Rep Deep Dive
  ├── 📋 Metric Definitions
  ├── 🤖 AI Assistant (Groq + Llama 3.3 70B)
  └── 🔌 MCP Server status + live demo
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Data generation | Python, Faker, NumPy |
| Storage | SQLite |
| Metrics layer | SQL Views (version-controlled) |
| Analytics | Pandas, NumPy |
| Visualisation | Plotly, Streamlit |
| AI Assistant | Groq API · Llama 3.3 70B · agentic tool-calling |
| MCP Server | FastMCP (`mcp[cli]`) · stdio transport |
| MCP Client | Claude Desktop |

---

## Project Structure

```
coachsphere/
├── data/
│   └── generate_data.py          # Generates all synthetic data → SQLite
├── metrics/
│   └── apply_metrics.py          # Creates all metric views + metric_definitions table
├── dashboard/
│   └── app.py                    # Streamlit dashboard (8 pages, full dark theme)
├── mcp/
│   ├── server.py                 # FastMCP server — 10 analytics tools via MCP
│   ├── requirements.txt          # mcp[cli]>=1.0.0
│   ├── claude_desktop_config.json # Drop into Claude Desktop settings
│   └── SETUP.md                  # 3-step MCP connection guide
├── requirements.txt
└── README.md
```

---

## Quick Start

```bash
# 1. Clone and set up virtual environment
git clone https://github.com/roshan-karkera/coachsphere.git
cd coachsphere
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # Mac/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Add your Groq API key (free at console.groq.com)
# Add to .env or Streamlit Cloud secrets:
# GROQ_API_KEY=your_key_here

# 4. Generate the database
python data/generate_data.py

# 5. Apply the metrics layer
python metrics/apply_metrics.py

# 6. Launch the dashboard
streamlit run dashboard/app.py
```

---

## MCP Server — Connect to Claude Desktop

CoachSphere exposes all 10 analytics tools via the [Model Context Protocol](https://modelcontextprotocol.io), so any MCP client (Claude Desktop, etc.) can query your coaching data in natural language.

```bash
# Install MCP library
pip install "mcp[cli]"
```

Add the following to Claude Desktop → Settings → Developer → Edit Config:

```json
{
  "mcpServers": {
    "coachsphere": {
      "command": "python",
      "args": ["C:\\path\\to\\coachsphere\\mcp\\server.py"]
    }
  }
}
```

Restart Claude Desktop — all 10 tools appear automatically. Try:
> *"Who are the top 5 reps by coaching effectiveness in June 2024?"*

See `mcp/SETUP.md` for full instructions and troubleshooting.

---

## 10 MCP Tools

| Tool | What it does |
|---|---|
| `get_top_performers` | Top 5 reps by coaching effectiveness for a given month / team |
| `get_team_summary` | Team-level engagement + effectiveness scores |
| `get_quota_attainment` | Avg quota %, win rate, total deals by team |
| `get_session_stats` | Sessions scheduled, completed, and completion rate |
| `get_skill_improvement` | Top 10 most improved reps by skill |
| `get_rep_profile` | Full 6-month coaching history for a specific rep |
| `get_top_by_metric` | Rank reps by any metric (deals, win rate, quota, effectiveness…) |
| `compare_skill_progression` | Skill trends across teams over time |
| `identify_underperforming_segments` | Teams performing below platform average |
| `explain_metric_definition` | How any KPI is defined, its formula, unit, and version |

---

## AI Assistant

The **🤖 AI Assistant** page lets you query coaching data in plain English. It uses Groq's Llama 3.3 70B with agentic tool-calling:

- Automatically selects the right tool and parameters from your question
- Handles typos and shorthand (e.g. `apu 24` → April 2024, `jsn` → June)
- Shows a collapsible **Agent trace** with the tool called, filters applied, SQL executed, and result table
- **✏️ Edit query** — click to modify the SQL inline and re-run it
- **✏️ Edit** on any user message — fix your question and re-send without retyping

---

## Metric Definitions

All KPIs are version-controlled in the `metric_definitions` table and viewable inside the dashboard under **📋 Metric Definitions**.

| Metric | Formula | Version |
|---|---|---|
| Session Engagement Score | `(completion_rate×0.5) + (avg_duration/45×0.3) + (feedback_rate×0.2)` | v1.2 |
| Skill Progression Rate | `(avg_score_this_month − avg_score_last_month) / avg_score_last_month × 100` | v1.1 |
| Communication Quality Score | `(communication + clarity + confidence) / 3` | v1.0 |
| Business Impact Index | `quota_attainment×0.6 + win_rate×0.4` | v1.3 |
| Coaching Effectiveness Score | `skill_score×0.35 + engagement×0.35 + business_impact×0.30` | v2.0 |

---

## Dataset

- **44 users** — 40 sales reps + 4 team leads across Enterprise, SMB, EMEA, APAC
- **2,437 coaching sessions** over 6 months (Jan–Jun 2024)
- **2,054 skill assessments** across 5 competency dimensions
- **2,054 feedback records** from AI coaching evaluation
- **240 monthly business metric records**

---

## Live Demo

[coachsphere-ekumda5ebehr6ypyd9qkmj.streamlit.app](https://coachsphere-ekumda5ebehr6ypyd9qkmj.streamlit.app/)

---

## Author

**Roshan Karkera** — M.Sc. International Information Systems, FAU Erlangen-Nürnberg  
[roshan-karkera.github.io](https://roshan-karkera.github.io) · [LinkedIn](https://linkedin.com/in/roshan-karkera)
