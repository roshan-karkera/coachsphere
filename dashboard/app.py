"""
CoachSphere Analytics Dashboard
Fictional AI Sales Coaching Platform – Internal Analytics Layer
"""

import sqlite3
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots

# ── Plotly chart white-text helper ─────────────────────────────────────────────
_PCHART = dict(
    font        = dict(color="#ffffff"),
    legend      = dict(font=dict(color="#ffffff"), title_font=dict(color="#ffffff")),
)
import streamlit as st

import os
import sys
import json
import base64
from pathlib import Path

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

# Clear cache on every fresh load
st.cache_data.clear()
st.cache_resource.clear()

# ── Dark theme overrides ──────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Full dark theme ─────────────────────────────────────── */

[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="block-container"] { background: #070d1a !important; }
[data-testid="stSidebar"] { background-color: #0a1628 !important; border-right: 1px solid rgba(56,189,248,0.08); }
[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
h1,h2,h3,h4,p,span,label { color: #e2e8f0; }
.stMarkdown p { color: #cbd5e1; }
[data-testid="stChatMessage"] .stMarkdown p,
[data-testid="stChatMessage"] .stMarkdown li,
[data-testid="stChatMessage"] .stMarkdown span,
[data-testid="stChatMessage"] p,
[data-testid="stChatMessage"] li { color: #ffffff !important; }

/* ── Hide Streamlit chrome (top & bottom bars) ───────────── */
header[data-testid="stHeader"] { display: none !important; }
[data-testid="stToolbar"] { display: none !important; }
[data-testid="stDecoration"] { display: none !important; }
[data-testid="stBottom"],
[data-testid="stBottom"] > div,
[data-testid="stBottom"] > div > div,
[data-testid="stBottom"] > div > div > div,
.stChatFloatingInputContainer,
[data-testid="stChatInputContainer"],
div[class*="stBottom"] {
    background: #070d1a !important;
    border-top: none !important;
    box-shadow: none !important;
}
/* Nuke any remaining white at the very bottom */
.main > div:last-child { background: #070d1a !important; }

/* ── Force sidebar always visible & wider ────────────────── */
section[data-testid="stSidebar"],
[data-testid="stSidebar"] {
    transform: none !important;
    width: 320px !important;
    min-width: 320px !important;
    max-width: 320px !important;
    visibility: visible !important;
    opacity: 1 !important;
    display: flex !important;
}
[data-testid="stSidebarCollapseButton"],
[data-testid="collapsedControl"] { display: none !important; }

/* ── Metric cards ────────────────────────────────────────── */
.metric-card {
    background: linear-gradient(135deg, #0f1f35 0%, #0a1628 100%);
    border-radius: 16px; padding: 22px 24px;
    border: 1px solid rgba(56,189,248,0.15); text-align: center;
    box-shadow: 0 4px 24px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.04);
    transition: transform 0.2s ease, border-color 0.2s ease;
}
.metric-card:hover { transform: translateY(-3px); border-color: rgba(56,189,248,0.4); }
.metric-val {
    font-size: 2.2rem; font-weight: 800;
    background: linear-gradient(135deg, #38bdf8 0%, #818cf8 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text; letter-spacing: -0.02em;
}
.metric-lbl { font-size: 0.72rem; color: #475569; margin-top: 8px; text-transform: uppercase; letter-spacing: 0.1em; font-weight: 600; }
.metric-delta { font-size: 0.85rem; margin-top: 8px; font-weight: 600; }

/* ── Section titles ──────────────────────────────────────── */
.section-title { font-size: 0.8rem; font-weight: 700; color: #475569; margin: 20px 0 12px; text-transform: uppercase; letter-spacing: 0.1em; }

/* ── Page hero ───────────────────────────────────────────── */
.page-hero {
    background: linear-gradient(135deg, #0d2137 0%, #0a1628 60%, #070d1a 100%);
    border-radius: 20px; padding: 28px 32px; margin-bottom: 24px;
    border: 1px solid rgba(56,189,248,0.12); position: relative; overflow: hidden;
}
.page-hero::before {
    content: ''; position: absolute; top: -40%; right: -5%; width: 280px; height: 280px;
    background: radial-gradient(circle, rgba(56,189,248,0.07) 0%, transparent 70%); pointer-events: none;
}
.hero-title { font-size: 1.7rem; font-weight: 800; background: linear-gradient(135deg, #e2e8f0 0%, #94a3b8 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; margin: 0 0 6px 0; }
.hero-sub { color: #ffffff; margin: 0; font-size: 0.9rem; }

/* ── MCP page ────────────────────────────────────────────── */
.mcp-badge {
    display: inline-flex; align-items: center; gap: 8px;
    background: rgba(52,211,153,0.08); border: 1px solid rgba(52,211,153,0.25);
    border-radius: 100px; padding: 6px 16px; font-size: 0.85rem; font-weight: 600; color: #34d399;
}
.pulse { width: 8px; height: 8px; background: #34d399; border-radius: 50%; display:inline-block; animation: pulse 2s ease-in-out infinite; }
@keyframes pulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:0.4;transform:scale(0.8)} }
.tool-card {
    background: linear-gradient(135deg, #0f1f35 0%, #0a1628 100%);
    border-radius: 12px; padding: 14px 18px; border: 1px solid rgba(56,189,248,0.1);
    margin-bottom: 10px; transition: border-color 0.2s;
}
.tool-card:hover { border-color: rgba(56,189,248,0.3); }
.tool-name { font-weight: 700; color: #38bdf8; font-size: 0.88rem; font-family: monospace; }
.tool-desc { color: #475569; font-size: 0.8rem; margin-top: 4px; }
.arch-box {
    background: linear-gradient(135deg, #0f1f35 0%, #0a1628 100%);
    border-radius: 14px; padding: 20px 24px; border: 1px solid rgba(56,189,248,0.12); text-align: center;
}
.arch-label { font-size: 0.7rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: #475569; margin-bottom: 6px; }
.arch-name { font-size: 1rem; font-weight: 700; color: #e2e8f0; }
.arch-sub { font-size: 0.75rem; color: #38bdf8; margin-top: 3px; }

/* ── Buttons ─────────────────────────────────────────────── */
.stButton > button {
    background: linear-gradient(135deg, #0f1f35 0%, #0a1628 100%) !important;
    border: 1px solid rgba(56,189,248,0.15) !important;
    color: #64748b !important;
    border-radius: 12px !important;
    font-size: 0.82rem !important;
    transition: all 0.2s ease !important;
    width: 100% !important;
}
.stButton > button:hover {
    border-color: rgba(56,189,248,0.45) !important;
    color: #e2e8f0 !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 4px 16px rgba(56,189,248,0.1) !important;
}

/* ── Chat input ──────────────────────────────────────────── */
[data-testid="stChatInput"],
[data-testid="stChatInput"] > div,
[data-testid="stChatInput"] > div > div {
    background: #ffffff !important;
    border-radius: 16px !important;
    border: none !important;
    box-shadow: 0 2px 20px rgba(0,0,0,0.3) !important;
}
[data-testid="stChatInput"] textarea {
    background: #ffffff !important;
    color: #0f172a !important;
    border: none !important;
    border-radius: 16px !important;
}
[data-testid="stChatInput"] textarea::placeholder { color: #94a3b8 !important; }
.stSelectbox > div > div, .stMultiSelect > div > div {
    background: #0f1f35 !important; border-color: rgba(56,189,248,0.15) !important; color: #e2e8f0 !important;
}
[data-testid="stSelectbox"] div[data-baseweb="select"] *,
[data-testid="stSelectbox"] input,
[data-testid="stSelectbox"] div[class*="ValueContainer"] *,
[data-testid="stSelectbox"] div[class*="singleValue"] {
    color: #e2e8f0 !important;
}
/* Dropdown open — portal-level selectors */
div[data-baseweb="popover"],
div[data-baseweb="popover"] > div,
div[data-baseweb="popover"] > div > div,
div[data-baseweb="menu"],
ul[data-baseweb="menu"],
div[role="listbox"],
div[role="listbox"] > div,
div[class*="Menu"],
div[class*="menu"] {
    background: #070d1a !important;
    border: 1px solid rgba(56,189,248,0.15) !important;
    border-radius: 10px !important;
    box-shadow: 0 8px 24px rgba(0,0,0,0.5) !important;
}
/* Option items */
li[role="option"],
div[role="option"],
div[data-baseweb="option"],
div[data-baseweb="menu"] li,
ul[data-baseweb="menu"] li {
    background: #070d1a !important;
    color: #e2e8f0 !important;
}
li[role="option"]:hover,
div[role="option"]:hover,
div[data-baseweb="option"]:hover,
li[aria-selected="true"],
div[aria-selected="true"] {
    background: #0f1f35 !important;
    color: #38bdf8 !important;
}
/* Multiselect — full dark theme */
[data-testid="stMultiSelect"] div[data-baseweb="select"] > div,
[data-testid="stMultiSelect"] div[data-baseweb="base-input"],
[data-testid="stMultiSelect"] > div > div,
[data-testid="stMultiSelect"] > div > div > div {
    background: #0f1f35 !important;
    border-color: rgba(56,189,248,0.15) !important;
}
[data-testid="stMultiSelect"] span[data-baseweb="tag"],
.stMultiSelect span[data-baseweb="tag"] {
    background: #0a1628 !important;
    border: 1px solid rgba(56,189,248,0.3) !important;
    color: #ffffff !important;
    border-radius: 6px !important;
}
[data-testid="stMultiSelect"] span[data-baseweb="tag"] span,
[data-testid="stMultiSelect"] span[data-baseweb="tag"] *,
[data-baseweb="tag"] span,
[data-baseweb="tag"] * {
    color: #ffffff !important;
    fill: #94a3b8 !important;
}
[data-testid="stExpander"] {
    background: #0f1f35 !important; border: 1px solid rgba(56,189,248,0.1) !important; border-radius: 12px !important;
}
[data-testid="stExpander"] summary { color: #94a3b8 !important; }

/* ── Inline code (backticks in markdown/expander labels) ─── */
code {
    background: #0a1628 !important;
    color: #e2e8f0 !important;
    border: 1px solid rgba(56,189,248,0.3) !important;
    border-radius: 6px !important;
    padding: 2px 10px !important;
    font-size: 0.85em !important;
}
/* ── Code blocks ─────────────────────────────────────────── */
[data-testid="stCodeBlock"],
[data-testid="stCodeBlock"] pre,
[data-testid="stCodeBlock"] code,
.stCode, .stCode pre, .stCode code {
    background: #060d1b !important;
    color: #e2e8f0 !important;
    border: 1px solid rgba(56,189,248,0.12) !important;
    border-radius: 10px !important;
}
[data-testid="stCodeBlock"] span { opacity: 1 !important; }
/* ── Metric Definitions formula block ────────────────────── */
details div[style*="monospace"] { color: #ffffff !important; font-weight: 700 !important; }
/* ── Code block copy button ───────────────────────────────── */
[data-testid="stCodeBlock"] button,
[data-testid="stCodeCopyButton"],
button[title="Copy to clipboard"],
button[aria-label="Copy to clipboard"] {
    background: rgba(15,31,53,0.95) !important;
    border: 1px solid rgba(56,189,248,0.3) !important;
    color: #38bdf8 !important;
    border-radius: 6px !important;
    box-shadow: none !important;
    opacity: 1 !important;
}
[data-testid="stCodeBlock"] button svg,
button[title="Copy to clipboard"] svg,
button[aria-label="Copy to clipboard"] svg {
    stroke: #38bdf8 !important;
    fill: none !important;
}
/* Global tooltip — Streamlit renders these as portals */
div[role="tooltip"],
div[data-radix-popper-content-wrapper] div,
[data-testid="stTooltipContent"],
.stTooltip {
    background: #0f1f35 !important;
    color: #94a3b8 !important;
    border: 1px solid rgba(56,189,248,0.25) !important;
    border-radius: 6px !important;
    box-shadow: 0 4px 12px rgba(0,0,0,0.4) !important;
    font-size: 0.78rem !important;
}
/* Expanders dark — open and closed states identical */
[data-testid="stExpander"],
[data-testid="stExpander"] details,
[data-testid="stExpander"] details[open] {
    background: #0a1628 !important;
    border: 1px solid rgba(56,189,248,0.1) !important;
    border-radius: 12px !important;
}
[data-testid="stExpander"] summary,
[data-testid="stExpander"] summary:hover,
[data-testid="stExpander"] summary:focus,
[data-testid="stExpander"] summary:active,
[data-testid="stExpander"] details[open] summary,
[data-testid="stExpander"] details[open] summary:hover,
[data-testid="stExpander"] details[open] summary:focus {
    background: #0a1628 !important;
    color: #94a3b8 !important;
    outline: none !important;
    box-shadow: none !important;
    border-bottom: none !important;
}
[data-testid="stExpander"] summary *,
[data-testid="stExpander"] details[open] summary *,
[data-testid="stExpander"] summary span,
[data-testid="stExpander"] summary p,
[data-testid="stExpander"] summary svg {
    color: #94a3b8 !important;
    fill: #94a3b8 !important;
    stroke: #94a3b8 !important;
}

/* ── Chat messages ───────────────────────────────────────── */
[data-testid="stChatMessage"],
[data-testid="stChatMessage"] > div,
[data-testid="stChatMessage"] > div > div {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}
/* ── Chat avatars — 3D gradient style ───────────────────── */
[data-testid="stChatMessageAvatarUser"] {
    background: linear-gradient(135deg, #f97316 0%, #ef4444 100%) !important;
    border-radius: 50% !important;
    box-shadow: 0 4px 14px rgba(249,115,22,0.45), 0 1px 3px rgba(0,0,0,0.4) !important;
    border: none !important;
}
[data-testid="stChatMessageAvatarAssistant"] {
    background: linear-gradient(135deg, #f59e0b 0%, #f97316 100%) !important;
    border-radius: 50% !important;
    box-shadow: 0 4px 14px rgba(245,158,11,0.45), 0 1px 3px rgba(0,0,0,0.4) !important;
    border: none !important;
}
[data-testid="stChatMessageAvatarUser"] svg,
[data-testid="stChatMessageAvatarAssistant"] svg {
    filter: drop-shadow(0 1px 2px rgba(0,0,0,0.3)) !important;
}

/* ── Dataframe ───────────────────────────────────────────── */
[data-testid="stDataFrame"] iframe { border-radius: 12px; }

/* ── Misc ────────────────────────────────────────────────── */
hr { border-color: rgba(56,189,248,0.08) !important; }
.stSelectbox label, .stMultiSelect label, .stRadio label { color: #94a3b8 !important; }
[data-testid="stSidebarContent"] h2 { color: #38bdf8 !important; }
footer,#MainMenu { visibility: hidden; }
div[class*="viewerBadge"],.stDeployButton { display: none !important; }
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

def _icon(name: str, size: int = 40) -> str:
    """Return an <img> tag for a page icon from dashboard/assets/."""
    p = Path(__file__).parent / "assets" / name
    if not p.exists():
        return ""
    b64 = base64.b64encode(p.read_bytes()).decode()
    return (f'<img src="data:image/png;base64,{b64}" '
            f'style="width:{size}px;height:{size}px;vertical-align:middle;'
            f'margin-right:10px;border-radius:8px">')

def dark_table(df):
    """Render a DataFrame as a dark-themed HTML table matching the UI palette."""
    if df is None or df.empty:
        return
    headers = "".join(
        f'<th style="padding:8px 14px;text-align:left;color:#38bdf8;font-size:0.78rem;'
        f'font-weight:600;text-transform:uppercase;letter-spacing:0.05em;'
        f'border-bottom:1px solid rgba(56,189,248,0.2);white-space:nowrap">{c}</th>'
        for c in df.columns
    )
    rows = ""
    for idx, row in df.iterrows():
        bg = "rgba(15,31,53,0.6)" if idx % 2 == 0 else "rgba(10,22,40,0.6)"
        cells = "".join(
            f'<td style="padding:7px 14px;color:#cbd5e1;font-size:0.82rem;'
            f'border-bottom:1px solid rgba(56,189,248,0.06);white-space:nowrap">{v}</td>'
            for v in row
        )
        rows += f'<tr style="background:{bg}">{cells}</tr>'
    html = f"""
    <div style="overflow-x:auto;border-radius:10px;border:1px solid rgba(56,189,248,0.18);margin-top:6px">
      <table style="width:100%;border-collapse:collapse;background:rgba(10,22,40,0.8)">
        <thead><tr style="background:rgba(15,31,53,0.9)">{headers}</tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </div>"""
    st.markdown(html, unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:4px;">
        <svg width="90" height="90" viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg">
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
        "🔌 MCP Server",
    ])
    st.divider()
    teams_all = query("SELECT DISTINCT team FROM users WHERE role != 'Team Lead'")['team'].tolist()
    sel_teams = st.multiselect("Filter by Team", teams_all, default=teams_all)
    months_all = query("SELECT DISTINCT period_month FROM v_coaching_effectiveness ORDER BY period_month")['period_month'].tolist()
    sel_month = st.selectbox("Reference Month", months_all, index=len(months_all)-1)


team_filter = "','".join(sel_teams) if sel_teams else "''"

# ═══════════════════════════════════════════════════════════════════════════════
if page == "📊 Overview":
    st.markdown(f"""<div class="page-hero">
        <div class="hero-title">{_icon('icon_overview.png')} Platform Overview</div>
        <div class="hero-sub">Platform metrics · {sel_month} &nbsp;·&nbsp; {len(sel_teams)} teams active</div>
    </div>""", unsafe_allow_html=True)

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
                          font=dict(color='#ffffff'), legend=dict(font=dict(color='#ffffff'), title_font=dict(color='#ffffff')), legend_title_text='',
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
                           font=dict(color='#ffffff'), legend=dict(font=dict(color='#ffffff'), title_font=dict(color='#ffffff')), showlegend=False,
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
                           font=dict(color='#ffffff'), legend=dict(font=dict(color='#ffffff'), title_font=dict(color='#ffffff')), xaxis=dict(gridcolor='#334155'),
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
                           font=dict(color='#ffffff'), legend=dict(font=dict(color='#ffffff'), title_font=dict(color='#ffffff')), xaxis=dict(gridcolor='#334155'),
                           yaxis=dict(gridcolor='#334155'))
        st.plotly_chart(fig4, use_container_width=True)

# ═══════════════════════════════════════════════════════════════════════════════
elif page == "👥 Team Analytics":
    st.markdown(f"""<div class="page-hero">
        <div class="hero-title">{_icon('icon_team.png')} Team Analytics</div>
        <div class="hero-sub">Effectiveness, engagement, and quota attainment across all teams</div>
    </div>""", unsafe_allow_html=True)
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
                          font=dict(color='#ffffff'), legend=dict(font=dict(color='#ffffff'), title_font=dict(color='#ffffff')), xaxis=dict(gridcolor='#334155'),
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
        fig2.update_layout(paper_bgcolor='rgba(255,255,255,0)', font=dict(color='#ffffff'), legend=dict(font=dict(color='#ffffff'), title_font=dict(color='#ffffff')),
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
    dark_table(top)

# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🧠 Skill Progression":
    st.markdown(f"""<div class="page-hero">
        <div class="hero-title">{_icon('icon_skill.png')} Skill Progression</div>
        <div class="hero-sub">Track communication, objection handling, and closing technique over time</div>
    </div>""", unsafe_allow_html=True)
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
                          font=dict(color='#ffffff'), legend=dict(font=dict(color='#ffffff'), title_font=dict(color='#ffffff')), yaxis=dict(range=[1,5], gridcolor='#334155'),
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
                                paper_bgcolor='rgba(255,255,255,0)', font=dict(color='#ffffff'), legend=dict(font=dict(color='#ffffff'), title_font=dict(color='#ffffff')), showlegend=False)
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
    st.markdown(f"""<div class="page-hero">
        <div class="hero-title">{_icon('icon_session.png')} Session Insights</div>
        <div class="hero-sub">Completion rates, session duration, and scenario breakdown</div>
    </div>""", unsafe_allow_html=True)

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
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'),
                          legend=dict(font=dict(color='#ffffff'), title_font=dict(color='#ffffff')), legend_title_text='')
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown('<div class="section-title">Completion Status Distribution</div>', unsafe_allow_html=True)
        st_cnt = sessions.groupby(['period_month','status'])['duration_minutes'].count().reset_index(name='count')
        fig2 = px.bar(st_cnt, x='period_month', y='count', color='status', barmode='stack',
                      color_discrete_sequence=COLORS,
                      labels={'count':'Sessions','period_month':'Month'})
        fig2.update_layout(plot_bgcolor='#0f172a', paper_bgcolor='rgba(255,255,255,0)',
                           font=dict(color='#ffffff'), legend=dict(font=dict(color='#ffffff'), title_font=dict(color='#ffffff')), xaxis=dict(gridcolor='#334155'),
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
                       font=dict(color='#ffffff'), legend=dict(font=dict(color='#ffffff'), title_font=dict(color='#ffffff')), coloraxis_showscale=False,
                       xaxis=dict(gridcolor='#334155'), yaxis=dict(gridcolor='#334155'))
    st.plotly_chart(fig3, use_container_width=True)

# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🔍 Rep Deep Dive":
    st.markdown(f"""<div class="page-hero">
        <div class="hero-title">{_icon('icon_rep.png')} Rep Deep Dive</div>
        <div class="hero-sub">Full coaching history, skill radar, and business metrics for any rep</div>
    </div>""", unsafe_allow_html=True)
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
        fig.update_layout(plot_bgcolor='#0f172a', paper_bgcolor='rgba(255,255,255,0)', font=dict(color='#ffffff'), legend=dict(font=dict(color='#ffffff'), title_font=dict(color='#ffffff')),
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
                                paper_bgcolor='rgba(255,255,255,0)', font=dict(color='#ffffff'), legend=dict(font=dict(color='#ffffff'), title_font=dict(color='#ffffff')), showlegend=False)
            st.plotly_chart(fig2, use_container_width=True)

    st.markdown('<div class="section-title">Business Metrics Over Time</div>', unsafe_allow_html=True)
    fig3 = make_subplots(specs=[[{"secondary_y": True}]])
    fig3.add_trace(go.Bar(x=bi['period_month'], y=bi['deals_closed'], name='Deals Closed',
                          marker_color='#38bdf8'), secondary_y=False)
    fig3.add_trace(go.Scatter(x=bi['period_month'], y=bi['win_rate']*100, name='Win Rate %',
                              mode='lines+markers', line=dict(color='#f472b6')), secondary_y=True)
    fig3.update_layout(plot_bgcolor='#0f172a', paper_bgcolor='rgba(255,255,255,0)', font=dict(color='#ffffff'), legend=dict(font=dict(color='#ffffff'), title_font=dict(color='#ffffff')),
                       xaxis=dict(gridcolor='#334155'), legend_title_text='')
    fig3.update_yaxes(gridcolor='#334155', secondary_y=False, title_text='Deals Closed')
    fig3.update_yaxes(gridcolor='#334155', secondary_y=True,  title_text='Win Rate %')
    st.plotly_chart(fig3, use_container_width=True)

# ═══════════════════════════════════════════════════════════════════════════════
elif page == "📋 Metric Definitions":
    st.markdown(f"""<div class="page-hero">
        <div class="hero-title">{_icon('icon_metric.png')} Metric Definitions</div>
        <div class="hero-sub">Version-controlled KPI definitions — every formula change is tracked in Git</div>
    </div>""", unsafe_allow_html=True)
    defs = query("SELECT * FROM metric_definitions")
    import html as _html
    for _, row in defs.iterrows():
        formula_esc = _html.escape(str(row['formula']))
        st.markdown(f"""
        <details style="background:rgba(10,22,40,0.6);border:1px solid rgba(56,189,248,0.12);
            border-radius:10px;margin-bottom:8px;overflow:hidden">
            <summary style="cursor:pointer;padding:14px 18px;color:#cbd5e1;font-size:0.88rem;
                list-style:none;display:flex;align-items:center;gap:8px;user-select:none">
                <span class="det-arrow" style="color:#38bdf8;font-size:0.75rem;transition:transform 0.2s">▶</span>
                {_html.escape(str(row['display_name']))}
                &nbsp;·&nbsp;
                <code style="background:rgba(56,189,248,0.1);color:#38bdf8;border:1px solid rgba(56,189,248,0.25);
                    padding:2px 8px;border-radius:5px;font-family:monospace;font-size:0.82rem">{_html.escape(str(row['metric_name']))}</code>
                &nbsp;·&nbsp; {_html.escape(str(row['version']))}
            </summary>
            <div style="padding:14px 18px;border-top:1px solid rgba(56,189,248,0.1)">
                <p style="color:#94a3b8;font-size:0.85rem;margin:0 0 12px">{_html.escape(str(row['description']))}</p>
                <div style="background:rgba(15,31,53,0.9);border:1px solid rgba(56,189,248,0.3);
                    border-radius:6px;padding:12px 16px;color:#ffffff !important;font-family:monospace;
                    font-size:0.92rem;overflow-x:auto;margin:0 0 12px;white-space:pre-wrap;
                    font-weight:700;letter-spacing:0.01em;line-height:1.6">{formula_esc}</div>
                <div style="display:flex;gap:24px;font-size:0.8rem">
                    <span><span style="color:#94a3b8;font-weight:600">Unit:</span>
                        <span style="color:#cbd5e1"> {_html.escape(str(row['unit']))}</span></span>
                    <span><span style="color:#94a3b8;font-weight:600">Version:</span>
                        <span style="color:#cbd5e1"> {_html.escape(str(row['version']))}</span></span>
                    <span><span style="color:#94a3b8;font-weight:600">Created:</span>
                        <span style="color:#cbd5e1"> {str(row['created_at'])[:10]}</span></span>
                </div>
            </div>
        </details>
        <style>details[open] .det-arrow {{ transform: rotate(90deg); }}</style>
        """, unsafe_allow_html=True)

elif page == "🤖 AI Assistant":
    st.markdown(f"""<div class="page-hero">
        <div class="hero-title">{_icon('robot_avatar.png')} AI Assistant</div>
        <div class="hero-sub">Ask any question in plain English · Powered by Groq · Llama 3.3 70B · Agentic tool-calling with trace</div>
    </div>""", unsafe_allow_html=True)

    if not GROQ_API_KEY:
        st.error("Groq API key not found. Add GROQ_API_KEY to your .env file.")
        st.stop()

    # ── Tool definitions ──────────────────────────────────────────────────
    TOOLS = [
        {
            "type": "function",
            "function": {
                "name": "get_top_performers",
                "description": "Get the top 5 sales reps ranked by coaching effectiveness score for a given month.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "month": {"type": "string", "description": "Period month YYYY-MM e.g. '2024-06'"},
                        "team":  {"type": "string", "description": "Team filter: Enterprise, SMB, EMEA, APAC, or 'all'"}
                    },
                    "required": ["month"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_team_summary",
                "description": "Get team-level performance: engagement score, effectiveness score, active rep count per month.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "month": {"type": "string", "description": "Period month YYYY-MM, or 'all' for every month"}
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_quota_attainment",
                "description": "Get average quota attainment %, win rate, and deals closed by team.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "month": {"type": "string", "description": "Period month YYYY-MM, or 'all' for every month"},
                        "team":  {"type": "string", "description": "Team name or 'all'"}
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_session_stats",
                "description": "Get coaching session counts: scheduled, completed, missed, and completion rate by team and month.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "month": {"type": "string", "description": "Period month YYYY-MM, or 'all' for every month"},
                        "team":  {"type": "string", "description": "Team name or 'all'"}
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_skill_improvement",
                "description": "Find the top 10 reps who improved the most in a specific skill (or overall) across the 6-month period.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "skill": {
                            "type": "string",
                            "description": "Skill to rank by: communication, product_knowledge, objection_handling, closing_technique, active_listening, or 'overall'"
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_rep_profile",
                "description": "Get full coaching history for a specific sales rep: effectiveness, skills, quota, deals over all months.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "rep_name": {"type": "string", "description": "Full or partial name of the sales rep"}
                    },
                    "required": ["rep_name"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_top_by_metric",
                "description": (
                    "Rank the top sales reps by any specific metric for a given month. "
                    "Use this tool when the user asks 'who closed the most deals', 'who has the highest win rate', "
                    "'who hit quota', 'who had the best quota attainment', or any question about ranking reps by a business or performance metric. "
                    "Metric options: 'deals_closed', 'quota_pct', 'win_rate_pct', 'effectiveness', 'engagement', 'skill_score'."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "metric": {
                            "type": "string",
                            "description": "Metric to rank by: 'deals_closed', 'quota_pct', 'win_rate_pct', 'effectiveness', 'engagement', 'skill_score'"
                        },
                        "month": {"type": "string", "description": "Period month YYYY-MM e.g. '2024-05', or 'all' for all months"},
                        "team":  {"type": "string", "description": "Team filter: Enterprise, SMB, EMEA, APAC, or 'all'"}
                    },
                    "required": ["metric"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "compare_skill_progression",
                "description": (
                    "Compare skill score trends across teams or for a specific skill over time. "
                    "Use when asked to compare teams, or how a skill changed month-over-month. "
                    "Skill options: communication, product_knowledge, objection_handling, "
                    "closing_technique, active_listening, or 'overall'."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "teams": {"type": "string", "description": "Comma-separated team names e.g. 'EMEA,Enterprise', or 'all'"},
                        "skill": {"type": "string", "description": "Skill to compare: communication, product_knowledge, objection_handling, closing_technique, active_listening, or 'overall'"}
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "identify_underperforming_segments",
                "description": (
                    "Find teams performing below the platform average coaching effectiveness score. "
                    "Use when asked which teams are struggling, underperforming, at risk, or below average. "
                    "Always returns results — teams ranked worst-first compared against the platform average. "
                    "Do NOT pass a threshold parameter — this tool has no threshold."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "month": {"type": "string", "description": "Period month YYYY-MM, or 'all' for all months"}
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "explain_metric_definition",
                "description": (
                    "Look up how a KPI or metric is defined and calculated. "
                    "Use when asked 'how is X calculated', 'what does X mean', or 'explain metric X'. "
                    "Returns the formula, version, description, and unit."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "metric_name": {"type": "string", "description": "Metric name or keyword e.g. 'engagement', 'effectiveness', 'business_impact'"}
                    },
                    "required": ["metric_name"]
                }
            }
        }
    ]

    # ── Tool execution ────────────────────────────────────────────────────
    def run_tool(name, args, _trace=None):
        conn = sqlite3.connect(DB)
        sql  = ""
        df   = pd.DataFrame()
        try:
            month = args.get("month", "all")
            team  = args.get("team",  "all")
            mf = f"AND period_month = '{month}'" if month and month != "all" else ""
            tf = f"AND team = '{team}'"          if team  and team  != "all" else ""

            if name == "get_top_performers":
                sql = f"""
                    SELECT name, team, period_month,
                           ROUND(coaching_effectiveness_score,3) AS effectiveness,
                           ROUND(engagement_score,3)             AS engagement,
                           ROUND(skill_score,3)                  AS skill_score
                    FROM v_coaching_effectiveness
                    WHERE 1=1 {mf} {tf}
                    ORDER BY coaching_effectiveness_score DESC LIMIT 5"""
                df = pd.read_sql_query(sql, conn)

            elif name == "get_team_summary":
                sql = f"""
                    SELECT team, period_month, active_reps,
                           ROUND(avg_engagement,3)    AS avg_engagement,
                           ROUND(avg_effectiveness,3) AS avg_effectiveness
                    FROM v_team_summary WHERE 1=1 {mf}
                    ORDER BY period_month, avg_effectiveness DESC"""
                df = pd.read_sql_query(sql, conn)

            elif name == "get_quota_attainment":
                sql = f"""
                    SELECT team, period_month,
                           ROUND(AVG(quota_attainment)*100,1) AS avg_quota_pct,
                           ROUND(AVG(win_rate)*100,1)         AS avg_win_rate_pct,
                           SUM(deals_closed)                  AS total_deals
                    FROM v_business_impact WHERE 1=1 {mf} {tf}
                    GROUP BY team, period_month
                    ORDER BY period_month, avg_quota_pct DESC"""
                df = pd.read_sql_query(sql, conn)

            elif name == "get_session_stats":
                sql = f"""
                    SELECT team, period_month,
                           SUM(sessions_scheduled) AS scheduled,
                           SUM(sessions_completed) AS completed,
                           ROUND(CAST(SUM(sessions_completed) AS REAL)/SUM(sessions_scheduled)*100,1) AS completion_pct
                    FROM v_session_engagement WHERE 1=1 {mf} {tf}
                    GROUP BY team, period_month ORDER BY period_month"""
                df = pd.read_sql_query(sql, conn)

            elif name == "get_skill_improvement":
                skill = args.get("skill", "overall")
                col   = "avg_overall_score" if skill in ("overall","") or skill not in [
                    "communication","product_knowledge","objection_handling",
                    "closing_technique","active_listening"
                ] else skill
                sql = f"""
                    SELECT name, team,
                           ROUND(MIN({col}),2)            AS start_score,
                           ROUND(MAX({col}),2)            AS end_score,
                           ROUND(MAX({col})-MIN({col}),2) AS improvement
                    FROM v_skill_progression
                    GROUP BY user_id, name, team
                    ORDER BY improvement DESC LIMIT 10"""
                df = pd.read_sql_query(sql, conn)

            elif name == "get_rep_profile":
                rep = args.get("rep_name","")
                sql = f"""
                    SELECT ce.name, ce.team, ce.period_month,
                           ROUND(ce.coaching_effectiveness_score,3) AS effectiveness,
                           ROUND(ce.engagement_score,3)             AS engagement,
                           ROUND(ce.skill_score,3)                  AS skill_score,
                           ROUND(bi.quota_attainment*100,1)         AS quota_pct,
                           bi.deals_closed,
                           ROUND(bi.win_rate*100,1)                 AS win_rate_pct
                    FROM v_coaching_effectiveness ce
                    LEFT JOIN v_business_impact bi
                        ON ce.user_id=bi.user_id AND ce.period_month=bi.period_month
                    WHERE ce.name LIKE '%{rep}%'
                    ORDER BY ce.period_month"""
                df = pd.read_sql_query(sql, conn)

            elif name == "get_top_by_metric":
                metric = args.get("metric", "deals_closed")
                limit  = int(args.get("limit", 5))
                # Qualify period_month and team with ce. alias to avoid ambiguity in JOIN
                mf2 = f"AND ce.period_month = '{month}'" if month and month != "all" else ""
                tf2 = f"AND ce.team = '{team}'"          if team  and team  != "all" else ""
                metric_map = {
                    "deals_closed":  "bi.deals_closed",
                    "quota_pct":     "ROUND(bi.quota_attainment*100,1)",
                    "win_rate_pct":  "ROUND(bi.win_rate*100,1)",
                    "effectiveness": "ROUND(ce.coaching_effectiveness_score,3)",
                    "engagement":    "ROUND(ce.engagement_score,3)",
                    "skill_score":   "ROUND(ce.skill_score,3)",
                }
                col = metric_map.get(metric, "bi.deals_closed")
                sql = f"""
                    SELECT ce.name, ce.team, ce.period_month,
                           {col} AS {metric},
                           bi.deals_closed, bi.quota_attainment,
                           ROUND(bi.quota_attainment*100,1) AS quota_pct,
                           ROUND(bi.win_rate*100,1)         AS win_rate_pct,
                           ROUND(ce.coaching_effectiveness_score,3) AS effectiveness
                    FROM v_coaching_effectiveness ce
                    LEFT JOIN v_business_impact bi
                        ON ce.user_id=bi.user_id AND ce.period_month=bi.period_month
                    WHERE {col} IS NOT NULL {mf2} {tf2}
                    ORDER BY {col} DESC
                    LIMIT {limit}"""
                df = pd.read_sql_query(sql, conn)
                df = df.loc[:, ~df.columns.duplicated()]
                df = df.drop(columns=["quota_attainment"], errors="ignore")

            elif name == "compare_skill_progression":
                teams = args.get("teams", "all")
                skill = args.get("skill", "overall")
                col   = "avg_overall_score" if skill in ("overall", "", None) or skill not in [
                    "communication","product_knowledge","objection_handling",
                    "closing_technique","active_listening"
                ] else skill
                team_filter = ""
                if teams and teams != "all":
                    team_list = "', '".join([t.strip() for t in teams.split(",")])
                    team_filter = f"AND team IN ('{team_list}')"
                sql = f"""
                    SELECT period_month, team,
                           ROUND(AVG({col}), 2) AS avg_score
                    FROM v_skill_progression
                    WHERE 1=1 {team_filter}
                    GROUP BY period_month, team
                    ORDER BY period_month, team"""
                df = pd.read_sql_query(sql, conn)

            elif name == "identify_underperforming_segments":
                sql = f"""
                    WITH platform AS (
                        SELECT ROUND(AVG(coaching_effectiveness_score), 3) AS platform_avg
                        FROM v_coaching_effectiveness
                        WHERE 1=1 {mf}
                    )
                    SELECT team, period_month,
                           ROUND(AVG(coaching_effectiveness_score), 3) AS avg_effectiveness,
                           ROUND(AVG(engagement_score), 3)             AS avg_engagement,
                           COUNT(DISTINCT user_id)                     AS rep_count,
                           ROUND(AVG(coaching_effectiveness_score) - (SELECT platform_avg FROM platform), 3) AS vs_platform_avg
                    FROM v_coaching_effectiveness
                    WHERE 1=1 {mf}
                    GROUP BY team, period_month
                    ORDER BY avg_effectiveness ASC"""
                df = pd.read_sql_query(sql, conn)

            elif name == "explain_metric_definition":
                metric_kw = args.get("metric_name", "")
                sql = f"""
                    SELECT metric_name, display_name, description, formula, unit, version
                    FROM metric_definitions
                    WHERE metric_name LIKE '%{metric_kw}%'
                       OR display_name LIKE '%{metric_kw}%'
                    LIMIT 3"""
                df = pd.read_sql_query(sql, conn)

            else:
                df = pd.DataFrame({"error": [f"Unknown tool: {name}"]})

            if _trace is not None:
                _trace["sql"]              = sql.strip()
                _trace["records_returned"] = len(df)

            return df.to_dict("records")
        except Exception as e:
            return [{"error": str(e)}]
        finally:
            conn.close()

    # ── Chat history ──────────────────────────────────────────────────────
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    _ASSETS = Path(__file__).parent / "assets"
    _ROBOT_AVT = str(_ASSETS / "robot_avatar.png")
    _USER_AVT  = "👤"
    for msg_idx, msg in enumerate(st.session_state.chat_history):
        _avatar = _ROBOT_AVT if msg["role"] == "assistant" else _USER_AVT
        with st.chat_message(msg["role"], avatar=_avatar):
            # ── User message: editable prompt ────────────────────────────────
            if msg["role"] == "user":
                _emk = f"edit_msg_{msg_idx}"
                if st.session_state.get(_emk, False):
                    _new_q = st.text_area("", value=msg["content"], height=80,
                                          key=f"edit_ta_{msg_idx}", label_visibility="collapsed")
                    _c1, _c2, _ = st.columns([1.2, 1, 6])
                    if _c1.button("↩ Re-send", key=f"resend_{msg_idx}"):
                        st.session_state.chat_history = st.session_state.chat_history[:msg_idx]
                        st.session_state.chat_history.append({"role": "user", "content": _new_q})
                        st.session_state[_emk] = False
                        st.session_state["_processing"] = True
                        st.rerun()
                    if _c2.button("✕ Cancel", key=f"cancel_edit_{msg_idx}"):
                        st.session_state[_emk] = False
                        st.rerun()
                else:
                    st.markdown(msg["content"])
                    if st.button("✏️ Edit", key=f"edit_user_{msg_idx}"):
                        st.session_state[_emk] = True
                        st.rerun()
                continue
            # ── Assistant message ─────────────────────────────────────────────
            st.markdown(msg["content"])
            if msg.get("tools_used"):
                label = f"🔍 Agent trace — {', '.join(msg['tools_used'])}"
                with st.expander(label, expanded=False):
                    if msg.get("question"):
                        st.markdown(f"**Question interpreted as:** {msg['question']}")
                        st.divider()
                    for i, entry in enumerate(msg.get("trace", [])):
                        st.markdown(
                            f'<p style="margin:4px 0"><span style="color:#94a3b8;font-weight:600;font-size:0.88rem">Tool selected:</span>&nbsp;&nbsp;'
                            f'<span style="background:rgba(52,211,153,0.15);color:#34d399;border:1px solid rgba(52,211,153,0.45);'
                            f'padding:3px 10px;border-radius:6px;font-family:monospace;font-size:0.82rem;display:inline-block">{entry.get("tool","?")}</span></p>',
                            unsafe_allow_html=True)
                        filters = {k: v for k, v in entry.get("args", {}).items()
                                   if v and v not in ("all", None)}
                        if filters:
                            st.markdown(
                                f'<p style="margin:4px 0"><span style="color:#94a3b8;font-weight:600;font-size:0.88rem">Filters applied:</span>&nbsp;&nbsp;'
                                f'<span style="background:rgba(56,189,248,0.1);color:#38bdf8;border:1px solid rgba(56,189,248,0.4);'
                                f'padding:3px 10px;border-radius:6px;font-family:monospace;font-size:0.82rem;display:inline-block">{filters}</span></p>',
                                unsafe_allow_html=True)
                        if entry.get("sql"):
                            _sql_key    = f"sql_{msg_idx}_{i}"
                            _edit_key   = f"editing_{msg_idx}_{i}"
                            _result_key = f"result_{msg_idx}_{i}"
                            if _sql_key not in st.session_state:
                                st.session_state[_sql_key] = entry["sql"].strip()
                            if st.session_state.get(_edit_key, False):
                                # ── Edit mode: code block replaced by text area ──
                                _new_sql = st.text_area(
                                    "",
                                    value=st.session_state[_sql_key],
                                    height=160,
                                    key=f"ta_{msg_idx}_{i}",
                                    label_visibility="collapsed",
                                )
                                _btn_l, _btn_r, _ = st.columns([1, 1, 6])
                                if _btn_l.button("▶ Run", key=f"btn_run_{msg_idx}_{i}"):
                                    try:
                                        _res = query(_new_sql)
                                        st.session_state[_sql_key]    = _new_sql
                                        st.session_state[_result_key] = _res
                                        st.session_state[_edit_key]   = False
                                    except Exception as _e:
                                        st.error(f"Query error: {_e}")
                                    st.rerun()
                                if _btn_r.button("✕ Cancel", key=f"btn_cancel_{msg_idx}_{i}"):
                                    st.session_state[_edit_key] = False
                                    st.rerun()
                            else:
                                # ── View mode: code block + edit button ──
                                st.code(st.session_state[_sql_key], language="sql")
                                if st.button("✏️ Edit query", key=f"btn_edit_{msg_idx}_{i}"):
                                    st.session_state[_edit_key] = True
                                    st.rerun()
                            if _result_key in st.session_state:
                                st.markdown("**Edited query result:**")
                                dark_table(st.session_state[_result_key])
                        st.markdown(f"**Records returned:** {entry.get('records_returned', '?')}")
                        if i < len(msg.get("trace", [])) - 1:
                            st.divider()
                    if msg.get("data"):
                        st.markdown("**Result data:**")
                        dark_table(pd.DataFrame(msg["data"]))

    # Example prompts on first load
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
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        st.session_state["_processing"] = True
        st.rerun()

    if st.session_state.get("_processing"):
        st.session_state["_processing"] = False
        user_q = st.session_state.chat_history[-1]["content"]

        # ── Conversational pre-filter — no tool call needed ──────────
        # If the query has no data-related keywords → treat as conversational
        _data_kw = {
            "rep","reps","team","teams","enterprise","smb","emea","apac",
            "deal","deals","quota","win","rate","skill","score","session","sessions",
            "jan","feb","mar","apr","may","jun","2024","2023","2025","month",
            "top","best","worst","compare","show","give","list","find","get",
            "who","which","what","how","performance","metric","metrics",
            "engagement","effectiveness","coaching","progression","improvement",
            "first","1st","2nd","3rd","last","highest","lowest","most","least"
        }
        _lower_q = user_q.lower().strip()
        _words = set(_lower_q.translate(str.maketrans("","","?!.,")).split())
        if not _words.intersection(_data_kw):
            _chat_reply = "Glad to help! Ask me anything about the coaching data. 😊"
            if any(g in _lower_q for g in ("hi","hello","hey")):
                _chat_reply = "Hey! Ask me anything about your reps or teams."
            st.session_state.chat_history.append({
                "role": "assistant", "content": _chat_reply,
                "tools_used": [], "data": None, "trace": [], "question": user_q
            })
            st.rerun()

        with st.spinner("Agent thinking..."):
            try:
                client = Groq(api_key=GROQ_API_KEY)

                SYSTEM = (
                    "You are CoachSphere's AI analytics agent for a sales coaching platform. "
                    "You have tools to query real coaching data (Jan–Jun 2024). "
                    "ALWAYS call a tool to look up data before answering — never guess numbers. "
                    "Teams: Enterprise, SMB, EMEA, APAC. After getting data, give a concise answer with specific numbers. "

                    "MONTH PARSING — do this FIRST before interpreting anything else: "
                    "Convert any month reference to YYYY-MM format. Common abbreviations and typos to recognise: "
                    "jan/jn → 2024-01, feb/fb → 2024-02, mar/mr → 2024-03, "
                    "apr/ap/apu/aprl → 2024-04, may → 2024-05, jun/jn/june → 2024-06. "
                    "If the user writes a 2-digit year like '24', treat it as 2024. "
                    "Examples: 'apr 24' → month=2024-04, 'apu 24' → month=2024-04 (typo for apr), "
                    "'jun 24' → month=2024-06, 'march' → month=2024-03. "
                    "NEVER interpret a 3-letter month abbreviation (jan/feb/mar/apr/may/jun) as a team name. "
                    "Teams are only: Enterprise, SMB, EMEA, APAC. "
                    "If no month is specified, use month='all'. "

                    "IMPORTANT tool selection rules: "
                    "- Use get_top_by_metric for ANY question about ranking reps by a specific metric: "
                    "  'most deals', 'highest win rate', 'best quota attainment', 'most deals closed', etc. "
                    "  Pass the metric name: deals_closed, quota_pct, win_rate_pct, effectiveness, engagement, skill_score. "
                    "- Use get_top_performers only when asked for top reps by overall coaching effectiveness. "
                    "- Use get_rep_profile only when you already know a rep's name and want their full history. "
                    "  Do NOT call get_rep_profile just to enrich results from another tool. "
                    "- Use identify_underperforming_segments when asked about struggling, weak, or at-risk teams. "
                    "- Use compare_skill_progression to compare skills across teams or over time. "
                    "- Use explain_metric_definition when asked how a metric is defined or calculated. "
                    "- Never say a rep was 'not found' if a tool returned data — report what you found. "
                    "- Call only ONE tool per question unless a second tool is truly necessary. "
                    "- For greetings, thanks, acknowledgements, or any non-data message "
                    "(e.g. 'hi', 'thanks', 'okay', 'good', 'great', 'cool', 'nice', 'got it', 'okay that's good'), "
                    "NEVER call a tool. Just reply conversationally in one short sentence. "

                    "EMPTY / OUT-OF-RANGE DATA HANDLING — if a tool returns an empty result or no rows: "
                    "ALWAYS respond with exactly: "
                    "'No data found for that period. The dataset covers January–June 2024.' "
                    "Do NOT say 'could not be found', do NOT make up data, do NOT suggest alternatives. "
                    "This applies when the user asks about any month outside Jan–Jun 2024 (e.g. Jul 2024, Jan 2025, any 2023 date), "
                    "or any team/rep that does not exist in the data. "

                    "If data reveals a team or rep performing below the platform average or below quota < 70%, "
                    "end your response with a BLANK LINE followed by '💡 AI Suggestion (not a fact):' on its own line, "
                    "then one specific actionable coaching recommendation. Always put the suggestion on a separate paragraph."
                )

                # Build messages with last 6 turns of history for follow-up chaining
                history_msgs = []
                prior = st.session_state.chat_history[:-1]  # exclude current user msg
                for h in prior[-6:]:
                    if h["role"] in ("user", "assistant"):
                        history_msgs.append({"role": h["role"], "content": h["content"]})

                messages = (
                    [{"role": "system", "content": SYSTEM}]
                    + history_msgs
                    + [{"role": "user", "content": user_q}]
                )

                tools_used    = []
                last_data     = None
                trace_entries = []

                # ── Agentic loop (max 5 iterations) ──────────────────────
                for _ in range(5):
                    response = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=messages,
                        tools=TOOLS,
                        tool_choice="auto",
                        temperature=0
                    )
                    resp_msg = response.choices[0].message

                    if resp_msg.tool_calls:
                        # Add assistant turn with tool_calls
                        messages.append({
                            "role": "assistant",
                            "content": resp_msg.content or "",
                            "tool_calls": [
                                {
                                    "id": tc.id,
                                    "type": "function",
                                    "function": {
                                        "name": tc.function.name,
                                        "arguments": tc.function.arguments
                                    }
                                } for tc in resp_msg.tool_calls
                            ]
                        })
                        # Execute each tool and feed results back
                        for tc in resp_msg.tool_calls:
                            fn_name      = tc.function.name
                            fn_args      = json.loads(tc.function.arguments)
                            _trace_entry = {"tool": fn_name, "args": fn_args, "sql": "", "records_returned": 0}
                            result       = run_tool(fn_name, fn_args, _trace=_trace_entry)
                            trace_entries.append(_trace_entry)
                            tools_used.append(fn_name)
                            last_data = result
                            messages.append({
                                "role":         "tool",
                                "tool_call_id": tc.id,
                                "content":      json.dumps(result)
                            })
                    else:
                        # No more tool calls — final answer reached
                        final_answer = resp_msg.content or "No answer generated."
                        break
                else:
                    final_answer = "Agent reached maximum iterations without a final answer."

                st.session_state.chat_history.append({
                    "role":       "assistant",
                    "content":    final_answer,
                    "tools_used": tools_used,
                    "data":       last_data,
                    "trace":      trace_entries,
                    "question":   user_q,
                })

            except Exception as e:
                err_str = str(e)
                if 'tool_use_failed' in err_str or 'failed_generation' in err_str:
                    # Model generated a malformed tool call (usually due to typos/abbreviations).
                    # Retry once with an explicit instruction to rephrase the query first.
                    try:
                        retry_messages = (
                            [{"role": "system", "content": SYSTEM}]
                            + history_msgs
                            + [{
                                "role": "user",
                                "content": (
                                    f"The user asked: '{user_q}'. "
                                    "This may contain typos or abbreviations. "
                                    "First interpret what they most likely meant "
                                    "(e.g. 'mont of jan' = January 2024, 'top team' = best performing team), "
                                    "then call the appropriate tool to answer it."
                                )
                            }]
                        )
                        retry_tools_used    = []
                        retry_last_data     = None
                        retry_trace_entries = []
                        for _ in range(5):
                            retry_resp = client.chat.completions.create(
                                model="llama-3.3-70b-versatile",
                                messages=retry_messages,
                                tools=TOOLS,
                                tool_choice="auto",
                                temperature=0
                            )
                            retry_msg = retry_resp.choices[0].message
                            if retry_msg.tool_calls:
                                retry_messages.append({
                                    "role": "assistant",
                                    "content": retry_msg.content or "",
                                    "tool_calls": [
                                        {"id": tc.id, "type": "function",
                                         "function": {"name": tc.function.name,
                                                      "arguments": tc.function.arguments}}
                                        for tc in retry_msg.tool_calls
                                    ]
                                })
                                for tc in retry_msg.tool_calls:
                                    fn_name      = tc.function.name
                                    fn_args      = json.loads(tc.function.arguments)
                                    _te          = {"tool": fn_name, "args": fn_args, "sql": "", "records_returned": 0}
                                    result       = run_tool(fn_name, fn_args, _trace=_te)
                                    retry_trace_entries.append(_te)
                                    retry_tools_used.append(fn_name)
                                    retry_last_data = result
                                    retry_messages.append({
                                        "role": "tool", "tool_call_id": tc.id,
                                        "content": json.dumps(result)
                                    })
                            else:
                                final_answer = retry_msg.content or "No answer generated."
                                break
                        else:
                            final_answer = "I understood your question but couldn't retrieve the data. Please try rephrasing."
                        st.session_state.chat_history.append({
                            "role":       "assistant",
                            "content":    final_answer,
                            "tools_used": retry_tools_used,
                            "data":       retry_last_data,
                            "trace":      retry_trace_entries,
                            "question":   user_q,
                        })
                    except Exception:
                        st.session_state.chat_history.append({
                            "role":    "assistant",
                            "content": "I couldn't interpret that query. Try: *'Which team performed best in January 2024?'*",
                            "tools_used": [], "data": None, "trace": [], "question": user_q,
                        })
                elif 'invalid_api_key' in err_str or '401' in err_str:
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": "Invalid API key. Please check your Groq API key in Streamlit secrets.",
                        "tools_used": [], "data": None, "trace": [], "question": user_q,
                    })
                else:
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": f"Something went wrong: {err_str}",
                        "tools_used": [], "data": None, "trace": [], "question": user_q,
                    })

        st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🔌 MCP Server":
    st.markdown(f"""<div class="page-hero">
        <div class="hero-title">{_icon('icon_mcp.png')} MCP Server</div>
        <div class="hero-sub">CoachSphere exposes its analytics tools via the Model Context Protocol — click any tool to run it live</div>
    </div>""", unsafe_allow_html=True)

    col_s, _ = st.columns([1, 4])
    with col_s:
        st.markdown('<div class="mcp-badge"><span class="pulse"></span> SERVER ACTIVE</div>', unsafe_allow_html=True)

    st.markdown('<div style="height:20px"></div>', unsafe_allow_html=True)

    # Architecture
    st.markdown('<div class="section-title">Architecture</div>', unsafe_allow_html=True)
    ca, cb, cc, cd, ce = st.columns([2, 1, 2, 1, 2])
    with ca:
        st.markdown("""<div class="arch-box"><div class="arch-label">Human Interface</div>
            <div class="arch-name">Streamlit UI</div><div class="arch-sub">localhost:8501</div></div>""", unsafe_allow_html=True)
    with cb:
        st.markdown('<div style="text-align:center;padding-top:28px;color:#475569;font-size:1.4rem;">⟷</div>', unsafe_allow_html=True)
    with cc:
        st.markdown("""<div class="arch-box" style="border-color:rgba(52,211,153,0.3)"><div class="arch-label">Data Layer</div>
            <div class="arch-name">SQLite + SQL Views</div><div class="arch-sub" style="color:#34d399">6 metric views · 5 tables</div></div>""", unsafe_allow_html=True)
    with cd:
        st.markdown('<div style="text-align:center;padding-top:28px;color:#475569;font-size:1.4rem;">⟷</div>', unsafe_allow_html=True)
    with ce:
        st.markdown("""<div class="arch-box" style="border-color:rgba(129,140,248,0.3)"><div class="arch-label">AI Client Interface</div>
            <div class="arch-name">MCP Server</div><div class="arch-sub" style="color:#818cf8">Claude Desktop · any LLM client</div></div>""", unsafe_allow_html=True)

    st.markdown('<div style="height:24px"></div>', unsafe_allow_html=True)

    # ── Tool selection ────────────────────────────────────────────────────────
    TOOLS_META = [
        {"name": "get_top_performers",               "emoji": "🏆", "desc": "Top 5 reps by coaching effectiveness",       "params": ["month", "team"]},
        {"name": "get_team_summary",                 "emoji": "👥", "desc": "Team engagement + effectiveness scores",      "params": ["month"]},
        {"name": "get_quota_attainment",             "emoji": "📈", "desc": "Quota %, win rate, deals by team",           "params": ["month", "team"]},
        {"name": "get_session_stats",                "emoji": "📅", "desc": "Session completion rates by team",           "params": ["month", "team"]},
        {"name": "get_skill_improvement",            "emoji": "🧠", "desc": "Most improved reps by skill",                "params": ["skill"]},
        {"name": "get_rep_profile",                  "emoji": "🔍", "desc": "Full 6-month history for a named rep",       "params": ["rep_name"]},
        {"name": "get_top_by_metric",                "emoji": "🥇", "desc": "Rank reps by any metric",                   "params": ["metric", "month", "team"]},
        {"name": "compare_skill_progression",        "emoji": "📊", "desc": "Skill trends across teams over time",        "params": ["teams", "skill"]},
        {"name": "identify_underperforming_segments","emoji": "⚠️",  "desc": "Teams performing below platform average",   "params": ["month"]},
        {"name": "explain_metric_definition",        "emoji": "📋", "desc": "KPI formula, description, and version",      "params": ["metric_name"]},
    ]

    if "mcp_selected" not in st.session_state:
        st.session_state.mcp_selected = "get_top_performers"

    st.markdown('<div class="section-title">10 Exposed Tools — Click to Run</div>', unsafe_allow_html=True)
    col_l, col_r = st.columns(2)
    for i, tool in enumerate(TOOLS_META):
        is_sel = (st.session_state.mcp_selected == tool["name"])
        border = "rgba(56,189,248,0.55)" if is_sel else "rgba(56,189,248,0.08)"
        bg     = "#0d2137"               if is_sel else "#0a1628"
        nc     = "#38bdf8"               if is_sel else "#475569"
        col = col_l if i % 2 == 0 else col_r
        with col:
            st.markdown(f"""<div style="background:{bg};border-radius:12px;padding:13px 16px;
                border:1px solid {border};margin-bottom:2px;transition:all 0.2s;">
                <span style="font-weight:700;color:{nc};font-family:monospace;font-size:0.85rem">
                    {tool['emoji']}  {tool['name']}()</span>
                <div style="color:#334155;font-size:0.78rem;margin-top:3px">{tool['desc']}</div>
            </div>""", unsafe_allow_html=True)
            if st.button("▶ Run", key=f"mcp_{tool['name']}", use_container_width=True):
                st.session_state.mcp_selected = tool["name"]
                st.rerun()

    # ── Live result ───────────────────────────────────────────────────────────
    sel = st.session_state.mcp_selected
    tool_meta = next(t for t in TOOLS_META if t["name"] == sel)

    st.markdown(f'<div class="section-title" style="margin-top:28px">Live Result — '
                f'<span style="color:#38bdf8;font-family:monospace">{sel}()</span></div>',
                unsafe_allow_html=True)

    months_list  = query("SELECT DISTINCT period_month FROM v_coaching_effectiveness ORDER BY period_month")['period_month'].tolist()
    reps_list    = query("SELECT DISTINCT name FROM users WHERE role != 'Team Lead' ORDER BY name")['name'].tolist()
    skills_list  = ["overall","communication","product_knowledge","objection_handling","closing_technique","active_listening"]
    metrics_list = ["deals_closed","quota_pct","win_rate_pct","effectiveness","engagement","skill_score"]

    params = {}
    if tool_meta["params"]:
        pcols = st.columns(len(tool_meta["params"]))
        for i, param in enumerate(tool_meta["params"]):
            with pcols[i]:
                if param == "month":
                    params["month"] = st.selectbox("month", months_list, index=len(months_list)-1, key=f"pp_month_{sel}")
                elif param == "team":
                    params["team"] = st.selectbox("team", ["all","Enterprise","SMB","EMEA","APAC"], key=f"pp_team_{sel}")
                elif param == "skill":
                    params["skill"] = st.selectbox("skill", skills_list, key=f"pp_skill_{sel}")
                elif param == "metric":
                    params["metric"] = st.selectbox("metric", metrics_list, key=f"pp_metric_{sel}")
                elif param == "teams":
                    params["teams"] = st.text_input("teams (comma-sep or 'all')", "all", key=f"pp_teams_{sel}")
                elif param == "rep_name":
                    params["rep_name"] = st.selectbox("rep_name", reps_list, key=f"pp_rep_{sel}")
                elif param == "metric_name":
                    params["metric_name"] = st.text_input("metric_name", "engagement", key=f"pp_mname_{sel}")

    param_str = ", ".join(f'{k}="{v}"' for k, v in params.items())
    with st.expander("MCP tool call", expanded=True):
        st.code(f"{sel}({param_str})", language="python")

    month = params.get("month", "all")
    team  = params.get("team", "all")
    mf = f"AND period_month = '{month}'" if month and month != "all" else ""
    tf = f"AND team = '{team}'"          if team  and team  != "all" else ""
    result_df = None

    if sel == "get_top_performers":
        result_df = query(f"""SELECT name, team, period_month,
            ROUND(coaching_effectiveness_score,3) AS effectiveness,
            ROUND(engagement_score,3) AS engagement, ROUND(skill_score,3) AS skill_score
            FROM v_coaching_effectiveness WHERE 1=1 {mf} {tf}
            ORDER BY coaching_effectiveness_score DESC LIMIT 5""")
    elif sel == "get_team_summary":
        result_df = query(f"""SELECT team, period_month, active_reps,
            ROUND(avg_engagement,3) AS avg_engagement, ROUND(avg_effectiveness,3) AS avg_effectiveness
            FROM v_team_summary WHERE 1=1 {mf} ORDER BY period_month, avg_effectiveness DESC""")
    elif sel == "get_quota_attainment":
        result_df = query(f"""SELECT team, period_month, ROUND(AVG(quota_attainment)*100,1) AS avg_quota_pct,
            ROUND(AVG(win_rate)*100,1) AS avg_win_rate_pct, SUM(deals_closed) AS total_deals
            FROM v_business_impact WHERE 1=1 {mf} {tf} GROUP BY team, period_month
            ORDER BY period_month, avg_quota_pct DESC""")
    elif sel == "get_session_stats":
        result_df = query(f"""SELECT team, period_month, SUM(sessions_scheduled) AS scheduled,
            SUM(sessions_completed) AS completed,
            ROUND(CAST(SUM(sessions_completed) AS REAL)/SUM(sessions_scheduled)*100,1) AS completion_pct
            FROM v_session_engagement WHERE 1=1 {mf} {tf} GROUP BY team, period_month ORDER BY period_month""")
    elif sel == "get_skill_improvement":
        sk = params.get("skill","overall")
        sc = sk if sk in {"communication","product_knowledge","objection_handling","closing_technique","active_listening"} else "avg_overall_score"
        result_df = query(f"""SELECT name, team, ROUND(MIN({sc}),2) AS start_score,
            ROUND(MAX({sc}),2) AS end_score, ROUND(MAX({sc})-MIN({sc}),2) AS improvement
            FROM v_skill_progression GROUP BY user_id, name, team ORDER BY improvement DESC LIMIT 10""")
    elif sel == "get_rep_profile":
        rep = params.get("rep_name","")
        result_df = query(f"""SELECT ce.name, ce.team, ce.period_month,
            ROUND(ce.coaching_effectiveness_score,3) AS effectiveness, ROUND(ce.engagement_score,3) AS engagement,
            ROUND(ce.skill_score,3) AS skill_score, ROUND(bi.quota_attainment*100,1) AS quota_pct,
            bi.deals_closed, ROUND(bi.win_rate*100,1) AS win_rate_pct
            FROM v_coaching_effectiveness ce LEFT JOIN v_business_impact bi
            ON ce.user_id=bi.user_id AND ce.period_month=bi.period_month
            WHERE ce.name LIKE '%{rep}%' ORDER BY ce.period_month""")
    elif sel == "get_top_by_metric":
        metric = params.get("metric","deals_closed")
        mm = {"deals_closed":"bi.deals_closed","quota_pct":"ROUND(bi.quota_attainment*100,1)",
              "win_rate_pct":"ROUND(bi.win_rate*100,1)","effectiveness":"ROUND(ce.coaching_effectiveness_score,3)",
              "engagement":"ROUND(ce.engagement_score,3)","skill_score":"ROUND(ce.skill_score,3)"}
        col_expr = mm.get(metric,"bi.deals_closed")
        mf2 = f"AND ce.period_month='{month}'" if month and month != "all" else ""
        tf2 = f"AND ce.team='{team}'"           if team  and team  != "all" else ""
        result_df = query(f"""SELECT ce.name, ce.team, ce.period_month, {col_expr} AS {metric},
            bi.deals_closed, ROUND(bi.quota_attainment*100,1) AS quota_pct, ROUND(bi.win_rate*100,1) AS win_rate_pct
            FROM v_coaching_effectiveness ce LEFT JOIN v_business_impact bi
            ON ce.user_id=bi.user_id AND ce.period_month=bi.period_month
            WHERE {col_expr} IS NOT NULL {mf2} {tf2} ORDER BY {col_expr} DESC LIMIT 5""")
    elif sel == "compare_skill_progression":
        teams = params.get("teams","all")
        sk    = params.get("skill","overall")
        sc    = sk if sk in {"communication","product_knowledge","objection_handling","closing_technique","active_listening"} else "avg_overall_score"
        if teams and teams != "all":
            _tlist = "', '".join([t.strip() for t in teams.split(",")])
            tmf = f"AND team IN ('{_tlist}')"
        else:
            tmf = ""
        result_df = query(f"""SELECT period_month, team, ROUND(AVG({sc}),2) AS avg_score
            FROM v_skill_progression WHERE 1=1 {tmf} GROUP BY period_month, team ORDER BY period_month, team""")
    elif sel == "identify_underperforming_segments":
        result_df = query(f"""WITH platform AS (SELECT ROUND(AVG(coaching_effectiveness_score),3) AS platform_avg
            FROM v_coaching_effectiveness WHERE 1=1 {mf})
            SELECT team, period_month, ROUND(AVG(coaching_effectiveness_score),3) AS avg_effectiveness,
            ROUND(AVG(engagement_score),3) AS avg_engagement, COUNT(DISTINCT user_id) AS rep_count,
            ROUND(AVG(coaching_effectiveness_score)-(SELECT platform_avg FROM platform),3) AS vs_platform_avg
            FROM v_coaching_effectiveness WHERE 1=1 {mf} GROUP BY team, period_month ORDER BY avg_effectiveness ASC""")
    elif sel == "explain_metric_definition":
        mn = params.get("metric_name","engagement")
        result_df = query(f"""SELECT metric_name, display_name, description, formula, unit, version
            FROM metric_definitions WHERE metric_name LIKE '%{mn}%' OR display_name LIKE '%{mn}%' LIMIT 3""")

    if result_df is not None and not result_df.empty:
        col_cfg = {}
        if "effectiveness" in result_df.columns:
            col_cfg["effectiveness"] = st.column_config.ProgressColumn("Effectiveness", min_value=0, max_value=1)
        if "engagement" in result_df.columns:
            col_cfg["engagement"] = st.column_config.ProgressColumn("Engagement", min_value=0, max_value=1)
        dark_table(result_df)
    else:
        st.info("No data returned for these parameters.")

    st.markdown('<div style="height:16px"></div>', unsafe_allow_html=True)
    st.markdown("""<div class="arch-box" style="text-align:left;padding:22px 26px">
        <div style="color:#38bdf8;font-size:0.7rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:14px">Connect to Claude Desktop</div>
        <div style="display:flex;flex-direction:column;gap:10px">
            <div style="display:flex;align-items:flex-start;gap:12px">
                <span style="background:rgba(56,189,248,0.15);color:#38bdf8;border:1px solid rgba(56,189,248,0.3);border-radius:50%;width:24px;height:24px;display:flex;align-items:center;justify-content:center;font-size:0.75rem;font-weight:700;flex-shrink:0">1</span>
                <span style="color:#94a3b8;font-size:0.83rem;line-height:1.6">Install the MCP library &nbsp;<code style="background:rgba(56,189,248,0.1);color:#38bdf8;border:1px solid rgba(56,189,248,0.25);padding:2px 8px;border-radius:5px;font-family:monospace">pip install "mcp[cli]"</code></span>
            </div>
            <div style="display:flex;align-items:flex-start;gap:12px">
                <span style="background:rgba(56,189,248,0.15);color:#38bdf8;border:1px solid rgba(56,189,248,0.3);border-radius:50%;width:24px;height:24px;display:flex;align-items:center;justify-content:center;font-size:0.75rem;font-weight:700;flex-shrink:0">2</span>
                <span style="color:#94a3b8;font-size:0.83rem;line-height:1.6">Add <code style="background:rgba(56,189,248,0.1);color:#38bdf8;border:1px solid rgba(56,189,248,0.25);padding:2px 8px;border-radius:5px;font-family:monospace">claude_desktop_config.json</code> block to Claude Desktop → Settings → Developer → Edit Config</span>
            </div>
            <div style="display:flex;align-items:flex-start;gap:12px">
                <span style="background:rgba(52,211,153,0.15);color:#34d399;border:1px solid rgba(52,211,153,0.3);border-radius:50%;width:24px;height:24px;display:flex;align-items:center;justify-content:center;font-size:0.75rem;font-weight:700;flex-shrink:0">3</span>
                <span style="color:#94a3b8;font-size:0.83rem;line-height:1.6">Restart Claude Desktop — all <span style="color:#34d399;font-weight:600">10 tools</span> appear automatically in the chat bar</span>
            </div>
        </div>
    </div>""", unsafe_allow_html=True)

