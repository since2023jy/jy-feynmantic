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
st.set_page_config(page_title="FeynmanTic Debug", page_icon="🔧", layout="centered")

st.markdown("""
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    .stApp { background-color: #0E1117; color: #E0E0E0; font-family: 'Pretendard', monospace; }
    .error-log { background-color: #3d0e0e; border: 1px solid #ff4b4b; color: #ffabab; padding: 15px; border-radius: 5px; font-family: monospace; font-size: 0.8rem; white-space: pre-wrap; }
    .chat-message { padding: 1rem; border-radius: 0.5rem; margin-bottom: 1rem; line-height: 1.6; box-shadow: 0 2px 4px rgba(0,0,0,0.2); }
    .chat-message.user { background-color: #161B22; border-right: 4px solid #7C4DFF; text-align: right; }
    .chat-message.bot { background-color: #1F2428; border-left: 4px solid #FF4B4B; font-family: 'Courier New'; }
    .stButton button { width: 100%; border-radius: 8px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# [Layer 1] Logic (Debug Mode)
# ==========================================
def init_db():
    conn = sqlite3.connect('feynmantic_debug.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY, timestamp TEXT, topic TEXT, mode TEXT, dialogue TEXT, score_json TEXT)''')
    conn.commit()
    conn.close()

# HTTP 요청 함수 (에러 로그 출력 강화)
def call_gemini_http(api_key, sys_prompt, user_input):
    # 최신 모델부터 순서대로 시도
    models = ["gemini-1.5-flash", "gemini-pro", "gemini-1.5-pro-latest"]
    
    error_logs = [] # 실패 기록 저장
    
    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        
        full_text = f"{sys_prompt}\n\nUser Input: {user_input}\n\n(Respond in JSON)"
        data = {
            "contents": [{"parts": [{"text": full_text}]}],
            "generationConfig": {"response_mime_type": "application/json"}
        }
        
        try:
            response = requests.post(url, headers=headers, json=data)
            
            if response.status_code == 200:
                result = response.json()
                # 성공하면 바로 리턴
                text_res = result['candidates'][0]['content']['parts'][0]['text']
                return {"decision": "SUCCESS", "data": json.loads(text_res), "model": model}
            else:
                # 실패하면 에러 메시지 저장하고 다음 모델 시도
                error_logs.append(f"❌ {model} Failed ({response.status_code}): {response.text}")
                continue
                
        except Exception as e:
            error_logs.append(f"❌ {model} Error: {str(e)}")
            continue

    # 모든 모델 실패 시 로그 합쳐서 리턴
    return {"decision": "FAIL", "response": "\n".join(error_logs)}

# Prompts
INTUITION_SYS = """당신은 '직관 유도자'입니다. 밸런스 게임을 만드세요. JSON: { "scenario": "...", "option_a": "...", "option_b": "...", "question": "..." }"""
SOCRATIC_SYS = """당신은 '파인만틱 소크라테스'입니다. 질문으로 논리를 검증하세요. JSON: { "decision": "PASS"|"FAIL", "response": "..." }"""

# ==========================================
# [Layer 2] UI Flow
# ==========================================
init_db()

if "mode" not in st.session_state: st.session_state.mode = "HOME"
if "gate" not in st.session_state: st.session_state.gate = 0
if "messages" not in st.session_state: st.session_state.messages = []

with st.sidebar:
    st.title("⚡ FeynmanTic DEBUG")
    api_key = st.text_input("Google API Key", type="password")
    if st.button("Reset"): st.session_state.clear(); st.rerun()

# --- HOME ---
if st.session_state.mode == "HOME":
    st.markdown("<h1 style='text-align: center;'>ARENA OF THOUGHT</h1>", unsafe_allow_html=True)
    if st.button("🔥 Daily Dismantle: 비트코인 (Test Connection)"): 
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
            box = st.empty(); box.markdown("Connecting to Google...")
            
            # HTTP 호출
            result = call_gemini_http(api_key, f"{SOCRATIC_SYS} Gate {st.session_state.gate}", f"Topic:{st.session_state.get('topic')}\nUser:{st.session_state.messages[-1]['content']}")
            
            if result['decision'] == "SUCCESS":
                res_data = result['data']
                full_text = res_data.get('response', str(res_data))
                box.markdown(f"<div class='chat-message bot'>{full_text}</div>", unsafe_allow_html=True)
                st.session_state.messages.append({"role":"assistant", "content":full_text})

                if res_data.get('decision') == "PASS":
                    st.session_state.gate += 1; st.toast(f"✅ Gate Passed! (Model: {result['model']})"); time.sleep(1); st.rerun()
            else:
                # [디버깅용 에러 출력]
                box.error("모든 연결이 거부되었습니다. 아래 상세 로그를 확인하세요.")
                st.markdown(f"<div class='error-log'>{result['response']}</div>", unsafe_allow_html=True)
