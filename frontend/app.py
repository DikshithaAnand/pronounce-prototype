import streamlit as st
import requests
import time
import threading
import itertools
import textwrap
from pathlib import Path
from datetime import datetime
from streamlit.runtime.scriptrunner import add_script_run_ctx

# --- AUTH IMPORT ---
from auth_client import login, signup, logout

# -----------------------------
# Configuration
# -----------------------------

st.set_page_config(
    page_title="Pronounce AI",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Load External CSS
def load_css():
    # Try finding the file relative to this script
    css_path = Path(__file__).parent / "style.css"
    
    if css_path.exists():
        with open(css_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    else:
        # Fallback: Try looking in the local directory
        fallback_path = Path("frontend/style.css")
        if fallback_path.exists():
             with open(fallback_path, "r", encoding="utf-8") as f:
                st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
        else:
            st.error(f"⚠️ CSS File not found at: {css_path}")
            
def show_custom_toast(message, type="error"):
    """
    Injects a temporary centered popup notification.
    """
    icon = "⚠️" if type == "error" else "🎉"
    css_class = "toast-error" if type == "error" else "toast-success"
    
    # We use st.markdown with unsafe_allow_html to inject the div
    st.markdown(f"""
        <div class="toast-container {css_class}">
            <span style="font-size: 1.5rem;">{icon}</span>
            <span>{message}</span>
        </div>
    """, unsafe_allow_html=True)
load_css()

# API Config (Using 127.0.0.1 to prevent Backend Down errors)
BACKEND_URL = "http://127.0.0.1:8000/process-audio/"
PASSAGE_URL = "http://127.0.0.1:8000/get-passage/"

LANGUAGES = {
    "English": "en",
    "Hindi (हिंदी)": "hi",
    "Tamil (தமிழ்)": "ta",
    "Telugu (తెలుగు)": "te",
    "Kannada (ಕನ್ನಡ)": "kn",
    "Gujarati (ગુજરાતી)": "gu",
}

# -----------------------------
# 1. AUTHENTICATION SCREENS
# -----------------------------

def show_login_page():
    st.markdown("<h1 style='text-align: center;'>🔐 Login to Pronounce</h1>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    
    with tab1:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_pass")
        if st.button("Login", use_container_width=True):
            with st.spinner("Logging in..."):
                user, error = login(email, password)
                if user:
                    st.session_state["user"] = user
                    st.success("Welcome back!")
                    st.rerun()
                else:
                    st.error(f"Error: {error}")

    with tab2:
        new_email = st.text_input("Email", key="signup_email")
        new_password = st.text_input("Password", type="password", key="signup_pass")
        if st.button("Create Account", use_container_width=True):
            with st.spinner("Creating account..."):
                user, error = signup(new_email, new_password)
                if user:
                    st.success("Account created! You are logged in.")
                    st.session_state["user"] = user
                    st.rerun()
                else:
                    st.error(f"Error: {error}")

# -----------------------------
# 2. HELPER FUNCTIONS
# -----------------------------

def render_comparison_table(error_list):
    """Renders the detailed error comparison table."""
    if not error_list:
        return "<div class='metric-success' style='padding:10px; text-align:center;'>🎉 Perfect Reading! Zero errors.</div>"

    rows = ""
    for err in error_list:
        e_type = err['type']
        expected = err['expected']
        actual = err['actual']
        
        if e_type == "mispronunciation":
            badge = "<span class='badge badge-mis'>Mispronounced</span>"
            actual_html = f"<span style='color:#d29922; font-weight:bold;'>{actual}</span>"
        elif e_type == "substitution":
            badge = "<span class='badge badge-sub'>Wrong Word</span>"
            actual_html = f"<span style='color:#ff7b72; font-weight:bold;'>{actual}</span>"
        elif e_type == "deletion":
            badge = "<span class='badge badge-del'>Skipped</span>"
            actual_html = "<i>(No Audio)</i>"
        elif e_type == "insertion":
            badge = "<span class='badge badge-ins'>Added</span>"
            actual_html = f"<span style='color:#58a6ff;'>{actual}</span>"
        else:
            badge = f"<span class='badge'>{e_type}</span>"
            actual_html = actual

        rows += f"<tr><td>{badge}</td><td><strong>{expected}</strong></td><td>{actual_html}</td></tr>"

    return textwrap.dedent(f"""
    <div style="overflow-x:auto;">
        <table class="comparison-table">
            <thead><tr><th style="width:20%">Error Type</th><th style="width:40%">Expected</th><th style="width:40%">You Said</th></tr></thead>
            <tbody>{rows}</tbody>
        </table>
    </div>
    """)

def render_highlighted_passage(alignment_data):
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
        elif status == "mispronunciation":
            html_parts.append(f"<span class='word-mispronunciation' title='Heard: {recognized}'>{target}</span>")
            
    return " ".join(html_parts)

def render_terminal_logs(logs):
    """Generates the Hacker-style Terminal HTML."""
    if not logs: return ""

    log_lines = ""
    for log in logs:
        ts = log.get('timestamp')
        if ts:
            ts_str = datetime.fromtimestamp(ts).strftime('%H:%M:%S')
        else:
            ts_str = datetime.now().strftime('%H:%M:%S')

        lvl = log.get('level', 'INFO')
        msg = log.get('message', '')
        
        log_lines += f"""<div class="log-entry">
            <span class="log-timestamp">[{ts_str}]</span>
            <span class="log-{lvl}">{lvl}</span>
            <span class="log-message">{msg}</span>
        </div>"""

    return textwrap.dedent(f"""
    <div class="terminal-window">
        <div class="terminal-header">
            <div class="terminal-title">system_logs — bash</div>
        </div>
        <div class="terminal-body">
            {log_lines}
            <div style="color: #3fb950; margin-top: 5px;">➜ root@backend: _</div>
        </div>
    </div>
    """)

def cycle_status_messages(placeholder, stop_event):
    messages = ["👂 Listening...", "✨ Analyzing...", "🐢 Checking pace...", "🌟 Formatting results..."]
    for msg in itertools.cycle(messages):
        if stop_event.is_set(): break
        placeholder.markdown(f"<h3 style='text-align: center; color: #8b949e;'>{msg}</h3>", unsafe_allow_html=True)
        time.sleep(1.5)

# -----------------------------
# 3. MAIN APP LOGIC
# -----------------------------

def main():
    # --- AUTH CHECK ---
    if "user" not in st.session_state:
        st.session_state["user"] = None

    if not st.session_state["user"]:
        show_login_page()
        return  # Stop here if not logged in

    # --- MAIN DASHBOARD (Only visible if logged in) ---
    user_email = st.session_state["user"].email
    
    with st.sidebar:
        st.caption(f"Logged in as:")
        st.write(f"👤 **{user_email}**")
        if st.button("Logout", use_container_width=True):
            logout()

    st.title("🗣️ Pronounce")
    st.caption("Ready to practice?")

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
                    r = requests.get(PASSAGE_URL, params={"language": lang_code}, timeout=3)
                    if r.status_code == 200:
                        st.session_state.current_passage = r.json()["passage"]
                        st.rerun()
                    else:
                        st.error("Server Error")
            except Exception:
                st.error("Backend Down")

    # Text Area
    text_len = len(st.session_state.current_passage)
    dynamic_height = max(150, int(text_len / 2.5))
    target_text = st.text_area("Read this:", value=st.session_state.current_passage, height=dynamic_height)

    # --- Audio Input ---
    audio_data = st.audio_input("Record your voice")

    if audio_data:
        st.audio(audio_data)
        
        if st.button("Analyze Reading", type="primary", use_container_width=True):
            audio_data.seek(0)
            files = {"file": ("recording.webm", audio_data, "audio/webm")}
            
            data = {
                "target_text": target_text, 
                "language": lang_code, 
                "user_id": st.session_state["user"].id
            }
            
            # Loading Animation
            status_placeholder = st.empty()
            stop_event = threading.Event()
            loader_thread = threading.Thread(target=cycle_status_messages, args=(status_placeholder, stop_event))
            add_script_run_ctx(loader_thread)
            loader_thread.start()
            
            try:
                response = requests.post(BACKEND_URL, files=files, data=data, timeout=60)
                
                stop_event.set()
                loader_thread.join()
                status_placeholder.empty()
                
                # --- NEW ERROR HANDLING WITH TOASTS ---
                if response.status_code != 200:
                    try:
                        # Try to get the clean message from backend (e.g., "Audio too short")
                        error_detail = response.json().get("detail", response.text)
                    except:
                        # Fallback if backend didn't send JSON
                        error_detail = f"Server Error ({response.status_code})"
                    
                    # SHOW THE FADING POPUP
                    show_custom_toast(error_detail, type="error")
                    st.stop() # Stop execution so we don't show empty graphs
                
                # If successful...
                result = response.json()
                # Optional: Show success toast
                show_custom_toast("Analysis Complete!", type="success")
                
            except Exception as e:
                stop_event.set()
                status_placeholder.empty()
                show_custom_toast(f"Connection Failed: {str(e)}", type="error")
                st.stop()

            # --- Results Display ---
            st.divider()
            
            # 1. EXTRACT METRICS
            metrics = result.get("metrics", {})
            alignment = result.get("word_alignment", [])
            error_list = result.get("error_analysis", [])
            logs = result.get("logs", [])
            
            # 2. CREATE TABS (MUST BE DONE BEFORE 'with t1:')
            t1, t2, t3, t4 = st.tabs(["📊 Summary", "🔍 Errors", "📖 Text", "💻 Logs"])

            # 3. FILL SUMMARY TAB
            with t1:
                st.subheader("Performance Overview")
                
                # --- ROW 1: SUCCESS METRICS ---
                c1, c2, c3 = st.columns(3)
                c1.metric("Overall Accuracy", f"{metrics.get('accuracy', 0)}%")
                c2.metric("Fluency Score", f"{metrics.get('fluency', 0)}/100")
                
                # Custom Green Card for "Correct Words"
                correct_n = metrics.get("correct_count", 0)
                c3.markdown(f"""
                <div class="metric-container card-correct">
                    <div class="metric-label">Words Read Perfectly</div>
                    <div class="metric-value">{correct_n}</div>
                    <div class="sub-metric">Keep it up!</div>
                </div>""", unsafe_allow_html=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                # --- ROW 2: DETAILED BREAKDOWN (Colored Cards) ---
                k1, k2, k3, k4 = st.columns(4)
                
                # 1. Mispronounced (Yellow)
                mis = metrics.get("mispronunciation_count", 0)
                k1.markdown(f"""
                <div class="metric-container card-mis">
                    <div class="metric-label">Mispronounced</div>
                    <div class="metric-value">{mis}</div>
                    <div class="sub-metric">Close attempts</div>
                </div>""", unsafe_allow_html=True)
                
                # 2. Wrong Words (Red)
                sub = metrics.get("substitution_count", 0)
                k2.markdown(f"""
                <div class="metric-container card-wrong">
                    <div class="metric-label">Wrong Words</div>
                    <div class="metric-value">{sub}</div>
                    <div class="sub-metric">Try again</div>
                </div>""", unsafe_allow_html=True)
                
                # 3. Skipped (Gray)
                dele = metrics.get("deletion_count", 0)
                k3.markdown(f"""
                <div class="metric-container card-skip">
                    <div class="metric-label">Skipped</div>
                    <div class="metric-value">{dele}</div>
                    <div class="sub-metric">Missed</div>
                </div>""", unsafe_allow_html=True)
                
                # 4. Stutters (Orange)
                stut = metrics.get("stutter_count", 0)
                k4.markdown(f"""
                <div class="metric-container card-stutter">
                    <div class="metric-label">Stutters</div>
                    <div class="metric-value">{stut}</div>
                    <div class="sub-metric">Repeats</div>
                </div>""", unsafe_allow_html=True)

                # --- ROW 3: SPEEDOMETER (PACE) ---
                st.markdown("<br>", unsafe_allow_html=True)
                wpm = metrics.get('wpm', 0)
                
                # Logic: Cap at 200 WPM for the visual bar
                display_wpm = min(wpm, 200)
                marker_pos = (display_wpm / 200) * 100
                
                if wpm < 80: speed_text = "Slow"
                elif wpm > 150: speed_text = "Fast"
                else: speed_text = "Optimal"

                st.markdown(f"""
                <div class="speed-container">
                    <div class="speed-header">
                        <span class="speed-title">Speaking Pace</span>
                        <span class="speed-value">{wpm} <span style="font-size:0.8em; color:#8b949e;">WPM</span></span>
                    </div>
                    <div class="speed-bar-wrapper">
                        <div class="speed-bar-bg"></div>
                        <div class="speed-marker" style="left: {marker_pos}%;"></div>
                    </div>
                    <div class="speed-labels">
                        <span>Slow</span>
                        <span>Optimal (110-150)</span>
                        <span>Fast</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            with t2:
                st.markdown(render_comparison_table(error_list), unsafe_allow_html=True)

            with t3:
                st.markdown(f"<div class='passage-box'>{render_highlighted_passage(alignment)}</div>", unsafe_allow_html=True)

            with t4:
                st.subheader("Backend Logs")
                st.markdown(render_terminal_logs(logs), unsafe_allow_html=True)

if __name__ == "__main__":
    main()