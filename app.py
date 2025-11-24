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
from datetime import datetime, date

# ==========================================
# [Layer 1] Logic & Core Functions (TOP DEFINITION)
# ==========================================
# Safety Setting
SAFETY = [{"category": cat, "threshold": "BLOCK_NONE"} for cat in ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]]

# Prompts
MAP_SYS = """... [지식의 지도 제작자 프롬프트 내용] ...""" # (For brevity, content remains the same as V29/V30)
DAILY_MISSION_SYS = """당신은 '일일 퀘스트 마스터'입니다. 오늘 날짜({today})를 기준으로 {role} 사용자가 해체할 만한 가장 흥미로운 주제 3가지를 뽑아주세요. JSON 출력: {{ "missions": [ {{"title": "주제명", "reason": "왜 중요한가"}}, ... ] }}"""
SOCRATIC_SYS = """당신은 '파인만틱 소크라테스'입니다. 질문으로 논리를 검증하세요. JSON: { "decision": "PASS"|"FAIL", "response": "..." }"""

def init_db():
    conn = sqlite3.connect('feynmantic_v31.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY, timestamp TEXT, role TEXT, topic TEXT, dialogue TEXT)''')
    conn.commit()
    conn.close()

def find_working_model(api_key):
    try:
        genai.configure(api_key=api_key)
        available = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        candidates = [m for m in available if 'gemini' in m]
        return candidates[0] if candidates else None
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

def call_gemini(api_key, sys, user, model_name):
    # [FIX] JSON Parsing & Model Logic Unified
    try:
        genai.configure(api_key=api_key)
        config = {"response_mime_type": "application/json"} if "1.5" in model_name else {}
        
        model = genai.GenerativeModel(model_name, system_instruction=sys, safety_settings=SAFETY, generation_config=config)
        final_prompt = f"{user}\n\n(Respond ONLY in JSON)" if "1.5" not in model_name else user
        
        res = model.generate_content(final_prompt)
        return extract_json(res.text)
        
    except Exception as e:
        return {"decision": "FAIL", "response": f"통신 오류 발생: {e}"}

# ==========================================
# [Layer 2] State Management & UI Config
# ==========================================
init_db()

st.set_page_config(page_title="FeynmanTic V31", page_icon="🗺️", layout="wide")

st.markdown("""
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    .stApp { background-color: #0E1117; color: #E0E0E0; font-family: 'Pretendard', sans-serif; }
    .chat-message { padding: 1.2rem; border-radius: 1rem; margin-bottom: 1rem; line-height: 1.6; box-shadow: 0 2px 4px rgba(0,0,0,0.2); }
    .chat-message.bot { background-color: #161B22; border-left: 4px solid #FF4B4B; font-family: 'Courier New', monospace; margin-right: 5%; }
    .mission-card { background: #2D333B; border-left: 5px solid #FFD700; padding: 15px; border-radius: 8px; margin-bottom: 15px; }
    .stButton button { width: 100%; border-radius: 8px; font-weight: bold; height: 3em; }
    </style>
""", unsafe_allow_html=True)

# Session State
if "mode" not in st.session_state: st.session_state.mode = "LANDING"
if "auto_model" not in st.session_state: st.session_state.auto_model = None
if "daily_missions" not in st.session_state: st.session_state.daily_missions = None
if "user_role" not in st.session_state: st.session_state.user_role = None
if "messages" not in st.session_state: st.session_state.messages = []
if "territory" not in st.session_state: st.session_state.territory = {"known": [], "unknown": []}
if "topic" not in st.session_state: st.session_state.topic = ""


# --- SIDEBAR & CONNECTION ---
with st.sidebar:
    st.title("⚡ FeynmanTic V31")
    api_key = st.text_input("Google API Key", type="password")
    
    if api_key and st.button("🔄 엔진 시동 (Connect)"):
        with st.spinner("시스템 점검 중..."):
            found = find_working_model(api_key)
            if found: st.session_state.auto_model = found; st.success(f"Connected: {found}")
            else: st.error("모델 연결 실패")

    if st.session_state.auto_model:
        st.info(f"✅ Connected: {st.session_state.auto_model}")
    
    if st.button("Reset"): st.session_state.clear(); st.rerun()

# --- SCENE 1: LANDING ---
if st.session_state.mode == "LANDING":
    st.markdown("<br><h1 style='text-align: center;'>CHOOSE YOUR UNIVERSE</h1><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    if c1.button("🎒 학생"): st.session_state.user_role = "SCHOOL"; st.session_state.mode = "HOME"; st.rerun()
    if c2.button("🛡️ 직장인"): st.session_state.user_role = "PRO"; st.session_state.mode = "HOME"; st.rerun()
    if c3.button("🌌 탐험가"): st.session_state.user_role = "EXPLORER"; st.session_state.mode = "HOME"; st.rerun()

# --- SCENE 2: HOME (Daily Mission + Map) ---
elif st.session_state.mode == "HOME":
    role = st.session_state.user_role
    st.markdown(f"## {role}의 작전실 (V31)")
    
    if not st.session_state.auto_model:
        st.warning("👈 엔진을 먼저 시동하세요.")
    else:
        # Daily Mission Generation (유저가 뭘 할지 고민할 필요 없게)
        if not st.session_state.daily_missions:
            with st.spinner("오늘의 미션을 생성 중..."):
                prompt = DAILY_MISSION_SYS.format(today=date.today(), role=role)
                res = call_gemini(api_key, "Daily Planner", prompt, st.session_state.auto_model)
                st.session_state.daily_missions = res.get('missions', [])

        st.markdown("### 🔥 Daily Mission")
        for mission in st.session_state.daily_missions:
            st.markdown(f"""
                <div class="mission-card">
                    <b>{mission['title']}</b>
                    <p style='font-size:0.8rem; color:#ccc;'>{mission['reason']}</p>
                </div>
            """, unsafe_allow_html=True)
            if st.button(f"🚩 정복 시작: {mission['title']}", key=f"mission_{mission['title'][:5]}"):
                st.session_state.topic = mission['title']
                st.session_state.mode = "CONQUEST"
                st.session_state.messages = [{"role":"assistant", "content":f"**'{mission['title']}'** 영토에 깃발을 꽂았습니다.\n\n이 땅에 대해 **당신이 아는 것(키워드)**들을 나열하여 지도를 그려보세요."}]
                st.rerun()
        
        st.markdown("---")
        custom_topic = st.text_input("직접 영토를 입력하세요", placeholder="예: 양자역학, 마키아벨리즘...")
        if st.button("🚩 Custom Topic 정복"):
            if custom_topic:
                st.session_state.topic = custom_topic
                st.session_state.mode = "CONQUEST"
                st.session_state.messages = [{"role":"assistant", "content":f"**'{custom_topic}'** 영토에 깃발을 꽂았습니다.\n\n이 땅에 대해 **당신이 아는 것(키워드)**들을 나열하여 지도를 그려보세요."}]
                st.rerun()

# --- SCENE 3: CONQUEST (Map Building) ---
elif st.session_state.mode == "CONQUEST":
    # 1. Knowledge Map Visualization
    st.markdown(f"### 🗺️ Map of {st.session_state.topic}")
    
    with st.container(border=True):
        k_list = st.session_state.territory['known']
        u_list = st.session_state.territory['unknown']
        
        st.markdown("#### 🏰 정복한 땅 (Known Territory)")
        if k_list:
            st.write(" ".join([f"<span class='territory-badge'>{k}</span>" for k in k_list]), unsafe_allow_html=True)
        else:
            st.caption("아직 밝혀진 땅이 없습니다.")
            
        st.markdown("#### ☁️ 미지의 안개 (Fog of War)")
        if u_list:
            cols = st.columns(min(len(u_list), 4))
            for i, u in enumerate(u_list):
                if cols[i%4].button(f"🔍 {u} 탐험하기", key=f"explore_{u}"):
                    st.session_state.messages.append({"role":"user", "content":f"나는 '{u}'에 대해 잘 몰라. 이게 내가 아는 것들과 어떻게 연결돼?"})
                    st.rerun()
        else: st.caption("탐색 중...")
    
    st.divider()

    # 2. Chat Interface
    for msg in st.session_state.messages:
        css = "user" if msg["role"] == "user" else "bot"
        st.markdown(f"<div class='chat-message {css}'>{msg['content']}</div>", unsafe_allow_html=True)

    if prompt := st.chat_input("아는 것을 설명하거나, 모르는 것을 물어보세요..."):
        # [Fix] UX 개선: Fake Loading Message
        st.session_state.messages.append({"role":"user", "content":prompt})
        st.session_state.messages.append({"role":"bot", "content":"Thinking... [AI Logic Filter Active]"}) # Fake Message
        st.rerun()

    if st.session_state.messages and st.session_state.messages[-1]["role"] != "user" and st.session_state.messages[-2]["role"] == "user":
        
        st.session_state.messages.pop() # remove fake message
        
        with st.chat_message("assistant"):
            box = st.empty(); box.markdown("지도를 그리는 중...")
            
            # Use the refined System Prompt
            sys_prompt = get_map_system_prompt(st.session_state.user_role, st.session_state.topic, st.session_state.territory['known'])
            user_prompt = f"Topic: {st.session_state.topic}. User Input: {st.session_state.messages[-1]['content']}. Current Known: {st.session_state.territory['known']}"

            res = call_gemini(api_key, sys_prompt, user_prompt, st.session_state.auto_model)
            
            text = res.get('response', str(res))
            box.markdown(f"<div class='chat-message bot'>{text}</div>", unsafe_allow_html=True)
            st.session_state.messages.append({"role":"assistant", "content":text})
            
            # Map Update Logic
            new_k = res.get('known_keywords', [])
            new_u = res.get('unknown_keywords', [])
            
            st.session_state.territory['known'] = list(set(st.session_state.territory['known'] + new_k))
            st.session_state.territory['unknown'] = list(set(st.session_state.territory['unknown'] + new_u) - set(st.session_state.territory['known']))
            
            if res.get('decision') == "CONQUERED":
                st.balloons()
                st.success("🎉 이 영토를 완전히 정복했습니다! 메인으로 돌아갑니다.")
                st.session_state.mode = "HOME"
            
            if new_k or new_u: st.rerun() # 지도 갱신을 위해 리로드
