import streamlit as st
import requests
import time
import threading
import itertools
import textwrap
import pandas as pd
import plotly.express as px
from pathlib import Path
from datetime import datetime, timedelta
from streamlit.runtime.scriptrunner import add_script_run_ctx
import base64
import extra_streamlit_components as stx

# --- AUTH IMPORT ---
from auth_client import login, signup, logout

# -----------------------------
# Configuration
# -----------------------------
class SessionUser:
    def __init__(self, id, email):
        self.id = id
        self.email = email
        
st.set_page_config(
    page_title="Pronounce AI",
    layout="wide",  # WIDE layout for Dashboard
    initial_sidebar_state="expanded"
)

# Load External CSS
def load_css():
    css_path = Path(__file__).parent / "style.css"
    if css_path.exists():
        with open(css_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

def show_custom_toast(message, type="error"):
    icon = "⚠️" if type == "error" else "🎉"
    css_class = "toast-error" if type == "error" else "toast-success"
    st.markdown(f"""
        <div class="toast-container {css_class}">
            <span style="font-size: 1.5rem;">{icon}</span>
            <span>{message}</span>
        </div>
    """, unsafe_allow_html=True)

load_css()

# API Config
BACKEND_URL = "http://127.0.0.1:8000/process-audio/"
PASSAGE_URL = "http://127.0.0.1:8000/get-passage/"
TTS_URL = "http://127.0.0.1:8000/tts/"
ANALYTICS_URL = "http://127.0.0.1:8000/analytics/"

LANGUAGES = {
    "English": "en",
    "Hindi (हिंदी)": "hi",
    "Tamil (தமிழ்)": "ta",
    "Telugu (తెలుగు)": "te",
    "Kannada (ಕನ್ನಡ)": "kn",
    "Gujarati (ગુજરાતી)": "gu",
}

# -----------------------------
# 1. AUTHENTICATION
# -----------------------------

def show_login_page(cookie_manager):
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.markdown("<h1 style='text-align: center;'>🔐 Login to Pronounce</h1>", unsafe_allow_html=True)
        tab1, tab2 = st.tabs(["Login", "Sign Up"])
        
        with tab1:
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_pass")
            if st.button("Login", width="stretch"):
                with st.spinner("Logging in..."):
                    user, error = login(email, password)
                    if user:
                        # --- SAVE COOKIE (Persist Session) ---
                        # We store ID and Email separated by '::'
                        cookie_manager.set("pronounce_auth", f"{user.id}::{user.email}", key="set_login_cookie")
                        
                        st.session_state["user"] = user
                        st.success("Welcome back!")
                        time.sleep(0.5) # Give cookie time to set
                        st.rerun()
                    else:
                        st.error(f"Error: {error}")

        with tab2:
            new_email = st.text_input("Email", key="signup_email")
            new_password = st.text_input("Password", type="password", key="signup_pass")
            if st.button("Create Account", width="stretch"):
                with st.spinner("Creating account..."):
                    user, error = signup(new_email, new_password)
                    if user:
                        # --- SAVE COOKIE ---
                        cookie_manager.set("pronounce_auth", f"{user.id}::{user.email}", key="set_signup_cookie")
                        
                        st.success("Account created!")
                        st.session_state["user"] = user
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error(f"Error: {error}")
# -----------------------------
# 2. HELPER FUNCTIONS
# -----------------------------

def render_comparison_table(error_list):
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
        status = item.get("status", "unknown")
        target = item.get("target", "")
        recognized = item.get("recognized", "")
        
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
    if not logs: return ""
    log_lines = ""
    for log in logs:
        ts = log.get('timestamp')
        ts_str = datetime.fromtimestamp(ts).strftime('%H:%M:%S') if ts else datetime.now().strftime('%H:%M:%S')
        lvl = log.get('level', 'INFO')
        msg = log.get('message', '')
        log_lines += f"""<div class="log-entry"><span class="log-timestamp">[{ts_str}]</span><span class="log-{lvl}">{lvl}</span><span class="log-message">{msg}</span></div>"""

    return f"""<div class="terminal-window"><div class="terminal-header"><div class="terminal-title">system_logs — bash</div></div><div class="terminal-body">{log_lines}<div style="color: #3fb950; margin-top: 5px;">➜ root@backend: _</div></div></div>"""

def cycle_status_messages(placeholder, stop_event):
    messages = ["👂 Listening...", "✨ Analyzing...", "🐢 Checking pace...", "🌟 Formatting results..."]
    for msg in itertools.cycle(messages):
        if stop_event.is_set(): break
        placeholder.markdown(f"<h3 style='text-align: center; color: #8b949e;'>{msg}</h3>", unsafe_allow_html=True)
        time.sleep(1.5)
        
def autoplay_audio(audio_bytes):
            import base64
            b64 = base64.b64encode(audio_bytes).decode()
            md = f"""
                <audio autoplay style="display:none;">
                <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
                </audio>
            """
            st.markdown(md, unsafe_allow_html=True)

# -----------------------------
# 3. PRACTICE MODE (Main App)
# -----------------------------
def render_practice_mode(lang_code):
    st.title("🎤 Practice Studio")
    st.caption("Read aloud and get instant feedback.")

    # --- HELPER: Invisible Audio Player ---
    def autoplay_audio(audio_bytes):
        import base64
        b64 = base64.b64encode(audio_bytes).decode()
        md = f"""
            <audio autoplay style="display:none;">
            <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
            </audio>
        """
        st.markdown(md, unsafe_allow_html=True)
    
    # --- CONTROL ROW (Difficulty + New Passage) ---
    c1, c2 = st.columns([1, 1]) # Split space 50/50

    with c1:
        # Local selector for difficulty
        difficulty = st.selectbox("Difficulty Level", ["Easy", "Medium", "Hard"], index=0, label_visibility="collapsed")
        diff_code = difficulty.lower()

    with c2:
        # Button is now right next to the dropdown
        if st.button("🔄 New Passage", width="stretch"):
            try:
                with st.spinner("Fetching text..."):
                    # Pass the locally selected 'diff_code'
                    params = {"language": lang_code, "difficulty": diff_code}
                    r = requests.get(PASSAGE_URL, params=params, timeout=3)
                    
                    if r.status_code == 200:
                        st.session_state.current_passage = r.json()["passage"]
                        st.session_state.current_difficulty = diff_code
                        st.session_state["analysis_result"] = None 
                        st.rerun()
                    else:
                        st.error("Server Error")
            except Exception:
                st.error("Backend Down")

    if "current_passage" not in st.session_state:
        st.session_state.current_passage = "Click 'New Passage' to start."
    if "current_difficulty" not in st.session_state:
        st.session_state.current_difficulty = "easy"
    
    if "analysis_result" not in st.session_state:
        st.session_state["analysis_result"] = None

    text_len = len(st.session_state.current_passage)
    dynamic_height = max(150, int(text_len / 2.5))
    target_text = st.text_area("Read this:", value=st.session_state.current_passage, height=dynamic_height)

    audio_data = st.audio_input("Record your voice")

    if audio_data:
        st.audio(audio_data)
        
        if st.button("Analyze Reading", type="primary", width="stretch"):
            audio_data.seek(0)
            files = {"file": ("recording.webm", audio_data, "audio/webm")}
            data = {
                "target_text": target_text, 
                "language": lang_code, 
                "difficulty": st.session_state.current_difficulty,
                "user_id": st.session_state["user"].id
            }
            
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
                
                if response.status_code != 200:
                    try: error_detail = response.json().get("detail", response.text)
                    except: error_detail = f"Server Error ({response.status_code})"
                    show_custom_toast(error_detail, type="error")
                    st.stop()
                
                st.session_state["analysis_result"] = response.json()
                show_custom_toast("Analysis Complete!", type="success")
                st.rerun()
                
            except Exception as e:
                stop_event.set()
                status_placeholder.empty()
                show_custom_toast(f"Connection Failed: {str(e)}", type="error")
                st.stop()

    # --- RESULTS DISPLAY ---
    if st.session_state["analysis_result"]:
        result = st.session_state["analysis_result"]
        metrics = result.get("metrics", {})
        alignment = result.get("word_alignment", [])
        error_list = result.get("error_analysis", [])
        logs = result.get("logs", [])
        
        t1, t2, t3, t4, t5 = st.tabs(["📊 Summary", "🔍 Errors", "🎧 Practice Zone", "📖 Text", "💻 Logs"])

        with t1:
            st.subheader("Performance Overview")
            c1, c2, c3 = st.columns(3)
            c1.metric("Overall Accuracy", f"{metrics.get('accuracy', 0)}%")
            c2.metric("Fluency Score", f"{metrics.get('fluency', 0)}/100")
            c3.markdown(f"<div class='metric-container card-correct'><div class='metric-label'>Words Read Perfectly</div><div class='metric-value'>{metrics.get('correct_count', 0)}</div></div>", unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            k1, k2, k3, k4 = st.columns(4)
            k1.markdown(f"<div class='metric-container card-mis'><div class='metric-label'>Mispronounced</div><div class='metric-value'>{metrics.get('mispronunciation_count', 0)}</div></div>", unsafe_allow_html=True)
            k2.markdown(f"<div class='metric-container card-wrong'><div class='metric-label'>Wrong Words</div><div class='metric-value'>{metrics.get('substitution_count', 0)}</div></div>", unsafe_allow_html=True)
            k3.markdown(f"<div class='metric-container card-skip'><div class='metric-label'>Skipped</div><div class='metric-value'>{metrics.get('deletion_count', 0)}</div></div>", unsafe_allow_html=True)
            k4.markdown(f"<div class='metric-container card-stutter'><div class='metric-label'>Stutters</div><div class='metric-value'>{metrics.get('stutter_count', 0)}</div></div>", unsafe_allow_html=True)

            # Speedometer
            wpm = metrics.get('wpm', 0)
            marker_pos = (min(wpm, 200) / 200) * 100
            st.markdown(f"""<div class="speed-container"><div class="speed-header"><span class="speed-title">Speaking Pace</span><span class="speed-value">{wpm} WPM</span></div><div class="speed-bar-wrapper"><div class="speed-bar-bg"></div><div class="speed-marker" style="left: {marker_pos}%;"></div></div><div class="speed-labels"><span>Slow</span><span>Optimal</span><span>Fast</span></div></div>""", unsafe_allow_html=True)

        with t2:
            st.subheader("Word-by-Word Analysis")
            st.markdown(render_comparison_table(error_list), unsafe_allow_html=True)

        with t3:
            st.subheader("🎧 Practice Zone")
            st.caption("Click 'Listen' to hear the correct pronunciation immediately.")
            
            # 1. Filter the errors
            mispronounced = [e for e in error_list if e['type'] == 'mispronunciation']
            substitutions = [e for e in error_list if e['type'] == 'substitution']
            
            if not mispronounced and not substitutions:
                st.success("🌟 Perfect reading! Nothing to practice here.")
            else:
                # Create two main columns for the "Tables"
                col_mis, col_sub = st.columns(2)
                
                # --- LEFT COLUMN: Mispronounced ---
                with col_mis:
                    st.markdown("### 🗣️ Mispronounced")
                    if not mispronounced:
                        st.info("No pronunciation errors!")
                    else:
                        for i, err in enumerate(mispronounced):
                            # Create a row-like structure: Word on left, Button on right
                            r1, r2 = st.columns([0.65, 0.35])
                            with r1:
                                st.markdown(f"**{err['expected']}**")
                                st.caption(f"You said: *{err['actual']}*")
                            with r2:
                                if st.button("👂 Listen", key=f"mis_btn_{i}", width="stretch"):
                                    try:
                                        params = {"text": err['expected'], "language": lang_code}
                                        r = requests.get(TTS_URL, params=params)
                                        if r.status_code == 200:
                                            autoplay_audio(r.content)
                                        else:
                                            st.error("TTS Error")
                                    except Exception as e:
                                        st.error("Conn Error")
                            st.divider()

                # --- RIGHT COLUMN: Wrong Words ---
                with col_sub:
                    st.markdown("### 🔀 Wrong Words")
                    if not substitutions:
                        st.info("No word substitutions!")
                    else:
                        for i, err in enumerate(substitutions):
                            r1, r2 = st.columns([0.65, 0.35])
                            with r1:
                                st.markdown(f"**{err['expected']}**")
                                st.caption(f"You said: *{err['actual']}*")
                            with r2:
                                if st.button("👂 Listen", key=f"sub_btn_{i}", width="stretch"):
                                    try:
                                        params = {"text": err['expected'], "language": lang_code}
                                        r = requests.get(TTS_URL, params=params)
                                        if r.status_code == 200:
                                            autoplay_audio(r.content)
                                        else:
                                            st.error("TTS Error")
                                    except Exception as e:
                                        st.error("Conn Error")
                            st.divider()
        with t4:
            st.markdown(f"<div class='passage-box'>{render_highlighted_passage(alignment)}</div>", unsafe_allow_html=True)

        with t5:
            st.subheader("Backend Logs")
            st.markdown(render_terminal_logs(logs), unsafe_allow_html=True)
# -----------------------------
# 4. ANALYTICS DASHBOARD (FIXED)
# -----------------------------
def render_dashboard():
    st.title("📈 Progress Analytics")
    st.caption("Track improvement over time.")

    user_id = st.session_state["user"].id
    
    # Fetch Data
    with st.spinner("Loading history..."):
        try:
            r = requests.get(f"{ANALYTICS_URL}{user_id}")
            if r.status_code == 200:
                payload = r.json()
                # UNPACK THE NEW BACKEND STRUCTURE
                stats = payload.get("stats", {})
                history = payload.get("history", [])
                error_dist = payload.get("errors", {})
            else:
                st.error("Failed to fetch analytics.")
                return
        except Exception as e:
            st.error(f"Connection Error: {e}")
            return

    if not history:
        st.info("No practice sessions found yet. Go to 'Practice Mode' and record your first session!")
        return

    # --- 1. TOP CARDS (Big Stats) ---
    st.divider()
    
    # Use the pre-calculated stats from backend
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Sessions", stats.get("total_attempts", 0))
    c2.metric("Avg Accuracy", f"{stats.get('avg_accuracy', 0)}%")
    c3.metric("Avg WPM", f"{stats.get('avg_wpm', 0)}")

    # --- 2. PREPARE HISTORY DATA ---
    df = pd.DataFrame(history)
    if not df.empty:
        df['created_at'] = pd.to_datetime(df['created_at'])
        df = df.sort_values('created_at')

        # --- LINE CHART: Performance Trends ---
        st.subheader("📊 Performance Over Time")
        
        tab_wpm, tab_acc = st.tabs(["⚡ Speed (WPM)", "🎯 Accuracy"])
        
        with tab_wpm:
            fig_wpm = px.line(df, x='created_at', y='wpm', markers=True, 
                              title="Words Per Minute Trend",
                              line_shape="spline",
                              labels={'wpm': 'Speed (WPM)', 'created_at': 'Date'})
            fig_wpm.update_traces(line_color='#3498db')
            # FIX: width="stretch"
            st.plotly_chart(fig_wpm, width="stretch")

        with tab_acc:
            fig_acc = px.line(df, x='created_at', y=['accuracy_score', 'fluency_score'], markers=True,
                              title="Accuracy & Fluency Trends",
                              line_shape="spline")
            # FIX: width="stretch"
            st.plotly_chart(fig_acc, width="stretch")

    # --- 3. PIE CHART: Error Distribution ---
    st.subheader("🚧 Error Breakdown")
    
    if error_dist:
        err_df = pd.DataFrame(list(error_dist.items()), columns=['Error Type', 'Count'])
        
        c_chart, c_text = st.columns([2, 1])
        
        with c_chart:
            fig_pie = px.pie(err_df, values='Count', names='Error Type', 
                             title="Distribution of Mistakes",
                             hole=0.4,
                             color_discrete_sequence=px.colors.qualitative.Pastel)
            # FIX: width="stretch"
            st.plotly_chart(fig_pie, width="stretch")
            
        with c_text:
            st.markdown("### Top Issues")
            sorted_errors = sorted(error_dist.items(), key=lambda x: x[1], reverse=True)
            for e_type, count in sorted_errors:
                st.write(f"**{e_type.title()}**: {count} times")
    else:
        st.success("No significant errors recorded in your history yet!")

    # --- 4. RECENT HISTORY TABLE ---
    st.subheader("📜 Recent Sessions")
    display_df = df[['created_at', 'accuracy_score', 'wpm', 'fluency_score']].sort_values('created_at', ascending=False).head(10)
    # FIX: width="stretch"
    st.dataframe(display_df, width="stretch")

# -----------------------------
# 5. MAIN ENTRY POINT
# -----------------------------
def main():
    # 1. Initialize Cookie Manager
    cookie_manager = stx.CookieManager()

    # 2. Auto-Login Check (If user is not in state, check cookies)
    if "user" not in st.session_state or st.session_state["user"] is None:
        cookie_val = cookie_manager.get("pronounce_auth")
        if cookie_val:
            try:
                # Reconstruct user object from the cookie string "ID::Email"
                uid, uemail = cookie_val.split("::")
                st.session_state["user"] = SessionUser(uid, uemail)
            except Exception:
                # If cookie is corrupted, delete it
                cookie_manager.delete("pronounce_auth")
                st.session_state["user"] = None
        else:
            st.session_state["user"] = None

    # 3. If still no user, show Login Page
    if not st.session_state["user"]:
        show_login_page(cookie_manager) # Pass the manager to the login page
        return

    # --- SIDEBAR NAV ---
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/2995/2995101.png", width=50)
        st.markdown(f"### Hello, \n**{st.session_state['user'].email}**")
        
        mode = st.radio("Navigation", ["🎤 Practice Mode", "📈 Analytics Dashboard"], index=0)
        
        st.divider()
        col_lang = st.container()
        with col_lang:
            selected_language = st.selectbox("Language", list(LANGUAGES.keys()))
            lang_code = LANGUAGES[selected_language]
            
        
        
        st.divider()
        
        if st.button("Logout", width="stretch"):
            # --- DELETE COOKIE ON LOGOUT (SAFE MODE) ---
            try:
                cookie_manager.delete("pronounce_auth")
            except KeyError:
                # If cookie is already gone, just ignore the error
                pass
            
            logout()
            st.rerun()
            
    # --- ROUTING ---
    if mode == "🎤 Practice Mode":
        render_practice_mode(lang_code)
    else:
        render_dashboard()
if __name__ == "__main__":
    main()