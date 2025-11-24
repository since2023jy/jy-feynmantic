import streamlit as st
import time
import html
import random
from dataclasses import dataclass
import streamlit.components.v1 as components

# ==========================================
# 1. CONFIGURATION
# ==========================================
@dataclass(frozen=True)
class AppConfig:
    VERSION = "13.0.0 (Feature Complete)"
    MAX_CHARS = 5000
    STORAGE_KEY = "feynman_v13_data"
    COLOR_RUTHLESS = "#ff4545"
    COLOR_ASSISTANT = "#00f2ff"
    BG_RUTHLESS = "radial-gradient(circle at 50% 0%, #450a0a 0%, #020617 60%, #000000 100%)"
    BG_ASSISTANT = "radial-gradient(circle at 50% 0%, #0e4a5a 0%, #020617 60%, #000000 100%)"

# ==========================================
# 2. SYSTEM SETUP
# ==========================================
st.set_page_config(
    page_title="FeynmanTic",
    page_icon="💠",
    layout="centered",
    initial_sidebar_state="collapsed",
    menu_items={'About': f"v{AppConfig.VERSION}"}
)

def init_state():
    defaults = {
        'entropy_state': 'CHAOS',
        'is_hardcore': st.query_params.get("mode") == "ruthless",
        'feedback': "AWAITING INPUT...",
        'input_text': "",
        'student_level': 'University', # [New] 학생 레벨
        'is_spectator': False,         # [New] 관중 모드
    }
    for k, v in defaults.items():
        if k not in st.session_state: st.session_state[k] = v

init_state()

# ==========================================
# 3. DESIGN SYSTEM (CSS)
# ==========================================
@st.cache_data(show_spinner=False)
def get_css(is_hardcore: bool) -> str:
    primary = AppConfig.COLOR_RUTHLESS if is_hardcore else AppConfig.COLOR_ASSISTANT
    bg = AppConfig.BG_RUTHLESS if is_hardcore else AppConfig.BG_ASSISTANT
    
    return f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Inter:wght@300;400;600&display=swap');
    
    :root {{ --primary: {primary}; --bg-gradient: {bg}; }}

    html, body {{ background-color: #000000 !important; overscroll-behavior: none; }}
    .stApp {{ background: var(--bg-gradient); background-attachment: fixed; min-height: 100dvh; }}
    #MainMenu, header, footer, div[data-testid="stDecoration"] {{ display: none !important; }}

    /* Typography */
    h1, h2, .mono {{ font-family: 'JetBrains Mono', monospace !important; letter-spacing: -0.03em; }}
    p, textarea, button, div {{ font-family: 'Inter', sans-serif !important; letter-spacing: 0.01em; }}

    /* Input Area */
    .stTextArea textarea {{
        background-color: rgba(20, 20, 20, 0.4) !important;
        color: #fff !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 16px !important;
        backdrop-filter: blur(20px);
        padding: 1.5rem !important;
        font-size: 16px !important;
        resize: none !important;
        min-height: 140px !important;
        caret-color: var(--primary);
        transition: all 0.3s ease;
    }}
    .stTextArea textarea:focus {{
        border-color: var(--primary) !important;
        box-shadow: 0 0 30px rgba({primary}, 0.2) !important;
    }}

    /* Buttons */
    div.stButton > button {{
        width: 100%; height: 56px; border-radius: 14px;
        background: linear-gradient(180deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0) 100%);
        border: 1px solid rgba(255,255,255,0.1);
        color: var(--primary); font-family: 'JetBrains Mono', monospace !important; font-weight: 700;
        transition: all 0.2s; margin-top: 10px;
    }}
    div.stButton > button:hover {{ border-color: var(--primary); transform: translateY(-2px); }}
    div.stButton > button:active {{ transform: scale(0.98); }}

    /* [New] Visual Map Styles (Mario/Tree) */
    .map-node {{
        width: 40px; height: 40px; border-radius: 50%; 
        background: rgba(255,255,255,0.1); border: 2px solid rgba(255,255,255,0.2);
        display: flex; align-items: center; justify-content: center;
        font-weight: bold; color: white; position: relative; z-index: 2;
        transition: all 0.5s ease;
    }}
    .map-node.active {{ background: var(--primary); border-color: white; box-shadow: 0 0 20px var(--primary); color: black; }}
    .map-line {{ position: absolute; background: rgba(255,255,255,0.1); z-index: 1; }}
    
    /* HUD */
    .hud-box {{
        background: rgba(10, 10, 10, 0.6); border: 1px solid rgba(255,255,255,0.08); border-left: 3px solid var(--primary);
        padding: 1rem 1.5rem; border-radius: 12px; color: var(--primary);
        font-family: 'JetBrains Mono', monospace; font-size: 0.85rem;
        backdrop-filter: blur(15px); min-height: 60px; display: flex; align-items: center; gap: 12px;
    }}

    .block-container {{ padding-top: 3rem; padding-bottom: 5rem; max-width: 680px; }}
    
    /* [New] Spectator Mode Overlay */
    .spectator-overlay {{
        position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        background: rgba(0,0,0,0.8); z-index: 999; pointer-events: none;
        display: flex; align-items: center; justify-content: center;
        font-family: 'JetBrains Mono'; color: var(--primary); letter-spacing: 2px;
    }}
    </style>
    """

st.markdown(get_css(st.session_state.is_hardcore), unsafe_allow_html=True)

# ==========================================
# 4. LOGIC
# ==========================================
def handle_reset():
    st.session_state.entropy_state = 'CHAOS'
    st.session_state.input_text = ""
    st.session_state.feedback = "SYSTEM RESET."

def handle_analyze():
    if not st.session_state.input_text.strip(): return
    st.session_state.entropy_state = 'PROCESSING'

def toggle_spectator():
    st.session_state.is_spectator = not st.session_state.is_spectator

def apply_cheat():
    # [New] Cunning Mode Logic
    cheats = [
        "According to First Principles, we must deconstruct this problem into...",
        "The entropy of this system can be reduced by applying...",
        "If we apply Popper's falsification to this premise...",
    ]
    st.session_state.input_text = random.choice(cheats)

# ==========================================
# 5. UI RENDER
# ==========================================

# Header
c1, c2 = st.columns([6, 4])
with c1:
    color = AppConfig.COLOR_RUTHLESS if st.session_state.is_hardcore else AppConfig.COLOR_ASSISTANT
    st.markdown(f"<div class='mono' style='font-weight:900; font-size:1.5rem;'>FEYNMANTIC<span style='color:{color}; font-size:0.6em; vertical-align:top; margin-left:4px;'>OS v13</span></div>", unsafe_allow_html=True)
with c2:
    # Mode Toggles
    c2_1, c2_2 = st.columns(2)
    with c2_1:
        spec_icon = "👁️" if st.session_state.is_spectator else "🕶️"
        if st.button(spec_icon, help="Spectator Mode"): toggle_spectator()
    with c2_2:
        btn_text = "🔥" if st.session_state.is_hardcore else "💎"
        if st.button(btn_text, help="Toggle Hardcore"):
            st.session_state.is_hardcore = not st.session_state.is_hardcore
            st.query_params["mode"] = "ruthless" if st.session_state.is_hardcore else "assistant"
            st.rerun()

st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

# Spectator Mode Overlay
if st.session_state.is_spectator:
    st.markdown(f"""
    <div class="spectator-overlay">
        <div style="text-align:center;">
            <div style="font-size:3rem; animation:pulse 1s infinite;">👁️</div>
            <div>SPECTATOR MODE ACTIVE</div>
            <div style="font-size:0.8rem; opacity:0.7;">Observing Neural Network...</div>
        </div>
    </div>
    <style>@keyframes pulse {{ 0% {{opacity:0.5}} 50% {{opacity:1}} 100% {{opacity:0.5}} }}</style>
    """, unsafe_allow_html=True)

# Status Area
status_area = st.empty()
if st.session_state.entropy_state == 'CHAOS':
    with status_area.container():
        st.markdown(f"""<div class="hud-box"><span style="animation:blink 1s infinite">_</span> {st.session_state.feedback}</div>""", unsafe_allow_html=True)
        # Idle Visual
        glow = AppConfig.COLOR_RUTHLESS if st.session_state.is_hardcore else AppConfig.COLOR_ASSISTANT
        st.markdown(f"""<div style="display:flex; justify-content:center; margin:40px 0;"><div style="width:100px; height:100px; border-radius:50%; background:radial-gradient(circle, {glow}40 0%, transparent 70%); box-shadow: 0 0 80px {glow}30;"></div></div>""", unsafe_allow_html=True)

elif st.session_state.entropy_state == 'PROCESSING':
    loader = st.empty()
    color = AppConfig.COLOR_RUTHLESS if st.session_state.is_hardcore else AppConfig.COLOR_ASSISTANT
    for i in range(31):
        loader.markdown(f"""<div style="background:rgba(0,0,0,0.8); padding:20px 40px; border-radius:50px; border:1px solid {color}50; position:fixed; top:50%; left:50%; transform:translate(-50%,-50%); z-index:9999; backdrop-filter:blur(20px);"><span style="font-family:'JetBrains Mono'; color:white;">OPTIMIZING... {int(i*3.33)}%</span></div>""", unsafe_allow_html=True)
        time.sleep(0.03)
    st.session_state.entropy_state = 'CRYSTAL'
    st.session_state.feedback = "CRYSTALLIZATION COMPLETE."
    st.rerun()

elif st.session_state.entropy_state == 'CRYSTAL':
    with status_area.container():
        st.markdown(f"""<div class="hud-box" style="border-color:#10b981; color:#10b981;"><span>✓</span> LOGIC VERIFIED.</div>""", unsafe_allow_html=True)
        st.markdown(f"""<div style="display:flex; justify-content:center; margin:40px 0;"><div style="font-size:4rem; filter:drop-shadow(0 0 30px #10b98160);">💠</div></div>""", unsafe_allow_html=True)

# --- TABS: The 3 World Views ---
t1, t2, t3 = st.tabs(["🗺️ STUDENT", "🌳 PRO", "🌌 EXPLORER"])

# 1. Student View (Mario Map)
with t1:
    # [New] Student Level Selection
    cols = st.columns([2, 1])
    with cols[0]:
        st.caption("ACADEMIC JOURNEY")
    with cols[1]:
        lvl = st.selectbox("Level", ["Elementary", "Middle", "High", "Univ"], label_visibility="collapsed", index=3)
    
    # [New] Visual Mario Map
    active_class = "active" if st.session_state.entropy_state == 'CRYSTAL' else ""
    st.markdown(f"""
    <div style="position:relative; height:100px; margin-top:20px; display:flex; align-items:center; justify-content:space-between; padding:0 20px;">
        <div class="map-line" style="width:90%; top:50%; left:5%; height:2px;"></div>
        <div class="map-node active">1</div>
        <div class="map-node {active_class}">2</div>
        <div class="map-node">3</div>
        <div class="map-node">4</div>
    </div>
    <div style="text-align:center; font-size:0.8em; opacity:0.6; margin-top:10px;">Current Stage: Logic Formulation ({lvl})</div>
    """, unsafe_allow_html=True)

# 2. Pro View (Tech Tree)
with t2:
    # [New] Visual Tech Tree
    active_color = "#10b981" if st.session_state.entropy_state == 'CRYSTAL' else "rgba(255,255,255,0.2)"
    st.markdown(f"""
    <div style="display:flex; flex-direction:column; align-items:center; gap:10px; margin-top:20px;">
        <div style="border:1px solid {active_color}; padding:5px 15px; border-radius:4px; color:{active_color}; font-size:0.8em;">GOAL: IPO</div>
        <div style="width:1px; height:20px; background:rgba(255,255,255,0.2);"></div>
        <div style="display:flex; gap:20px;">
            <div style="border:1px solid rgba(255,255,255,0.2); padding:5px 10px; border-radius:4px; font-size:0.7em;">Product</div>
            <div style="border:1px solid rgba(255,255,255,0.2); padding:5px 10px; border-radius:4px; font-size:0.7em;">Sales</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# 3. Explorer View (Galaxy)
with t3:
    # [New] Visual Galaxy
    st.markdown(f"""
    <div style="display:flex; justify-content:center; align-items:center; height:150px; perspective: 500px;">
        <div style="width:60px; height:60px; border:1px solid var(--primary); border-radius:50%; animation: orbit 4s linear infinite; position:absolute;"></div>
        <div style="width:100px; height:100px; border:1px solid rgba(255,255,255,0.1); border-radius:50%; animation: orbit 7s linear infinite reverse; position:absolute;"></div>
        <div style="width:10px; height:10px; background:white; border-radius:50%; box-shadow:0 0 10px white;"></div>
    </div>
    <style>@keyframes orbit {{ from{{transform:rotateX(60deg) rotateZ(0deg)}} to{{transform:rotateX(60deg) rotateZ(360deg)}} }}</style>
    """, unsafe_allow_html=True)

st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

# Input Area
c_input, c_cheat = st.columns([8, 1])
with c_input:
    st.text_area(
        "Input",
        key="input_text",
        placeholder="Initialize thought sequence...",
        height=140,
        label_visibility="collapsed",
        disabled=st.session_state.entropy_state == 'PROCESSING'
    )
with c_cheat:
    # [New] Cunning Mode Button
    st.markdown("<div style='height:5px'></div>", unsafe_allow_html=True)
    if st.button("🦊", help="Cunning Mode (Auto-Fill)"):
        apply_cheat()
        st.rerun()

# Action Buttons
if st.session_state.entropy_state == 'CRYSTAL':
    if st.button("⚡ RESET SYSTEM", type="primary"):
        handle_reset()
        st.rerun()
else:
    if st.button("🚀 EXECUTE", disabled=st.session_state.entropy_state == 'PROCESSING', type="primary"):
        handle_analyze()
        st.rerun()

# JS Bridge
components.html(f"""
<script>
    const STORAGE_KEY = '{AppConfig.STORAGE_KEY}';
    const textArea = parent.document.querySelector('textarea');
    const buttons = parent.document.querySelectorAll('button');
    let executeBtn = null;
    buttons.forEach(b => {{ if(b.innerText.includes("EXECUTE")) executeBtn = b; }});

    if(textArea && !textArea.dataset.bound) {{
        textArea.dataset.bound = "true";
        let timeout;
        textArea.addEventListener('input', () => {{
            clearTimeout(timeout);
            timeout = setTimeout(() => {{
                try {{ localStorage.setItem(STORAGE_KEY, textArea.value); }} catch(e){{}}
            }}, 300);
        }});
        
        // Restore
        try {{
            const saved = localStorage.getItem(STORAGE_KEY);
            if(saved && textArea.value === "") {{
                const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value").set;
                setter.call(textArea, saved);
                textArea.dispatchEvent(new Event('input', {{ bubbles: true }}));
            }}
        }} catch(e){{}}
        
        const isMobile = ('ontouchstart' in window) && (window.innerWidth < 768);
        textArea.addEventListener('keydown', (e) => {{
            if(e.key === 'Enter' && !e.shiftKey && !e.isComposing) {{
                if(!isMobile && executeBtn && !executeBtn.disabled) {{
                    e.preventDefault();
                    executeBtn.click();
                }}
            }}
        }});
    }}
    if(executeBtn) executeBtn.onclick = () => {{ if(document.activeElement) document.activeElement.blur(); }};
    if(textArea && textArea.value === "") try {{ localStorage.removeItem(STORAGE_KEY); }} catch(e){{}}
</script>
""", height=0, width=0)
