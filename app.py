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
st.set_page_config(page_title="FeynmanTic Auto", page_icon="⚡", layout="centered")

st.markdown("""
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    .stApp { background-color: #0E1117; color: #E0E0E0; font-family: 'Pretendard', monospace; }
    .chat-message { padding: 1rem; border-radius: 0.5rem; margin-bottom: 1rem; line-height: 1.6; box-shadow: 0 2px 4px rgba(0,0,0,0.2); }
    .chat-message.user { background-color: #161B22; border-right: 4px solid #7C4DFF; text-align: right; }
    .chat-message.bot { background-color: #1F2428; border-left: 4px solid #FF4B4B; font-family: 'Courier New'; }
    .success-box { background-color: #00E676; color: black; padding: 10px; border-radius: 5px; font-weight: bold; margin-bottom: 10px;}
    .stButton button { width: 100%; border-radius: 8px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# [Layer 1] Logic & Data
# ==========================================
def init_db():
    conn = sqlite3.connect('feynmantic_auto.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY, timestamp TEXT, topic TEXT, mode TEXT, dialogue TEXT, score_json TEXT)''')
    conn.commit()
    conn.close()

# [핵심] 사용 가능한 모델 자동 검색 함수
def find_working_model(api_key):
    try:
        genai.configure(api_key=api_key)
        # 구글에게 "나 무슨 모델 쓸 수 있어?" 물어보기
        available_models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available_models.append(m.name)
        
        # 우선순위: Flash -> Pro -> 아무거나
        for m in available_models:
            if 'flash' in m: return m
        for m in available_models:
            if 'pro' in m: return m
        
        return available_models[0] if available_models else None
    except:
        return None

# AI Logic
SAFETY = [{"category": cat, "threshold": "BLOCK_NONE"} for cat in ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]]

SOCRATIC_SYS = """당신은 '파인만틱 소크라테스'입니다. 질문으로 논리를 검증하세요. JSON: { "decision": "PASS"|"FAIL", "response": "..." }"""

def call_gemini(api_key, sys, user, model_name):
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name, system_instruction=sys, safety_settings=SAFETY, generation_config={"response_mime_type": "application/json"})
        res = model.generate_content(user)
        return json.loads(res.text)
    except Exception as e: return {"decision": "FAIL", "response": f"Error: {e}"}

# ==========================================
# [Layer 2] UI Flow
# ==========================================
init_db()

if "mode" not in st.session_state: st.session_state.mode = "HOME"
if "gate" not in st.session_state: st.session_state.gate = 0
if "messages" not in st.session_state: st.session_state.messages = []
if "auto_model" not in st.session_state: st.session_state.auto_model = None

with st.sidebar:
    st.title("⚡ FeynmanTic Auto")
    api_key = st.text_input("Google API Key", type="password")
    
    if api_key:
        if st.button("🔄 모델 연결하기 (Connect)"):
            with st.spinner("사용 가능한 모델 스캔 중..."):
                found_model = find_working_model(api_key)
                if found_model:
                    st.session_state.auto_model = found_model
                    st.success(f"연결 성공! 잡힌 모델: {found_model}")
                else:
                    st.error("이 키로 사용할 수 있는 모델이 없습니다. (키 권한 문제)")

    if st.session_state.auto_model:
        st.info(f"✅ Connected: {st.session_state.auto_model}")

    if st.button("Reset"): st.session_state.clear(); st.rerun()

# --- HOME ---
if st.session_state.mode == "HOME":
    st.markdown("<h1 style='text-align: center;'>ARENA OF THOUGHT</h1>", unsafe_allow_html=True)
    
    if st.session_state.auto_model:
        st.markdown(f"<div class='success-box'>시스템 준비 완료 ({st.session_state.auto_model})</div>", unsafe_allow_html=True)
        if st.button("🔥 Daily Dismantle: 비트코인"): 
            st.session_state.topic="비트코인"; st.session_state.mode="CHAT"; st.session_state.gate=1; st.rerun()
    else:
        st.warning("👈 사이드바에서 API Key를 넣고 [모델 연결하기]를 먼저 눌러주세요.")

# --- CHAT ---
elif st.session_state.mode == "CHAT":
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
            res = call_gemini(api_key, f"{SOCRATIC_SYS}\n{instruction}", f"Topic:{st.session_state.topic}\nUser:{st.session_state.messages[-1]['content']}", st.session_state.auto_model)
            
            full_text = res.get('response', str(res))
            box.markdown(f"<div class='chat-message bot'>{full_text}</div>", unsafe_allow_html=True)
            st.session_state.messages.append({"role":"assistant", "content":full_text})

            if res.get('decision') == "PASS":
                if st.session_state.gate < 4:
                    st.session_state.gate += 1; st.toast("✅ Gate Passed!"); time.sleep(1); st.rerun()
                else:
                    st.balloons(); st.success("Complete!")
