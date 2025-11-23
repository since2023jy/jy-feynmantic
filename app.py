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
from datetime import datetime

# ==========================================
# [Layer 0] Config & Design System
# ==========================================
st.set_page_config(page_title="FeynmanTic V25.1", page_icon="⚡", layout="centered")

st.markdown("""
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    .stApp { background-color: #0E1117; color: #E0E0E0; font-family: 'Pretendard', sans-serif; }
    
    .mode-card { background: #161B22; border: 1px solid #30363D; border-radius: 15px; padding: 25px; text-align: center; height: 180px; display: flex; flex-direction: column; justify-content: center; cursor: pointer; transition: 0.2s; }
    .mode-card:hover { border-color: #7C4DFF; background: #1F2428; transform: translateY(-5px); }
    
    .chat-message { padding: 1rem; border-radius: 0.5rem; margin-bottom: 1rem; line-height: 1.6; box-shadow: 0 2px 4px rgba(0,0,0,0.2); }
    .chat-message.user { background-color: #21262D; border-right: 4px solid #7C4DFF; text-align: right; margin-left: 15%; }
    .chat-message.bot { background-color: #161B22; border-left: 4px solid #FF4B4B; font-family: 'Courier New', monospace; margin-right: 5%; }
    .chat-message.whisper { background-color: #0d1117; border: 1px dashed #4285F4; color: #8ab4f8; font-size: 0.9rem; text-align: center; padding: 10px; margin: 10px 0; }

    .gate-badge { font-size: 0.75rem; padding: 4px 10px; border-radius: 20px; background: #30363D; color: #aaa; margin-right: 4px; border: 1px solid #444; }
    .gate-active { background: rgba(0, 230, 118, 0.1); color: #00E676; border-color: #00E676; font-weight: bold; }
    
    .artifact-box { background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); border: 2px solid #FFD700; border-radius: 15px; padding: 25px; text-align: center; margin-top: 20px; }
    
    .stButton button { width: 100%; border-radius: 8px; font-weight: bold; height: 3em; }
    .stTextInput input { background-color: #0d1117 !important; color: #fff !important; border: 1px solid #30363d !important; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# [Layer 1] Logic
# ==========================================
def init_db():
    conn = sqlite3.connect('feynmantic_v25_1.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY, timestamp TEXT, role TEXT, topic TEXT, dialogue TEXT)''')
    conn.commit()
    conn.close()

def find_working_model(api_key):
    try:
        genai.configure(api_key=api_key)
        available = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available.append(m.name)
        
        priority = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-1.0-pro', 'gemini-pro']
        for p in priority:
            for a in available:
                if p in a: return a
        for a in available:
            if 'gemini' in a: return a
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

# --- [FIX] PROMPTS MOVED TO GLOBAL SCOPE ---
SCHOOL_SYS = """[Role] 파인만틱 선생님. [Mission] 학생이 개념을 '비유'로 설명하게 유도. 정답을 주지 말고 질문할 것. 짧고 명확하게."""
RED_TEAM_SYS = """[Role] 기업 레드팀 리더. [Mission] 보고서/기획안을 무자비하게 검증. 추상적 형용사 금지. 숫자 요구. 리스크 공격."""
DOPPEL_SYS = """[Role] 지적 성향 분석가. [Mission] 사용자의 답변을 분석해 역사 속 위인(일론 머스크, 소크라테스, 손자 등)과 매칭하고 싱크로율을 계산."""
WHISPER_SYS = """당신은 '천사의 속삭임'입니다. 사용자가 막힌 부분에 대해 결정적인 '비유 힌트'만 짧게 던지세요. JSON: {"response": "..."}"""
ARTIFACT_SYS = """당신은 '지식 큐레이터'입니다. 대화 내용을 요약하세요. 특히 사용자의 통찰(View)을 강조하세요. JSON: { "title": "...", "fact_summary": ["...", "..."], "user_insight": "...", "closing_remark": "..." }"""

def call_gemini(api_key, sys, user, model_name, retry_count=0):
    try:
        genai.configure(api_key=api_key)
        config = {"response_mime_type": "application/json"} if "1.5" in model_name else {}
        safety = [{"category": cat, "threshold": "BLOCK_NONE"} for cat in ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]]
        
        model = genai.GenerativeModel(model_name, system_instruction=sys, safety_settings=safety, generation_config=config)
        final_prompt = f"{user}\n\n(Respond ONLY in JSON)" if "1.5" not in model_name else user
        
        res = model.generate_content(final_prompt)
        parsed = extract_json(res.text)
        
        if parsed:
            return parsed
        else:
            if retry_count < 1:
                time.sleep(1)
                return call_gemini(api_key, sys, user, model_name, retry_count + 1)
            else:
                return {"decision": "FAIL", "response": res.text}
    except Exception as e:
        return {"decision": "FAIL", "response": f"Error: {e}"}

# ==========================================
# [Layer 2] UI Flow
# ==========================================
init_db()
if "mode" not in st.session_state: st.session_state.mode = "LANDING"
if "user_role" not in st.session_state: st.session_state.user_role = None
if "gate" not in st.session_state: st.session_state.gate = 0
if "messages" not in st.session_state: st.session_state.messages = []
if "auto_model" not in st.session_state: st.session_state.auto_model = None
if "artifact" not in st.session_state: st.session_state.artifact = None
if "shadow_mates" not in st.session_state: st.session_state.shadow_mates = [{"name": "논리왕 공룡", "status": "🔥 분수 격파 중"}, {"name": "새벽의 부엉이", "status": "💤 휴식 중"}]

with st.sidebar:
    st.title("⚡ FeynmanTic")
    st.caption("V25.1 Patched")
    api_key = st.text_input("Google API Key", type="password")
    
    if api_key and st.button("🔄 엔진 시동 (Connect)"):
        with st.spinner("시스템 점검 중..."):
            found = find_working_model(api_key)
            if found: 
                st.session_state.auto_model = found
                st.success(f"Connected: {found}")
            else: 
                st.error("모델 연결 실패 (키 권한 확인)")
    st.divider()
    if st.button("🏠 메인으로 (Reset)"): st.session_state.clear(); st.rerun()

# --- SCENE 1: LANDING ---
if st.session_state.mode == "LANDING":
    st.markdown("<br><h1 style='text-align: center;'>CHOOSE YOUR UNIVERSE</h1><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("""<div class="mode-card"><h1>🎒</h1><h3>SCHOOL</h3><p style='color:#888; font-size:0.8rem;'>초중고 개념 정복</p></div>""", unsafe_allow_html=True)
        if st.button("학생 입장"): st.session_state.user_role = "SCHOOL"; st.session_state.mode = "SCHOOL_HOME"; st.rerun()
    with c2:
        st.markdown("""<div class="mode-card"><h1>🛡️</h1><h3>RED TEAM</h3><p style='color:#888; font-size:0.8rem;'>직장인 보고서 검증</p></div>""", unsafe_allow_html=True)
        if st.button("직장인 입장"): st.session_state.user_role = "PRO"; st.session_state.mode = "PRO_HOME"; st.rerun()
    with c3:
        st.markdown("""<div class="mode-card"><h1>🌌</h1><h3>EXPLORER</h3><p style='color:#888; font-size:0.8rem;'>지적 도플갱어 찾기</p></div>""", unsafe_allow_html=True)
        if st.button("탐험가 입장"): st.session_state.user_role = "EXPLORER"; st.session_state.mode = "EXPLORER_HOME"; st.rerun()

# --- SCENE 2: HOMES ---
elif st.session_state.mode == "SCHOOL_HOME":
    st.markdown("## 🎒 오늘의 퀘스트")
    t1, t2 = st.tabs(["⚔️ 퀘스트", "👻 친구들"])
    with t1:
        quests = ["분수의 덧셈 (초3)", "피타고라스 (중2)", "미분가능성 (고3)"]
        for q in quests:
            if st.button(f"도전: {q}"):
                if not st.session_state.auto_model: st.error("키 연결 필요"); st.stop()
                st.session_state.topic = q; st.session_state.mode = "CHAT"; st.session_state.gate = 1
                st.session_state.messages = [{"role":"assistant", "content":f"안녕! **'{q}'** 정복하러 왔구나.\n책 보지 말고, 네가 이해한 대로 쉽게 설명해 줄래?"}]
                st.rerun()
    with t2:
        for mate in st.session_state.shadow_mates: st.info(f"👻 **{mate['name']}**: {mate['status']}")

elif st.session_state.mode == "PRO_HOME":
    st.markdown("## 🛡️ 작전 상황실")
    st.markdown("""<div style='border:1px solid #FF4B4B; color:#FF4B4B; padding:10px; border-radius:5px; text-align:center; margin-bottom:15px;'>🚨 WARNING: 감정 배제. 팩트 중심.</div>""", unsafe_allow_html=True)
    topic = st.text_input("검증받을 안건 (Agenda)", placeholder="예: 2025년 마케팅 예산 증액안")
    if st.button("검증 시작"):
        if not st.session_state.auto_model: st.error("키 연결 필요"); st.stop()
        if topic:
            st.session_state.topic = topic; st.session_state.mode = "CHAT"; st.session_state.gate = 1
            st.session_state.messages = [{"role":"assistant", "content":f"**'{topic}'** 안건 상정합니다.\n\n이 기획의 **핵심 논리(Core Thesis)**를 한 문장으로 보고하십시오."}]
            st.rerun()

elif st.session_state.mode == "EXPLORER_HOME":
    st.markdown("## 🌌 지식의 평원")
    t1, t2 = st.tabs(["🔥 News", "🏛️ Classics"])
    with t1:
        news = ["비트코인 반감기", "AI 기본소득", "저출산 대책"]
        for n in news:
            if st.button(f"해체하기: {n}"):
                if not st.session_state.auto_model: st.error("키 연결 필요"); st.stop()
                st.session_state.topic = n; st.session_state.mode = "CHAT"; st.session_state.gate = 1
                st.session_state.messages = [{"role":"assistant", "content":f"**'{n}'**... 흥미로운 주제군요.\n이 현상을 꿰뚫는 당신만의 **한 줄 정의**는 무엇입니까?"}]
                st.rerun()
    with t2:
        if st.button("📜 정의란 무엇인가?"):
            st.session_state.topic = "정의"; st.session_state.mode = "CHAT"; st.session_state.gate = 1
            st.session_state.messages = [{"role":"assistant", "content":"정의(Justice)... 당신의 철학을 들려주세요."}]
            st.rerun()

# --- SCENE 3: CHAT ---
elif st.session_state.mode == "CHAT":
    role = st.session_state.user_role
    color = "#00E676" if role == "SCHOOL" else "#FF4B4B" if role == "PRO" else "#7C4DFF"
    st.markdown(f"<div style='text-align:center; border-bottom:2px solid {color}; margin-bottom:20px; font-weight:bold; color:{color};'>TOPIC: {st.session_state.topic}</div>", unsafe_allow_html=True)
    
    gates = ["Def", "Mech", "Fals", "View"]
    badges = "".join([f"<span class='gate-badge {'gate-active' if st.session_state.gate==i+1 else ''}'>🔒 {g}</span>" for i, g in enumerate(gates)])
    st.markdown(f"<div style='text-align:center; margin-bottom:20px;'>{badges}</div>", unsafe_allow_html=True)

    for msg in st.session_state.messages:
        css = "user" if msg["role"] == "user" else "bot"
        st.markdown(f"<div class='chat-message {css}'>{msg['content']}</div>", unsafe_allow_html=True)

    # Whisper Hint [FIXED]
    if st.session_state.messages[-1]["role"] == "assistant" and st.session_state.gate < 5:
        with st.expander("👼 Help Me"):
            if st.button("힌트 듣기"):
                hint = call_gemini(api_key, WHISPER_SYS, f"주제:{st.session_state.topic}\n질문:{st.session_state.messages[-1]['content']}", st.session_state.auto_model)
                st.markdown(f"<div class='chat-message whisper'>👼 {hint.get('response', '...')}</div>", unsafe_allow_html=True)

    if st.session_state.gate <= 4:
        if prompt := st.chat_input("입력..."):
            st.session_state.messages.append({"role":"user", "content":prompt})
            st.rerun()

    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        with st.chat_message("assistant"):
            box = st.empty(); box.markdown("Thinking...")
            
            # Select System Prompt based on Role
            if role == "SCHOOL": sys = SCHOOL_SYS
            elif role == "PRO": sys = RED_TEAM_SYS
            else: sys = DOPPEL_SYS

            instruction = ""
            if st.session_state.gate == 1: instruction = "Gate 1: Definition. No Jargon."
            elif st.session_state.gate == 2: instruction = "Gate 2: Mechanism. Check Causality."
            elif st.session_state.gate == 3: instruction = "Gate 3: Falsification. Check Edge Cases."
            elif st.session_state.gate == 4: instruction = "Gate 4: Insight."

            res = call_gemini(api_key, f"{sys}\n{instruction}", f"Topic:{st.session_state.topic}\nUser:{st.session_state.messages[-1]['content']}", st.session_state.auto_model)
            
            text = res.get('response', str(res))
            box.markdown(f"<div class='chat-message bot'>{text}</div>", unsafe_allow_html=True)
            st.session_state.messages.append({"role":"assistant", "content":text})

            if res.get('decision') == "PASS":
                if st.session_state.gate < 4:
                    st.session_state.gate += 1; st.toast("✅ Gate Passed!"); time.sleep(1.5); st.rerun()
                else:
                    st.session_state.mode = "ARTIFACT"; st.rerun()

# --- SCENE 4: ARTIFACT ---
elif st.session_state.mode == "ARTIFACT":
    st.balloons()
    st.markdown("<h1 style='text-align:center; color:#00E676;'>INSIGHT ACQUIRED</h1>", unsafe_allow_html=True)
    
    if not st.session_state.artifact:
        with st.spinner("Creating Artifact..."):
            dialogue = json.dumps(st.session_state.messages)
            data = call_gemini(api_key, ARTIFACT_SYS, f"Dialog: {dialogue}", st.session_state.auto_model)
            st.session_state.artifact = data
            
            script = f"주제 {st.session_state.topic}. 당신의 통찰: {data.get('user_insight', '')}."
            st.session_state.audio_path = generate_audio(script)

    data = st.session_state.artifact
    st.markdown(f"""
        <div class="artifact-box">
            <h3>🏆 {data.get('title', 'Result')}</h3>
            <div style='background:rgba(255,215,0,0.1); padding:10px; border-radius:5px; color:#FFD700; margin:10px 0;'>
                ❝ {data.get('user_insight', '')} ❞
            </div>
            <p style='font-size:0.8rem; color:#aaa;'>AI: {data.get('closing_remark', '')}</p>
        </div>
    """, unsafe_allow_html=True)
    
    if st.session_state.audio_path:
        st.audio(st.session_state.audio_path, format="audio/mp3")
        
    if st.button("🏠 Home"): st.session_state.clear(); st.rerun()
