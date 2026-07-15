"""Apply version-controlled metric views to the CoachSphere database."""
import os
import sqlite3

DB = os.path.join(os.environ.get('TEMP', '/tmp'), 'coachsphere.db')

VIEWS = [
    # ── 1. Session Engagement Score ──────────────────────────────────────
    """
    CREATE VIEW IF NOT EXISTS v_session_engagement AS
    SELECT
        u.user_id,
        u.name,
        u.team,
        strftime('%Y-%m', cs.scheduled_at) AS period_month,
        COUNT(*) AS sessions_scheduled,
        SUM(CASE WHEN cs.status = 'completed' THEN 1 ELSE 0 END) AS sessions_completed,
        ROUND(AVG(CASE WHEN cs.status = 'completed' THEN cs.duration_minutes END), 1) AS avg_duration_min,
        SUM(CASE WHEN sf.feedback_id IS NOT NULL THEN 1 ELSE 0 END) AS feedback_submitted,
        ROUND(
            (CAST(SUM(CASE WHEN cs.status='completed' THEN 1 ELSE 0 END) AS REAL) / COUNT(*)) * 0.5
          + (COALESCE(AVG(CASE WHEN cs.status='completed' THEN cs.duration_minutes END), 0) / 45.0) * 0.3
          + (CAST(SUM(CASE WHEN sf.feedback_id IS NOT NULL THEN 1 ELSE 0 END) AS REAL) / COUNT(*)) * 0.2
        , 3) AS engagement_score
    FROM coaching_sessions cs
    JOIN users u ON cs.user_id = u.user_id
    LEFT JOIN session_feedback sf ON cs.session_id = sf.session_id
    GROUP BY u.user_id, period_month
    """,

    # ── 2. Skill Progression ─────────────────────────────────────────────
    """
    CREATE VIEW IF NOT EXISTS v_skill_progression AS
    SELECT
        sa.user_id,
        u.name,
        u.team,
        strftime('%Y-%m', sa.assessed_at) AS period_month,
        ROUND(AVG(sa.communication), 2)      AS communication,
        ROUND(AVG(sa.product_knowledge), 2)  AS product_knowledge,
        ROUND(AVG(sa.objection_handling), 2) AS objection_handling,
        ROUND(AVG(sa.closing_technique), 2)  AS closing_technique,
        ROUND(AVG(sa.active_listening), 2)   AS active_listening,
        ROUND(AVG(sa.overall_score), 2)      AS avg_overall_score,
        COUNT(*)                             AS assessments_count
    FROM skill_assessments sa
    JOIN users u ON sa.user_id = u.user_id
    GROUP BY sa.user_id, period_month
    """,

    # ── 3. Communication Quality ─────────────────────────────────────────
    """
    CREATE VIEW IF NOT EXISTS v_communication_quality AS
    SELECT
        sf.user_id,
        u.name,
        u.team,
        strftime('%Y-%m', sf.given_at) AS period_month,
        ROUND(AVG(sf.engagement_score), 2)  AS avg_engagement,
        ROUND(AVG(sf.clarity_score), 2)     AS avg_clarity,
        ROUND(AVG(sf.confidence_score), 2)  AS avg_confidence,
        ROUND(AVG(sf.overall_score), 2)     AS communication_quality_score,
        COUNT(*) AS feedback_count
    FROM session_feedback sf
    JOIN users u ON sf.user_id = u.user_id
    GROUP BY sf.user_id, period_month
    """,

    # ── 4. Business Impact Index ─────────────────────────────────────────
    """
    CREATE VIEW IF NOT EXISTS v_business_impact AS
    SELECT
        bm.user_id,
        u.name,
        u.team,
        bm.period_month,
        bm.deals_closed,
        bm.win_rate,
        bm.avg_deal_size,
        bm.pipeline_value,
        bm.quota_attainment,
        bm.sessions_completed,
        ROUND(bm.quota_attainment * 0.6 + bm.win_rate * 0.4, 3) AS business_impact_index
    FROM business_metrics bm
    JOIN users u ON bm.user_id = u.user_id
    """,

    # ── 5. Coaching Effectiveness (composite) ────────────────────────────
    """
    CREATE VIEW IF NOT EXISTS v_coaching_effectiveness AS
    SELECT
        se.user_id,
        se.name,
        se.team,
        se.period_month,
        se.engagement_score,
        sp.avg_overall_score  AS skill_score,
        cq.communication_quality_score,
        bi.business_impact_index,
        ROUND(
            COALESCE(sp.avg_overall_score / 5.0, 0) * 0.35
          + COALESCE(se.engagement_score, 0)        * 0.35
          + COALESCE(bi.business_impact_index, 0)   * 0.30
        , 3) AS coaching_effectiveness_score
    FROM v_session_engagement se
    LEFT JOIN v_skill_progression   sp ON se.user_id = sp.user_id AND se.period_month = sp.period_month
    LEFT JOIN v_communication_quality cq ON se.user_id = cq.user_id AND se.period_month = cq.period_month
    LEFT JOIN v_business_impact     bi ON se.user_id = bi.user_id AND se.period_month = bi.period_month
    """,

    # ── 6. Team Summary ──────────────────────────────────────────────────
    """
    CREATE VIEW IF NOT EXISTS v_team_summary AS
    SELECT
        team,
        period_month,
        COUNT(DISTINCT user_id)                     AS active_reps,
        ROUND(AVG(engagement_score), 3)             AS avg_engagement,
        ROUND(AVG(coaching_effectiveness_score), 3) AS avg_effectiveness
    FROM v_coaching_effectiveness
    GROUP BY team, period_month
    """,
]


def main():
    conn = sqlite3.connect(DB)
    for sql in VIEWS:
        conn.execute(sql.strip())
    conn.commit()

    views = conn.execute("SELECT name FROM sqlite_master WHERE type='view'").fetchall()
    print("Views created:")
    for v in views:
        row = conn.execute(f"SELECT COUNT(*) FROM {v[0]}").fetchone()
        print(f"  {v[0]}: {row[0]} rows")

    conn.close()
    print("\nMetrics layer ready.")


if __name__ == '__main__':
    main()
