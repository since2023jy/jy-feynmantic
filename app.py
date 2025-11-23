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
# [Layer 0] Config & Styles
# ==========================================
st.set_page_config(page_title="FeynmanTic V11.5", page_icon="⚡", layout="centered")

st.markdown("""
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    .stApp { background-color: #0E1117; color: #E0E0E0; font-family: 'Pretendard', monospace; }
    .chat-message { padding: 1rem; border-radius: 0.5rem; margin-bottom: 1rem; line-height: 1.6; box-shadow: 0 2px 4px rgba(0,0,0,0.2); }
    .chat-message.user { background-color: #161B22; border-right: 4px solid #7C4DFF; text-align: right; margin-left: 20%; }
    .chat-message.bot { background-color: #1F2428; border-left: 4px solid #FF4B4B; font-family: 'Courier New', monospace; margin-right: 10%; }
    .gate-badge { font-size: 0.7rem; padding: 4px 8px; border-radius: 20px; background: #21262D; color: #6E7681; border: 1px solid #30363D; margin-right: 3px; }
    .gate-active { background: rgba(255, 75, 75, 0.1); color: #FF4B4B; border-color: #FF4B4B; font-weight: bold; }
    .stButton button { width: 100%; border-radius: 8px; font-weight: bold; background-color: #21262D; color: #C9D1D9; border: 1px solid #30363D; }
    .stTextInput input { background-color: #0d1117 !important; color: #fff !important; border: 1px solid #30363d !important; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# [Layer 1] Logic & Data
# ==========================================
def init_db():
    conn = sqlite3.connect('feynmantic_debug.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY, timestamp TEXT, topic TEXT, mode TEXT, dialogue TEXT, score_json TEXT)''')
    conn.commit()
    conn.close()

def save_log(topic, mode, messages, score_data=None):
    conn = sqlite3.connect('feynmantic_debug.db')
    c = conn.cursor()
    c.execute('INSERT INTO logs (timestamp, topic, mode, dialogue, score_json) VALUES (?, ?, ?, ?, ?)',
              (datetime.now().strftime("%Y-%m-%d"), topic, mode, json.dumps(messages, ensure_ascii=False), json.dumps(score_data) if score_data else None))
    conn.commit()
    conn.close()

def get_spectator_feed():
    return [{"topic": "비트코인", "user_view": "디지털 에너지다.", "f_score": 92, "likes": 128},
            {"topic": "자유의지", "user_view": "화학작용일 뿐.", "f_score": 88, "likes": 95}]

# AI Config
SAFETY = [{"category": cat, "threshold": "BLOCK_NONE"} for cat in ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]]

INTUITION_SYS = """당신은 '직관 유도자'입니다. 밸런스 게임을 만드세요. JSON: { "scenario": "...", "option_a": "...", "option_b": "...", "question": "..." }"""
SOCRATIC_SYS = """당신은 '파인만틱 소크라테스'입니다. 질문으로 논리를 검증하세요. JSON: { "decision": "PASS"|"FAIL", "response": "..." }"""
WHISPER_SYS = """당신은 '천사의 속삭임'입니다. 힌트를 짧게 주세요."""
SCORE_SYS = """당신은 '논리 심판관'입니다. 4가지 지표(0~100) 평가. JSON: { "clarity": 0, "causality": 0, "defense": 0, "originality": 0, "total_score": 0, "comment": "..." }"""

def call_gemini(api_key, sys, user, model_name='gemini-1.5-flash', json_mode=True):
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name, system_instruction=sys, safety_settings=SAFETY, generation_config={"response_mime_type": "application/json"} if json_mode else None)
        res = model.generate_content(user)
        return json.loads(res.text) if json_mode else res.text
    except Exception as e: return {"decision": "FAIL", "response": f"Error: {e}"}

# ==========================================
# [Layer 2] UI Flow
# ==========================================
init_db()

if "mode" not in st.session_state: st.session_state.mode = "HOME"
if "gate" not in st.session_state: st.session_state.gate = 0
if "messages" not in st.session_state: st.session_state.messages = []
if "working_model" not in st.session_state: st.session_state.working_model = "gemini-1.5-flash" # Default

with st.sidebar:
    st.title("⚡ FeynmanTic V11.5")
    st.caption("Connection Doctor Edition")
    api_key = st.text_input("Google API Key", type="password")
    st.markdown("[🔑 키 발급받기](https://aistudio.google.com/app/apikey)")
    
    st.divider()
    
    # [DIAGNOSTIC BUTTON]
    if st.button("🔧 내 모델 찾기 (연결 테스트)"):
        if not api_key:
            st.error("API Key를 먼저 입력하세요.")
        else:
            try:
                genai.configure(api_key=api_key)
                with st.spinner("사용 가능한 모델을 스캔 중..."):
                    models = genai.list_models()
                    found_models = []
                    for m in models:
                        if 'generateContent' in m.supported_generation_methods:
                            found_models.append(m.name)
                    
                    if found_models:
                        st.success(f"연결 성공! 사용 가능 모델: {len(found_models)}개")
                        # 가장 최신 모델 자동 선택
                        if 'models/gemini-1.5-flash' in found_models:
                            st.session_state.working_model = 'gemini-1.5-flash'
                        elif 'models/gemini-1.5-pro' in found_models:
                            st.session_state.working_model = 'gemini-1.5-pro'
                        elif 'models/gemini-pro' in found_models:
                            st.session_state.working_model = 'gemini-pro'
                        
                        st.info(f"✅ 자동 선택된 모델: {st.session_state.working_model}")
                    else:
                        st.error("사용 가능한 모델이 없습니다. 새 API Key를 발급받으세요.")
            except Exception as e:
                st.error(f"연결 실패. 키를 확인하세요. (공백 주의)\n에러: {e}")

    if st.button("🔄 Reset System"): st.session_state.clear(); st.rerun()

# --- HOME ---
if st.session_state.mode == "HOME":
    st.markdown("<h1 style='text-align: center;'>ARENA OF THOUGHT</h1>", unsafe_allow_html=True)
    st.caption(f"Current Engine: {st.session_state.working_model}")
    
    if st.button("🔥 Daily Dismantle: 비트코인"): 
        if not api_key: st.error("API Key Required"); st.stop()
        st.session_state.topic="비트코인"; st.session_state.mode="CHAT"; st.session_state.gate=1; st.rerun()

# --- CHAT ---
elif st.session_state.mode == "CHAT":
    badges = "".join([f"<span class='gate-badge {'gate-active' if st.session_state.gate==i else ''}'>🔒 {i}</span>" for i in range(1,5)])
    st.markdown(f"<div style='text-align:center; margin-bottom:15px;'>{badges}</div>", unsafe_allow_html=True)
    
    for msg in st.session_state.messages:
        role = "user" if msg["role"] == "user" else "bot"
        st.markdown(f"<div class='chat-message {role}'>{msg['content']}</div>", unsafe_allow_html=True)

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

            # Use the detected model
            res = call_gemini(api_key, f"{SOCRATIC_SYS}\n{instruction}", f"Topic:{st.session_state.topic}\nUser:{st.session_state.messages[-1]['content']}", model_name=st.session_state.working_model)
            
            full_text = res.get('response', str(res))
            box.markdown(f"<div class='chat-message bot'>{full_text}</div>", unsafe_allow_html=True)
            st.session_state.messages.append({"role":"assistant", "content":full_text})

            if res.get('decision') == "PASS":
                if st.session_state.gate < 4:
                    st.session_state.gate += 1; st.toast("✅ Gate Passed!"); time.sleep(1); st.rerun()
                else:
                    st.balloons(); st.success("Complete!")
