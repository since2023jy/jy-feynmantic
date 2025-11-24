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
st.set_page_config(page_title="FeynmanTic V33", page_icon="⚡", layout="wide")

st.markdown("""
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    .stApp { background-color: #0E1117; color: #E0E0E0; font-family: 'Pretendard', sans-serif; }
    
    .chat-message { padding: 1.2rem; border-radius: 1rem; margin-bottom: 1rem; line-height: 1.6; box-shadow: 0 2px 4px rgba(0,0,0,0.2); }
    .chat-message.user { background-color: #21262D; border-right: 4px solid #7C4DFF; text-align: right; margin-left: 15%; }
    .chat-message.bot { background-color: #161B22; border-left: 4px solid #FF4B4B; font-family: 'Courier New', monospace; margin-right: 5%; }
    .chat-message.thinking { background-color: #383838; color: #ccc; border-left: 4px solid #FFD700; font-style: italic; margin-right: 10%; } /* NEW STYLE */
    
    .gate-badge { font-size: 0.75rem; padding: 4px 10px; border-radius: 20px; background: #30363D; color: #aaa; margin-right: 4px; border: 1px solid #444; }
    .gate-active { background: rgba(0, 230, 118, 0.1); color: #00E676; border-color: #00E676; font-weight: bold; }
    
    .stButton button { width: 100%; border-radius: 8px; font-weight: bold; height: 3em; }
    .stTextInput input { background-color: #0d1117 !important; color: #fff !important; border: 1px solid #30363d !important; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# [Layer 1] Logic
# ==========================================
def init_db():
    conn = sqlite3.connect('feynmantic_v32.db', check_same_thread=False)
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

def generate_audio(text):
    try:
        sound_file = BytesIO()
        tts = gTTS(text=text, lang='ko')
        tts.write_to_fp(sound_file)
        sound_file.seek(0)
        return sound_file
    except: return None

def extract_json(text):
    try:
        return json.loads(text)
    except:
        try:
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match: return json.loads(match.group())
            else: return None
        except: return None

# --- PROMPTS --- (Simplified for this final code block)
SCHOOL_SYS = """[Role] 파인만틱 선생님. [Mission] 학생이 개념을 '비유'로 설명하게 유도. 정답을 주지 말고 질문할 것. 짧고 명확하게."""
RED_TEAM_SYS = """[Role] 기업 레드팀 리더. [Mission] 보고서/기획안을 무자비하게 검증. 추상적 형용사 금지. 숫자 요구. 리스크 공격."""
DOPPEL_SYS = """[Role] 지적 성향 분석가. [Mission] 위인 매칭 및 사고력 평가."""
ARTIFACT_SYS = """당신은 '지식 큐레이터'입니다. 통찰을 강조하여 요약하세요. JSON: { "title": "...", "fact_summary": ["..."], "user_insight": "...", "closing_remark": "..." }"""

def call_gemini(api_key, sys, user, model_name, retry_count=0):
    try:
        genai.configure(api_key=api_key)
        config = {"response_mime_type": "application/json"} if "1.5" in model_name else {}
        safety = [{"category": cat, "threshold": "BLOCK_NONE"} for cat in ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]]
        
        model = genai.GenerativeModel(model_name, system_instruction=sys, safety_settings=safety, generation_config=config)
        final_prompt = f"{user}\n\n(Respond ONLY in JSON)" if "1.5" not in model_name else user
        
        res = model.generate_content(final_prompt)
        parsed = extract_json(res.text)
        
        if parsed: return parsed
        else:
            if retry_count < 1:
                time.sleep(1)
                return call_gemini(api_key, sys, user, model_name, retry_count + 1)
            else:
                return {"decision": "FAIL", "response": res.text}
            
    except Exception as e:
        return {"decision": "FAIL", "response": f"Error: {e}"}

# ==========================================
# [Layer 2] UI & State Management
# ==========================================
init_db()
if "mode" not in st.session_state: st.session_state.mode = "LANDING"
if "gate" not in st.session_state: st.session_state.gate = 0
if "messages" not in st.session_state: st.session_state.messages = []
if "auto_model" not in st.session_state: st.session_state.auto_model = None
if "artifact" not in st.session_state: st.session_state.artifact = None
if "user_role" not in st.session_state: st.session_state.user_role = None

with st.sidebar:
    st.title("⚡ FeynmanTic V33")
    st.caption("Performance UX Optimized")
    api_key = st.text_input("Google API Key", type="password")
    
    if api_key and st.button("🔄 엔진 시동 (Connect)"):
        with st.spinner("시스템 점검 중..."):
            found = find_working_model(api_key)
            if found: 
                st.session_state.auto_model = found
                st.success(f"Connected: {found}")
            else: 
                st.error("모델 연결 실패 (키 권한 확인)")
    
    st.divider()
    if st.button("🏠 메인으로 (Reset)"): st.session_state.clear(); st.rerun()

# --- SCENE 1: LANDING (Simple for Demo) ---
if st.session_state.mode == "LANDING":
    st.markdown("<br><h1 style='text-align: center;'>CHOOSE MODE</h1><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    if c1.button("🎒 학생"): st.session_state.user_role = "SCHOOL"; st.session_state.mode = "CHAT_INIT"; st.rerun()
    if c2.button("🛡️ 직장인"): st.session_state.user_role = "PRO"; st.session_state.mode = "CHAT_INIT"; st.rerun()
    if c3.button("🌌 탐험가"): st.session_state.user_role = "EXPLORER"; st.session_state.mode = "CHAT_INIT"; st.rerun()

# --- SCENE 2: INIT CHAT ---
elif st.session_state.mode == "CHAT_INIT":
    topic = st.text_input("주제 입력", placeholder="비트코인, 미분...")
    if st.button("START"):
        st.session_state.topic = topic
        st.session_state.mode = "CHAT"
        st.session_state.gate = 1
        intro = f"**'{topic}'** 해체 시작. 정의하십시오."
        st.session_state.messages = [{"role":"assistant", "content":intro}]
        st.rerun()

# --- SCENE 3: CHAT (UX Optimized) ---
elif st.session_state.mode == "CHAT":
    for msg in st.session_state.messages:
        css = "user" if msg["role"] == "user" else "bot"
        st.markdown(f"<div class='chat-message {css}'>{msg['content']}</div>", unsafe_allow_html=True)

    if prompt := st.chat_input("입력..."):
        # 1. User Input Append
        st.session_state.messages.append({"role":"user", "content":prompt})
        # 2. [UX FIX] Fake Loading/Thinking message append
        st.session_state.messages.append({"role":"thinking", "content":"지도를 분석 중입니다. 잠시만 기다려 주십시오..."})
        st.rerun()

    if st.session_state.messages and st.session_state.messages[-1]["role"] == "thinking":
        # 3. [UX FIX] Remove fake message before starting API call
        st.session_state.messages.pop() 

        # 4. AI Logic
        with st.chat_message("assistant"):
            box = st.empty(); box.markdown("...")
            
            sys = SCHOOL_SYS if st.session_state.user_role=="SCHOOL" else RED_TEAM_SYS if st.session_state.user_role=="PRO" else DOPPEL_SYS
            instruction = f"Gate: {st.session_state.gate}. Topic: {st.session_state.topic}"
            
            res = call_gemini(api_key, f"{sys}\n{instruction}", f"User Input: {st.session_state.messages[-2]['content']}", st.session_state.auto_model)
            
            text = res.get('response', str(res))
            box.markdown(f"<div class='chat-message bot'>{text}</div>", unsafe_allow_html=True)
            st.session_state.messages.append({"role":"assistant", "content":text})

            if res.get('decision') == "PASS":
                if st.session_state.gate < 4:
                    st.session_state.gate += 1; st.toast("✅ Gate Passed!"); 
                    time.sleep(1); st.rerun()
                else:
                    st.session_state.mode = "ARTIFACT"; st.rerun()

# --- SCENE 4: ARTIFACT ---
elif st.session_state.mode == "ARTIFACT":
    st.balloons()
    st.markdown("<h1 style='text-align:center; color:#00E676;'>INSIGHT ACQUIRED</h1>", unsafe_allow_html=True)
    
    if not st.session_state.artifact:
        with st.spinner("Creating Artifact..."):
            dialogue = json.dumps(st.session_state.messages)
            data = call_gemini(api_key, ARTIFACT_SYS, f"Dialog: {dialogue}", st.session_state.auto_model)
            st.session_state.artifact = data
            
            # Audio Generation
            script = f"주제 {st.session_state.topic}. 당신의 통찰: {data.get('user_insight', '')}."
            st.session_state.audio_path = generate_audio(script)

    data = st.session_state.artifact
    st.markdown(f"""
        <div class="artifact-box">
            <h3>🏆 {data.get('title', 'Result')}</h3>
            <p style='color:#FFD700;'>"{data.get('user_insight', '')}"</p>
        </div>
    """, unsafe_allow_html=True)
    
    if st.session_state.audio_path:
        st.audio(st.session_state.audio_path, format="audio/mp3")
        
    if st.button("🏠 Home"): st.session_state.clear(); st.rerun()
