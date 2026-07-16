"""
CoachSphere Analytics Dashboard
Fictional AI Sales Coaching Platform – Internal Analytics Layer
"""

import sqlite3
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

import os
import sys

# Load API key — Streamlit Cloud secrets take priority, then .env for local dev
try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except Exception:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
    GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')

from groq import Groq

import subprocess

# DB path — use /tmp on cloud, %TEMP% locally
DB = os.path.join(os.environ.get('TEMP', '/tmp'), 'coachsphere.db')
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

def _db_ready():
    """Returns True if DB exists and has the users table populated."""
    try:
        conn = sqlite3.connect(DB)
        count = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='users'"
        ).fetchone()[0]
        conn.close()
        return count > 0
    except Exception:
        return False

if not _db_ready():
    subprocess.run([sys.executable, os.path.join(ROOT, 'data', 'generate_data.py')], check=True)
    subprocess.run([sys.executable, os.path.join(ROOT, 'metrics', 'apply_metrics.py')], check=True)

st.set_page_config(
    page_title="CoachSphere Analytics",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Dark theme overrides ──────────────────────────────────────────────────────
st.markdown("""
<style>
[data-testid="stSidebar"] { background-color: #0f172a; }
[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
.metric-card {
    background: #ffffff; border-radius: 12px; padding: 18px 22px;
    border: 1px solid #cbd5e1; text-align: center;
}
.metric-val { font-size: 2rem; font-weight: 700; color: #000000; }
.metric-lbl { font-size: 0.78rem; color: #000000; margin-top: 4px; text-transform: uppercase; letter-spacing: 0.05em; }
.metric-delta { font-size: 0.85rem; margin-top: 6px; }
.section-title { font-size: 1.1rem; font-weight: 600; color: #000000; margin: 18px 0 10px; }
footer { visibility: hidden; }
#MainMenu { visibility: hidden; }
div[class*="viewerBadge"] { display: none !important; }
.stDeployButton { display: none !important; }
[data-testid="collapsedControl"] { display: flex !important; visibility: visible !important; }
</style>
""", unsafe_allow_html=True)

COLORS = ['#38bdf8','#818cf8','#34d399','#f472b6','#fb923c']
TEAM_COLORS = {'Enterprise':'#38bdf8','SMB':'#818cf8','EMEA':'#34d399','APAC':'#f472b6'}

@st.cache_data
def query(sql, params=()):
    conn = sqlite3.connect(DB)
    df = pd.read_sql_query(sql, conn, params=params)
    conn.close()
    return df

def fmt_score(v): return f"{v:.2f}"
def fmt_pct(v):   return f"{v*100:.1f}%"

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:4px;">
        <svg width="48" height="48" viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg">
            <circle cx="24" cy="24" r="23" fill="#38bdf8" stroke="#0ea5e9" stroke-width="1.5"/>
            <rect x="10" y="28" width="6" height="10" rx="1.5" fill="white"/>
            <rect x="19" y="22" width="6" height="16" rx="1.5" fill="white"/>
            <rect x="28" y="16" width="6" height="22" rx="1.5" fill="white"/>
            <polyline points="13,22 22,16 31,10" stroke="white" stroke-width="2.2" stroke-linecap="round" fill="none"/>
            <circle cx="13" cy="22" r="2" fill="white"/>
            <circle cx="22" cy="16" r="2" fill="white"/>
            <circle cx="31" cy="10" r="2" fill="white"/>
        </svg>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("## CoachSphere")
    st.markdown("*AI Sales Coaching Analytics*")
    st.divider()
    page = st.radio("Navigation", [
        "📊 Overview",
        "👥 Team Analytics",
        "🧠 Skill Progression",
        "📅 Session Insights",
        "🔍 Rep Deep Dive",
        "📋 Metric Definitions",
        "🤖 AI Assistant",
    ])
    st.divider()
    teams_all = query("SELECT DISTINCT team FROM users WHERE role != 'Team Lead'")['team'].tolist()
    sel_teams = st.multiselect("Filter by Team", teams_all, default=teams_all)
    months_all = query("SELECT DISTINCT period_month FROM v_coaching_effectiveness ORDER BY period_month")['period_month'].tolist()
    sel_month = st.selectbox("Reference Month", months_all, index=len(months_all)-1)

team_filter = "','".join(sel_teams) if sel_teams else "''"

# ═══════════════════════════════════════════════════════════════════════════════
if page == "📊 Overview":
    st.markdown("# 📊 Platform Overview")
    st.markdown(f"**Platform metrics · {sel_month}** — all coaching activity across {len(sel_teams)} teams")

    # KPI cards
    kpi = query(f"""
        SELECT
          ROUND(AVG(engagement_score),3)             AS avg_engagement,
          ROUND(AVG(coaching_effectiveness_score),3) AS avg_effectiveness,
          ROUND(AVG(skill_score),3)                  AS avg_skill,
          COUNT(DISTINCT user_id)                    AS active_reps
        FROM v_coaching_effectiveness
        WHERE period_month = ? AND team IN ('{team_filter}')
    """, (sel_month,)).iloc[0]

    prev_month = months_all[months_all.index(sel_month)-1] if months_all.index(sel_month) > 0 else sel_month
    kpi_prev = query(f"""
        SELECT ROUND(AVG(coaching_effectiveness_score),3) AS eff_prev
        FROM v_coaching_effectiveness
        WHERE period_month = ? AND team IN ('{team_filter}')
    """, (prev_month,)).iloc[0]

    eff_delta = float(kpi['avg_effectiveness']) - float(kpi_prev['eff_prev'])

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""<div class="metric-card">
            <div class="metric-val">{fmt_score(kpi['avg_engagement'])}</div>
            <div class="metric-lbl">Avg Engagement Score</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        arrow = "↑" if eff_delta >= 0 else "↓"
        color = "#34d399" if eff_delta >= 0 else "#f87171"
        st.markdown(f"""<div class="metric-card">
            <div class="metric-val">{fmt_score(kpi['avg_effectiveness'])}</div>
            <div class="metric-lbl">Coaching Effectiveness</div>
            <div class="metric-delta" style="color:{color}">{arrow} {abs(eff_delta):.3f} vs prev month</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class="metric-card">
            <div class="metric-val">{fmt_score(kpi['avg_skill'])}</div>
            <div class="metric-lbl">Avg Skill Score (1–5)</div>
        </div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""<div class="metric-card">
            <div class="metric-val">{int(kpi['active_reps'])}</div>
            <div class="metric-lbl">Active Reps</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")
    col_l, col_r = st.columns(2)

    with col_l:
        st.markdown('<div class="section-title">Coaching Effectiveness Over Time</div>', unsafe_allow_html=True)
        trend = query(f"""
            SELECT period_month, team,
                   ROUND(AVG(coaching_effectiveness_score),3) AS effectiveness
            FROM v_coaching_effectiveness
            WHERE team IN ('{team_filter}')
            GROUP BY period_month, team ORDER BY period_month
        """)
        fig = px.line(trend, x='period_month', y='effectiveness', color='team',
                      color_discrete_map=TEAM_COLORS,
                      labels={'period_month':'Month','effectiveness':'Score','team':'Team'},
                      markers=True)
        fig.update_layout(plot_bgcolor='#0f172a', paper_bgcolor='rgba(255,255,255,0)',
                          font_color='#1e293b', legend_title_text='',
                          xaxis=dict(gridcolor='#334155'), yaxis=dict(gridcolor='#334155'))
        st.plotly_chart(fig, use_container_width=True)

    with col_r:
        st.markdown('<div class="section-title">Session Completion Rate by Team</div>', unsafe_allow_html=True)
        comp = query(f"""
            SELECT u.team,
                   SUM(sessions_completed) AS completed,
                   SUM(sessions_scheduled) AS scheduled,
                   ROUND(CAST(SUM(sessions_completed) AS REAL)/SUM(sessions_scheduled)*100,1) AS pct
            FROM v_session_engagement se
            JOIN users u ON se.user_id=u.user_id
            WHERE se.period_month=? AND u.team IN ('{team_filter}')
            GROUP BY u.team
        """, (sel_month,))
        fig2 = px.bar(comp, x='team', y='pct', color='team',
                      color_discrete_map=TEAM_COLORS, text='pct',
                      labels={'pct':'Completion %','team':'Team'})
        fig2.update_traces(texttemplate='%{text}%', textposition='outside')
        fig2.update_layout(plot_bgcolor='#0f172a', paper_bgcolor='rgba(255,255,255,0)',
                           font_color='#1e293b', showlegend=False,
                           xaxis=dict(gridcolor='#334155'), yaxis=dict(gridcolor='#334155', range=[0,105]))
        st.plotly_chart(fig2, use_container_width=True)

    col_l2, col_r2 = st.columns(2)
    with col_l2:
        st.markdown('<div class="section-title">Business Impact: Quota Attainment Trend</div>', unsafe_allow_html=True)
        quota = query(f"""
            SELECT period_month, team, ROUND(AVG(quota_attainment)*100,1) AS quota_pct
            FROM v_business_impact
            WHERE team IN ('{team_filter}')
            GROUP BY period_month, team ORDER BY period_month
        """)
        fig3 = px.area(quota, x='period_month', y='quota_pct', color='team',
                       color_discrete_map=TEAM_COLORS,
                       labels={'quota_pct':'Quota Attainment %','period_month':'Month'})
        fig3.update_layout(plot_bgcolor='#0f172a', paper_bgcolor='rgba(255,255,255,0)',
                           font_color='#1e293b', xaxis=dict(gridcolor='#334155'),
                           yaxis=dict(gridcolor='#334155'))
        st.plotly_chart(fig3, use_container_width=True)

    with col_r2:
        st.markdown('<div class="section-title">Win Rate vs Sessions Completed</div>', unsafe_allow_html=True)
        scatter = query(f"""
            SELECT bi.user_id, u.name, bi.team,
                   AVG(bi.win_rate)*100 AS avg_win_rate,
                   SUM(bi.sessions_completed) AS total_sessions
            FROM v_business_impact bi
            JOIN users u ON bi.user_id=u.user_id
            WHERE bi.team IN ('{team_filter}')
            GROUP BY bi.user_id
        """)
        fig4 = px.scatter(scatter, x='total_sessions', y='avg_win_rate', color='team',
                          color_discrete_map=TEAM_COLORS, hover_name='name',
                          trendline='ols',
                          labels={'total_sessions':'Total Sessions','avg_win_rate':'Avg Win Rate %'})
        fig4.update_layout(plot_bgcolor='#0f172a', paper_bgcolor='rgba(255,255,255,0)',
                           font_color='#1e293b', xaxis=dict(gridcolor='#334155'),
                           yaxis=dict(gridcolor='#334155'))
        st.plotly_chart(fig4, use_container_width=True)

# ═══════════════════════════════════════════════════════════════════════════════
elif page == "👥 Team Analytics":
    st.markdown("# 👥 Team Analytics")
    team_sum = query(f"""
        SELECT ts.team, ts.period_month, ts.avg_engagement, ts.avg_effectiveness,
               ts.active_reps
        FROM v_team_summary ts
        WHERE ts.team IN ('{team_filter}')
        ORDER BY ts.period_month, ts.team
    """)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="section-title">Avg Effectiveness by Team & Month</div>', unsafe_allow_html=True)
        fig = px.bar(team_sum, x='period_month', y='avg_effectiveness', color='team',
                     barmode='group', color_discrete_map=TEAM_COLORS,
                     labels={'avg_effectiveness':'Effectiveness Score','period_month':'Month'})
        fig.update_layout(plot_bgcolor='#0f172a', paper_bgcolor='rgba(255,255,255,0)',
                          font_color='#1e293b', xaxis=dict(gridcolor='#334155'),
                          yaxis=dict(gridcolor='#334155'))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown('<div class="section-title">Team Engagement Heatmap</div>', unsafe_allow_html=True)
        pivot = team_sum.pivot(index='team', columns='period_month', values='avg_engagement')
        fig2 = go.Figure(go.Heatmap(
            z=pivot.values, x=pivot.columns.tolist(), y=pivot.index.tolist(),
            colorscale='Blues', text=pivot.values.round(3),
            texttemplate='%{text}', showscale=True,
            colorbar=dict(title='Score')
        ))
        fig2.update_layout(paper_bgcolor='rgba(255,255,255,0)', font_color='#1e293b',
                           xaxis_title='Month', yaxis_title='Team')
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown('<div class="section-title">Top Performers This Month</div>', unsafe_allow_html=True)
    top = query(f"""
        SELECT ce.name, ce.team,
               ROUND(ce.coaching_effectiveness_score,3) AS effectiveness,
               ROUND(ce.engagement_score,3) AS engagement,
               ROUND(ce.skill_score,3) AS skill_score,
               ROUND(COALESCE(bm.quota_attainment,0)*100,1) AS quota_pct
        FROM v_coaching_effectiveness ce
        LEFT JOIN business_metrics bm
            ON ce.user_id = bm.user_id
            AND bm.period_month = (
                SELECT MAX(period_month) FROM business_metrics
                WHERE user_id = ce.user_id AND period_month <= ce.period_month
            )
        WHERE ce.period_month=? AND ce.team IN ('{team_filter}')
        ORDER BY effectiveness DESC LIMIT 10
    """, (sel_month,))
    st.dataframe(top, use_container_width=True, hide_index=True,
                 column_config={
                     'effectiveness': st.column_config.ProgressColumn('Effectiveness', min_value=0, max_value=1),
                     'engagement':    st.column_config.ProgressColumn('Engagement',    min_value=0, max_value=1),
                     'quota_pct':     st.column_config.NumberColumn('Quota %', format='%.1f%%'),
                 })

# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🧠 Skill Progression":
    st.markdown("# 🧠 Skill Progression")
    skills = ['communication','product_knowledge','objection_handling','closing_technique','active_listening']

    avg_skills = query(f"""
        SELECT period_month,
               ROUND(AVG(communication),2)      AS communication,
               ROUND(AVG(product_knowledge),2)  AS product_knowledge,
               ROUND(AVG(objection_handling),2) AS objection_handling,
               ROUND(AVG(closing_technique),2)  AS closing_technique,
               ROUND(AVG(active_listening),2)   AS active_listening
        FROM v_skill_progression sp
        JOIN users u ON sp.user_id=u.user_id
        WHERE u.team IN ('{team_filter}')
        GROUP BY period_month ORDER BY period_month
    """)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="section-title">Skill Trend Over Time</div>', unsafe_allow_html=True)
        melted = avg_skills.melt('period_month', var_name='Skill', value_name='Score')
        fig = px.line(melted, x='period_month', y='Score', color='Skill', markers=True,
                      color_discrete_sequence=COLORS)
        fig.update_layout(plot_bgcolor='#0f172a', paper_bgcolor='rgba(255,255,255,0)',
                          font_color='#1e293b', yaxis=dict(range=[1,5], gridcolor='#334155'),
                          xaxis=dict(gridcolor='#334155'), legend_title_text='')
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown(f'<div class="section-title">Skill Radar – {sel_month}</div>', unsafe_allow_html=True)
        radar_row = avg_skills[avg_skills['period_month']==sel_month]
        if not radar_row.empty:
            vals = radar_row[skills].values.flatten().tolist()
            fig2 = go.Figure(go.Scatterpolar(
                r=vals + [vals[0]],
                theta=[s.replace('_',' ').title() for s in skills] + [skills[0].replace('_',' ').title()],
                fill='toself', line_color='#38bdf8', fillcolor='rgba(56,189,248,0.2)'
            ))
            fig2.update_layout(polar=dict(bgcolor='#0f172a',
                                          radialaxis=dict(range=[0,5], gridcolor='#334155'),
                                          angularaxis=dict(gridcolor='#334155')),
                                paper_bgcolor='rgba(255,255,255,0)', font_color='#1e293b', showlegend=False)
            st.plotly_chart(fig2, use_container_width=True)

    st.markdown('<div class="section-title">Month-over-Month Skill Improvement</div>', unsafe_allow_html=True)
    if len(avg_skills) >= 2:
        first = avg_skills.iloc[0][skills]
        last  = avg_skills.iloc[-1][skills]
        delta = ((last - first) / first * 100).round(1)
        dcols = st.columns(5)
        for i, sk in enumerate(skills):
            with dcols[i]:
                color = "#34d399" if delta[sk] >= 0 else "#f87171"
                st.markdown(f"""<div class="metric-card">
                    <div class="metric-val" style="color:{color}">{delta[sk]:+.1f}%</div>
                    <div class="metric-lbl">{sk.replace('_',' ').title()}</div>
                </div>""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
elif page == "📅 Session Insights":
    st.markdown("# 📅 Session Insights")

    sessions = query(f"""
        SELECT cs.scenario, cs.status,
               strftime('%Y-%m', cs.scheduled_at) AS period_month,
               u.team,
               COALESCE(cs.duration_minutes, 0) AS duration_minutes
        FROM coaching_sessions cs JOIN users u ON cs.user_id=u.user_id
        WHERE u.team IN ('{team_filter}')
    """)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="section-title">Sessions by Scenario Type</div>', unsafe_allow_html=True)
        sc_cnt = sessions.groupby('scenario')['status'].count().reset_index(name='count')
        fig = px.pie(sc_cnt, names='scenario', values='count',
                     color_discrete_sequence=COLORS, hole=0.45)
        fig.update_layout(paper_bgcolor='rgba(255,255,255,0)', font_color='#1e293b', legend_title_text='')
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown('<div class="section-title">Completion Status Distribution</div>', unsafe_allow_html=True)
        st_cnt = sessions.groupby(['period_month','status'])['duration_minutes'].count().reset_index(name='count')
        fig2 = px.bar(st_cnt, x='period_month', y='count', color='status', barmode='stack',
                      color_discrete_sequence=COLORS,
                      labels={'count':'Sessions','period_month':'Month'})
        fig2.update_layout(plot_bgcolor='#0f172a', paper_bgcolor='rgba(255,255,255,0)',
                           font_color='#1e293b', xaxis=dict(gridcolor='#334155'),
                           yaxis=dict(gridcolor='#334155'), legend_title_text='Status')
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown('<div class="section-title">Avg Session Duration by Scenario (completed only)</div>', unsafe_allow_html=True)
    dur = sessions[sessions['status']=='completed'].groupby('scenario')['duration_minutes'].mean().reset_index()
    dur.columns = ['scenario','avg_duration']
    dur = dur.sort_values('avg_duration', ascending=True)
    fig3 = px.bar(dur, x='avg_duration', y='scenario', orientation='h',
                  color='avg_duration', color_continuous_scale='Blues',
                  labels={'avg_duration':'Avg Duration (min)','scenario':'Scenario'})
    fig3.update_layout(plot_bgcolor='#0f172a', paper_bgcolor='rgba(255,255,255,0)',
                       font_color='#1e293b', coloraxis_showscale=False,
                       xaxis=dict(gridcolor='#334155'), yaxis=dict(gridcolor='#334155'))
    st.plotly_chart(fig3, use_container_width=True)

# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🔍 Rep Deep Dive":
    st.markdown("# 🔍 Rep Deep Dive")
    reps = query(f"SELECT user_id, name, team FROM users WHERE role!='Team Lead' AND team IN ('{team_filter}') ORDER BY name")
    sel_rep = st.selectbox("Select Sales Rep", reps['name'].tolist())
    uid = int(reps[reps['name']==sel_rep]['user_id'].iloc[0])

    eff = query("SELECT * FROM v_coaching_effectiveness WHERE user_id=? ORDER BY period_month", (uid,))
    bi  = query("SELECT * FROM v_business_impact WHERE user_id=? ORDER BY period_month", (uid,))
    sp  = query("SELECT * FROM v_skill_progression WHERE user_id=? ORDER BY period_month", (uid,))

    if not eff.empty:
        row = eff.iloc[-1]
        c1,c2,c3,c4 = st.columns(4)
        with c1: st.metric("Effectiveness", fmt_score(row['coaching_effectiveness_score']))
        with c2: st.metric("Engagement",    fmt_score(row['engagement_score']))
        with c3: st.metric("Skill Score",   fmt_score(row['skill_score']) if row['skill_score'] else 'N/A')
        with c4:
            bi_row = bi[bi['period_month']==sel_month]
            if not bi_row.empty:
                st.metric("Quota Attainment", fmt_pct(bi_row.iloc[0]['quota_attainment']))

    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="section-title">Coaching Effectiveness Trend</div>', unsafe_allow_html=True)
        fig = px.line(eff, x='period_month', y='coaching_effectiveness_score',
                      markers=True, color_discrete_sequence=['#38bdf8'])
        fig.update_layout(plot_bgcolor='#0f172a', paper_bgcolor='rgba(255,255,255,0)', font_color='#1e293b',
                          xaxis=dict(gridcolor='#334155'), yaxis=dict(gridcolor='#334155'))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown('<div class="section-title">Skill Radar – Latest Month</div>', unsafe_allow_html=True)
        skills = ['communication','product_knowledge','objection_handling','closing_technique','active_listening']
        if not sp.empty:
            latest = sp.iloc[-1]
            vals = [latest[s] for s in skills]
            fig2 = go.Figure(go.Scatterpolar(
                r=vals+[vals[0]],
                theta=[s.replace('_',' ').title() for s in skills]+[skills[0].replace('_',' ').title()],
                fill='toself', line_color='#818cf8', fillcolor='rgba(129,140,248,0.2)'
            ))
            fig2.update_layout(polar=dict(bgcolor='#0f172a',
                                          radialaxis=dict(range=[0,5], gridcolor='#334155'),
                                          angularaxis=dict(gridcolor='#334155')),
                                paper_bgcolor='rgba(255,255,255,0)', font_color='#1e293b', showlegend=False)
            st.plotly_chart(fig2, use_container_width=True)

    st.markdown('<div class="section-title">Business Metrics Over Time</div>', unsafe_allow_html=True)
    fig3 = make_subplots(specs=[[{"secondary_y": True}]])
    fig3.add_trace(go.Bar(x=bi['period_month'], y=bi['deals_closed'], name='Deals Closed',
                          marker_color='#38bdf8'), secondary_y=False)
    fig3.add_trace(go.Scatter(x=bi['period_month'], y=bi['win_rate']*100, name='Win Rate %',
                              mode='lines+markers', line=dict(color='#f472b6')), secondary_y=True)
    fig3.update_layout(plot_bgcolor='#0f172a', paper_bgcolor='rgba(255,255,255,0)', font_color='#1e293b',
                       xaxis=dict(gridcolor='#334155'), legend_title_text='')
    fig3.update_yaxes(gridcolor='#334155', secondary_y=False, title_text='Deals Closed')
    fig3.update_yaxes(gridcolor='#334155', secondary_y=True,  title_text='Win Rate %')
    st.plotly_chart(fig3, use_container_width=True)

# ═══════════════════════════════════════════════════════════════════════════════
elif page == "📋 Metric Definitions":
    st.markdown("# 📋 Metric Definitions")
    st.markdown("Version-controlled definitions for all CoachSphere KPIs. Updated via Git — every change is tracked.")
    defs = query("SELECT * FROM metric_definitions")
    for _, row in defs.iterrows():
        with st.expander(f"**{row['display_name']}** — `{row['metric_name']}` · version {row['version']}"):
            st.markdown(f"**Description:** {row['description']}")
            st.code(row['formula'], language='sql')
            col1, col2 = st.columns(2)
            col1.markdown(f"**Unit:** `{row['unit']}`")
            col2.markdown(f"**Version:** `{row['version']}`")
            st.caption(f"Created: {row['created_at'][:10]}")

elif page == "🤖 AI Assistant":
    st.markdown("# 🤖 AI Assistant")
    st.markdown("Ask any question about your coaching data in plain English. Powered by **Groq · Llama 3.3 70B**.")

    SCHEMA = """
    You are a SQL expert querying a SQLite database for CoachSphere, an AI sales coaching analytics platform.
    Data covers Jan 2024 to Jun 2024. period_month format is 'YYYY-MM' (e.g. '2024-01' to '2024-06').
    Teams are: Enterprise, SMB, EMEA, APAC.

    CRITICAL RULES:
    1. ALWAYS use the views below for any metric, skill, business, or engagement questions. Never query raw tables for these.
    2. business_metrics raw table has NO team column — always use v_business_impact view which has team.
    3. Use EXACT column names as listed — do not guess or add prefixes like avg_.
    4. Return ONLY a valid SQLite SELECT statement. No markdown, no explanation, no code fences.

    VIEWS (preferred — use these always):
    v_coaching_effectiveness: user_id, name, team, period_month, engagement_score, skill_score, communication_quality_score, business_impact_index, coaching_effectiveness_score
    v_business_impact: user_id, name, team, period_month, deals_closed, win_rate, avg_deal_size, pipeline_value, quota_attainment, sessions_completed, business_impact_index
    v_skill_progression: user_id, name, team, period_month, communication, product_knowledge, objection_handling, closing_technique, active_listening, avg_overall_score, assessments_count
    v_session_engagement: user_id, name, team, period_month, sessions_scheduled, sessions_completed, avg_duration_min, feedback_submitted, engagement_score
    v_communication_quality: user_id, name, team, period_month, avg_engagement, avg_clarity, avg_confidence, communication_quality_score, feedback_count
    v_team_summary: team, period_month, active_reps, avg_engagement, avg_effectiveness

    RAW TABLES (only for session-level or user-level queries):
    users: user_id, name, email, role, team, region, hire_date, manager_id
    coaching_sessions: session_id, user_id, scenario, scheduled_at, duration_minutes, status ('completed','started','missed')
    skill_assessments: assessment_id, session_id, user_id, assessed_at, communication, product_knowledge, objection_handling, closing_technique, active_listening, overall_score
    session_feedback: feedback_id, session_id, user_id, given_at, engagement_score, clarity_score, confidence_score, overall_score
    business_metrics: metric_id, user_id, period_month, deals_closed, pipeline_value, win_rate, avg_deal_size, quota_attainment, sessions_completed (NO team column)

    EXAMPLE QUERIES:
    Q: Which team has the highest quota attainment?
    A: SELECT team, ROUND(AVG(quota_attainment)*100,1) AS avg_quota_pct FROM v_business_impact GROUP BY team ORDER BY avg_quota_pct DESC LIMIT 1

    Q: Top 5 reps by coaching effectiveness in June 2024?
    A: SELECT name, team, coaching_effectiveness_score FROM v_coaching_effectiveness WHERE period_month='2024-06' ORDER BY coaching_effectiveness_score DESC LIMIT 5

    Q: Reps whose objection handling improved most over 6 months?
    A: SELECT name, team, MIN(objection_handling) AS start_score, MAX(objection_handling) AS end_score, ROUND(MAX(objection_handling)-MIN(objection_handling),2) AS improvement FROM v_skill_progression GROUP BY user_id, name, team ORDER BY improvement DESC LIMIT 10

    Q: How many sessions were missed each month?
    A: SELECT strftime('%Y-%m', scheduled_at) AS month, COUNT(*) AS missed FROM coaching_sessions WHERE status='missed' GROUP BY month ORDER BY month

    Q: Which rep closed the most deals in May 2024?
    A: SELECT name, team, deals_closed FROM v_business_impact WHERE period_month='2024-05' ORDER BY deals_closed DESC LIMIT 1
    """

    if not GROQ_API_KEY:
        st.error("Groq API key not found. Add GROQ_API_KEY to your .env file.")
        st.stop()

    # Initialise chat history
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Display all messages from history
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("sql"):
                with st.expander("🔍 Generated SQL"):
                    st.code(msg["sql"], language="sql")
            if msg.get("data"):
                st.dataframe(pd.DataFrame(msg["data"]), use_container_width=True, hide_index=True)

    # Example prompts shown only on first load
    if not st.session_state.chat_history:
        st.markdown("**Try asking:**")
        examples = [
            "Who are the top 5 reps by coaching effectiveness in June 2024?",
            "Which team has the highest quota attainment on average?",
            "Show me reps whose objection handling improved the most over 6 months.",
            "How many sessions were missed in each month?",
            "Which rep closed the most deals in May 2024?",
        ]
        cols = st.columns(2)
        for i, ex in enumerate(examples):
            if cols[i % 2].button(ex, use_container_width=True):
                st.session_state["prefill"] = ex
                st.rerun()

    user_input = st.chat_input("Ask a question about your coaching data...")
    if "prefill" in st.session_state:
        user_input = st.session_state.pop("prefill")

    if user_input:
        # Append user message and rerun to show it immediately
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        st.session_state["_processing"] = True
        st.rerun()

    # Process the last user message if flagged
    if st.session_state.get("_processing"):
        st.session_state["_processing"] = False
        user_q = st.session_state.chat_history[-1]["content"]

        with st.spinner("Thinking..."):
            try:
                client = Groq(api_key=GROQ_API_KEY)

                # Step 1: Generate SQL
                sql_prompt = f"{SCHEMA}\n\nQuestion: {user_q}\n\nSQL:"
                sql_resp = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": sql_prompt}],
                    temperature=0
                )
                raw_sql = sql_resp.choices[0].message.content.strip()
                if raw_sql.startswith("```"):
                    raw_sql = raw_sql.split("```")[1]
                    if raw_sql.lower().startswith("sql"):
                        raw_sql = raw_sql[3:]
                generated_sql = raw_sql.strip()

                # Step 2: Run SQL
                try:
                    result_df = query(generated_sql)
                    sql_error = None
                except Exception as e:
                    result_df = pd.DataFrame()
                    sql_error = str(e)

                # Step 3: Natural language answer
                if sql_error:
                    answer_prompt = f"The user asked: '{user_q}'\nSQL failed: {sql_error}\nExplain briefly and suggest how to rephrase."
                elif result_df.empty:
                    answer_prompt = f"The user asked: '{user_q}'\nThe query returned no results. Give a helpful response."
                else:
                    data_preview = result_df.head(10).to_string(index=False)
                    answer_prompt = f"The user asked: '{user_q}'\nData:\n{data_preview}\nGive a concise 2-3 sentence answer with specific numbers."

                ans_resp = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": answer_prompt}],
                    temperature=0.3
                )
                answer_text = ans_resp.choices[0].message.content.strip()

                # Store data as records (not DataFrame) to avoid session_state issues
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": answer_text,
                    "sql": generated_sql if not sql_error else None,
                    "data": result_df.to_dict("records") if not result_df.empty else None
                })

            except Exception as e:
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": f"Error: {str(e)}"
                })

        st.rerun()

