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
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", "")

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
    {"level": 1,  "title": "Wanderer",     "min_xp": 0,     "icon": "🥾"},
    {"level": 2,  "title": "Jogger",       "min_xp": 200,   "icon": "🏃"},
    {"level": 3,  "title": "Pacer",        "min_xp": 600,   "icon": "⚡"},
    {"level": 4,  "title": "Strider",      "min_xp": 1200,  "icon": "💨"},
    {"level": 5,  "title": "Racer",        "min_xp": 2200,  "icon": "🔥"},
    {"level": 6,  "title": "Sprinter",     "min_xp": 3500,  "icon": "⚔️"},
    {"level": 7,  "title": "Champion",     "min_xp": 5500,  "icon": "👑"},
    {"level": 8,  "title": "Legend",       "min_xp": 8000,  "icon": "🌟"},
    {"level": 9,  "title": "Mythic",       "min_xp": 12000, "icon": "🌌"},
    {"level": 10, "title": "Transcendent", "min_xp": 18000, "icon": "💫"},
]
QUESTS = [
    {"id": "first_run",     "title": "First Step",        "desc": "Complete your very first run",       "icon": "👟", "xp": 30},
    {"id": "run_5km",       "title": "Five Kilometers",   "desc": "Run 5km in a single session",        "icon": "🎯", "xp": 60},
    {"id": "run_10km",      "title": "Double Digits",     "desc": "Run 10km in a single session",       "icon": "🏅", "xp": 120},
    {"id": "run_3_times",   "title": "Habit Forming",     "desc": "Complete 3 runs total",              "icon": "🔄", "xp": 40},
    {"id": "run_7_times",   "title": "Weekly Warrior",    "desc": "Complete 7 runs total",              "icon": "⚔️", "xp": 100},
    {"id": "sub_6_pace",    "title": "Speed Seeker",      "desc": "Run a pace under 6:00 min/km",       "icon": "⚡", "xp": 60},
    {"id": "sub_5_pace",    "title": "Lightning Legs",    "desc": "Run a pace under 5:00 min/km",       "icon": "🌩️", "xp": 180},
    {"id": "total_50km",    "title": "Fifty & Counting",  "desc": "Accumulate 50km total",              "icon": "🗺️", "xp": 250},
    {"id": "total_100km",   "title": "Century Runner",    "desc": "Accumulate 100km total",             "icon": "💯", "xp": 500},
    {"id": "half_marathon", "title": "Half the Glory",    "desc": "Complete a half marathon (21.1km)",  "icon": "🎖️", "xp": 400},
    {"id": "full_marathon", "title": "Marathon Legend",   "desc": "Complete a full marathon (42.2km)",  "icon": "🏆", "xp": 1500},
    {"id": "run_streak_3",  "title": "On a Roll",         "desc": "Run 3 days in a row",                "icon": "🔥", "xp": 80},
    {"id": "run_streak_7",  "title": "Unstoppable",       "desc": "Run 7 days in a row",                "icon": "💥", "xp": 300},
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
    xp = int(distance_km * 5)          # 5 XP/km (was 10)
    pace = (duration_seconds / 60) / distance_km if distance_km else 999
    if pace < 4.5: xp += 25            # sub 4:30 (was sub 5:00 = 30)
    elif pace < 5: xp += 15            # sub 5:00 (was sub 6:00 = 15)
    elif pace < 6: xp += 5             # sub 6:00 (new tier)
    if distance_km >= 5:  xp += 10     # 5km bonus (was 20)
    if distance_km >= 10: xp += 20     # 10km bonus (was 40)
    if distance_km >= 21: xp += 60     # 21km bonus (was 100)
    if distance_km >= 42: xp += 150    # marathon bonus (new)
    if is_pb: xp += 25                 # PB bonus (was 50)
    return max(1, xp)

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
        min-width: 220px !important;
        max-width: 220px !important;
        width: 220px !important;
        resize: none !important;
    }}
    section[data-testid="stSidebar"] > div:first-child {{
        min-width: 220px !important;
        max-width: 220px !important;
    }}
    [data-testid="stSidebarResizeHandle"] {{
        display: none !important;
        pointer-events: none !important;
        width: 0 !important;
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

    /* Invisible rank icon buttons */
    [data-testid="stButton"] button[kind="secondary"][id*="rank_btn"] {{
        background: transparent !important;
        border: none !important;
        padding: 0 !important;
        height: 4px !important;
        min-height: 0 !important;
        opacity: 0.01 !important;
        margin-top: -8px !important;
        box-shadow: none !important;
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
    .sidebar-nav .stButton > button,
    section[data-testid="stSidebar"] .stButton > button {{
        text-align: left !important;
        justify-content: flex-start !important;
        border-radius: 0px !important;
        margin: 0 !important;
        font-family: 'Exo 2', sans-serif !important;
        font-size: 0.9rem !important;
        letter-spacing: 0.5px !important;
        font-weight: 500 !important;
        padding: 10px 14px !important;
        border: none !important;
        background: transparent !important;
        color: {TEXT2} !important;
        width: 100% !important;
        transition: all 0.15s !important;
        box-shadow: none !important;
    }}
    section[data-testid="stSidebar"] .stButton > button:hover {{
        background: {"rgba(255,179,0,0.06)" if dark_mode else "rgba(192,120,0,0.06)"} !important;
        color: {TEXT} !important;
        box-shadow: none !important;
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

        # Logo - bracket frame
        logo_bg = "#0A0C12" if c["dark_mode"] else "#FFF8EC"

        st.markdown(f"""
        <div style='padding:12px 10px 10px; background:{logo_bg}; border-bottom:2px solid {c["ACCENT"]}; position:relative;'>
            <div style='position:absolute; top:0; left:0; right:0; height:2px; background:linear-gradient(90deg, {c["ACCENT"]}, {c["ACCENT2"]}, transparent);'></div>
            <div style='border:1px solid {c["ACCENT"]}40; padding:8px 8px; position:relative; border-radius:2px;'>
                <div style='position:absolute; top:-1px; left:8px; right:8px; height:2px; background:{c["ACCENT"]};'></div>
                <div style='position:absolute; bottom:-1px; left:8px; right:8px; height:1px; background:{c["ACCENT"]}60;'></div>
                <div style='position:absolute; top:-3px; left:-3px; width:7px; height:7px; border-top:2px solid {c["ACCENT"]}; border-left:2px solid {c["ACCENT"]}; background:{logo_bg};'></div>
                <div style='position:absolute; top:-3px; right:-3px; width:7px; height:7px; border-top:2px solid {c["ACCENT"]}; border-right:2px solid {c["ACCENT"]}; background:{logo_bg};'></div>
                <div style='position:absolute; bottom:-3px; left:-3px; width:7px; height:7px; border-bottom:2px solid {c["ACCENT"]}60; border-left:2px solid {c["ACCENT"]}60; background:{logo_bg};'></div>
                <div style='position:absolute; bottom:-3px; right:-3px; width:7px; height:7px; border-bottom:2px solid {c["ACCENT"]}60; border-right:2px solid {c["ACCENT"]}60; background:{logo_bg};'></div>
                <div style='font-family:Share Tech Mono,monospace; font-size:0.45rem; color:{c["ACCENT"]}80; letter-spacing:3px; margin-bottom:5px;'>[ SYS:ACTIVE ]</div>
                <div style='font-family:Orbitron,sans-serif; font-weight:900; letter-spacing:0px; line-height:1; margin-bottom:5px; font-size:1.55rem;'>
                    <span style='color:{c["ACCENT"]};'>RUN</span><span style='color:{c["TEXT"]};'>QUEST</span>
                </div>
                <div style='font-family:Share Tech Mono,monospace; font-size:0.42rem; color:{c["TEXT3"]}; letter-spacing:3px;'>v2.0 // PERF TRACK</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Rank symbols (text-based, no SVG needed)
        RANK_SYMBOLS = ["○","△","◇","⬡","★","⬟","◉","⬠","✦","✸"]
        rank_sym = RANK_SYMBOLS[min(rank["level"]-1, 9)]

        st.markdown(f"""
        <div style='padding:14px 16px; border-bottom:1px solid {c["BORDER2"]}50;'>
            <div style='display:flex; align-items:center; gap:10px; margin-bottom:8px;'>
                <div style='width:36px; height:36px; border:2px solid {c["ACCENT"]}; border-radius:6px;
                    display:flex; align-items:center; justify-content:center; flex-shrink:0;
                    background:rgba(255,179,0,0.1);
                    font-size:1.2rem; color:{c["ACCENT"]}; font-weight:900;'>{rank_sym}</div>
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

        # Nav - icon embedded directly in button text
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
            ("Stats",       "∿"),
            ("AI Coach",    "✺"),
            ("Settings",    "⊛"),
        ]

        for name, icon in NAV_ITEMS:
            is_active = page == name
            ac = c["ACCENT"]
            t2 = c["TEXT2"]
            dm = c["dark_mode"]
            bar = ac if is_active else "transparent"
            bg = f"rgba(255,179,0,0.08)" if (is_active and dm) else f"rgba(192,120,0,0.08)" if (is_active and not dm) else "transparent"

            # Wrap button in a styled div for the left bar + background
            st.markdown(f"<div style='border-left:3px solid {bar}; background:{bg}; margin-bottom:1px;'>", unsafe_allow_html=True)
            if st.button(f"  {icon}  {name}", key=f"snav_{name}"):
                st.session_state.page = name
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)


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
def render_route_map(route, c, height=300):
    import json
    if not route:
        st.markdown(f"<div style='background:{c['CARD']};border:1.5px solid {c['BORDER2']};border-radius:8px;padding:16px;text-align:center;color:{c['TEXT3']};font-family:Share Tech Mono,monospace;font-size:0.75rem;'>[ NO ROUTE DATA ]</div>", unsafe_allow_html=True)
        return
    if isinstance(route, str):
        try: route = json.loads(route)
        except: return
    if len(route) < 2: return
    clat = sum(p["lat"] for p in route) / len(route)
    clon = sum(p["lon"] for p in route) / len(route)
    coords_js = json.dumps([[p["lat"], p["lon"]] for p in route])
    start_p = route[0]; end_p = route[-1]
    accent = c["ACCENT"]
    border = c["BORDER2"]
    osm_tile = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"

    st.components.v1.html(f"""
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <div style="width:100%;perspective:800px;border-radius:8px;overflow:hidden;">
      <div id="rmap" style="width:100%;height:{height}px;border-radius:8px;border:1.5px solid {border};transform:rotateX(20deg) scale(1.05);transform-origin:center bottom;overflow:hidden;"></div>
    </div>
    <script>
    var m=L.map('rmap',{{zoomControl:true}}).setView([{clat},{clon}],16);
    L.tileLayer('{osm_tile}',{{maxZoom:19,attribution:'© OpenStreetMap'}}).addTo(m);
    var coords={coords_js};
    var poly=L.polyline(coords,{{color:'{accent}',weight:6,opacity:0.95,lineCap:'round',lineJoin:'round'}}).addTo(m);
    var si=L.divIcon({{html:'<div style="width:14px;height:14px;border-radius:50%;background:#00C853;border:3px solid white;box-shadow:0 0 8px #00C853;"></div>',className:'',iconSize:[14,14],iconAnchor:[7,7]}});
    var ei=L.divIcon({{html:'<div style="width:14px;height:14px;border-radius:50%;background:#FF4444;border:3px solid white;box-shadow:0 0 8px #FF4444;"></div>',className:'',iconSize:[14,14],iconAnchor:[7,7]}});
    L.marker(coords[0],{{icon:si}}).addTo(m).bindPopup('<b>START</b>');
    L.marker(coords[coords.length-1],{{icon:ei}}).addTo(m).bindPopup('<b>FINISH</b>');
    m.fitBounds(poly.getBounds(),{{padding:[30,30]}});
    setTimeout(function(){{m.invalidateSize();}},200);
    setTimeout(function(){{m.invalidateSize();}},600);
    setTimeout(function(){{m.invalidateSize();m.fitBounds(poly.getBounds(),{{padding:[30,30]}});}},1200);
    </script>
    """, height=height+40, scrolling=False)

# ─── GPS COMPONENT WITH LIVE MAP ────────────────────────────────
def gps_component(unit_sel, c):
    accent = c["ACCENT"]
    card = c["CARD"]
    border2 = c["BORDER2"]
    text3 = c["TEXT3"]
    text_c = c["TEXT"]
    osm_tile = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"

    html = f"""
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&family=Share+Tech+Mono&family=Exo+2:wght@600&display=swap" rel="stylesheet">
<style>
  @keyframes pg {{0%,100%{{opacity:1;box-shadow:0 0 8px {accent}}}50%{{opacity:0.3;box-shadow:none}}}}
  @keyframes pulse {{0%,100%{{transform:scale(1)}}50%{{transform:scale(1.3)}}}}
  .live-dot {{width:16px;height:16px;border-radius:50%;background:{accent};border:3px solid white;box-shadow:0 0 12px {accent};animation:pulse 1.5s infinite;}}
</style>
<div style="font-family:'Exo 2',sans-serif;">
  <div id="wl-warn" style="display:none;background:rgba(255,179,0,0.1);border:1.5px solid {border2};border-radius:8px;padding:10px 14px;margin-bottom:10px;font-family:'Share Tech Mono',monospace;font-size:0.75rem;color:{accent};letter-spacing:1px;">⚠ KEEP SCREEN ACTIVE</div>
  <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:12px;">
    <div style="background:{card};border:1.5px solid {border2};border-radius:8px;padding:12px 6px;text-align:center;position:relative;overflow:hidden;"><div style="position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,transparent,{accent},transparent);"></div><div id="dv" style="font-family:'Orbitron',sans-serif;font-size:1.5rem;font-weight:900;color:{accent};line-height:1;">0.00</div><div style="font-family:'Share Tech Mono',monospace;font-size:0.55rem;color:{text3};letter-spacing:2px;margin-top:3px;">{unit_sel.upper()}</div></div>
    <div style="background:{card};border:1.5px solid {border2};border-radius:8px;padding:12px 6px;text-align:center;position:relative;overflow:hidden;"><div style="position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,transparent,{accent},transparent);"></div><div id="tv" style="font-family:'Orbitron',sans-serif;font-size:1.5rem;font-weight:900;color:{text_c};line-height:1;">00:00</div><div style="font-family:'Share Tech Mono',monospace;font-size:0.55rem;color:{text3};letter-spacing:2px;margin-top:3px;">TIME</div></div>
    <div style="background:{card};border:1.5px solid {border2};border-radius:8px;padding:12px 6px;text-align:center;position:relative;overflow:hidden;"><div style="position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,transparent,{accent},transparent);"></div><div id="pv" style="font-family:'Orbitron',sans-serif;font-size:1.5rem;font-weight:900;color:{text_c};line-height:1;">--:--</div><div style="font-family:'Share Tech Mono',monospace;font-size:0.55rem;color:{text3};letter-spacing:2px;margin-top:3px;">MIN/{unit_sel.upper()}</div></div>
  </div>
  <div id="st" style="text-align:center;font-family:'Share Tech Mono',monospace;font-size:0.75rem;color:{text3};letter-spacing:2px;margin-bottom:8px;">[ SYSTEM READY — PRESS INITIATE ]</div>
  <div id="ac" style="display:none;text-align:center;font-family:'Share Tech Mono',monospace;font-size:0.7rem;color:{text3};letter-spacing:1px;margin-bottom:8px;">GPS: <span id="av" style="color:{accent};">--</span>m accuracy</div>
  <div style="display:flex;gap:8px;margin-bottom:12px;">
    <button id="b-start" onclick="gs()" style="flex:1;padding:13px 6px;border-radius:6px;border:2px solid {accent};cursor:pointer;background:rgba(255,179,0,0.12);color:{accent};font-family:'Orbitron',sans-serif;font-size:0.7rem;font-weight:800;letter-spacing:2px;">▶ INITIATE</button>
    <button id="b-pause" onclick="gp()" style="flex:1;padding:13px 6px;border-radius:6px;border:2px solid #FF8C00;cursor:pointer;background:{card};color:#FF8C00;font-family:'Orbitron',sans-serif;font-size:0.7rem;font-weight:800;letter-spacing:2px;display:none;">⏸ PAUSE</button>
    <button id="b-resume" onclick="gr()" style="flex:1;padding:13px 6px;border-radius:6px;border:2px solid {accent};cursor:pointer;background:rgba(255,179,0,0.12);color:{accent};font-family:'Orbitron',sans-serif;font-size:0.7rem;font-weight:800;letter-spacing:2px;display:none;">▶ RESUME</button>
    <button id="b-stop" onclick="gst()" style="flex:1;padding:13px 6px;border-radius:6px;border:2px solid #FF5555;cursor:pointer;background:{card};color:#FF5555;font-family:'Orbitron',sans-serif;font-size:0.7rem;font-weight:800;letter-spacing:2px;display:none;">■ HALT</button>
  </div>
  <div id="map-wrap" style="display:none;margin-bottom:12px;border-radius:8px;overflow:hidden;border:1.5px solid {border2};">
    <div style="background:{card};padding:6px 12px;font-family:'Share Tech Mono',monospace;font-size:0.6rem;color:{accent};letter-spacing:2px;border-bottom:1px solid {border2};">◈ LIVE POSITION TRACKING</div>
    <div style="perspective:900px;">
      <div id="livemap" style="width:100%;height:260px;transform:rotateX(25deg) scale(1.08);transform-origin:center bottom;"></div>
    </div>
  </div>
  <input type="hidden" id="fd" value="0">
  <input type="hidden" id="ft" value="0">
  <div id="sum" style="display:none;background:{card};border:1.5px solid {border2};border-radius:8px;padding:16px;position:relative;overflow:hidden;">
    <div style="position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,transparent,{accent},transparent);"></div>
    <div style="font-family:'Orbitron',sans-serif;font-size:0.7rem;font-weight:700;color:{accent};letter-spacing:2px;margin-bottom:12px;">◈ RUN SUMMARY</div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:14px;">
      <div style="text-align:center;"><div style="font-family:'Exo 2',sans-serif;font-size:0.7rem;color:{text3};margin-bottom:4px;">DISTANCE</div><div id="sd" style="font-family:'Orbitron',sans-serif;font-size:1.2rem;font-weight:800;color:{accent};"></div></div>
      <div style="text-align:center;"><div style="font-family:'Exo 2',sans-serif;font-size:0.7rem;color:{text3};margin-bottom:4px;">DURATION</div><div id="st2" style="font-family:'Orbitron',sans-serif;font-size:1.2rem;font-weight:800;color:{text_c};"></div></div>
      <div style="text-align:center;"><div style="font-family:'Exo 2',sans-serif;font-size:0.7rem;color:{text3};margin-bottom:4px;">AVG PACE</div><div id="sp" style="font-family:'Orbitron',sans-serif;font-size:1.2rem;font-weight:800;color:{text_c};"></div></div>
      <div style="text-align:center;"><div style="font-family:'Exo 2',sans-serif;font-size:0.7rem;color:{text3};margin-bottom:4px;">STATUS</div><div style="font-family:'Orbitron',sans-serif;font-size:1.2rem;font-weight:800;color:{accent};">DONE ✓</div></div>
    </div>
    <div style="border-radius:6px;overflow:hidden;border:1px solid {border2};margin-bottom:14px;perspective:900px;">
      <div id="summap" style="width:100%;height:220px;transform:rotateX(25deg) scale(1.08);transform-origin:center bottom;"></div>
    </div>
    <div style="text-align:center;font-family:'Share Tech Mono',monospace;font-size:0.75rem;color:{accent};letter-spacing:1px;padding:10px;background:rgba(255,179,0,0.08);border-radius:6px;border:1px solid {accent}40;">↓ SCROLL DOWN TO SAVE YOUR RUN ↓</div>
  </div>
</div>
<script>
var wId=null,tI=null,lP=null,tD=0,tS=0,paused=false,wl=null,unit='{unit_sel}';
var route=[],liveMap=null,liveDot=null,livePoly=null,sumMap=null;
var OSM='{osm_tile}';
function hav(a,b,c,d){{var R=6371,dL=(c-a)*Math.PI/180,dl=(d-b)*Math.PI/180,x=Math.sin(dL/2)**2+Math.cos(a*Math.PI/180)*Math.cos(c*Math.PI/180)*Math.sin(dl/2)**2;return R*2*Math.atan2(Math.sqrt(x),Math.sqrt(1-x));}}
function ft(s){{var h=Math.floor(s/3600),m=Math.floor((s%3600)/60),x=s%60;return h>0?h+':'+String(m).padStart(2,'0')+':'+String(x).padStart(2,'0'):String(m).padStart(2,'0')+':'+String(x).padStart(2,'0');}}
function fp(s,d){{if(d<0.001)return'--:--';var p=(s/60)/d;if(unit==='mi')p/=1.60934;var m=Math.floor(p),x=Math.round((p-m)*60);return m+':'+String(x).padStart(2,'0');}}
function fd2(k){{return unit==='mi'?(k*0.621371).toFixed(2):k.toFixed(2);}}
function setStatus(h){{document.getElementById('st').innerHTML=h;}}
async function rwl(){{try{{if('wakeLock'in navigator)wl=await navigator.wakeLock.request('screen');}}catch(e){{document.getElementById('wl-warn').style.display='block';}}}}

function initLiveMap(lat,lon){{
    document.getElementById('map-wrap').style.display='block';
    if(liveMap){{liveMap.remove();liveMap=null;}}
    liveMap=L.map('livemap',{{zoomControl:false,attributionControl:false}}).setView([lat,lon],17);
    L.tileLayer(OSM,{{maxZoom:19}}).addTo(liveMap);
    var si=L.divIcon({{html:'<div style="width:12px;height:12px;border-radius:50%;background:#00C853;border:2px solid white;box-shadow:0 0 6px #00C853;"></div>',className:'',iconSize:[12,12],iconAnchor:[6,6]}});
    L.marker([lat,lon],{{icon:si}}).addTo(liveMap);
    var di=L.divIcon({{html:'<div class="live-dot"></div>',className:'',iconSize:[16,16],iconAnchor:[8,8]}});
    liveDot=L.marker([lat,lon],{{icon:di,zIndexOffset:1000}}).addTo(liveMap);
    livePoly=L.polyline([[lat,lon]],{{color:'{accent}',weight:6,opacity:0.95,lineCap:'round',lineJoin:'round'}}).addTo(liveMap);
    setTimeout(function(){{liveMap.invalidateSize();}},300);
    setTimeout(function(){{liveMap.invalidateSize();}},800);
    setTimeout(function(){{liveMap.invalidateSize();}},1500);
}}
function updateLiveMap(lat,lon){{
    if(!liveMap)return;
    liveDot.setLatLng([lat,lon]);
    livePoly.addLatLng([lat,lon]);
    liveMap.panTo([lat,lon],{{animate:true,duration:1}});
}}
function initSumMap(){{
    if(route.length<2)return;
    setTimeout(function(){{
        if(sumMap){{sumMap.remove();sumMap=null;}}
        var clat=route.reduce((s,p)=>s+p.lat,0)/route.length;
        var clon=route.reduce((s,p)=>s+p.lon,0)/route.length;
        sumMap=L.map('summap',{{zoomControl:false,attributionControl:false}}).setView([clat,clon],15);
        L.tileLayer(OSM,{{maxZoom:19}}).addTo(sumMap);
        var coords=route.map(p=>[p.lat,p.lon]);
        var poly=L.polyline(coords,{{color:'{accent}',weight:6,opacity:0.95,lineCap:'round',lineJoin:'round'}}).addTo(sumMap);
        var si=L.divIcon({{html:'<div style="width:12px;height:12px;border-radius:50%;background:#00C853;border:2px solid white;"></div>',className:'',iconSize:[12,12],iconAnchor:[6,6]}});
        var ei=L.divIcon({{html:'<div style="width:12px;height:12px;border-radius:50%;background:#FF4444;border:2px solid white;"></div>',className:'',iconSize:[12,12],iconAnchor:[6,6]}});
        L.marker(coords[0],{{icon:si}}).addTo(sumMap);
        L.marker(coords[coords.length-1],{{icon:ei}}).addTo(sumMap);
        sumMap.fitBounds(poly.getBounds(),{{padding:[20,20]}});
        setTimeout(function(){{sumMap.invalidateSize();}},300);
        setTimeout(function(){{sumMap.invalidateSize();}},800);
        setTimeout(function(){{sumMap.invalidateSize();}},1500);
    }},500);
}}
function gs(){{
    if(!navigator.geolocation){{setStatus('<span style="color:#FF5555;">❌ GPS NOT AVAILABLE</span>');return;}}
    tD=0;tS=0;lP=null;paused=false;route=[];
    if(liveMap){{liveMap.remove();liveMap=null;}}liveDot=null;livePoly=null;
    document.getElementById('b-start').style.display='none';
    document.getElementById('b-pause').style.display='flex';
    document.getElementById('b-stop').style.display='flex';
    document.getElementById('sum').style.display='none';
    document.getElementById('ac').style.display='block';
    document.getElementById('dv').textContent='0.00';
    document.getElementById('tv').textContent='00:00';
    document.getElementById('pv').textContent='--:--';
    setStatus('<span style="color:{accent};font-family:Share Tech Mono,monospace;font-size:0.75rem;letter-spacing:2px;">● TRACKING ACTIVE</span>');
    rwl();
    tI=setInterval(function(){{if(!paused){{tS++;document.getElementById('tv').textContent=ft(tS);document.getElementById('pv').textContent=fp(tS,tD);}}}},1000);
    wId=navigator.geolocation.watchPosition(
        function(pos){{
            var lat=pos.coords.latitude,lon=pos.coords.longitude,ac=Math.round(pos.coords.accuracy);
            var av=document.getElementById('av');av.textContent=ac;
            av.style.color=ac<15?'{accent}':ac<30?'#FF8C00':'#FF5555';
            if(!paused){{
                if(!liveMap){{initLiveMap(lat,lon);}}
                if(lP){{var d=hav(lP.lat,lP.lon,lat,lon);if(d<0.5&&d>0.0005){{tD+=d;document.getElementById('dv').textContent=fd2(tD);}}}}
                route.push({{lat:lat,lon:lon}});
                updateLiveMap(lat,lon);
                lP={{lat:lat,lon:lon}};
            }}
        }},
        function(e){{setStatus('<span style="color:#FF5555;font-family:Share Tech Mono,monospace;font-size:0.7rem;">⚠ GPS: '+e.message+'</span>');}},
        {{enableHighAccuracy:true,maximumAge:0,timeout:10000}}
    );
}}
function gp(){{paused=true;document.getElementById('b-pause').style.display='none';document.getElementById('b-resume').style.display='flex';setStatus('<span style="color:#FF8C00;font-family:Share Tech Mono,monospace;font-size:0.75rem;letter-spacing:2px;">⏸ PAUSED</span>');}}
function gr(){{paused=false;lP=null;document.getElementById('b-resume').style.display='none';document.getElementById('b-pause').style.display='flex';setStatus('<span style="color:{accent};font-family:Share Tech Mono,monospace;font-size:0.75rem;letter-spacing:2px;">● TRACKING ACTIVE</span>');}}
function gst(){{
    paused=false;clearInterval(tI);
    if(wId!==null){{navigator.geolocation.clearWatch(wId);wId=null;}}
    if(wl){{try{{wl.release();}}catch(e){{}}}}
    document.getElementById('b-pause').style.display='none';
    document.getElementById('b-resume').style.display='none';
    document.getElementById('b-stop').style.display='none';
    document.getElementById('b-start').style.display='flex';
    document.getElementById('ac').style.display='none';
    document.getElementById('map-wrap').style.display='none';
    document.getElementById('sd').textContent=fd2(tD)+' '+unit;
    document.getElementById('st2').textContent=ft(tS);
    document.getElementById('sp').textContent=fp(tS,tD)+'/'+unit;
    document.getElementById('fd').value=tD.toFixed(4);
    document.getElementById('ft').value=tS;
    document.getElementById('sum').style.display='block';
    setStatus('<span style="color:{accent};font-family:Share Tech Mono,monospace;font-size:0.7rem;letter-spacing:1px;">[ SCROLL DOWN TO SAVE ]</span>');
    initSumMap();
}}
</script>
"""
    st.components.v1.html(html, height=700, scrolling=True)



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

def quest_svg_icon(quest_id, accent, border):
    SVGS = {
        "first_run":    f'<svg width="22" height="22" viewBox="0 0 22 22" fill="none"><circle cx="11" cy="11" r="9" stroke="{accent}" stroke-width="1.5" fill="rgba(255,179,0,0.12)"/><circle cx="11" cy="11" r="4" fill="{accent}"/></svg>',
        "run_5km":      f'<svg width="22" height="22" viewBox="0 0 22 22" fill="none"><polygon points="11,1 13,7.5 20,7.5 14.5,11.5 16.5,18 11,14 5.5,18 7.5,11.5 2,7.5 9,7.5" stroke="{accent}" stroke-width="1.5" fill="rgba(255,179,0,0.12)"/></svg>',
        "run_10km":     f'<svg width="22" height="22" viewBox="0 0 22 22" fill="none"><polygon points="11,1 13,7.5 20,7.5 14.5,11.5 16.5,18 11,14 5.5,18 7.5,11.5 2,7.5 9,7.5" stroke="{accent}" stroke-width="1.5" fill="rgba(255,179,0,0.12)"/><circle cx="11" cy="10" r="2.5" fill="{accent}"/></svg>',
        "run_3_times":  f'<svg width="22" height="22" viewBox="0 0 22 22" fill="none"><rect x="2" y="2" width="18" height="18" rx="3" stroke="{accent}" stroke-width="1.5" fill="rgba(255,179,0,0.08)"/><line x1="2" y1="9" x2="20" y2="9" stroke="{accent}" stroke-width="1"/><line x1="2" y1="13" x2="20" y2="13" stroke="{accent}" stroke-width="1"/><circle cx="7" cy="11" r="1.5" fill="{accent}"/><circle cx="11" cy="11" r="1.5" fill="{accent}"/><circle cx="15" cy="11" r="1.5" fill="{accent}"/></svg>',
        "run_7_times":  f'<svg width="22" height="22" viewBox="0 0 22 22" fill="none"><rect x="2" y="2" width="18" height="18" rx="3" stroke="{accent}" stroke-width="1.5" fill="rgba(255,179,0,0.08)"/><line x1="2" y1="8" x2="20" y2="8" stroke="{accent}" stroke-width="1"/><line x1="2" y1="14" x2="20" y2="14" stroke="{accent}" stroke-width="1"/><circle cx="5" cy="11" r="1.5" fill="{accent}"/><circle cx="8" cy="11" r="1.5" fill="{accent}"/><circle cx="11" cy="11" r="1.5" fill="{accent}"/><circle cx="14" cy="11" r="1.5" fill="{accent}"/><circle cx="17" cy="11" r="1.5" fill="{accent}"/></svg>',
        "sub_6_pace":   f'<svg width="22" height="22" viewBox="0 0 22 22" fill="none"><polygon points="11,2 20,7 20,15 11,20 2,15 2,7" stroke="{accent}" stroke-width="1.5" fill="rgba(255,179,0,0.08)"/><polyline points="6,13 9,10 12,12 16,7" stroke="{accent}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
        "sub_5_pace":   f'<svg width="22" height="22" viewBox="0 0 22 22" fill="none"><polygon points="11,2 20,7 20,15 11,20 2,15 2,7" stroke="{accent}" stroke-width="1.5" fill="rgba(255,179,0,0.08)"/><polyline points="5,14 8,10 11,12 16,6" stroke="{accent}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
        "total_50km":   f'<svg width="22" height="22" viewBox="0 0 22 22" fill="none"><path d="M11 2 L20 7 L20 15 L11 20 L2 15 L2 7 Z" stroke="{accent}" stroke-width="1.5" fill="rgba(255,179,0,0.08)"/><path d="M11 6 L16 9 L16 13 L11 16 L6 13 L6 9 Z" fill="{accent}"/></svg>',
        "total_100km":  f'<svg width="22" height="22" viewBox="0 0 22 22" fill="none"><circle cx="11" cy="11" r="9" stroke="{accent}" stroke-width="1.5" fill="none"/><circle cx="11" cy="11" r="6" stroke="{accent}" stroke-width="1" fill="rgba(255,179,0,0.08)"/><circle cx="11" cy="11" r="3" fill="{accent}"/></svg>',
        "half_marathon":f'<svg width="22" height="22" viewBox="0 0 22 22" fill="none"><path d="M11 2 L20 8 L17 19 L5 19 L2 8 Z" stroke="{accent}" stroke-width="1.5" fill="rgba(255,179,0,0.08)"/><path d="M11 6 L16 10 L14 17 L8 17 L6 10 Z" fill="{accent}"/></svg>',
        "full_marathon":f'<svg width="22" height="22" viewBox="0 0 22 22" fill="none"><polygon points="11,1 13.5,8 21,8 15,13 17.5,20 11,16 4.5,20 7,13 1,8 8.5,8" stroke="{accent}" stroke-width="1.5" fill="rgba(255,179,0,0.12)"/><polygon points="11,5 12.5,9.5 17,9.5 13.5,12 15,16.5 11,14 7,16.5 8.5,12 5,9.5 9.5,9.5" fill="{accent}"/></svg>',
        "run_streak_3": f'<svg width="22" height="22" viewBox="0 0 22 22" fill="none"><path d="M11 2 L20 6 L20 16 L11 20 L2 16 L2 6 Z" stroke="{accent}" stroke-width="1.5" fill="rgba(255,179,0,0.08)"/><line x1="7" y1="11" x2="15" y2="11" stroke="{accent}" stroke-width="1.5"/><line x1="11" y1="7" x2="11" y2="15" stroke="{accent}" stroke-width="1.5"/></svg>',
        "run_streak_7": f'<svg width="22" height="22" viewBox="0 0 22 22" fill="none"><path d="M11 2 L20 6 L20 16 L11 20 L2 16 L2 6 Z" stroke="{accent}" stroke-width="1.5" fill="rgba(255,179,0,0.08)"/><line x1="6" y1="11" x2="16" y2="11" stroke="{accent}" stroke-width="1.5"/><line x1="11" y1="6" x2="11" y2="16" stroke="{accent}" stroke-width="1.5"/><line x1="7.5" y1="7.5" x2="14.5" y2="14.5" stroke="{accent}" stroke-width="1"/><line x1="14.5" y1="7.5" x2="7.5" y2="14.5" stroke="{accent}" stroke-width="1"/></svg>',
    }
    return SVGS.get(quest_id, SVGS["first_run"])


def page_dashboard(user_id, profile, runs, unit, c):
    xp = profile.get("xp", 0)
    rank = get_rank(xp); next_rank = get_next_rank(xp); progress = get_xp_progress(xp)
    st.markdown("<div class='page-title'>◈ COMMAND CENTER</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='page-sub'>OPERATIVE: {st.session_state.user.email.split('@')[0].upper()}</div>", unsafe_allow_html=True)

    ac = c["ACCENT"]
    RANK_SYMBOLS_DASH = ["○","△","◇","⬡","★","⬟","◉","⬠","✦","✸"]
    dash_rank_sym = RANK_SYMBOLS_DASH[min(rank["level"]-1, 9)]

    st.markdown(f"""
    <div class='cyber-card'>
      <div style='display:flex; align-items:center; gap:14px; flex-wrap:wrap;'>
        <div style='font-size:2.8rem; line-height:1;'>{dash_rank_sym}</div>
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
            svg_icon = quest_svg_icon(q["id"], c["ACCENT"], c["BORDER2"])
            st.markdown(f"""
            <div class='quest-card'>
              <div style='display:flex; align-items:center; gap:10px;'>
                <div style='width:38px; height:38px; border:1.5px solid {c["ACCENT"]}60;
                    border-radius:8px; display:flex; align-items:center; justify-content:center;
                    flex-shrink:0; background:rgba(255,179,0,0.08);'>{svg_icon}</div>
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
    st.markdown("<div class='page-title'>◈ GPS UPLINK</div>", unsafe_allow_html=True)
    st.markdown("<div class='page-sub'>REAL-TIME POSITION & ROUTE TRACKING</div>", unsafe_allow_html=True)

    # Show save result
    if "last_run_saved" in st.session_state:
        r = st.session_state.pop("last_run_saved")
        st.success(f"✅ Run saved! {format_distance(r['dist'], r['unit'])} {r['unit']} in {format_time(r['dur'])}")
        if r["is_pb"]:
            st.balloons()
            st.success("🏅 New Personal Record!")
        st.info(f"⭐ +{r['xp']} XP earned!")
        for q in r["fresh"]:
            st.success(f"🎯 Quest: {q['icon']} {q['title']} (+{q['xp']} XP)")

    st.warning("⚠ Keep this tab open and screen ON while running!")
    unit_sel = st.radio("Unit System", ["km", "mi"], horizontal=True,
                        index=0 if unit == "km" else 1)
    gps_component(unit_sel, c)

    # ── SAVE FORM ── shown always, user fills from GPS display above
    st.markdown("<hr class='divider'>", unsafe_allow_html=True)
    st.markdown(f"<div style='font-family:Orbitron,sans-serif; font-size:0.8rem; font-weight:700; color:{c['ACCENT']}; letter-spacing:2px; margin-bottom:4px;'>◈ SAVE RUN</div>", unsafe_allow_html=True)
    st.markdown(f"<div style='font-family:Exo 2,sans-serif; font-size:0.85rem; color:{c['TEXT2']}; margin-bottom:12px;'>After pressing <b>HALT</b>, enter the distance and time shown above then tap Save.</div>", unsafe_allow_html=True)

    with st.form("gps_save_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            dist_in = st.number_input("Distance", min_value=0.001, max_value=300.0, step=0.001, value=0.100, format="%.3f")
        with col2:
            unit_in = st.selectbox("Unit", ["km","mi"], index=0 if unit_sel=="km" else 1)
        c1,c2,c3 = st.columns(3)
        with c1: hh = st.number_input("HH", 0, 24, 0)
        with c2: mm = st.number_input("MM", 0, 59, 0)
        with c3: ss = st.number_input("SS", 0, 59, 0)
        if st.form_submit_button("◈  SAVE RUN TO HISTORY", use_container_width=True):
            dist_km = dist_in if unit_in=="km" else dist_in/0.621371
            total_s = hh*3600 + mm*60 + ss
            if total_s == 0:
                st.error("Enter a valid duration.")
            else:
                txp, is_pb, fresh = process_and_save_run(user_id, profile, runs, dist_km, total_s, unit_in, [])
                st.session_state["last_run_saved"] = {
                    "dist": dist_km, "dur": total_s, "xp": txp,
                    "is_pb": is_pb, "fresh": fresh, "unit": unit_in
                }
                st.rerun()

    st.caption("💡 Go outside · Wait for GPS accuracy <15m · Keep screen on while running")


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

    st.markdown(f"<div style='font-family:Orbitron,sans-serif; font-size:0.82rem; font-weight:700; color:{c['ACCENT']}; letter-spacing:2px; margin-bottom:8px;'>◈ RANK LADDER</div>", unsafe_allow_html=True)

    RANK_SVGS = [
        '<svg width="26" height="26" viewBox="0 0 26 26"><circle cx="13" cy="13" r="10" stroke="CLRX" stroke-width="1.5" fill="FILX"/><circle cx="13" cy="13" r="4" fill="CLRX"/></svg>',
        '<svg width="26" height="26" viewBox="0 0 26 26"><polygon points="13,2 24,22 2,22" stroke="CLRX" stroke-width="1.5" fill="FILX"/><polygon points="13,9 18,19 8,19" fill="CLRX"/></svg>',
        '<svg width="26" height="26" viewBox="0 0 26 26"><rect x="5" y="5" width="16" height="16" stroke="CLRX" stroke-width="1.5" fill="FILX" transform="rotate(45 13 13)"/><rect x="9" y="9" width="8" height="8" fill="CLRX" transform="rotate(45 13 13)"/></svg>',
        '<svg width="26" height="26" viewBox="0 0 26 26"><polygon points="13,2 20,7 23,15 18,23 8,23 3,15 6,7" stroke="CLRX" stroke-width="1.5" fill="FILX"/><circle cx="13" cy="13" r="3" fill="CLRX"/></svg>',
        '<svg width="26" height="26" viewBox="0 0 26 26"><polygon points="13,1 15.5,9.5 24,9.5 17.5,14.5 20,23 13,18 6,23 8.5,14.5 2,9.5 10.5,9.5" stroke="CLRX" stroke-width="1.5" fill="FILX"/></svg>',
        '<svg width="26" height="26" viewBox="0 0 26 26"><path d="M13 2 L22 6 L22 16 L13 24 L4 16 L4 6 Z" stroke="CLRX" stroke-width="1.5" fill="FILX"/><path d="M13 7 L18 10 L18 15 L13 20 L8 15 L8 10 Z" fill="CLRX"/></svg>',
        '<svg width="26" height="26" viewBox="0 0 26 26"><circle cx="13" cy="13" r="11" stroke="CLRX" stroke-width="1.5" fill="none"/><circle cx="13" cy="13" r="7" stroke="CLRX" stroke-width="1" fill="FILX"/><circle cx="13" cy="13" r="3" fill="CLRX"/></svg>',
        '<svg width="26" height="26" viewBox="0 0 26 26"><path d="M13 2 L24 9 L20 22 L6 22 L2 9 Z" stroke="CLRX" stroke-width="1.5" fill="FILX"/><path d="M13 7 L18 11 L16 18 L10 18 L8 11 Z" fill="CLRX"/></svg>',
        '<svg width="26" height="26" viewBox="0 0 26 26"><polygon points="13,1 14.8,8.5 22,7 16.5,12 22,17 14.8,15.5 13,23 11.2,15.5 4,17 9.5,12 4,7 11.2,8.5" stroke="CLRX" stroke-width="1.2" fill="FILX"/><circle cx="13" cy="12" r="3" fill="CLRX"/></svg>',
        '<svg width="26" height="26" viewBox="0 0 26 26"><circle cx="13" cy="13" r="9" stroke="CLRX" stroke-width="1.5" fill="FILX"/><circle cx="13" cy="13" r="4" fill="CLRX"/><line x1="13" y1="1" x2="13" y2="4" stroke="CLRX" stroke-width="1.5"/><line x1="13" y1="22" x2="13" y2="25" stroke="CLRX" stroke-width="1.5"/><line x1="1" y1="13" x2="4" y2="13" stroke="CLRX" stroke-width="1.5"/><line x1="22" y1="13" x2="25" y2="13" stroke="CLRX" stroke-width="1.5"/><line x1="4.5" y1="4.5" x2="6.6" y2="6.6" stroke="CLRX" stroke-width="1.5"/><line x1="19.4" y1="19.4" x2="21.5" y2="21.5" stroke="CLRX" stroke-width="1.5"/><line x1="21.5" y1="4.5" x2="19.4" y2="6.6" stroke="CLRX" stroke-width="1.5"/><line x1="6.6" y1="19.4" x2="4.5" y2="21.5" stroke="CLRX" stroke-width="1.5"/></svg>',
    ]

    if "selected_rank" not in st.session_state:
        st.session_state.selected_rank = None

    cols = st.columns(10)
    for i, r in enumerate(RANKS):
        is_cur = r["level"] == rank["level"]
        unlocked = xp >= r["min_xp"]
        is_selected = st.session_state.selected_rank == i
        with cols[i]:
            clr = c["ACCENT"] if (is_cur or is_selected) else (c["TEXT3"] if unlocked else c["TEXT3"])
            fil = "rgba(255,179,0,0.15)" if (is_cur or is_selected) else ("rgba(255,179,0,0.05)" if unlocked else "rgba(90,74,42,0.05)")
            op = "1" if unlocked else "0.2"
            border = f"2px solid {c['ACCENT']}" if (is_cur or is_selected) else f"1px solid {c['BORDER2'] if unlocked else c['BORDER2']+'40'}"
            svg = RANK_SVGS[i].replace("CLRX", clr).replace("FILX", fil)
            now = f"<div style='font-size:8px;color:{c['ACCENT']};font-family:monospace;'>▲</div>" if is_cur else ""
            st.markdown(f"<div style='text-align:center;padding:6px 2px 4px;border-radius:6px;border:{border};opacity:{op};{'background:rgba(255,179,0,0.1);' if (is_cur or is_selected) else ''}'>{svg}{now}</div>", unsafe_allow_html=True)
            if st.button("", key=f"rank_btn_{i}", help=r["title"]):
                st.session_state.selected_rank = i if st.session_state.selected_rank != i else None
                st.rerun()

    # Show selected rank info
    if st.session_state.selected_rank is not None:
        sr = RANKS[st.session_state.selected_rank]
        unlocked_sr = xp >= sr["min_xp"]
        is_cur_sr = sr["level"] == rank["level"]
        status_text = "◈ CURRENT RANK" if is_cur_sr else ("✅ UNLOCKED" if unlocked_sr else f"🔒 LOCKED — Need {sr['min_xp']} XP")
        border_col = c["ACCENT"] if is_cur_sr else c["BORDER2"]
        st.markdown(f"""
        <div style='background:{c["CARD"]};border:1.5px solid {border_col};border-radius:8px;padding:14px 16px;margin-top:8px;position:relative;overflow:hidden;'>
        <div style='position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,{c["ACCENT"]},transparent);'></div>
        <div style='font-family:Orbitron,sans-serif;font-size:1.1rem;font-weight:900;color:{c["ACCENT"]};letter-spacing:3px;margin-bottom:4px;'>{sr["title"].upper()}</div>
        <div style='font-family:Share Tech Mono,monospace;font-size:0.65rem;color:{c["TEXT3"]};letter-spacing:1px;'>LEVEL {sr["level"]} · {sr["min_xp"]:,} XP · {status_text}</div>
        </div>
        """, unsafe_allow_html=True)

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
    # SVG icons per quest - unique geometric shapes matching rank style
    QUEST_SVGS = {
        "first_run":    '<svg width="22" height="22" viewBox="0 0 22 22" fill="none"><circle cx="11" cy="11" r="9" stroke="CLRX" stroke-width="1.5" fill="FILX"/><circle cx="11" cy="11" r="4" fill="CLRX"/></svg>',
        "run_5km":      '<svg width="22" height="22" viewBox="0 0 22 22" fill="none"><polygon points="11,1 13,7.5 20,7.5 14.5,11.5 16.5,18 11,14 5.5,18 7.5,11.5 2,7.5 9,7.5" stroke="CLRX" stroke-width="1.5" fill="FILX"/></svg>',
        "run_10km":     '<svg width="22" height="22" viewBox="0 0 22 22" fill="none"><polygon points="11,1 13,7.5 20,7.5 14.5,11.5 16.5,18 11,14 5.5,18 7.5,11.5 2,7.5 9,7.5" stroke="CLRX" stroke-width="1.5" fill="FILX"/><circle cx="11" cy="10" r="2.5" fill="CLRX"/></svg>',
        "run_3_times":  '<svg width="22" height="22" viewBox="0 0 22 22" fill="none"><rect x="2" y="2" width="18" height="18" rx="3" stroke="CLRX" stroke-width="1.5" fill="FILX"/><line x1="2" y1="9" x2="20" y2="9" stroke="CLRX" stroke-width="1"/><line x1="2" y1="13" x2="20" y2="13" stroke="CLRX" stroke-width="1"/><circle cx="7" cy="11" r="1.5" fill="CLRX"/><circle cx="11" cy="11" r="1.5" fill="CLRX"/><circle cx="15" cy="11" r="1.5" fill="CLRX"/></svg>',
        "run_7_times":  '<svg width="22" height="22" viewBox="0 0 22 22" fill="none"><rect x="2" y="2" width="18" height="18" rx="3" stroke="CLRX" stroke-width="1.5" fill="FILX"/><line x1="2" y1="8" x2="20" y2="8" stroke="CLRX" stroke-width="1"/><line x1="2" y1="14" x2="20" y2="14" stroke="CLRX" stroke-width="1"/><circle cx="6" cy="11" r="1.5" fill="CLRX"/><circle cx="9" cy="11" r="1.5" fill="CLRX"/><circle cx="12" cy="11" r="1.5" fill="CLRX"/><circle cx="15" cy="11" r="1.5" fill="CLRX"/></svg>',
        "sub_6_pace":   '<svg width="22" height="22" viewBox="0 0 22 22" fill="none"><polygon points="11,2 20,7 20,15 11,20 2,15 2,7" stroke="CLRX" stroke-width="1.5" fill="FILX"/><polyline points="6,13 9,10 12,12 16,7" stroke="CLRX" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
        "sub_5_pace":   '<svg width="22" height="22" viewBox="0 0 22 22" fill="none"><polygon points="11,2 20,7 20,15 11,20 2,15 2,7" stroke="CLRX" stroke-width="1.5" fill="FILX"/><polyline points="5,14 8,10 11,12 16,6" stroke="CLRX" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
        "total_50km":   '<svg width="22" height="22" viewBox="0 0 22 22" fill="none"><path d="M11 2 L20 7 L20 15 L11 20 L2 15 L2 7 Z" stroke="CLRX" stroke-width="1.5" fill="FILX"/><path d="M11 6 L16 9 L16 13 L11 16 L6 13 L6 9 Z" fill="CLRX"/></svg>',
        "total_100km":  '<svg width="22" height="22" viewBox="0 0 22 22" fill="none"><circle cx="11" cy="11" r="9" stroke="CLRX" stroke-width="1.5" fill="none"/><circle cx="11" cy="11" r="6" stroke="CLRX" stroke-width="1" fill="FILX"/><circle cx="11" cy="11" r="3" fill="CLRX"/></svg>',
        "half_marathon":'<svg width="22" height="22" viewBox="0 0 22 22" fill="none"><path d="M11 2 L20 8 L17 19 L5 19 L2 8 Z" stroke="CLRX" stroke-width="1.5" fill="FILX"/><path d="M11 6 L16 10 L14 17 L8 17 L6 10 Z" fill="CLRX"/></svg>',
        "full_marathon": '<svg width="22" height="22" viewBox="0 0 22 22" fill="none"><polygon points="11,1 13.5,8 21,8 15,13 17.5,20 11,16 4.5,20 7,13 1,8 8.5,8" stroke="CLRX" stroke-width="1.5" fill="FILX"/><polygon points="11,5 12.5,9.5 17,9.5 13.5,12 15,16.5 11,14 7,16.5 8.5,12 5,9.5 9.5,9.5" fill="CLRX"/></svg>',
        "run_streak_3": '<svg width="22" height="22" viewBox="0 0 22 22" fill="none"><path d="M11 2 L20 6 L20 16 L11 20 L2 16 L2 6 Z" stroke="CLRX" stroke-width="1.5" fill="FILX"/><line x1="7" y1="11" x2="15" y2="11" stroke="CLRX" stroke-width="1.5"/><line x1="11" y1="7" x2="11" y2="15" stroke="CLRX" stroke-width="1.5"/></svg>',
        "run_streak_7": '<svg width="22" height="22" viewBox="0 0 22 22" fill="none"><path d="M11 2 L20 6 L20 16 L11 20 L2 16 L2 6 Z" stroke="CLRX" stroke-width="1.5" fill="FILX"/><line x1="6" y1="11" x2="16" y2="11" stroke="CLRX" stroke-width="1.5"/><line x1="11" y1="6" x2="11" y2="16" stroke="CLRX" stroke-width="1.5"/><line x1="7.5" y1="7.5" x2="14.5" y2="14.5" stroke="CLRX" stroke-width="1"/><line x1="14.5" y1="7.5" x2="7.5" y2="14.5" stroke="CLRX" stroke-width="1"/></svg>',
    }

    def quest_svg(quest_id, active=True):
        clr = c["ACCENT"] if active else "#00C853"
        brd = c["BORDER2"]
        return quest_svg_icon(quest_id, clr, brd)

    if pending:
        st.markdown(f"<div style='font-family:Orbitron,sans-serif; font-size:0.82rem; font-weight:700; color:{c['ACCENT']}; letter-spacing:2px; margin-bottom:10px;'>◈ ACTIVE QUESTS ({len(pending)})</div>", unsafe_allow_html=True)
        for q in pending:
            svg_icon = quest_svg(q["id"], active=True)
            st.markdown(f"""
            <div class='quest-card'>
              <div style='display:flex; align-items:center; gap:12px;'>
                <div style='width:40px; height:40px; border:1.5px solid {c["ACCENT"]}60;
                    border-radius:8px; display:flex; align-items:center; justify-content:center;
                    flex-shrink:0; background:rgba(255,179,0,0.08);'>
                    {svg_icon}
                </div>
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
                svg_icon = quest_svg(q["id"], active=False)
                st.markdown(f"""
                <div class='quest-done'>
                  <div style='display:flex; align-items:center; gap:10px;'>
                    <div style='width:34px; height:34px; border:1.5px solid #00C85360;
                        border-radius:6px; display:flex; align-items:center; justify-content:center;
                        flex-shrink:0; background:rgba(0,200,83,0.08);'>
                        {svg_icon}
                    </div>
                    <div style='flex:1;'>
                      <div style='font-family:Exo 2,sans-serif; font-size:0.9rem; font-weight:700; color:{c["TEXT"]};'>{q['title']}</div>
                      <div style='font-family:Exo 2,sans-serif; font-size:0.8rem; color:#00C853; margin-top:2px;'>+{q['xp']} XP earned</div>
                    </div>
                    <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><polyline points="2,8 6,12 14,4" stroke="#00C853" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
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
    t1,t2,t3 = st.tabs([
        "◈ Pace Trend",
        f"◈ Distance ({unit_sel})",
        "◈ XP Earned"
    ])
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
    import datetime
    st.markdown("<div class='page-title'>◈ SYSTEM CONFIG</div>", unsafe_allow_html=True)
    st.markdown("<div class='page-sub'>PERSONALIZE YOUR RUNQUEST EXPERIENCE</div>", unsafe_allow_html=True)

    # ── SECTION: DISPLAY ──────────────────────────────────────────
    st.markdown(f"""
    <div style='background:{c["CARD"]};border:1.5px solid {c["BORDER2"]};border-radius:10px;
        padding:18px;margin-bottom:16px;position:relative;overflow:hidden;'>
        <div style='position:absolute;top:0;left:0;right:0;height:2px;
            background:linear-gradient(90deg,{c["ACCENT"]},transparent);'></div>
        <div style='font-family:Orbitron,sans-serif;font-size:0.78rem;font-weight:700;
            color:{c["ACCENT"]};letter-spacing:3px;margin-bottom:14px;'>◈ DISPLAY</div>
    </div>""", unsafe_allow_html=True)

    with st.form("display_form"):
        dark = st.selectbox("Theme", ["🌑  Dark Mode (Cyber Gold)", "☀️  Light Mode (Amber)"],
                            index=0 if st.session_state.get("dark_mode", True) else 1)
        unit = st.radio("Distance Unit", ["km", "mi"], horizontal=True,
                        index=0 if profile.get("unit","km")=="km" else 1)
        if st.form_submit_button("◈ SAVE DISPLAY SETTINGS", use_container_width=True):
            st.session_state.dark_mode = "Dark" in dark
            update_profile(user_id, profile.get("xp",0), profile.get("completed_quests",[]), unit)
            st.success("✅ Display settings saved!")
            st.rerun()

    # ── SECTION: PROFILE ──────────────────────────────────────────
    st.markdown(f"""
    <div style='background:{c["CARD"]};border:1.5px solid {c["BORDER2"]};border-radius:10px;
        padding:18px;margin-bottom:16px;position:relative;overflow:hidden;'>
        <div style='position:absolute;top:0;left:0;right:0;height:2px;
            background:linear-gradient(90deg,{c["ACCENT"]},transparent);'></div>
        <div style='font-family:Orbitron,sans-serif;font-size:0.78rem;font-weight:700;
            color:{c["ACCENT"]};letter-spacing:3px;margin-bottom:14px;'>◈ OPERATIVE PROFILE</div>
    </div>""", unsafe_allow_html=True)

    xp = profile.get("xp", 0)
    rank = get_rank(xp)
    total_runs = len(get_runs(user_id))
    joined = "—"
    try:
        joined = st.session_state.user.created_at[:10]
    except: pass
    user_email = st.session_state.user.email if st.session_state.user else ""

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div style='background:{c["BG"]};border:1.5px solid {c["BORDER2"]};border-radius:8px;padding:14px;margin-bottom:10px;'>
            <div style='font-family:Share Tech Mono,monospace;font-size:0.55rem;color:{c["TEXT3"]};letter-spacing:2px;margin-bottom:4px;'>OPERATIVE ID</div>
            <div style='font-family:Exo 2,sans-serif;font-size:0.85rem;font-weight:600;color:{c["TEXT2"]};word-break:break-all;'>{user_email}</div>
        </div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div style='background:{c["BG"]};border:1.5px solid {c["BORDER2"]};border-radius:8px;padding:14px;margin-bottom:10px;'>
            <div style='font-family:Share Tech Mono,monospace;font-size:0.55rem;color:{c["TEXT3"]};letter-spacing:2px;margin-bottom:4px;'>CURRENT RANK</div>
            <div style='font-family:Orbitron,sans-serif;font-size:0.85rem;font-weight:700;color:{c["ACCENT"]};'>{rank["icon"]} {rank["title"]} LV.{rank["level"]}</div>
        </div>""", unsafe_allow_html=True)

    col3, col4 = st.columns(2)
    with col3:
        st.markdown(f"""
        <div style='background:{c["BG"]};border:1.5px solid {c["BORDER2"]};border-radius:8px;padding:14px;margin-bottom:10px;'>
            <div style='font-family:Share Tech Mono,monospace;font-size:0.55rem;color:{c["TEXT3"]};letter-spacing:2px;margin-bottom:4px;'>TOTAL XP</div>
            <div style='font-family:Orbitron,sans-serif;font-size:0.85rem;font-weight:700;color:{c["ACCENT"]};'>{xp:,} XP</div>
        </div>""", unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div style='background:{c["BG"]};border:1.5px solid {c["BORDER2"]};border-radius:8px;padding:14px;margin-bottom:10px;'>
            <div style='font-family:Share Tech Mono,monospace;font-size:0.55rem;color:{c["TEXT3"]};letter-spacing:2px;margin-bottom:4px;'>TOTAL MISSIONS</div>
            <div style='font-family:Orbitron,sans-serif;font-size:0.85rem;font-weight:700;color:{c["TEXT"]};'>{total_runs} runs</div>
        </div>""", unsafe_allow_html=True)

    # ── SECTION: TRAINING GOALS ───────────────────────────────────
    st.markdown(f"""
    <div style='background:{c["CARD"]};border:1.5px solid {c["BORDER2"]};border-radius:10px;
        padding:18px;margin-bottom:16px;margin-top:6px;position:relative;overflow:hidden;'>
        <div style='position:absolute;top:0;left:0;right:0;height:2px;
            background:linear-gradient(90deg,{c["ACCENT"]},transparent);'></div>
        <div style='font-family:Orbitron,sans-serif;font-size:0.78rem;font-weight:700;
            color:{c["ACCENT"]};letter-spacing:3px;margin-bottom:14px;'>◈ TRAINING GOALS</div>
    </div>""", unsafe_allow_html=True)

    with st.form("goals_form"):
        weekly_target = st.slider("Weekly run target (runs/week)", 1, 14,
                                  value=profile.get("weekly_target", 3))
        km_goal = st.slider("Monthly distance goal (km)", 10, 500,
                            value=profile.get("km_goal", 50), step=10)
        pace_goal_min = st.slider("Pace goal (min/km)", 3, 15,
                                  value=profile.get("pace_goal", 6))
        race_options = ["No goal", "5K", "10K", "Half Marathon (21.1km)", "Full Marathon (42.2km)"]
        race_goal = st.selectbox("Race goal", race_options,
                                 index=race_options.index(profile.get("race_goal","No goal")) if profile.get("race_goal","No goal") in race_options else 0)
        if st.form_submit_button("◈ SAVE TRAINING GOALS", use_container_width=True):
            st.success(f"✅ Goals saved! Target: {weekly_target}x/week · {km_goal}km/month · sub {pace_goal_min}:00/km")

    # ── SECTION: NOTIFICATIONS ────────────────────────────────────
    st.markdown(f"""
    <div style='background:{c["CARD"]};border:1.5px solid {c["BORDER2"]};border-radius:10px;
        padding:18px;margin-bottom:16px;position:relative;overflow:hidden;'>
        <div style='position:absolute;top:0;left:0;right:0;height:2px;
            background:linear-gradient(90deg,{c["ACCENT"]},transparent);'></div>
        <div style='font-family:Orbitron,sans-serif;font-size:0.78rem;font-weight:700;
            color:{c["ACCENT"]};letter-spacing:3px;margin-bottom:14px;'>◈ NOTIFICATIONS</div>
    </div>""", unsafe_allow_html=True)

    col_a, col_b = st.columns(2)
    with col_a:
        streak_reminder = st.toggle("Streak reminders", value=True)
        quest_alerts = st.toggle("Quest completion alerts", value=True)
    with col_b:
        rank_up = st.toggle("Rank up notifications", value=True)
        weekly_summary = st.toggle("Weekly summary", value=True)

    # ── SECTION: DATA ─────────────────────────────────────────────
    st.markdown(f"""
    <div style='background:{c["CARD"]};border:1.5px solid {c["BORDER2"]};border-radius:10px;
        padding:18px;margin-bottom:16px;position:relative;overflow:hidden;'>
        <div style='position:absolute;top:0;left:0;right:0;height:2px;
            background:linear-gradient(90deg,{c["ACCENT"]},transparent);'></div>
        <div style='font-family:Orbitron,sans-serif;font-size:0.78rem;font-weight:700;
            color:{c["ACCENT"]};letter-spacing:3px;margin-bottom:14px;'>◈ DATA & PRIVACY</div>
    </div>""", unsafe_allow_html=True)

    col_x, col_y = st.columns(2)
    with col_x:
        if st.button("📤 Export Run Data", use_container_width=True):
            runs_data = get_runs(user_id)
            import json
            export = json.dumps(runs_data, indent=2, default=str)
            st.download_button("⬇ Download JSON", export, "runquest_data.json", "application/json", use_container_width=True)
    with col_y:
        if st.button("🗑 Clear All Runs", use_container_width=True):
            st.warning("⚠ This will delete ALL your run history! Type DELETE to confirm.")
            confirm = st.text_input("Type DELETE to confirm", key="delete_confirm")
            if confirm == "DELETE":
                runs_all = get_runs(user_id)
                for r in runs_all:
                    delete_run(r["id"])
                update_profile(user_id, 0, [], profile.get("unit","km"))
                st.success("All runs deleted.")
                st.rerun()

    # ── SECTION: APP INFO ─────────────────────────────────────────
    st.markdown(f"""
    <div style='background:{c["CARD"]};border:1.5px solid {c["BORDER2"]}40;border-radius:10px;
        padding:16px;margin-top:6px;'>
        <div style='font-family:Share Tech Mono,monospace;font-size:0.55rem;color:{c["TEXT3"]};letter-spacing:3px;margin-bottom:10px;'>◈ APP INFO</div>
        <div style='display:grid;grid-template-columns:1fr 1fr;gap:8px;'>
            <div style='font-family:Exo 2,sans-serif;font-size:0.8rem;color:{c["TEXT3"]};'>Version</div>
            <div style='font-family:Share Tech Mono,monospace;font-size:0.8rem;color:{c["TEXT2"]};text-align:right;'>v2.0 PERF TRACK</div>
            <div style='font-family:Exo 2,sans-serif;font-size:0.8rem;color:{c["TEXT3"]};'>AI Coach</div>
            <div style='font-family:Share Tech Mono,monospace;font-size:0.8rem;color:{c["ACCENT"]};text-align:right;'>ARIA / Groq Llama 3.1</div>
            <div style='font-family:Exo 2,sans-serif;font-size:0.8rem;color:{c["TEXT3"]};'>Backend</div>
            <div style='font-family:Share Tech Mono,monospace;font-size:0.8rem;color:{c["TEXT2"]};text-align:right;'>Supabase</div>
            <div style='font-family:Exo 2,sans-serif;font-size:0.8rem;color:{c["TEXT3"]};'>Built with</div>
            <div style='font-family:Share Tech Mono,monospace;font-size:0.8rem;color:{c["TEXT2"]};text-align:right;'>Streamlit + Python</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ─── MAIN ────────────────────────────────────────────────────────
def page_ai_coach(user_id, profile, runs, unit, c):
    import requests, json, datetime

    st.markdown("<div class='page-title'>◈ AI COACH</div>", unsafe_allow_html=True)
    st.markdown("<div class='page-sub'>POWERED BY CLAUDE AI — YOUR PERSONAL RUNNING INTELLIGENCE</div>", unsafe_allow_html=True)

    if not GROQ_API_KEY:
        st.error("⚠ Add GROQ_API_KEY to Streamlit Secrets to enable AI Coach.")
        st.markdown("""
        **How to get your free key:**
        1. Go to [console.groq.com](https://console.groq.com)
        2. Sign up free — no card needed
        3. Click **API Keys** → Create API Key
        4. Add to Streamlit Secrets: `GROQ_API_KEY = "gsk_..."`
        """)
        return

    # Build context from user data
    xp = profile.get("xp", 0)
    rank = get_rank(xp)
    rank_name = rank["title"]
    rank_lv = rank["level"]
    total_runs = len(runs)
    total_km = sum(r["distance_km"] for r in runs)
    avg_pace_sec = (sum(r["duration_seconds"] / r["distance_km"] for r in runs if r["distance_km"] > 0) / total_runs) if total_runs > 0 else 0
    recent = runs[:5] if runs else []
    recent_summary = "; ".join([f"{format_distance(r['distance_km'],unit)}{unit} in {format_time(r['duration_seconds'])}" for r in recent]) if recent else "No runs yet"
    days_since = None
    if runs:
        try:
            last = datetime.datetime.fromisoformat(runs[0]["started_at"].replace("Z",""))
            days_since = (datetime.datetime.utcnow() - last).days
        except: pass

    user_context = f"""User stats: Rank={rank_name} LV.{rank_lv}, XP={xp}, Total runs={total_runs}, Total distance={total_km:.1f}km, Avg pace={format_pace(avg_pace_sec,1,unit)}/km. Recent runs: {recent_summary}. Days since last run: {days_since if days_since is not None else 'N/A'}."""

    def ask_groq(prompt, system=""):
        full_system = f"You are ARIA — an elite AI running coach inside the RunQuest performance tracking app. You are concise, motivating, and give actionable advice. Always respond in under 300 words. Use short paragraphs. {user_context}\n{system}"
        try:
            resp = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                json={"model": "llama-3.1-8b-instant", "max_tokens": 400, "temperature": 0.7,
                      "messages": [{"role": "system", "content": full_system}, {"role": "user", "content": prompt}]},
                timeout=30
            )
            data = resp.json()
            if "choices" in data:
                return data["choices"][0]["message"]["content"]
            elif "error" in data:
                return f"Error: {data['error']['message']}"
            return "No response received."
        except Exception as e:
            return f"Connection error: {str(e)}"

    # ARIA header card
    st.markdown(f"""
    <div style='background:{c["CARD"]}; border:1.5px solid {c["ACCENT"]}40; border-radius:12px;
        padding:20px; position:relative; overflow:hidden; margin-bottom:20px;'>
        <div style='position:absolute; top:0; left:0; right:0; height:3px;
            background:linear-gradient(90deg,{c["ACCENT"]},{c["ACCENT2"]},transparent);'></div>
        <div style='display:flex; align-items:center; gap:14px;'>
            <div style='width:52px; height:52px; border-radius:50%;
                background:linear-gradient(135deg,{c["ACCENT"]}30,{c["ACCENT2"]}20);
                border:2px solid {c["ACCENT"]}60;
                display:flex; align-items:center; justify-content:center; flex-shrink:0;
                font-size:1.6rem;'>🤖</div>
            <div>
                <div style='font-family:Orbitron,sans-serif; font-size:1.1rem; font-weight:900;
                    color:{c["ACCENT"]}; letter-spacing:3px;'>ARIA</div>
                <div style='font-family:Share Tech Mono,monospace; font-size:0.6rem;
                    color:{c["TEXT3"]}; letter-spacing:2px;'>ADAPTIVE RUNNING INTELLIGENCE AGENT</div>
                <div style='font-family:Exo 2,sans-serif; font-size:0.82rem;
                    color:{c["TEXT2"]}; margin-top:4px;'>
                    Analyzing {total_runs} runs · {total_km:.1f}km total · {rank_name} LV.{rank_lv}
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── MENU CATEGORIES ──────────────────────────────────────────
    MENU = {
        "📊 Performance": {
            "icon": "📊", "color": "#4FC3F7",
            "items": [
                ("Weekly Briefing",       "Give me a full weekly performance briefing based on my recent runs. Include what went well, what to improve, and specific goals for next week."),
                ("Pace Analysis",         "Analyze my running pace trends. Am I improving? What pace should I target next run?"),
                ("Progress Report",       "Give me a detailed progress report. How am I trending toward higher ranks and completing quests?"),
                ("Personal Best Tips",    "How can I beat my personal records? Give me specific strategies based on my current stats."),
            ]
        },
        "🏃 Training Plan": {
            "icon": "🏃", "color": "#81C784",
            "items": [
                ("Today's Run Plan",      "Based on my recent runs, design the perfect run for today. Include distance, pace target, and structure (warmup/main/cooldown)."),
                ("Weekly Schedule",       "Create a 7-day training schedule for me this week. Balance rest days and running days based on my current fitness level."),
                ("Speed Training",        "Design a speed/interval training session for me. Include exact distances and pace targets."),
                ("Long Run Plan",         "Plan a long slow distance run for me. What distance, pace, and tips should I follow?"),
                ("5K Training Program",   "Build me a 4-week program to improve my 5K time. Give week-by-week targets."),
            ]
        },
        "💪 Daily Exercise": {
            "icon": "💪", "color": "#FFB74D",
            "items": [
                ("Pre-Run Warmup",        "Give me a complete pre-run warmup routine. Include dynamic stretches and activation exercises with reps/sets."),
                ("Post-Run Cooldown",     "Design a post-run cooldown and stretching routine. Include static stretches targeting running muscles."),
                ("Strength for Runners",  "Give me a strength training workout specifically for runners. Focus on legs, core, and glutes with sets/reps."),
                ("Push-Up Challenge",     "Create a 30-day push-up progression plan for me. Start from my current level and build up progressively."),
                ("Core Workout",          "Design a 15-minute core workout for runners. Include planks, crunches, and stability exercises."),
                ("Rest Day Exercise",     "What exercises should I do on rest days? Give me light activities that aid recovery without overtraining."),
            ]
        },
        "🩹 Recovery": {
            "icon": "🩹", "color": "#F48FB1",
            "items": [
                ("Recovery Check",        "Assess my recovery needs based on recent training. Should I rest or is it okay to run today?"),
                ("Injury Prevention",     "What are the top injury risks for a runner at my level? Give me specific prevention exercises and habits."),
                ("Muscle Soreness Help",  "I have sore muscles after running. What should I do to recover faster? Include specific techniques."),
                ("Knee Care Tips",        "Give me exercises and tips to protect my knees while running and building mileage."),
                ("Sleep & Recovery",      "How should I optimize my sleep and recovery for better running performance? Give practical daily habits."),
            ]
        },
        "🥗 Nutrition": {
            "icon": "🥗", "color": "#A5D6A7",
            "items": [
                ("Pre-Run Meal",          "What should I eat before a run? Give specific meal ideas for different run lengths (short/medium/long)."),
                ("Post-Run Nutrition",    "What should I eat after running to maximize recovery? Include protein, carbs, and timing."),
                ("Hydration Plan",        "Design a hydration strategy for me. How much water before, during, and after runs? Any electrolyte tips?"),
                ("Daily Diet for Runners","What does an ideal daily diet look like for a runner at my level? Give a simple meal structure."),
                ("Energy Snacks",         "What are the best energy snacks to eat during or before longer runs? Give healthy portable options."),
            ]
        },
        "⏰ Reminders": {
            "icon": "⏰", "color": "#CE93D8",
            "items": [
                ("Should I Run Today?",   "Based on my recent activity, should I run today or rest? Give a clear recommendation with reasoning."),
                ("Streak Motivation",     "Motivate me to keep running consistently. Give me specific reasons why consistency matters at my level."),
                ("Quest Strategy",        "Which quests should I focus on completing next? Give me a strategy to earn the most XP efficiently."),
                ("Rank Up Plan",          "How many more runs do I need to rank up? Give me a specific plan to reach the next rank as fast as possible."),
            ]
        },
    }

    # Session state for results
    if "coach_result" not in st.session_state: st.session_state.coach_result = None
    if "coach_title" not in st.session_state: st.session_state.coach_title = None
    if "coach_loading" not in st.session_state: st.session_state.coach_loading = False

    # Show result if available
    if st.session_state.coach_result:
        st.markdown(f"""
        <div style='background:{c["CARD"]}; border:1.5px solid {c["ACCENT"]}50;
            border-radius:10px; padding:18px; margin-bottom:20px; position:relative; overflow:hidden;'>
            <div style='position:absolute; top:0; left:0; right:0; height:2px;
                background:linear-gradient(90deg,{c["ACCENT"]},transparent);'></div>
            <div style='font-family:Orbitron,sans-serif; font-size:0.72rem; font-weight:700;
                color:{c["ACCENT"]}; letter-spacing:2px; margin-bottom:12px;'>
                🤖 ARIA · {st.session_state.coach_title}
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(st.session_state.coach_result)
        if st.button("✕ Clear Response", key="clear_coach"):
            st.session_state.coach_result = None
            st.session_state.coach_title = None
            st.rerun()
        st.markdown("<hr>", unsafe_allow_html=True)

    # Render menu categories
    for cat_name, cat_data in MENU.items():
        cat_color = cat_data["color"]
        with st.expander(f"{cat_data['icon']}  {cat_name.split(' ', 1)[1]}", expanded=False):
            st.markdown(f"""
            <div style='height:3px; background:linear-gradient(90deg,{cat_color}80,transparent);
                border-radius:2px; margin-bottom:14px;'></div>
            """, unsafe_allow_html=True)
            for item_title, item_prompt in cat_data["items"]:
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(f"""
                    <div style='font-family:Exo 2,sans-serif; font-size:0.9rem; font-weight:600;
                        color:{c["TEXT"]}; padding:6px 0;'>{item_title}</div>
                    """, unsafe_allow_html=True)
                with col2:
                    if st.button("ASK", key=f"ask_{item_title.replace(' ','_')}"):
                        st.session_state.coach_loading = True
                        st.session_state.coach_title = item_title
                        with st.spinner(f"🤖 ARIA is analyzing..."):
                            result = ask_groq(item_prompt)
                        st.session_state.coach_result = result
                        st.session_state.coach_loading = False
                        st.rerun()

    # Custom question
    st.markdown(f"""
    <div style='margin-top:20px; background:{c["CARD"]}; border:1.5px solid {c["BORDER2"]};
        border-radius:10px; padding:16px; position:relative; overflow:hidden;'>
        <div style='position:absolute; top:0; left:0; right:0; height:2px;
            background:linear-gradient(90deg,transparent,{c["ACCENT"]},transparent);'></div>
        <div style='font-family:Orbitron,sans-serif; font-size:0.72rem; font-weight:700;
            color:{c["ACCENT"]}; letter-spacing:2px; margin-bottom:10px;'>◈ ASK ARIA ANYTHING</div>
    </div>
    """, unsafe_allow_html=True)
    with st.form("custom_coach_form"):
        custom_q = st.text_area("Your question", placeholder="e.g. How do I run faster without getting tired? What shoes are best for beginners?...", height=80)
        if st.form_submit_button("◈ ASK ARIA", use_container_width=True):
            if custom_q.strip():
                with st.spinner("🤖 ARIA is thinking..."):
                    result = ask_groq(custom_q)
                st.session_state.coach_result = result
                st.session_state.coach_title = "Custom Question"
                st.rerun()
            else:
                st.error("Please type a question first.")


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
    elif page == "AI Coach":    page_ai_coach(user_id, profile, runs, unit, c)

if __name__ == "__main__":
    main()

