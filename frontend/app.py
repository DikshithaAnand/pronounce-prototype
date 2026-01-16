import streamlit as st
import requests
import time
import threading
import itertools
import textwrap
from pathlib import Path
from datetime import datetime
from streamlit.runtime.scriptrunner import add_script_run_ctx

# -----------------------------
# Configuration
# -----------------------------

st.set_page_config(
    page_title="Pronounce Prototype",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Load External CSS
def load_css():
    css_path = Path("frontend/style.css")
    if css_path.exists():
        with open(css_path) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    else:
        st.warning("⚠️ frontend/style.css not found.")

load_css()

# API Config
BACKEND_URL = "http://localhost:8000/process-audio/"
PASSAGE_URL = "http://localhost:8000/get-passage/"

LANGUAGES = {
    "English": "en",
    "Hindi (हिंदी)": "hi",
    "Tamil (தமிழ்)": "ta",
    "Telugu (తెలుగు)": "te",
    "Kannada (ಕನ್ನಡ)": "kn",
    "Gujarati (ગુજરાતી)": "gu",
}

# -----------------------------
# Rendering Helpers (FIXED)
# -----------------------------

def render_comparison_table(error_list):
    """Renders the detailed error comparison table with Mispronunciation support."""
    if not error_list:
        return "<div class='metric-success' style='padding:10px; text-align:center;'>🎉 Perfect Reading! Zero specific errors detected.</div>"

    rows = ""
    for err in error_list:
        e_type = err['type']
        expected = err['expected']
        actual = err['actual']
        
        # --- NEW BADGE LOGIC ---
        if e_type == "mispronunciation":
            badge = "<span class='badge badge-mis'>Mispronounced</span>"
            # Highlight the 'Actual' word in Orange to indicate 'Close attempt'
            actual_html = f"<span style='color:#e67700; font-weight:bold;'>{actual}</span>"
            
        elif e_type == "substitution":
            badge = "<span class='badge badge-sub'>Wrong Word</span>"
            actual_html = f"<span style='color:#d63384; font-weight:bold;'>{actual}</span>"
            
        elif e_type == "deletion":
            badge = "<span class='badge badge-del'>Skipped</span>"
            actual_html = "<i>(No Audio)</i>"
            
        elif e_type == "insertion":
            badge = "<span class='badge badge-ins'>Added</span>"
            actual_html = f"<span style='color:#fd7e14;'>{actual}</span>"

        rows += f"""<tr>
            <td>{badge}</td>
            <td><strong>{expected}</strong></td>
            <td>{actual_html}</td>
        </tr>"""

    return textwrap.dedent(f"""
    <div style="overflow-x:auto;">
        <table class="comparison-table">
            <thead>
                <tr>
                    <th style="width:20%">Error Type</th>
                    <th style="width:40%">Expected Word</th>
                    <th style="width:40%">You Said</th>
                </tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
    </div>
    """)

def render_highlighted_passage(alignment_data):
    """Generates the Karaoke-style HTML."""
    html_parts = []
    for item in alignment_data:
        target = item.get("target", "")
        recognized = item.get("recognized", "")
        status = item.get("status", "unknown")
        
        if status == "correct":
            html_parts.append(f"<span class='word-correct'>{target}</span>")
        elif status == "substitution":
            html_parts.append(f"<span class='word-substitution' title='Heard: {recognized}'>{target}</span>")
        elif status == "deletion":
            html_parts.append(f"<span class='word-deletion'>{target}</span>")
        elif status == "insertion":
            html_parts.append(f"<span class='word-insertion'>+{recognized}</span>")
        elif status == "stutter":
            html_parts.append(f"<span class='word-stutter'>{recognized}</span>")
            
    return " ".join(html_parts)

def render_terminal_logs(logs):
    """Generates the Hacker-style Terminal HTML."""
    if not logs: return ""

    log_lines = ""
    for log in logs:
        ts = datetime.fromtimestamp(log['timestamp']).strftime('%H:%M:%S')
        lvl = log['level']
        msg = log['message']
        
        log_lines += f"""<div class="log-entry">
            <span class="log-timestamp">[{ts}]</span>
            <span class="log-{lvl}">{lvl}</span>
            <span class="log-message">{msg}</span>
        </div>"""

    return textwrap.dedent(f"""
    <div class="terminal-window">
        <div class="terminal-header">
            <div class="terminal-dots">
                <div class="dot red"></div><div class="dot yellow"></div><div class="dot green"></div>
            </div>
            <div class="terminal-title">system_logs — bash — 80x24</div>
        </div>
        <div class="terminal-body">
            {log_lines}
            <div style="color: #27c93f; margin-top: 5px;">➜ root@backend: _</div>
        </div>
    </div>
    """)

# -----------------------------
# Dynamic Loading Logic (FIXED)
# -----------------------------
def cycle_status_messages(placeholder, stop_event):
    """
    Updates a Streamlit placeholder with friendly, encouraging messages.
    """
    messages = [
        "👂 Listening to your lovely voice...",
        "✨ You sound amazing!",
        "🐢 Catching all the words...",
        "🌟 Checking for magic stars...",
        "📚 Almost ready...",
        "🎉 Putting it all together...",
    ]
    
    # Cycle through messages indefinitely
    for msg in itertools.cycle(messages):
        if stop_event.is_set():
            break
        
        # Friendly blue/purple color, centered text
        placeholder.markdown(
            f"<h3 style='text-align: center; color: #4a4e69; font-family: sans-serif; padding: 20px;'>{msg}</h3>", 
            unsafe_allow_html=True
        )
        time.sleep(1.5)

# -----------------------------
# UI Application
# -----------------------------

st.title("🗣️ Pronounce — Reading Assistant")
st.caption("Dyslexia-Optimized Assessment Engine")

# --- Control Bar ---
col_lang, col_btn = st.columns([3, 1])
with col_lang:
    selected_language = st.selectbox("Select Language", list(LANGUAGES.keys()))
    lang_code = LANGUAGES[selected_language]

if "current_passage" not in st.session_state:
    st.session_state.current_passage = "Click 'New Passage' to start."

with col_btn:
    if st.button("🔄 New Passage", use_container_width=True):
        try:
            with st.spinner("Fetching text..."):
                r = requests.get(PASSAGE_URL, params={"language": lang_code})
                if r.status_code == 200:
                    data = r.json()
                    st.session_state.current_passage = data["passage"]
                    st.rerun()
        except:
            st.error("Backend Down")

# Dynamic Height for Text Area
text_len = len(st.session_state.current_passage)
dynamic_height = max(150, int(text_len / 2.5))

target_text = st.text_area(
    "Read this aloud:", 
    value=st.session_state.current_passage, 
    height=dynamic_height
)

# --- Audio Input ---
audio_data = st.audio_input("Record your voice")

if audio_data:
    st.audio(audio_data)
    
    if st.button("Analyze Reading", type="primary", use_container_width=True):
        
        # Prepare file for upload
        audio_data.seek(0)
        files = {"file": ("recording.webm", audio_data, "audio/webm")}
        data = {"target_text": target_text, "language": lang_code}
        
        # --- DYNAMIC LOADING ANIMATION ---
        status_placeholder = st.empty()
        stop_event = threading.Event()
        
        # Start the background thread
        loader_thread = threading.Thread(
            target=cycle_status_messages, 
            args=(status_placeholder, stop_event)
        )
        
        # IMPORTANT: Attach Streamlit Context to the thread so it can write to UI
        add_script_run_ctx(loader_thread)
        
        loader_thread.start()
        
        try:
            # Main synchronous API call
            response = requests.post(BACKEND_URL, files=files, data=data)
            
            # Stop the animation
            stop_event.set()
            loader_thread.join()
            status_placeholder.empty() # Clear the loading text
            
            if response.status_code != 200:
                st.error(f"Error: {response.text}")
                st.stop()
                
            result = response.json()
            
        except Exception as e:
            stop_event.set()
            status_placeholder.empty()
            st.error(f"Connection Error: {e}")
            st.stop()

        # -----------------------------
        # TABBED RESULTS
        # -----------------------------
        st.divider()
        
        # Extract Data
        metrics = result.get("metrics", {})
        scores = result.get("components", {})
        alignment = result.get("word_alignment", [])
        error_list = result.get("error_analysis", [])
        logs = result.get("logs", [])
        
        t1, t2, t3, t4 = st.tabs(["📊 Summary", "🔍 Errors", "📖 Text", "💻 Logs"])

        # --- TAB 1: SUMMARY (UPDATED) ---
        with t1:
            st.subheader("Performance Overview")
            
            # --- ROW 1: SUCCESS METRICS (Positive Reinforcement) ---
            c1, c2, c3 = st.columns(3)
            
            # 1. Accuracy
            c1.metric("Overall Accuracy", f"{metrics.get('accuracy', 0)}%")
            
            # 2. Fluency (Now using the Calculated Score)
            c2.metric("Fluency Score", f"{metrics.get('fluency', 0)}/100")
            
            # 3. Correct Words (NEW: Green Card for Motivation)
            correct_n = metrics.get("correct_count", 0)
            c3.markdown(f"""
            <div class="metric-container" style="border-left: 5px solid #28a745;">
                <div class="metric-label">Words Read Perfectly</div>
                <div class="metric-value" style="color:#28a745">✨ {correct_n}</div>
                <div class="sub-metric">Great job!</div>
            </div>""", unsafe_allow_html=True)
            
            st.divider()
            
            # --- ROW 2: AREAS TO IMPROVE ---
            k1, k2, k3, k4 = st.columns(4)
            
            # Mispronounced
            mis = metrics.get("mispronunciation_count", 0)
            k1.markdown(f"""
            <div class="metric-container">
                <div class="metric-label">Mispronounced</div>
                <div class="metric-value" style="color:#f08c00">{mis}</div>
                <div class="sub-metric">Close attempts</div>
            </div>""", unsafe_allow_html=True)
            
            # Wrong Words
            sub = metrics.get("substitution_count", 0)
            k2.markdown(f"""
            <div class="metric-container">
                <div class="metric-label">Wrong Words</div>
                <div class="metric-value" style="color:#dc3545">{sub}</div>
                <div class="sub-metric">Try again</div>
            </div>""", unsafe_allow_html=True)
            
            # Skipped
            dele = metrics.get("deletion_count", 0)
            k3.markdown(f"""
            <div class="metric-container">
                <div class="metric-label">Skipped Words</div>
                <div class="metric-value" style="color:#6c757d">{dele}</div>
                <div class="sub-metric">Missed</div>
            </div>""", unsafe_allow_html=True)
            
            # Stutters
            stut = metrics.get("stutter_count", 0)
            k4.markdown(f"""
            <div class="metric-container">
                <div class="metric-label">Stutters</div>
                <div class="metric-value" style="color:#ffc107">{stut}</div>
                <div class="sub-metric">Repeats</div>
            </div>""", unsafe_allow_html=True)

            # --- ROW 3: SPEEDOMETER ---
            st.markdown("<br>", unsafe_allow_html=True)
            wpm = metrics.get('wpm', 0)
            
            display_wpm = min(wpm, 200)
            marker_pos = (display_wpm / 200) * 100
            
            if wpm < 80: speed_text = "Slow"
            elif wpm > 160: speed_text = "Fast"
            else: speed_text = "Optimal"

            st.markdown(f"""
            <div class="speed-container">
                <div class="metric-label">Speaking Pace: {wpm} Words Per Min ({speed_text})</div>
                <div class="speed-bar-bg">
                    <div class="speed-marker" style="left: {marker_pos}%;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # --- TAB 2: ERROR TABLE ---
        with t2:
            st.subheader("Word-by-Word Analysis")
            st.markdown(render_comparison_table(error_list), unsafe_allow_html=True)

        # --- TAB 3: HIGHLIGHTED TEXT ---
        with t3:
            st.subheader("Visual Feedback")
            html_view = render_highlighted_passage(alignment)
            st.markdown(f"<div class='passage-box'>{html_view}</div>", unsafe_allow_html=True)

        # --- TAB 4: SYSTEM LOGS ---
        with t4:
            st.subheader("Backend Logs")
            st.markdown(render_terminal_logs(logs), unsafe_allow_html=True)