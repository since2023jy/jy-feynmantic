import streamlit as st
import google.generativeai as genai
import json
import time
import random
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import datetime

# ==========================================
# [Layer 0] Config & Design System
# ==========================================
st.set_page_config(page_title="FeynmanTic V11", page_icon="⚡", layout="centered")

st.markdown("""
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    .stApp { background-color: #0E1117; color: #E0E0E0; font-family: 'Pretendard', monospace; }
    
    /* Manifesto Modal Style */
    .manifesto-box { border: 2px solid #FF4B4B; padding: 30px; border-radius: 10px; text-align: center; background: rgba(255, 75, 75, 0.05); margin-bottom: 30px; }
    
    /* Chat UI */
    .chat-message { padding: 1rem; border-radius: 0.5rem; margin-bottom: 1rem; line-height: 1.6; box-shadow: 0 2px 4px rgba(0,0,0,0.2); }
    .chat-message.user { background-color: #161B22; border-right: 4px solid #7C4DFF; text-align: right; margin-left: 20%; }
    .chat-message.bot { background-color: #1F2428; border-left: 4px solid #FF4B4B; font-family: 'Courier New', monospace; margin-right: 10%; }
    .chat-message.whisper { background-color: #0d1117; border: 1px dashed #4285F4; color: #8ab4f8; font-size: 0.9rem; text-align: center; padding: 10px; }

    /* Spectator Card */
    .spectator-card { background: #161B22; border: 1px solid #30363D; padding: 15px; border-radius: 10px; margin-bottom: 15px; }
    .score-badge { background: #7C4DFF; color: white; padding: 3px 8px; border-radius: 5px; font-size: 0.8rem; font-weight: bold; }
    
    /* Components */
    .gate-badge { font-size: 0.7rem; padding: 4px 8px; border-radius: 20px; background: #21262D; color: #6E7681; border: 1px solid #333; margin-right: 3px; }
    .gate-active { background: rgba(255, 75, 75, 0.1); color: #FF4B4B; border-color: #FF4B4B; font-weight: bold; }
    .stButton button { width: 100%; border-radius: 8px; font-weight: bold; background-color: #21262D; color: #C9D1D9; border: 1px solid #30363D; }
    .stButton button:hover { border-color: #7C4DFF; color: #7C4DFF; }
    .stTextInput input { background-color: #0d1117 !important; color: #fff !important; border: 1px solid #30363d !important; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# [Layer 1] Logic & Data
# ==========================================
def init_db():
    conn = sqlite3.connect('feynmantic_v11.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY, timestamp TEXT, topic TEXT, mode TEXT, dialogue TEXT, score_json TEXT)''')
    conn.commit()
    conn.close()

def save_log(topic, mode, messages, score_data=None):
    conn = sqlite3.connect('feynmantic_v11.db')
    c = conn.cursor()
    c.execute('INSERT INTO logs (timestamp, topic, mode, dialogue, score_json) VALUES (?, ?, ?, ?, ?)',
              (datetime.now().strftime("%Y-%m-%d"), topic, mode, json.dumps(messages, ensure_ascii=False), json.dumps(score_data) if score_data else None))
    conn.commit()
    conn.close()

def get_spectator_feed():
    return [
        {"topic": "비트코인", "user_view": "디지털 에너지 저장소다.", "f_score": 92, "likes": 128},
        {"topic": "자유의지", "user_view": "뇌의 화학작용일 뿐이다.", "f_score": 88, "likes": 95},
        {"topic": "AI 규제", "user_view": "핵무기급 통제가 필요하다.", "f_score": 45, "likes": 12}
    ]

# AI Config
# Flash 모델 에러 방지를 위해 Pro 모델로 변경
MODEL_NAME = 'gemini-1.5-pro' 
SAFETY = [{"category": cat, "threshold": "BLOCK_NONE"} for cat in ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]]

# Prompts
INTUITION_SYS = """당신은 '직관 유도자'입니다. 주제에 대해 '전혀 모른다'는 사용자를 위해 '밸런스 게임(이지선다)'을 만드세요. JSON: { "scenario": "...", "option_a": "...", "option_b": "...", "question": "..." }"""
SOCRATIC_SYS = """당신은 '파인만틱 소크라테스'입니다. 질문으로 논리를 검증하세요. JSON: { "decision": "PASS"|"FAIL"|"SURRENDER", "response": "...", "reason": "..." }"""
WHISPER_SYS = """당신은 '천사의 속삭임'입니다. 결정적인 '비유 힌트'만 짧게 던지세요."""
SCORE_SYS = """당신은 '논리 심판관'입니다. 대화를 분석해 4가지 지표(0~100점)로 평가하세요. JSON: { "clarity": 0, "causality": 0, "defense": 0, "originality": 0, "total_score": 0, "comment": "..." }"""

def call_gemini(api_key, sys, user, json_mode=True):
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(MODEL_NAME, system_instruction=sys, safety_settings=SAFETY, generation_config={"response_mime_type": "application/json"} if json_mode else None)
        res = model.generate_content(user)
        return json.loads(res.text) if json_mode else res.text
    except Exception as e: return {"decision": "FAIL", "response": f"API Error: {e}"}

# ==========================================
# [Layer 2] UI Flow
# ==========================================
init_db()

if "signed_manifesto" not in st.session_state: st.session_state.signed_manifesto = False
if "mode" not in st.session_state: st.session_state.mode = "HOME"
if "messages" not in st.session_state: st.session_state.messages = []
if "gate" not in st.session_state: st.session_state.gate = 0

with st.sidebar:
    st.title("⚡ FeynmanTic V11")
    st.caption("The Civilization Edition")
    api_key = st.text_input("Google API Key", type="password")
    st.markdown("[🔑 키 발급받기](https://aistudio.google.com/app/apikey)")
    if st.button("🔄 Reset System"): st.session_state.clear(); st.rerun()

# --- STEP 1: MANIFESTO (Onboarding) ---
if not st.session_state.signed_manifesto:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("""
        <div class="manifesto-box">
            <h2>📜 THE MANIFESTO</h2>
            <p>나는 정답을 베끼지 않겠습니다.</p>
            <p>나는 나의 언어로 설명하겠습니다.</p>
            <p>나는 고통스러운 사고의 과정을 즐기겠습니다.</p>
            <br>
            <p style='font-size:0.8rem; color:#888;'>서명하는 순간, 당신은 전토클럽의 예비 회원이 됩니다.</p>
        </div>
    """, unsafe_allow_html=True)
    if st.button("서명하고 입장하기 (I Agree)"):
        st.session_state.signed_manifesto = True
        st.rerun()

# --- STEP 2: MAIN HUB ---
elif st.session_state.mode == "HOME":
    st.markdown("<h1 style='text-align: center; letter-spacing:-1px;'>ARENA OF THOUGHT</h1>", unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["📅 News", "🏛️ Classics", "🏟️ Colosseum"])
    
    with tab1:
        st.markdown("### 🔥 Daily Dismantle")
        if st.button("📈 [Economy] 비트코인 반감기, 왜 오르는가?"): st.session_state.topic="비트코인"; st.session_state.mode="CHAT"; st.session_state.gate=1; st.rerun()
        if st.button("🤖 [Tech] AI가 인간을 대체할까?"): st.session_state.topic="AI 대체"; st.session_state.mode="CHAT"; st.session_state.gate=1; st.rerun()
        
        st.markdown("---")
        custom = st.text_input("Or enter your own topic:", placeholder="e.g. Quantum Physics")
        if st.button("Start Analysis"): 
            if custom: st.session_state.topic=custom; st.session_state.mode="CHAT"; st.session_state.gate=1; st.rerun()

    with tab2:
        st.markdown("### 🏛️ Eternal Questions")
        if st.button("🦁 [Ethics] 정의란 무엇인가?"): st.session_state.topic="정의(Justice)"; st.session_state.mode="CHAT"; st.session_state.gate=1; st.rerun()
        if st.button("🌌 [Physics] 신은 존재하는가?"): st.session_state.topic="신(God)"; st.session_state.mode="CHAT"; st.session_state.gate=1; st.rerun()

    with tab3:
        st.markdown("### 🏟️ Spectator Mode")
        feed = get_spectator_feed()
        for item in feed:
            st.markdown(f"""
                <div class="spectator-card">
                    <div style='display:flex; justify-content:space-between;'>
                        <span style='color:#FF4B4B; font-weight:bold;'>{item['topic']}</span>
                        <span class="score-badge">F-Score: {item['f_score']}</span>
                    </div>
                    <p style='margin:10px 0; font-style:italic; color:#ccc;'>"{item['user_view']}"</p>
                    <div style='font-size:0.8rem; color:#888;'>❤️ {item['likes']} Votes</div>
                </div>
            """, unsafe_allow_html=True)
            st.button(f"📺 Replay Log", key=f"rep_{item['topic']}")

# --- STEP 3: SOCRATIC LOOP ---
elif st.session_state.mode == "CHAT":
    if not api_key: st.error("Google API Key Required"); st.stop()
    
    # Badges
    badges = "".join([f"<span class='gate-badge {'gate-active' if st.session_state.gate==i else ''}'>🔒 {i}</span>" for i in range(1,5)])
    st.markdown(f"<div style='text-align:center; margin-bottom:15px;'>{badges}</div>", unsafe_allow_html=True)
    
    for msg in st.session_state.messages:
        role = "user" if msg["role"] == "user" else "bot"
        st.markdown(f"<div class='chat-message {role}'>{msg['content']}</div>", unsafe_allow_html=True)

    if st.session_state.messages and st.session_state.messages[-1]["role"] == "assistant" and st.session_state.gate < 4:
        with st.expander("👼 Help Me (Whisper)"):
            if st.button("힌트 듣기"):
                hint = call_gemini(api_key, WHISPER_SYS, f"주제:{st.session_state.topic}\n질문:{st.session_state.messages[-1]['content']}", json_mode=False)
                st.markdown(f"<div class='chat-message whisper'>👼 Whisper: {hint}</div>", unsafe_allow_html=True)

    if prompt := st.chat_input("Your Logic..."):
        st.session_state.messages.append({"role":"user", "content":prompt})
        st.rerun()

    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        with st.chat_message("assistant"):
            box = st.empty(); box.markdown("*Thinking...*")
            
            instruction = ""
            if st.session_state.gate == 1: instruction = "Gate 1: Definition. No Jargon."
            elif st.session_state.gate == 2: instruction = "Gate 2: Mechanism. Check Causality."
            elif st.session_state.gate == 3: instruction = "Gate 3: Falsification. Check Edge Cases."
            elif st.session_state.gate == 4: instruction = "Gate 4: Insight. Ask for User's View."

            res = call_gemini(api_key, f"{SOCRATIC_SYS}\n{instruction}", f"Topic:{st.session_state.topic}\nUser:{st.session_state.messages[-1]['content']}")
            
            # Streaming
            full_text = res['response']
            disp = ""; 
            for char in full_text: 
                disp += char; box.markdown(f"<div class='chat-message bot'>{disp}▌</div>", unsafe_allow_html=True); time.sleep(0.005)
            box.markdown(f"<div class='chat-message bot'>{full_text}</div>", unsafe_allow_html=True)
            st.session_state.messages.append({"role":"assistant", "content":full_text})

            if res['decision'] == "PASS":
                if st.session_state.gate < 4:
                    st.session_state.gate += 1; st.toast("✅ Gate Passed!"); time.sleep(1); st.rerun()
                else:
                    st.session_state.mode = "SCORE"
                    st.rerun()
            elif res['decision'] == "FAIL":
                pass # Just continue chat

# --- STEP 4: F-SCORE (Evaluation) ---
elif st.session_state.mode == "SCORE":
    st.balloons()
    st.markdown("<h1 style='text-align:center; color:#00E676;'>LOGIC AUDIT COMPLETE</h1>", unsafe_allow_html=True)
    
    if "score_data" not in st.session_state:
        with st.spinner("Calculating F-Score..."):
            dialogue = json.dumps(st.session_state.messages)
            st.session_state.score_data = call_gemini(api_key, SCORE_SYS, f"대화내용: {dialogue}")
            save_log(st.session_state.topic, "COMPLETED", st.session_state.messages, st.session_state.score_data)
            
    score = st.session_state.score_data
    
    # Radar Chart
    data = pd.DataFrame(dict(
        r=[score['clarity'], score['causality'], score['defense'], score['originality']],
        theta=['Clarity', 'Causality', 'Defense', 'Originality']))
    fig = px.line_polar(data, r='r', theta='theta', line_close=True, range_r=[0,100])
    fig.update_traces(fill='toself', line_color='#00E676')
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="white")
    
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown(f"""
        <div style='text-align:center;'>
            <h2 style='color:#00E676; font-size:3rem;'>{score['total_score']} <span style='font-size:1rem;'>/ 100</span></h2>
            <p style='font-style:italic; color:#ccc;'>"{score['comment']}"</p>
        </div>
    """, unsafe_allow_html=True)
    
    if st.button("🏠 Return to Arena"): st.session_state.clear(); st.rerun()
