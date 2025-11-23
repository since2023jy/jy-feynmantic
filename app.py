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
st.set_page_config(page_title="FeynmanTic V25.3", page_icon="⚡", layout="centered")

st.markdown("""
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    .stApp { background-color: #0E1117; color: #E0E0E0; font-family: 'Pretendard', sans-serif; }
    
    .mode-card { background: #161B22; border: 1px solid #30363D; border-radius: 15px; padding: 25px; text-align: center; height: 180px; display: flex; flex-direction: column; justify-content: center; cursor: pointer; transition: 0.2s; }
    .mode-card:hover { border-color: #7C4DFF; background: #1F2428; transform: translateY(-5px); }
    
    .chat-message { padding: 1.2rem; border-radius: 1rem; margin-bottom: 1rem; line-height: 1.6; box-shadow: 0 2px 4px rgba(0,0,0,0.2); }
    .chat-message.user { background-color: #21262D; border-right: 4px solid #7C4DFF; text-align: right; margin-left: 15%; }
    .chat-message.bot { background-color: #161B22; border-left: 4px solid #00E676; margin-right: 10%; }
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
    conn = sqlite3.connect('feynmantic_v25_3.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY, timestamp TEXT, role TEXT, level TEXT, topic TEXT, dialogue TEXT)''')
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

# --- DYNAMIC PROMPTS (학교별 분기) ---
def get_school_prompt(level):
    if level == "ELEM": # 초등
        return """[Role] 친절한 몬스터 헌터 선생님. [Mission] 어려운 말 금지. '피자', '장난감' 같은 쉬운 비유로 설명하게 유도. 칭찬 많이."""
    elif level == "MIDDLE": # 중등
        return """[Role] 개념 검증관. [Mission] 교과서 핵심 키워드가 들어갔는지 확인. 80점 이상이면 통과."""
    elif level == "HIGH": # 고등
        return """[Role] 수능 출제위원. [Mission] '왜?'를 집요하게 물어 논리적 허점(함정)을 파고들 것. 냉철하게 평가."""
    return """[Role] 파인만틱 선생님."""

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
        final_prompt = f"{user}\n\n(Respond ONLY in JSON with key 'response')" if "1.5" not in model_name else user
        
        res = model.generate_content(final_prompt)
        parsed = extract_json(res.text)
        
        if parsed: return parsed
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
if "school_level" not in st.session_state: st.session_state.school_level = None # New: 학교 레벨
if "gate" not in st.session_state: st.session_state.gate = 0
if "messages" not in st.session_state: st.session_state.messages = []
if "auto_model" not in st.session_state: st.session_state.auto_model = None
if "artifact" not in st.session_state: st.session_state.artifact = None

with st.sidebar:
    st.title("⚡ FeynmanTic")
    st.caption("V25.3 School Patch")
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
        if st.button("학생 입장"): st.session_state.user_role = "SCHOOL"; st.session_state.mode = "SCHOOL_SELECT"; st.rerun()
    with c2:
        st.markdown("""<div class="mode-card"><h1>🛡️</h1><h3>RED TEAM</h3><p style='color:#888; font-size:0.8rem;'>직장인 보고서 검증</p></div>""", unsafe_allow_html=True)
        if st.button("직장인 입장"): st.session_state.user_role = "PRO"; st.session_state.mode = "PRO_HOME"; st.rerun()
    with c3:
        st.markdown("""<div class="mode-card"><h1>🌌</h1><h3>EXPLORER</h3><p style='color:#888; font-size:0.8rem;'>지적 도플갱어 찾기</p></div>""", unsafe_allow_html=True)
        if st.button("탐험가 입장"): st.session_state.user_role = "EXPLORER"; st.session_state.mode = "EXPLORER_HOME"; st.rerun()

# --- SCENE 2-A: SCHOOL LEVEL SELECT (NEW) ---
elif st.session_state.mode == "SCHOOL_SELECT":
    st.markdown("<h2 style='text-align: center;'>학년을 선택하세요</h2>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.markdown("""<div style='text-align:center; padding:20px; background:#1F2428; border-radius:10px; border:1px solid #333;'><h3>🐣 초등</h3><p>몬스터 잡기</p></div>""", unsafe_allow_html=True)
        if st.button("초등 입장"): st.session_state.school_level="ELEM"; st.session_state.mode="SCHOOL_HOME"; st.rerun()
    with c2:
        st.markdown("""<div style='text-align:center; padding:20px; background:#1F2428; border-radius:10px; border:1px solid #333;'><h3>🏫 중등</h3><p>개념 80점 도전</p></div>""", unsafe_allow_html=True)
        if st.button("중등 입장"): st.session_state.school_level="MIDDLE"; st.session_state.mode="SCHOOL_HOME"; st.rerun()
    with c3:
        st.markdown("""<div style='text-align:center; padding:20px; background:#1F2428; border-radius:10px; border:1px solid #333;'><h3>🎓 고등</h3><p>수능 킬러 저격</p></div>""", unsafe_allow_html=True)
        if st.button("고등 입장"): st.session_state.school_level="HIGH"; st.session_state.mode="SCHOOL_HOME"; st.rerun()

# --- SCENE 2-B: SCHOOL HOME ---
elif st.session_state.mode == "SCHOOL_HOME":
    lv = st.session_state.school_level
    title = "🐣 초등 몬스터" if lv=="ELEM" else "🏫 중등 필수개념" if lv=="MIDDLE" else "🎓 수능 킬러주제"
    quests = {
        "ELEM": ["분수 몬스터", "도형의 이동", "시간과 시각"],
        "MIDDLE": ["피타고라스 정리", "광합성", "기회비용"],
        "HIGH": ["미분가능성", "상대성이론", "빈칸추론"]
    }
    
    st.markdown(f"## {title}")
    for q in quests[lv]:
        if st.button(f"도전: {q}"):
            if not st.session_state.auto_model: st.error("키 연결 필요"); st.stop()
            st.session_state.topic=q; st.session_state.mode="CHAT"; st.session_state.gate=1
            
            # 첫 인사말도 레벨별로 다르게
            intro = ""
            if lv == "ELEM": intro = f"안녕! **'{q}'** 잡으러 왔구나! 책 말고 네 생각대로 쉽게 설명해볼래?"
            elif lv == "MIDDLE": intro = f"**'{q}'** 개념 인증 시작합니다. 핵심 키워드를 포함해서 설명하세요."
            else: intro = f"**'{q}'** 출제 의도 파악 시작. 단순히 외운 거 말고, 논리적 구조를 브리핑해."
            
            st.session_state.messages=[{"role":"assistant", "content":intro}]
            st.rerun()

# --- SCENE 2-C: PRO & EXPLORER HOME ---
elif st.session_state.mode == "PRO_HOME":
    st.markdown("## 🛡️ 레드팀 작전실")
    if st.button("검증: 마케팅 기획안"):
        if not st.session_state.auto_model: st.error("키 필요"); st.stop()
        st.session_state.topic="마케팅"; st.session_state.mode="CHAT"; st.session_state.gate=1
        st.session_state.messages=[{"role":"assistant", "content":"기획안의 핵심 논리를 한 문장으로 요약하십시오. 수치 포함 필수."}]
        st.rerun()

elif st.session_state.mode == "EXPLORER_HOME":
    st.markdown("## 🌌 지식 탐험")
    if st.button("해체: 비트코인"):
        if not st.session_state.auto_model: st.error("키 필요"); st.stop()
        st.session_state.topic="비트코인"; st.session_state.mode="CHAT"; st.session_state.gate=1
        st.session_state.messages=[{"role":"assistant", "content":"비트코인을 한 줄로 정의한다면 무엇입니까?"}]
        st.rerun()

# --- SCENE 3: CHAT ---
elif st.session_state.mode == "CHAT":
    role = st.session_state.user_role
    st.markdown(f"<div style='text-align:center; margin-bottom:20px; color:#888;'>Topic: {st.session_state.topic} (Gate {st.session_state.gate})</div>", unsafe_allow_html=True)

    for msg in st.session_state.messages:
        css = "user" if msg["role"] == "user" else "bot"
        clean_content = str(msg['content']) # Display clean text
        st.markdown(f"<div class='chat-message {css}'>{clean_content}</div>", unsafe_allow_html=True)

    # Whisper (Gate 1~4)
    if st.session_state.messages[-1]["role"] == "assistant" and st.session_state.gate < 5:
        with st.expander("👼 Help"):
            if st.button("힌트"):
                hint = call_gemini(api_key, WHISPER_SYS, f"주제:{st.session_state.topic}\n질문:{st.session_state.messages[-1]['content']}", st.session_state.auto_model)
                st.markdown(f"<div class='chat-message whisper'>👼 {hint.get('response', '...')}</div>", unsafe_allow_html=True)

    if st.session_state.gate <= 4:
        if prompt := st.chat_input("입력..."):
            st.session_state.messages.append({"role":"user", "content":prompt})
            st.rerun()

    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        with st.chat_message("assistant"):
            box = st.empty(); box.markdown("Thinking...")
            
            # Prompt Selection Logic
            sys = ""
            if role == "SCHOOL":
                # [FIX] 학교 레벨에 따른 프롬프트 선택
                sys = get_school_prompt(st.session_state.school_level)
            elif role == "PRO":
                sys = RED_TEAM_SYS
            else:
                sys = DOPPEL_SYS
            
            # Common Instruction
            inst = f"현재 단계: Gate {st.session_state.gate}. 사용자의 논리를 검증하고 통과(PASS) 여부를 결정해. JSON: {{'decision':'PASS'|'FAIL', 'response':'...'}}"
            if role == "EXPLORER": inst += ", 'doppelganger': '위인 이름'"

            res = call_gemini(api_key, sys, f"{inst}\nUser:{st.session_state.messages[-1]['content']}", st.session_state.auto_model)
            
            text = res.get('response', str(res))
            box.markdown(f"<div class='chat-message bot'>{text}</div>", unsafe_allow_html=True)
            st.session_state.messages.append({"role":"assistant", "content":text})

            if res.get('decision') == "PASS":
                if st.session_state.gate < 4:
                    st.session_state.gate += 1; st.toast("✅ Passed!"); time.sleep(1); st.rerun()
                else:
                    st.session_state.result_data = res
                    st.session_state.mode = "ARTIFACT"; st.rerun()

# --- SCENE 4: ARTIFACT ---
elif st.session_state.mode == "ARTIFACT":
    st.balloons()
    st.markdown("<h1 style='text-align:center; color:#00E676;'>COMPLETE</h1>", unsafe_allow_html=True)
    
    if not st.session_state.artifact:
        with st.spinner("Creating..."):
            dialogue = json.dumps(st.session_state.messages)
            data = call_gemini(api_key, ARTIFACT_SYS, f"Dialog: {dialogue}", st.session_state.auto_model)
            st.session_state.artifact = data
            
            # Audio Generation
            script = f"{data.get('closing_remark', '축하합니다.')}"
            st.session_state.audio_path = generate_audio(script)

    data = st.session_state.artifact
    st.markdown(f"""
        <div class="artifact-box">
            <h3>🏆 {data.get('title', 'Result')}</h3>
            <p>✅ {data.get('fact_summary', [''])[0]}</p>
            <div style='background:rgba(255,215,0,0.1); padding:10px; border-radius:5px; color:#FFD700; margin:10px 0;'>
                ❝ {data.get('user_insight', '')} ❞
            </div>
            <p style='font-size:0.8rem; color:#aaa;'>AI: {data.get('closing_remark', '')}</p>
        </div>
    """, unsafe_allow_html=True)
    
    if st.session_state.audio_path:
        st.audio(st.session_state.audio_path, format="audio/mp3")
        
    if st.button("🏠 Home"): st.session_state.clear(); st.rerun()
