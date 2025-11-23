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
# [Layer 0] Config & Style
# ==========================================
st.set_page_config(page_title="FeynmanTic V26", page_icon="🧠", layout="wide") # 레이아웃 wide로 변경

st.markdown("""
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    .stApp { background-color: #0E1117; color: #E0E0E0; font-family: 'Pretendard', sans-serif; }
    
    /* UI Components */
    .chat-message { padding: 1rem; border-radius: 0.5rem; margin-bottom: 1rem; line-height: 1.6; box-shadow: 0 2px 4px rgba(0,0,0,0.2); }
    .chat-message.user { background-color: #21262D; border-right: 4px solid #7C4DFF; text-align: right; margin-left: 15%; }
    .chat-message.bot { background-color: #161B22; border-left: 4px solid #00E676; font-family: 'Courier New', monospace; margin-right: 5%; }
    .chat-message.system { background-color: #2D0A0A; color: #FF4B4B; border: 1px dashed #FF4B4B; text-align: center; font-size: 0.9rem; }
    
    .stat-box { background: #161B22; border: 1px solid #30363D; border-radius: 10px; padding: 15px; margin-bottom: 10px; }
    .stat-delta { color: #00E676; font-weight: bold; font-size: 0.8rem; float: right; }
    .stat-minus { color: #FF4B4B; font-weight: bold; font-size: 0.8rem; float: right; }
    
    .stButton button { width: 100%; border-radius: 8px; font-weight: bold; }
    .stTextInput input { background-color: #0d1117 !important; color: #fff !important; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# [Layer 1] Logic & Stats
# ==========================================
def init_db():
    conn = sqlite3.connect('feynmantic_v26.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY, timestamp TEXT, role TEXT, topic TEXT, dialogue TEXT, final_stats TEXT)''')
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

# --- NEW: Scoring Prompts ---
# AI가 답변만 보는 게 아니라 '점수 변화량'을 계산해서 줌
SCORING_INSTRUCTION = """
[평가 기준]
1. 이해력(und): 개념 정의가 명확한가?
2. 설명력(exp): 비유가 적절한가?
3. 창의력(cre): 독창적인 관점인가?
4. 융합력(syn): 다른 개념과 연결했는가?
5. 애티튜드(att): 논리적인 태도인가? (공격적이지 않고 차분한가)

[Output Format]
JSON: {
    "decision": "PASS"|"FAIL",
    "response": "피드백 멘트",
    "score_delta": { "und": 0~10, "exp": 0~10, "cre": 0~10, "syn": 0~10, "att": -5~5 }
}
"""

SCHOOL_SYS = f"""[Role] 파인만틱 선생님. [Mission] 학생이 개념을 '비유'로 설명하게 유도. {SCORING_INSTRUCTION}"""
RED_TEAM_SYS = f"""[Role] 기업 레드팀 리더. [Mission] 보고서를 무자비하게 검증. 숫자/논리 집착. {SCORING_INSTRUCTION}"""
DOPPEL_SYS = f"""[Role] 지적 성향 분석가. [Mission] 위인 매칭 및 사고력 평가. {SCORING_INSTRUCTION}"""

def call_gemini(api_key, sys, user, model_name):
    try:
        genai.configure(api_key=api_key)
        config = {"response_mime_type": "application/json"} if "1.5" in model_name else {}
        safety = [{"category": cat, "threshold": "BLOCK_NONE"} for cat in ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]]
        
        model = genai.GenerativeModel(model_name, system_instruction=sys, safety_settings=safety, generation_config=config)
        # 현재 스탯 정보도 같이 줌 (AI가 참고하라고)
        final_prompt = f"{user}\n\n(JSON format only)"
        
        res = model.generate_content(final_prompt)
        return extract_json(res.text)
    except Exception as e:
        return {"decision": "FAIL", "response": f"Error: {e}", "score_delta": {}}

# ==========================================
# [Layer 2] State Management
# ==========================================
init_db()
if "mode" not in st.session_state: st.session_state.mode = "LANDING"
if "stats" not in st.session_state: 
    # 초기 스탯 (Attitude는 100점 만점 시작, 나머지는 0점부터 빌드업)
    st.session_state.stats = {"und": 10, "exp": 10, "cre": 10, "syn": 10, "att": 100}
if "messages" not in st.session_state: st.session_state.messages = []
if "gate" not in st.session_state: st.session_state.gate = 0
if "auto_model" not in st.session_state: st.session_state.auto_model = None

# ==========================================
# [Layer 3] UI Flow
# ==========================================
with st.sidebar:
    st.title("⚡ FeynmanTic V26")
    st.caption("The Pentagonal Stat System")
    
    if st.session_state.mode == "CHAT":
        st.markdown("### 🧠 My Brain Stats")
        
        # Radar Chart
        labels = {"und":"이해력", "exp":"설명력", "cre":"창의력", "syn":"융합력", "att":"애티튜드"}
        data = pd.DataFrame(dict(
            r=list(st.session_state.stats.values()),
            theta=[labels[k] for k in st.session_state.stats.keys()]
        ))
        fig = px.line_polar(data, r='r', theta='theta', line_close=True, range_r=[0, 100])
        fig.update_traces(fill='toself', line_color='#7C4DFF')
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", 
            plot_bgcolor="rgba(0,0,0,0)", 
            font_color="white",
            margin=dict(t=20, b=20, l=30, r=30),
            height=250
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Stat Detail
        for k, v in st.session_state.stats.items():
            color = "#FF4B4B" if k == 'att' and v < 80 else "#00E676"
            st.markdown(f"**{labels[k]}**: <span style='color:{color}'>{v}</span>", unsafe_allow_html=True)

    api_key = st.text_input("Google API Key", type="password")
    if api_key and st.button("🔄 Connect"):
        found = find_working_model(api_key)
        if found: st.session_state.auto_model = found; st.success("Connected")
    
    if st.button("Reset"): st.session_state.clear(); st.rerun()

# --- SCENE 1: LANDING ---
if st.session_state.mode == "LANDING":
    st.markdown("<br><h1 style='text-align: center;'>CHOOSE UNIVERSE</h1><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    if c1.button("🎒 SCHOOL"): st.session_state.user_role="SCHOOL"; st.session_state.mode="CHAT_INIT"; st.rerun()
    if c2.button("🛡️ RED TEAM"): st.session_state.user_role="PRO"; st.session_state.mode="CHAT_INIT"; st.rerun()
    if c3.button("🌌 EXPLORER"): st.session_state.user_role="EXPLORER"; st.session_state.mode="CHAT_INIT"; st.rerun()

# --- SCENE 2: INIT CHAT ---
elif st.session_state.mode == "CHAT_INIT":
    topic = st.text_input("주제 입력 (Topic)", placeholder="예: 비트코인, 미분, 마케팅...")
    if st.button("START"):
        st.session_state.topic = topic
        st.session_state.mode = "CHAT"
        st.session_state.gate = 1
        intro = f"**'{topic}'** 해체를 시작합니다. \n\n먼저 이것의 **'정의(Definition)'**를 내려보세요."
        st.session_state.messages = [{"role":"assistant", "content":intro}]
        st.rerun()

# --- SCENE 3: THE ARENA (Main Chat) ---
elif st.session_state.mode == "CHAT":
    # Main Layout (Chat vs Stats handled by Sidebar)
    
    # Gate Progress
    cols = st.columns(4)
    gates = ["Def", "Mech", "Fals", "View"]
    for i, g in enumerate(gates):
        active = "border: 2px solid #00E676; color: #00E676;" if st.session_state.gate == i+1 else "border: 1px solid #333; color: #555;"
        cols[i].markdown(f"<div style='text-align:center; border-radius:5px; padding:5px; {active} font-size:0.8rem;'>{g}</div>", unsafe_allow_html=True)

    st.markdown("---")

    # Chat Log
    for msg in st.session_state.messages:
        css = "user" if msg["role"] == "user" else "bot" if msg["role"] == "assistant" else "whisper"
        st.markdown(f"<div class='chat-message {css}'>{msg['content']}</div>", unsafe_allow_html=True)

    # Hint Button (Attitude Penalty)
    if st.session_state.gate < 5:
        col1, col2 = st.columns([4, 1])
        with col2:
            if st.button("🆘 힌트 (-10 Att)"):
                # Penalty Logic
                st.session_state.stats['att'] -= 10
                st.toast("⚠️ 태도 점수가 10점 감점되었습니다!")
                
                # Get Hint
                hint_sys = "당신은 힌트 요정입니다. 결정적 힌트를 짧게 주세요. JSON: {'response': '...'}"
                res = call_gemini(api_key, hint_sys, f"Topic:{st.session_state.topic}\nHistory:{st.session_state.messages[-1]['content']}", st.session_state.auto_model)
                
                hint_text = res.get('response', '힌트 생성 실패')
                st.session_state.messages.append({"role":"whisper", "content":f"👼 힌트: {hint_text}"})
                st.rerun()

    # Input
    if st.session_state.gate <= 4:
        if prompt := st.chat_input("논리 입력..."):
            st.session_state.messages.append({"role":"user", "content":prompt})
            st.rerun()

    # AI Logic
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        with st.chat_message("assistant"):
            box = st.empty(); box.markdown("채점 중...")
            
            role = st.session_state.user_role
            sys = SCHOOL_SYS if role=="SCHOOL" else RED_TEAM_SYS if role=="PRO" else DOPPEL_SYS
            
            inst = f"Current Gate: {st.session_state.gate}. User Input: {st.session_state.messages[-1]['content']}"
            res = call_gemini(api_key, sys, inst, st.session_state.auto_model)
            
            text = res.get('response', 'Error')
            box.markdown(f"<div class='chat-message bot'>{text}</div>", unsafe_allow_html=True)
            st.session_state.messages.append({"role":"assistant", "content":text})
            
            # [핵심] 스탯 업데이트 로직
            deltas = res.get('score_delta', {})
            if deltas:
                changes = []
                for k, v in deltas.items():
                    if k in st.session_state.stats:
                        st.session_state.stats[k] = max(0, min(100, st.session_state.stats[k] + v))
                        if v != 0: changes.append(f"{k.upper()} {'+' if v>0 else ''}{v}")
                
                if changes:
                    st.toast(f"📈 스탯 변동: {', '.join(changes)}")

            if res.get('decision') == "PASS":
                if st.session_state.gate < 4:
                    st.session_state.gate += 1; time.sleep(1.5); st.rerun()
                else:
                    st.session_state.mode = "ARTIFACT"; st.rerun()

# --- SCENE 4: ARTIFACT ---
elif st.session_state.mode == "ARTIFACT":
    st.balloons()
    st.markdown("<h1 style='text-align:center; color:#00E676;'>LEGENDARY</h1>", unsafe_allow_html=True)
    
    # Final Radar Chart
    labels = {"und":"이해력", "exp":"설명력", "cre":"창의력", "syn":"융합력", "att":"애티튜드"}
    df = pd.DataFrame(dict(r=list(st.session_state.stats.values()), theta=list(labels.values())))
    fig = px.line_polar(df, r='r', theta='theta', line_close=True, range_r=[0, 100])
    fig.update_traces(fill='toself', line_color='#00E676')
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="white")
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown(f"<h3 style='text-align:center;'>최종 태도 점수: {st.session_state.stats['att']}점</h3>", unsafe_allow_html=True)
    if st.session_state.stats['att'] < 80:
        st.warning("⚠️ 힌트를 너무 많이 사용했습니다. 다음엔 스스로 힘으로 도전하세요!")
    else:
        st.success("🎖️ 명예로운 승리입니다!")

    if st.button("처음으로"): st.session_state.clear(); st.rerun()
