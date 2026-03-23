import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timedelta

st.set_page_config(
    page_title="RunQuest",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

@st.cache_resource
def get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)
sb = get_supabase()

# ─── HELPERS ────────────────────────────────────────────────────
def format_time(seconds):
    if not seconds: return "00:00"
    h = int(seconds // 3600); m = int((seconds % 3600) // 60); s = int(seconds % 60)
    return f"{h}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"

def format_pace(seconds, distance_km, unit='km'):
    if not distance_km or distance_km == 0: return "--:--"
    pace = (seconds / 60) / distance_km
    if unit == 'mi': pace = pace / 1.60934
    m = int(pace); s = int((pace - m) * 60)
    return f"{m}:{s:02d}"

def format_distance(km, unit='km'):
    return round(km * 0.621371, 2) if unit == 'mi' else round(km, 2)

def is_this_week(date_str):
    try:
        d = datetime.fromisoformat(date_str.replace('Z', '+00:00')).replace(tzinfo=None)
        today = datetime.utcnow()
        start = (today - timedelta(days=today.weekday())).replace(hour=0, minute=0, second=0)
        return d >= start
    except: return False

# ─── RPG ────────────────────────────────────────────────────────
RANKS = [
    {"level": 1,  "title": "Wanderer",     "min_xp": 0,    "icon": "🥾"},
    {"level": 2,  "title": "Jogger",       "min_xp": 100,  "icon": "🏃"},
    {"level": 3,  "title": "Pacer",        "min_xp": 300,  "icon": "⚡"},
    {"level": 4,  "title": "Strider",      "min_xp": 600,  "icon": "💨"},
    {"level": 5,  "title": "Racer",        "min_xp": 1000, "icon": "🔥"},
    {"level": 6,  "title": "Sprinter",     "min_xp": 1500, "icon": "⚔️"},
    {"level": 7,  "title": "Champion",     "min_xp": 2200, "icon": "👑"},
    {"level": 8,  "title": "Legend",       "min_xp": 3000, "icon": "🌟"},
    {"level": 9,  "title": "Mythic",       "min_xp": 4000, "icon": "🌌"},
    {"level": 10, "title": "Transcendent", "min_xp": 5500, "icon": "💫"},
]
QUESTS = [
    {"id": "first_run",     "title": "First Step",         "desc": "Complete your very first run",       "icon": "👟", "xp": 50},
    {"id": "run_5km",       "title": "Five Kilometers",    "desc": "Run 5km in a single session",        "icon": "🎯", "xp": 75},
    {"id": "run_10km",      "title": "Double Digits",      "desc": "Run 10km in a single session",       "icon": "🏅", "xp": 150},
    {"id": "run_3_times",   "title": "Habit Forming",      "desc": "Complete 3 runs total",              "icon": "🔄", "xp": 60},
    {"id": "run_7_times",   "title": "Weekly Warrior",     "desc": "Complete 7 runs total",              "icon": "⚔️", "xp": 120},
    {"id": "sub_6_pace",    "title": "Speed Seeker",       "desc": "Run a pace under 6:00 min/km",       "icon": "⚡", "xp": 80},
    {"id": "sub_5_pace",    "title": "Lightning Legs",     "desc": "Run a pace under 5:00 min/km",       "icon": "🌩️", "xp": 200},
    {"id": "total_50km",    "title": "Fifty & Counting",   "desc": "Accumulate 50km total",              "icon": "🗺️", "xp": 200},
    {"id": "total_100km",   "title": "Century Runner",     "desc": "Accumulate 100km total",             "icon": "💯", "xp": 400},
    {"id": "half_marathon", "title": "Half the Glory",     "desc": "Complete a half marathon (21.1km)",  "icon": "🎖️", "xp": 300},
    {"id": "full_marathon", "title": "Marathon Legend",    "desc": "Complete a full marathon (42.2km)",  "icon": "🏆", "xp": 1000},
    {"id": "run_streak_3",  "title": "On a Roll",          "desc": "Run 3 days in a row",                "icon": "🔥", "xp": 100},
    {"id": "run_streak_7",  "title": "Unstoppable",        "desc": "Run 7 days in a row",                "icon": "💥", "xp": 250},
]

def get_rank(xp):
    rank = RANKS[0]
    for r in RANKS:
        if xp >= r["min_xp"]: rank = r
    return rank

def get_next_rank(xp):
    current = get_rank(xp)
    for r in RANKS:
        if r["level"] == current["level"] + 1: return r
    return None

def get_xp_progress(xp):
    current = get_rank(xp); next_r = get_next_rank(xp)
    if not next_r: return 100
    return min(100, int(((xp - current["min_xp"]) / (next_r["min_xp"] - current["min_xp"])) * 100))

def calculate_xp(distance_km, duration_seconds, is_pb=False):
    xp = int(distance_km * 10)
    pace = (duration_seconds / 60) / distance_km if distance_km else 999
    if pace < 5: xp += 30
    elif pace < 6: xp += 15
    if distance_km >= 5: xp += 20
    if distance_km >= 10: xp += 40
    if distance_km >= 21: xp += 100
    if is_pb: xp += 50
    return xp

def has_streak(runs, days):
    if len(runs) < days: return False
    dates = sorted(set([r["started_at"][:10] for r in runs]))
    streak = 1
    for i in range(1, len(dates)):
        if (datetime.fromisoformat(dates[i]) - datetime.fromisoformat(dates[i-1])).days == 1:
            streak += 1
            if streak >= days: return True
        else: streak = 1
    return False

def check_quest(quest_id, runs):
    total_dist = sum(r["distance_km"] for r in runs)
    if quest_id == "first_run":     return len(runs) >= 1
    if quest_id == "run_5km":       return any(r["distance_km"] >= 5 for r in runs)
    if quest_id == "run_10km":      return any(r["distance_km"] >= 10 for r in runs)
    if quest_id == "run_3_times":   return len(runs) >= 3
    if quest_id == "run_7_times":   return len(runs) >= 7
    if quest_id == "sub_6_pace":    return any((r["duration_seconds"]/60/r["distance_km"]) < 6 for r in runs if r["distance_km"] > 0)
    if quest_id == "sub_5_pace":    return any((r["duration_seconds"]/60/r["distance_km"]) < 5 for r in runs if r["distance_km"] > 0)
    if quest_id == "total_50km":    return total_dist >= 50
    if quest_id == "total_100km":   return total_dist >= 100
    if quest_id == "half_marathon": return any(r["distance_km"] >= 21.1 for r in runs)
    if quest_id == "full_marathon": return any(r["distance_km"] >= 42.2 for r in runs)
    if quest_id == "run_streak_3":  return has_streak(runs, 3)
    if quest_id == "run_streak_7":  return has_streak(runs, 7)
    return False

# ─── DB ─────────────────────────────────────────────────────────
def get_profile(user_id):
    res = sb.table("profiles").select("*").eq("id", user_id).execute()
    if res.data: return res.data[0]
    sb.table("profiles").insert({"id": user_id, "xp": 0, "unit": "km", "completed_quests": []}).execute()
    return {"id": user_id, "xp": 0, "unit": "km", "completed_quests": []}

def get_runs(user_id):
    res = sb.table("runs").select("*").eq("user_id", user_id).order("started_at", desc=True).execute()
    return res.data or []

def save_run(user_id, distance_km, duration_seconds, xp_earned, is_pb):
    sb.table("runs").insert({
        "user_id": user_id, "distance_km": distance_km,
        "duration_seconds": duration_seconds, "xp_earned": xp_earned,
        "is_pb": is_pb, "started_at": datetime.utcnow().isoformat()
    }).execute()

def update_profile(user_id, xp, completed_quests, unit):
    sb.table("profiles").upsert({
        "id": user_id, "xp": xp,
        "completed_quests": completed_quests, "unit": unit
    }).execute()

def delete_run(run_id):
    sb.table("runs").delete().eq("id", run_id).execute()

def process_and_save_run(user_id, profile, runs, dist_km, total_seconds, unit_sel):
    existing = [r for r in runs if abs(r["distance_km"] - dist_km) < 0.2]
    is_pb = len(existing) == 0 or total_seconds < min(r["duration_seconds"] for r in existing)
    xp = calculate_xp(dist_km, total_seconds, is_pb)
    prev_completed = [q["id"] for q in QUESTS if check_quest(q["id"], runs)]
    save_run(user_id, dist_km, total_seconds, xp, is_pb)
    new_runs = get_runs(user_id)
    now_completed = [q["id"] for q in QUESTS if check_quest(q["id"], new_runs)]
    fresh_quests = [q for q in QUESTS if q["id"] in now_completed and q["id"] not in prev_completed]
    quest_xp = sum(q["xp"] for q in fresh_quests)
    update_profile(user_id, profile.get("xp", 0) + xp + quest_xp, now_completed, unit_sel)
    return xp + quest_xp, is_pb, fresh_quests

# ─── THEME ──────────────────────────────────────────────────────
def apply_theme(dark_mode=True):
    if dark_mode:
        BG      = "#07090D"
        CARD    = "#0E1118"
        CARD2   = "#131820"
        BORDER  = "#FFB30035"
        BORDER2 = "#FFB30060"
        TEXT    = "#F0E6C8"
        TEXT2   = "#B8A882"
        TEXT3   = "#6B5E42"
        ACCENT  = "#FFB300"
        ACCENT2 = "#FFD700"
        DANGER  = "#FF5555"
        SUCCESS = "#50FA7B"
        SIDEBAR = "#0A0C12"
    else:
        BG      = "#F5F0E8"
        CARD    = "#FFFFFF"
        CARD2   = "#FFF8EC"
        BORDER  = "#FFB30050"
        BORDER2 = "#FFB300"
        TEXT    = "#1A1400"
        TEXT2   = "#5A4A20"
        TEXT3   = "#9A8A60"
        ACCENT  = "#C07800"
        ACCENT2 = "#9A6000"
        DANGER  = "#CC3333"
        SUCCESS = "#2A7A3A"
        SIDEBAR = "#FFF3D4"

    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;600;700;900&family=Exo+2:wght@300;400;500;600;700;800&family=Share+Tech+Mono&display=swap');

    /* ── BASE ── */
    html, body, [class*="css"] {{
        font-family: 'Exo 2', sans-serif !important;
        background-color: {BG} !important;
        color: {TEXT} !important;
        font-size: 16px !important;
    }}
    .stApp {{
        background: {BG} !important;
        background-image: radial-gradient(ellipse at 10% 10%, {"rgba(255,179,0,0.04)" if dark_mode else "rgba(255,179,0,0.08)"} 0%, transparent 60%) !important;
    }}

    /* ── SIDEBAR ── */
    section[data-testid="stSidebar"] {{
        background: {SIDEBAR} !important;
        border-right: 2px solid {BORDER2} !important;
        min-width: 240px !important;
    }}
    section[data-testid="stSidebar"] > div {{
        padding: 0 !important;
    }}

    /* ── BUTTONS ── */
    .stButton > button {{
        font-family: 'Orbitron', sans-serif !important;
        border-radius: 6px !important;
        font-weight: 700 !important;
        font-size: 0.8rem !important;
        letter-spacing: 1.5px !important;
        padding: 12px 20px !important;
        transition: all 0.2s !important;
        border: 1.5px solid {BORDER2} !important;
        background: {"#FFB30018" if dark_mode else "#FFB30015"} !important;
        color: {ACCENT} !important;
        width: 100% !important;
    }}
    .stButton > button:hover {{
        background: {"#FFB30030" if dark_mode else "#FFB30025"} !important;
        border-color: {ACCENT2} !important;
        box-shadow: 0 0 20px rgba(255,179,0,0.25) !important;
        transform: translateY(-1px) !important;
    }}

    /* ── INPUTS ── */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stSelectbox > div > div {{
        background: {CARD} !important;
        color: {TEXT} !important;
        border: 1.5px solid {BORDER2} !important;
        border-radius: 6px !important;
        font-family: 'Exo 2', sans-serif !important;
        font-size: 1rem !important;
        padding: 10px 14px !important;
    }}
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus {{
        border-color: {ACCENT} !important;
        box-shadow: 0 0 12px rgba(255,179,0,0.2) !important;
    }}

    /* ── LABELS ── */
    label, .stTextInput label, .stNumberInput label,
    .stSelectbox label, .stRadio label {{
        color: {TEXT2} !important;
        font-family: 'Exo 2', sans-serif !important;
        font-size: 0.95rem !important;
        font-weight: 600 !important;
    }}

    /* ── TABS ── */
    .stTabs [data-baseweb="tab-list"] {{
        background: {CARD} !important;
        border-bottom: 2px solid {BORDER2} !important;
        gap: 4px !important;
    }}
    .stTabs [data-baseweb="tab"] {{
        font-family: 'Orbitron', sans-serif !important;
        font-size: 0.7rem !important;
        color: {TEXT3} !important;
        letter-spacing: 1px !important;
        padding: 10px 16px !important;
    }}
    .stTabs [aria-selected="true"] {{
        color: {ACCENT} !important;
        border-bottom: 3px solid {ACCENT} !important;
        background: {"rgba(255,179,0,0.08)" if dark_mode else "rgba(255,179,0,0.12)"} !important;
    }}

    /* ── METRICS ── */
    div[data-testid="stMetricValue"] {{
        font-family: 'Orbitron', sans-serif !important;
        color: {ACCENT} !important;
        font-size: 1.6rem !important;
        font-weight: 700 !important;
    }}
    div[data-testid="stMetricLabel"] {{
        font-family: 'Exo 2', sans-serif !important;
        color: {TEXT2} !important;
        font-size: 0.85rem !important;
        font-weight: 600 !important;
    }}

    /* ── RADIO ── */
    .stRadio > div > label {{
        font-family: 'Exo 2', sans-serif !important;
        font-size: 1rem !important;
        font-weight: 600 !important;
        color: {TEXT} !important;
        padding: 8px 16px !important;
    }}

    /* ── ALERTS ── */
    .stAlert > div {{
        font-family: 'Exo 2', sans-serif !important;
        font-size: 0.95rem !important;
        border-radius: 6px !important;
        font-weight: 500 !important;
    }}

    /* ── SCROLLBAR ── */
    ::-webkit-scrollbar {{ width: 4px; }}
    ::-webkit-scrollbar-track {{ background: {BG}; }}
    ::-webkit-scrollbar-thumb {{ background: {BORDER2}; border-radius: 2px; }}

    /* ── HIDE DEFAULT SIDEBAR TOGGLE ON MOBILE ── */
    @media (max-width: 768px) {{
        section[data-testid="stSidebar"] {{ display: none !important; }}
        .main .block-container {{ padding: 1rem 1rem 6rem 1rem !important; }}
    }}
    @media (min-width: 769px) {{
        .bottom-nav {{ display: none !important; }}
        .main .block-container {{ padding: 2rem 2rem 2rem 2rem !important; }}
    }}

    /* ── CUSTOM COMPONENTS ── */

    .rq-logo {{
        font-family: 'Orbitron', sans-serif;
        font-size: 1.6rem;
        font-weight: 900;
        letter-spacing: 4px;
        background: linear-gradient(135deg, {ACCENT2}, {ACCENT}, #FF8C00);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        line-height: 1.2;
    }}
    .rq-logo-sub {{
        font-family: 'Share Tech Mono', monospace;
        font-size: 0.6rem;
        color: {TEXT3};
        letter-spacing: 5px;
        margin-top: 2px;
    }}

    .page-title {{
        font-family: 'Orbitron', sans-serif;
        font-size: 1.5rem;
        font-weight: 800;
        color: {ACCENT};
        letter-spacing: 3px;
        text-transform: uppercase;
        margin-bottom: 2px;
    }}
    .page-sub {{
        font-family: 'Share Tech Mono', monospace;
        font-size: 0.7rem;
        color: {TEXT3};
        letter-spacing: 3px;
        text-transform: uppercase;
        margin-bottom: 16px;
    }}

    .cyber-card {{
        background: {CARD};
        border: 1.5px solid {BORDER2};
        border-radius: 8px;
        padding: 18px 16px;
        margin-bottom: 14px;
        position: relative;
        overflow: hidden;
    }}
    .cyber-card::before {{
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 2px;
        background: linear-gradient(90deg, transparent, {ACCENT}, transparent);
    }}

    .metric-card {{
        background: {CARD};
        border: 1.5px solid {BORDER2};
        border-radius: 8px;
        padding: 16px 10px;
        text-align: center;
        position: relative;
        overflow: hidden;
    }}
    .metric-card::before {{
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 2px;
        background: linear-gradient(90deg, transparent, {ACCENT}, transparent);
    }}
    .metric-value {{
        font-family: 'Orbitron', sans-serif;
        font-size: 1.6rem;
        font-weight: 800;
        color: {ACCENT};
        line-height: 1.1;
    }}
    .metric-label {{
        font-family: 'Exo 2', sans-serif;
        font-size: 0.75rem;
        font-weight: 700;
        color: {TEXT2};
        text-transform: uppercase;
        letter-spacing: 1.5px;
        margin-top: 6px;
    }}

    .run-card {{
        background: {CARD};
        border: 1.5px solid {BORDER};
        border-left: 4px solid {ACCENT};
        border-radius: 8px;
        padding: 14px 16px;
        margin-bottom: 10px;
    }}

    .quest-card {{
        background: {CARD};
        border: 1.5px solid {BORDER};
        border-radius: 8px;
        padding: 14px 16px;
        margin-bottom: 10px;
        transition: all 0.2s;
    }}
    .quest-done {{
        background: {"rgba(255,179,0,0.06)" if dark_mode else "rgba(255,179,0,0.1)"};
        border: 1.5px solid {BORDER2};
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 8px;
    }}

    .xp-bar-outer {{
        background: {CARD2};
        border: 1px solid {BORDER};
        border-radius: 99px;
        height: 10px;
        overflow: hidden;
        margin: 8px 0;
    }}
    .xp-bar-inner {{
        height: 100%;
        background: linear-gradient(90deg, #FF8C00, {ACCENT}, {ACCENT2});
        border-radius: 99px;
        box-shadow: 0 0 8px rgba(255,179,0,0.4);
        transition: width 0.8s ease;
    }}

    .rank-chip {{
        display: inline-block;
        padding: 5px 14px;
        border-radius: 4px;
        font-family: 'Orbitron', sans-serif;
        font-size: 0.7rem;
        font-weight: 700;
        color: {ACCENT};
        background: {"rgba(255,179,0,0.12)" if dark_mode else "rgba(255,179,0,0.15)"};
        border: 1.5px solid {BORDER2};
        letter-spacing: 1.5px;
    }}

    .pb-badge {{
        display: inline-block;
        padding: 3px 10px;
        border-radius: 4px;
        font-family: 'Orbitron', sans-serif;
        font-size: 0.6rem;
        font-weight: 700;
        color: #FFD700;
        background: rgba(255,215,0,0.12);
        border: 1.5px solid rgba(255,215,0,0.5);
        letter-spacing: 1px;
    }}

    .data-val {{
        font-family: 'Share Tech Mono', monospace;
        font-size: 1rem;
        color: {ACCENT};
        font-weight: 600;
    }}
    .data-label {{
        font-family: 'Exo 2', sans-serif;
        font-size: 0.7rem;
        font-weight: 700;
        color: {TEXT3};
        text-transform: uppercase;
        letter-spacing: 1px;
    }}

    .divider {{
        border: none;
        height: 1px;
        background: linear-gradient(90deg, transparent, {BORDER2}, transparent);
        margin: 18px 0;
    }}

    /* ── BOTTOM NAV ── */
    .bottom-nav {{
        position: fixed;
        bottom: 0; left: 0; right: 0;
        background: {SIDEBAR};
        border-top: 2px solid {BORDER2};
        display: flex;
        justify-content: space-around;
        align-items: center;
        padding: 8px 0 12px;
        z-index: 9999;
        box-shadow: 0 -4px 20px rgba(0,0,0,0.4);
    }}
    .nav-item {{
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 3px;
        padding: 4px 8px;
        cursor: pointer;
        border-radius: 6px;
        transition: all 0.15s;
        text-decoration: none;
        min-width: 44px;
    }}
    .nav-item.active {{
        background: rgba(255,179,0,0.15);
    }}
    .nav-icon {{
        font-size: 1.3rem;
        line-height: 1;
    }}
    .nav-label-text {{
        font-family: 'Orbitron', sans-serif;
        font-size: 0.45rem;
        letter-spacing: 0.5px;
        font-weight: 700;
        color: {TEXT3};
        text-transform: uppercase;
    }}
    .nav-item.active .nav-label-text {{ color: {ACCENT}; }}

    /* ── SIDEBAR NAV ITEMS ── */
    .sidebar-nav-item {{
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 12px 16px;
        border-radius: 6px;
        margin: 2px 8px;
        cursor: pointer;
        transition: all 0.15s;
        border: 1px solid transparent;
    }}
    .sidebar-nav-item:hover {{
        background: rgba(255,179,0,0.08);
        border-color: {BORDER2};
    }}
    .sidebar-nav-item.active {{
        background: rgba(255,179,0,0.12);
        border-color: {BORDER2};
        border-left: 3px solid {ACCENT};
    }}
    .sidebar-nav-icon {{ font-size: 1.2rem; }}
    .sidebar-nav-label {{
        font-family: 'Exo 2', sans-serif;
        font-size: 0.95rem;
        font-weight: 700;
        color: {TEXT};
        letter-spacing: 0.5px;
    }}
    .sidebar-nav-item.active .sidebar-nav-label {{ color: {ACCENT}; }}

    /* ── GPS CARDS ── */
    .gps-metric {{
        background: {CARD};
        border: 1.5px solid {BORDER2};
        border-radius: 8px;
        padding: 16px 8px;
        text-align: center;
        position: relative;
        overflow: hidden;
    }}
    .gps-metric::before {{
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 2px;
        background: linear-gradient(90deg, transparent, {ACCENT}, transparent);
    }}
    .gps-value {{
        font-family: 'Orbitron', sans-serif;
        font-size: 2rem;
        font-weight: 900;
        color: {ACCENT};
        line-height: 1;
    }}
    .gps-unit {{
        font-family: 'Share Tech Mono', monospace;
        font-size: 0.6rem;
        color: {TEXT3};
        letter-spacing: 2px;
        margin-top: 4px;
    }}

    </style>
    """, unsafe_allow_html=True)
    return {"BG": BG, "CARD": CARD, "BORDER": BORDER, "BORDER2": BORDER2,
            "TEXT": TEXT, "TEXT2": TEXT2, "TEXT3": TEXT3, "ACCENT": ACCENT,
            "ACCENT2": ACCENT2, "DANGER": DANGER, "SUCCESS": SUCCESS, "SIDEBAR": SIDEBAR,
            "dark_mode": dark_mode}

# ─── BOTTOM NAV HTML ─────────────────────────────────────────────
def render_bottom_nav(current_page, c):
    pages = [
        ("⚡", "HOME",    "Dashboard"),
        ("📍", "GPS",     "GPS Tracker"),
        ("✍️", "LOG",     "Manual Log"),
        ("📋", "HISTORY", "History"),
        ("🎯", "QUESTS",  "Quests"),
        ("📈", "STATS",   "Stats"),
    ]
    items = ""
    for icon, label, page_name in pages:
        active = "active" if current_page == page_name else ""
        items += f"""
        <div class='nav-item {active}' onclick="window.location.href='?nav={page_name.replace(' ','+')}'" >
            <div class='nav-icon'>{icon}</div>
            <div class='nav-label-text'>{label}</div>
        </div>"""
    st.markdown(f"<div class='bottom-nav'>{items}</div>", unsafe_allow_html=True)

# ─── SIDEBAR ────────────────────────────────────────────────────
def render_sidebar(profile, current_page, c):
    pages = [
        ("⚡", "Dashboard"),
        ("📍", "GPS Tracker"),
        ("✍️", "Manual Log"),
        ("📋", "History"),
        ("🎯", "Quests"),
        ("📈", "Stats"),
        ("⚙️", "Settings"),
    ]
    with st.sidebar:
        # Logo block
        st.markdown(f"""
        <div style='padding:24px 16px 16px; border-bottom:1px solid {c["BORDER2"]}40'>
            <div style='font-family:Share Tech Mono,monospace; font-size:0.55rem; color:{c["TEXT3"]}; letter-spacing:4px; margin-bottom:8px'>◈ SYSTEM ACTIVE</div>
            <div class='rq-logo'>RUN<span style='background:none; -webkit-text-fill-color:{c["TEXT"]}'>QUEST</span></div>
            <div class='rq-logo-sub'>PERFORMANCE OS v2.0</div>
        </div>
        """, unsafe_allow_html=True)

        # XP bar in sidebar
        xp = profile.get("xp", 0)
        rank = get_rank(xp)
        progress = get_xp_progress(xp)
        st.markdown(f"""
        <div style='padding:14px 16px; border-bottom:1px solid {c["BORDER2"]}40'>
            <div style='display:flex; align-items:center; gap:10px; margin-bottom:8px'>
                <span style='font-size:1.6rem'>{rank['icon']}</span>
                <div>
                    <div class='rank-chip'>{rank['title'].upper()} · LV.{rank['level']}</div>
                    <div style='font-family:Orbitron,sans-serif; font-size:1rem; font-weight:800; color:{c["ACCENT"]}; margin-top:4px'>{xp:,} <span style='font-size:0.6rem; color:{c["TEXT3"]}'>XP</span></div>
                </div>
            </div>
            <div class='xp-bar-outer'>
                <div class='xp-bar-inner' style='width:{progress}%'></div>
            </div>
            <div style='font-family:Share Tech Mono,monospace; font-size:0.6rem; color:{c["TEXT3"]}; letter-spacing:1px'>{progress}% TO NEXT RANK</div>
        </div>
        """, unsafe_allow_html=True)

        # Navigation
        st.markdown(f"<div style='padding:12px 16px 4px; font-family:Share Tech Mono,monospace; font-size:0.6rem; color:{c['TEXT3']}; letter-spacing:3px'>◈ NAVIGATION</div>", unsafe_allow_html=True)

        selected = current_page
        for icon, page_name in pages:
            active = "active" if selected == page_name else ""
            if st.button(f"{icon}  {page_name}", key=f"nav_{page_name}", use_container_width=True):
                st.session_state.page = page_name
                st.rerun()

        st.markdown(f"<div style='height:1px; background:linear-gradient(90deg,transparent,{c['BORDER2']},transparent); margin:12px 16px'></div>", unsafe_allow_html=True)

        # Account
        st.markdown(f"""
        <div style='padding:8px 16px'>
            <div style='font-family:Share Tech Mono,monospace; font-size:0.6rem; color:{c["TEXT3"]}; letter-spacing:2px; margin-bottom:4px'>◈ OPERATIVE</div>
            <div style='font-family:Exo 2,sans-serif; font-size:0.9rem; font-weight:600; color:{c["TEXT2"]}; word-break:break-all'>{st.session_state.user.email}</div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("⏻  TERMINATE SESSION", key="signout", use_container_width=True):
            sb.auth.sign_out()
            st.session_state.user = None
            st.rerun()

# ─── GPS JS ─────────────────────────────────────────────────────
def gps_component(unit_sel, c):
    html = f"""
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&family=Share+Tech+Mono&family=Exo+2:wght@600&display=swap" rel="stylesheet">
<div id="gps-wrap" style="font-family:'Exo 2',sans-serif;">

  <div id="wakelock-warn" style="display:none; background:rgba(255,179,0,0.1); border:1.5px solid {c['BORDER2']};
    border-radius:8px; padding:12px 16px; margin-bottom:14px; font-family:'Share Tech Mono',monospace;
    font-size:0.8rem; color:{c['ACCENT']}; letter-spacing:1px;">
    ⚠ KEEP SCREEN ACTIVE — DO NOT LOCK DEVICE
  </div>

  <!-- 3 big metrics -->
  <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:10px; margin-bottom:16px;">
    <div class="gps-metric" style="background:{c['CARD']}; border:1.5px solid {c['BORDER2']}; border-radius:8px; padding:16px 8px; text-align:center; position:relative; overflow:hidden;">
      <div style="position:absolute; top:0; left:0; right:0; height:2px; background:linear-gradient(90deg,transparent,{c['ACCENT']},transparent);"></div>
      <div id="dist-val" style="font-family:'Orbitron',sans-serif; font-size:1.8rem; font-weight:900; color:{c['ACCENT']}; line-height:1;">0.00</div>
      <div id="dist-unit" style="font-family:'Share Tech Mono',monospace; font-size:0.6rem; color:{c['TEXT3']}; letter-spacing:2px; margin-top:4px;">{unit_sel.upper()}</div>
    </div>
    <div style="background:{c['CARD']}; border:1.5px solid {c['BORDER2']}; border-radius:8px; padding:16px 8px; text-align:center; position:relative; overflow:hidden;">
      <div style="position:absolute; top:0; left:0; right:0; height:2px; background:linear-gradient(90deg,transparent,{c['ACCENT']},transparent);"></div>
      <div id="time-val" style="font-family:'Orbitron',sans-serif; font-size:1.8rem; font-weight:900; color:{c['TEXT']}; line-height:1;">00:00</div>
      <div style="font-family:'Share Tech Mono',monospace; font-size:0.6rem; color:{c['TEXT3']}; letter-spacing:2px; margin-top:4px;">TIME</div>
    </div>
    <div style="background:{c['CARD']}; border:1.5px solid {c['BORDER2']}; border-radius:8px; padding:16px 8px; text-align:center; position:relative; overflow:hidden;">
      <div style="position:absolute; top:0; left:0; right:0; height:2px; background:linear-gradient(90deg,transparent,{c['ACCENT']},transparent);"></div>
      <div id="pace-val" style="font-family:'Orbitron',sans-serif; font-size:1.8rem; font-weight:900; color:{c['TEXT']}; line-height:1;">--:--</div>
      <div id="pace-unit" style="font-family:'Share Tech Mono',monospace; font-size:0.6rem; color:{c['TEXT3']}; letter-spacing:2px; margin-top:4px;">MIN/{unit_sel.upper()}</div>
    </div>
  </div>

  <!-- Status -->
  <div id="status-txt" style="text-align:center; font-family:'Share Tech Mono',monospace; font-size:0.8rem; color:{c['TEXT3']}; letter-spacing:2px; margin-bottom:12px;">
    [ SYSTEM READY — PRESS INITIATE ]
  </div>
  <div id="gps-acc" style="display:none; text-align:center; font-family:'Share Tech Mono',monospace; font-size:0.75rem; color:{c['TEXT3']}; letter-spacing:1px; margin-bottom:10px;">
    GPS ACCURACY: <span id="acc-val" style="color:{c['ACCENT']};">--</span>m
  </div>

  <!-- Buttons -->
  <div style="display:flex; gap:10px; margin-bottom:14px;">
    <button id="btn-start" onclick="gpsStart()" style="flex:1; padding:15px 8px; border-radius:6px;
      border:2px solid {c['ACCENT']}; cursor:pointer; background:rgba(255,179,0,0.12);
      color:{c['ACCENT']}; font-family:'Orbitron',sans-serif; font-size:0.75rem; font-weight:800; letter-spacing:2px;">
      ▶ INITIATE
    </button>
    <button id="btn-pause" onclick="gpsPause()" style="flex:1; padding:15px 8px; border-radius:6px;
      border:2px solid #FF8C00; cursor:pointer; background:{c['CARD']};
      color:#FF8C00; font-family:'Orbitron',sans-serif; font-size:0.75rem; font-weight:800; letter-spacing:2px; display:none;">
      ⏸ PAUSE
    </button>
    <button id="btn-resume" onclick="gpsResume()" style="flex:1; padding:15px 8px; border-radius:6px;
      border:2px solid {c['ACCENT']}; cursor:pointer; background:rgba(255,179,0,0.12);
      color:{c['ACCENT']}; font-family:'Orbitron',sans-serif; font-size:0.75rem; font-weight:800; letter-spacing:2px; display:none;">
      ▶ RESUME
    </button>
    <button id="btn-stop" onclick="gpsStop()" style="flex:1; padding:15px 8px; border-radius:6px;
      border:2px solid #FF5555; cursor:pointer; background:{c['CARD']};
      color:#FF5555; font-family:'Orbitron',sans-serif; font-size:0.75rem; font-weight:800; letter-spacing:2px; display:none;">
      ■ HALT
    </button>
  </div>

  <!-- Hidden inputs -->
  <input type="hidden" id="f-dist" value="0">
  <input type="hidden" id="f-dur" value="0">

  <!-- Summary -->
  <div id="summary-box" style="display:none; background:{c['CARD']}; border:1.5px solid {c['BORDER2']};
    border-radius:8px; padding:18px; position:relative; overflow:hidden; margin-top:8px;">
    <div style="position:absolute; top:0; left:0; right:0; height:2px; background:linear-gradient(90deg,transparent,{c['ACCENT']},transparent);"></div>
    <div style="font-family:'Orbitron',sans-serif; font-size:0.7rem; font-weight:700; color:{c['ACCENT']}; letter-spacing:2px; margin-bottom:14px;">◈ RUN SUMMARY</div>
    <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-bottom:16px;">
      <div style="text-align:center;">
        <div style="font-family:'Exo 2',sans-serif; font-size:0.7rem; font-weight:700; color:{c['TEXT3']}; text-transform:uppercase; letter-spacing:1px; margin-bottom:4px;">Distance</div>
        <div id="s-dist" style="font-family:'Orbitron',sans-serif; font-size:1.3rem; font-weight:800; color:{c['ACCENT']};"></div>
      </div>
      <div style="text-align:center;">
        <div style="font-family:'Exo 2',sans-serif; font-size:0.7rem; font-weight:700; color:{c['TEXT3']}; text-transform:uppercase; letter-spacing:1px; margin-bottom:4px;">Duration</div>
        <div id="s-time" style="font-family:'Orbitron',sans-serif; font-size:1.3rem; font-weight:800; color:{c['TEXT']};"></div>
      </div>
      <div style="text-align:center;">
        <div style="font-family:'Exo 2',sans-serif; font-size:0.7rem; font-weight:700; color:{c['TEXT3']}; text-transform:uppercase; letter-spacing:1px; margin-bottom:4px;">Avg Pace</div>
        <div id="s-pace" style="font-family:'Orbitron',sans-serif; font-size:1.3rem; font-weight:800; color:{c['TEXT']};"></div>
      </div>
      <div style="text-align:center;">
        <div style="font-family:'Exo 2',sans-serif; font-size:0.7rem; font-weight:700; color:{c['TEXT3']}; text-transform:uppercase; letter-spacing:1px; margin-bottom:4px;">Status</div>
        <div style="font-family:'Orbitron',sans-serif; font-size:1.3rem; font-weight:800; color:{c['ACCENT']};">DONE</div>
      </div>
    </div>
    <button onclick="gpsSave()" style="width:100%; padding:14px; border-radius:6px;
      border:2px solid {c['ACCENT']}; cursor:pointer; background:rgba(255,179,0,0.12);
      color:{c['ACCENT']}; font-family:'Orbitron',sans-serif; font-size:0.8rem; font-weight:800; letter-spacing:2px;">
      ◈ UPLOAD RUN DATA
    </button>
  </div>
</div>

<script>
var wId=null,tInt=null,lPos=null,tDist=0,tSec=0,isPaused=false,wl=null;
var unit='{unit_sel}';
function hav(a,b,c,d){{var R=6371,dL=(c-a)*Math.PI/180,dl=(d-b)*Math.PI/180,x=Math.sin(dL/2)**2+Math.cos(a*Math.PI/180)*Math.cos(c*Math.PI/180)*Math.sin(dl/2)**2;return R*2*Math.atan2(Math.sqrt(x),Math.sqrt(1-x));}}
function fmtT(s){{var h=Math.floor(s/3600),m=Math.floor((s%3600)/60),x=s%60;return h>0?h+':'+String(m).padStart(2,'0')+':'+String(x).padStart(2,'0'):String(m).padStart(2,'0')+':'+String(x).padStart(2,'0');}}
function fmtP(sec,dist){{if(dist<0.01)return'--:--';var p=(sec/60)/dist;if(unit==='mi')p=p/1.60934;var m=Math.floor(p),s=Math.round((p-m)*60);return m+':'+String(s).padStart(2,'0');}}
function fmtD(km){{return unit==='mi'?(km*0.621371).toFixed(2):km.toFixed(2);}}
async function rwl(){{try{{if('wakeLock' in navigator)wl=await navigator.wakeLock.request('screen');}}catch(e){{document.getElementById('wakelock-warn').style.display='block';}}}}
function gpsStart(){{
  if(!navigator.geolocation){{document.getElementById('status-txt').innerHTML='<span style="color:#FF5555">❌ GPS NOT AVAILABLE ON THIS DEVICE</span>';return;}}
  tDist=0;tSec=0;lPos=null;isPaused=false;
  document.getElementById('btn-start').style.display='none';
  document.getElementById('btn-pause').style.display='flex';
  document.getElementById('btn-stop').style.display='flex';
  document.getElementById('summary-box').style.display='none';
  document.getElementById('gps-acc').style.display='block';
  document.getElementById('status-txt').innerHTML='<span style="display:inline-flex;align-items:center;gap:8px;color:{c["ACCENT"]};font-family:Share Tech Mono,monospace;font-size:0.8rem;letter-spacing:2px"><span style="width:10px;height:10px;border-radius:50%;background:{c["ACCENT"]};box-shadow:0 0 8px {c["ACCENT"]};animation:pg 1.5s infinite;display:inline-block"></span>TRACKING ACTIVE</span>';
  rwl();
  tInt=setInterval(function(){{if(!isPaused){{tSec++;document.getElementById('time-val').textContent=fmtT(tSec);document.getElementById('pace-val').textContent=fmtP(tSec,tDist);}}}},1000);
  wId=navigator.geolocation.watchPosition(function(p){{
    var ac=Math.round(p.coords.accuracy);
    document.getElementById('acc-val').textContent=ac;
    document.getElementById('acc-val').style.color=ac<15?'{c["ACCENT"]}':ac<30?'#FF8C00':'#FF5555';
    if(!isPaused){{
      var np={{lat:p.coords.latitude,lon:p.coords.longitude}};
      if(lPos){{var d=hav(lPos.lat,lPos.lon,np.lat,np.lon);if(d<0.3&&d>0.002){{tDist+=d;document.getElementById('dist-val').textContent=fmtD(tDist);}}}}
      lPos=np;
    }}
  }},function(e){{document.getElementById('status-txt').innerHTML='<span style="color:#FF5555;font-family:Share Tech Mono,monospace;font-size:0.75rem">⚠ GPS: '+e.message+'</span>';}},
  {{enableHighAccuracy:true,maximumAge:2000,timeout:15000}});
}}
function gpsPause(){{isPaused=true;document.getElementById('btn-pause').style.display='none';document.getElementById('btn-resume').style.display='flex';document.getElementById('status-txt').innerHTML='<span style="color:#FF8C00;font-family:Share Tech Mono,monospace;font-size:0.8rem;letter-spacing:2px">⏸ SESSION PAUSED</span>';}}
function gpsResume(){{isPaused=false;lPos=null;document.getElementById('btn-resume').style.display='none';document.getElementById('btn-pause').style.display='flex';document.getElementById('status-txt').innerHTML='<span style="display:inline-flex;align-items:center;gap:8px;color:{c["ACCENT"]};font-family:Share Tech Mono,monospace;font-size:0.8rem;letter-spacing:2px"><span style="width:10px;height:10px;border-radius:50%;background:{c["ACCENT"]};animation:pg 1.5s infinite;display:inline-block"></span>TRACKING ACTIVE</span>';}}
function gpsStop(){{
  isPaused=false;clearInterval(tInt);
  if(wId!==null)navigator.geolocation.clearWatch(wId);
  if(wl)wl.release();
  document.getElementById('btn-pause').style.display='none';
  document.getElementById('btn-resume').style.display='none';
  document.getElementById('btn-stop').style.display='none';
  document.getElementById('btn-start').style.display='flex';
  document.getElementById('gps-acc').style.display='none';
  document.getElementById('status-txt').innerHTML='<span style="color:{c["TEXT3"]};font-family:Share Tech Mono,monospace;font-size:0.75rem;letter-spacing:1px">[ SESSION ENDED — REVIEW & UPLOAD ]</span>';
  document.getElementById('s-dist').textContent=fmtD(tDist)+' '+unit;
  document.getElementById('s-time').textContent=fmtT(tSec);
  document.getElementById('s-pace').textContent=fmtP(tSec,tDist)+'/'+unit;
  document.getElementById('f-dist').value=tDist.toFixed(4);
  document.getElementById('f-dur').value=tSec;
  document.getElementById('summary-box').style.display='block';
}}
function gpsSave(){{
  var d=parseFloat(document.getElementById('f-dist').value);
  var t=parseInt(document.getElementById('f-dur').value);
  if(d<0.01||t<1){{alert('No run data!');return;}}
  var u=new URL(window.location.href);
  u.searchParams.set('gps_dist',d.toFixed(4));
  u.searchParams.set('gps_dur',t);
  u.searchParams.set('gps_unit',unit);
  window.location.href=u.toString();
}}
</script>
<style>@keyframes pg{{0%,100%{{opacity:1;box-shadow:0 0 8px {c["ACCENT"]}}}50%{{opacity:0.3;box-shadow:0 0 2px {c["ACCENT"]}}}}}</style>
"""
    st.components.v1.html(html, height=540, scrolling=False)

# ─── AUTH ────────────────────────────────────────────────────────
def auth_page(c):
    st.markdown(f"""
    <div style='text-align:center; padding:50px 0 30px;'>
        <div style='font-family:Share Tech Mono,monospace; font-size:0.7rem; color:{c["TEXT3"]}; letter-spacing:6px; margin-bottom:16px;'>◈ SYSTEM INITIALIZED ◈</div>
        <div style='font-family:Orbitron,sans-serif; font-size:2.6rem; font-weight:900;
            background:linear-gradient(135deg,{c["ACCENT2"]},{c["ACCENT"]},#FF8C00);
            -webkit-background-clip:text; -webkit-text-fill-color:transparent;
            background-clip:text; letter-spacing:6px; line-height:1.2;'>
            RUN<span style='-webkit-text-fill-color:{c["TEXT"]}'>QUEST</span>
        </div>
        <div style='font-family:Share Tech Mono,monospace; font-size:0.65rem; color:{c["TEXT3"]}; letter-spacing:6px; margin-top:8px;'>
            PERFORMANCE TRACKING OS v2.0
        </div>
        <div style='width:140px; height:2px; background:linear-gradient(90deg,transparent,{c["ACCENT"]},transparent); margin:20px auto;'></div>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["◈  ACCESS", "◈  REGISTER"])
    with tab1:
        with st.form("login_form"):
            email = st.text_input("Email Address", placeholder="operative@domain.com")
            password = st.text_input("Access Code", type="password", placeholder="Min. 6 characters")
            if st.form_submit_button("▶  INITIALIZE SESSION", use_container_width=True):
                try:
                    res = sb.auth.sign_in_with_password({"email": email, "password": password})
                    st.session_state.user = res.user
                    st.session_state.session = res.session
                    st.rerun()
                except Exception as e:
                    st.error(f"Access denied: {str(e)}")
    with tab2:
        with st.form("register_form"):
            email = st.text_input("Email Address", placeholder="operative@domain.com", key="re")
            password = st.text_input("Access Code", type="password", placeholder="Min. 6 characters", key="rp")
            if st.form_submit_button("◈  CREATE PROFILE", use_container_width=True):
                try:
                    sb.auth.sign_up({"email": email, "password": password})
                    st.success("✅ Profile created! Check your email to confirm, then sign in.")
                except Exception as e:
                    st.error(f"Error: {str(e)}")

# ─── PAGES ───────────────────────────────────────────────────────
def page_dashboard(user_id, profile, runs, unit, c):
    xp = profile.get("xp", 0)
    rank = get_rank(xp); next_rank = get_next_rank(xp); progress = get_xp_progress(xp)

    st.markdown(f"<div class='page-title'>◈ COMMAND CENTER</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='page-sub'>OPERATIVE: {st.session_state.user.email.split('@')[0].upper()}</div>", unsafe_allow_html=True)

    # Rank card
    st.markdown(f"""
    <div class='cyber-card'>
        <div style='display:flex; align-items:center; gap:16px; flex-wrap:wrap;'>
            <div style='font-size:3rem; filter:drop-shadow(0 0 10px {c["ACCENT"]})'>{rank['icon']}</div>
            <div style='flex:1; min-width:150px;'>
                <div class='rank-chip'>{rank['title'].upper()} · LEVEL {rank['level']}</div>
                <div style='font-family:Orbitron,sans-serif; font-size:1.8rem; font-weight:900;
                    color:{c["ACCENT"]}; margin:6px 0 2px;'>{xp:,}
                    <span style='font-size:0.9rem; color:{c["TEXT3"]}'>XP</span>
                </div>
                <div style='font-family:Exo 2,sans-serif; font-size:0.85rem; color:{c["TEXT3"]}; font-weight:600;'>
                    {"▶ Next: " + next_rank["title"] + " @ " + f"{next_rank['min_xp']:,}" + " XP" if next_rank else "◈ MAX RANK ACHIEVED"}
                </div>
            </div>
        </div>
        <div class='xp-bar-outer' style='margin-top:12px;'>
            <div class='xp-bar-inner' style='width:{progress}%'></div>
        </div>
        <div style='font-family:Share Tech Mono,monospace; font-size:0.7rem; color:{c["TEXT3"]}; letter-spacing:1px;'>{progress}% CAPACITY USED</div>
    </div>
    """, unsafe_allow_html=True)

    total_dist = sum(r["distance_km"] for r in runs)
    week_runs = [r for r in runs if is_this_week(r["started_at"])]
    week_dist = sum(r["distance_km"] for r in week_runs)
    week_time = sum(r["duration_seconds"] for r in week_runs)
    completed_count = sum(1 for q in QUESTS if check_quest(q["id"], runs))

    c1,c2,c3,c4 = st.columns(4)
    with c1: st.markdown(f"<div class='metric-card'><div class='metric-value'>{len(runs)}</div><div class='metric-label'>Missions</div></div>", unsafe_allow_html=True)
    with c2: st.markdown(f"<div class='metric-card'><div class='metric-value'>{format_distance(total_dist,unit)}</div><div class='metric-label'>Total {unit}</div></div>", unsafe_allow_html=True)
    with c3: st.markdown(f"<div class='metric-card'><div class='metric-value'>{format_distance(week_dist,unit)}</div><div class='metric-label'>This Week</div></div>", unsafe_allow_html=True)
    with c4: st.markdown(f"<div class='metric-card'><div class='metric-value'>{completed_count}</div><div class='metric-label'>Quests</div></div>", unsafe_allow_html=True)

    st.markdown("<hr class='divider'>", unsafe_allow_html=True)
    col_a, col_b = st.columns([1,1])

    with col_a:
        st.markdown(f"<div style='font-family:Orbitron,sans-serif; font-size:0.85rem; font-weight:700; color:{c['ACCENT']}; letter-spacing:2px; margin-bottom:10px;'>◈ ACTIVE MISSIONS</div>", unsafe_allow_html=True)
        active = [q for q in QUESTS if not check_quest(q["id"], runs)][:3]
        if not active:
            st.success("◈ All missions complete! 🎉")
        for q in active:
            st.markdown(f"""
            <div class='quest-card'>
                <div style='display:flex; align-items:center; gap:10px;'>
                    <span style='font-size:1.4rem'>{q['icon']}</span>
                    <div style='flex:1;'>
                        <div style='font-family:Exo 2,sans-serif; font-size:1rem; font-weight:700; color:{c["TEXT"]};'>{q['title']}</div>
                        <div style='font-family:Exo 2,sans-serif; font-size:0.8rem; color:{c["TEXT2"]}; margin-top:2px;'>{q['desc']}</div>
                    </div>
                    <div style='font-family:Orbitron,sans-serif; font-size:0.75rem; font-weight:800; color:{c["ACCENT"]}; white-space:nowrap;'>+{q['xp']} XP</div>
                </div>
            </div>""", unsafe_allow_html=True)

    with col_b:
        st.markdown(f"<div style='font-family:Orbitron,sans-serif; font-size:0.85rem; font-weight:700; color:{c['ACCENT']}; letter-spacing:2px; margin-bottom:10px;'>◈ LAST MISSION</div>", unsafe_allow_html=True)
        if not runs:
            st.info("No missions logged yet. Start your first run!")
        else:
            r = runs[0]
            pb = f"<span class='pb-badge'>◈ PB</span> " if r.get("is_pb") else ""
            st.markdown(f"""
            <div class='run-card'>
                <div style='margin-bottom:8px'>{pb}</div>
                <div style='display:grid; grid-template-columns:1fr 1fr; gap:10px;'>
                    <div><div class='data-label'>Distance</div><div class='data-val'>{format_distance(r["distance_km"],unit)} {unit}</div></div>
                    <div><div class='data-label'>Duration</div><div class='data-val'>{format_time(r["duration_seconds"])}</div></div>
                    <div><div class='data-label'>Avg Pace</div><div class='data-val'>{format_pace(r["duration_seconds"],r["distance_km"],unit)}/{unit}</div></div>
                    <div><div class='data-label'>XP Gained</div><div class='data-val' style='color:{c["ACCENT"]}'>+{r.get("xp_earned",0)}</div></div>
                </div>
                <div style='margin-top:8px; font-family:Share Tech Mono,monospace; font-size:0.65rem; color:{c["TEXT3"]};'>{r["started_at"][:10]}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<hr class='divider'>", unsafe_allow_html=True)
    st.markdown(f"<div style='font-family:Orbitron,sans-serif; font-size:0.85rem; font-weight:700; color:{c['ACCENT']}; letter-spacing:2px; margin-bottom:10px;'>◈ CYCLE REPORT</div>", unsafe_allow_html=True)
    w1,w2,w3 = st.columns(3)
    with w1: st.markdown(f"<div class='metric-card'><div class='metric-value'>{len(week_runs)}</div><div class='metric-label'>Runs</div></div>", unsafe_allow_html=True)
    with w2: st.markdown(f"<div class='metric-card'><div class='metric-value'>{format_distance(week_dist,unit)}</div><div class='metric-label'>Distance</div></div>", unsafe_allow_html=True)
    with w3: st.markdown(f"<div class='metric-card'><div class='metric-value'>{format_time(week_time)}</div><div class='metric-label'>Total Time</div></div>", unsafe_allow_html=True)


def page_gps_tracker(user_id, profile, runs, unit, c):
    st.markdown("<div class='page-title'>◈ GPS UPLINK</div>", unsafe_allow_html=True)
    st.markdown("<div class='page-sub'>REAL-TIME POSITION TRACKING</div>", unsafe_allow_html=True)
    st.warning("⚠ Keep this tab open and your screen ON while running!")

    params = st.query_params
    if "gps_dist" in params and "gps_dur" in params:
        try:
            dist_km = float(params["gps_dist"])
            dur = int(params["gps_dur"])
            gu = params.get("gps_unit", "km")
            if gu == "mi": dist_km = dist_km / 0.621371
            if dist_km > 0.01 and dur > 0:
                total_xp, is_pb, fresh = process_and_save_run(user_id, profile, runs, dist_km, dur, unit)
                st.query_params.clear()
                st.success(f"✅ Run saved! {format_distance(dist_km,unit)} {unit} in {format_time(dur)}")
                if is_pb: st.balloons(); st.success("🏅 NEW PERSONAL RECORD!")
                st.info(f"⭐ +{total_xp} XP earned!")
                for q in fresh: st.success(f"🎯 Quest Complete: {q['icon']} {q['title']} (+{q['xp']} XP)")
        except Exception as e:
            st.error(f"Save error: {e}")
            st.query_params.clear()

    unit_sel = st.radio("Unit System", ["km", "mi"], horizontal=True, index=0 if unit == "km" else 1)
    gps_component(unit_sel, c)
    st.markdown(f"<div style='font-family:Exo 2,sans-serif; font-size:0.85rem; font-weight:500; color:{c['TEXT3']}; margin-top:8px;'>💡 Go outside first · Wait for GPS accuracy &lt;15m · Keep phone in hand</div>", unsafe_allow_html=True)


def page_log_run(user_id, profile, runs, unit, c):
    st.markdown("<div class='page-title'>◈ MANUAL LOG</div>", unsafe_allow_html=True)
    st.markdown("<div class='page-sub'>LOG RUN FROM EXTERNAL DEVICE</div>", unsafe_allow_html=True)

    with st.form("log_run_form"):
        col1, col2 = st.columns(2)
        with col1: distance = st.number_input("Distance", min_value=0.1, max_value=200.0, step=0.1, value=5.0)
        with col2: unit_sel = st.selectbox("Unit", ["km", "mi"], index=0 if unit == "km" else 1)
        col3,col4,col5 = st.columns(3)
        with col3: hours = st.number_input("Hours", min_value=0, max_value=24, value=0)
        with col4: minutes = st.number_input("Minutes", min_value=0, max_value=59, value=30)
        with col5: seconds_val = st.number_input("Seconds", min_value=0, max_value=59, value=0)
        if st.form_submit_button("◈  UPLOAD DATA", use_container_width=True):
            dist_km = distance if unit_sel == "km" else distance / 0.621371
            total_secs = hours*3600 + minutes*60 + seconds_val
            if total_secs == 0:
                st.error("Please enter a valid duration.")
            else:
                total_xp, is_pb, fresh = process_and_save_run(user_id, profile, runs, dist_km, total_secs, unit_sel)
                st.success(f"✅ Run saved! {distance} {unit_sel} in {format_time(total_secs)} — {format_pace(total_secs,dist_km,unit_sel)}/{unit_sel}")
                if is_pb: st.balloons(); st.success("🏅 New Personal Record!")
                st.info(f"⭐ +{total_xp} XP earned!")
                for q in fresh: st.success(f"🎯 Quest: {q['icon']} {q['title']} (+{q['xp']} XP)")
                st.rerun()


def page_history(user_id, runs, unit, c):
    st.markdown("<div class='page-title'>◈ MISSION LOG</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='page-sub'>{len(runs)} RECORDS IN DATABASE</div>", unsafe_allow_html=True)
    if not runs:
        st.info("No runs logged yet. Complete your first mission!")
        return
    unit_sel = st.radio("Unit", ["km", "mi"], horizontal=True, index=0 if unit == "km" else 1)
    for r in runs:
        pb = f"<span class='pb-badge'>◈ PB</span> " if r.get("is_pb") else ""
        col1, col2 = st.columns([5,1])
        with col1:
            st.markdown(f"""
            <div class='run-card'>
                <div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;'>
                    <span style='font-family:Share Tech Mono,monospace; font-size:0.75rem; color:{c["TEXT3"]};'>{r["started_at"][:10]}</span>
                    <span>{pb}<span style='font-family:Orbitron,sans-serif; font-size:0.75rem; font-weight:800; color:{c["ACCENT"]};'>+{r.get("xp_earned",0)} XP</span></span>
                </div>
                <div style='display:grid; grid-template-columns:1fr 1fr 1fr; gap:10px;'>
                    <div><div class='data-label'>Distance</div><div class='data-val'>{format_distance(r["distance_km"],unit_sel)} {unit_sel}</div></div>
                    <div><div class='data-label'>Time</div><div class='data-val'>{format_time(r["duration_seconds"])}</div></div>
                    <div><div class='data-label'>Pace</div><div class='data-val'>{format_pace(r["duration_seconds"],r["distance_km"],unit_sel)}/{unit_sel}</div></div>
                </div>
            </div>""", unsafe_allow_html=True)
        with col2:
            if st.button("✕", key=f"del_{r['id']}"):
                delete_run(r["id"]); st.rerun()


def page_quests(user_id, profile, runs, c):
    st.markdown("<div class='page-title'>◈ MISSION BOARD</div>", unsafe_allow_html=True)
    xp = profile.get("xp", 0)
    rank = get_rank(xp); next_rank = get_next_rank(xp); progress = get_xp_progress(xp)
    completed_ids = set(q["id"] for q in QUESTS if check_quest(q["id"], runs))
    completed = [q for q in QUESTS if q["id"] in completed_ids]
    pending = [q for q in QUESTS if q["id"] not in completed_ids]

    st.markdown(f"<div style='font-family:Orbitron,sans-serif; font-size:0.85rem; font-weight:700; color:{c['ACCENT']}; letter-spacing:2px; margin-bottom:12px;'>◈ RANK LADDER</div>", unsafe_allow_html=True)
    cols = st.columns(len(RANKS))
    for i, r in enumerate(RANKS):
        is_cur = r["level"] == rank["level"]
        unlocked = xp >= r["min_xp"]
        with cols[i]:
            st.markdown(f"""
            <div style='text-align:center; padding:10px 4px; border-radius:6px;
                border:2px solid {"" + c["ACCENT"] + "" if is_cur else c["BORDER"]};
                background:{"rgba(255,179,0,0.1)" if is_cur else "transparent"};
                opacity:{"1" if unlocked else "0.25"};
                box-shadow:{"0 0 14px rgba(255,179,0,0.2)" if is_cur else "none"}'>
                <div style='font-size:1.2rem'>{r["icon"]}</div>
                <div style='font-family:Orbitron,sans-serif; font-size:0.5rem; font-weight:700; color:{"" + c["ACCENT"] + "" if is_cur else c["TEXT3"]}; margin-top:2px'>{r["title"][:4].upper()}</div>
                {"<div style='font-size:0.5rem; color:" + c["ACCENT"] + "; font-family:Share Tech Mono'>YOU</div>" if is_cur else ""}
            </div>""", unsafe_allow_html=True)

    st.markdown(f"""
    <div style='margin:14px 0;'>
        <div style='display:flex; justify-content:space-between; font-family:Exo 2,sans-serif; font-size:0.85rem; font-weight:600; color:{c["TEXT2"]}; margin-bottom:6px;'>
            <span>{rank["icon"]} {rank["title"]} — {xp:,} XP</span>
            <span>{"→ " + next_rank["title"] + " @ " + f"{next_rank['min_xp']:,}" if next_rank else "◈ MAX RANK"}</span>
        </div>
        <div class='xp-bar-outer'><div class='xp-bar-inner' style='width:{progress}%'></div></div>
        <div style='font-family:Exo 2,sans-serif; font-size:0.8rem; font-weight:600; color:{c["TEXT3"]}; margin-top:4px;'>{progress}% — {str(next_rank["min_xp"]-xp)+" XP to next rank" if next_rank else "Transcendent achieved!"}</div>
    </div>""", unsafe_allow_html=True)

    st.markdown("<hr class='divider'>", unsafe_allow_html=True)
    if pending:
        st.markdown(f"<div style='font-family:Orbitron,sans-serif; font-size:0.85rem; font-weight:700; color:{c['ACCENT']}; letter-spacing:2px; margin-bottom:10px;'>◈ ACTIVE QUESTS ({len(pending)})</div>", unsafe_allow_html=True)
        for q in pending:
            st.markdown(f"""
            <div class='quest-card'>
                <div style='display:flex; align-items:center; gap:12px;'>
                    <span style='font-size:1.5rem'>{q['icon']}</span>
                    <div style='flex:1;'>
                        <div style='font-family:Exo 2,sans-serif; font-size:1rem; font-weight:700; color:{c["TEXT"]};'>{q['title']}</div>
                        <div style='font-family:Exo 2,sans-serif; font-size:0.85rem; color:{c["TEXT2"]}; margin-top:2px;'>{q['desc']}</div>
                    </div>
                    <div style='background:rgba(255,179,0,0.12); border:1.5px solid {c["BORDER2"]}; border-radius:4px; padding:4px 12px; font-family:Orbitron,sans-serif; font-size:0.7rem; font-weight:800; color:{c["ACCENT"]}; white-space:nowrap;'>+{q['xp']} XP</div>
                </div>
            </div>""", unsafe_allow_html=True)

    if completed:
        st.markdown(f"<div style='font-family:Orbitron,sans-serif; font-size:0.85rem; font-weight:700; color:{c['ACCENT']}; letter-spacing:2px; margin:16px 0 10px;'>◈ COMPLETED ({len(completed)})</div>", unsafe_allow_html=True)
        cols2 = st.columns(2)
        for i, q in enumerate(completed):
            with cols2[i%2]:
                st.markdown(f"""
                <div class='quest-done'>
                    <div style='display:flex; align-items:center; gap:10px;'>
                        <span style='font-size:1.3rem'>{q['icon']}</span>
                        <div style='flex:1;'>
                            <div style='font-family:Exo 2,sans-serif; font-size:0.95rem; font-weight:700; color:{c["TEXT"]};'>{q['title']}</div>
                            <div style='font-family:Exo 2,sans-serif; font-size:0.8rem; color:{c["ACCENT"]}; margin-top:2px;'>+{q['xp']} XP earned</div>
                        </div>
                        <span style='font-size:1.2rem'>✅</span>
                    </div>
                </div>""", unsafe_allow_html=True)


def page_stats(user_id, runs, unit, c):
    st.markdown("<div class='page-title'>◈ DATA ANALYSIS</div>", unsafe_allow_html=True)
    if not runs:
        st.info("Complete some runs to see your stats!")
        return
    unit_sel = st.radio("Unit", ["km", "mi"], horizontal=True, index=0 if unit == "km" else 1)
    runs_asc = list(reversed(runs))
    total_dist = sum(r["distance_km"] for r in runs)
    total_time = sum(r["duration_seconds"] for r in runs)
    avg_pace = (total_time/60)/total_dist if total_dist else 0
    best_pace = min((r["duration_seconds"]/60/r["distance_km"]) for r in runs if r["distance_km"] > 0)

    c1,c2,c3,c4 = st.columns(4)
    with c1: st.metric("Total Runs", len(runs))
    with c2: st.metric(f"Total {unit_sel}", format_distance(total_dist, unit_sel))
    with c3: st.metric("Avg Pace", f"{format_pace(int(avg_pace*60),1,unit_sel)}/{unit_sel}")
    with c4: st.metric("Best Pace", f"{format_pace(int(best_pace*60),1,unit_sel)}/{unit_sel}")

    st.markdown("<hr class='divider'>", unsafe_allow_html=True)
    cp,cd,cx = {},{},{}
    for r in runs_asc:
        date = r["started_at"][:10]
        pv = (r["duration_seconds"]/60)/r["distance_km"]
        if unit_sel == 'mi': pv = pv/1.60934
        cp[date] = round(pv,2)
        cd[date] = float(format_distance(r["distance_km"],unit_sel))
        cx[date] = r.get("xp_earned",0)

    tab1,tab2,tab3 = st.tabs(["⚡ Pace Trend", f"🗺 Distance ({unit_sel})", "⭐ XP Earned"])
    with tab1: st.line_chart(cp)
    with tab2: st.bar_chart(cd)
    with tab3: st.bar_chart(cx)

    st.markdown("<hr class='divider'>", unsafe_allow_html=True)
    st.markdown(f"<div style='font-family:Orbitron,sans-serif; font-size:0.85rem; font-weight:700; color:{c['ACCENT']}; letter-spacing:2px; margin-bottom:12px;'>◈ PERSONAL RECORDS</div>", unsafe_allow_html=True)
    pb_distances = [1,3,5,10,21.1,42.2]
    pb_labels = {1:"1 KM",3:"3 KM",5:"5 KM",10:"10 KM",21.1:"Half Marathon",42.2:"Full Marathon"}
    pb_cols = st.columns(3); found=0
    for dist in pb_distances:
        rel = [r for r in runs if abs(r["distance_km"]-dist)<0.2]
        if rel:
            pb = min(rel, key=lambda r: r["duration_seconds"])
            with pb_cols[found%3]:
                st.markdown(f"""
                <div style='background:{c["CARD"]}; border:1.5px solid {c["BORDER2"]}; border-top:3px solid {c["ACCENT"]};
                    border-radius:8px; padding:14px; text-align:center; margin-bottom:10px;'>
                    <div style='font-family:Orbitron,sans-serif; font-size:0.7rem; font-weight:700; color:{c["ACCENT"]}; letter-spacing:1px;'>{pb_labels[dist]}</div>
                    <div style='font-family:Orbitron,sans-serif; font-size:1.4rem; font-weight:800; color:{c["TEXT"]}; margin-top:6px;'>{format_time(pb["duration_seconds"])}</div>
                    <div style='font-family:Share Tech Mono,monospace; font-size:0.7rem; color:{c["TEXT2"]}; margin-top:4px;'>{format_pace(pb["duration_seconds"],pb["distance_km"],unit_sel)}/{unit_sel}</div>
                </div>""", unsafe_allow_html=True)
            found += 1
    if found == 0:
        st.caption("No personal records yet. Complete runs near standard distances.")


def page_settings(user_id, profile, c):
    st.markdown("<div class='page-title'>◈ SYSTEM CONFIG</div>", unsafe_allow_html=True)
    with st.form("settings_form"):
        st.markdown(f"<div style='font-family:Orbitron,sans-serif; font-size:0.8rem; font-weight:700; color:{c['ACCENT']}; letter-spacing:2px; margin-bottom:8px;'>Display Mode</div>", unsafe_allow_html=True)
        dark = st.selectbox("", ["🌑  Dark Mode (Cyber)", "☀️  Light Mode (Clean)"],
                            index=0 if st.session_state.get("dark_mode", True) else 1,
                            label_visibility="collapsed")
        st.markdown(f"<div style='font-family:Orbitron,sans-serif; font-size:0.8rem; font-weight:700; color:{c['ACCENT']}; letter-spacing:2px; margin:16px 0 8px;'>Distance Unit</div>", unsafe_allow_html=True)
        unit = st.radio("", ["km", "mi"], horizontal=True,
                        index=0 if profile.get("unit","km")=="km" else 1,
                        label_visibility="collapsed")
        st.markdown(f"<div style='font-family:Orbitron,sans-serif; font-size:0.8rem; font-weight:700; color:{c['ACCENT']}; letter-spacing:2px; margin:16px 0 8px;'>Operative ID</div>", unsafe_allow_html=True)
        st.text_input("", value=st.session_state.user.email, disabled=True, label_visibility="collapsed")
        if st.form_submit_button("◈  APPLY CONFIGURATION", use_container_width=True):
            st.session_state.dark_mode = "Dark" in dark
            update_profile(user_id, profile.get("xp",0), profile.get("completed_quests",[]), unit)
            st.success("✅ Configuration saved!")
            st.rerun()

# ─── MAIN ────────────────────────────────────────────────────────
def main():
    if "user" not in st.session_state: st.session_state.user = None
    if "dark_mode" not in st.session_state: st.session_state.dark_mode = True
    if "page" not in st.session_state: st.session_state.page = "Dashboard"

    # Handle bottom nav URL params
    params = st.query_params
    if "nav" in params:
        st.session_state.page = params["nav"].replace("+", " ")

    c = apply_theme(st.session_state.dark_mode)

    if not st.session_state.user:
        auth_page(c)
        return

    user_id = st.session_state.user.id
    profile = get_profile(user_id)
    runs = get_runs(user_id)
    unit = profile.get("unit", "km")
    page = st.session_state.get("page", "Dashboard")

    render_sidebar(profile, page, c)
    render_bottom_nav(page, c)

    if page == "Dashboard":         page_dashboard(user_id, profile, runs, unit, c)
    elif page == "GPS Tracker":     page_gps_tracker(user_id, profile, runs, unit, c)
    elif page == "Manual Log":      page_log_run(user_id, profile, runs, unit, c)
    elif page == "History":         page_history(user_id, runs, unit, c)
    elif page == "Quests":          page_quests(user_id, profile, runs, c)
    elif page == "Stats":           page_stats(user_id, runs, unit, c)
    elif page == "Settings":        page_settings(user_id, profile, c)

if __name__ == "__main__":
    main()
