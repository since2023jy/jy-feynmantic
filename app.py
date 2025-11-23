import streamlit as st
import requests
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
st.set_page_config(page_title="FeynmanTic HTTP", page_icon="⚡", layout="centered")

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
# [Layer 1] Logic (HTTP Request) - 핵심 변경
# ==========================================
def init_db():
    conn = sqlite3.connect('feynmantic_http.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY, timestamp TEXT, topic TEXT, mode TEXT, dialogue TEXT, score_json TEXT)''')
    conn.commit()
    conn.close()

# HTTP 요청 함수 (라이브러리 없이 직접 통신)
def call_gemini_http(api_key, sys_prompt, user_input):
    # 1. Flash 모델 시도, 안되면 Pro 모델 시도
    models = ["gemini-1.5-flash", "gemini-pro"]
    
    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        
        # 프롬프트 합치기
        full_text = f"{sys_prompt}\n\nUser Input: {user_input}\n\n(Respond in JSON)"
        data = {
            "contents": [{"parts": [{"text": full_text}]}],
            "generationConfig": {"response_mime_type": "application/json"}
        }
        
        try:
            response = requests.post(url, headers=headers, json=data)
            
            if response.status_code == 200:
                result = response.json()
                text_res = result['candidates'][0]['content']['parts'][0]['text']
                return json.loads(text_res)
            else:
                continue # 실패하면 다음 모델 시도
                
        except Exception:
            continue

    # 모두 실패 시
    return {"decision": "FAIL", "response": "API Key Error or Server Busy. Try a NEW Key."}

# Prompts
INTUITION_SYS = """당신은 '직관 유도자'입니다. 밸런스 게임을 만드세요. JSON: { "scenario": "...", "option_a": "...", "option_b": "...", "question": "..." }"""
SOCRATIC_SYS = """당신은 '파인만틱 소크라테스'입니다. 질문으로 논리를 검증하세요. JSON: { "decision": "PASS"|"FAIL", "response": "..." }"""
SCORE_SYS = """당신은 '논리 심판관'입니다. 4가지 지표(0~100) 평가. JSON: { "clarity": 0, "causality": 0, "defense": 0, "originality": 0, "total_score": 0, "comment": "..." }"""

# ==========================================
# [Layer 2] UI Flow
# ==========================================
init_db()

if "mode" not in st.session_state: st.session_state.mode = "HOME"
if "gate" not in st.session_state: st.session_state.gate = 0
if "messages" not in st.session_state: st.session_state.messages = []

with st.sidebar:
    st.title("⚡ FeynmanTic HTTP")
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
            
            # HTTP 호출 사용
            res = call_gemini_http(api_key, f"{SOCRATIC_SYS}\n{instruction}", f"Topic:{st.session_state.get('topic')}\nUser:{st.session_state.messages[-1]['content']}")
            
            full_text = res.get('response', "Error connecting to Google.")
            box.markdown(f"<div class='chat-message bot'>{full_text}</div>", unsafe_allow_html=True)
            st.session_state.messages.append({"role":"assistant", "content":full_text})

            if res.get('decision') == "PASS":
                if st.session_state.gate < 4:
                    st.session_state.gate += 1; st.toast("✅ Gate Passed!"); time.sleep(1); st.rerun()
                else:
                    st.balloons(); st.success("Complete!")
