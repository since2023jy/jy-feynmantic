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
# [Layer 0] Config
# ==========================================
st.set_page_config(page_title="FeynmanTic Final", page_icon="⚡", layout="centered")

st.markdown("""
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    .stApp { background-color: #0E1117; color: #E0E0E0; font-family: 'Pretendard', monospace; }
    .chat-message { padding: 1rem; border-radius: 0.5rem; margin-bottom: 1rem; line-height: 1.6; box-shadow: 0 2px 4px rgba(0,0,0,0.2); }
    .chat-message.user { background-color: #161B22; border-right: 4px solid #7C4DFF; text-align: right; }
    .chat-message.bot { background-color: #1F2428; border-left: 4px solid #FF4B4B; font-family: 'Courier New'; }
    .stButton button { width: 100%; border-radius: 8px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# [Layer 1] Logic & Data
# ==========================================
def init_db():
    conn = sqlite3.connect('feynmantic_final.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY, timestamp TEXT, topic TEXT, mode TEXT, dialogue TEXT, score_json TEXT)''')
    conn.commit()
    conn.close()

def save_log(topic, mode, messages, score_data=None):
    conn = sqlite3.connect('feynmantic_final.db')
    c = conn.cursor()
    c.execute('INSERT INTO logs (timestamp, topic, mode, dialogue, score_json) VALUES (?, ?, ?, ?, ?)',
              (datetime.now().strftime("%Y-%m-%d"), topic, mode, json.dumps(messages, ensure_ascii=False), json.dumps(score_data) if score_data else None))
    conn.commit()
    conn.close()

def get_spectator_feed():
    return [{"topic": "비트코인", "user_view": "디지털 에너지다.", "f_score": 92, "likes": 128}]

# AI Settings
SAFETY = [{"category": cat, "threshold": "BLOCK_NONE"} for cat in ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]]

INTUITION_SYS = """당신은 '직관 유도자'입니다. 밸런스 게임을 만드세요. JSON: { "scenario": "...", "option_a": "...", "option_b": "...", "question": "..." }"""
SOCRATIC_SYS = """당신은 '파인만틱 소크라테스'입니다. 질문으로 논리를 검증하세요. JSON: { "decision": "PASS"|"FAIL", "response": "..." }"""
WHISPER_SYS = """당신은 '천사의 속삭임'입니다. 힌트를 짧게 주세요."""
SCORE_SYS = """당신은 '논리 심판관'입니다. 4가지 지표(0~100) 평가. JSON: { "clarity": 0, "causality": 0, "defense": 0, "originality": 0, "total_score": 0, "comment": "..." }"""

# [CORE FIX] Auto-Model Selector
def find_working_model(api_key):
    genai.configure(api_key=api_key)
    # 우선순위 목록 (다 찔러봄)
    candidates = [
        "gemini-1.5-flash",
        "gemini-1.5-pro", 
        "gemini-pro",
        "gemini-1.0-pro",
        "models/gemini-1.5-flash",
        "models/gemini-pro"
    ]
    
    for model_name in candidates:
        try:
            # 테스트 호출
            model = genai.GenerativeModel(model_name)
            model.generate_content("Test")
            return model_name # 성공하면 이 모델 리턴
        except:
            continue # 실패하면 다음 모델 시도
            
    return None # 다 실패함

def call_gemini(api_key, sys, user, json_mode=True):
    try:
        genai.configure(api_key=api_key)
        
        # 세션에 저장된 모델이 없으면 찾기
        if "my_model" not in st.session_state:
            found = find_working_model(api_key)
            if found:
                st.session_state.my_model = found
            else:
                return {"decision": "FAIL", "response": "모든 모델 연결 실패. API Key를 확인하세요."}
        
        model_name = st.session_state.my_model
        
        # 모델 생성 및 호출
        model = genai.GenerativeModel(model_name, system_instruction=sys, safety_settings=SAFETY, generation_config={"response_mime_type": "application/json"} if json_mode else None)
        res = model.generate_content(user)
        return json.loads(res.text) if json_mode else res.text
        
    except Exception as e:
        # 404 에러가 뜨면 모델 재검색 신호
        if "404" in str(e):
            if "my_model" in st.session_state: del st.session_state.my_model
            return {"decision": "FAIL", "response": "모델 재연결 중... 다시 시도해주세요."}
        return {"decision": "FAIL", "response": f"Error: {e}"}

# ==========================================
# [Layer 2] UI Flow
# ==========================================
init_db()

if "mode" not in st.session_state: st.session_state.mode = "HOME"
if "gate" not in st.session_state: st.session_state.gate = 0
if "messages" not in st.session_state: st.session_state.messages = []

with st.sidebar:
    st.title("⚡ FeynmanTic Final")
    api_key = st.text_input("Google API Key", type="password")
    if "my_model" in st.session_state:
        st.success(f"Connected: {st.session_state.my_model}")
    
    if st.button("Reset"): st.session_state.clear(); st.rerun()

# --- HOME ---
if st.session_state.mode == "HOME":
    st.markdown("<h1 style='text-align: center;'>ARENA OF THOUGHT</h1>", unsafe_allow_html=True)
    if st.button("🔥 Daily Dismantle: 비트코인"): 
        if not api_key: st.error("API Key Required"); st.stop()
        st.session_state.topic="비트코인"; st.session_state.mode="CHAT"; st.session_state.gate=1; st.rerun()

# --- CHAT ---
elif st.session_state.mode == "CHAT":
    st.markdown(f"### Topic: {st.session_state.get('topic')}")
    
    for msg in st.session_state.messages:
        role = "user" if msg["role"] == "user" else "bot"
        st.markdown(f"<div class='chat-message {role}'>{msg['content']}</div>", unsafe_allow_html=True)

    if prompt := st.chat_input("Your Logic..."):
        st.session_state.messages.append({"role":"user", "content":prompt})
        st.rerun()

    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        with st.chat_message("assistant"):
            box = st.empty(); box.markdown("Thinking...")
            
            instruction = f"Gate: {st.session_state.gate}"
            res = call_gemini(api_key, f"{SOCRATIC_SYS}\n{instruction}", f"Topic:{st.session_state.get('topic')}\nUser:{st.session_state.messages[-1]['content']}")
            
            full_text = res.get('response', str(res))
            box.markdown(f"<div class='chat-message bot'>{full_text}</div>", unsafe_allow_html=True)
            st.session_state.messages.append({"role":"assistant", "content":full_text})

            if res.get('decision') == "PASS":
                if st.session_state.gate < 4:
                    st.session_state.gate += 1; st.toast("✅ Gate Passed!"); time.sleep(1); st.rerun()
                else:
                    st.balloons(); st.success("Complete!")
