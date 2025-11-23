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
st.set_page_config(page_title="FeynmanTic Hardcore", page_icon="⚡", layout="centered")

st.markdown("""
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    .stApp { background-color: #0E1117; color: #E0E0E0; font-family: 'Pretendard', monospace; }
    
    /* Chat UI - Sharp & Dark */
    .chat-message { padding: 1.2rem; border-radius: 0.5rem; margin-bottom: 1rem; line-height: 1.6; font-size: 1.05rem; }
    .chat-message.user { background-color: #161B22; border-right: 4px solid #7C4DFF; text-align: right; margin-left: 20%; }
    .chat-message.bot { background-color: #1F2428; border-left: 4px solid #FF4B4B; font-family: 'Courier New', monospace; margin-right: 5%; }
    
    /* Components */
    .gate-badge { font-size: 0.75rem; padding: 4px 10px; border-radius: 20px; background: #21262D; color: #888; border: 1px solid #333; margin-right: 5px; }
    .gate-active { background: rgba(255, 75, 75, 0.15); color: #FF4B4B; border-color: #FF4B4B; font-weight: bold; box-shadow: 0 0 8px rgba(255, 75, 75, 0.2); }
    .gate-insight { background: rgba(255, 215, 0, 0.15); color: #FFD700; border-color: #FFD700; font-weight: bold; }
    
    .stButton button { width: 100%; border-radius: 8px; font-weight: bold; }
    .stTextInput input { background-color: #0d1117 !important; color: #fff !important; border: 1px solid #30363d !important; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# [Layer 1] The Brain (System Prompts) - 여기가 핵심!
# ==========================================

# 1. 소크라테스 엔진 (매운맛)
SOCRATIC_SYS = """
[Role]
당신은 '파인만틱 논리 검증관'입니다. 친절한 AI 비서가 아닙니다.
사용자의 지적 허영심을 부수고, 진짜 이해했는지 검증하는 것이 목표입니다.

[Rules]
1. **절대 먼저 설명하지 마십시오.** 사용자가 설명하게 만드십시오.
2. **모호한 단어 금지:** "대충 그런 거", "느낌", "복잡한 시스템" 같은 단어를 쓰면 즉시 지적하십시오.
3. **반말/존댓말:** 냉철하고 건조한 존댓말을 사용하십시오. (예: "그건 비유가 틀렸습니다. 다시.")
4. **Format:** 반드시 JSON으로 응답하십시오.
   { "decision": "PASS" | "FAIL", "response": "검증관의 날카로운 피드백" }

[Gates Logic]
- Gate 1 (Definition): 전문 용어 금지. 5살 아이도 알 수 있는 '물리적/직관적 비유'를 요구하십시오.
- Gate 2 (Mechanism): '왜?'를 집요하게 물으십시오. A에서 B로 가는 인과관계를 설명 못하면 탈락시키십시오.
- Gate 3 (Falsification): 반증 사례(Edge Case)를 제시하고 방어하게 하십시오.
"""

# 2. 인사이트 엔진 (Gate 4)
INSIGHT_SYS = """
[Role]
당신은 '철학적 동반자'입니다. 
사용자가 팩트 검증(Gate 1~3)을 통과했습니다. 이제 칭찬해주고, 그들의 **'관점(View)'**을 물으십시오.

[Mission]
"팩트는 완벽합니다. 그렇다면 이 주제에 대한 당신만의 '한 줄 정의'는 무엇입니까?"라고 정중하게 물으십시오.
"""

# 3. 점수 및 요약 (Artifact)
SCORE_SYS = """
당신은 '지식 큐레이터'입니다.
대화를 분석해 4가지 지표(0~100)로 평가하고, 사용자의 통찰을 요약하십시오.
JSON: { "clarity": 0, "causality": 0, "defense": 0, "originality": 0, "total_score": 0, "user_insight_summary": "..." }
"""

# ==========================================
# [Layer 2] Connection Logic (Auto-Detect)
# ==========================================
def find_working_model(api_key):
    try:
        genai.configure(api_key=api_key)
        models = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']
        for m in models:
            try:
                model = genai.GenerativeModel(m)
                model.generate_content("Test")
                return m
            except: continue
        return None
    except: return None

def call_gemini(api_key, sys, user, model_name):
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name, system_instruction=sys, generation_config={"response_mime_type": "application/json"})
        res = model.generate_content(user)
        return json.loads(res.text)
    except Exception as e:
        # JSON 파싱 실패 시 텍스트라도 반환하는 안전장치
        return {"decision": "FAIL", "response": f"시스템 오류: {str(e)}. 다시 시도해주세요."}

# ==========================================
# [Layer 3] App Flow
# ==========================================
if "mode" not in st.session_state: st.session_state.mode = "HOME"
if "gate" not in st.session_state: st.session_state.gate = 0
if "messages" not in st.session_state: st.session_state.messages = []
if "auto_model" not in st.session_state: st.session_state.auto_model = None

with st.sidebar:
    st.title("⚡ FeynmanTic V12")
    st.caption("Hardcore Logic Engine")
    api_key = st.text_input("Google API Key", type="password")
    
    if api_key and not st.session_state.auto_model:
        if st.button("🔗 엔진 시동 (Connect)"):
            with st.spinner("검증관을 호출하는 중..."):
                found = find_working_model(api_key)
                if found:
                    st.session_state.auto_model = found
                    st.success(f"연결됨: {found}")
                else:
                    st.error("유효한 모델을 찾을 수 없습니다. 키를 확인하세요.")
    
    if st.session_state.auto_model:
        st.info(f"Engine: {st.session_state.auto_model}")
    
    if st.button("Reset"): st.session_state.clear(); st.rerun()

# --- HOME ---
if st.session_state.mode == "HOME":
    st.markdown("<br><h1 style='text-align: center;'>DISMANTLE WHAT?</h1>", unsafe_allow_html=True)
    st.caption("어설픈 지식은 여기서 통하지 않습니다.")
    
    if st.session_state.auto_model:
        col1, col2 = st.columns(2)
        if col1.button("🔥 Daily: 비트코인"): 
            st.session_state.topic="비트코인"; st.session_state.mode="CHAT"; st.session_state.gate=1
            st.session_state.messages = [{"role":"assistant", "content": "비트코인을 선택했군요. \n\n먼저 **'비트코인'이 무엇인지 정의**하십시오. \n단, **'가상화폐', '블록체인' 같은 전문 용어는 금지**입니다. 5살 아이에게 설명하듯 비유를 드십시오."}]
            st.rerun()
            
        if col2.button("🌌 Daily: 엔트로피"): 
            st.session_state.topic="엔트로피"; st.session_state.mode="CHAT"; st.session_state.gate=1
            st.session_state.messages = [{"role":"assistant", "content": "엔트로피라... 어려운 주제군요. \n\n수식 쓰지 말고 설명해 보세요. **방 청소를 안 하면 방이 어떻게 되나요?** 거기서부터 정의를 시작하십시오."}]
            st.rerun()
    else:
        st.warning("👈 먼저 사이드바에서 엔진 시동을 거십시오.")

# --- CHAT ---
elif st.session_state.mode == "CHAT":
    # Gate Progress
    gates = ["1.Definition", "2.Mechanism", "3.Falsification", "4.Insight"]
    badges = ""
    for i, g in enumerate(gates, 1):
        style = "gate-active" if st.session_state.gate == i else ""
        if i == 4 and st.session_state.gate == 4: style = "gate-insight"
        badges += f"<span class='gate-badge {style}'>🔒 {g}</span>"
    st.markdown(f"<div style='text-align:center; margin-bottom:20px;'>{badges}</div>", unsafe_allow_html=True)

    # Chat History
    for msg in st.session_state.messages:
        role = "user" if msg["role"] == "user" else "bot"
        st.markdown(f"<div class='chat-message {role}'>{msg['content']}</div>", unsafe_allow_html=True)

    # Input
    if prompt := st.chat_input("논리를 입력하세요..."):
        st.session_state.messages.append({"role":"user", "content":prompt})
        st.rerun()

    # AI Response
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        with st.chat_message("assistant"):
            box = st.empty()
            box.markdown("Thinking...")
            
            # Prompt Selection
            sys_prompt = SOCRATIC_SYS
            instruction = ""
            if st.session_state.gate == 1: instruction = "현재 단계: Gate 1 (정의). 전문 용어를 썼는지 감시하고, 썼으면 가차없이 FAIL을 주십시오."
            elif st.session_state.gate == 2: instruction = "현재 단계: Gate 2 (메커니즘). '왜?'라고 묻고 인과관계를 검증하십시오."
            elif st.session_state.gate == 3: instruction = "현재 단계: Gate 3 (반증). 예외 상황을 제시하고 방어하게 하십시오."
            elif st.session_state.gate == 4: sys_prompt = INSIGHT_SYS; instruction = "현재 단계: Gate 4 (통찰). 유저의 철학을 물어보십시오."

            full_prompt = f"{sys_prompt}\n\n[System Instruction]: {instruction}\n[Topic]: {st.session_state.topic}\n[User Input]: {st.session_state.messages[-1]['content']}"
            
            res = call_gemini(api_key, sys_prompt, full_prompt, st.session_state.auto_model)
            
            # Display Streaming-like
            response_text = res.get('response', '오류 발생')
            box.markdown(f"<div class='chat-message bot'>{response_text}</div>", unsafe_allow_html=True)
            st.session_state.messages.append({"role":"assistant", "content":response_text})

            # State Transition
            if res.get('decision') == "PASS":
                if st.session_state.gate < 4:
                    st.session_state.gate += 1
                    time.sleep(1); st.rerun()
                else:
                    st.balloons()
                    st.success("🎉 모든 관문을 통과했습니다! 당신의 논리는 완벽합니다.")
                    # Here could go to Artifact View
