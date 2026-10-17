"""
CoachSphere MCP Server
Exposes CoachSphere's 13 analytics tools to any MCP client (e.g. Claude Desktop).
For testing MCP server on Web UI run: npx @modelcontextprotocol/inspector
"""

import os
import re
import sys
import sqlite3
import subprocess
from pathlib import Path

from mcp.server.fastmcp import FastMCP

# ── Database setup ─────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent          # coachsphere/ project root
DB   = Path(os.environ.get("TEMP", "/tmp")) / "coachsphere.db"


def _ensure_db():
    """Boot the database if it doesn't exist yet."""
    try:
        conn = sqlite3.connect(DB)
        count = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='users'"
        ).fetchone()[0]
        conn.close()
        if count > 0:
            return
    except Exception:
        pass
    subprocess.run([sys.executable, str(ROOT / "data" / "generate_data.py")], check=True)
    subprocess.run([sys.executable, str(ROOT / "metrics" / "apply_metrics.py")], check=True)


_ensure_db()


def _q(sql: str, params: tuple = ()) -> list[dict]:
    """Run a parameterised SQL query and return rows as a list of dicts."""
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ── Input validation ───────────────────────────────────────────────────────────
# Whitelist team and month before interpolating into SQL.
# Any value not in the known set is dropped (no filter = all rows returned),
# which is safe: an unrecognised value returns all data rather than executing
# injected SQL. Parameterised queries are used for free-text inputs (rep_name,
# metric_name) where whitelisting is not applicable.

def _valid_teams() -> set:
    """Load the current team list from the database — no hardcoding."""
    try:
        return {r["team"] for r in _q("SELECT DISTINCT team FROM users WHERE team IS NOT NULL")}
    except Exception:
        return {"Enterprise", "SMB", "EMEA", "APAC"}  # fallback if DB not yet initialised


def _tf(team: str, col: str = "team") -> str:
    """Safe team filter — validates against the live team list from the database."""
    return f"AND {col} = '{team}'" if team in _valid_teams() else ""


def _mf(month: str, col: str = "period_month") -> str:
    """Safe month filter — accepts only YYYY-MM format."""
    return f"AND {col} = '{month}'" if re.match(r"^\d{4}-\d{2}$", month or "") else ""


# ── MCP server ─────────────────────────────────────────────────────────────────
_port = int(os.environ.get("PORT", 8000))
mcp = FastMCP(
    name="CoachSphere",
    instructions=(
        "You have access to CoachSphere's AI sales coaching analytics platform. "
        "Data covers Jan–Jun 2024 across 4 teams: Enterprise, SMB, EMEA, APAC. "
        "Always call a tool to retrieve data before answering — never guess numbers. "
        "After getting data, give a concise answer with specific figures."
    ),
    host="0.0.0.0",
    port=_port,
)


# ── Tool 1: Top Performers ─────────────────────────────────────────────────────
@mcp.tool()
def get_top_performers(month: str, team: str = "all") -> list[dict]:
    """
    Get the top 5 sales reps ranked by coaching effectiveness score for a given month.

    Args:
        month: Period month in YYYY-MM format, e.g. '2024-06'.
        team: Team filter — Enterprise, SMB, EMEA, APAC, or 'all'.
    """
    return _q(f"""
        SELECT name, team, period_month,
               ROUND(coaching_effectiveness_score, 3) AS effectiveness,
               ROUND(engagement_score, 3)             AS engagement,
               ROUND(skill_score, 3)                  AS skill_score
        FROM v_coaching_effectiveness
        WHERE 1=1 {_mf(month)} {_tf(team)}
        ORDER BY coaching_effectiveness_score DESC
        LIMIT 5
    """)


# ── Tool 2: Team Summary ───────────────────────────────────────────────────────
@mcp.tool()
def get_team_summary(month: str = "all") -> list[dict]:
    """
    Get team-level performance: engagement score, effectiveness score, active rep count.

    Args:
        month: Period month YYYY-MM, or 'all' to return every month.
    """
    return _q(f"""
        SELECT team, period_month, active_reps,
               ROUND(avg_engagement, 3)    AS avg_engagement,
               ROUND(avg_effectiveness, 3) AS avg_effectiveness
        FROM v_team_summary
        WHERE 1=1 {_mf(month)}
        ORDER BY period_month, avg_effectiveness DESC
    """)


# ── Tool 3: Quota Attainment ───────────────────────────────────────────────────
@mcp.tool()
def get_quota_attainment(month: str = "all", team: str = "all") -> list[dict]:
    """
    Get average quota attainment %, win rate, and total deals closed by team.

    Args:
        month: Period month YYYY-MM, or 'all'.
        team: Team name or 'all'.
    """
    return _q(f"""
        SELECT team, period_month,
               ROUND(AVG(quota_attainment) * 100, 1) AS avg_quota_pct,
               ROUND(AVG(win_rate) * 100, 1)         AS avg_win_rate_pct,
               SUM(deals_closed)                     AS total_deals
        FROM v_business_impact
        WHERE 1=1 {_mf(month)} {_tf(team)}
        GROUP BY team, period_month
        ORDER BY period_month, avg_quota_pct DESC
    """)


# ── Tool 4: Session Stats ──────────────────────────────────────────────────────
@mcp.tool()
def get_session_stats(month: str = "all", team: str = "all") -> list[dict]:
    """
    Get coaching session counts: scheduled, completed, and completion rate by team and month.

    Args:
        month: Period month YYYY-MM, or 'all'.
        team: Team name or 'all'.
    """
    return _q(f"""
        SELECT team, period_month,
               SUM(sessions_scheduled) AS scheduled,
               SUM(sessions_completed) AS completed,
               ROUND(
                   CAST(SUM(sessions_completed) AS REAL) / SUM(sessions_scheduled) * 100,
                   1
               ) AS completion_pct
        FROM v_session_engagement
        WHERE 1=1 {_mf(month)} {_tf(team)}
        GROUP BY team, period_month
        ORDER BY period_month
    """)


# ── Tool 5: Skill Improvement ──────────────────────────────────────────────────
@mcp.tool()
def get_skill_improvement(skill: str = "overall") -> list[dict]:
    """
    Find the top 10 reps who improved the most in a specific skill across the 6-month period.

    Args:
        skill: One of communication, product_knowledge, objection_handling,
               closing_technique, active_listening, or 'overall'.
    """
    valid = {"communication", "product_knowledge", "objection_handling",
             "closing_technique", "active_listening"}
    col = skill if skill in valid else "avg_overall_score"
    return _q(f"""
        SELECT name, team,
               ROUND(MIN({col}), 2)             AS start_score,
               ROUND(MAX({col}), 2)             AS end_score,
               ROUND(MAX({col}) - MIN({col}), 2) AS improvement
        FROM v_skill_progression
        GROUP BY user_id, name, team
        ORDER BY improvement DESC
        LIMIT 10
    """)


# ── Tool 6: Rep Profile ────────────────────────────────────────────────────────
@mcp.tool()
def get_rep_profile(rep_name: str) -> list[dict]:
    """
    Get full coaching history for a specific sales rep across all months.
    Returns effectiveness, engagement, skill score, quota attainment, deals closed, win rate.

    Args:
        rep_name: Full or partial name of the sales rep.
    """
    return _q("""
        SELECT ce.name, ce.team, ce.period_month,
               ROUND(ce.coaching_effectiveness_score, 3) AS effectiveness,
               ROUND(ce.engagement_score, 3)             AS engagement,
               ROUND(ce.skill_score, 3)                  AS skill_score,
               ROUND(bi.quota_attainment * 100, 1)       AS quota_pct,
               bi.deals_closed,
               ROUND(bi.win_rate * 100, 1)               AS win_rate_pct
        FROM v_coaching_effectiveness ce
        LEFT JOIN v_business_impact bi
            ON ce.user_id = bi.user_id AND ce.period_month = bi.period_month
        WHERE ce.name LIKE '%' || ? || '%'
        ORDER BY ce.period_month
    """, (rep_name,))


# ── Tool 7: Top by Metric ──────────────────────────────────────────────────────
@mcp.tool()
def get_top_by_metric(
    metric: str,
    month: str = "all",
    team: str = "all",
    limit: int = 5,
) -> list[dict]:
    """
    Rank the top sales reps by any specific metric.

    Args:
        metric: One of: deals_closed, quota_pct, win_rate_pct,
                effectiveness, engagement, skill_score.
        month: Period month YYYY-MM, or 'all'.
        team: Team name or 'all'.
        limit: Number of top reps to return (default 5).
    """
    metric_map = {
        "deals_closed":  "bi.deals_closed",
        "quota_pct":     "ROUND(bi.quota_attainment * 100, 1)",
        "win_rate_pct":  "ROUND(bi.win_rate * 100, 1)",
        "effectiveness": "ROUND(ce.coaching_effectiveness_score, 3)",
        "engagement":    "ROUND(ce.engagement_score, 3)",
        "skill_score":   "ROUND(ce.skill_score, 3)",
    }
    col = metric_map.get(metric, "bi.deals_closed")
    return _q(f"""
        SELECT ce.name, ce.team, ce.period_month,
               {col}                                     AS {metric},
               bi.deals_closed,
               ROUND(bi.quota_attainment * 100, 1)       AS quota_pct,
               ROUND(bi.win_rate * 100, 1)               AS win_rate_pct,
               ROUND(ce.coaching_effectiveness_score, 3) AS effectiveness
        FROM v_coaching_effectiveness ce
        LEFT JOIN v_business_impact bi
            ON ce.user_id = bi.user_id AND ce.period_month = bi.period_month
        WHERE {col} IS NOT NULL {_mf(month, "ce.period_month")} {_tf(team, "ce.team")}
        ORDER BY {col} DESC
        LIMIT {max(1, min(int(limit), 50))}
    """)


# ── Tool 8: Compare Skill Progression ─────────────────────────────────────────
@mcp.tool()
def compare_skill_progression(teams: str = "all", skill: str = "overall") -> list[dict]:
    """
    Compare skill score trends across teams or for a specific skill over time.

    Args:
        teams: Comma-separated team names e.g. 'EMEA,Enterprise', or 'all'.
        skill: One of communication, product_knowledge, objection_handling,
               closing_technique, active_listening, or 'overall'.
    """
    valid_skills = {"communication", "product_knowledge", "objection_handling",
                    "closing_technique", "active_listening"}
    col = skill if skill in valid_skills else "avg_overall_score"
    # Whitelist each team name individually before interpolating
    requested = [t.strip() for t in (teams or "").split(",")]
    safe = [t for t in requested if t in _valid_teams()]
    team_list = "', '".join(safe)
    team_filter = f"AND team IN ('{team_list}')" if safe else ""
    return _q(f"""
        SELECT period_month, team, ROUND(AVG({col}), 2) AS avg_score
        FROM v_skill_progression
        WHERE 1=1 {team_filter}
        GROUP BY period_month, team
        ORDER BY period_month, team
    """)


# ── Tool 9: Identify Underperforming Segments ──────────────────────────────────
@mcp.tool()
def identify_underperforming_segments(month: str = "all") -> list[dict]:
    """
    Find teams performing below the platform average coaching effectiveness score.
    Returns teams ranked worst-first with their deviation from the platform average.

    Args:
        month: Period month YYYY-MM, or 'all'.
    """
    return _q(f"""
        WITH platform AS (
            SELECT ROUND(AVG(coaching_effectiveness_score), 3) AS platform_avg
            FROM v_coaching_effectiveness
            WHERE 1=1 {_mf(month)}
        )
        SELECT team, period_month,
               ROUND(AVG(coaching_effectiveness_score), 3) AS avg_effectiveness,
               ROUND(AVG(engagement_score), 3)             AS avg_engagement,
               COUNT(DISTINCT user_id)                     AS rep_count,
               ROUND(
                   AVG(coaching_effectiveness_score) - (SELECT platform_avg FROM platform),
                   3
               ) AS vs_platform_avg
        FROM v_coaching_effectiveness
        WHERE 1=1 {_mf(month)}
        GROUP BY team, period_month
        ORDER BY avg_effectiveness ASC
    """)


# ── Tool 10: Explain Metric Definition ────────────────────────────────────────
@mcp.tool()
def explain_metric_definition(metric_name: str) -> list[dict]:
    """
    Look up how a KPI or metric is defined and calculated.
    Use when asked 'how is X calculated', 'what does X mean', or 'explain metric X'.

    Args:
        metric_name: Metric name or keyword, e.g. 'engagement', 'effectiveness', 'business_impact'.
    """
    return _q("""
        SELECT metric_name, display_name, description, formula, unit, version
        FROM metric_definitions
        WHERE metric_name  LIKE '%' || ? || '%'
           OR display_name LIKE '%' || ? || '%'
        LIMIT 3
    """, (metric_name, metric_name))


# ── Tool 11: Team Roster ───────────────────────────────────────────────────────
@mcp.tool()
def get_team_roster(team: str = "all") -> list[dict]:
    """
    List all sales reps in a team with their role, region, and hire date.
    Use when asked for names of people in a team, who is on a team, or to list team members.

    Args:
        team: Team name — Enterprise, SMB, EMEA, APAC, or 'all' for everyone.
    """
    return _q(f"""
        SELECT name, team, role, region, hire_date
        FROM users
        WHERE role != 'Team Lead' {_tf(team)}
        ORDER BY team, name
    """)


# ── Tool 12: Manager Details ───────────────────────────────────────────────────
@mcp.tool()
def get_manager_details(team: str = "all") -> list[dict]:
    """
    Get each team manager's name along with their team's latest performance summary.
    Use when asked for details about managers, who leads each team, or manager performance.

    Args:
        team: Team name — Enterprise, SMB, EMEA, APAC, or 'all' for all managers.
    """
    return _q(f"""
        SELECT
            u.name        AS manager_name,
            ts.team,
            ts.period_month,
            ts.active_reps,
            ROUND(ts.avg_engagement, 3)    AS avg_engagement,
            ROUND(ts.avg_effectiveness, 3) AS avg_effectiveness
        FROM v_team_summary ts
        JOIN users u ON u.team = ts.team AND u.role = 'Team Lead'
        WHERE ts.period_month = (SELECT MAX(period_month) FROM v_team_summary)
        {_tf(team, "ts.team")}
        ORDER BY ts.avg_effectiveness DESC
    """)


# ── Tool 13: Coaching ROI ─────────────────────────────────────────────────────
@mcp.tool()
def get_coaching_roi(
    team: str = "all",
    cost_per_session: float = 150.0,
    target_quota: float = 30000.0,
) -> list[dict]:
    """
    Calculate coaching ROI, revenue gap, and cost optimisation signals by team.
    Use when asked about ROI, cost of coaching, revenue impact, underperformance cost,
    which teams are over- or under-coached, budget efficiency, or revenue gap.

    Args:
        team: Team filter — Enterprise, SMB, EMEA, APAC, or 'all'.
        cost_per_session: Assumed cost per coaching session in EUR (default 150).
        target_quota: Monthly revenue target per rep in EUR (default 30000).
    """
    # Fix: aggregate sessions and metrics at the same grain (team) in separate CTEs,
    # then join one-row-per-team to one-row-per-team.
    # Mixing coaching_sessions (per-event) with monthly views in a single GROUP BY
    # fans out rows by session count and corrupts team-level averages.
    rows = _q(f"""
        WITH s AS (
            SELECT u.team,
                   COUNT(cs.session_id) AS sessions
            FROM coaching_sessions cs
            JOIN users u ON u.user_id = cs.user_id
            WHERE u.role != 'Team Lead' {_tf(team, "u.team")}
            GROUP BY u.team
        ),
        m AS (
            SELECT u.team,
                   ROUND(AVG(bi.quota_attainment) * 100, 1)      AS avg_quota_pct,
                   ROUND(SUM(
                       CASE WHEN bi.quota_attainment < 1.0
                            THEN (1.0 - bi.quota_attainment) * {float(target_quota)}
                            ELSE 0 END
                   ), 0)                                          AS revenue_gap_eur,
                   ROUND(AVG(ce.coaching_effectiveness_score), 3) AS avg_effectiveness
            FROM users u
            JOIN v_business_impact bi ON bi.user_id = u.user_id
            JOIN v_coaching_effectiveness ce
                 ON ce.user_id = u.user_id AND ce.period_month = bi.period_month
            WHERE u.role != 'Team Lead' {_tf(team, "u.team")}
            GROUP BY u.team
        )
        SELECT m.team,
               s.sessions,
               m.avg_quota_pct,
               m.revenue_gap_eur,
               m.avg_effectiveness
        FROM m JOIN s ON s.team = m.team
        ORDER BY m.revenue_gap_eur DESC
    """)
    for r in rows:
        spend = r["sessions"] * cost_per_session
        r["coaching_spend_eur"] = round(spend, 0)
        gap = r.get("revenue_gap_eur") or 0
        r["roi_ratio"] = round(gap / spend, 2) if spend > 0 else None
    return rows


# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    mcp.run(transport=transport)
