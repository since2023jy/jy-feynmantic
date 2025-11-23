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
st.set_page_config(page_title="FeynmanTic V11.5", page_icon="⚡", layout="centered")

# 구형 라이브러리 호환을 위한 안전 설정
# (최신 안전 설정 문법이 구버전에서 에러날 수 있어 기본값 사용)
def safe_generate(model, prompt):
    try:
        return model.generate_content(prompt).text
    except:
        return "{}"

st.markdown("""
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    .stApp { background-color: #0E1117; color: #E0E0E0; font-family: 'Pretendard', monospace; }
    .chat-message { padding: 1rem; border-radius: 0.5rem; margin-bottom: 1rem; line-height: 1.6; }
    .chat-message.user { background-color: #161B22; border-right: 4px solid #7C4DFF; text-align: right; }
    .chat-message.bot { background-color: #1F2428; border-left: 4px solid #FF4B4B; font-family: 'Courier New'; }
    .stButton button { width: 100%; border-radius: 8px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# [Layer 1] Database
# ==========================================
def init_db():
    conn = sqlite3.connect('feynmantic.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY, timestamp TEXT, topic TEXT, mode TEXT, dialogue TEXT)''')
    conn.commit()
    conn.close()

def save_log(topic, mode, messages):
    conn = sqlite3.connect('feynmantic.db')
    c = conn.cursor()
    c.execute('INSERT INTO logs (timestamp, topic, mode, dialogue) VALUES (?, ?, ?, ?)',
              (datetime.now().strftime("%Y-%m-%d"), topic, mode, json.dumps(messages, ensure_ascii=False)))
    conn.commit()
    conn.close()

# ==========================================
# [Layer 2] AI Engine (Safe Mode)
# ==========================================
# 여기가 핵심 수정 사항입니다: gemini-pro 사용
MODEL_NAME = 'gemini-pro'

INTUITION_SYS = """당신은 '직관 유도자'입니다. 주제에 대해 '전혀 모른다'는 사용자를 위해 '밸런스 게임(이지선다)'을 만드세요. JSON 포맷으로 답하세요: { "scenario": "...", "option_a": "...", "option_b": "...", "question": "..." }"""
SOCRATIC_SYS = """당신은 '파인만틱 소크라테스'입니다. 질문으로 논리를 검증하세요. JSON 포맷으로 답하세요: { "decision": "PASS"|"FAIL", "response": "..." }"""

def call_gemini(api_key, sys, user):
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(MODEL_NAME)
        
        # 구형 모델은 System Prompt를 지원하지 않을 수 있어 User Prompt에 합침
        full_prompt = f"{sys}\n\n[User Input]: {user}\n\n(Please respond in JSON format only)"
        
        response = model.generate_content(full_prompt)
        text = response.text
        
        # JSON 파싱 보정
        s = text.find('{')
        e = text.rfind('}') + 1
        if s != -1 and e != -1:
            return json.loads(text[s:e])
        else:
            return {"decision": "FAIL", "response": text}
            
    except Exception as e:
        return {"decision": "FAIL", "response": f"Error: {str(e)}"}

# ==========================================
# [Layer 3] UI Flow
# ==========================================
init_db()

if "mode" not in st.session_state: st.session_state.mode = "HOME"
if "gate" not in st.session_state: st.session_state.gate = 0
if "messages" not in st.session_state: st.session_state.messages = []

with st.sidebar:
    st.title("⚡ FeynmanTic")
    st.caption(f"Engine: {MODEL_NAME}")
    api_key = st.text_input("Google API Key", type="password")
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
    st.progress(st.session_state.gate / 4)
    
    for msg in st.session_state.messages:
        role = "user" if msg["role"] == "user" else "bot"
        st.markdown(f"<div class='chat-message {role}'>{msg['content']}</div>", unsafe_allow_html=True)

    if prompt := st.chat_input("Your Logic..."):
        st.session_state.messages.append({"role":"user", "content":prompt})
        st.rerun()

    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        with st.chat_message("assistant"):
            box = st.empty(); box.markdown("Thinking...")
            
            instruction = f"Current Gate: {st.session_state.gate}"
            res = call_gemini(api_key, f"{SOCRATIC_SYS}\n{instruction}", f"Topic:{st.session_state.get('topic')}\nUser:{st.session_state.messages[-1]['content']}")
            
            full_text = res.get('response', str(res))
            box.markdown(f"<div class='chat-message bot'>{full_text}</div>", unsafe_allow_html=True)
            st.session_state.messages.append({"role":"assistant", "content":full_text})

            if res.get('decision') == "PASS":
                if st.session_state.gate < 4:
                    st.session_state.gate += 1; st.toast("✅ Gate Passed!"); time.sleep(1); st.rerun()
                else:
                    st.balloons(); st.success("Complete!")
