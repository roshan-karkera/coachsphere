"""
CoachSphere MCP Server
Exposes CoachSphere's 10 analytics tools to any MCP client (e.g. Claude Desktop).
"""

import os
import sys
import json
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


def _q(sql: str) -> list[dict]:
    """Run a SQL query and return rows as a list of dicts."""
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(sql).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ── MCP server ─────────────────────────────────────────────────────────────────
mcp = FastMCP(
    name="CoachSphere",
    instructions=(
        "You have access to CoachSphere's AI sales coaching analytics platform. "
        "Data covers Jan–Jun 2024 across 4 teams: Enterprise, SMB, EMEA, APAC. "
        "Always call a tool to retrieve data before answering — never guess numbers. "
        "After getting data, give a concise answer with specific figures."
    ),
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
    mf = f"AND period_month = '{month}'" if month and month != "all" else ""
    tf = f"AND team = '{team}'"          if team  and team  != "all" else ""
    return _q(f"""
        SELECT name, team, period_month,
               ROUND(coaching_effectiveness_score, 3) AS effectiveness,
               ROUND(engagement_score, 3)             AS engagement,
               ROUND(skill_score, 3)                  AS skill_score
        FROM v_coaching_effectiveness
        WHERE 1=1 {mf} {tf}
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
    mf = f"AND period_month = '{month}'" if month and month != "all" else ""
    return _q(f"""
        SELECT team, period_month, active_reps,
               ROUND(avg_engagement, 3)    AS avg_engagement,
               ROUND(avg_effectiveness, 3) AS avg_effectiveness
        FROM v_team_summary
        WHERE 1=1 {mf}
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
    mf = f"AND period_month = '{month}'" if month and month != "all" else ""
    tf = f"AND team = '{team}'"          if team  and team  != "all" else ""
    return _q(f"""
        SELECT team, period_month,
               ROUND(AVG(quota_attainment) * 100, 1) AS avg_quota_pct,
               ROUND(AVG(win_rate) * 100, 1)         AS avg_win_rate_pct,
               SUM(deals_closed)                     AS total_deals
        FROM v_business_impact
        WHERE 1=1 {mf} {tf}
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
    mf = f"AND period_month = '{month}'" if month and month != "all" else ""
    tf = f"AND team = '{team}'"          if team  and team  != "all" else ""
    return _q(f"""
        SELECT team, period_month,
               SUM(sessions_scheduled) AS scheduled,
               SUM(sessions_completed) AS completed,
               ROUND(
                   CAST(SUM(sessions_completed) AS REAL) / SUM(sessions_scheduled) * 100,
                   1
               ) AS completion_pct
        FROM v_session_engagement
        WHERE 1=1 {mf} {tf}
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
    return _q(f"""
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
        WHERE ce.name LIKE '%{rep_name}%'
        ORDER BY ce.period_month
    """)


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
    Use when asked 'who closed the most deals', 'who has the highest win rate',
    'who hit quota', or any ranking question about a business metric.

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
    col  = metric_map.get(metric, "bi.deals_closed")
    mf   = f"AND ce.period_month = '{month}'" if month and month != "all" else ""
    tf   = f"AND ce.team = '{team}'"          if team  and team  != "all" else ""
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
        WHERE {col} IS NOT NULL {mf} {tf}
        ORDER BY {col} DESC
        LIMIT {limit}
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
    valid = {"communication", "product_knowledge", "objection_handling",
             "closing_technique", "active_listening"}
    col = skill if skill in valid else "avg_overall_score"

    team_filter = ""
    if teams and teams != "all":
        team_list = "', '".join([t.strip() for t in teams.split(",")])
        team_filter = f"AND team IN ('{team_list}')"

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
    mf = f"AND period_month = '{month}'" if month and month != "all" else ""
    return _q(f"""
        WITH platform AS (
            SELECT ROUND(AVG(coaching_effectiveness_score), 3) AS platform_avg
            FROM v_coaching_effectiveness
            WHERE 1=1 {mf}
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
        WHERE 1=1 {mf}
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
    return _q(f"""
        SELECT metric_name, display_name, description, formula, unit, version
        FROM metric_definitions
        WHERE metric_name  LIKE '%{metric_name}%'
           OR display_name LIKE '%{metric_name}%'
        LIMIT 3
    """)


# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    mcp.run()
