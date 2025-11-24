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
st.set_page_config(page_title="FeynmanTic V35", page_icon="🗺️", layout="wide")

st.markdown("""
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    .stApp { background-color: #0E1117; color: #E0E0E0; font-family: 'Pretendard', sans-serif; }
    
    .mode-card { background: #161B22; border: 1px solid #30363D; border-radius: 15px; padding: 25px; text-align: center; height: 180px; display: flex; flex-direction: column; justify-content: center; cursor: pointer; transition: 0.2s; }
    .mode-card:hover { border-color: #7C4DFF; background: #1F2428; transform: translateY(-5px); }
    
    .chat-message { padding: 1.2rem; border-radius: 1rem; margin-bottom: 1rem; line-height: 1.6; box-shadow: 0 2px 4px rgba(0,0,0,0.2); }
    .chat-message.user { background-color: #21262D; border-right: 4px solid #7C4DFF; text-align: right; margin-left: 15%; }
    .chat-message.bot { background-color: #161B22; border-left: 4px solid #FF4B4B; font-family: 'Courier New', monospace; margin-right: 5%; }
    
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
    conn = sqlite3.connect('feynmantic_v35.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY, timestamp TEXT, role TEXT, topic TEXT, dialogue TEXT)''')
    conn.commit()
    conn.close()

# [Fix] Model Finder (The 404 Buster)
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

# [Fix] Robust JSON Extraction
def extract_json(text):
    try:
        return json.loads(text)
    except:
        try:
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match: return json.loads(match.group())
            else: return None
        except: return None

# [NEW] Role-Specific System Prompt Generator
def get_map_system_prompt(role, topic, current_known):
    instruction = ""
    role_persona = "일반 지도 제작자"
    
    if role == "SCHOOL":
        instruction = "초등/중등 학생 눈높이에 맞춰 '비유'와 개념적 전제 조건을 'Unknown'으로 제시하십시오."
        role_persona = "친절한 가정 교사"
    elif role == "PRO":
        instruction = "기업 전문가(레드팀)의 관점에서, '규제 리스크', '수익성(ROI)', '경쟁자 방어 논리' 같은 비즈니스 결함을 'Unknown'으로 제시하여 공격하십시오."
        role_persona = "냉철한 투자 심의 위원"
    elif role == "EXPLORER":
        instruction = "지적 탐험가로서, 주제의 '역사적 맥락', '윤리적 딜레마', '다른 학문과의 연결고리' 같은 경계를 확장할 새로운 영역을 'Unknown'으로 제시하십시오."
        role_persona = "광장의 소크라테스"

    # 최종 시스템 프롬프트 구성
    final_prompt = f"""
    [Role] 당신은 '{role_persona}' 모드의 '지식의 지도 제작자(Cartographer)'입니다.
    [Directive] {instruction}
    
    사용자(유저 역할: {role})가 주제('{topic}')에 대해 아는 것들을 말하면, 그것을 'Known'으로 처리하고, 지시에 맞는 새로운 'Unknown'을 제시하여 확장을 유도하십시오.
    
    [Output JSON]
    {{
        "decision": "CONTINUE"|"CONQUERED",
        "response": "피드백 및 다음 질문 (사용자 역할에 맞는 질문)",
        "known_keywords": ["사용자가 말한 핵심단어1", "단어2"],
        "unknown_keywords": ["사용자가 놓친 핵심단어1", "단어2"] 
    }}
    """
    return final_prompt

# AI Call Function
def call_gemini(api_key, sys, user, model_name, retry_count=0):
    try:
        genai.configure(api_key=api_key)
        config = {"response_mime_type": "application/json"} if "1.5" in model_name else {}
        safety = [{"category": cat, "threshold": "BLOCK_NONE"} for cat in ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]]
        
        model = genai.GenerativeModel(model_name, system_instruction=sys, safety_settings=safety, generation_config=config)
        final_prompt = f"{user}\n\n(Respond ONLY in JSON)" 
        
        res = model.generate_content(final_prompt)
        parsed = extract_json(res.text)
        
        if parsed: return parsed
        else:
            if retry_count < 1:
                time.sleep(1)
                return call_gemini(api_key, sys, user, model_name, retry_count + 1)
            else:
                return {"decision": "FAIL", "response": f"JSON Parsing Failed. Raw Text: {res.text}"}
            
    except Exception as e:
        return {"decision": "FAIL", "response": f"System Error: {e}"}

# ==========================================
# [Layer 2] State Management & UI Flow
# ==========================================
init_db()

if "mode" not in st.session_state: st.session_state.mode = "LANDING"
if "auto_model" not in st.session_state: st.session_state.auto_model = None
if "user_role" not in st.session_state: st.session_state.user_role = None
if "messages" not in st.session_state: st.session_state.messages = []
if "territory" not in st.session_state: st.session_state.territory = {"known": [], "unknown": []}
if "topic" not in st.session_state: st.session_state.topic = ""
if "daily_missions" not in st.session_state: st.session_state.daily_missions = None # For simplicity, removed fetching logic

with st.sidebar:
    st.title("⚡ FeynmanTic V35")
    st.caption("Final Universe Edition")
    api_key = st.text_input("Google API Key", type="password")
    
    if api_key and st.button("🔄 엔진 시동 (Connect)"):
        with st.spinner("시스템 점검 중..."):
            found = find_working_model(api_key)
            if found: 
                st.session_state.auto_model = found
                st.success(f"Connected: {found}")
            else: 
                st.error("모델 연결 실패")
    
    st.divider()
    if st.button("Reset"): st.session_state.clear(); st.rerun()

# --- SCENE 1: LANDING ---
if st.session_state.mode == "LANDING":
    st.markdown("<br><h1 style='text-align: center;'>CHOOSE YOUR UNIVERSE</h1><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    if c1.button("🎒 학생"): st.session_state.user_role = "SCHOOL"; st.session_state.mode = "HOME"; st.rerun()
    if c2.button("🛡️ 직장인"): st.session_state.user_role = "PRO"; st.session_state.mode = "HOME"; st.rerun()
    if c3.button("🌌 탐험가"): st.session_state.user_role = "EXPLORER"; st.session_state.mode = "HOME"; st.rerun()

# --- SCENE 2: HOME ---
elif st.session_state.mode == "HOME":
    role = st.session_state.user_role
    st.markdown(f"## {role}의 작전실")
    
    if not st.session_state.auto_model:
        st.warning("👈 엔진을 먼저 시동하세요.")
    else:
        topic_input = st.text_input("정복할 영토(주제)를 입력하세요", placeholder="예: 비트코인, 광합성...")
        if st.button("🚩 깃발 꽂고 정복 시작"):
            if topic_input:
                st.session_state.topic = topic_input
                st.session_state.mode = "CONQUEST"
                
                initial_msg = ""
                if role == "SCHOOL": initial_msg = f"**'{topic_input}'** 개념을 네가 아는 가장 쉬운 말로 설명해 봐."
                elif role == "PRO": initial_msg = f"**'{topic_input}'** 안건에 대해 당신이 아는 핵심 논리만 보고하십시오."
                else: initial_msg = f"**'{topic_input}'**... 당신의 지도를 그릴 준비를 합시다. 아는 키워드를 나열해 주세요."
                
                st.session_state.messages = [{"role":"assistant", "content":initial_msg}]
                st.session_state.territory = {"known": [], "unknown": []}
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
            st.caption("아직 밝혀진 땅이 없습니다. 키워드를 말해주세요.")
            
        st.markdown("#### ☁️ 미지의 안개 (Fog of War)")
        if u_list:
            cols = st.columns(min(len(u_list), 4))
            for i, u in enumerate(u_list):
                if cols[i%4].button(f"🔍 {u} 탐험하기", key=f"explore_{u}"):
                    st.session_state.messages.append({"role":"user", "content":f"'{u}'에 대해 더 알아서 내 지도를 넓히고 싶어. 이게 내가 아는 것들과 어떻게 연결돼?"})
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
        st.session_state.messages.append({"role":"bot", "content":"Thinking... [AI Logic Filter Active]"}) 
        st.rerun()

    if st.session_state.messages and st.session_state.messages[-1]["role"] != "user" and st.session_state.messages[-2]["role"] == "user":
        
        st.session_state.messages.pop() # remove fake message
        
        with st.chat_message("assistant"):
            box = st.empty(); box.markdown("지도를 그리는 중...")
            
            sys_prompt = get_map_system_prompt(st.session_state.user_role, st.session_state.topic, st.session_state.territory['known'])
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

# --- SCENE 4: ARTIFACT ---
elif st.session_state.mode == "ARTIFACT":
    st.balloons()
    st.markdown("<h1 style='text-align:center; color:#00E676;'>CONQUEST ARTIFACT</h1>", unsafe_allow_html=True)
    
    if not st.session_state.artifact:
        with st.spinner("Artifact Creation..."):
            # Use ARTIFACT_SYS (placeholder)
            data = {"title": "The Conquered Territory", "user_insight": "My final view on this topic.", "closing_remark": "The map is now larger."}
            st.session_state.artifact = data
            
            # Audio Generation (requires a clean string input)
            script = f"정복 완료. 당신의 통찰: {data.get('user_insight', '')}."
            st.session_state.audio_path = generate_audio(script)

    data = st.session_state.artifact
    st.markdown(f"""
        <div class="artifact-box">
            <h3>🏆 {data.get('title', 'Result')}</h3>
            <p style='color:#FFD700;'>"{data.get('user_insight', '통찰 분석 중...')}"</p>
            <p style='font-size:0.8rem; color:#aaa;'>AI: {data.get('closing_remark', '')}</p>
        </div>
    """, unsafe_allow_html=True)
    
    if st.session_state.audio_path:
        st.audio(st.session_state.audio_path, format="audio/mp3")
        
    if st.button("🏠 Home"): st.session_state.clear(); st.rerun()
