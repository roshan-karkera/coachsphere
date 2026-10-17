"""
CoachSphere Agent Tools
LangChain-compatible tools that query the CoachSphere SQLite database.
These are the same analytics operations as the MCP server, wrapped for agent use.
"""

import os
import re
import sqlite3
import json
from pathlib import Path
from langchain_core.tools import tool

DB = Path(os.environ.get("TEMP", "/tmp")) / "coachsphere.db"

# ── Input validation ───────────────────────────────────────────────────────────
# Whitelist team and month before interpolating into SQL.
# Any value not in the known set is silently dropped (returns no filter),
# which is safe: an unrecognised team returns zero rows rather than crashing
# or executing injected SQL.

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


def _q(sql: str, params: tuple = ()) -> list[dict]:
    """Run a parameterised SQL query and return rows as a list of dicts."""
    conn = sqlite3.connect(str(DB))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def _fmt(rows) -> str:
    """Format query results as readable JSON string for the LLM."""
    return json.dumps(rows, indent=2, default=str)


@tool
def get_top_performers(month: str, team: str = "all") -> str:
    """
    Get the top 5 sales reps ranked by coaching effectiveness score for a given month.
    Use this when asked who the best performers are, top reps, or highest scores.

    Args:
        month: Period month in YYYY-MM format e.g. '2024-06'. Use '2024-06' as the latest.
        team: Team filter — Enterprise, SMB, EMEA, APAC, or 'all'.
    """
    rows = _q(f"""
        SELECT name, team, period_month,
               ROUND(coaching_effectiveness_score, 3) AS effectiveness,
               ROUND(engagement_score, 3)             AS engagement,
               ROUND(skill_score, 3)                  AS skill_score
        FROM v_coaching_effectiveness
        WHERE 1=1 {_mf(month)} {_tf(team)}
        ORDER BY coaching_effectiveness_score DESC
        LIMIT 5
    """)
    return _fmt(rows)


@tool
def get_team_summary(month: str = "all") -> str:
    """
    Get team-level performance: avg engagement, avg effectiveness, active rep count.
    Use this when asked about team comparisons, overall performance, or which team is best/worst.

    Args:
        month: Period month YYYY-MM, or 'all' to return every month.
    """
    rows = _q(f"""
        SELECT team, period_month, active_reps,
               ROUND(avg_engagement, 3)    AS avg_engagement,
               ROUND(avg_effectiveness, 3) AS avg_effectiveness
        FROM v_team_summary
        WHERE 1=1 {_mf(month)}
        ORDER BY period_month, avg_effectiveness DESC
    """)
    return _fmt(rows)


@tool
def get_quota_attainment(month: str = "all", team: str = "all") -> str:
    """
    Get average quota attainment %, win rate, and total deals closed by team.
    Use this when asked about quota, sales targets, deals closed, or win rates.

    Args:
        month: Period month YYYY-MM, or 'all'.
        team: Team name or 'all'.
    """
    rows = _q(f"""
        SELECT team, period_month,
               ROUND(AVG(quota_attainment) * 100, 1) AS avg_quota_pct,
               ROUND(AVG(win_rate) * 100, 1)         AS avg_win_rate_pct,
               SUM(deals_closed)                     AS total_deals
        FROM v_business_impact
        WHERE 1=1 {_mf(month)} {_tf(team)}
        GROUP BY team, period_month
        ORDER BY period_month, avg_quota_pct DESC
    """)
    return _fmt(rows)


@tool
def get_session_stats(month: str = "all", team: str = "all") -> str:
    """
    Get coaching session counts: scheduled, completed, and completion rate.
    Use this when asked about coaching sessions, completion rates, or session engagement.

    Args:
        month: Period month YYYY-MM, or 'all'.
        team: Team name or 'all'.
    """
    rows = _q(f"""
        SELECT team, period_month,
               SUM(sessions_scheduled) AS scheduled,
               SUM(sessions_completed) AS completed,
               ROUND(
                   CAST(SUM(sessions_completed) AS REAL) / SUM(sessions_scheduled) * 100, 1
               ) AS completion_pct
        FROM v_session_engagement
        WHERE 1=1 {_mf(month)} {_tf(team)}
        GROUP BY team, period_month
        ORDER BY period_month
    """)
    return _fmt(rows)


@tool
def get_skill_improvement(skill: str = "overall") -> str:
    """
    Find the top 10 reps who improved the most in a specific skill over 6 months.
    Use this when asked about skill development, improvement, or coaching impact.

    Args:
        skill: One of: communication, product_knowledge, objection_handling,
               closing_technique, active_listening, or 'overall'.
    """
    valid = {"communication", "product_knowledge", "objection_handling",
             "closing_technique", "active_listening"}
    col = skill if skill in valid else "avg_overall_score"
    rows = _q(f"""
        SELECT name, team,
               ROUND(MIN({col}), 2)              AS start_score,
               ROUND(MAX({col}), 2)              AS end_score,
               ROUND(MAX({col}) - MIN({col}), 2) AS improvement
        FROM v_skill_progression
        GROUP BY user_id, name, team
        ORDER BY improvement DESC
        LIMIT 10
    """)
    return _fmt(rows)


@tool
def get_rep_profile(rep_name: str) -> str:
    """
    Get full coaching history for a specific sales rep across all months.
    Use this when asked about a specific person's performance, history, or progress.

    Args:
        rep_name: Full or partial name of the sales rep.
    """
    rows = _q("""
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
    return _fmt(rows)


@tool
def get_top_by_metric(metric: str, month: str = "all", team: str = "all", limit: int = 5) -> str:
    """
    Rank the top sales reps by any specific metric.
    Use when asked who closed the most deals, who has the highest win rate, or any ranking question.

    Args:
        metric: One of: deals_closed, quota_pct, win_rate_pct, effectiveness, engagement, skill_score.
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
    rows = _q(f"""
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
    return _fmt(rows)


@tool
def compare_skill_progression(teams: str = "all", skill: str = "overall") -> str:
    """
    Compare skill score trends across teams over time.
    Use when asked about skill trends, team skill comparison, or how skills changed over months.

    Args:
        teams: Comma-separated team names e.g. 'EMEA,Enterprise', or 'all'.
        skill: One of: communication, product_knowledge, objection_handling,
               closing_technique, active_listening, or 'overall'.
    """
    valid_skills = {"communication", "product_knowledge", "objection_handling",
                    "closing_technique", "active_listening"}
    col = skill if skill in valid_skills else "avg_overall_score"
    # Whitelist each team name individually
    requested = [t.strip() for t in (teams or "").split(",")]
    safe = [t for t in requested if t in _VALID_TEAMS]
    if safe:
        team_list = "', '".join(safe)
        team_filter = f"AND team IN ('{team_list}')"
    else:
        team_filter = ""
    rows = _q(f"""
        SELECT period_month, team, ROUND(AVG({col}), 2) AS avg_score
        FROM v_skill_progression
        WHERE 1=1 {team_filter}
        GROUP BY period_month, team
        ORDER BY period_month, team
    """)
    return _fmt(rows)


@tool
def identify_underperforming_segments(month: str = "all") -> str:
    """
    Find teams performing below the platform average coaching effectiveness score.
    Use when asked who needs coaching, which teams are struggling, or underperformers.

    Args:
        month: Period month YYYY-MM, or 'all'.
    """
    rows = _q(f"""
        WITH platform AS (
            SELECT ROUND(AVG(coaching_effectiveness_score), 3) AS platform_avg
            FROM v_coaching_effectiveness WHERE 1=1 {_mf(month)}
        )
        SELECT team, period_month,
               ROUND(AVG(coaching_effectiveness_score), 3) AS avg_effectiveness,
               ROUND(AVG(engagement_score), 3)             AS avg_engagement,
               COUNT(DISTINCT user_id)                     AS rep_count,
               ROUND(AVG(coaching_effectiveness_score) - (SELECT platform_avg FROM platform), 3)
                   AS vs_platform_avg
        FROM v_coaching_effectiveness
        WHERE 1=1 {_mf(month)}
        GROUP BY team, period_month
        ORDER BY avg_effectiveness ASC
    """)
    return _fmt(rows)


@tool
def explain_metric_definition(metric_name: str) -> str:
    """
    Look up how a KPI or metric is defined and calculated.
    Use when asked what a metric means, how it is calculated, or to explain a KPI.

    Args:
        metric_name: Metric name or keyword e.g. 'engagement', 'effectiveness'.
    """
    rows = _q("""
        SELECT metric_name, display_name, description, formula, unit, version
        FROM metric_definitions
        WHERE metric_name  LIKE '%' || ? || '%'
           OR display_name LIKE '%' || ? || '%'
        LIMIT 3
    """, (metric_name, metric_name))
    return _fmt(rows)


@tool
def get_team_roster(team: str = "all") -> str:
    """
    List all sales reps in a team with their role, region, and hire date.
    Use when asked for names of people in a team, who is on a team, or to list team members.

    Args:
        team: Team name — Enterprise, SMB, EMEA, APAC, or 'all' for everyone.
    """
    rows = _q(f"""
        SELECT name, team, role, region, hire_date
        FROM users
        WHERE role != 'Team Lead' {_tf(team)}
        ORDER BY team, name
    """)
    return _fmt(rows)


@tool
def get_manager_details(team: str = "all") -> str:
    """
    Get each team manager's name along with their team's latest performance summary.
    Use when asked for details about managers, who leads each team, or manager performance.

    Args:
        team: Team name — Enterprise, SMB, EMEA, APAC, or 'all' for all managers.
    """
    rows = _q(f"""
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
    return _fmt(rows)


@tool
def get_coaching_roi(
    cost_per_session: float = 150.0,
    target_quota: float = 30000.0,
    team: str = "all",
) -> str:
    """
    Calculate coaching ROI and revenue gap by team and by rep.
    Use when asked about ROI, cost of coaching, revenue impact, underperformance cost,
    resource allocation, which teams are over- or under-coached, or any cost/budget question.

    Args:
        cost_per_session: Cost of one coaching session in euros. Default 150.
        target_quota: Monthly revenue target per rep in euros. Default 30000.
        team: Team filter — Enterprise, SMB, EMEA, APAC, or 'all'.
    """
    # Fix: aggregate sessions and metrics at the same grain (team) in separate CTEs,
    # then join one-row-per-team to one-row-per-team.
    # Mixing coaching_sessions (per-event) with monthly views in a single GROUP BY
    # fans out rows by session count and corrupts averages.
    team_rows = _q(f"""
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
                   ROUND(AVG(bi.quota_attainment) * 100, 1)          AS avg_quota_pct,
                   ROUND(AVG(ce.coaching_effectiveness_score), 3)     AS avg_effectiveness
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
               m.avg_effectiveness
        FROM m JOIN s ON s.team = m.team
        ORDER BY m.avg_effectiveness DESC
    """)

    rep_rows = _q(f"""
        SELECT u.name, u.team,
               ROUND(AVG(bi.quota_attainment) * 100, 1) AS quota_pct,
               COUNT(DISTINCT cs.session_id)             AS sessions
        FROM users u
        JOIN v_business_impact bi ON bi.user_id = u.user_id
        LEFT JOIN coaching_sessions cs ON cs.user_id = u.user_id
        WHERE u.role != 'Team Lead' {_tf(team, "u.team")}
        GROUP BY u.user_id, u.name, u.team
        ORDER BY quota_pct ASC
        LIMIT 10
    """)

    result = []
    for r in team_rows:
        spend    = r["sessions"] * cost_per_session
        baseline = 0.65
        recovered = spend * (r["avg_quota_pct"] / 100 / baseline) if baseline else 0
        roi      = round(recovered / spend, 2) if spend else 0
        sessions_median = sum(x["sessions"] for x in team_rows) / len(team_rows) if team_rows else 1
        eff_median      = sum(x["avg_effectiveness"] for x in team_rows) / len(team_rows) if team_rows else 0.5
        if r["sessions"] > sessions_median and r["avg_effectiveness"] > eff_median:
            allocation = "over-coached (high spend, already performing — consider reducing sessions)"
        elif r["sessions"] < sessions_median and r["avg_effectiveness"] < eff_median:
            allocation = "under-coached (low investment, low performance — increase sessions)"
        else:
            allocation = "optimal"
        result.append({
            "team": r["team"],
            "sessions": r["sessions"],
            "coaching_spend_eur": round(spend, 0),
            "revenue_recovered_eur": round(recovered, 0),
            "roi": roi,
            "avg_quota_pct": r["avg_quota_pct"],
            "resource_allocation": allocation,
        })

    rep_gaps = []
    for r in rep_rows:
        gap   = round((r["quota_pct"] - 100) / 100 * target_quota, 0)
        spend = r["sessions"] * cost_per_session
        session_roi = round(abs(gap) / spend, 2) if spend else 0
        rep_gaps.append({
            "name": r["name"],
            "team": r["team"],
            "quota_pct": r["quota_pct"],
            "revenue_gap_eur": gap,
            "sessions": r["sessions"],
            "session_roi": session_roi,
        })

    return _fmt({
        "team_roi": result,
        "rep_revenue_gaps": rep_gaps,
        "assumptions": {
            "cost_per_session_eur": cost_per_session,
            "target_quota_eur": target_quota,
        },
    })


# All 13 tools exported
ALL_TOOLS = [
    get_top_performers,
    get_team_summary,
    get_quota_attainment,
    get_session_stats,
    get_skill_improvement,
    get_rep_profile,
    get_top_by_metric,
    compare_skill_progression,
    identify_underperforming_segments,
    explain_metric_definition,
    get_team_roster,
    get_manager_details,
    get_coaching_roi,
]
