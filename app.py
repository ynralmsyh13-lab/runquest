import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timedelta

# ─── PAGE CONFIG ────────────────────────────────────────────────
st.set_page_config(
    page_title="RunQuest",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── SUPABASE ───────────────────────────────────────────────────
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

@st.cache_resource
def get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

sb = get_supabase()

# ─── HELPERS ────────────────────────────────────────────────────
def format_time(seconds):
    if not seconds: return "00:00"
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0: return f"{h}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

def format_pace(seconds, distance_km, unit='km'):
    if not distance_km or distance_km == 0: return "--:--"
    pace = (seconds / 60) / distance_km
    if unit == 'mi': pace = pace / 1.60934
    m = int(pace); s = int((pace - m) * 60)
    return f"{m}:{s:02d}"

def format_distance(km, unit='km'):
    if unit == 'mi': return round(km * 0.621371, 2)
    return round(km, 2)

def is_this_week(date_str):
    try:
        d = datetime.fromisoformat(date_str.replace('Z', '+00:00')).replace(tzinfo=None)
        today = datetime.utcnow()
        start = today - timedelta(days=today.weekday())
        start = start.replace(hour=0, minute=0, second=0)
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
    {"id": "total_50km",    "title": "Fifty and Counting","desc": "Accumulate 50km total distance",      "icon": "🗺️", "xp": 200},
    {"id": "total_100km",   "title": "Century Runner",    "desc": "Accumulate 100km total distance",    "icon": "💯", "xp": 400},
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
    current = get_rank(xp)
    next_r = get_next_rank(xp)
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
        diff = (datetime.fromisoformat(dates[i]) - datetime.fromisoformat(dates[i-1])).days
        if diff == 1:
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
    fresh_ids = [qid for qid in now_completed if qid not in prev_completed]
    fresh_quests = [q for q in QUESTS if q["id"] in fresh_ids]
    quest_xp = sum(q["xp"] for q in fresh_quests)
    update_profile(user_id, profile.get("xp", 0) + xp + quest_xp, now_completed, unit_sel)
    return xp + quest_xp, is_pb, fresh_quests

# ─── CYBER GOLD THEME ───────────────────────────────────────────
def apply_theme():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;600;700;900&family=Rajdhani:wght@300;400;600;700&family=Share+Tech+Mono&display=swap');

    html, body, [class*="css"] {
        font-family: 'Rajdhani', sans-serif !important;
        background-color: #070A0E !important;
        color: #E8D5A3 !important;
    }

    .stApp {
        background: #070A0E !important;
        background-image:
            radial-gradient(ellipse at 15% 20%, rgba(255, 180, 0, 0.04) 0%, transparent 50%),
            radial-gradient(ellipse at 85% 80%, rgba(255, 140, 0, 0.03) 0%, transparent 50%),
            linear-gradient(180deg, #070A0E 0%, #0A0D12 100%) !important;
    }

    section[data-testid="stSidebar"] {
        background: #080B10 !important;
        border-right: 1px solid #FFB30030 !important;
        background-image: linear-gradient(180deg, #0D1117 0%, #080B10 100%) !important;
    }

    section[data-testid="stSidebar"]::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 2px;
        background: linear-gradient(90deg, transparent, #FFB300, transparent);
    }

    .stButton > button {
        font-family: 'Orbitron', sans-serif !important;
        border-radius: 4px !important;
        font-weight: 600 !important;
        letter-spacing: 1px !important;
        font-size: 0.75rem !important;
        transition: all 0.2s !important;
        border: 1px solid #FFB30060 !important;
        background: #0D1117 !important;
        color: #FFB300 !important;
    }

    .stButton > button:hover {
        background: #FFB30015 !important;
        border-color: #FFB300 !important;
        box-shadow: 0 0 15px rgba(255,179,0,0.2) !important;
    }

    .stTextInput > div > div > input,
    .stNumberInput > div > div > input {
        background: #0D1117 !important;
        color: #E8D5A3 !important;
        border: 1px solid #FFB30040 !important;
        border-radius: 4px !important;
        font-family: 'Rajdhani', sans-serif !important;
    }

    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus {
        border-color: #FFB300 !important;
        box-shadow: 0 0 10px rgba(255,179,0,0.15) !important;
    }

    .stSelectbox > div > div {
        background: #0D1117 !important;
        color: #E8D5A3 !important;
        border: 1px solid #FFB30040 !important;
    }

    .stRadio > div { gap: 8px; }
    .stRadio label { color: #E8D5A3 !important; font-family: 'Rajdhani', sans-serif !important; }

    .stTabs [data-baseweb="tab-list"] {
        background: #0D1117 !important;
        border-bottom: 1px solid #FFB30030 !important;
    }
    .stTabs [data-baseweb="tab"] {
        font-family: 'Orbitron', sans-serif !important;
        font-size: 0.65rem !important;
        color: #8A7A5A !important;
        letter-spacing: 1px !important;
    }
    .stTabs [aria-selected="true"] {
        color: #FFB300 !important;
        border-bottom: 2px solid #FFB300 !important;
    }

    div[data-testid="stMetricValue"] {
        font-family: 'Orbitron', sans-serif !important;
        color: #FFB300 !important;
    }
    div[data-testid="stMetricLabel"] {
        font-family: 'Rajdhani', sans-serif !important;
        color: #8A7A5A !important;
    }

    .stAlert { border-radius: 4px !important; }

    hr { border-color: #FFB30020 !important; }

    ::-webkit-scrollbar { width: 4px; }
    ::-webkit-scrollbar-track { background: #070A0E; }
    ::-webkit-scrollbar-thumb { background: #FFB30040; border-radius: 2px; }

    /* ── CUSTOM COMPONENTS ── */

    .cyber-logo {
        font-family: 'Orbitron', sans-serif;
        font-size: 1.5rem;
        font-weight: 900;
        letter-spacing: 4px;
        background: linear-gradient(135deg, #FFB300, #FF8C00, #FFD700);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        text-shadow: none;
        position: relative;
    }

    .cyber-logo-sub {
        font-family: 'Share Tech Mono', monospace;
        font-size: 0.55rem;
        color: #FFB30060;
        letter-spacing: 6px;
        text-transform: uppercase;
        margin-top: -4px;
    }

    .cyber-card {
        background: linear-gradient(135deg, #0D1117 0%, #0A0D12 100%);
        border: 1px solid #FFB30030;
        border-radius: 4px;
        padding: 20px;
        position: relative;
        overflow: hidden;
        margin-bottom: 12px;
    }

    .cyber-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 1px;
        background: linear-gradient(90deg, transparent, #FFB300, transparent);
    }

    .cyber-card::after {
        content: '';
        position: absolute;
        bottom: 0; left: 0;
        width: 40%;
        height: 1px;
        background: linear-gradient(90deg, #FFB30060, transparent);
    }

    .metric-card {
        background: #0D1117;
        border: 1px solid #FFB30025;
        border-radius: 4px;
        padding: 18px 12px;
        text-align: center;
        position: relative;
        overflow: hidden;
    }

    .metric-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 2px;
        background: linear-gradient(90deg, transparent, #FFB300, transparent);
    }

    .metric-value {
        font-family: 'Orbitron', sans-serif;
        font-size: 1.8rem;
        font-weight: 700;
        background: linear-gradient(135deg, #FFD700, #FFB300);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        line-height: 1.1;
    }

    .metric-label {
        font-family: 'Share Tech Mono', monospace;
        font-size: 0.6rem;
        color: #5A4A2A;
        text-transform: uppercase;
        letter-spacing: 2px;
        margin-top: 6px;
    }

    .cyber-page-title {
        font-family: 'Orbitron', sans-serif;
        font-size: 1.4rem;
        font-weight: 700;
        background: linear-gradient(135deg, #FFD700, #FF8C00);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        letter-spacing: 3px;
        text-transform: uppercase;
        margin-bottom: 4px;
    }

    .cyber-subtitle {
        font-family: 'Share Tech Mono', monospace;
        font-size: 0.65rem;
        color: #5A4A2A;
        letter-spacing: 3px;
        text-transform: uppercase;
    }

    .rank-chip {
        display: inline-block;
        padding: 4px 14px;
        border-radius: 2px;
        font-family: 'Orbitron', sans-serif;
        font-size: 0.6rem;
        font-weight: 700;
        background: #FFB30010;
        color: #FFB300;
        border: 1px solid #FFB30050;
        letter-spacing: 2px;
        text-transform: uppercase;
    }

    .xp-bar-outer {
        background: #0D1117;
        border: 1px solid #FFB30020;
        border-radius: 2px;
        height: 8px;
        overflow: hidden;
        margin: 10px 0;
        position: relative;
    }

    .xp-bar-inner {
        height: 100%;
        background: linear-gradient(90deg, #FF8C00, #FFB300, #FFD700);
        border-radius: 2px;
        position: relative;
        box-shadow: 0 0 8px rgba(255,179,0,0.5);
    }

    .run-card {
        background: #0D1117;
        border: 1px solid #FFB30020;
        border-left: 3px solid #FFB300;
        border-radius: 4px;
        padding: 14px 18px;
        margin-bottom: 8px;
        position: relative;
        transition: all 0.2s;
    }

    .run-card:hover {
        border-color: #FFB30060;
        box-shadow: 0 0 15px rgba(255,179,0,0.08);
    }

    .quest-card {
        background: #0D1117;
        border: 1px solid #FFB30020;
        border-radius: 4px;
        padding: 14px 18px;
        margin-bottom: 8px;
        transition: all 0.2s;
    }

    .quest-card:hover {
        border-color: #FFB30050;
        transform: translateX(4px);
    }

    .quest-done {
        background: rgba(255,179,0,0.04);
        border: 1px solid rgba(255,179,0,0.15);
        border-radius: 4px;
        padding: 12px 16px;
        margin-bottom: 8px;
    }

    .pb-badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 2px;
        font-family: 'Orbitron', sans-serif;
        font-size: 0.55rem;
        font-weight: 700;
        background: rgba(255,215,0,0.1);
        color: #FFD700;
        border: 1px solid rgba(255,215,0,0.4);
        letter-spacing: 1px;
    }

    .nav-label {
        font-family: 'Share Tech Mono', monospace;
        font-size: 0.6rem;
        color: #5A4A2A;
        letter-spacing: 3px;
        text-transform: uppercase;
        margin-bottom: 8px;
        padding: 0 4px;
    }

    .data-val {
        font-family: 'Share Tech Mono', monospace;
        font-size: 0.9rem;
        color: #FFB300;
        font-weight: 600;
    }

    .data-label {
        font-family: 'Share Tech Mono', monospace;
        font-size: 0.6rem;
        color: #5A4A2A;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    .divider-cyber {
        border: none;
        height: 1px;
        background: linear-gradient(90deg, transparent, #FFB30030, transparent);
        margin: 16px 0;
    }

    .gps-display {
        background: #070A0E;
        border: 1px solid #FFB30030;
        border-radius: 4px;
        padding: 24px 16px;
        text-align: center;
        position: relative;
        overflow: hidden;
    }

    .gps-display::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 1px;
        background: linear-gradient(90deg, transparent, #FFB300, transparent);
    }

    .gps-value {
        font-family: 'Orbitron', sans-serif;
        font-size: 3rem;
        font-weight: 900;
        background: linear-gradient(135deg, #FFD700, #FFB300);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        line-height: 1;
    }

    .gps-unit {
        font-family: 'Share Tech Mono', monospace;
        font-size: 0.65rem;
        color: #5A4A2A;
        letter-spacing: 3px;
        margin-top: 6px;
    }

    .live-indicator {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-family: 'Share Tech Mono', monospace;
        font-size: 0.65rem;
        color: #FFB300;
        letter-spacing: 2px;
    }

    .live-dot {
        width: 8px; height: 8px;
        border-radius: 50%;
        background: #FFB300;
        box-shadow: 0 0 8px #FFB300;
        animation: pulse-gold 1.5s ease-in-out infinite;
    }

    @keyframes pulse-gold {
        0%, 100% { opacity: 1; box-shadow: 0 0 8px #FFB300; }
        50% { opacity: 0.4; box-shadow: 0 0 2px #FFB300; }
    }

    @keyframes scanline {
        0% { transform: translateY(-100%); }
        100% { transform: translateY(100vh); }
    }

    .corner-tl {
        position: absolute; top: 0; left: 0;
        width: 12px; height: 12px;
        border-top: 2px solid #FFB300;
        border-left: 2px solid #FFB300;
    }

    .corner-br {
        position: absolute; bottom: 0; right: 0;
        width: 12px; height: 12px;
        border-bottom: 2px solid #FFB300;
        border-right: 2px solid #FFB300;
    }

    </style>
    """, unsafe_allow_html=True)

# ─── GPS JS ─────────────────────────────────────────────────────
GPS_JS = """
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&family=Share+Tech+Mono&display=swap" rel="stylesheet">
<div id="gps-tracker" style="font-family:'Rajdhani',sans-serif;">

  <div id="wakelock-tip" style="
    background:rgba(255,179,0,0.06); border:1px solid rgba(255,179,0,0.3);
    border-radius:4px; padding:10px 14px; margin-bottom:14px;
    font-family:'Share Tech Mono',monospace; font-size:0.7rem; color:#FFB300;
    letter-spacing:1px; display:none;">
    ⚠ KEEP SCREEN ACTIVE — DO NOT LOCK DEVICE
  </div>

  <!-- Metrics grid -->
  <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:10px; margin-bottom:16px;">

    <div style="background:#070A0E; border:1px solid #FFB30030; border-radius:4px; padding:18px 8px; text-align:center; position:relative; overflow:hidden;">
      <div style="position:absolute; top:0; left:0; right:0; height:1px; background:linear-gradient(90deg,transparent,#FFB300,transparent);"></div>
      <div id="dist-display" style="font-family:'Orbitron',sans-serif; font-size:2.2rem; font-weight:900; background:linear-gradient(135deg,#FFD700,#FFB300); -webkit-background-clip:text; -webkit-text-fill-color:transparent; line-height:1;">0.00</div>
      <div id="dist-unit" style="font-family:'Share Tech Mono',monospace; font-size:0.6rem; color:#5A4A2A; letter-spacing:3px; margin-top:4px;">KM</div>
    </div>

    <div style="background:#070A0E; border:1px solid #FFB30030; border-radius:4px; padding:18px 8px; text-align:center; position:relative; overflow:hidden;">
      <div style="position:absolute; top:0; left:0; right:0; height:1px; background:linear-gradient(90deg,transparent,#FFB300,transparent);"></div>
      <div id="time-display" style="font-family:'Orbitron',sans-serif; font-size:2.2rem; font-weight:900; color:#E8D5A3; line-height:1;">00:00</div>
      <div style="font-family:'Share Tech Mono',monospace; font-size:0.6rem; color:#5A4A2A; letter-spacing:3px; margin-top:4px;">TIME</div>
    </div>

    <div style="background:#070A0E; border:1px solid #FFB30030; border-radius:4px; padding:18px 8px; text-align:center; position:relative; overflow:hidden;">
      <div style="position:absolute; top:0; left:0; right:0; height:1px; background:linear-gradient(90deg,transparent,#FFB300,transparent);"></div>
      <div id="pace-display" style="font-family:'Orbitron',sans-serif; font-size:2.2rem; font-weight:900; color:#E8D5A3; line-height:1;">--:--</div>
      <div id="pace-unit" style="font-family:'Share Tech Mono',monospace; font-size:0.6rem; color:#5A4A2A; letter-spacing:3px; margin-top:4px;">MIN/KM</div>
    </div>
  </div>

  <!-- Status -->
  <div id="status-bar" style="text-align:center; margin-bottom:12px; font-family:'Share Tech Mono',monospace; font-size:0.7rem; color:#5A4A2A; letter-spacing:2px;">
    [ SYSTEM READY — PRESS START ]
  </div>

  <!-- GPS accuracy -->
  <div id="accuracy-bar" style="text-align:center; margin-bottom:12px; font-family:'Share Tech Mono',monospace; font-size:0.65rem; color:#5A4A2A; display:none; letter-spacing:1px;">
    SIGNAL ACCURACY: <span id="accuracy-val" style="color:#FFB300;">--</span>m
  </div>

  <!-- Buttons -->
  <div style="display:flex; gap:8px; margin-bottom:12px;">
    <button id="btn-start" onclick="startTracking()" style="
      flex:1; padding:14px 8px; border-radius:4px; border:1px solid #FFB300; cursor:pointer;
      background:linear-gradient(135deg,#FFB30020,#FF8C0010);
      color:#FFB300; font-family:'Orbitron',sans-serif; font-size:0.7rem;
      font-weight:700; letter-spacing:2px; transition:all 0.2s;">
      ▶ INITIATE
    </button>
    <button id="btn-pause" onclick="pauseTracking()" style="
      flex:1; padding:14px 8px; border-radius:4px; border:1px solid #FF8C0080; cursor:pointer;
      background:#0D1117; color:#FF8C00; font-family:'Orbitron',sans-serif;
      font-size:0.7rem; font-weight:700; letter-spacing:2px; display:none;">
      ⏸ PAUSE
    </button>
    <button id="btn-resume" onclick="resumeTracking()" style="
      flex:1; padding:14px 8px; border-radius:4px; border:1px solid #FFB300; cursor:pointer;
      background:linear-gradient(135deg,#FFB30020,#FF8C0010);
      color:#FFB300; font-family:'Orbitron',sans-serif;
      font-size:0.7rem; font-weight:700; letter-spacing:2px; display:none;">
      ▶ RESUME
    </button>
    <button id="btn-stop" onclick="stopTracking()" style="
      flex:1; padding:14px 8px; border-radius:4px; border:1px solid #FF444480; cursor:pointer;
      background:#0D1117; color:#FF4444; font-family:'Orbitron',sans-serif;
      font-size:0.7rem; font-weight:700; letter-spacing:2px; display:none;">
      ■ HALT
    </button>
  </div>

  <!-- Hidden inputs -->
  <input type="hidden" id="final-distance" value="0">
  <input type="hidden" id="final-duration" value="0">

  <!-- Summary -->
  <div id="save-section" style="display:none; margin-top:12px; background:#070A0E;
    border:1px solid #FFB30030; border-radius:4px; padding:18px; position:relative;">
    <div style="position:absolute; top:0; left:0; right:0; height:1px; background:linear-gradient(90deg,transparent,#FFB300,transparent);"></div>
    <div style="font-family:'Share Tech Mono',monospace; font-size:0.6rem; color:#FFB300; letter-spacing:3px; margin-bottom:14px;">◈ RUN SUMMARY</div>
    <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
      <div style="text-align:center;">
        <div style="font-family:'Share Tech Mono',monospace; font-size:0.55rem; color:#5A4A2A; letter-spacing:2px; margin-bottom:4px;">DISTANCE</div>
        <div id="summary-dist" style="font-family:'Orbitron',sans-serif; font-size:1.3rem; font-weight:700; color:#FFB300;"></div>
      </div>
      <div style="text-align:center;">
        <div style="font-family:'Share Tech Mono',monospace; font-size:0.55rem; color:#5A4A2A; letter-spacing:2px; margin-bottom:4px;">DURATION</div>
        <div id="summary-time" style="font-family:'Orbitron',sans-serif; font-size:1.3rem; font-weight:700; color:#E8D5A3;"></div>
      </div>
      <div style="text-align:center;">
        <div style="font-family:'Share Tech Mono',monospace; font-size:0.55rem; color:#5A4A2A; letter-spacing:2px; margin-bottom:4px;">AVG PACE</div>
        <div id="summary-pace" style="font-family:'Orbitron',sans-serif; font-size:1.3rem; font-weight:700; color:#E8D5A3;"></div>
      </div>
      <div style="text-align:center;">
        <div style="font-family:'Share Tech Mono',monospace; font-size:0.55rem; color:#5A4A2A; letter-spacing:2px; margin-bottom:4px;">STATUS</div>
        <div style="font-family:'Orbitron',sans-serif; font-size:1.3rem; font-weight:700; color:#FFB300;">COMPLETE</div>
      </div>
    </div>
    <button id="btn-save" onclick="saveRun()" style="
      width:100%; margin-top:16px; padding:14px; border-radius:4px;
      border:1px solid #FFB300; cursor:pointer;
      background:linear-gradient(135deg,#FFB30025,#FF8C0015);
      color:#FFB300; font-family:'Orbitron',sans-serif;
      font-size:0.75rem; font-weight:700; letter-spacing:3px;">
      ◈ UPLOAD RUN DATA
    </button>
  </div>
</div>

<script>
var watchId=null, timerInterval=null, lastPos=null;
var totalDistance=0, elapsedSeconds=0, isPaused=false, wakeLock=null;
var unit='UNIT_PLACEHOLDER';

function haversine(lat1,lon1,lat2,lon2){
  var R=6371, dLat=(lat2-lat1)*Math.PI/180, dLon=(lon2-lon1)*Math.PI/180;
  var a=Math.sin(dLat/2)*Math.sin(dLat/2)+Math.cos(lat1*Math.PI/180)*Math.cos(lat2*Math.PI/180)*Math.sin(dLon/2)*Math.sin(dLon/2);
  return R*2*Math.atan2(Math.sqrt(a),Math.sqrt(1-a));
}
function formatTime(s){
  var h=Math.floor(s/3600),m=Math.floor((s%3600)/60),sec=s%60;
  if(h>0)return h+':'+String(m).padStart(2,'0')+':'+String(sec).padStart(2,'0');
  return String(m).padStart(2,'0')+':'+String(sec).padStart(2,'0');
}
function formatPace(sec,dist){
  if(dist<0.01)return '--:--';
  var pace=(sec/60)/dist;
  if(unit==='mi')pace=pace/1.60934;
  var m=Math.floor(pace),s=Math.round((pace-m)*60);
  return m+':'+String(s).padStart(2,'0');
}
function formatDist(km){
  return unit==='mi'?(km*0.621371).toFixed(2):km.toFixed(2);
}
async function requestWakeLock(){
  try{if('wakeLock' in navigator)wakeLock=await navigator.wakeLock.request('screen');}
  catch(e){document.getElementById('wakelock-tip').style.display='block';}
}
function startTracking(){
  if(!navigator.geolocation){
    document.getElementById('status-bar').innerHTML='<span style="color:#FF4444;font-family:Share Tech Mono,monospace;letter-spacing:2px">⚠ GPS NOT AVAILABLE</span>';
    return;
  }
  totalDistance=0; elapsedSeconds=0; lastPos=null; isPaused=false;
  document.getElementById('btn-start').style.display='none';
  document.getElementById('btn-pause').style.display='flex';
  document.getElementById('btn-stop').style.display='flex';
  document.getElementById('save-section').style.display='none';
  document.getElementById('accuracy-bar').style.display='block';
  document.getElementById('status-bar').innerHTML='<span style="display:inline-flex;align-items:center;gap:6px;font-family:Share Tech Mono,monospace;font-size:0.7rem;color:#FFB300;letter-spacing:2px"><span style="width:8px;height:8px;border-radius:50%;background:#FFB300;box-shadow:0 0 8px #FFB300;animation:pulse-gold 1.5s ease-in-out infinite;display:inline-block"></span>TRACKING ACTIVE</span>';
  requestWakeLock();
  timerInterval=setInterval(function(){
    if(!isPaused){
      elapsedSeconds++;
      document.getElementById('time-display').textContent=formatTime(elapsedSeconds);
      document.getElementById('pace-display').textContent=formatPace(elapsedSeconds,totalDistance);
    }
  },1000);
  watchId=navigator.geolocation.watchPosition(
    function(pos){
      var acc=Math.round(pos.coords.accuracy);
      var col=acc<15?'#FFB300':acc<30?'#FF8C00':'#FF4444';
      document.getElementById('accuracy-val').textContent=acc;
      document.getElementById('accuracy-val').style.color=col;
      if(!isPaused){
        var newPos={lat:pos.coords.latitude,lon:pos.coords.longitude};
        if(lastPos){
          var d=haversine(lastPos.lat,lastPos.lon,newPos.lat,newPos.lon);
          if(d<0.3&&d>0.002){
            totalDistance+=d;
            document.getElementById('dist-display').textContent=formatDist(totalDistance);
            document.getElementById('dist-unit').textContent=unit.toUpperCase();
            document.getElementById('pace-unit').textContent='MIN/'+unit.toUpperCase();
          }
        }
        lastPos=newPos;
      }
    },
    function(err){
      document.getElementById('status-bar').innerHTML='<span style="color:#FF4444;font-family:Share Tech Mono,monospace;letter-spacing:1px;font-size:0.65rem">⚠ GPS ERROR: '+err.message+'</span>';
    },
    {enableHighAccuracy:true,maximumAge:2000,timeout:15000}
  );
}
function pauseTracking(){
  isPaused=true;
  document.getElementById('btn-pause').style.display='none';
  document.getElementById('btn-resume').style.display='flex';
  document.getElementById('status-bar').innerHTML='<span style="color:#FF8C00;font-family:Share Tech Mono,monospace;letter-spacing:2px;font-size:0.7rem">⏸ SESSION PAUSED</span>';
}
function resumeTracking(){
  isPaused=false; lastPos=null;
  document.getElementById('btn-resume').style.display='none';
  document.getElementById('btn-pause').style.display='flex';
  document.getElementById('status-bar').innerHTML='<span style="display:inline-flex;align-items:center;gap:6px;font-family:Share Tech Mono,monospace;font-size:0.7rem;color:#FFB300;letter-spacing:2px"><span style="width:8px;height:8px;border-radius:50%;background:#FFB300;animation:pulse-gold 1.5s ease-in-out infinite;display:inline-block"></span>TRACKING ACTIVE</span>';
}
function stopTracking(){
  isPaused=false;
  clearInterval(timerInterval);
  if(watchId!==null)navigator.geolocation.clearWatch(watchId);
  if(wakeLock)wakeLock.release();
  document.getElementById('btn-pause').style.display='none';
  document.getElementById('btn-resume').style.display='none';
  document.getElementById('btn-stop').style.display='none';
  document.getElementById('btn-start').style.display='flex';
  document.getElementById('accuracy-bar').style.display='none';
  document.getElementById('status-bar').innerHTML='<span style="color:#5A4A2A;font-family:Share Tech Mono,monospace;letter-spacing:2px;font-size:0.65rem">[ SESSION TERMINATED — REVIEW DATA ]</span>';
  document.getElementById('summary-dist').textContent=formatDist(totalDistance)+' '+unit;
  document.getElementById('summary-time').textContent=formatTime(elapsedSeconds);
  document.getElementById('summary-pace').textContent=formatPace(elapsedSeconds,totalDistance)+'/'+unit;
  document.getElementById('final-distance').value=totalDistance.toFixed(4);
  document.getElementById('final-duration').value=elapsedSeconds;
  document.getElementById('save-section').style.display='block';
}
function saveRun(){
  var dist=parseFloat(document.getElementById('final-distance').value);
  var dur=parseInt(document.getElementById('final-duration').value);
  if(dist<0.01||dur<1){alert('No run data recorded!');return;}
  var url=new URL(window.location.href);
  url.searchParams.set('gps_dist',dist.toFixed(4));
  url.searchParams.set('gps_dur',dur);
  url.searchParams.set('gps_unit',unit);
  window.location.href=url.toString();
}
</script>
<style>
@keyframes pulse-gold{0%,100%{opacity:1;box-shadow:0 0 8px #FFB300}50%{opacity:0.3;box-shadow:0 0 2px #FFB300}}
</style>
"""

# ─── AUTH PAGE ───────────────────────────────────────────────────
def auth_page():
    st.markdown("""
    <div style='text-align:center; padding:60px 0 30px;'>
        <div style='font-family:"Share Tech Mono",monospace; font-size:0.65rem; color:#5A4A2A; letter-spacing:6px; margin-bottom:16px;'>
            ◈ SYSTEM INITIALIZED ◈
        </div>
        <div style='font-family:"Orbitron",sans-serif; font-size:2.8rem; font-weight:900;
            background:linear-gradient(135deg,#FFD700,#FF8C00,#FFB300);
            -webkit-background-clip:text; -webkit-text-fill-color:transparent;
            background-clip:text; letter-spacing:6px; line-height:1;'>
            RUN<span style='-webkit-text-fill-color:#E8D5A3'>QUEST</span>
        </div>
        <div style='font-family:"Share Tech Mono",monospace; font-size:0.6rem; color:#5A4A2A; letter-spacing:8px; margin-top:8px;'>
            PERFORMANCE TRACKING SYSTEM v2.0
        </div>
        <div style='width:120px; height:1px; background:linear-gradient(90deg,transparent,#FFB300,transparent); margin:20px auto;'></div>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["ACCESS", "REGISTER"])
    with tab1:
        with st.form("login_form"):
            email = st.text_input("IDENTIFIER", placeholder="runner@domain.com")
            password = st.text_input("ACCESS CODE", type="password", placeholder="••••••••")
            submit = st.form_submit_button("▶ INITIALIZE SESSION", use_container_width=True)
            if submit:
                try:
                    res = sb.auth.sign_in_with_password({"email": email, "password": password})
                    st.session_state.user = res.user
                    st.session_state.session = res.session
                    st.rerun()
                except Exception as e:
                    st.error(f"ACCESS DENIED: {str(e)}")

    with tab2:
        with st.form("register_form"):
            email = st.text_input("IDENTIFIER", placeholder="runner@domain.com", key="reg_email")
            password = st.text_input("ACCESS CODE", type="password", placeholder="Min. 6 characters", key="reg_pass")
            submit = st.form_submit_button("◈ CREATE PROFILE", use_container_width=True)
            if submit:
                try:
                    sb.auth.sign_up({"email": email, "password": password})
                    st.success("◈ PROFILE CREATED — Check email to confirm access")
                except Exception as e:
                    st.error(f"ERROR: {str(e)}")

# ─── PAGES ───────────────────────────────────────────────────────
def page_dashboard(user_id, profile, runs, unit):
    xp = profile.get("xp", 0)
    rank = get_rank(xp)
    next_rank = get_next_rank(xp)
    progress = get_xp_progress(xp)

    st.markdown("<div class='cyber-page-title'>◈ COMMAND CENTER</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='cyber-subtitle'>OPERATIVE: {st.session_state.user.email.split('@')[0].upper()}</div>", unsafe_allow_html=True)
    st.markdown("<hr class='divider-cyber'>", unsafe_allow_html=True)

    # Rank card
    col1, col2 = st.columns([1, 3])
    with col1:
        st.markdown(f"<div style='font-size:3.5rem; text-align:center; filter:drop-shadow(0 0 8px #FFB300)'>{rank['icon']}</div>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"<div class='rank-chip'>LVL {rank['level']} // {rank['title'].upper()}</div>", unsafe_allow_html=True)
        st.markdown(f"""
        <div style='font-family:Orbitron,sans-serif; font-size:2rem; font-weight:900;
            background:linear-gradient(135deg,#FFD700,#FFB300);
            -webkit-background-clip:text; -webkit-text-fill-color:transparent;
            background-clip:text; margin-top:4px;'>
            {xp:,} <span style='font-size:1rem; -webkit-text-fill-color:#5A4A2A'>XP</span>
        </div>""", unsafe_allow_html=True)
        next_txt = f"▶ {next_rank['title'].upper()} @ {next_rank['min_xp']:,} XP" if next_rank else "◈ MAX RANK ACHIEVED"
        st.markdown(f"<div style='font-family:Share Tech Mono,monospace; font-size:0.65rem; color:#5A4A2A; letter-spacing:1px'>{next_txt}</div>", unsafe_allow_html=True)
        st.markdown(f"""
        <div class='xp-bar-outer'>
            <div class='xp-bar-inner' style='width:{progress}%'></div>
        </div>
        <div style='font-family:Share Tech Mono,monospace; font-size:0.6rem; color:#5A4A2A; letter-spacing:1px'>{progress}% CAPACITY</div>
        """, unsafe_allow_html=True)

    st.markdown("<hr class='divider-cyber'>", unsafe_allow_html=True)

    total_dist = sum(r["distance_km"] for r in runs)
    week_runs = [r for r in runs if is_this_week(r["started_at"])]
    week_dist = sum(r["distance_km"] for r in week_runs)
    week_time = sum(r["duration_seconds"] for r in week_runs)
    completed_count = sum(1 for q in QUESTS if check_quest(q["id"], runs))

    c1,c2,c3,c4 = st.columns(4)
    with c1: st.markdown(f"<div class='metric-card'><div class='metric-value'>{len(runs)}</div><div class='metric-label'>MISSIONS</div></div>", unsafe_allow_html=True)
    with c2: st.markdown(f"<div class='metric-card'><div class='metric-value'>{format_distance(total_dist,unit)}</div><div class='metric-label'>TOTAL {unit.upper()}</div></div>", unsafe_allow_html=True)
    with c3: st.markdown(f"<div class='metric-card'><div class='metric-value'>{format_distance(week_dist,unit)}</div><div class='metric-label'>THIS CYCLE</div></div>", unsafe_allow_html=True)
    with c4: st.markdown(f"<div class='metric-card'><div class='metric-value'>{completed_count}</div><div class='metric-label'>QUESTS DONE</div></div>", unsafe_allow_html=True)

    st.markdown("<hr class='divider-cyber'>", unsafe_allow_html=True)
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("<div style='font-family:Orbitron,sans-serif; font-size:0.75rem; font-weight:700; color:#FFB300; letter-spacing:3px; margin-bottom:12px;'>◈ ACTIVE MISSIONS</div>", unsafe_allow_html=True)
        active = [q for q in QUESTS if not check_quest(q["id"], runs)][:3]
        if not active:
            st.success("◈ ALL MISSIONS COMPLETE")
        for q in active:
            st.markdown(f"""
            <div class='quest-card'>
                <span style='font-size:1.2rem'>{q['icon']}</span>
                <span style='font-family:Orbitron,sans-serif; font-size:0.7rem; font-weight:700; color:#E8D5A3; letter-spacing:1px;'> {q['title'].upper()}</span>
                <span style='float:right; font-family:Orbitron,sans-serif; font-size:0.65rem; color:#FFB300; font-weight:700'>+{q['xp']}</span>
                <br><span style='font-family:Share Tech Mono,monospace; font-size:0.6rem; color:#5A4A2A; letter-spacing:1px'>{q['desc']}</span>
            </div>""", unsafe_allow_html=True)

    with col_b:
        st.markdown("<div style='font-family:Orbitron,sans-serif; font-size:0.75rem; font-weight:700; color:#FFB300; letter-spacing:3px; margin-bottom:12px;'>◈ LAST MISSION</div>", unsafe_allow_html=True)
        if not runs:
            st.info("[ NO MISSION DATA — INITIATE FIRST RUN ]")
        else:
            r = runs[0]
            d = format_distance(r["distance_km"], unit)
            t = format_time(r["duration_seconds"])
            p = format_pace(r["duration_seconds"], r["distance_km"], unit)
            pb = "<span class='pb-badge'>◈ PB</span> " if r.get("is_pb") else ""
            st.markdown(f"""
            <div class='run-card'>
                {pb}
                <div style='display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-top:8px'>
                    <div><div class='data-label'>DISTANCE</div><div class='data-val'>{d} {unit}</div></div>
                    <div><div class='data-label'>DURATION</div><div class='data-val'>{t}</div></div>
                    <div><div class='data-label'>AVG PACE</div><div class='data-val'>{p}/{unit}</div></div>
                    <div><div class='data-label'>XP GAINED</div><div class='data-val' style='color:#FFB300'>+{r.get("xp_earned",0)}</div></div>
                </div>
                <div style='margin-top:8px; font-family:Share Tech Mono,monospace; font-size:0.55rem; color:#3A3020'>{r["started_at"][:10]}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<hr class='divider-cyber'>", unsafe_allow_html=True)
    st.markdown("<div style='font-family:Orbitron,sans-serif; font-size:0.75rem; font-weight:700; color:#FFB300; letter-spacing:3px; margin-bottom:12px;'>◈ CYCLE REPORT</div>", unsafe_allow_html=True)
    w1,w2,w3 = st.columns(3)
    with w1: st.markdown(f"<div class='metric-card'><div class='metric-value'>{len(week_runs)}</div><div class='metric-label'>RUNS</div></div>", unsafe_allow_html=True)
    with w2: st.markdown(f"<div class='metric-card'><div class='metric-value'>{format_distance(week_dist,unit)}</div><div class='metric-label'>DISTANCE</div></div>", unsafe_allow_html=True)
    with w3: st.markdown(f"<div class='metric-card'><div class='metric-value'>{format_time(week_time)}</div><div class='metric-label'>TOTAL TIME</div></div>", unsafe_allow_html=True)


def page_gps_tracker(user_id, profile, runs, unit):
    st.markdown("<div class='cyber-page-title'>◈ GPS UPLINK</div>", unsafe_allow_html=True)
    st.markdown("<div class='cyber-subtitle'>REAL-TIME POSITION TRACKING</div>", unsafe_allow_html=True)
    st.warning("⚠ KEEP TAB ACTIVE — MAINTAIN SCREEN POWER — DO NOT LOCK DEVICE")

    params = st.query_params
    if "gps_dist" in params and "gps_dur" in params:
        try:
            dist_km = float(params["gps_dist"])
            duration = int(params["gps_dur"])
            gps_unit = params.get("gps_unit", "km")
            if gps_unit == "mi": dist_km = dist_km / 0.621371
            if dist_km > 0.01 and duration > 0:
                total_xp, is_pb, fresh_quests = process_and_save_run(user_id, profile, runs, dist_km, duration, unit)
                st.query_params.clear()
                st.success(f"◈ DATA UPLOADED — {format_distance(dist_km,unit)} {unit} // {format_time(duration)}")
                if is_pb: st.balloons(); st.success("◈ NEW PERSONAL RECORD LOGGED")
                st.info(f"⭐ +{total_xp} XP CREDITED")
                for q in fresh_quests:
                    st.success(f"◈ QUEST COMPLETE: {q['icon']} {q['title'].upper()} (+{q['xp']} XP)")
        except Exception as e:
            st.error(f"UPLOAD ERROR: {e}")
            st.query_params.clear()

    unit_sel = st.radio("UNIT SYSTEM", ["km", "mi"], horizontal=True, index=0 if unit == "km" else 1)
    gps_html = GPS_JS.replace("UNIT_PLACEHOLDER", unit_sel)
    st.components.v1.html(gps_html, height=560, scrolling=False)
    st.markdown("<hr class='divider-cyber'>", unsafe_allow_html=True)
    st.markdown("<div style='font-family:Share Tech Mono,monospace; font-size:0.6rem; color:#3A3020; letter-spacing:1px'>◈ OPTIMAL CONDITIONS: OUTDOOR ENVIRONMENT // GPS ACCURACY TARGET &lt;15m // MAINTAIN DEVICE IN HAND OR ARM MOUNT</div>", unsafe_allow_html=True)


def page_log_run(user_id, profile, runs, unit):
    st.markdown("<div class='cyber-page-title'>◈ MANUAL ENTRY</div>", unsafe_allow_html=True)
    st.markdown("<div class='cyber-subtitle'>LOG RUN DATA FROM EXTERNAL DEVICE</div>", unsafe_allow_html=True)

    with st.form("log_run_form"):
        col1, col2 = st.columns(2)
        with col1: distance = st.number_input("DISTANCE", min_value=0.1, max_value=200.0, step=0.1, value=5.0)
        with col2: unit_sel = st.selectbox("UNIT", ["km", "mi"], index=0 if unit == "km" else 1)
        col3,col4,col5 = st.columns(3)
        with col3: hours = st.number_input("HH", min_value=0, max_value=24, value=0)
        with col4: minutes = st.number_input("MM", min_value=0, max_value=59, value=30)
        with col5: seconds = st.number_input("SS", min_value=0, max_value=59, value=0)
        submitted = st.form_submit_button("◈ UPLOAD DATA", use_container_width=True)
        if submitted:
            dist_km = distance if unit_sel == "km" else distance / 0.621371
            total_seconds = hours*3600 + minutes*60 + seconds
            if total_seconds == 0:
                st.error("[ ERROR: INVALID DURATION ]")
            else:
                total_xp, is_pb, fresh_quests = process_and_save_run(user_id, profile, runs, dist_km, total_seconds, unit_sel)
                pace = format_pace(total_seconds, dist_km, unit_sel)
                st.success(f"◈ DATA LOGGED — {distance} {unit_sel} // {format_time(total_seconds)} // PACE {pace}/{unit_sel}")
                if is_pb: st.balloons(); st.success("◈ NEW PERSONAL RECORD")
                st.info(f"⭐ +{total_xp} XP CREDITED")
                for q in fresh_quests:
                    st.success(f"◈ QUEST UNLOCKED: {q['icon']} {q['title'].upper()} (+{q['xp']} XP)")
                st.rerun()


def page_history(user_id, runs, unit):
    st.markdown("<div class='cyber-page-title'>◈ MISSION LOG</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='cyber-subtitle'>{len(runs)} RECORDS IN DATABASE</div>", unsafe_allow_html=True)
    if not runs:
        st.info("[ NO RECORDS FOUND — INITIATE FIRST MISSION ]")
        return
    unit_sel = st.radio("UNIT", ["km", "mi"], horizontal=True, index=0 if unit == "km" else 1)
    for r in runs:
        d = format_distance(r["distance_km"], unit_sel)
        t = format_time(r["duration_seconds"])
        p = format_pace(r["duration_seconds"], r["distance_km"], unit_sel)
        pb = "<span class='pb-badge'>◈ PB</span> " if r.get("is_pb") else ""
        col1, col2 = st.columns([5,1])
        with col1:
            st.markdown(f"""
            <div class='run-card'>
                <div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:8px'>
                    <span style='font-family:Share Tech Mono,monospace; font-size:0.6rem; color:#3A3020; letter-spacing:1px'>{r["started_at"][:10]}</span>
                    <span>{pb}<span style='font-family:Orbitron,sans-serif; font-size:0.65rem; color:#FFB300; font-weight:700'>+{r.get("xp_earned",0)} XP</span></span>
                </div>
                <div style='display:grid; grid-template-columns:1fr 1fr 1fr; gap:8px'>
                    <div><div class='data-label'>DISTANCE</div><div class='data-val'>{d} {unit_sel}</div></div>
                    <div><div class='data-label'>TIME</div><div class='data-val'>{t}</div></div>
                    <div><div class='data-label'>PACE</div><div class='data-val'>{p}/{unit_sel}</div></div>
                </div>
            </div>""", unsafe_allow_html=True)
        with col2:
            if st.button("✕", key=f"del_{r['id']}"):
                delete_run(r["id"]); st.rerun()


def page_quests(user_id, profile, runs):
    st.markdown("<div class='cyber-page-title'>◈ MISSION BOARD</div>", unsafe_allow_html=True)
    xp = profile.get("xp", 0)
    rank = get_rank(xp); next_rank = get_next_rank(xp); progress = get_xp_progress(xp)
    completed_ids = set(q["id"] for q in QUESTS if check_quest(q["id"], runs))
    completed = [q for q in QUESTS if q["id"] in completed_ids]
    pending = [q for q in QUESTS if q["id"] not in completed_ids]

    st.markdown("<div style='font-family:Orbitron,sans-serif; font-size:0.75rem; font-weight:700; color:#FFB300; letter-spacing:3px; margin-bottom:12px;'>◈ RANK PROGRESSION</div>", unsafe_allow_html=True)
    cols = st.columns(len(RANKS))
    for i, r in enumerate(RANKS):
        unlocked = xp >= r["min_xp"]
        is_current = r["level"] == rank["level"]
        with cols[i]:
            st.markdown(f"""
            <div style='text-align:center; padding:10px 4px; border-radius:4px;
                border:2px solid {"#FFB300" if is_current else "#FFB30020"};
                background:{"rgba(255,179,0,0.08)" if is_current else "transparent"};
                opacity:{"1" if unlocked else "0.25"};
                box-shadow:{"0 0 12px rgba(255,179,0,0.2)" if is_current else "none"}'>
                <div style='font-size:1.2rem'>{r['icon']}</div>
                <div style='font-family:Orbitron,sans-serif; font-size:0.5rem; font-weight:700;
                    color:{"#FFB300" if is_current else "#5A4A2A"}; letter-spacing:0.5px; margin-top:2px'>{r['title'][:4].upper()}</div>
                {"<div style='font-size:0.5rem; color:#FFB300; font-family:Share Tech Mono,monospace'>◈YOU</div>" if is_current else ""}
            </div>""", unsafe_allow_html=True)

    st.markdown(f"""
    <div style='margin-top:16px'>
        <div style='display:flex; justify-content:space-between; font-family:Share Tech Mono,monospace; font-size:0.65rem; color:#5A4A2A; margin-bottom:6px; letter-spacing:1px'>
            <span>{rank['icon']} {rank['title'].upper()} — {xp:,} XP</span>
            <span>{"▶ " + next_rank['title'].upper() if next_rank else "◈ APEX REACHED"}</span>
        </div>
        <div class='xp-bar-outer'>
            <div class='xp-bar-inner' style='width:{progress}%'></div>
        </div>
        <div style='font-family:Share Tech Mono,monospace; font-size:0.6rem; color:#3A3020; letter-spacing:1px'>
            {progress}% — {str(next_rank["min_xp"] - xp) + " XP TO NEXT RANK" if next_rank else "◈ TRANSCENDENT ACHIEVED"}
        </div>
    </div>""", unsafe_allow_html=True)

    st.markdown("<hr class='divider-cyber'>", unsafe_allow_html=True)
    if pending:
        st.markdown(f"<div style='font-family:Orbitron,sans-serif; font-size:0.75rem; font-weight:700; color:#FFB300; letter-spacing:3px; margin-bottom:12px;'>◈ ACTIVE MISSIONS [{len(pending)}]</div>", unsafe_allow_html=True)
        for q in pending:
            st.markdown(f"""
            <div class='quest-card'>
                <span style='font-size:1.3rem'>{q['icon']}</span>
                <span style='font-family:Orbitron,sans-serif; font-size:0.7rem; font-weight:700; color:#E8D5A3; letter-spacing:1px'> {q['title'].upper()}</span>
                <span style='float:right; background:rgba(255,179,0,0.1); color:#FFB300; border:1px solid rgba(255,179,0,0.3); border-radius:2px; padding:2px 10px; font-family:Orbitron,sans-serif; font-size:0.6rem; font-weight:700'>+{q['xp']} XP</span>
                <br><span style='font-family:Share Tech Mono,monospace; font-size:0.6rem; color:#5A4A2A; letter-spacing:1px'>{q['desc']}</span>
            </div>""", unsafe_allow_html=True)

    if completed:
        st.markdown(f"<div style='font-family:Orbitron,sans-serif; font-size:0.75rem; font-weight:700; color:#FFB300; letter-spacing:3px; margin:16px 0 12px;'>◈ COMPLETED [{len(completed)}]</div>", unsafe_allow_html=True)
        cols = st.columns(2)
        for i, q in enumerate(completed):
            with cols[i % 2]:
                st.markdown(f"""
                <div class='quest-done'>
                    <span style='font-size:1.1rem'>{q['icon']}</span>
                    <span style='font-family:Orbitron,sans-serif; font-size:0.65rem; font-weight:700; color:#E8D5A3'> {q['title'].upper()}</span>
                    <span style='float:right'>✅</span>
                    <br><span style='font-family:Share Tech Mono,monospace; font-size:0.6rem; color:#FFB30080'>+{q['xp']} XP CREDITED</span>
                </div>""", unsafe_allow_html=True)


def page_stats(user_id, runs, unit):
    st.markdown("<div class='cyber-page-title'>◈ DATA ANALYSIS</div>", unsafe_allow_html=True)
    if not runs:
        st.info("[ INSUFFICIENT DATA — COMPLETE MISSIONS TO POPULATE ]")
        return

    unit_sel = st.radio("UNIT", ["km", "mi"], horizontal=True, index=0 if unit == "km" else 1)
    runs_asc = list(reversed(runs))
    total_dist = sum(r["distance_km"] for r in runs)
    total_time = sum(r["duration_seconds"] for r in runs)
    avg_pace = (total_time/60)/total_dist if total_dist else 0
    best_pace = min((r["duration_seconds"]/60/r["distance_km"]) for r in runs if r["distance_km"] > 0)

    c1,c2,c3,c4 = st.columns(4)
    with c1: st.metric("MISSIONS", len(runs))
    with c2: st.metric(f"TOTAL {unit_sel.upper()}", format_distance(total_dist, unit_sel))
    with c3: st.metric("AVG PACE", f"{format_pace(int(avg_pace*60),1,unit_sel)}/{unit_sel}")
    with c4: st.metric("BEST PACE", f"{format_pace(int(best_pace*60),1,unit_sel)}/{unit_sel}")

    st.markdown("<hr class='divider-cyber'>", unsafe_allow_html=True)

    chart_pace = {}; chart_dist = {}; chart_xp = {}
    for r in runs_asc:
        date = r["started_at"][:10]
        pv = (r["duration_seconds"]/60)/r["distance_km"]
        if unit_sel == 'mi': pv = pv/1.60934
        chart_pace[date] = round(pv, 2)
        chart_dist[date] = float(format_distance(r["distance_km"], unit_sel))
        chart_xp[date] = r.get("xp_earned", 0)

    tab1,tab2,tab3 = st.tabs(["⚡ PACE TREND", "🗺 DISTANCE", "⭐ XP LOG"])
    with tab1: st.line_chart(chart_pace)
    with tab2: st.bar_chart(chart_dist)
    with tab3: st.bar_chart(chart_xp)

    st.markdown("<hr class='divider-cyber'>", unsafe_allow_html=True)
    st.markdown("<div style='font-family:Orbitron,sans-serif; font-size:0.75rem; font-weight:700; color:#FFB300; letter-spacing:3px; margin-bottom:12px'>◈ PERSONAL RECORDS</div>", unsafe_allow_html=True)
    pb_distances = [1,3,5,10,21.1,42.2]
    pb_labels = {1:"1KM",3:"3KM",5:"5KM",10:"10KM",21.1:"HALF MARATHON",42.2:"FULL MARATHON"}
    pb_cols = st.columns(3); found = 0
    for dist in pb_distances:
        relevant = [r for r in runs if abs(r["distance_km"]-dist) < 0.2]
        if relevant:
            pb = min(relevant, key=lambda r: r["duration_seconds"])
            with pb_cols[found%3]:
                st.markdown(f"""
                <div style='background:#0D1117; border:1px solid rgba(255,179,0,0.2);
                    border-top:2px solid #FFB300; border-radius:4px; padding:14px;
                    text-align:center; margin-bottom:10px'>
                    <div style='font-family:Orbitron,sans-serif; font-size:0.65rem; color:#FFB300; font-weight:700; letter-spacing:2px'>{pb_labels[dist]}</div>
                    <div style='font-family:Orbitron,sans-serif; font-size:1.3rem; font-weight:800; color:#E8D5A3; margin-top:6px'>{format_time(pb["duration_seconds"])}</div>
                    <div style='font-family:Share Tech Mono,monospace; font-size:0.6rem; color:#5A4A2A; margin-top:4px'>{format_pace(pb["duration_seconds"],pb["distance_km"],unit_sel)}/{unit_sel}</div>
                </div>""", unsafe_allow_html=True)
            found += 1
    if found == 0:
        st.markdown("<div style='font-family:Share Tech Mono,monospace; font-size:0.65rem; color:#3A3020'>[ NO RECORDS — COMPLETE STANDARD DISTANCE MISSIONS ]</div>", unsafe_allow_html=True)


def page_settings(user_id, profile):
    st.markdown("<div class='cyber-page-title'>◈ SYSTEM CONFIG</div>", unsafe_allow_html=True)
    with st.form("settings_form"):
        st.markdown("<div style='font-family:Orbitron,sans-serif; font-size:0.7rem; color:#FFB300; letter-spacing:2px; margin-bottom:8px'>DISPLAY MODE</div>", unsafe_allow_html=True)
        theme = st.selectbox("", ["Dark Cyber (Default)", "Light Mode"],
                             index=0 if st.session_state.get("theme","Dark") == "Dark" else 1, label_visibility="collapsed")
        st.markdown("<div style='font-family:Orbitron,sans-serif; font-size:0.7rem; color:#FFB300; letter-spacing:2px; margin:16px 0 8px'>UNIT SYSTEM</div>", unsafe_allow_html=True)
        unit = st.radio("", ["km", "mi"], horizontal=True,
                        index=0 if profile.get("unit","km")=="km" else 1, label_visibility="collapsed")
        st.markdown("<div style='font-family:Orbitron,sans-serif; font-size:0.7rem; color:#FFB300; letter-spacing:2px; margin:16px 0 8px'>OPERATIVE ID</div>", unsafe_allow_html=True)
        st.text_input("", value=st.session_state.user.email, disabled=True, label_visibility="collapsed")
        saved = st.form_submit_button("◈ APPLY CONFIGURATION", use_container_width=True)
        if saved:
            st.session_state.theme = "Dark" if "Dark" in theme else "Light"
            update_profile(user_id, profile.get("xp",0), profile.get("completed_quests",[]), unit)
            st.success("◈ CONFIGURATION UPDATED")
            st.rerun()

# ─── MAIN ────────────────────────────────────────────────────────
def main():
    if "user" not in st.session_state: st.session_state.user = None
    if "theme" not in st.session_state: st.session_state.theme = "Dark"
    if "accent" not in st.session_state: st.session_state.accent = "#FFB300"
    if "font" not in st.session_state: st.session_state.font = "Orbitron"

    apply_theme()

    if not st.session_state.user:
        auth_page()
        return

    user_id = st.session_state.user.id
    profile = get_profile(user_id)
    runs = get_runs(user_id)
    unit = profile.get("unit", "km")

    with st.sidebar:
        # Cyber Logo
        st.markdown("""
        <div style='padding:8px 0 16px'>
            <div style='font-family:Share Tech Mono,monospace; font-size:0.55rem; color:#3A3020; letter-spacing:4px; margin-bottom:6px'>◈ SYSTEM ACTIVE</div>
            <div class='cyber-logo'>RUN<span style='background:none; -webkit-text-fill-color:#E8D5A3'>QUEST</span></div>
            <div class='cyber-logo-sub'>PERFORMANCE OS v2.0</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='height:1px; background:linear-gradient(90deg,transparent,#FFB30040,transparent); margin-bottom:16px'></div>", unsafe_allow_html=True)

        st.markdown("<div class='nav-label'>◈ NAVIGATION</div>", unsafe_allow_html=True)
        page = st.radio("", [
            "⚡ Dashboard",
            "📍 GPS Tracker",
            "✍️ Manual Log",
            "📋 History",
            "🎯 Quests",
            "📈 Stats",
            "⚙️ Settings",
        ], label_visibility="collapsed")

        st.markdown("<div style='height:1px; background:linear-gradient(90deg,transparent,#FFB30040,transparent); margin:16px 0'></div>", unsafe_allow_html=True)

        xp = profile.get("xp", 0)
        rank = get_rank(xp)
        progress = get_xp_progress(xp)
        st.markdown(f"""
        <div style='font-family:Share Tech Mono,monospace; font-size:0.6rem; color:#5A4A2A; margin-bottom:4px; letter-spacing:1px'>
            {rank['icon']} {rank['title'].upper()} // LV.{rank['level']}
        </div>
        <div class='xp-bar-outer'>
            <div class='xp-bar-inner' style='width:{progress}%'></div>
        </div>
        <div style='font-family:Share Tech Mono,monospace; font-size:0.6rem; color:#3A3020; margin-top:4px; letter-spacing:1px'>
            {xp:,} XP TOTAL
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='height:1px; background:linear-gradient(90deg,transparent,#FFB30040,transparent); margin:16px 0'></div>", unsafe_allow_html=True)

        if st.button("⏻  TERMINATE SESSION", use_container_width=True):
            sb.auth.sign_out()
            st.session_state.user = None
            st.rerun()

    if page == "⚡ Dashboard": page_dashboard(user_id, profile, runs, unit)
    elif page == "📍 GPS Tracker": page_gps_tracker(user_id, profile, runs, unit)
    elif page == "✍️ Manual Log": page_log_run(user_id, profile, runs, unit)
    elif page == "📋 History": page_history(user_id, runs, unit)
    elif page == "🎯 Quests": page_quests(user_id, profile, runs)
    elif page == "📈 Stats": page_stats(user_id, runs, unit)
    elif page == "⚙️ Settings": page_settings(user_id, profile)

if __name__ == "__main__":
    main()
