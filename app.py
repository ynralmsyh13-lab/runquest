import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timedelta

# ─── PAGE CONFIG ────────────────────────────────────────────────
st.set_page_config(
    page_title="RunQuest",
    page_icon="🏃",
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
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

def format_pace(seconds, distance_km, unit='km'):
    if not distance_km or distance_km == 0: return "--:--"
    pace = (seconds / 60) / distance_km
    if unit == 'mi':
        pace = pace / 1.60934
    m = int(pace)
    s = int((pace - m) * 60)
    return f"{m}:{s:02d}"

def format_distance(km, unit='km'):
    if unit == 'mi':
        return round(km * 0.621371, 2)
    return round(km, 2)

def is_this_week(date_str):
    try:
        d = datetime.fromisoformat(date_str.replace('Z', '+00:00')).replace(tzinfo=None)
        today = datetime.utcnow()
        start = today - timedelta(days=today.weekday())
        start = start.replace(hour=0, minute=0, second=0)
        return d >= start
    except:
        return False

# ─── RPG SYSTEM ─────────────────────────────────────────────────
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
    {"id": "first_run",     "title": "First Step",        "desc": "Complete your very first run",        "icon": "👟", "xp": 50},
    {"id": "run_5km",       "title": "Five Kilometers",   "desc": "Run 5km in a single session",         "icon": "🎯", "xp": 75},
    {"id": "run_10km",      "title": "Double Digits",     "desc": "Run 10km in a single session",        "icon": "🏅", "xp": 150},
    {"id": "run_3_times",   "title": "Habit Forming",     "desc": "Complete 3 runs total",               "icon": "🔄", "xp": 60},
    {"id": "run_7_times",   "title": "Weekly Warrior",    "desc": "Complete 7 runs total",               "icon": "⚔️", "xp": 120},
    {"id": "sub_6_pace",    "title": "Speed Seeker",      "desc": "Run a pace under 6:00 min/km",        "icon": "⚡", "xp": 80},
    {"id": "sub_5_pace",    "title": "Lightning Legs",    "desc": "Run a pace under 5:00 min/km",        "icon": "🌩️", "xp": 200},
    {"id": "total_50km",    "title": "Fifty and Counting","desc": "Accumulate 50km total distance",       "icon": "🗺️", "xp": 200},
    {"id": "total_100km",   "title": "Century Runner",    "desc": "Accumulate 100km total distance",     "icon": "💯", "xp": 400},
    {"id": "half_marathon", "title": "Half the Glory",    "desc": "Complete a half marathon (21.1km)",   "icon": "🎖️", "xp": 300},
    {"id": "full_marathon", "title": "Marathon Legend",   "desc": "Complete a full marathon (42.2km)",   "icon": "🏆", "xp": 1000},
    {"id": "run_streak_3",  "title": "On a Roll",         "desc": "Run 3 days in a row",                 "icon": "🔥", "xp": 100},
    {"id": "run_streak_7",  "title": "Unstoppable",       "desc": "Run 7 days in a row",                 "icon": "💥", "xp": 250},
]

def get_rank(xp):
    rank = RANKS[0]
    for r in RANKS:
        if xp >= r["min_xp"]:
            rank = r
    return rank

def get_next_rank(xp):
    current = get_rank(xp)
    for r in RANKS:
        if r["level"] == current["level"] + 1:
            return r
    return None

def get_xp_progress(xp):
    current = get_rank(xp)
    next_r = get_next_rank(xp)
    if not next_r:
        return 100
    rng = next_r["min_xp"] - current["min_xp"]
    earned = xp - current["min_xp"]
    return min(100, int((earned / rng) * 100))

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
        else:
            streak = 1
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

# ─── SUPABASE DB HELPERS ─────────────────────────────────────────
def get_profile(user_id):
    res = sb.table("profiles").select("*").eq("id", user_id).execute()
    if res.data:
        return res.data[0]
    sb.table("profiles").insert({"id": user_id, "xp": 0, "unit": "km", "completed_quests": []}).execute()
    return {"id": user_id, "xp": 0, "unit": "km", "completed_quests": []}

def get_runs(user_id):
    res = sb.table("runs").select("*").eq("user_id", user_id).order("started_at", desc=True).execute()
    return res.data or []

def save_run(user_id, distance_km, duration_seconds, xp_earned, is_pb):
    sb.table("runs").insert({
        "user_id": user_id,
        "distance_km": distance_km,
        "duration_seconds": duration_seconds,
        "xp_earned": xp_earned,
        "is_pb": is_pb,
        "started_at": datetime.utcnow().isoformat()
    }).execute()

def update_profile(user_id, xp, completed_quests, unit):
    sb.table("profiles").upsert({
        "id": user_id,
        "xp": xp,
        "completed_quests": completed_quests,
        "unit": unit
    }).execute()

def delete_run(run_id):
    sb.table("runs").delete().eq("id", run_id).execute()

def process_and_save_run(user_id, profile, runs, dist_km, total_seconds, unit_sel):
    """Shared logic for saving a run and checking quests/PBs."""
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

    new_xp = profile.get("xp", 0) + xp + quest_xp
    update_profile(user_id, new_xp, now_completed, unit_sel)
    return xp + quest_xp, is_pb, fresh_quests

# ─── THEME CSS ───────────────────────────────────────────────────
def apply_theme(theme, accent, font):
    if theme == "Dark":
        bg = "#0A0C10"; card = "#1A1F2E"; text = "#E8EAF0"; secondary = "#8892A4"; border = "#2A3148"
    else:
        bg = "#F0F4F8"; card = "#FFFFFF"; text = "#1A202C"; secondary = "#4A5568"; border = "#E2E8F0"

    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Exo+2:wght@400;600;800&family=Rajdhani:wght@600;700&family=JetBrains+Mono:wght@400;600&display=swap');
    html, body, [class*="css"] {{
        font-family: '{font}', sans-serif !important;
        background-color: {bg} !important;
        color: {text} !important;
    }}
    .stApp {{ background-color: {bg} !important; }}
    section[data-testid="stSidebar"] {{
        background-color: {card} !important;
        border-right: 1px solid {border} !important;
    }}
    .stButton > button {{
        font-family: '{font}', sans-serif !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        transition: all 0.2s !important;
    }}
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input {{
        background: {card} !important;
        color: {text} !important;
        border: 1px solid {border} !important;
        border-radius: 8px !important;
        font-family: '{font}', sans-serif !important;
    }}
    .metric-card {{
        background: {card};
        border: 1px solid {border};
        border-radius: 12px;
        padding: 20px;
        text-align: center;
    }}
    .metric-value {{
        font-family: 'Rajdhani', sans-serif;
        font-size: 2rem;
        font-weight: 800;
        color: {accent};
        line-height: 1.1;
    }}
    .metric-label {{
        font-size: 0.75rem;
        color: {secondary};
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-top: 4px;
    }}
    .gps-metric {{
        background: {card};
        border: 1px solid {border};
        border-radius: 12px;
        padding: 20px;
        text-align: center;
    }}
    .gps-value {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 2.8rem;
        font-weight: 800;
        color: {accent};
        line-height: 1;
    }}
    .gps-label {{
        font-size: 0.7rem;
        color: {secondary};
        text-transform: uppercase;
        letter-spacing: 2px;
        margin-top: 6px;
    }}
    .run-card {{
        background: {card};
        border: 1px solid {border};
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 10px;
    }}
    .quest-card {{
        background: {card};
        border: 1px solid {border};
        border-radius: 10px;
        padding: 14px 18px;
        margin-bottom: 8px;
    }}
    .quest-done {{
        background: {'rgba(0,245,160,0.05)' if theme=='Dark' else 'rgba(56,161,105,0.05)'};
        border: 1px solid {'rgba(0,245,160,0.2)' if theme=='Dark' else 'rgba(56,161,105,0.2)'};
        border-radius: 10px;
        padding: 12px 16px;
        margin-bottom: 8px;
    }}
    .xp-bar-outer {{
        background: {border};
        border-radius: 99px;
        height: 10px;
        overflow: hidden;
        margin: 8px 0;
    }}
    .rank-chip {{
        display: inline-block;
        padding: 3px 12px;
        border-radius: 99px;
        font-size: 0.75rem;
        font-weight: 700;
        background: {'rgba(0,245,160,0.1)' if theme=='Dark' else 'rgba(0,102,255,0.1)'};
        color: {accent};
        border: 1px solid {accent}40;
    }}
    .pb-badge {{
        display: inline-block;
        padding: 2px 10px;
        border-radius: 99px;
        font-size: 0.7rem;
        font-weight: 700;
        background: rgba(255,215,0,0.15);
        color: #FFD700;
        border: 1px solid rgba(255,215,0,0.3);
    }}
    .logo-text {{
        font-family: 'Rajdhani', sans-serif;
        font-size: 1.8rem;
        font-weight: 700;
        letter-spacing: 2px;
        color: {text};
    }}
    .logo-accent {{ color: {accent}; }}
    .live-dot {{
        display: inline-block;
        width: 10px; height: 10px;
        border-radius: 50%;
        background: #00F5A0;
        animation: pulse 1.5s ease-in-out infinite;
        margin-right: 6px;
    }}
    @keyframes pulse {{
        0%, 100% {{ opacity: 1; transform: scale(1); }}
        50% {{ opacity: 0.4; transform: scale(0.8); }}
    }}
    </style>
    """, unsafe_allow_html=True)

# ─── GPS TRACKER COMPONENT ───────────────────────────────────────
GPS_JS = """
<div id="gps-tracker" style="font-family: 'JetBrains Mono', monospace;">

  <!-- Wake Lock warning -->
  <div id="wakelock-tip" style="
    background: rgba(255,215,0,0.1); border: 1px solid rgba(255,215,0,0.3);
    border-radius: 8px; padding: 10px 14px; margin-bottom: 16px;
    font-size: 0.8rem; color: #FFD700; display: none;">
    ⚠️ Keep your screen on and this tab active while running!
  </div>

  <!-- Big metrics display -->
  <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; margin-bottom: 20px;">
    <div style="background:#1A1F2E; border:1px solid #2A3148; border-radius:12px; padding:20px; text-align:center;">
      <div id="dist-display" style="font-size:2.4rem; font-weight:800; color:#00F5A0; line-height:1;">0.00</div>
      <div id="dist-unit" style="font-size:0.7rem; color:#8892A4; text-transform:uppercase; letter-spacing:2px; margin-top:4px;">KM</div>
    </div>
    <div style="background:#1A1F2E; border:1px solid #2A3148; border-radius:12px; padding:20px; text-align:center;">
      <div id="time-display" style="font-size:2.4rem; font-weight:800; color:#E8EAF0; line-height:1;">00:00</div>
      <div style="font-size:0.7rem; color:#8892A4; text-transform:uppercase; letter-spacing:2px; margin-top:4px;">TIME</div>
    </div>
    <div style="background:#1A1F2E; border:1px solid #2A3148; border-radius:12px; padding:20px; text-align:center;">
      <div id="pace-display" style="font-size:2.4rem; font-weight:800; color:#E8EAF0; line-height:1;">--:--</div>
      <div id="pace-unit" style="font-size:0.7rem; color:#8892A4; text-transform:uppercase; letter-spacing:2px; margin-top:4px;">MIN/KM</div>
    </div>
  </div>

  <!-- Status -->
  <div id="status-bar" style="text-align:center; margin-bottom:16px; font-size:0.85rem; color:#8892A4;">
    Press START to begin GPS tracking
  </div>

  <!-- GPS accuracy -->
  <div id="accuracy-bar" style="text-align:center; margin-bottom:16px; font-size:0.75rem; color:#4A5568; display:none;">
    📡 GPS Accuracy: <span id="accuracy-val">--</span>m
  </div>

  <!-- Control buttons -->
  <div style="display:flex; gap:10px; margin-bottom:16px;">
    <button id="btn-start" onclick="startTracking()" style="
      flex:1; padding:16px; border-radius:8px; border:none; cursor:pointer;
      background:#00F5A0; color:#000; font-size:1rem; font-weight:700;
      font-family:'JetBrains Mono',monospace; letter-spacing:1px;">
      ▶ START
    </button>
    <button id="btn-pause" onclick="pauseTracking()" style="
      flex:1; padding:16px; border-radius:8px; border:none; cursor:pointer;
      background:#1A1F2E; color:#FFD700; border:1px solid #FFD700;
      font-size:1rem; font-weight:700; font-family:'JetBrains Mono',monospace;
      display:none;">
      ⏸ PAUSE
    </button>
    <button id="btn-resume" onclick="resumeTracking()" style="
      flex:1; padding:16px; border-radius:8px; border:none; cursor:pointer;
      background:#00F5A0; color:#000; font-size:1rem; font-weight:700;
      font-family:'JetBrains Mono',monospace; display:none;">
      ▶ RESUME
    </button>
    <button id="btn-stop" onclick="stopTracking()" style="
      flex:1; padding:16px; border-radius:8px; border:none; cursor:pointer;
      background:#FF4757; color:#fff; font-size:1rem; font-weight:700;
      font-family:'JetBrains Mono',monospace; display:none;">
      ⏹ STOP
    </button>
  </div>

  <!-- Hidden inputs to pass data back to Streamlit -->
  <input type="hidden" id="final-distance" value="0">
  <input type="hidden" id="final-duration" value="0">

  <!-- Save button (shown after stop) -->
  <button id="btn-save" onclick="saveRun()" style="
    width:100%; padding:16px; border-radius:8px; border:none; cursor:pointer;
    background:#00F5A0; color:#000; font-size:1rem; font-weight:700;
    font-family:'JetBrains Mono',monospace; display:none; margin-top:8px;">
    💾 SAVE RUN
  </button>

  <!-- Save form (hidden, submitted programmatically) -->
  <div id="save-section" style="display:none; margin-top:16px;
    background:#1A1F2E; border:1px solid #2A3148; border-radius:12px; padding:20px;">
    <div style="font-size:0.85rem; color:#8892A4; margin-bottom:12px;">📋 Run Summary</div>
    <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
      <div style="text-align:center;">
        <div style="font-size:0.65rem; color:#4A5568; text-transform:uppercase; letter-spacing:1px;">Distance</div>
        <div id="summary-dist" style="font-size:1.4rem; font-weight:800; color:#00F5A0;"></div>
      </div>
      <div style="text-align:center;">
        <div style="font-size:0.65rem; color:#4A5568; text-transform:uppercase; letter-spacing:1px;">Time</div>
        <div id="summary-time" style="font-size:1.4rem; font-weight:800; color:#E8EAF0;"></div>
      </div>
      <div style="text-align:center;">
        <div style="font-size:0.65rem; color:#4A5568; text-transform:uppercase; letter-spacing:1px;">Avg Pace</div>
        <div id="summary-pace" style="font-size:1.4rem; font-weight:800; color:#E8EAF0;"></div>
      </div>
      <div style="text-align:center;">
        <div style="font-size:0.65rem; color:#4A5568; text-transform:uppercase; letter-spacing:1px;">Status</div>
        <div style="font-size:1.4rem; font-weight:800; color:#FFD700;">Ready</div>
      </div>
    </div>
  </div>
</div>

<script>
var watchId = null;
var timerInterval = null;
var lastPos = null;
var totalDistance = 0;
var elapsedSeconds = 0;
var isPaused = false;
var isRunning = false;
var wakeLock = null;
var unit = 'UNIT_PLACEHOLDER';

function haversine(lat1, lon1, lat2, lon2) {
  var R = 6371;
  var dLat = (lat2 - lat1) * Math.PI / 180;
  var dLon = (lon2 - lon1) * Math.PI / 180;
  var a = Math.sin(dLat/2) * Math.sin(dLat/2) +
          Math.cos(lat1 * Math.PI/180) * Math.cos(lat2 * Math.PI/180) *
          Math.sin(dLon/2) * Math.sin(dLon/2);
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
}

function formatTime(s) {
  var h = Math.floor(s / 3600);
  var m = Math.floor((s % 3600) / 60);
  var sec = s % 60;
  if (h > 0) return h + ':' + String(m).padStart(2,'0') + ':' + String(sec).padStart(2,'0');
  return String(m).padStart(2,'0') + ':' + String(sec).padStart(2,'0');
}

function formatPace(seconds, distKm) {
  if (distKm < 0.01) return '--:--';
  var pace = (seconds / 60) / distKm;
  if (unit === 'mi') pace = pace / 1.60934;
  var m = Math.floor(pace);
  var s = Math.round((pace - m) * 60);
  return m + ':' + String(s).padStart(2,'0');
}

function formatDist(km) {
  if (unit === 'mi') return (km * 0.621371).toFixed(2);
  return km.toFixed(2);
}

async function requestWakeLock() {
  try {
    if ('wakeLock' in navigator) {
      wakeLock = await navigator.wakeLock.request('screen');
    }
  } catch(e) {
    document.getElementById('wakelock-tip').style.display = 'block';
  }
}

function releaseWakeLock() {
  if (wakeLock) { wakeLock.release(); wakeLock = null; }
}

function startTracking() {
  if (!navigator.geolocation) {
    document.getElementById('status-bar').innerHTML =
      '<span style="color:#FF4757">❌ GPS not supported on this device</span>';
    return;
  }

  totalDistance = 0;
  elapsedSeconds = 0;
  lastPos = null;
  isPaused = false;
  isRunning = true;

  document.getElementById('btn-start').style.display = 'none';
  document.getElementById('btn-pause').style.display = 'flex';
  document.getElementById('btn-stop').style.display = 'flex';
  document.getElementById('btn-save').style.display = 'none';
  document.getElementById('save-section').style.display = 'none';
  document.getElementById('accuracy-bar').style.display = 'block';
  document.getElementById('status-bar').innerHTML =
    '<span class="live-dot"></span><span style="color:#00F5A0">TRACKING LIVE</span>';

  requestWakeLock();

  // Start timer
  timerInterval = setInterval(function() {
    if (!isPaused) {
      elapsedSeconds++;
      document.getElementById('time-display').textContent = formatTime(elapsedSeconds);
      document.getElementById('pace-display').textContent = formatPace(elapsedSeconds, totalDistance);
    }
  }, 1000);

  // Start GPS
  watchId = navigator.geolocation.watchPosition(
    function(pos) {
      var acc = Math.round(pos.coords.accuracy);
      document.getElementById('accuracy-val').textContent = acc;
      var color = acc < 15 ? '#00F5A0' : acc < 30 ? '#FFD700' : '#FF4757';
      document.getElementById('accuracy-val').style.color = color;

      if (!isPaused) {
        var newPos = { lat: pos.coords.latitude, lon: pos.coords.longitude };
        if (lastPos) {
          var d = haversine(lastPos.lat, lastPos.lon, newPos.lat, newPos.lon);
          if (d < 0.3 && d > 0.002) {
            totalDistance += d;
            document.getElementById('dist-display').textContent = formatDist(totalDistance);
            document.getElementById('dist-unit').textContent = unit.toUpperCase();
            document.getElementById('pace-unit').textContent = 'MIN/' + unit.toUpperCase();
          }
        }
        lastPos = newPos;
      }
    },
    function(err) {
      document.getElementById('status-bar').innerHTML =
        '<span style="color:#FF4757">❌ GPS Error: ' + err.message + '</span>';
    },
    { enableHighAccuracy: true, maximumAge: 2000, timeout: 15000 }
  );
}

function pauseTracking() {
  isPaused = true;
  document.getElementById('btn-pause').style.display = 'none';
  document.getElementById('btn-resume').style.display = 'flex';
  document.getElementById('status-bar').innerHTML =
    '<span style="color:#FFD700">⏸ PAUSED</span>';
}

function resumeTracking() {
  isPaused = false;
  document.getElementById('btn-resume').style.display = 'none';
  document.getElementById('btn-pause').style.display = 'flex';
  document.getElementById('status-bar').innerHTML =
    '<span class="live-dot"></span><span style="color:#00F5A0">TRACKING LIVE</span>';
  lastPos = null;
}

function stopTracking() {
  isRunning = false;
  isPaused = false;
  clearInterval(timerInterval);
  if (watchId !== null) navigator.geolocation.clearWatch(watchId);
  releaseWakeLock();

  document.getElementById('btn-pause').style.display = 'none';
  document.getElementById('btn-resume').style.display = 'none';
  document.getElementById('btn-stop').style.display = 'none';
  document.getElementById('btn-start').style.display = 'flex';
  document.getElementById('accuracy-bar').style.display = 'none';
  document.getElementById('status-bar').innerHTML =
    '<span style="color:#8892A4">Run stopped. Review and save below.</span>';

  // Show summary
  var distKm = totalDistance;
  document.getElementById('summary-dist').textContent = formatDist(distKm) + ' ' + unit;
  document.getElementById('summary-time').textContent = formatTime(elapsedSeconds);
  document.getElementById('summary-pace').textContent = formatPace(elapsedSeconds, distKm) + '/'+unit;
  document.getElementById('save-section').style.display = 'block';

  // Store values for Streamlit
  document.getElementById('final-distance').value = distKm.toFixed(4);
  document.getElementById('final-duration').value = elapsedSeconds;

  if (distKm > 0.01) {
    document.getElementById('btn-save').style.display = 'block';
  }
}

function saveRun() {
  var dist = parseFloat(document.getElementById('final-distance').value);
  var dur = parseInt(document.getElementById('final-duration').value);
  if (dist < 0.01 || dur < 1) {
    alert('No run data to save!');
    return;
  }
  // Send to Streamlit via URL params
  var url = new URL(window.location.href);
  url.searchParams.set('gps_dist', dist.toFixed(4));
  url.searchParams.set('gps_dur', dur);
  url.searchParams.set('gps_unit', unit);
  window.location.href = url.toString();
}
</script>
"""

# ─── AUTH ────────────────────────────────────────────────────────
def auth_page():
    st.markdown("""
    <div style='text-align:center; padding: 40px 0 20px'>
        <div style='font-size:3rem'>🏃</div>
        <div class='logo-text'>RUN<span class='logo-accent'>QUEST</span></div>
        <p style='color:#8892A4; margin-top:4px'>Level up your running journey</p>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["Sign In", "Register"])
    with tab1:
        with st.form("login_form"):
            email = st.text_input("Email", placeholder="runner@example.com")
            password = st.text_input("Password", type="password", placeholder="••••••••")
            submit = st.form_submit_button("▶ START RUNNING", use_container_width=True)
            if submit:
                try:
                    res = sb.auth.sign_in_with_password({"email": email, "password": password})
                    st.session_state.user = res.user
                    st.session_state.session = res.session
                    st.rerun()
                except Exception as e:
                    st.error(f"Login failed: {str(e)}")

    with tab2:
        with st.form("register_form"):
            email = st.text_input("Email", placeholder="runner@example.com", key="reg_email")
            password = st.text_input("Password", type="password", placeholder="Min. 6 characters", key="reg_pass")
            submit = st.form_submit_button("CREATE ACCOUNT →", use_container_width=True)
            if submit:
                try:
                    sb.auth.sign_up({"email": email, "password": password})
                    st.success("✅ Account created! Check your email to confirm, then sign in.")
                except Exception as e:
                    st.error(f"Registration failed: {str(e)}")

# ─── PAGES ───────────────────────────────────────────────────────

def page_dashboard(user_id, profile, runs, unit):
    xp = profile.get("xp", 0)
    rank = get_rank(xp)
    next_rank = get_next_rank(xp)
    progress = get_xp_progress(xp)
    accent = st.session_state.get("accent", "#00F5A0")

    st.markdown("## ⚡ Dashboard")
    st.markdown(f"Welcome back, **{st.session_state.user.email.split('@')[0]}** 👋")
    st.markdown("---")

    col1, col2 = st.columns([1, 3])
    with col1:
        st.markdown(f"<div style='font-size:3rem; text-align:center'>{rank['icon']}</div>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"<div class='rank-chip'>Level {rank['level']} • {rank['title']}</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='font-family:Rajdhani,sans-serif; font-size:1.8rem; font-weight:800; color:{accent}'>{xp:,} XP</div>", unsafe_allow_html=True)
        next_txt = f"→ {next_rank['icon']} {next_rank['title']} ({next_rank['min_xp'] - xp} XP away)" if next_rank else "MAX RANK 🌟"
        st.caption(next_txt)
        st.markdown(f"""
        <div class='xp-bar-outer'>
            <div style='width:{progress}%; height:100%; background:linear-gradient(90deg,#00F5A0,#00D4FF); border-radius:99px'></div>
        </div>
        <small style='color:#4A5568'>{progress}% to next rank</small>
        """, unsafe_allow_html=True)

    st.markdown("---")
    total_dist = sum(r["distance_km"] for r in runs)
    week_runs = [r for r in runs if is_this_week(r["started_at"])]
    week_dist = sum(r["distance_km"] for r in week_runs)
    week_time = sum(r["duration_seconds"] for r in week_runs)
    completed_count = sum(1 for q in QUESTS if check_quest(q["id"], runs))

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f"<div class='metric-card'><div class='metric-value'>{len(runs)}</div><div class='metric-label'>Total Runs</div></div>", unsafe_allow_html=True)
    with c2: st.markdown(f"<div class='metric-card'><div class='metric-value'>{format_distance(total_dist, unit)}</div><div class='metric-label'>Total {unit}</div></div>", unsafe_allow_html=True)
    with c3: st.markdown(f"<div class='metric-card'><div class='metric-value'>{format_distance(week_dist, unit)}</div><div class='metric-label'>This Week ({unit})</div></div>", unsafe_allow_html=True)
    with c4: st.markdown(f"<div class='metric-card'><div class='metric-value'>{completed_count}</div><div class='metric-label'>Quests Done</div></div>", unsafe_allow_html=True)

    st.markdown("---")
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("#### 🎯 Active Quests")
        active = [q for q in QUESTS if not check_quest(q["id"], runs)][:3]
        if not active:
            st.success("All quests complete! 🎉")
        for q in active:
            st.markdown(f"""
            <div class='quest-card'>
                <span style='font-size:1.3rem'>{q['icon']}</span>
                <strong> {q['title']}</strong>
                <span style='float:right; color:#FFD700; font-weight:700'>+{q['xp']} XP</span>
                <br><small style='color:#8892A4'>{q['desc']}</small>
            </div>""", unsafe_allow_html=True)

    with col_b:
        st.markdown("#### ⚡ Last Run")
        if not runs:
            st.info("No runs yet. Start tracking! 👟")
        else:
            r = runs[0]
            d = format_distance(r["distance_km"], unit)
            t = format_time(r["duration_seconds"])
            p = format_pace(r["duration_seconds"], r["distance_km"], unit)
            pb_badge = "<span class='pb-badge'>🏅 PB</span>" if r.get("is_pb") else ""
            st.markdown(f"""
            <div class='run-card'>
                {pb_badge}
                <div style='display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-top:8px'>
                    <div><div style='font-size:0.7rem;color:#4A5568;text-transform:uppercase'>Distance</div>
                    <div style='font-family:JetBrains Mono,monospace;font-weight:700'>{d} {unit}</div></div>
                    <div><div style='font-size:0.7rem;color:#4A5568;text-transform:uppercase'>Time</div>
                    <div style='font-family:JetBrains Mono,monospace;font-weight:700'>{t}</div></div>
                    <div><div style='font-size:0.7rem;color:#4A5568;text-transform:uppercase'>Pace</div>
                    <div style='font-family:JetBrains Mono,monospace;font-weight:700'>{p} /{unit}</div></div>
                    <div><div style='font-size:0.7rem;color:#4A5568;text-transform:uppercase'>XP</div>
                    <div style='font-family:JetBrains Mono,monospace;font-weight:700;color:#00F5A0'>+{r.get("xp_earned",0)}</div></div>
                </div>
                <div style='margin-top:8px;font-size:0.75rem;color:#4A5568'>{r["started_at"][:10]}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### 📅 This Week")
    w1, w2, w3 = st.columns(3)
    with w1: st.markdown(f"<div class='metric-card'><div class='metric-value'>{len(week_runs)}</div><div class='metric-label'>Runs</div></div>", unsafe_allow_html=True)
    with w2: st.markdown(f"<div class='metric-card'><div class='metric-value'>{format_distance(week_dist, unit)}</div><div class='metric-label'>Distance ({unit})</div></div>", unsafe_allow_html=True)
    with w3: st.markdown(f"<div class='metric-card'><div class='metric-value'>{format_time(week_time)}</div><div class='metric-label'>Total Time</div></div>", unsafe_allow_html=True)


def page_gps_tracker(user_id, profile, runs, unit):
    st.markdown("## 📍 GPS Tracker")
    st.warning("⚠️ Keep this tab open and your screen ON while running. Do NOT lock your phone!")

    # Check if GPS data was submitted via URL params
    params = st.query_params
    if "gps_dist" in params and "gps_dur" in params:
        try:
            dist_km = float(params["gps_dist"])
            duration = int(params["gps_dur"])
            gps_unit = params.get("gps_unit", "km")
            if gps_unit == "mi":
                dist_km = dist_km / 0.621371

            if dist_km > 0.01 and duration > 0:
                total_xp, is_pb, fresh_quests = process_and_save_run(
                    user_id, profile, runs, dist_km, duration, unit
                )
                st.query_params.clear()
                st.success(f"✅ Run saved! **{format_distance(dist_km, unit)} {unit}** in **{format_time(duration)}**")
                if is_pb:
                    st.balloons()
                    st.success("🏅 NEW PERSONAL BEST!")
                st.info(f"⭐ +{total_xp} XP earned!")
                for q in fresh_quests:
                    st.success(f"🎯 Quest Complete: **{q['icon']} {q['title']}** (+{q['xp']} XP)")
        except Exception as e:
            st.error(f"Error saving GPS run: {e}")
            st.query_params.clear()

    # Unit selector
    unit_sel = st.radio("Unit", ["km", "mi"], horizontal=True, index=0 if unit == "km" else 1)

    # Inject GPS tracker with correct unit
    gps_html = GPS_JS.replace("UNIT_PLACEHOLDER", unit_sel)
    st.components.v1.html(gps_html, height=580, scrolling=False)

    st.markdown("---")
    st.caption("💡 **Tips for best accuracy:** Go outside before starting • Wait for GPS accuracy < 15m • Keep phone in hand or armband")


def page_log_run(user_id, profile, runs, unit):
    st.markdown("## ✍️ Manual Log")
    st.markdown("Log a run manually using data from your fitness watch or health app.")

    with st.form("log_run_form"):
        col1, col2 = st.columns(2)
        with col1:
            distance = st.number_input("Distance", min_value=0.1, max_value=200.0, step=0.1, value=5.0)
        with col2:
            unit_sel = st.selectbox("Unit", ["km", "mi"], index=0 if unit == "km" else 1)

        col3, col4, col5 = st.columns(3)
        with col3: hours = st.number_input("Hours", min_value=0, max_value=24, value=0)
        with col4: minutes = st.number_input("Minutes", min_value=0, max_value=59, value=30)
        with col5: seconds = st.number_input("Seconds", min_value=0, max_value=59, value=0)

        submitted = st.form_submit_button("💾 SAVE RUN", use_container_width=True)
        if submitted:
            dist_km = distance if unit_sel == "km" else distance / 0.621371
            total_seconds = hours * 3600 + minutes * 60 + seconds
            if total_seconds == 0:
                st.error("Please enter a valid duration.")
            else:
                total_xp, is_pb, fresh_quests = process_and_save_run(
                    user_id, profile, runs, dist_km, total_seconds, unit_sel
                )
                pace = format_pace(total_seconds, dist_km, unit_sel)
                st.success(f"✅ Run saved! **{distance} {unit_sel}** in **{format_time(total_seconds)}** — Pace: {pace} /{unit_sel}")
                if is_pb:
                    st.balloons()
                    st.success("🏅 NEW PERSONAL BEST!")
                st.info(f"⭐ +{total_xp} XP earned!")
                for q in fresh_quests:
                    st.success(f"🎯 Quest Complete: **{q['icon']} {q['title']}** (+{q['xp']} XP)")
                st.rerun()


def page_history(user_id, runs, unit):
    st.markdown("## 📋 Run History")
    st.caption(f"{len(runs)} runs recorded")
    if not runs:
        st.info("No runs yet. Start tracking! 👟")
        return

    unit_sel = st.radio("Unit", ["km", "mi"], horizontal=True, index=0 if unit == "km" else 1)
    for r in runs:
        d = format_distance(r["distance_km"], unit_sel)
        t = format_time(r["duration_seconds"])
        p = format_pace(r["duration_seconds"], r["distance_km"], unit_sel)
        pb_badge = "🏅 PB  " if r.get("is_pb") else ""
        col1, col2 = st.columns([5, 1])
        with col1:
            st.markdown(f"""
            <div class='run-card'>
                <div style='display:flex; justify-content:space-between; align-items:center'>
                    <span style='font-size:0.8rem; color:#8892A4'>{r["started_at"][:10]}</span>
                    <span>{pb_badge}<span style='color:#00F5A0; font-weight:700; font-size:0.85rem'>+{r.get("xp_earned",0)} XP</span></span>
                </div>
                <div style='display:grid; grid-template-columns:1fr 1fr 1fr; gap:8px; margin-top:8px'>
                    <div><div style='font-size:0.65rem;color:#4A5568;text-transform:uppercase'>Distance</div>
                    <div style='font-family:JetBrains Mono,monospace;font-weight:700'>{d} {unit_sel}</div></div>
                    <div><div style='font-size:0.65rem;color:#4A5568;text-transform:uppercase'>Time</div>
                    <div style='font-family:JetBrains Mono,monospace;font-weight:700'>{t}</div></div>
                    <div><div style='font-size:0.65rem;color:#4A5568;text-transform:uppercase'>Pace</div>
                    <div style='font-family:JetBrains Mono,monospace;font-weight:700'>{p}/{unit_sel}</div></div>
                </div>
            </div>""", unsafe_allow_html=True)
        with col2:
            if st.button("✕", key=f"del_{r['id']}"):
                delete_run(r["id"])
                st.rerun()


def page_quests(user_id, profile, runs):
    st.markdown("## 🎯 Quests & Progression")
    xp = profile.get("xp", 0)
    rank = get_rank(xp)
    next_rank = get_next_rank(xp)
    progress = get_xp_progress(xp)
    completed_ids = set(q["id"] for q in QUESTS if check_quest(q["id"], runs))
    completed = [q for q in QUESTS if q["id"] in completed_ids]
    pending = [q for q in QUESTS if q["id"] not in completed_ids]

    st.markdown("### ⭐ Rank Ladder")
    cols = st.columns(len(RANKS))
    for i, r in enumerate(RANKS):
        unlocked = xp >= r["min_xp"]
        is_current = r["level"] == rank["level"]
        with cols[i]:
            st.markdown(f"""
            <div style='text-align:center; padding:10px 4px; border-radius:8px;
                border: 2px solid {"#00F5A0" if is_current else "#2A3148"};
                background: {"rgba(0,245,160,0.1)" if is_current else "transparent"};
                opacity: {"1" if unlocked else "0.35"}'>
                <div style='font-size:1.3rem'>{r['icon']}</div>
                <div style='font-size:0.6rem; font-weight:700; color:{"#00F5A0" if is_current else "#8892A4"};
                    text-transform:uppercase; margin-top:2px'>{r['title']}</div>
                <div style='font-size:0.55rem; color:#4A5568'>Lv.{r["level"]}</div>
                {"<div style='font-size:0.55rem; color:#00F5A0; font-weight:700'>YOU</div>" if is_current else ""}
            </div>""", unsafe_allow_html=True)

    st.markdown(f"""
    <div style='margin-top:16px'>
        <div style='display:flex; justify-content:space-between; font-size:0.8rem; color:#8892A4; margin-bottom:6px'>
            <span>{rank['icon']} {rank['title']} — {xp:,} XP</span>
            <span>{"→ " + next_rank['icon'] + " " + next_rank['title'] if next_rank else "MAX RANK 🌟"}</span>
        </div>
        <div class='xp-bar-outer'>
            <div style='width:{progress}%; height:100%; background:linear-gradient(90deg,#00F5A0,#00D4FF); border-radius:99px'></div>
        </div>
        <small style='color:#4A5568'>{progress}% — {str(next_rank["min_xp"] - xp) + " XP to " + next_rank["title"] if next_rank else "Transcendent achieved!"}</small>
    </div>""", unsafe_allow_html=True)

    st.markdown("---")
    if pending:
        st.markdown(f"### ⚔️ Active Quests ({len(pending)})")
        for q in pending:
            st.markdown(f"""
            <div class='quest-card'>
                <span style='font-size:1.4rem'>{q['icon']}</span>
                <strong> {q['title']}</strong>
                <span style='float:right; background:rgba(255,215,0,0.12); color:#FFD700;
                    border:1px solid rgba(255,215,0,0.3); border-radius:99px;
                    padding:2px 10px; font-size:0.75rem; font-weight:700'>+{q['xp']} XP</span>
                <br><small style='color:#8892A4'>{q['desc']}</small>
            </div>""", unsafe_allow_html=True)

    if completed:
        st.markdown(f"### ✅ Completed ({len(completed)})")
        cols = st.columns(2)
        for i, q in enumerate(completed):
            with cols[i % 2]:
                st.markdown(f"""
                <div class='quest-done'>
                    <span style='font-size:1.2rem'>{q['icon']}</span>
                    <strong style='font-size:0.9rem'> {q['title']}</strong>
                    <span style='float:right'>✅</span>
                    <br><small style='color:#00F5A0'>+{q['xp']} XP earned</small>
                </div>""", unsafe_allow_html=True)


def page_stats(user_id, runs, unit):
    st.markdown("## 📈 Stats")
    if not runs:
        st.info("Complete some runs to see your stats! 📊")
        return

    unit_sel = st.radio("Unit", ["km", "mi"], horizontal=True, index=0 if unit == "km" else 1)
    runs_asc = list(reversed(runs))
    total_dist = sum(r["distance_km"] for r in runs)
    total_time = sum(r["duration_seconds"] for r in runs)
    avg_pace = (total_time / 60) / total_dist if total_dist else 0
    best_pace = min((r["duration_seconds"] / 60 / r["distance_km"]) for r in runs if r["distance_km"] > 0)

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("Total Runs", len(runs))
    with c2: st.metric(f"Total {unit_sel}", format_distance(total_dist, unit_sel))
    with c3: st.metric("Avg Pace", f"{format_pace(int(avg_pace * 60), 1, unit_sel)} /{unit_sel}")
    with c4: st.metric("Best Pace", f"{format_pace(int(best_pace * 60), 1, unit_sel)} /{unit_sel}")

    st.markdown("---")
    chart_pace = {}
    chart_dist = {}
    chart_xp = {}
    for r in runs_asc:
        date = r["started_at"][:10]
        pace_val = (r["duration_seconds"] / 60) / r["distance_km"]
        if unit_sel == 'mi': pace_val = pace_val / 1.60934
        chart_pace[date] = round(pace_val, 2)
        chart_dist[date] = float(format_distance(r["distance_km"], unit_sel))
        chart_xp[date] = r.get("xp_earned", 0)

    tab1, tab2, tab3 = st.tabs(["⚡ Pace Trend", f"🗺️ Distance", "⭐ XP Earned"])
    with tab1: st.line_chart(chart_pace)
    with tab2: st.bar_chart(chart_dist)
    with tab3: st.bar_chart(chart_xp)

    st.markdown("---")
    st.markdown("### 🏅 Personal Bests")
    pb_distances = [1, 3, 5, 10, 21.1, 42.2]
    pb_labels = {1: "1km", 3: "3km", 5: "5km", 10: "10km", 21.1: "Half Marathon", 42.2: "Marathon"}
    pb_cols = st.columns(3)
    found = 0
    for dist in pb_distances:
        relevant = [r for r in runs if abs(r["distance_km"] - dist) < 0.2]
        if relevant:
            pb = min(relevant, key=lambda r: r["duration_seconds"])
            with pb_cols[found % 3]:
                st.markdown(f"""
                <div style='background:rgba(255,215,0,0.06); border:1px solid rgba(255,215,0,0.2);
                    border-radius:10px; padding:14px; text-align:center; margin-bottom:10px'>
                    <div style='font-size:0.8rem; color:#FFD700; font-weight:700'>{pb_labels[dist]}</div>
                    <div style='font-family:JetBrains Mono,monospace; font-size:1.4rem; font-weight:800; margin-top:4px'>{format_time(pb["duration_seconds"])}</div>
                    <div style='font-size:0.75rem; color:#8892A4; margin-top:2px'>{format_pace(pb["duration_seconds"], pb["distance_km"], unit_sel)} /{unit_sel}</div>
                </div>""", unsafe_allow_html=True)
            found += 1
    if found == 0:
        st.caption("No personal bests yet. Complete runs near standard distances.")


def page_settings(user_id, profile):
    st.markdown("## ⚙️ Settings")
    with st.form("settings_form"):
        st.markdown("#### 🎨 Theme")
        theme = st.selectbox("Color Mode", ["Dark", "Light"],
                             index=0 if st.session_state.get("theme", "Dark") == "Dark" else 1)
        st.markdown("#### 🎨 Accent Color")
        accent = st.color_picker("Accent Color", value=st.session_state.get("accent", "#00F5A0"))
        st.markdown("#### ✏️ Font")
        font_options = ["Exo 2", "Rajdhani", "JetBrains Mono", "Georgia", "Trebuchet MS"]
        font = st.selectbox("Font Family", font_options,
                            index=font_options.index(st.session_state.get("font", "Exo 2")))
        st.markdown("#### 📏 Units")
        unit = st.radio("Distance Unit", ["km", "mi"], horizontal=True,
                        index=0 if profile.get("unit", "km") == "km" else 1)
        st.markdown("#### 👤 Account")
        st.text_input("Email", value=st.session_state.user.email, disabled=True)
        saved = st.form_submit_button("💾 SAVE SETTINGS", use_container_width=True)
        if saved:
            st.session_state.theme = theme
            st.session_state.accent = accent
            st.session_state.font = font
            update_profile(user_id, profile.get("xp", 0), profile.get("completed_quests", []), unit)
            st.success("✅ Settings saved!")
            st.rerun()


# ─── MAIN ────────────────────────────────────────────────────────
def main():
    if "user" not in st.session_state: st.session_state.user = None
    if "theme" not in st.session_state: st.session_state.theme = "Dark"
    if "accent" not in st.session_state: st.session_state.accent = "#00F5A0"
    if "font" not in st.session_state: st.session_state.font = "Exo 2"

    apply_theme(st.session_state.theme, st.session_state.accent, st.session_state.font)

    if not st.session_state.user:
        auth_page()
        return

    user_id = st.session_state.user.id
    profile = get_profile(user_id)
    runs = get_runs(user_id)
    unit = profile.get("unit", "km")

    with st.sidebar:
        st.markdown("<div class='logo-text'>RUN<span class='logo-accent'>QUEST</span></div>", unsafe_allow_html=True)
        st.markdown("---")
        page = st.radio("Navigation", [
            "⚡ Dashboard",
            "📍 GPS Tracker",
            "✍️ Manual Log",
            "📋 History",
            "🎯 Quests",
            "📈 Stats",
            "⚙️ Settings",
        ], label_visibility="collapsed")
        st.markdown("---")
        xp = profile.get("xp", 0)
        rank = get_rank(xp)
        progress = get_xp_progress(xp)
        st.markdown(f"""
        <div style='font-size:0.8rem; color:#8892A4; margin-bottom:4px'>{rank['icon']} {rank['title']} • Lv.{rank['level']}</div>
        <div class='xp-bar-outer'>
            <div style='width:{progress}%; height:100%; background:linear-gradient(90deg,#00F5A0,#00D4FF); border-radius:99px'></div>
        </div>
        <div style='font-size:0.7rem; color:#4A5568; margin-top:4px'>{xp:,} XP</div>
        """, unsafe_allow_html=True)
        st.markdown("---")
        if st.button("🚪 Sign Out", use_container_width=True):
            sb.auth.sign_out()
            st.session_state.user = None
            st.rerun()

    if page == "⚡ Dashboard":
        page_dashboard(user_id, profile, runs, unit)
    elif page == "📍 GPS Tracker":
        page_gps_tracker(user_id, profile, runs, unit)
    elif page == "✍️ Manual Log":
        page_log_run(user_id, profile, runs, unit)
    elif page == "📋 History":
        page_history(user_id, runs, unit)
    elif page == "🎯 Quests":
        page_quests(user_id, profile, runs)
    elif page == "📈 Stats":
        page_stats(user_id, runs, unit)
    elif page == "⚙️ Settings":
        page_settings(user_id, profile)

if __name__ == "__main__":
    main()
