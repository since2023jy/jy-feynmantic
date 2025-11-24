import streamlit as st
import google.generativeai as genai
import json
import time
import random
import sqlite3
import pandas as pd
import plotly.express as px
from gtts import gTTS
from io import BytesIO
import re
from datetime import datetime

# ==========================================
# [Layer 0] Config & Styles
# ==========================================
st.set_page_config(page_title="FeynmanTic V26", page_icon="🧠", layout="wide")

st.markdown("""
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    .stApp { background-color: #0E1117; color: #E0E0E0; font-family: 'Pretendard', sans-serif; }
    
    .chat-message { padding: 1rem; border-radius: 0.5rem; margin-bottom: 1rem; line-height: 1.6; box-shadow: 0 2px 4px rgba(0,0,0,0.2); }
    .chat-message.user { background-color: #21262D; border-right: 4px solid #7C4DFF; text-align: right; margin-left: 15%; }
    .chat-message.bot { background-color: #161B22; border-left: 4px solid #00E676; font-family: 'Courier New', monospace; margin-right: 5%; }
    
    .stButton button { width: 100%; border-radius: 8px; font-weight: bold; height: 3em; }
    .stTextInput input { background-color: #0d1117 !important; color: #fff !important; border: 1px solid #30363d !important; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# [Layer 1] Robust Logic & Core Functions
# ==========================================
def init_db():
    conn = sqlite3.connect('feynmantic_v26.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY, timestamp TEXT, role TEXT, topic TEXT, dialogue TEXT)''')
    conn.commit()
    conn.close()

def find_working_model(api_key):
    try:
        genai.configure(api_key=api_key)
        available = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        priority = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']
        for p in priority:
            for a in available:
                if p in a: return a
        return None
    except: return None

# [Fix] Audio Generation with Seek(0)
def generate_audio(text):
    try:
        sound_file = BytesIO()
        tts = gTTS(text=text, lang='ko')
        tts.write_to_fp(sound_file)
        sound_file.seek(0) # [Critical Fix] 커서 맨 앞으로 되감기
        return sound_file
    except: return None

# [Fix] Robust JSON Parser
def extract_json(text):
    try:
        return json.loads(text)
    except:
        try:
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match: return json.loads(match.group())
            else: return None
        except: return None

# --- PROMPTS --- (Score System)
SCORING_FORMAT = """
[평가 기준]
1. Understanding: 이해력 (0~100)
2. Logic: 논리력 (0~100)
3. Clarity: 설명력 (0~100)
4. Creativity: 창의력 (0~100)
5. Attitude: 태도 (0~100)

JSON 출력: {
    "decision": "PASS"|"FAIL",
    "response": "피드백 멘트",
    "stats_result": { "Understanding": 0, "Logic": 0, "Clarity": 0, "Creativity": 0, "Attitude": 0 },
    "feedback_detail": { "Logic": "점수 이유", "Clarity": "점수 이유", "Attitude": "점수 이유 (힌트 사용 등)" }
}
"""

SCHOOL_SYS = f"""[Role] 파인만틱 선생님. [Mission] 학생이 개념을 '비유'로 설명하게 유도. {SCORING_FORMAT}"""
RED_TEAM_SYS = f"""[Role] 기업 레드팀 리더. [Mission] 보고서를 무자비하게 검증. 숫자 요구. 리스크 공격. {SCORING_FORMAT}"""
DOPPEL_SYS = f"""[Role] 지적 성향 분석가. [Mission] 위인 매칭 및 사고력 평가. {SCORING_FORMAT}"""

def call_gemini(api_key, sys, user, model_name):
    try:
        genai.configure(api_key=api_key)
        config = {"response_mime_type": "application/json"} if "1.5" in model_name else {}
        safety = [{"category": cat, "threshold": "BLOCK_NONE"} for cat in ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]]
        
        model = genai.GenerativeModel(model_name, system_instruction=sys, safety_settings=safety, generation_config=config)
        final_prompt = f"{user}\n\n(Respond ONLY in JSON with the structure defined)"
        
        res = model.generate_content(final_prompt)
        return extract_json(res.text)
    except Exception as e:
        return {"decision": "FAIL", "response": f"System Error: {e}", "stats_result": {}}

# ==========================================
# [Layer 2] UI & State Management
# ==========================================
init_db()
if "mode" not in st.session_state: st.session_state.mode = "LANDING"
if "current_stats" not in st.session_state: 
    st.session_state.current_stats = {"Understanding": 10, "Logic": 10, "Clarity": 10, "Creativity": 10, "Attitude": 100}
if "messages" not in st.session_state: st.session_state.messages = []
if "auto_model" not in st.session_state: st.session_state.auto_model = None
if "gate" not in st.session_state: st.session_state.gate = 0
if "feedback_log" not in st.session_state: st.session_state.feedback_log = {}

with st.sidebar:
    st.title("⚡ FeynmanTic V26")
    st.caption("Final Stat System")
    
    # Radar Chart Display
    st.markdown("### 🧠 My Brain Stats")
    stats = st.session_state.current_stats
    df = pd.DataFrame(dict(r=list(stats.values()), theta=list(stats.keys())))
    fig = px.line_polar(df, r='r', theta='theta', line_close=True, range_r=[0, 100])
    fig.update_traces(fill='toself', line_color='#7C4DFF')
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="white", margin=dict(t=20, b=20, l=30, r=30), height=250)
    st.plotly_chart(fig, use_container_width=True)

    api_key = st.text_input("Google API Key", type="password")
    if api_key and st.button("🔄 Connect"):
        found = find_working_model(api_key)
        if found: st.session_state.auto_model = found; st.success("Connected")
    
    if st.button("Reset"): st.session_state.clear(); st.rerun()

# --- SCENE 1: LANDING ---
if st.session_state.mode == "LANDING":
    st.markdown("<br><h1 style='text-align: center;'>CHOOSE MODE</h1><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    if c1.button("🎒 학생"): st.session_state.user_role="SCHOOL"; st.session_state.mode="CHAT"; st.session_state.gate=1; st.rerun()
    if c2.button("🛡️ 직장인"): st.session_state.user_role="PRO"; st.session_state.mode="CHAT"; st.session_state.gate=1; st.rerun()
    if c3.button("🌌 탐험가"): st.session_state.user_role="EXPLORER"; st.session_state.mode="CHAT"; st.session_state.gate=1; st.rerun()

# --- SCENE 3: CHAT ---
elif st.session_state.mode == "CHAT":
    # Header
    st.markdown(f"## Topic: {st.session_state.topic}")
    st.caption(f"Role: {st.session_state.user_role} | Gate: {st.session_state.gate}")
    
    # Chat Log
    chat_container = st.container(height=400)
    with chat_container:
        for msg in st.session_state.messages:
            css = "user" if msg["role"] == "user" else "bot"
            st.markdown(f"<div class='chat-message {css}'>{msg['content']}</div>", unsafe_allow_html=True)
            
        # Display Detailed Feedback if available (After a response)
        if st.session_state.feedback_log:
            st.markdown("### 📝 채점 코멘트")
            for k, v in st.session_state.feedback_log.items():
                if v: st.markdown(f"**{k}**: {v}")
            st.session_state.feedback_log = {} # Clear after display

    # Hint Button (Attitude Penalty)
    if st.session_state.gate < 5:
        if st.button("🆘 힌트 (-10 Attitude)"):
            st.session_state.current_stats['Attitude'] = max(0, st.session_state.current_stats['Attitude'] - 10)
            st.toast("⚠️ 태도 점수 10점 감점되었습니다!")
            # Get Hint (Simplified for display)
            st.session_state.messages.append({"role":"assistant", "content": "Hint: Think about the core cause, not the surface effect."}) 
            st.rerun()

    # Input
    if st.session_state.gate <= 4:
        if prompt := st.chat_input("논리 입력..."):
            st.session_state.messages.append({"role":"user", "content":prompt})
            st.rerun()

    # AI Logic
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        with st.chat_message("assistant"):
            box = st.empty(); box.markdown("채점 중...")
            
            # Select System Prompt
            role = st.session_state.user_role
            sys = SCHOOL_SYS if role=="SCHOOL" else RED_TEAM_SYS if role=="PRO" else DOPPEL_SYS
            inst = f"Current Gate: {st.session_state.gate}. User Input: {st.session_state.messages[-1]['content']}"
            
            res = call_gemini(api_key, sys, inst, st.session_state.auto_model)
            
            text = res.get('response', '응답 처리 중 오류가 발생했습니다.')
            box.markdown(f"<div class='chat-message bot'>{text}</div>", unsafe_allow_html=True)
            st.session_state.messages.append({"role":"assistant", "content":text})
            
            # Update Stats & Feedback Log [CRUCIAL]
            new_stats = res.get('stats_result', {})
            feedback_log = res.get('feedback_detail', {})
            
            if new_stats:
                changes = []
                for k, v in new_stats.items():
                    if k in st.session_state.current_stats:
                        # Clamp values between 0 and 100
                        st.session_state.current_stats[k] = max(0, min(100, v))
                        changes.append(f"{k}: {v}")
                
                if changes:
                    st.toast(f"📈 스탯 갱신 완료!")
                    st.session_state.feedback_log = feedback_log # Store log for display in the next run

            if res.get('decision') == "PASS":
                if st.session_state.gate < 4:
                    st.session_state.gate += 1; time.sleep(1); st.rerun()
                else:
                    st.session_state.mode = "ARTIFACT"; st.rerun()

# --- SCENE 4: ARTIFACT ---
elif st.session_state.mode == "ARTIFACT":
    st.balloons()
    st.markdown("<h1 style='text-align:center; color:#00E676;'>INSIGHT ACQUIRED</h1>", unsafe_allow_html=True)
    
    if not st.session_state.artifact:
        with st.spinner("Creating Artifact..."):
            # Dummy artifact creation as actual full JSON is too complex for this demo
            st.session_state.artifact = {"title": "Final Thought Report", "user_insight": "My thinking is complete."}
    
    data = st.session_state.artifact
    st.markdown(f"""
        <div class="artifact-box">
            <h3>🏆 {data.get('title', 'Result')}</h3>
            <p style='color:#FFD700;'>"{data.get('user_insight', '통찰 생성 중...')}"</p>
        </div>
    """, unsafe_allow_html=True)
    
    if st.button("🏠 Home"): st.session_state.clear(); st.rerun()
