"""
CoachSphere – Data Generation Script
Generates realistic coaching session data for a fictional AI sales coaching platform.
"""

import sqlite3
import random
import numpy as np
from datetime import datetime, timedelta
from faker import Faker
import os

fake = Faker()
random.seed(42)
np.random.seed(42)

DB_PATH = os.path.join(os.environ.get('TEMP', os.path.expanduser('~')), 'coachsphere.db')

TEAMS       = ['Enterprise', 'SMB', 'EMEA', 'APAC']
REGIONS     = {'Enterprise': 'Germany', 'SMB': 'Germany', 'EMEA': 'UK', 'APAC': 'Singapore'}
SCENARIOS   = ['Cold Call', 'Discovery Call', 'Product Demo',
                'Objection Handling', 'Closing Negotiation', 'Follow-up Call']
ROLES       = ['Sales Development Rep', 'Sales Rep', 'Senior Sales Rep', 'Account Executive']
SKILL_NAMES = ['communication', 'product_knowledge', 'objection_handling',
               'closing_technique', 'active_listening']

START_DATE  = datetime(2024, 1, 1)
END_DATE    = datetime(2024, 6, 30)


def random_date(start, end):
    return start + timedelta(seconds=random.randint(0, int((end - start).total_seconds())))


def trending_score(base, month_index, noise=0.08):
    """Score that trends upward over months (coaching effect)."""
    trend = base + (month_index * 0.04)
    return float(np.clip(np.random.normal(trend, noise), 1.0, 5.0))


def create_schema(conn):
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        user_id       INTEGER PRIMARY KEY,
        name          TEXT NOT NULL,
        email         TEXT UNIQUE NOT NULL,
        role          TEXT NOT NULL,
        team          TEXT NOT NULL,
        region        TEXT NOT NULL,
        hire_date     TEXT NOT NULL,
        manager_id    INTEGER
    );

    CREATE TABLE IF NOT EXISTS coaching_sessions (
        session_id      INTEGER PRIMARY KEY,
        user_id         INTEGER NOT NULL,
        session_type    TEXT NOT NULL,
        scenario        TEXT NOT NULL,
        scheduled_at    TEXT NOT NULL,
        started_at      TEXT,
        completed_at    TEXT,
        duration_minutes INTEGER,
        status          TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    );

    CREATE TABLE IF NOT EXISTS skill_assessments (
        assessment_id          INTEGER PRIMARY KEY,
        session_id             INTEGER NOT NULL,
        user_id                INTEGER NOT NULL,
        assessed_at            TEXT NOT NULL,
        communication          REAL NOT NULL,
        product_knowledge      REAL NOT NULL,
        objection_handling     REAL NOT NULL,
        closing_technique      REAL NOT NULL,
        active_listening       REAL NOT NULL,
        overall_score          REAL NOT NULL,
        FOREIGN KEY (session_id) REFERENCES coaching_sessions(session_id)
    );

    CREATE TABLE IF NOT EXISTS session_feedback (
        feedback_id        INTEGER PRIMARY KEY,
        session_id         INTEGER NOT NULL,
        user_id            INTEGER NOT NULL,
        given_at           TEXT NOT NULL,
        engagement_score   REAL NOT NULL,
        clarity_score      REAL NOT NULL,
        confidence_score   REAL NOT NULL,
        overall_score      REAL NOT NULL,
        FOREIGN KEY (session_id) REFERENCES coaching_sessions(session_id)
    );

    CREATE TABLE IF NOT EXISTS business_metrics (
        metric_id         INTEGER PRIMARY KEY,
        user_id           INTEGER NOT NULL,
        period_month      TEXT NOT NULL,
        deals_closed      INTEGER NOT NULL,
        pipeline_value    REAL NOT NULL,
        win_rate          REAL NOT NULL,
        avg_deal_size     REAL NOT NULL,
        quota_attainment  REAL NOT NULL,
        sessions_completed INTEGER NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    );

    CREATE TABLE IF NOT EXISTS metric_definitions (
        metric_name   TEXT PRIMARY KEY,
        display_name  TEXT NOT NULL,
        description   TEXT NOT NULL,
        formula       TEXT NOT NULL,
        unit          TEXT NOT NULL,
        version       TEXT NOT NULL,
        created_at    TEXT NOT NULL
    );
    """)
    conn.commit()


def seed_users(conn):
    managers = []
    users = []
    uid = 1
    for team in TEAMS:
        mgr = (uid, fake.name(), fake.email(), 'Team Lead', team,
               REGIONS[team], (START_DATE - timedelta(days=random.randint(400, 800))).date().isoformat(), None)
        managers.append(mgr)
        users.append(mgr)
        uid += 1
        for _ in range(10):
            role = random.choice(ROLES)
            hire = (START_DATE - timedelta(days=random.randint(60, 600))).date().isoformat()
            users.append((uid, fake.name(), fake.email(), role, team,
                          REGIONS[team], hire, mgr[0]))
            uid += 1
    conn.executemany("INSERT OR IGNORE INTO users VALUES (?,?,?,?,?,?,?,?)", users)
    conn.commit()
    return [u[0] for u in users if u[3] != 'Team Lead']


def seed_sessions(conn, rep_ids):
    sessions, assessments, feedbacks = [], [], []
    sid = 1
    aid = 1
    fid = 1

    # base skill scores per user (varying starting points)
    base_scores = {uid: {s: round(random.uniform(2.2, 3.5), 2) for s in SKILL_NAMES} for uid in rep_ids}

    for uid in rep_ids:
        for m in range(6):
            month_dt = datetime(2024, m + 1, 1)
            num_sessions = random.randint(6, 14)
            for _ in range(num_sessions):
                sched = random_date(month_dt, month_dt + timedelta(days=28))
                completed = random.random() > 0.15  # 85% completion rate
                started_at  = sched + timedelta(minutes=random.randint(0, 5)) if completed or random.random() > 0.4 else None
                completed_at = (started_at + timedelta(minutes=random.randint(18, 45))) if completed and started_at else None
                duration     = int((completed_at - started_at).total_seconds() / 60) if completed and started_at and completed_at else None
                status       = 'completed' if completed else ('started' if started_at else 'missed')
                scenario     = random.choice(SCENARIOS)

                sessions.append((sid, uid, 'AI Role-play', scenario,
                                 sched.isoformat(),
                                 started_at.isoformat() if started_at else None,
                                 completed_at.isoformat() if completed_at else None,
                                 duration, status))

                if completed:
                    bs = base_scores[uid]
                    scores = {s: trending_score(bs[s], m) for s in SKILL_NAMES}
                    overall = round(sum(scores.values()) / len(scores), 2)
                    assessments.append((aid, sid, uid, completed_at.isoformat(),
                                        scores['communication'], scores['product_knowledge'],
                                        scores['objection_handling'], scores['closing_technique'],
                                        scores['active_listening'], overall))
                    aid += 1

                    eng   = trending_score(random.uniform(2.8, 4.0), m, 0.1)
                    clar  = trending_score(random.uniform(2.5, 3.8), m, 0.1)
                    conf  = trending_score(random.uniform(2.6, 3.9), m, 0.1)
                    fov   = round((eng + clar + conf) / 3, 2)
                    feedbacks.append((fid, sid, uid, completed_at.isoformat(),
                                      round(eng, 2), round(clar, 2), round(conf, 2), fov))
                    fid += 1

                sid += 1

    conn.executemany("INSERT OR IGNORE INTO coaching_sessions VALUES (?,?,?,?,?,?,?,?,?)", sessions)
    conn.executemany("INSERT OR IGNORE INTO skill_assessments VALUES (?,?,?,?,?,?,?,?,?,?)", assessments)
    conn.executemany("INSERT OR IGNORE INTO session_feedback VALUES (?,?,?,?,?,?,?,?)", feedbacks)
    conn.commit()
    return base_scores


def seed_business_metrics(conn, rep_ids):
    rows = []
    mid = 1
    for uid in rep_ids:
        base_deals    = random.randint(2, 7)
        base_winrate  = random.uniform(0.22, 0.48)
        base_deal_sz  = random.uniform(8000, 45000)
        for m in range(6):
            month_label   = f"2024-{m+1:02d}"
            coaching_boost = 1 + (m * 0.025)
            deals         = max(1, int(np.random.normal(base_deals * coaching_boost, 1)))
            win_rate      = float(np.clip(np.random.normal(base_winrate * coaching_boost, 0.04), 0.1, 0.85))
            avg_sz        = float(np.random.normal(base_deal_sz * (1 + m*0.015), 1200))
            pipeline      = round(avg_sz * random.randint(8, 20), 2)
            quota         = float(np.clip(np.random.normal(0.68 + m*0.04, 0.08), 0.3, 1.15))
            completed_cnt = random.randint(5, 13)
            rows.append((mid, uid, month_label, deals, round(pipeline, 2),
                         round(win_rate, 3), round(avg_sz, 2), round(quota, 3), completed_cnt))
            mid += 1
    conn.executemany("INSERT OR IGNORE INTO business_metrics VALUES (?,?,?,?,?,?,?,?,?)", rows)
    conn.commit()


def seed_metric_definitions(conn):
    defs = [
        ('session_engagement_score',
         'Session Engagement Score',
         'Composite score combining session completion rate, average session duration, and feedback submission rate per user per month.',
         '(completions / scheduled) * 0.5 + (avg_duration / 45) * 0.3 + (feedback_rate) * 0.2',
         'score (0–1)', 'v1.2', datetime.now().isoformat()),
        ('skill_progression_rate',
         'Skill Progression Rate',
         'Month-over-month percentage improvement in average skill assessment score across all five competency dimensions.',
         '(avg_score_this_month - avg_score_last_month) / avg_score_last_month * 100',
         '% change', 'v1.1', datetime.now().isoformat()),
        ('communication_quality_score',
         'Communication Quality Score',
         'Average of AI-evaluated communication, clarity, and confidence sub-scores from session feedback.',
         '(communication + clarity + confidence) / 3',
         'score (1–5)', 'v1.0', datetime.now().isoformat()),
        ('business_impact_index',
         'Business Impact Index',
         'Weighted composite of quota attainment and win rate improvement, normalised against team average.',
         '(quota_attainment * 0.6 + win_rate_delta * 0.4) / team_avg',
         'index (0–2)', 'v1.3', datetime.now().isoformat()),
        ('coaching_effectiveness_score',
         'Coaching Effectiveness Score',
         'Overall coaching ROI metric combining skill progression, engagement, and business impact per user.',
         '(skill_progression * 0.4) + (engagement_score * 0.35) + (business_impact * 0.25)',
         'score (0–5)', 'v2.0', datetime.now().isoformat()),
    ]
    conn.executemany("INSERT OR IGNORE INTO metric_definitions VALUES (?,?,?,?,?,?,?)", defs)
    conn.commit()


def main():
    conn = sqlite3.connect(DB_PATH)
    print("Creating schema...")
    create_schema(conn)
    print("Seeding users...")
    rep_ids = seed_users(conn)
    print(f"  → {len(rep_ids)} sales reps created")
    print("Seeding sessions, assessments, feedback...")
    seed_sessions(conn, rep_ids)
    print("Seeding business metrics...")
    seed_business_metrics(conn, rep_ids)
    print("Seeding metric definitions...")
    seed_metric_definitions(conn)
    # summary
    for tbl in ['users','coaching_sessions','skill_assessments','session_feedback','business_metrics']:
        c = conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
        print(f"  {tbl}: {c} rows")
    conn.close()
    print(f"\nDatabase created at: {DB_PATH}")


if __name__ == '__main__':
    main()
