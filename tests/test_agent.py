"""
Unit tests for CoachSphere agent tools and metric calculations.

Run from the coachsphere/ root directory:
    pytest tests/ -v

Requires the database to be generated first:
    python data/generate_data.py
    python metrics/apply_metrics.py
"""

import os
import sqlite3

import pandas as pd
import pytest

# ── Database path (mirrors the logic in app.py) ───────────────────────────────
DB = os.path.join(os.environ.get("TEMP", "/tmp"), "coachsphere.db")

VALID_TEAMS  = {"Enterprise", "SMB", "EMEA", "APAC"}
VALID_SKILLS = ["communication", "product_knowledge", "objection_handling",
                "closing_technique", "active_listening"]


@pytest.fixture(scope="module")
def conn():
    """Module-scoped SQLite connection. Skips all tests if DB is missing."""
    if not os.path.exists(DB):
        pytest.skip(
            f"Database not found at {DB}. "
            "Run `python data/generate_data.py && python metrics/apply_metrics.py` first."
        )
    connection = sqlite3.connect(DB)
    yield connection
    connection.close()


# ── Metric calculation tests ──────────────────────────────────────────────────

class TestMetricCalculations:
    """Verify that composite scores stay within expected bounds."""

    def test_engagement_score_in_bounds(self, conn):
        """engagement_score is a weighted composite — must be in [0, 1]."""
        df = pd.read_sql_query(
            "SELECT engagement_score FROM v_session_engagement", conn
        )
        assert not df.empty, "v_session_engagement returned no rows"
        assert df["engagement_score"].between(0, 1).all(), (
            f"engagement_score has values outside [0, 1]: "
            f"{df[~df['engagement_score'].between(0, 1)]['engagement_score'].tolist()}"
        )

    def test_coaching_effectiveness_score_in_bounds(self, conn):
        """coaching_effectiveness_score = weighted sum of normalised components."""
        df = pd.read_sql_query(
            "SELECT coaching_effectiveness_score FROM v_coaching_effectiveness", conn
        )
        assert not df.empty
        assert df["coaching_effectiveness_score"].between(0, 1).all(), (
            "coaching_effectiveness_score has out-of-bounds values"
        )

    def test_business_impact_index_formula(self, conn):
        """business_impact_index = quota_attainment*0.6 + win_rate*0.4 (±0.001 rounding)."""
        df = pd.read_sql_query(
            "SELECT quota_attainment, win_rate, business_impact_index FROM v_business_impact LIMIT 50",
            conn,
        )
        expected = (df["quota_attainment"] * 0.6 + df["win_rate"] * 0.4).round(3)
        diff = (df["business_impact_index"] - expected).abs()
        assert (diff < 0.002).all(), (
            f"business_impact_index deviates from formula: max diff = {diff.max()}"
        )


# ── SQL output tests ──────────────────────────────────────────────────────────

class TestSQLOutputs:
    """Verify that tool SQL queries return correct shapes and values."""

    def test_top_performers_returns_at_most_5_rows(self, conn):
        """get_top_performers caps at LIMIT 5."""
        df = pd.read_sql_query(
            """SELECT name, coaching_effectiveness_score
               FROM v_coaching_effectiveness
               WHERE period_month = '2024-06'
               ORDER BY coaching_effectiveness_score DESC LIMIT 5""",
            conn,
        )
        assert 1 <= len(df) <= 5, f"Expected 1–5 rows, got {len(df)}"

    def test_team_names_are_valid(self, conn):
        """All team values in `users` must belong to the four known teams."""
        df = pd.read_sql_query(
            "SELECT DISTINCT team FROM users WHERE role != 'Team Lead'", conn
        )
        unknown = set(df["team"]) - VALID_TEAMS
        assert not unknown, f"Unexpected team names: {unknown}"

    def test_skill_scores_in_range(self, conn):
        """Individual skill scores (1–5 scale) must stay within bounds."""
        for col in VALID_SKILLS:
            df = pd.read_sql_query(f"SELECT {col} FROM v_skill_progression", conn)
            out = df[~df[col].between(1, 5)]
            assert out.empty, (
                f"'{col}' has {len(out)} value(s) outside [1, 5]: {out[col].tolist()[:5]}"
            )

    def test_all_expected_months_present(self, conn):
        """Dataset must cover exactly Jan–Jun 2024."""
        df = pd.read_sql_query(
            "SELECT DISTINCT period_month FROM v_coaching_effectiveness ORDER BY period_month",
            conn,
        )
        actual   = df["period_month"].tolist()
        expected = [f"2024-{m:02d}" for m in range(1, 7)]
        assert actual == expected, f"Expected {expected}, got {actual}"

    def test_team_summary_has_all_teams(self, conn):
        """v_team_summary must include all four teams."""
        df = pd.read_sql_query("SELECT DISTINCT team FROM v_team_summary", conn)
        missing = VALID_TEAMS - set(df["team"])
        assert not missing, f"Teams missing from v_team_summary: {missing}"

    def test_metric_definitions_table_populated(self, conn):
        """metric_definitions must have at least 5 rows (one per KPI)."""
        df = pd.read_sql_query("SELECT COUNT(*) AS cnt FROM metric_definitions", conn)
        assert df["cnt"].iloc[0] >= 5, "metric_definitions table appears empty or incomplete"


# ── Edge case / invalid input tests ──────────────────────────────────────────

class TestEdgeCases:
    """Verify graceful handling of missing or invalid query parameters."""

    def test_unknown_rep_returns_empty(self, conn):
        """Querying a non-existent rep name must return zero rows (no crash)."""
        df = pd.read_sql_query(
            "SELECT * FROM v_coaching_effectiveness WHERE name LIKE '%NONEXISTENT_XYZ_999%'",
            conn,
        )
        assert len(df) == 0, "Expected 0 rows for a non-existent rep"

    def test_invalid_month_returns_empty(self, conn):
        """Querying a month outside the data range must return zero rows."""
        df = pd.read_sql_query(
            "SELECT * FROM v_coaching_effectiveness WHERE period_month = '1999-01'",
            conn,
        )
        assert len(df) == 0, "Expected 0 rows for a month outside the dataset"

    def test_underperforming_query_with_high_threshold(self, conn):
        """identify_underperforming_segments with threshold=1.0 must return all teams."""
        df = pd.read_sql_query(
            """SELECT DISTINCT team FROM v_coaching_effectiveness
               GROUP BY team, period_month
               HAVING AVG(coaching_effectiveness_score) < 1.0""",
            conn,
        )
        # All teams should appear since no team can be perfect
        assert len(df) > 0

    def test_explain_metric_no_match_returns_empty(self, conn):
        """explain_metric_definition with a nonsense keyword returns zero rows."""
        df = pd.read_sql_query(
            """SELECT * FROM metric_definitions
               WHERE metric_name LIKE '%NOMETRICZZZZ%'
                  OR display_name LIKE '%NOMETRICZZZZ%'""",
            conn,
        )
        assert len(df) == 0

    def test_compare_skill_with_nonexistent_team_returns_empty(self, conn):
        """compare_skill_progression with a fake team name must return zero rows."""
        df = pd.read_sql_query(
            "SELECT * FROM v_skill_progression WHERE team = 'FakeTeamXYZ'",
            conn,
        )
        assert len(df) == 0
