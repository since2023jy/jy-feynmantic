import streamlit as st
import google.generativeai as genai
import json
import time
import random
import sqlite3
import pandas as pd
import plotly.graph_objects as go # [New] 지도 시각화용
from gtts import gTTS
from io import BytesIO
import re
from datetime import datetime

# ==========================================
# [Layer 0] Config & Style
# ==========================================
st.set_page_config(page_title="FeynmanTic V29", page_icon="🗺️", layout="wide")

st.markdown("""
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    .stApp { background-color: #0E1117; color: #E0E0E0; font-family: 'Pretendard', sans-serif; }
    
    .map-container { background: #1F2428; border: 1px solid #30363D; border-radius: 15px; padding: 20px; margin-bottom: 20px; text-align: center; }
    .territory-badge { background: #238636; color: white; padding: 5px 10px; border-radius: 15px; font-size: 0.8rem; margin: 5px; display: inline-block; }
    .fog-badge { background: #333; color: #888; padding: 5px 10px; border-radius: 15px; font-size: 0.8rem; margin: 5px; display: inline-block; border: 1px dashed #555; }
    
    .chat-message { padding: 1rem; border-radius: 0.5rem; margin-bottom: 1rem; line-height: 1.6; box-shadow: 0 2px 4px rgba(0,0,0,0.2); }
    .chat-message.user { background-color: #21262D; border-right: 4px solid #7C4DFF; text-align: right; }
    .chat-message.bot { background-color: #161B22; border-left: 4px solid #00E676; }
    
    .stButton button { width: 100%; border-radius: 8px; font-weight: bold; }
    .stTextInput input { background-color: #0d1117 !important; color: #fff !important; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# [Layer 1] Logic
# ==========================================
def init_db():
    conn = sqlite3.connect('feynmantic_v29.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY, timestamp TEXT, topic TEXT, territory TEXT)''')
    conn.commit()
    conn.close()

def find_working_model(api_key):
    try:
        genai.configure(api_key=api_key)
        available = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        priority = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-1.0-pro', 'gemini-pro']
        for p in priority:
            for a in available:
                if p in a: return a
        return available[0] if available else None
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

# --- PROMPTS (Map Expansion Logic) ---
# 퀴즈가 아니라 "네가 아는 키워드를 말해봐, 내가 연결해줄게" 방식
MAP_SYS = """
당신은 '지식의 지도 제작자(Cartographer)'입니다.
사용자가 주제에 대해 아는 것들을 말하면, 그것이 '핵심 영토(Core Territory)'인지 '변방(Edge)'인지 판단하세요.
그리고 사용자가 모르는(언급하지 않은) '미지의 땅(Fog of War)'이 무엇인지 지적하여 확장을 유도하세요.

[Output JSON]
{
    "decision": "CONTINUE"|"CONQUERED",
    "response": "피드백 (연결고리 질문)",
    "known_keywords": ["사용자가 말한 핵심단어1", "단어2"],
    "unknown_keywords": ["사용자가 놓친 핵심단어1", "단어2"] 
}
"""

def call_gemini(api_key, sys, user, model_name):
    try:
        genai.configure(api_key=api_key)
        config = {"response_mime_type": "application/json"} if "1.5" in model_name else {}
        safety = [{"category": cat, "threshold": "BLOCK_NONE"} for cat in ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]]
        
        model = genai.GenerativeModel(model_name, system_instruction=sys, safety_settings=safety, generation_config=config)
        final_prompt = f"{user}\n\n(Respond ONLY in JSON)" if "1.5" not in model_name else user
        res = model.generate_content(final_prompt)
        return extract_json(res.text)
    except Exception as e: return {"decision": "FAIL", "response": f"Error: {e}"}

# ==========================================
# [Layer 2] UI Flow
# ==========================================
init_db()
if "mode" not in st.session_state: st.session_state.mode = "LANDING"
if "messages" not in st.session_state: st.session_state.messages = []
if "auto_model" not in st.session_state: st.session_state.auto_model = None
if "territory" not in st.session_state: st.session_state.territory = {"known": [], "unknown": []}

with st.sidebar:
    st.title("🗺️ FeynmanTic")
    st.caption("V29 Conquest Edition")
    api_key = st.text_input("Google API Key", type="password")
    if api_key and st.button("🔄 Connect"):
        found = find_working_model(api_key)
        if found: st.session_state.auto_model = found; st.success("Connected")
    st.divider()
    if st.button("Reset"): st.session_state.clear(); st.rerun()

# --- SCENE 1: LANDING ---
if st.session_state.mode == "LANDING":
    st.markdown("<br><h1 style='text-align: center;'>BUILD YOUR MAP</h1><br>", unsafe_allow_html=True)
    topic = st.text_input("정복할 영토(주제)를 입력하세요", placeholder="예: 비트코인, 피타고라스, 광합성...")
    
    if st.button("🚩 깃발 꽂기 (Start)"):
        if not st.session_state.auto_model: st.error("키 연결 필요"); st.stop()
        st.session_state.topic = topic
        st.session_state.mode = "CONQUEST"
        st.session_state.messages = [{"role":"assistant", "content":f"**'{topic}'** 영토에 깃발을 꽂았습니다.\n\n이 땅에 대해 **당신이 확실히 아는 것(키워드)**들을 나열해 보세요. 지도를 그려드리겠습니다."}]
        st.rerun()

# --- SCENE 2: CONQUEST (Map Building) ---
elif st.session_state.mode == "CONQUEST":
    # [NEW] Knowledge Map Visualization
    st.markdown(f"### 🗺️ Map of {st.session_state.topic}")
    
    # Map Display
    with st.container():
        k_list = st.session_state.territory['known']
        u_list = st.session_state.territory['unknown']
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**🏰 정복한 땅 (Known)**")
            if k_list:
                for k in k_list: st.markdown(f"<span class='territory-badge'>{k}</span>", unsafe_allow_html=True)
            else: st.caption("아직 밝혀진 땅이 없습니다.")
            
        with col2:
            st.markdown("**☁️ 미지의 안개 (Unknown)**")
            if u_list:
                for u in u_list: 
                    if st.button(f"🔍 {u} 탐험하기"): # 클릭하면 바로 채팅으로 질문 입력
                        st.session_state.messages.append({"role":"user", "content":f"나는 '{u}'에 대해 잘 몰라. 이게 내가 아는 것들과 어떻게 연결돼?"})
                        st.rerun()
            else: st.caption("탐색 중...")
    
    st.divider()

    # Chat Interface
    for msg in st.session_state.messages:
        css = "user" if msg["role"] == "user" else "bot"
        st.markdown(f"<div class='chat-message {css}'>{msg['content']}</div>", unsafe_allow_html=True)

    if prompt := st.chat_input("아는 것을 설명하거나, 모르는 것을 물어보세요..."):
        st.session_state.messages.append({"role":"user", "content":prompt})
        st.rerun()

    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        with st.chat_message("assistant"):
            box = st.empty(); box.markdown("지도를 그리는 중...")
            
            inst = f"Topic: {st.session_state.topic}. User Input: {st.session_state.messages[-1]['content']}. Current Known: {st.session_state.territory['known']}"
            res = call_gemini(api_key, MAP_SYS, inst, st.session_state.auto_model)
            
            text = res.get('response', str(res))
            box.markdown(f"<div class='chat-message bot'>{text}</div>", unsafe_allow_html=True)
            st.session_state.messages.append({"role":"assistant", "content":text})
            
            # Update Map
            new_k = res.get('known_keywords', [])
            new_u = res.get('unknown_keywords', [])
            
            # 중복 제거 후 업데이트
            st.session_state.territory['known'] = list(set(st.session_state.territory['known'] + new_k))
            # Unknown에서 Known으로 이동한 것 제거
            st.session_state.territory['unknown'] = list(set(st.session_state.territory['unknown'] + new_u) - set(st.session_state.territory['known']))
            
            if new_k or new_u: st.rerun() # 지도 갱신을 위해 리로드

            if res.get('decision') == "CONQUERED":
                st.balloons()
                st.success("🎉 이 영토를 완전히 정복했습니다!")
                if st.button("메인으로"): st.session_state.clear(); st.rerun()
