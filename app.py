import streamlit as st
import google.generativeai as genai
import json
import time
import random

# -----------------------------------------------------------------------------
# 1. VISUAL OVERHAUL (CSS INJECTION)
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Glitch Hunter: ZERO", page_icon="👾", layout="centered")

# [Custom Font & Animation Loading]
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Black+Ops+One&display=swap');

    /* 1. 전체 배경 및 CRT 효과 (레트로 해커 감성) */
    .stApp {
        background-color: #050505;
        background-image: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.25) 50%), linear-gradient(90deg, rgba(255, 0, 0, 0.06), rgba(0, 255, 0, 0.02), rgba(0, 0, 255, 0.06));
        background-size: 100% 2px, 3px 100%;
        color: #00ff41;
        font-family: 'Share Tech Mono', monospace;
    }
    
    /* 화면 깜빡임(Rerun) 숨기기 위한 트릭 */
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display:none;}
    
    /* 2. 타이틀 스타일링 (Glitch Effect) */
    .hacker-header {
        text-align: center; font-family: 'Black Ops One', cursive; font-size: 50px;
        color: #fff; text-shadow: 2px 2px 0px #ff00de, -2px -2px 0px #00ff41;
        animation: glitch-text 1s infinite linear alternate-reverse;
        margin-bottom: 30px;
    }
    @keyframes glitch-text {
        0% { transform: skew(0deg); }
        20% { transform: skew(-2deg); }
        40% { transform: skew(2deg); }
        60% { transform: skew(0deg); }
        80% { transform: skew(3deg); }
        100% { transform: skew(0deg); }
    }

    /* 3. 섹터 카드 (Glassmorphism + Neon) */
    .sector-card {
        background: rgba(20, 20, 20, 0.7);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(0, 255, 65, 0.3);
        border-radius: 15px;
        padding: 20px;
        margin-bottom: 15px;
        transition: all 0.3s;
        box-shadow: 0 0 10px rgba(0, 255, 65, 0.1);
        position: relative; overflow: hidden;
    }
    .sector-card:hover { transform: translateY(-5px); box-shadow: 0 0 20px rgba(0, 255, 65, 0.4); border-color: #00ff41; }

    /* 상태별 컬러 오버라이드 */
    .state-BLACK { border-color: #444; color: #666; }
    .state-GREY { border-color: #ff00de; box-shadow: 0 0 10px rgba(255, 0, 222, 0.2); animation: pulse-border 1.5s infinite; }
    .state-LIGHT { border-color: #ffd700; box-shadow: 0 0 15px rgba(255, 215, 0, 0.3); }

    /* 4. 버튼 커스텀 (Streamlit 버튼 못생김 해결) */
    .stButton > button {
        width: 100%;
        border-radius: 0px;
        border: 2px solid #00ff41;
        background: transparent;
        color: #00ff41;
        font-family: 'Share Tech Mono', monospace;
        font-size: 18px;
        font-weight: bold;
        transition: 0.2s;
        text-transform: uppercase;
        clip-path: polygon(10% 0, 100% 0, 100% 80%, 90% 100%, 0 100%, 0 20%);
    }
    .stButton > button:hover {
        background: #00ff41;
        color: #000;
        box-shadow: 0 0 20px #00ff41;
    }
    .stButton > button:active { transform: scale(0.98); }

    /* 5. 애니메이션 키프레임 */
    @keyframes pulse-border { 0% { border-color: #555; } 50% { border-color: #ff00de; } 100% { border-color: #555; } }
    
    /* 6. 회로도 칩 스타일 */
    .chip-box {
        display: inline-block; padding: 5px 10px; margin: 3px; 
        background: #111; border: 1px solid #333; color: #888; 
        font-size: 14px; cursor: not-allowed;
    }
    .chip-active {
        border-color: #00ff41; color: #00ff41; cursor: pointer;
    }
    .chip-active:hover { background: #00ff41; color: black; }
    
    .status-badge {
        position: absolute; top: 0; right: 0; 
        background: #00ff41; color: black; padding: 3px 10px; 
        font-size: 12px; font-weight: bold;
        clip-path: polygon(0 0, 100% 0, 100% 100%, 20% 100%);
    }

</style>
""", unsafe_allow_html=True)

# API Setup
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel("gemini-1.5-flash", generation_config={"response_mime_type": "application/json"})
except:
    pass

# -----------------------------------------------------------------------------
# 2. STATE & DATA
# -----------------------------------------------------------------------------
if "sectors" not in st.session_state:
    st.session_state.sectors = {
        "Def": {"name": "Protocol: DEFINE", "desc": "개념 정의 및 본질 파악", "state": "BLACK"}, 
        "Ing": {"name": "Protocol: SYNTHESIS", "desc": "재료 합성 및 반응식", "state": "BLACK"}, 
        "Imp": {"name": "Protocol: CAUSALITY", "desc": "인과 관계 및 영향력", "state": "BLACK"},
    }
if "view" not in st.session_state: st.session_state.view = "MAP"
if "buffer" not in st.session_state: st.session_state.buffer = []
if "curr_sector" not in st.session_state: st.session_state.curr_sector = None
if "glitch_shards" not in st.session_state: st.session_state.glitch_shards = []

KEYWORD_MAP = {
    "Def": {"pool": ["SOLAR_ENERGY", "GLUCOSE", "SYNTHESIS", "FIRE", "DIGESTION", "DECAY"], "ans": {"SOLAR_ENERGY", "GLUCOSE", "SYNTHESIS"}},
    "Ing": {"pool": ["H2O", "CO2", "PHOTON", "SALT", "ROCK", "VOLT"], "ans": {"H2O", "CO2", "PHOTON"}},
    "Imp": {"pool": ["OXYGEN", "ECOSYSTEM", "BREATH", "COLD", "TOXIN"], "ans": {"OXYGEN", "ECOSYSTEM", "BREATH"}}
}

# -----------------------------------------------------------------------------
# 3. VIEW CONTROLLER
# -----------------------------------------------------------------------------

# [SCENE 1: MAP DASHBOARD]
if st.session_state.view == "MAP":
    st.markdown("<div class='hacker-header'>GLITCH HUNTER v0.9</div>", unsafe_allow_html=True)
    
    # Dashboard Grid
    for sid, data in st.session_state.sectors.items():
        state_cls = f"state-{data['state']}"
        status_text = "LOCKED"
        if data['state'] == "GREY": status_text = "UNSTABLE"
        elif data['state'] == "LIGHT": status_text = "SECURE"
        
        # HTML Card Render
        st.markdown(f"""
        <div class='sector-card {state_cls}'>
            <div class='status-badge' style='background-color: {"#555" if data["state"]=="BLACK" else "#ff00de" if data["state"]=="GREY" else "#ffd700"}'>{status_text}</div>
            <h2 style='margin:0; font-size:24px;'>{data['name']}</h2>
            <p style='margin:5px 0 15px 0; font-size:14px; opacity:0.8;'>{data['desc']}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Action Buttons (Streamlit Native)
        c1, c2, c3 = st.columns([1, 4, 1])
        with c2:
            if data['state'] == "BLACK":
                if st.button(f"🚀 INITIATE HACK ({sid})", key=f"btn_{sid}"):
                    st.session_state.curr_sector = sid
                    st.session_state.sectors[sid]['state'] = "GREY"
                    st.session_state.view = "LINK"
                    st.rerun()
            elif data['state'] == "GREY":
                if st.button(f"⚡ STABILIZE ({sid})", key=f"btn_{sid}"):
                    st.session_state.curr_sector = sid
                    st.session_state.view = "LINK"
                    st.rerun()
            elif data['state'] == "LIGHT":
                st.markdown("<div style='text-align:center; color:#ffd700; font-weight:bold;'>ACCESS GRANTED</div>", unsafe_allow_html=True)

    # Glitch Vault Teaser
    if len(st.session_state.glitch_shards) > 0:
        st.error(f"⚠️ DETECTED GLITCH SHARDS: {len(st.session_state.glitch_shards)}")

# [SCENE 2: LINK GAME]
elif st.session_state.view == "LINK":
    sid = st.session_state.curr_sector
    sec = st.session_state.sectors[sid]
    pool = KEYWORD_MAP[sid]['pool']
    
    st.markdown(f"<div class='hacker-header' style='font-size:30px; margin-bottom:10px;'>{sec['name']}</div>", unsafe_allow_html=True)
    st.info("CONNECT 3 CORE MODULES TO STABILIZE")
    
    # 1. Visual Buffer (The Slot)
    st.markdown("### ■ ACTIVE MODULES")
    
    slot_html = "<div style='display:flex; gap:10px; margin-bottom:20px; justify-content:center;'>"
    for item in st.session_state.buffer:
        slot_html += f"<div style='border:2px solid #00ff41; padding:10px; color:#00ff41; font-weight:bold; box-shadow:0 0 10px #00ff41;'>{item}</div>"
    for _ in range(3 - len(st.session_state.buffer)):
         slot_html += f"<div style='border:2px dashed #444; padding:10px; color:#444; min-width:80px; text-align:center;'>EMPTY</div>"
    slot_html += "</div>"
    st.markdown(slot_html, unsafe_allow_html=True)
    
    # 2. Controls
    c1, c2 = st.columns(2)
    with c1:
        if st.button("❌ FLUSH BUFFER"):
            st.session_state.buffer = []
            st.rerun()
    with c2:
        can_run = len(st.session_state.buffer) == 3
        if st.button("🔥 EXECUTE", type="primary", disabled=not can_run):
            user_set = set(st.session_state.buffer)
            ans_set = KEYWORD_MAP[sid]['ans']
            
            if user_set == ans_set:
                st.balloons()
                st.success("SYSTEM RESTORED.")
                st.session_state.sectors[sid]['state'] = "LIGHT"
                time.sleep(1.5)
                st.session_state.buffer = []
                st.session_state.view = "MAP"
            else:
                st.error("FATAL ERROR. GLITCH CREATED.")
                st.session_state.sectors[sid]['state'] = "BLACK"
                st.session_state.glitch_shards.append({"sid": sid, "wrong": list(user_set)})
                time.sleep(1.5)
                st.session_state.buffer = []
                st.session_state.view = "MAP"
            st.rerun()
            
    # 3. Chip Selection
    st.markdown("### ■ AVAILABLE DATA")
    cols = st.columns(3)
    for i, word in enumerate(pool):
        with cols[i%3]:
            # Streamlit 버튼 디자인 오버라이드 됨
            disabled = word in st.session_state.buffer or len(st.session_state.buffer) >= 3
            if st.button(word, key=f"chip_{i}", disabled=disabled):
                st.session_state.buffer.append(word)
                st.rerun()
