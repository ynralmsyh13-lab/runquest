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
    {"id": "first_run",     "title": "First Step",        "desc": "Complete your very first run",       "icon": "👟", "xp": 50},
    {"id": "run_5km",       "title": "Five Kilometers",   "desc": "Run 5km in a single session",        "icon": "🎯", "xp": 75},
    {"id": "run_10km",      "title": "Double Digits",     "desc": "Run 10km in a single session",       "icon": "🏅", "xp": 150},
    {"id": "run_3_times",   "title": "Habit Forming",     "desc": "Complete 3 runs total",              "icon": "🔄", "xp": 60},
    {"id": "run_7_times",   "title": "Weekly Warrior",    "desc": "Complete 7 runs total",              "icon": "⚔️", "xp": 120},
    {"id": "sub_6_pace",    "title": "Speed Seeker",      "desc": "Run a pace under 6:00 min/km",       "icon": "⚡", "xp": 80},
    {"id": "sub_5_pace",    "title": "Lightning Legs",    "desc": "Run a pace under 5:00 min/km",       "icon": "🌩️", "xp": 200},
    {"id": "total_50km",    "title": "Fifty & Counting",  "desc": "Accumulate 50km total",              "icon": "🗺️", "xp": 200},
    {"id": "total_100km",   "title": "Century Runner",    "desc": "Accumulate 100km total",             "icon": "💯", "xp": 400},
    {"id": "half_marathon", "title": "Half the Glory",    "desc": "Complete a half marathon (21.1km)",  "icon": "🎖️", "xp": 300},
    {"id": "full_marathon", "title": "Marathon Legend",   "desc": "Complete a full marathon (42.2km)",  "icon": "🏆", "xp": 1000},
    {"id": "run_streak_3",  "title": "On a Roll",         "desc": "Run 3 days in a row",                "icon": "🔥", "xp": 100},
    {"id": "run_streak_7",  "title": "Unstoppable",       "desc": "Run 7 days in a row",                "icon": "💥", "xp": 250},
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

def save_run(user_id, distance_km, duration_seconds, xp_earned, is_pb, route=None):
    import json
    sb.table("runs").insert({
        "user_id": user_id, "distance_km": distance_km,
        "duration_seconds": duration_seconds, "xp_earned": xp_earned,
        "is_pb": is_pb, "started_at": datetime.utcnow().isoformat(),
        "route": json.dumps(route or [])
    }).execute()

def update_profile(user_id, xp, completed_quests, unit):
    sb.table("profiles").upsert({
        "id": user_id, "xp": xp,
        "completed_quests": completed_quests, "unit": unit
    }).execute()

def delete_run(run_id):
    sb.table("runs").delete().eq("id", run_id).execute()

def process_and_save_run(user_id, profile, runs, dist_km, total_seconds, unit_sel, route=None):
    existing = [r for r in runs if abs(r["distance_km"] - dist_km) < 0.2]
    is_pb = len(existing) == 0 or total_seconds < min(r["duration_seconds"] for r in existing)
    xp = calculate_xp(dist_km, total_seconds, is_pb)
    prev_completed = [q["id"] for q in QUESTS if check_quest(q["id"], runs)]
    save_run(user_id, dist_km, total_seconds, xp, is_pb, route)
    new_runs = get_runs(user_id)
    now_completed = [q["id"] for q in QUESTS if check_quest(q["id"], new_runs)]
    fresh_quests = [q for q in QUESTS if q["id"] in now_completed and q["id"] not in prev_completed]
    quest_xp = sum(q["xp"] for q in fresh_quests)
    update_profile(user_id, profile.get("xp", 0) + xp + quest_xp, now_completed, unit_sel)
    return xp + quest_xp, is_pb, fresh_quests

# ─── THEME ──────────────────────────────────────────────────────
def apply_theme(dark_mode=True):
    if dark_mode:
        BG="#07090D"; CARD="#0E1118"; CARD2="#131820"
        BORDER="#FFB30035"; BORDER2="#FFB30070"
        TEXT="#F0E6C8"; TEXT2="#C8B882"; TEXT3="#7A6A48"
        ACCENT="#FFB300"; ACCENT2="#FFD700"
        DANGER="#FF5555"; SIDEBAR="#0A0C12"
    else:
        BG="#F5F0E8"; CARD="#FFFFFF"; CARD2="#FFF8EC"
        BORDER="#FFB30050"; BORDER2="#C07800"
        TEXT="#1A1200"; TEXT2="#5A4A20"; TEXT3="#8A7A50"
        ACCENT="#C07800"; ACCENT2="#9A6000"
        DANGER="#CC3333"; SIDEBAR="#FFF3D4"

    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;600;700;900&family=Exo+2:wght@300;400;500;600;700;800&family=Share+Tech+Mono&display=swap');

    html, body, [class*="css"] {{
        font-family: 'Exo 2', sans-serif !important;
        background-color: {BG} !important;
        color: {TEXT} !important;
        font-size: 16px !important;
    }}
    .stApp {{ background: {BG} !important; }}

    section[data-testid="stSidebar"] {{
        background: {SIDEBAR} !important;
        border-right: 2px solid {BORDER2} !important;
    }}

    /* Buttons */
    .stButton > button {{
        font-family: 'Orbitron', sans-serif !important;
        border-radius: 6px !important;
        font-weight: 700 !important;
        font-size: 0.78rem !important;
        letter-spacing: 1.5px !important;
        padding: 12px 16px !important;
        border: 1.5px solid {BORDER2} !important;
        background: {"rgba(255,179,0,0.1)" if dark_mode else "rgba(192,120,0,0.1)"} !important;
        color: {ACCENT} !important;
        width: 100% !important;
        transition: all 0.2s !important;
    }}
    .stButton > button:hover {{
        background: {"rgba(255,179,0,0.2)" if dark_mode else "rgba(192,120,0,0.2)"} !important;
        box-shadow: 0 0 16px rgba(255,179,0,0.25) !important;
    }}

    /* Inputs */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input {{
        background: {CARD} !important; color: {TEXT} !important;
        border: 1.5px solid {BORDER2} !important; border-radius: 6px !important;
        font-family: 'Exo 2', sans-serif !important; font-size: 1rem !important;
    }}
    .stSelectbox > div > div {{
        background: {CARD} !important; color: {TEXT} !important;
        border: 1.5px solid {BORDER2} !important;
    }}

    label, .stTextInput label, .stNumberInput label,
    .stSelectbox label, .stRadio label, .stRadio > div > label,
    .stRadio > div > label > div, p {{
        color: {TEXT} !important;
        font-family: 'Exo 2', sans-serif !important;
        font-size: 1rem !important; font-weight: 600 !important;
    }}

    /* Force radio option text to always be visible */
    .stRadio label span {{
        color: {TEXT} !important;
        font-weight: 600 !important;
    }}

    /* Force all input text visible */
    .stTextInput input, .stNumberInput input {{
        color: {TEXT} !important;
        -webkit-text-fill-color: {TEXT} !important;
    }}

    /* Disabled input text */
    .stTextInput input:disabled {{
        color: {TEXT2} !important;
        -webkit-text-fill-color: {TEXT2} !important;
        opacity: 1 !important;
    }}

    .stTabs [data-baseweb="tab-list"] {{
        background: {CARD} !important;
        border-bottom: 2px solid {BORDER2} !important;
    }}
    .stTabs [data-baseweb="tab"] {{
        font-family: 'Orbitron', sans-serif !important;
        font-size: 0.65rem !important; color: {TEXT3} !important;
        letter-spacing: 1px !important; padding: 10px 14px !important;
    }}
    .stTabs [aria-selected="true"] {{
        color: {ACCENT} !important;
        border-bottom: 3px solid {ACCENT} !important;
        background: {"rgba(255,179,0,0.08)" if dark_mode else "rgba(192,120,0,0.08)"} !important;
    }}

    div[data-testid="stMetricValue"] {{
        font-family: 'Orbitron', sans-serif !important;
        color: {ACCENT} !important; font-size: 1.5rem !important; font-weight: 700 !important;
    }}
    div[data-testid="stMetricLabel"] {{
        font-family: 'Exo 2', sans-serif !important;
        color: {TEXT2} !important; font-size: 0.85rem !important; font-weight: 600 !important;
    }}

    /* Form submit buttons */
    .stFormSubmitButton > button {{
        font-family: 'Orbitron', sans-serif !important;
        border-radius: 6px !important;
        font-weight: 700 !important;
        font-size: 0.78rem !important;
        letter-spacing: 1.5px !important;
        padding: 12px 16px !important;
        border: 2px solid {BORDER2} !important;
        background: {"rgba(255,179,0,0.15)" if dark_mode else "rgba(192,120,0,0.15)"} !important;
        color: {ACCENT} !important;
        width: 100% !important;
        transition: all 0.2s !important;
    }}
    .stFormSubmitButton > button:hover {{
        background: {"rgba(255,179,0,0.25)" if dark_mode else "rgba(192,120,0,0.25)"} !important;
        box-shadow: 0 0 16px rgba(255,179,0,0.2) !important;
    }}

    .stAlert > div {{
        font-family: 'Exo 2', sans-serif !important;
        font-size: 0.95rem !important; font-weight: 500 !important;
    }}
    hr {{ border-color: {BORDER2}40 !important; }}
    ::-webkit-scrollbar-track {{ background: {BG}; }}
    ::-webkit-scrollbar-thumb {{ background: {BORDER2}; border-radius: 2px; }}

    /* Hide sidebar on mobile, show bottom nav */
    @media (max-width: 768px) {{
        section[data-testid="stSidebar"] {{ display: none !important; }}
        .main .block-container {{ padding: 1rem 0.8rem 5rem 0.8rem !important; max-width: 100% !important; }}
    }}
    @media (min-width: 769px) {{
        .bottom-nav-container {{ display: none !important; }}
        .main .block-container {{ padding: 2rem !important; }}
    }}

    /* ── COMPONENTS ── */
    .rq-logo {{
        font-family: 'Orbitron', sans-serif; font-size: 1.5rem; font-weight: 900;
        letter-spacing: 4px; color: {ACCENT};
    }}

    .page-title {{
        font-family: 'Orbitron', sans-serif; font-size: 1.4rem; font-weight: 800;
        color: {ACCENT}; letter-spacing: 3px; text-transform: uppercase; margin-bottom: 2px;
    }}
    .page-sub {{
        font-family: 'Share Tech Mono', monospace; font-size: 0.7rem;
        color: {TEXT3}; letter-spacing: 3px; text-transform: uppercase; margin-bottom: 16px;
    }}

    .cyber-card {{
        background: {CARD}; border: 1.5px solid {BORDER2}; border-radius: 8px;
        padding: 18px 16px; margin-bottom: 14px; position: relative; overflow: hidden;
    }}
    .cyber-card::before {{
        content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
        background: linear-gradient(90deg, transparent, {ACCENT}, transparent);
    }}

    .metric-card {{
        background: {CARD}; border: 1.5px solid {BORDER2}; border-radius: 8px;
        padding: 16px 8px; text-align: center; position: relative; overflow: hidden; margin-bottom: 8px;
    }}
    .metric-card::before {{
        content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
        background: linear-gradient(90deg, transparent, {ACCENT}, transparent);
    }}
    .metric-value {{
        font-family: 'Orbitron', sans-serif; font-size: 1.5rem; font-weight: 800;
        color: {ACCENT}; line-height: 1.1;
    }}
    .metric-label {{
        font-family: 'Exo 2', sans-serif; font-size: 0.75rem; font-weight: 700;
        color: {TEXT2}; text-transform: uppercase; letter-spacing: 1px; margin-top: 5px;
    }}

    .run-card {{
        background: {CARD}; border: 1.5px solid {BORDER}; border-left: 4px solid {ACCENT};
        border-radius: 8px; padding: 14px 16px; margin-bottom: 10px;
    }}
    .quest-card {{
        background: {CARD}; border: 1.5px solid {BORDER}; border-radius: 8px;
        padding: 14px 16px; margin-bottom: 10px;
    }}
    .quest-done {{
        background: {"rgba(255,179,0,0.06)" if dark_mode else "rgba(192,120,0,0.08)"};
        border: 1.5px solid {BORDER2}; border-radius: 8px; padding: 12px 16px; margin-bottom: 8px;
    }}

    .xp-bar-outer {{
        background: {CARD2}; border: 1px solid {BORDER}; border-radius: 99px;
        height: 10px; overflow: hidden; margin: 8px 0;
    }}
    .xp-bar-inner {{
        height: 100%;
        background: linear-gradient(90deg, #FF8C00, {ACCENT}, {ACCENT2});
        border-radius: 99px; box-shadow: 0 0 8px rgba(255,179,0,0.4);
    }}

    .rank-chip {{
        display: inline-block; padding: 5px 14px; border-radius: 4px;
        font-family: 'Orbitron', sans-serif; font-size: 0.7rem; font-weight: 700;
        color: {ACCENT}; background: {"rgba(255,179,0,0.12)" if dark_mode else "rgba(192,120,0,0.12)"};
        border: 1.5px solid {BORDER2}; letter-spacing: 1.5px;
    }}
    .pb-badge {{
        display: inline-block; padding: 3px 10px; border-radius: 4px;
        font-family: 'Orbitron', sans-serif; font-size: 0.6rem; font-weight: 700;
        color: #FFD700; background: rgba(255,215,0,0.12);
        border: 1.5px solid rgba(255,215,0,0.5); letter-spacing: 1px;
    }}
    .data-val {{
        font-family: 'Share Tech Mono', monospace; font-size: 1rem;
        color: {ACCENT}; font-weight: 600;
    }}
    .data-label {{
        font-family: 'Exo 2', sans-serif; font-size: 0.72rem; font-weight: 700;
        color: {TEXT3}; text-transform: uppercase; letter-spacing: 1px;
    }}
    .divider {{
        border: none; height: 1px;
        background: linear-gradient(90deg, transparent, {BORDER2}, transparent);
        margin: 16px 0;
    }}

    /* Sign out button */
    .signout-btn .stButton > button {{
        font-family: 'Exo 2', sans-serif !important;
        font-size: 0.85rem !important;
        font-weight: 600 !important;
        letter-spacing: 0.5px !important;
        border-radius: 0px !important;
        border: none !important;
        border-left: 3px solid transparent !important;
        background: transparent !important;
        color: {TEXT3} !important;
        text-align: left !important;
        justify-content: flex-start !important;
        padding: 10px 16px 10px 20px !important;
        box-shadow: none !important;
        transition: all 0.15s !important;
    }}
    .signout-btn .stButton > button:hover {{
        color: {DANGER} !important;
        border-left-color: {DANGER} !important;
        background: {"rgba(255,85,85,0.08)" if dark_mode else "rgba(204,51,51,0.06)"} !important;
        box-shadow: none !important;
    }}
    .bottom-nav-container {{
        position: fixed; bottom: 0; left: 0; right: 0;
        background: {SIDEBAR}; border-top: 2px solid {BORDER2};
        z-index: 9999; padding: 0;
    }}
    .bottom-nav-container .stButton > button {{
        border-radius: 0 !important; border: none !important;
        background: transparent !important;
        font-size: 0.5rem !important; padding: 10px 4px 8px !important;
        letter-spacing: 0.5px !important; height: 60px !important;
        display: flex !important; flex-direction: column !important;
        align-items: center !important; justify-content: center !important;
        gap: 2px !important;
    }}
    .bottom-nav-container .stButton > button:hover {{
        background: {"rgba(255,179,0,0.1)" if dark_mode else "rgba(192,120,0,0.1)"} !important;
        box-shadow: none !important;
    }}
    .nav-active .stButton > button {{
        background: {"rgba(255,179,0,0.15)" if dark_mode else "rgba(192,120,0,0.15)"} !important;
        border-top: 2px solid {ACCENT} !important;
        color: {ACCENT} !important;
    }}

    /* ── SIDEBAR NAV BUTTONS ── */
    .sidebar-nav .stButton > button {{
        text-align: left !important;
        justify-content: flex-start !important;
        border-radius: 0px !important;
        margin: 0 !important;
        font-family: 'Exo 2', sans-serif !important;
        font-size: 0.92rem !important;
        letter-spacing: 0.5px !important;
        font-weight: 600 !important;
        padding: 11px 16px 11px 20px !important;
        border: none !important;
        border-left: 3px solid transparent !important;
        background: transparent !important;
        color: {TEXT2} !important;
        width: 100% !important;
        transition: all 0.15s !important;
        box-shadow: none !important;
    }}
    .sidebar-nav .stButton > button:hover {{
        background: {"rgba(255,179,0,0.07)" if dark_mode else "rgba(192,120,0,0.07)"} !important;
        border-left-color: {"rgba(255,179,0,0.4)" if dark_mode else "rgba(192,120,0,0.4)"} !important;
        color: {TEXT} !important;
        box-shadow: none !important;
    }}
    .sidebar-active .stButton > button {{
        background: {"rgba(255,179,0,0.1)" if dark_mode else "rgba(192,120,0,0.1)"} !important;
        border-left: 3px solid {ACCENT} !important;
        color: {ACCENT} !important;
        font-weight: 700 !important;
        box-shadow: inset 0 0 20px {"rgba(255,179,0,0.05)" if dark_mode else "rgba(192,120,0,0.05)"} !important;
    }}

    </style>
    """, unsafe_allow_html=True)

    return {"BG":BG,"CARD":CARD,"CARD2":CARD2,"BORDER":BORDER,"BORDER2":BORDER2,
            "TEXT":TEXT,"TEXT2":TEXT2,"TEXT3":TEXT3,"ACCENT":ACCENT,"ACCENT2":ACCENT2,
            "DANGER":DANGER,"SIDEBAR":SIDEBAR,"dark_mode":dark_mode}

# ─── NAV ────────────────────────────────────────────────────────
NAV_PAGES = [
    ("⚡", "Dashboard"),
    ("📍", "GPS Tracker"),
    ("✍️", "Manual Log"),
    ("📋", "History"),
    ("🎯", "Quests"),
    ("📈", "Stats"),
    ("⚙️", "Settings"),
]

def render_bottom_nav(page, c):
    # Only shown on mobile via CSS
    pass

def render_sidebar(profile, page, c):
    with st.sidebar:
        xp = profile.get("xp", 0)
        rank = get_rank(xp)
        progress = get_xp_progress(xp)

        # Logo - Option C: Bracket frame + scanline
        logo_bg = "#0A0C12" if c["dark_mode"] else "#FFF8EC"

        st.markdown(f"""
        <div style='padding:20px 16px 16px; background:{logo_bg}; border-bottom:2px solid {c["ACCENT"]}; position:relative; overflow:hidden;'>
            <div style='position:absolute; top:0; left:0; right:0; height:2px; background:linear-gradient(90deg, {c["ACCENT"]}, {c["ACCENT2"]}, transparent);'></div>
            <div style='border:1px solid {c["ACCENT"]}40; padding:12px 14px; position:relative; border-radius:2px;'>
                <div style='position:absolute; top:-1px; left:12px; right:12px; height:2px; background:{c["ACCENT"]};'></div>
                <div style='position:absolute; bottom:-1px; left:12px; right:12px; height:1px; background:{c["ACCENT"]}60;'></div>
                <div style='position:absolute; top:-3px; left:-3px; width:8px; height:8px; border-top:2px solid {c["ACCENT"]}; border-left:2px solid {c["ACCENT"]}; background:{logo_bg};'></div>
                <div style='position:absolute; top:-3px; right:-3px; width:8px; height:8px; border-top:2px solid {c["ACCENT"]}; border-right:2px solid {c["ACCENT"]}; background:{logo_bg};'></div>
                <div style='position:absolute; bottom:-3px; left:-3px; width:8px; height:8px; border-bottom:2px solid {c["ACCENT"]}60; border-left:2px solid {c["ACCENT"]}60; background:{logo_bg};'></div>
                <div style='position:absolute; bottom:-3px; right:-3px; width:8px; height:8px; border-bottom:2px solid {c["ACCENT"]}60; border-right:2px solid {c["ACCENT"]}60; background:{logo_bg};'></div>
                <div style='font-family:Share Tech Mono,monospace; font-size:0.5rem; color:{c["ACCENT"]}80; letter-spacing:3px; margin-bottom:8px;'>[ SYS:ACTIVE ]</div>
                <div style='font-family:Orbitron,sans-serif; font-size:1.6rem; font-weight:900; letter-spacing:4px; line-height:1; margin-bottom:8px;'>
                    <span style='color:{c["ACCENT"]};'>RUN</span><span style='color:{c["TEXT"]};'>QUEST</span>
                </div>
                <div style='font-family:Share Tech Mono,monospace; font-size:0.48rem; color:{c["TEXT3"]}; letter-spacing:4px;'>v2.0 // PERF TRACK</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Rank block
        st.markdown(f"""
        <div style='padding:14px 16px; border-bottom:1px solid {c["BORDER2"]}50;'>
            <div style='display:flex; align-items:center; gap:10px; margin-bottom:8px;'>
                <span style='font-size:1.8rem; filter:drop-shadow(0 0 8px {c["ACCENT"]});'>{rank["icon"]}</span>
                <div>
                    <div class='rank-chip'>{rank["title"].upper()} · LV.{rank["level"]}</div>
                    <div style='font-family:Orbitron,sans-serif; font-size:1.1rem; font-weight:900; color:{c["ACCENT"]}; margin-top:4px;'>{xp:,} <span style='font-size:0.65rem; color:{c["TEXT3"]}'>XP</span></div>
                </div>
            </div>
            <div class='xp-bar-outer'>
                <div class='xp-bar-inner' style='width:{progress}%;'></div>
            </div>
            <div style='font-family:Share Tech Mono,monospace; font-size:0.6rem; color:{c["TEXT3"]}; letter-spacing:1px;'>{progress}% TO NEXT RANK</div>
        </div>
        """, unsafe_allow_html=True)

        # Nav header
        st.markdown(f"""
        <div style='padding:6px 0 4px; border-bottom:1px solid {c["BORDER2"]}40; margin-bottom:0;'>
            <div style='padding:4px 16px 6px; font-family:Share Tech Mono,monospace;
                font-size:0.5rem; color:{c["TEXT3"]}; letter-spacing:4px;'>◈ NAVIGATE</div>
        </div>
        """, unsafe_allow_html=True)

        NAV_ITEMS = [
            ("Dashboard",   "⬡"),
            ("GPS Tracker", "◎"),
            ("Manual Log",  "▤"),
            ("History",     "▦"),
            ("Quests",      "✦"),
            ("Stats",       "⟋"),
            ("Settings",    "✳"),
        ]

        for icon_char, name in [(v, k) for k, v in NAV_ITEMS]:
            is_active = page == name
            ac = c["ACCENT"]
            t2 = c["TEXT2"]
            dm = c["dark_mode"]
            bar_color = ac if is_active else "transparent"
            row_bg = f"rgba(255,179,0,0.08)" if (is_active and dm) else f"rgba(192,120,0,0.08)" if (is_active and not dm) else "transparent"
            icon_col = ac if is_active else t2
            text_col = ac if is_active else t2

            st.markdown(f"""
            <style>
            div[data-testid="stButton"] button[kind="secondary"]#btn_{name.replace(" ","")} {{
                border-left: 3px solid {bar_color} !important;
                background: {row_bg} !important;
                border-radius: 0 !important;
                border-top: none !important;
                border-right: none !important;
                border-bottom: none !important;
                color: {text_col} !important;
                text-align: left !important;
                padding: 10px 12px 10px 14px !important;
                width: 100% !important;
                font-family: Exo 2, sans-serif !important;
                font-size: 0.9rem !important;
                font-weight: {"700" if is_active else "500"} !important;
                letter-spacing: 0.5px !important;
                box-shadow: none !important;
                display: flex !important;
                align-items: center !important;
                gap: 10px !important;
            }}
            </style>
            """, unsafe_allow_html=True)

            # Use a container div for the border-left styling since CSS override is tricky
            st.markdown(f"""
            <div style='border-left:3px solid {bar_color}; background:{row_bg}; margin:0; padding:0;
                display:flex; align-items:center;'>
                <div style='width:28px; height:28px; border:1.5px solid {bar_color if is_active else c["BORDER2"]+"60"};
                    border-radius:3px; display:flex; align-items:center; justify-content:center;
                    margin:6px 0 6px 12px; flex-shrink:0; background:{"rgba(255,179,0,0.1)" if is_active else "transparent"};'>
                    <span style='font-size:14px; color:{icon_col}; line-height:1;'>{icon_char}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            if st.button(name, key=f"snav_{name}"):
                st.session_state.page = name
                st.rerun()


        # Account + signout
        st.markdown(f"""
        <div style='padding:10px 16px 6px; border-top:1px solid {c["BORDER2"]}40; margin-top:4px;'>
            <div style='font-family:Share Tech Mono,monospace; font-size:0.5rem;
                color:{c["TEXT3"]}; letter-spacing:3px; margin-bottom:6px;'>◈ OPERATIVE</div>
            <div style='display:flex; align-items:center; gap:10px; margin-bottom:8px;'>
                <div style='width:28px; height:28px; border-radius:50%;
                    background:{"rgba(255,179,0,0.12)" if c["dark_mode"] else "rgba(192,120,0,0.12)"};
                    border:1px solid {c["BORDER2"]};
                    display:flex; align-items:center; justify-content:center; flex-shrink:0;
                    font-size:0.85rem;'>&#128100;</div>
                <div style='font-family:Exo 2,sans-serif; font-size:0.75rem; font-weight:600;
                    color:{c["TEXT2"]}; word-break:break-all;'>
                    {st.session_state.user.email}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Sign Out", key="signout"):
            sb.auth.sign_out()
            st.session_state.user = None
            st.rerun()


# ─── ROUTE MAP ───────────────────────────────────────────────────
def render_route_map(route, c, height=280):
    import json
    if not route:
        st.markdown(f"<div style='background:{c['CARD']}; border:1.5px solid {c['BORDER2']}; border-radius:8px; padding:16px; text-align:center; color:{c['TEXT3']}; font-family:Share Tech Mono,monospace; font-size:0.75rem; letter-spacing:1px;'>[ NO ROUTE DATA ]</div>", unsafe_allow_html=True)
        return
    if isinstance(route, str):
        try: route = json.loads(route)
        except: return
    if len(route) < 2:
        st.markdown(f"<div style='background:{c['CARD']}; border:1.5px solid {c['BORDER2']}; border-radius:8px; padding:16px; text-align:center; color:{c['TEXT3']}; font-family:Share Tech Mono,monospace; font-size:0.75rem;'>[ ROUTE TOO SHORT TO DISPLAY ]</div>", unsafe_allow_html=True)
        return

    clat = sum(p["lat"] for p in route) / len(route)
    clon = sum(p["lon"] for p in route) / len(route)
    coords_js = json.dumps([[p["lat"], p["lon"]] for p in route])
    start = route[0]; end = route[-1]

    st.components.v1.html(f"""
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <div id="rmap_{id(route)}" style="width:100%;height:{height}px;border-radius:8px;border:1.5px solid {c['BORDER2']};overflow:hidden;"></div>
    <script>
    (function(){{
        var m=L.map('rmap_{id(route)}',{{zoomControl:true,attributionControl:false}}).setView([{clat},{clon}],15);
        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png',{{maxZoom:19}}).addTo(m);
        var coords={coords_js};
        var poly=L.polyline(coords,{{color:'{c["ACCENT"]}',weight:5,opacity:0.9,lineCap:'round',lineJoin:'round'}}).addTo(m);
        var si=L.divIcon({{html:'<div style="width:14px;height:14px;border-radius:50%;background:#00C853;border:3px solid white;box-shadow:0 0 8px rgba(0,200,83,0.8);"></div>',className:'',iconSize:[14,14],iconAnchor:[7,7]}});
        var ei=L.divIcon({{html:'<div style="width:14px;height:14px;border-radius:50%;background:#FF4444;border:3px solid white;box-shadow:0 0 8px rgba(255,68,68,0.8);"></div>',className:'',iconSize:[14,14],iconAnchor:[7,7]}});
        L.marker([{start['lat']},{start['lon']}],{{icon:si}}).addTo(m).bindPopup('<b>🟢 START</b>');
        L.marker([{end['lat']},{end['lon']}],{{icon:ei}}).addTo(m).bindPopup('<b>🔴 FINISH</b>');
        m.fitBounds(poly.getBounds(),{{padding:[20,20]}});
        L.control.attribution({{position:'bottomright',prefix:''}}).addAttribution('© <a href="https://openstreetmap.org">OSM</a>').addTo(m);
    }})();
    </script>
    """, height=height+10, scrolling=False)


# ─── GPS COMPONENT WITH LIVE MAP ────────────────────────────────
def gps_component(unit_sel, c):
    html = f"""
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&family=Share+Tech+Mono&family=Exo+2:wght@600&display=swap" rel="stylesheet">
<div style="font-family:'Exo 2',sans-serif;">

  <div id="wl-warn" style="display:none; background:rgba(255,179,0,0.1); border:1.5px solid {c['BORDER2']};
    border-radius:8px; padding:10px 14px; margin-bottom:10px; font-family:'Share Tech Mono',monospace;
    font-size:0.75rem; color:{c['ACCENT']}; letter-spacing:1px;">
    ⚠ KEEP SCREEN ACTIVE — DO NOT LOCK DEVICE
  </div>

  <!-- Metrics -->
  <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:8px; margin-bottom:12px;">
    <div style="background:{c['CARD']}; border:1.5px solid {c['BORDER2']}; border-radius:8px; padding:12px 6px; text-align:center; position:relative; overflow:hidden;">
      <div style="position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,transparent,{c['ACCENT']},transparent);"></div>
      <div id="dv" style="font-family:'Orbitron',sans-serif; font-size:1.5rem; font-weight:900; color:{c['ACCENT']}; line-height:1;">0.00</div>
      <div id="du" style="font-family:'Share Tech Mono',monospace; font-size:0.55rem; color:{c['TEXT3']}; letter-spacing:2px; margin-top:3px;">{unit_sel.upper()}</div>
    </div>
    <div style="background:{c['CARD']}; border:1.5px solid {c['BORDER2']}; border-radius:8px; padding:12px 6px; text-align:center; position:relative; overflow:hidden;">
      <div style="position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,transparent,{c['ACCENT']},transparent);"></div>
      <div id="tv" style="font-family:'Orbitron',sans-serif; font-size:1.5rem; font-weight:900; color:{c['TEXT']}; line-height:1;">00:00</div>
      <div style="font-family:'Share Tech Mono',monospace; font-size:0.55rem; color:{c['TEXT3']}; letter-spacing:2px; margin-top:3px;">TIME</div>
    </div>
    <div style="background:{c['CARD']}; border:1.5px solid {c['BORDER2']}; border-radius:8px; padding:12px 6px; text-align:center; position:relative; overflow:hidden;">
      <div style="position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,transparent,{c['ACCENT']},transparent);"></div>
      <div id="pv" style="font-family:'Orbitron',sans-serif; font-size:1.5rem; font-weight:900; color:{c['TEXT']}; line-height:1;">--:--</div>
      <div id="pu" style="font-family:'Share Tech Mono',monospace; font-size:0.55rem; color:{c['TEXT3']}; letter-spacing:2px; margin-top:3px;">MIN/{unit_sel.upper()}</div>
    </div>
  </div>

  <!-- Status + accuracy -->
  <div id="st" style="text-align:center; font-family:'Share Tech Mono',monospace; font-size:0.75rem; color:{c['TEXT3']}; letter-spacing:2px; margin-bottom:8px;">[ SYSTEM READY — PRESS INITIATE ]</div>
  <div id="ac" style="display:none; text-align:center; font-family:'Share Tech Mono',monospace; font-size:0.7rem; color:{c['TEXT3']}; letter-spacing:1px; margin-bottom:8px;">GPS: <span id="av" style="color:{c['ACCENT']};">--</span>m accuracy</div>

  <!-- Buttons -->
  <div style="display:flex; gap:8px; margin-bottom:12px;">
    <button id="b-start" onclick="gs()" style="flex:1; padding:13px 6px; border-radius:6px; border:2px solid {c['ACCENT']}; cursor:pointer; background:rgba(255,179,0,0.12); color:{c['ACCENT']}; font-family:'Orbitron',sans-serif; font-size:0.7rem; font-weight:800; letter-spacing:2px;">▶ INITIATE</button>
    <button id="b-pause" onclick="gp()" style="flex:1; padding:13px 6px; border-radius:6px; border:2px solid #FF8C00; cursor:pointer; background:{c['CARD']}; color:#FF8C00; font-family:'Orbitron',sans-serif; font-size:0.7rem; font-weight:800; letter-spacing:2px; display:none;">⏸ PAUSE</button>
    <button id="b-resume" onclick="gr()" style="flex:1; padding:13px 6px; border-radius:6px; border:2px solid {c['ACCENT']}; cursor:pointer; background:rgba(255,179,0,0.12); color:{c['ACCENT']}; font-family:'Orbitron',sans-serif; font-size:0.7rem; font-weight:800; letter-spacing:2px; display:none;">▶ RESUME</button>
    <button id="b-stop" onclick="gst()" style="flex:1; padding:13px 6px; border-radius:6px; border:2px solid #FF5555; cursor:pointer; background:{c['CARD']}; color:#FF5555; font-family:'Orbitron',sans-serif; font-size:0.7rem; font-weight:800; letter-spacing:2px; display:none;">■ HALT</button>
  </div>

  <!-- LIVE MAP -->
  <div id="map-wrap" style="display:none; margin-bottom:12px; border-radius:8px; overflow:hidden; border:1.5px solid {c['BORDER2']};">
    <div style="background:{c['CARD']}; padding:8px 12px; font-family:'Share Tech Mono',monospace; font-size:0.6rem; color:{c['ACCENT']}; letter-spacing:2px; border-bottom:1px solid {c['BORDER2']};">
      ◈ LIVE POSITION TRACKING
    </div>
    <div id="livemap" style="width:100%; height:280px;"></div>
  </div>

  <!-- Hidden inputs -->
  <input type="hidden" id="fd" value="0">
  <input type="hidden" id="ft" value="0">
  <input type="hidden" id="fr" value="[]">

  <!-- Summary -->
  <div id="sum" style="display:none; background:{c['CARD']}; border:1.5px solid {c['BORDER2']}; border-radius:8px; padding:16px; position:relative; overflow:hidden;">
    <div style="position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,transparent,{c['ACCENT']},transparent);"></div>
    <div style="font-family:'Orbitron',sans-serif; font-size:0.7rem; font-weight:700; color:{c['ACCENT']}; letter-spacing:2px; margin-bottom:12px;">◈ RUN SUMMARY</div>
    <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-bottom:14px;">
      <div style="text-align:center;"><div style="font-family:'Exo 2',sans-serif;font-size:0.7rem;font-weight:700;color:{c['TEXT3']};text-transform:uppercase;margin-bottom:4px;">Distance</div><div id="sd" style="font-family:'Orbitron',sans-serif;font-size:1.2rem;font-weight:800;color:{c['ACCENT']};"></div></div>
      <div style="text-align:center;"><div style="font-family:'Exo 2',sans-serif;font-size:0.7rem;font-weight:700;color:{c['TEXT3']};text-transform:uppercase;margin-bottom:4px;">Duration</div><div id="st2" style="font-family:'Orbitron',sans-serif;font-size:1.2rem;font-weight:800;color:{c['TEXT']};"></div></div>
      <div style="text-align:center;"><div style="font-family:'Exo 2',sans-serif;font-size:0.7rem;font-weight:700;color:{c['TEXT3']};text-transform:uppercase;margin-bottom:4px;">Avg Pace</div><div id="sp" style="font-family:'Orbitron',sans-serif;font-size:1.2rem;font-weight:800;color:{c['TEXT']};"></div></div>
      <div style="text-align:center;"><div style="font-family:'Exo 2',sans-serif;font-size:0.7rem;font-weight:700;color:{c['TEXT3']};text-transform:uppercase;margin-bottom:4px;">Status</div><div style="font-family:'Orbitron',sans-serif;font-size:1.2rem;font-weight:800;color:{c['ACCENT']};">DONE ✓</div></div>
    </div>
    <!-- Route preview in summary -->
    <div id="sum-map-wrap" style="border-radius:6px; overflow:hidden; border:1px solid {c['BORDER2']}; margin-bottom:14px;">
      <div id="summap" style="width:100%; height:200px;"></div>
    </div>
    <button onclick="gsave()" style="width:100%;padding:13px;border-radius:6px;border:2px solid {c['ACCENT']};cursor:pointer;background:rgba(255,179,0,0.12);color:{c['ACCENT']};font-family:'Orbitron',sans-serif;font-size:0.75rem;font-weight:800;letter-spacing:2px;">◈ UPLOAD RUN DATA</button>
  </div>
</div>

<script>
var wId=null,tI=null,lP=null,tD=0,tS=0,paused=false,wl=null,unit='{unit_sel}';
var route=[],liveMap=null,livePoly=null,liveMarker=null,startMarker=null,sumMap=null;

function hav(a,b,c,d){{var R=6371,dL=(c-a)*Math.PI/180,dl=(d-b)*Math.PI/180,x=Math.sin(dL/2)**2+Math.cos(a*Math.PI/180)*Math.cos(c*Math.PI/180)*Math.sin(dl/2)**2;return R*2*Math.atan2(Math.sqrt(x),Math.sqrt(1-x));}}
function ft(s){{var h=Math.floor(s/3600),m=Math.floor((s%3600)/60),x=s%60;return h>0?h+':'+String(m).padStart(2,'0')+':'+String(x).padStart(2,'0'):String(m).padStart(2,'0')+':'+String(x).padStart(2,'0');}}
function fp(s,d){{if(d<0.01)return'--:--';var p=(s/60)/d;if(unit==='mi')p/=1.60934;var m=Math.floor(p),x=Math.round((p-m)*60);return m+':'+String(x).padStart(2,'0');}}
function fd2(k){{return unit==='mi'?(k*0.621371).toFixed(2):k.toFixed(2);}}
function setStatus(html){{document.getElementById('st').innerHTML=html;}}

async function rwl(){{try{{if('wakeLock'in navigator)wl=await navigator.wakeLock.request('screen');}}catch(e){{document.getElementById('wl-warn').style.display='block';}}}}

function initLiveMap(lat, lon){{
    document.getElementById('map-wrap').style.display='block';
    if(liveMap){{liveMap.remove(); liveMap=null;}}
    liveMap=L.map('livemap',{{zoomControl:false,attributionControl:false}}).setView([lat,lon],17);
    L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png',{{maxZoom:19}}).addTo(liveMap);

    // Start marker
    var si=L.divIcon({{html:'<div style="width:14px;height:14px;border-radius:50%;background:#00C853;border:3px solid white;box-shadow:0 0 10px rgba(0,200,83,0.9);"></div>',className:'',iconSize:[14,14],iconAnchor:[7,7]}});
    startMarker=L.marker([lat,lon],{{icon:si}}).addTo(liveMap).bindPopup('<b>🟢 START</b>');

    // Live position dot (pulsing gold)
    var li=L.divIcon({{html:'<div style="width:16px;height:16px;border-radius:50%;background:{c["ACCENT"]};border:3px solid white;box-shadow:0 0 12px {c["ACCENT"]};animation:pg 1.5s infinite;"></div>',className:'',iconSize:[16,16],iconAnchor:[8,8]}});
    liveMarker=L.marker([lat,lon],{{icon:li,zIndexOffset:1000}}).addTo(liveMap);

    // Route polyline
    livePoly=L.polyline([[lat,lon]],{{color:'{c["ACCENT"]}',weight:5,opacity:0.9,lineCap:'round',lineJoin:'round'}}).addTo(liveMap);

    L.control.zoom({{position:'bottomright'}}).addTo(liveMap);
    L.control.attribution({{position:'bottomleft',prefix:''}}).addAttribution('© <a href="https://openstreetmap.org">OSM</a>').addTo(liveMap);
}}

function updateLiveMap(lat, lon){{
    if(!liveMap) return;
    liveMarker.setLatLng([lat,lon]);
    livePoly.addLatLng([lat,lon]);
    liveMap.panTo([lat,lon],{{animate:true,duration:1}});
}}

function initSumMap(){{
    if(route.length < 2) return;
    setTimeout(function(){{
        if(sumMap){{sumMap.remove(); sumMap=null;}}
        var clat=route.reduce((s,p)=>s+p.lat,0)/route.length;
        var clon=route.reduce((s,p)=>s+p.lon,0)/route.length;
        sumMap=L.map('summap',{{zoomControl:false,attributionControl:false}}).setView([clat,clon],15);
        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png',{{maxZoom:19}}).addTo(sumMap);
        var coords=route.map(p=>[p.lat,p.lon]);
        var poly=L.polyline(coords,{{color:'{c["ACCENT"]}',weight:5,opacity:0.9}}).addTo(sumMap);
        var si=L.divIcon({{html:'<div style="width:12px;height:12px;border-radius:50%;background:#00C853;border:2px solid white;"></div>',className:'',iconSize:[12,12],iconAnchor:[6,6]}});
        var ei=L.divIcon({{html:'<div style="width:12px;height:12px;border-radius:50%;background:#FF4444;border:2px solid white;"></div>',className:'',iconSize:[12,12],iconAnchor:[6,6]}});
        L.marker(coords[0],{{icon:si}}).addTo(sumMap).bindPopup('<b>🟢 START</b>');
        L.marker(coords[coords.length-1],{{icon:ei}}).addTo(sumMap).bindPopup('<b>🔴 FINISH</b>');
        sumMap.fitBounds(poly.getBounds(),{{padding:[16,16]}});
    }},300);
}}

function gs(){{
    if(!navigator.geolocation){{setStatus('<span style="color:#FF5555;font-family:Share Tech Mono,monospace;">❌ GPS NOT AVAILABLE</span>');return;}}
    tD=0;tS=0;lP=null;paused=false;route=[];
    document.getElementById('b-start').style.display='none';
    document.getElementById('b-pause').style.display='flex';
    document.getElementById('b-stop').style.display='flex';
    document.getElementById('sum').style.display='none';
    document.getElementById('ac').style.display='block';
    setStatus('<span style="display:inline-flex;align-items:center;gap:8px;color:{c["ACCENT"]};font-family:Share Tech Mono,monospace;font-size:0.75rem;letter-spacing:2px;"><span style="width:10px;height:10px;border-radius:50%;background:{c["ACCENT"]};box-shadow:0 0 8px {c["ACCENT"]};animation:pg 1.5s infinite;display:inline-block;"></span>TRACKING ACTIVE</span>');
    rwl();
    tI=setInterval(function(){{if(!paused){{tS++;document.getElementById('tv').textContent=ft(tS);document.getElementById('pv').textContent=fp(tS,tD);}}}},1000);
    wId=navigator.geolocation.watchPosition(
        function(pos){{
            var lat=pos.coords.latitude, lon=pos.coords.longitude;
            var ac=Math.round(pos.coords.accuracy);
            var av=document.getElementById('av');
            av.textContent=ac;
            av.style.color=ac<15?'{c["ACCENT"]}':ac<30?'#FF8C00':'#FF5555';
            if(!paused){{
                var np={{lat:lat,lon:lon}};
                // Init map on first fix
                if(!liveMap){{initLiveMap(lat,lon);}}
                if(lP){{
                    var d=hav(lP.lat,lP.lon,lat,lon);
                    if(d<0.3&&d>0.002){{
                        tD+=d;
                        document.getElementById('dv').textContent=fd2(tD);
                    }}
                }}
                route.push(np);
                updateLiveMap(lat,lon);
                lP=np;
            }}
        }},
        function(e){{setStatus('<span style="color:#FF5555;font-family:Share Tech Mono,monospace;font-size:0.7rem;">⚠ GPS: '+e.message+'</span>');}},
        {{enableHighAccuracy:true,maximumAge:2000,timeout:15000}}
    );
}}

function gp(){{paused=true;document.getElementById('b-pause').style.display='none';document.getElementById('b-resume').style.display='flex';setStatus('<span style="color:#FF8C00;font-family:Share Tech Mono,monospace;font-size:0.75rem;letter-spacing:2px;">⏸ SESSION PAUSED</span>');}}
function gr(){{paused=false;lP=null;document.getElementById('b-resume').style.display='none';document.getElementById('b-pause').style.display='flex';setStatus('<span style="display:inline-flex;align-items:center;gap:8px;color:{c["ACCENT"]};font-family:Share Tech Mono,monospace;font-size:0.75rem;letter-spacing:2px;"><span style="width:10px;height:10px;border-radius:50%;background:{c["ACCENT"]};animation:pg 1.5s infinite;display:inline-block;"></span>TRACKING ACTIVE</span>');}}

function gst(){{
    paused=false;clearInterval(tI);
    if(wId!==null)navigator.geolocation.clearWatch(wId);
    if(wl)wl.release();
    document.getElementById('b-pause').style.display='none';
    document.getElementById('b-resume').style.display='none';
    document.getElementById('b-stop').style.display='none';
    document.getElementById('b-start').style.display='flex';
    document.getElementById('ac').style.display='none';
    document.getElementById('map-wrap').style.display='none';
    setStatus('<span style="color:{c["TEXT3"]};font-family:Share Tech Mono,monospace;font-size:0.7rem;letter-spacing:1px;">[ SESSION ENDED — REVIEW & UPLOAD ]</span>');
    document.getElementById('sd').textContent=fd2(tD)+' '+unit;
    document.getElementById('st2').textContent=ft(tS);
    document.getElementById('sp').textContent=fp(tS,tD)+'/'+unit;
    document.getElementById('fd').value=tD.toFixed(4);
    document.getElementById('ft').value=tS;
    document.getElementById('fr').value=JSON.stringify(route);
    document.getElementById('sum').style.display='block';
    initSumMap();
}}

function gsave(){{
    var d=parseFloat(document.getElementById('fd').value);
    var t=parseInt(document.getElementById('ft').value);
    var r=document.getElementById('fr').value;
    if(t<1){{alert('No run data to save! Make sure you pressed INITIATE first.');return;}}
    if(d<=0){{
        // Fallback: try to read from displayed value
        var dv=document.getElementById('dv');
        if(dv){{d=parseFloat(dv.textContent)||0;}}
    }}
    if(d<=0){{alert('Distance is 0. Please run a short distance before saving.');return;}}
    var u=new URL(window.location.href);
    u.searchParams.set('gps_dist',d.toFixed(4));
    u.searchParams.set('gps_dur',t);
    u.searchParams.set('gps_unit',unit);
    u.searchParams.set('gps_route',encodeURIComponent(r));
    window.location.href=u.toString();
}}
</script>
<style>@keyframes pg{{0%,100%{{opacity:1;box-shadow:0 0 8px {c["ACCENT"]}}}50%{{opacity:0.3;box-shadow:none}}}}</style>
"""
    st.components.v1.html(html, height=700, scrolling=True)


# ─── AUTH ────────────────────────────────────────────────────────
def auth_page(c):
    st.markdown(f"""
    <div style='text-align:center; padding:50px 0 28px;'>
        <div style='font-family:Share Tech Mono,monospace; font-size:0.65rem; color:{c["TEXT3"]}; letter-spacing:6px; margin-bottom:14px;'>◈ SYSTEM INITIALIZED ◈</div>
        <div style='font-family:Orbitron,sans-serif; font-size:2.4rem; font-weight:900; letter-spacing:6px; line-height:1.2;'>
            <span style='color:{c["ACCENT"]};'>RUN</span><span style='color:{c["TEXT"]};'>QUEST</span>
        </div>
        <div style='font-family:Share Tech Mono,monospace; font-size:0.6rem; color:{c["TEXT3"]}; letter-spacing:5px; margin-top:8px;'>PERFORMANCE TRACKING OS v2.0</div>
        <div style='width:120px; height:2px; background:linear-gradient(90deg,transparent,{c["ACCENT"]},transparent); margin:18px auto;'></div>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["◈  SIGN IN", "◈  REGISTER"])
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
    st.markdown("<div class='page-title'>◈ COMMAND CENTER</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='page-sub'>OPERATIVE: {st.session_state.user.email.split('@')[0].upper()}</div>", unsafe_allow_html=True)

    st.markdown(f"""
    <div class='cyber-card'>
      <div style='display:flex; align-items:center; gap:14px; flex-wrap:wrap;'>
        <div style='font-size:2.8rem; filter:drop-shadow(0 0 10px {c["ACCENT"]});'>{rank["icon"]}</div>
        <div style='flex:1; min-width:140px;'>
          <div class='rank-chip'>{rank["title"].upper()} · LEVEL {rank["level"]}</div>
          <div style='font-family:Orbitron,sans-serif; font-size:1.7rem; font-weight:900; color:{c["ACCENT"]}; margin:6px 0 2px;'>{xp:,} <span style='font-size:0.85rem; color:{c["TEXT3"]}'>XP</span></div>
          <div style='font-family:Exo 2,sans-serif; font-size:0.9rem; font-weight:600; color:{c["TEXT2"]};'>{"▶ Next: "+next_rank["title"]+" @ "+f"{next_rank['min_xp']:,}"+" XP" if next_rank else "◈ MAX RANK ACHIEVED"}</div>
        </div>
      </div>
      <div class='xp-bar-outer' style='margin-top:12px;'><div class='xp-bar-inner' style='width:{progress}%;'></div></div>
      <div style='font-family:Share Tech Mono,monospace; font-size:0.65rem; color:{c["TEXT3"]}; letter-spacing:1px;'>{progress}% CAPACITY</div>
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
    ca, cb = st.columns(2)
    with ca:
        st.markdown(f"<div style='font-family:Orbitron,sans-serif; font-size:0.82rem; font-weight:700; color:{c['ACCENT']}; letter-spacing:2px; margin-bottom:10px;'>◈ ACTIVE MISSIONS</div>", unsafe_allow_html=True)
        active = [q for q in QUESTS if not check_quest(q["id"], runs)][:3]
        if not active: st.success("◈ All missions complete! 🎉")
        for q in active:
            st.markdown(f"""
            <div class='quest-card'>
              <div style='display:flex; align-items:center; gap:10px;'>
                <span style='font-size:1.4rem;'>{q['icon']}</span>
                <div style='flex:1;'>
                  <div style='font-family:Exo 2,sans-serif; font-size:1rem; font-weight:700; color:{c["TEXT"]};'>{q['title']}</div>
                  <div style='font-family:Exo 2,sans-serif; font-size:0.82rem; color:{c["TEXT2"]}; margin-top:2px;'>{q['desc']}</div>
                </div>
                <div style='font-family:Orbitron,sans-serif; font-size:0.72rem; font-weight:800; color:{c["ACCENT"]}; white-space:nowrap; background:rgba(255,179,0,0.1); border:1px solid {c["BORDER2"]}; border-radius:4px; padding:3px 8px;'>+{q['xp']} XP</div>
              </div>
            </div>""", unsafe_allow_html=True)
    with cb:
        st.markdown(f"<div style='font-family:Orbitron,sans-serif; font-size:0.82rem; font-weight:700; color:{c['ACCENT']}; letter-spacing:2px; margin-bottom:10px;'>◈ LAST MISSION</div>", unsafe_allow_html=True)
        if not runs:
            st.info("No missions yet. Start your first run!")
        else:
            r = runs[0]
            pb = f"<span class='pb-badge'>◈ PB</span><br>" if r.get("is_pb") else ""
            st.markdown(f"""
            <div class='run-card'>
              {pb}
              <div style='display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-top:4px;'>
                <div><div class='data-label'>Distance</div><div class='data-val'>{format_distance(r["distance_km"],unit)} {unit}</div></div>
                <div><div class='data-label'>Duration</div><div class='data-val'>{format_time(r["duration_seconds"])}</div></div>
                <div><div class='data-label'>Avg Pace</div><div class='data-val'>{format_pace(r["duration_seconds"],r["distance_km"],unit)}/{unit}</div></div>
                <div><div class='data-label'>XP</div><div class='data-val' style='color:{c["ACCENT"]}'>+{r.get("xp_earned",0)}</div></div>
              </div>
              <div style='margin-top:8px; font-family:Share Tech Mono,monospace; font-size:0.65rem; color:{c["TEXT3"]};'>{r["started_at"][:10]}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<hr class='divider'>", unsafe_allow_html=True)
    st.markdown(f"<div style='font-family:Orbitron,sans-serif; font-size:0.82rem; font-weight:700; color:{c['ACCENT']}; letter-spacing:2px; margin-bottom:10px;'>◈ CYCLE REPORT</div>", unsafe_allow_html=True)
    w1,w2,w3 = st.columns(3)
    with w1: st.markdown(f"<div class='metric-card'><div class='metric-value'>{len(week_runs)}</div><div class='metric-label'>Runs</div></div>", unsafe_allow_html=True)
    with w2: st.markdown(f"<div class='metric-card'><div class='metric-value'>{format_distance(week_dist,unit)}</div><div class='metric-label'>Distance</div></div>", unsafe_allow_html=True)
    with w3: st.markdown(f"<div class='metric-card'><div class='metric-value'>{format_time(week_time)}</div><div class='metric-label'>Total Time</div></div>", unsafe_allow_html=True)


def page_gps_tracker(user_id, profile, runs, unit, c):
    import json, urllib.parse
    st.markdown("<div class='page-title'>◈ GPS UPLINK</div>", unsafe_allow_html=True)
    st.markdown("<div class='page-sub'>REAL-TIME POSITION & ROUTE TRACKING</div>", unsafe_allow_html=True)
    st.warning("⚠ Keep this tab open and screen ON while running!")

    params = st.query_params
    if "gps_dist" in params and "gps_dur" in params:
        try:
            dist_km = float(params["gps_dist"])
            dur = int(params["gps_dur"])
            gu = params.get("gps_unit", "km")
            route_raw = params.get("gps_route", "[]")
            try:
                route = json.loads(urllib.parse.unquote(route_raw))
            except:
                route = []
            if gu == "mi": dist_km = dist_km / 0.621371
            if dist_km > 0.001 and dur > 0:
                total_xp, is_pb, fresh = process_and_save_run(
                    user_id, profile, runs, dist_km, dur, unit, route
                )
                st.query_params.clear()
                st.session_state["last_run_saved"] = {
                    "dist": dist_km, "dur": dur, "xp": total_xp,
                    "is_pb": is_pb, "fresh": fresh, "route": route, "unit": unit
                }
                st.rerun()
        except Exception as e:
            st.error(f"Save error: {e}")
            st.query_params.clear()

    # Show save result if just saved
    if "last_run_saved" in st.session_state:
        r = st.session_state.pop("last_run_saved")
        st.success(f"✅ Run saved! {format_distance(r['dist'], r['unit'])} {r['unit']} in {format_time(r['dur'])}")
        if r["is_pb"]:
            st.balloons()
            st.success("🏅 New Personal Record!")
        st.info(f"⭐ +{r['xp']} XP earned!")
        for q in r["fresh"]:
            st.success(f"🎯 Quest: {q['icon']} {q['title']} (+{q['xp']} XP)")
        if r["route"] and len(r["route"]) >= 2:
            st.markdown(f"<div style='font-family:Orbitron,sans-serif; font-size:0.8rem; font-weight:700; color:{c['ACCENT']}; letter-spacing:2px; margin:12px 0 8px;'>◈ YOUR ROUTE</div>", unsafe_allow_html=True)
            render_route_map(r["route"], c, height=300)

    unit_sel = st.radio("Unit System", ["km", "mi"], horizontal=True, index=0 if unit == "km" else 1)
    gps_component(unit_sel, c)
    st.caption("💡 Go outside first · Wait for accuracy <15m · Keep phone in hand or armband")


def page_log_run(user_id, profile, runs, unit, c):
    st.markdown("<div class='page-title'>◈ MANUAL LOG</div>", unsafe_allow_html=True)
    st.markdown("<div class='page-sub'>LOG FROM WATCH OR FITNESS APP</div>", unsafe_allow_html=True)
    with st.form("log_run_form"):
        c1, c2 = st.columns(2)
        with c1: distance = st.number_input("Distance", min_value=0.1, max_value=200.0, step=0.1, value=5.0)
        with c2: unit_sel = st.selectbox("Unit", ["km", "mi"], index=0 if unit == "km" else 1)
        c3,c4,c5 = st.columns(3)
        with c3: hours = st.number_input("Hours", min_value=0, max_value=24, value=0)
        with c4: minutes = st.number_input("Minutes", min_value=0, max_value=59, value=30)
        with c5: secs = st.number_input("Seconds", min_value=0, max_value=59, value=0)
        if st.form_submit_button("◈  SAVE RUN", use_container_width=True):
            dist_km = distance if unit_sel == "km" else distance / 0.621371
            total_secs = hours*3600 + minutes*60 + secs
            if total_secs == 0: st.error("Please enter a valid duration.")
            else:
                total_xp, is_pb, fresh = process_and_save_run(user_id, profile, runs, dist_km, total_secs, unit_sel)
                st.success(f"✅ Saved! {distance} {unit_sel} · {format_time(total_secs)} · {format_pace(total_secs,dist_km,unit_sel)}/{unit_sel}")
                if is_pb: st.balloons(); st.success("🏅 New Personal Record!")
                st.info(f"⭐ +{total_xp} XP earned!")
                for q in fresh: st.success(f"🎯 Quest: {q['icon']} {q['title']} (+{q['xp']} XP)")
                st.rerun()


def page_history(user_id, runs, unit, c):
    import json
    st.markdown("<div class='page-title'>◈ MISSION LOG</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='page-sub'>{len(runs)} RECORDS IN DATABASE</div>", unsafe_allow_html=True)
    if not runs: st.info("No runs logged yet!"); return
    unit_sel = st.radio("Unit", ["km", "mi"], horizontal=True, index=0 if unit == "km" else 1)

    for r in runs:
        pb = f"<span class='pb-badge'>◈ PB</span> " if r.get("is_pb") else ""
        route = r.get("route", [])
        if isinstance(route, str):
            try: route = json.loads(route)
            except: route = []
        has_route = route and len(route) >= 2

        col1, col2 = st.columns([5,1])
        with col1:
            st.markdown(f"""
            <div class='run-card'>
              <div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;'>
                <span style='font-family:Share Tech Mono,monospace; font-size:0.72rem; color:{c["TEXT3"]};'>{r["started_at"][:10]}</span>
                <span>{pb}<span style='font-family:Orbitron,sans-serif; font-size:0.72rem; font-weight:800; color:{c["ACCENT"]};'>+{r.get("xp_earned",0)} XP</span></span>
              </div>
              <div style='display:grid; grid-template-columns:1fr 1fr 1fr; gap:8px;'>
                <div><div class='data-label'>Distance</div><div class='data-val'>{format_distance(r["distance_km"],unit_sel)} {unit_sel}</div></div>
                <div><div class='data-label'>Time</div><div class='data-val'>{format_time(r["duration_seconds"])}</div></div>
                <div><div class='data-label'>Pace</div><div class='data-val'>{format_pace(r["duration_seconds"],r["distance_km"],unit_sel)}/{unit_sel}</div></div>
              </div>
              {"<div style='margin-top:8px; font-family:Share Tech Mono,monospace; font-size:0.6rem; color:" + c["ACCENT"] + "; letter-spacing:1px;'>🗺 ROUTE AVAILABLE — EXPAND BELOW</div>" if has_route else "<div style='margin-top:8px; font-family:Share Tech Mono,monospace; font-size:0.6rem; color:" + c["TEXT3"] + "; letter-spacing:1px;'>[ NO ROUTE DATA ]</div>"}
            </div>""", unsafe_allow_html=True)

        with col2:
            if st.button("✕", key=f"del_{r['id']}"): delete_run(r["id"]); st.rerun()

        # Show route map expandable
        if has_route:
            with st.expander(f"🗺 View Route Map — {r['started_at'][:10]}"):
                render_route_map(route, c, height=260)


def page_quests(user_id, profile, runs, c):
    st.markdown("<div class='page-title'>◈ MISSION BOARD</div>", unsafe_allow_html=True)
    xp = profile.get("xp", 0)
    rank = get_rank(xp); next_rank = get_next_rank(xp); progress = get_xp_progress(xp)
    completed_ids = set(q["id"] for q in QUESTS if check_quest(q["id"], runs))
    completed = [q for q in QUESTS if q["id"] in completed_ids]
    pending = [q for q in QUESTS if q["id"] not in completed_ids]

    st.markdown(f"<div style='font-family:Orbitron,sans-serif; font-size:0.82rem; font-weight:700; color:{c['ACCENT']}; letter-spacing:2px; margin-bottom:10px;'>◈ RANK LADDER</div>", unsafe_allow_html=True)
    cols = st.columns(len(RANKS))
    for i, r in enumerate(RANKS):
        is_cur = r["level"] == rank["level"]; unlocked = xp >= r["min_xp"]
        with cols[i]:
            st.markdown(f"""
            <div style='text-align:center; padding:8px 3px; border-radius:6px;
              border:2px solid {"" + c["ACCENT"] + "" if is_cur else c["BORDER"]};
              background:{"rgba(255,179,0,0.1)" if is_cur else "transparent"};
              opacity:{"1" if unlocked else "0.25"};
              box-shadow:{"0 0 12px rgba(255,179,0,0.2)" if is_cur else "none"}'>
              <div style='font-size:1.1rem;'>{r["icon"]}</div>
              <div style='font-family:Orbitron,sans-serif; font-size:0.48rem; font-weight:700; color:{"" + c["ACCENT"] + "" if is_cur else c["TEXT3"]}; margin-top:2px;'>{r["title"][:4].upper()}</div>
              {"<div style='font-size:0.48rem; color:" + c["ACCENT"] + "; font-family:Share Tech Mono,monospace;'>YOU</div>" if is_cur else ""}
            </div>""", unsafe_allow_html=True)

    st.markdown(f"""
    <div style='margin:12px 0;'>
      <div style='display:flex; justify-content:space-between; font-family:Exo 2,sans-serif; font-size:0.88rem; font-weight:600; color:{c["TEXT2"]}; margin-bottom:6px;'>
        <span>{rank["icon"]} {rank["title"]} — {xp:,} XP</span>
        <span>{"→ "+next_rank["title"]+" @ "+f"{next_rank['min_xp']:,}" if next_rank else "◈ MAX RANK"}</span>
      </div>
      <div class='xp-bar-outer'><div class='xp-bar-inner' style='width:{progress}%;'></div></div>
      <div style='font-family:Exo 2,sans-serif; font-size:0.82rem; font-weight:600; color:{c["TEXT3"]}; margin-top:4px;'>{progress}% — {str(next_rank["min_xp"]-xp)+" XP to next rank" if next_rank else "Transcendent achieved!"}</div>
    </div>""", unsafe_allow_html=True)

    st.markdown("<hr class='divider'>", unsafe_allow_html=True)
    if pending:
        st.markdown(f"<div style='font-family:Orbitron,sans-serif; font-size:0.82rem; font-weight:700; color:{c['ACCENT']}; letter-spacing:2px; margin-bottom:10px;'>◈ ACTIVE QUESTS ({len(pending)})</div>", unsafe_allow_html=True)
        for q in pending:
            st.markdown(f"""
            <div class='quest-card'>
              <div style='display:flex; align-items:center; gap:12px;'>
                <span style='font-size:1.4rem;'>{q['icon']}</span>
                <div style='flex:1;'>
                  <div style='font-family:Exo 2,sans-serif; font-size:1rem; font-weight:700; color:{c["TEXT"]};'>{q['title']}</div>
                  <div style='font-family:Exo 2,sans-serif; font-size:0.85rem; color:{c["TEXT2"]}; margin-top:2px;'>{q['desc']}</div>
                </div>
                <div style='background:rgba(255,179,0,0.12); border:1.5px solid {c["BORDER2"]}; border-radius:4px; padding:4px 10px; font-family:Orbitron,sans-serif; font-size:0.68rem; font-weight:800; color:{c["ACCENT"]}; white-space:nowrap;'>+{q['xp']} XP</div>
              </div>
            </div>""", unsafe_allow_html=True)

    if completed:
        st.markdown(f"<div style='font-family:Orbitron,sans-serif; font-size:0.82rem; font-weight:700; color:{c['ACCENT']}; letter-spacing:2px; margin:14px 0 10px;'>◈ COMPLETED ({len(completed)})</div>", unsafe_allow_html=True)
        cols2 = st.columns(2)
        for i, q in enumerate(completed):
            with cols2[i%2]:
                st.markdown(f"""
                <div class='quest-done'>
                  <div style='display:flex; align-items:center; gap:10px;'>
                    <span style='font-size:1.2rem;'>{q['icon']}</span>
                    <div style='flex:1;'>
                      <div style='font-family:Exo 2,sans-serif; font-size:0.95rem; font-weight:700; color:{c["TEXT"]};'>{q['title']}</div>
                      <div style='font-family:Exo 2,sans-serif; font-size:0.82rem; color:{c["ACCENT"]}; margin-top:2px;'>+{q['xp']} XP earned</div>
                    </div>
                    <span style='font-size:1.1rem;'>✅</span>
                  </div>
                </div>""", unsafe_allow_html=True)


def page_stats(user_id, runs, unit, c):
    st.markdown("<div class='page-title'>◈ DATA ANALYSIS</div>", unsafe_allow_html=True)
    if not runs: st.info("Complete some runs to see your stats!"); return
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
        d = r["started_at"][:10]
        pv = (r["duration_seconds"]/60)/r["distance_km"]
        if unit_sel=='mi': pv/=1.60934
        cp[d]=round(pv,2); cd[d]=float(format_distance(r["distance_km"],unit_sel)); cx[d]=r.get("xp_earned",0)
    t1,t2,t3 = st.tabs(["⚡ Pace Trend",f"🗺 Distance ({unit_sel})","⭐ XP Earned"])
    with t1: st.line_chart(cp)
    with t2: st.bar_chart(cd)
    with t3: st.bar_chart(cx)
    st.markdown("<hr class='divider'>", unsafe_allow_html=True)
    st.markdown(f"<div style='font-family:Orbitron,sans-serif; font-size:0.82rem; font-weight:700; color:{c['ACCENT']}; letter-spacing:2px; margin-bottom:10px;'>◈ PERSONAL RECORDS</div>", unsafe_allow_html=True)
    pb_distances = [1,3,5,10,21.1,42.2]
    pb_labels = {1:"1 KM",3:"3 KM",5:"5 KM",10:"10 KM",21.1:"Half Marathon",42.2:"Marathon"}
    pb_cols = st.columns(3); found=0
    for dist in pb_distances:
        rel = [r for r in runs if abs(r["distance_km"]-dist)<0.2]
        if rel:
            pb = min(rel, key=lambda r: r["duration_seconds"])
            with pb_cols[found%3]:
                st.markdown(f"""
                <div style='background:{c["CARD"]}; border:1.5px solid {c["BORDER2"]}; border-top:3px solid {c["ACCENT"]}; border-radius:8px; padding:14px; text-align:center; margin-bottom:10px;'>
                  <div style='font-family:Orbitron,sans-serif; font-size:0.68rem; font-weight:700; color:{c["ACCENT"]}; letter-spacing:1px;'>{pb_labels[dist]}</div>
                  <div style='font-family:Orbitron,sans-serif; font-size:1.3rem; font-weight:800; color:{c["TEXT"]}; margin-top:6px;'>{format_time(pb["duration_seconds"])}</div>
                  <div style='font-family:Share Tech Mono,monospace; font-size:0.68rem; color:{c["TEXT2"]}; margin-top:4px;'>{format_pace(pb["duration_seconds"],pb["distance_km"],unit_sel)}/{unit_sel}</div>
                </div>""", unsafe_allow_html=True)
            found += 1
    if found==0: st.caption("No personal records yet. Complete runs near standard distances.")


def page_settings(user_id, profile, c):
    st.markdown("<div class='page-title'>◈ SYSTEM CONFIG</div>", unsafe_allow_html=True)
    with st.form("settings_form"):
        st.markdown(f"<div style='font-family:Orbitron,sans-serif; font-size:0.8rem; font-weight:700; color:{c['ACCENT']}; letter-spacing:2px; margin-bottom:8px;'>Display Mode</div>", unsafe_allow_html=True)
        dark = st.selectbox("", ["🌑  Dark Mode (Cyber Gold)", "☀️  Light Mode (Amber)"],
                            index=0 if st.session_state.get("dark_mode", True) else 1,
                            label_visibility="collapsed")
        st.markdown(f"<div style='font-family:Orbitron,sans-serif; font-size:0.8rem; font-weight:700; color:{c['ACCENT']}; letter-spacing:2px; margin:16px 0 8px;'>Distance Unit</div>", unsafe_allow_html=True)
        unit = st.radio("", ["km", "mi"], horizontal=True,
                        index=0 if profile.get("unit","km")=="km" else 1,
                        label_visibility="collapsed")
        st.markdown(f"<div style='font-family:Orbitron,sans-serif; font-size:0.8rem; font-weight:700; color:{c['ACCENT']}; letter-spacing:2px; margin:16px 0 8px;'>Operative ID</div>", unsafe_allow_html=True)
        user_email = st.session_state.user.email if st.session_state.user else ""
        st.text_input("", value=user_email, disabled=True, label_visibility="collapsed")
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

    c = apply_theme(st.session_state.dark_mode)

    if not st.session_state.user:
        auth_page(c); return

    user_id = st.session_state.user.id
    profile = get_profile(user_id)
    runs = get_runs(user_id)
    unit = profile.get("unit", "km")
    page = st.session_state.get("page", "Dashboard")

    render_sidebar(profile, page, c)
    render_bottom_nav(page, c)

    if page == "Dashboard":     page_dashboard(user_id, profile, runs, unit, c)
    elif page == "GPS Tracker": page_gps_tracker(user_id, profile, runs, unit, c)
    elif page == "Manual Log":  page_log_run(user_id, profile, runs, unit, c)
    elif page == "History":     page_history(user_id, runs, unit, c)
    elif page == "Quests":      page_quests(user_id, profile, runs, c)
    elif page == "Stats":       page_stats(user_id, runs, unit, c)
    elif page == "Settings":    page_settings(user_id, profile, c)

if __name__ == "__main__":
    main()
