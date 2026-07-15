# CoachSphere Analytics Platform

> Fictional AI Sales Coaching Platform — Internal Analytics Layer  
> Built as a portfolio project demonstrating enterprise data engineering, metrics layers, and interactive dashboards.

---

## What This Is

CoachSphere is a fictional B2B SaaS company that coaches enterprise sales teams using AI-driven role-play sessions, real-time feedback, and skill assessments. This repository contains the **internal analytics and metrics layer** — the data backbone that answers the questions the product and business teams keep asking.

**Inspired by:** Retorio, Gong, Chorus — AI coaching platforms for enterprise sales.

---

## Architecture

```
Data Source (Python/Faker)
        │
        ▼
SQLite Database (coachsphere.db)
  ├── users
  ├── coaching_sessions
  ├── skill_assessments
  ├── session_feedback
  └── business_metrics
        │
        ▼
Metrics Layer (SQL Views — version controlled)
  ├── v_session_engagement        ← engagement_score definition v1.2
  ├── v_skill_progression         ← skill_progression_rate definition v1.1
  ├── v_communication_quality     ← communication_quality_score definition v1.0
  ├── v_business_impact           ← business_impact_index definition v1.3
  ├── v_coaching_effectiveness    ← coaching_effectiveness_score definition v2.0
  └── v_team_summary              ← team-level rollup
        │
        ▼
Streamlit Dashboard (Plotly)
  ├── Overview KPIs
  ├── Team Analytics
  ├── Skill Progression
  ├── Session Insights
  ├── Rep Deep Dive
  ├── Metric Definitions
  └── 🤖 AI Assistant (natural language queries via Groq)
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
| AI Assistant | Groq API (Llama 3.3 70B) |
| Future: API | FastAPI |
| Future: AI Agent | Google ADK + MCP |

---

## Project Structure

```
coachsphere/
├── data/
│   └── generate_data.py       # Generates all synthetic data → SQLite
├── metrics/
│   └── apply_metrics.py       # Creates all metric views in the DB
├── dashboard/
│   └── app.py                 # Streamlit multi-page dashboard
├── agent/                     # (coming) AI agent + MCP server
├── docs/                      # Architecture diagrams, API reference
├── coachsphere.db             # SQLite database (generated)
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
echo GROQ_API_KEY=your_key_here > .env

# 4. Generate the database
python data/generate_data.py

# 5. Apply the metrics layer
python metrics/apply_metrics.py

# 6. Launch the dashboard
streamlit run dashboard/app.py
```

---

## Metric Definitions

All KPIs are version-controlled in `metric_definitions` table and viewable inside the dashboard under **Metric Definitions**.

| Metric | Formula | Version |
|---|---|---|
| Session Engagement Score | `(completion_rate×0.5) + (avg_duration/45×0.3) + (feedback_rate×0.2)` | v1.2 |
| Skill Progression Rate | `(avg_score_this_month − avg_score_last_month) / avg_score_last_month × 100` | v1.1 |
| Communication Quality Score | `(communication + clarity + confidence) / 3` | v1.0 |
| Business Impact Index | `quota_attainment×0.6 + win_rate×0.4` | v1.3 |
| Coaching Effectiveness Score | `skill_score×0.35 + engagement×0.35 + business_impact×0.30` | v2.0 |

---

## Dataset

- **44 users** (40 sales reps + 4 team leads) across Enterprise, SMB, EMEA, APAC
- **2,437 coaching sessions** over 6 months (Jan–Jun 2024)
- **2,054 skill assessments** across 5 competency dimensions
- **2,054 feedback records** from AI coaching evaluation
- **240 monthly business metric records**

---

## Roadmap

- [x] Data simulation & SQLite schema  
- [x] Metric views (version-controlled)  
- [x] Streamlit dashboard (6 pages)  
- [x] AI Assistant — natural language queries via Groq (Llama 3.3 70B)
- [ ] FastAPI REST layer with OpenAPI docs  
- [ ] AI agent (Google ADK) querying the metrics layer via MCP  
- [ ] Before/after launch comparison view  
- [ ] dbt integration for transformation models

---

## Author

**Roshan Karkera** — M.Sc. Integrated Information Systems, FAU Erlangen-Nürnberg  
[roshan-karkera.github.io](https://roshan-karkera.github.io) · [LinkedIn](https://linkedin.com/in/roshan-karkera)
