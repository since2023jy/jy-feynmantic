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
# [Layer 0] Config & Styles
# ==========================================
st.set_page_config(page_title="FeynmanTic V37", page_icon="🧠", layout="wide")

st.markdown("""
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    .stApp { background-color: #0E1117; color: #E0E0E0; font-family: 'Pretendard', sans-serif; }
    
    .mode-card { background: #161B22; border: 1px solid #30363D; border-radius: 15px; padding: 25px; text-align: center; height: 180px; display: flex; flex-direction: column; justify-content: center; cursor: pointer; transition: 0.2s; }
    .mode-card:hover { border-color: #7C4DFF; background: #1F2428; transform: translateY(-5px); }
    
    .chat-message { padding: 1.2rem; border-radius: 1rem; margin-bottom: 1rem; line-height: 1.6; box-shadow: 0 2px 4px rgba(0,0,0,0.2); }
    .chat-message.user { background-color: #21262D; border-right: 4px solid #7C4DFF; text-align: right; margin-left: 15%; }
    .chat-message.bot { background-color: #161B22; border-left: 4px solid #FF4B4B; font-family: 'Courier New', monospace; margin-right: 5%; }
    .chat-message.thinking { background-color: #383838; color: #ccc; border-left: 4px solid #FFD700; font-style: italic; margin-right: 10%; }

    .territory-badge { background: #00E676; color: black; padding: 5px 10px; border-radius: 15px; font-size: 0.8rem; margin: 5px; display: inline-block; font-weight: bold; }
    .fog-badge { background: #333; color: #888; padding: 5px 10px; border-radius: 15px; font-size: 0.8rem; margin: 5px; display: inline-block; border: 1px dashed #555; }
    
    .artifact-box { background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); border: 2px solid #FFD700; border-radius: 15px; padding: 25px; text-align: center; margin-top: 20px; }
    
    .stButton button { width: 100%; border-radius: 8px; font-weight: bold; height: 3em; }
    .stTextInput input { background-color: #0d1117 !important; color: #fff !important; border: 1px solid #30363d !important; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# [Layer 1] Logic & Core Functions
# ==========================================
def init_db():
    conn = sqlite3.connect('feynmantic_v37.db', check_same_thread=False)
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

# --- DYNAMIC PROMPTS ---
def get_persona_data(role, level=None):
    if role == "SCHOOL":
        return {"persona": "친절한 가정 교사", "instruction": "초등/중등 학생 눈높이에 맞춰 '비유'와 개념의 전제 조건을 'Unknown'으로 제시하십시오."}
    elif role == "PRO":
        return {"persona": "냉철한 투자 심의 위원", "instruction": "비즈니스 결함, 규제 리스크, 수익성(ROI) 같은 실용적 결함을 'Unknown'으로 제시하여 공격하십시오."}
    elif role == "EXPLORER":
        return {"persona": "광장의 소크라테스", "instruction": "주제의 역사, 윤리, 철학적 맥락 같은 경계를 확장할 새로운 영역을 'Unknown'으로 제시하십시오."}
    return {"persona": "일반 지도 제작자", "instruction": "일반적인 지식의 연결고리를 Unknown으로 제시하세요."}

MAP_SYS_BASE = """
[Role] 당신은 '{role_persona}' 모드의 '지식의 지도 제작자'입니다.
[Directive] {instruction}
[Output JSON]
{{
    "decision": "CONTINUE"|"CONQUERED",
    "response": "피드백 및 다음 질문 (사용자 역할에 맞는 질문)",
    "known_keywords": ["키워드1", "키워드2"],
    "unknown_keywords": ["키워드1", "키워드2"] 
}}
"""

ARTIFACT_SYS = """당신은 '지식 큐레이터'입니다. 통찰을 강조하여 요약하세요. JSON: { "title": "...", "fact_summary": ["...", "..."], "user_insight": "...", "closing_remark": "..." }"""

def call_gemini(api_key, sys, user, model_name):
    try:
        genai.configure(api_key=api_key)
        config = {"response_mime_type": "application/json"} if "1.5" in model_name else {}
        safety = [{"category": cat, "threshold": "BLOCK_NONE"} for cat in ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]]
        
        model = genai.GenerativeModel(model_name, system_instruction=sys, safety_settings=safety, generation_config=config)
        final_prompt = f"{user}\n\n(Respond ONLY in JSON)" 
        
        res = model.generate_content(final_prompt)
        return extract_json(res.text)
    except Exception as e:
        return {"decision": "FAIL", "response": f"System Error: {e}"}

# ==========================================
# [Layer 2] UI & State Management
# ==========================================
init_db()
if "mode" not in st.session_state: st.session_state.mode = "CONNECT"
if "auto_model" not in st.session_state: st.session_state.auto_model = None
if "user_role" not in st.session_state: st.session_state.user_role = None
if "messages" not in st.session_state: st.session_state.messages = []
if "territory" not in st.session_state: st.session_state.territory = {"known": [], "unknown": []}
if "topic" not in st.session_state: st.session_state.topic = ""
if "artifact" not in st.session_state: st.session_state.artifact = None

with st.sidebar:
    st.title("⚡ FeynmanTic V37")
    st.caption("Final Universe Edition")
    api_key = st.text_input("Google API Key", type="password")
    
    if api_key and st.button("🔄 엔진 시동 (Connect)"):
        with st.spinner("시스템 점검 중..."):
            found = find_working_model(api_key)
            if found: 
                st.session_state.auto_model = found
                st.success(f"Connected: {found}")
                if st.session_state.mode == "CONNECT": 
                     st.session_state.mode = "LANDING"
            else: 
                st.error("모델 연결 실패")
    
    if st.session_state.auto_model:
        st.info(f"Engine: {st.session_state.auto_model.split('/')[-1]}")
    
    if st.button("Reset"): st.session_state.clear(); st.rerun()

# --- SCENE 0: CONNECTION CHECK ---
if st.session_state.mode == "CONNECT":
    st.markdown("<h1 style='text-align: center;'>ENTER THE ARENA</h1><br>", unsafe_allow_html=True)
    st.caption("API Key를 입력하고 엔진을 시동하십시오.")

# --- SCENE 1: LANDING (Role Selection) ---
elif st.session_state.mode == "LANDING":
    st.markdown("<h1 style='text-align: center;'>CHOOSE YOUR UNIVERSE</h1><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    if c1.button("🎒 학생"): st.session_state.user_role = "SCHOOL"; st.session_state.mode = "HOME"; st.rerun()
    if c2.button("🛡️ 직장인"): st.session_state.user_role = "PRO"; st.session_state.mode = "HOME"; st.rerunou.
    if c3.button("🌌 탐험가"): st.session_state.user_role = "EXPLORER"; st.session_state.mode = "HOME"; st.rerun()

# --- SCENE 2: HOME (Topic Input) ---
elif st.session_state.mode == "HOME":
    role = st.session_state.user_role
    st.markdown(f"## {role}의 작전실")
    
    topic_input = st.text_input("정복할 영토(주제)를 입력하세요", placeholder="예: 비트코인, 광합성...")
    if st.button("🚩 깃발 꽂고 정복 시작"):
        if topic_input:
            st.session_state.topic = topic_input
            st.session_state.mode = "CONQUEST"
            
            role_data = get_persona_data(st.session_state.user_role)
            # [UX Nudge] 권위적인 첫 메시지 + 키워드 넛지
            initial_msg = f"""
            **'{topic_input}'** 영토에 깃발을 꽂았습니다.

            당신의 역할 **({role_data['persona']})**에 맞춰 지도를 그릴 시간입니다.

            **[첫 번째 임무]**
            <b>책이나 검색 없이, 이 주제에 대해 당신이 '확실히 아는' 키워드를 3~5개만 나열하십시오.</b> (예: 기술, 리스크, 투자)
            """
            
            st.session_state.messages = [{"role":"assistant", "content":initial_msg}]
            st.session_state.territory = {"known": [], "unknown": []}
            st.rerun()

# --- SCENE 3: CONQUEST (Map Building Logic) ---
elif st.session_state.mode == "CONQUEST":
    # 1. Knowledge Map Visualization
    st.markdown(f"### 🗺️ Map of {st.session_state.topic}")
    
    with st.container(border=True):
        k_list = st.session_state.territory['known']
        u_list = st.session_state.territory['unknown']
        
        st.markdown("#### 🏰 정복한 땅 (Known Territory)")
        if k_list: st.write(" ".join([f"<span class='territory-badge'>{k}</span>" for k in k_list]), unsafe_allow_html=True)
        else: st.caption("아직 밝혀진 땅이 없습니다. 키워드를 말해주세요.")
            
        st.markdown("#### ☁️ 미지의 안개 (Fog of War)")
        if u_list:
            cols = st.columns(min(len(u_list), 4))
            for i, u in enumerate(u_list):
                if cols[i%4].button(f"🔍 {u} 탐험하기", key=f"explore_{u}"):
                    st.session_state.messages.append({"role":"user", "content":f"'{u}'에 대해 더 알아서 내 지도를 넓히고 싶어. 이게 내가 아는 것들과 어떻게 연결돼?'"})
                    st.session_state.messages.append({"role":"bot", "content":"Thinking... [AI Logic Filter Active]"}) # Fake Loading
                    st.rerun()
        else: st.caption("더 이상 탐험할 미지의 땅이 없습니다! 정복 완료.")
    
    st.divider()

    # 2. Chat Interface
    for msg in st.session_state.messages:
        css = "user" if msg["role"] == "user" else "bot"
        st.markdown(f"<div class='chat-message {css}'>{msg['content']}</div>", unsafe_allow_html=True)

    if prompt := st.chat_input("아는 것을 설명하거나, 모르는 것을 물어보세요..."):
        # 1. User Input Append + Fake Loading
        st.session_state.messages.append({"role":"user", "content":prompt})
        st.session_state.messages.append({"role":"bot", "content":"Thinking... [AI Logic Filter Active]"}) # Fake Loading
        st.rerun()

    # 3. AI Logic Execution
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "bot" and st.session_state.messages[-2]["role"] == "user":
        
        st.session_state.messages.pop() # remove fake message
        
        with st.chat_message("assistant"):
            box = st.empty(); box.markdown("지도를 그리는 중...")
            
            # Dynamic System Prompt Call
            role_data = get_persona_data(st.session_state.user_role)
            sys_prompt = MAP_SYS_BASE.format(role_persona=role_data['persona'], instruction=role_data['instruction'])
            user_prompt = f"Topic: {st.session_state.topic}. User Input: {st.session_state.messages[-1]['content']}. Current Known: {st.session_state.territory['known']}"

            res = call_gemini(api_key, sys_prompt, user_prompt, st.session_state.auto_model)
            
            text = res.get('response', str(res))
            box.markdown(f"<div class='chat-message bot'>{text}</div>", unsafe_allow_html=True)
            st.session_state.messages.append({"role":"assistant", "content":text})
            
            # Map Update Logic
            new_k = [k for k in res.get('known_keywords', []) if k]
            new_u = [u for u in res.get('unknown_keywords', []) if u]
            
            st.session_state.territory['known'] = list(set(st.session_state.territory['known'] + new_k))
            st.session_state.territory['unknown'] = list(set(st.session_state.territory['unknown'] + new_u) - set(st.session_state.territory['known']))
            
            if res.get('decision') == "CONQUERED":
                st.balloons()
                st.success("🎉 영토 정복 완료! 아티팩트를 생성합니다.")
                st.session_state.mode = "ARTIFACT"
            
            if new_k or new_u or res.get('decision') == "CONQUERED": st.rerun() 

# --- SCENE 4: ARTIFACT (Final Diploma Screen) ---
elif st.session_state.mode == "ARTIFACT":
    st.balloons()
    st.markdown("<h1 style='text-align:center; color:#00E676;'>CONQUEST ARTIFACT DIPLOMA</h1>", unsafe_allow_html=True)
    
    if st.button("🏠 Home"): st.session_state.clear(); st.rerun()
