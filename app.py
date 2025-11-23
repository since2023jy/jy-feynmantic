import streamlit as st
import google.generativeai as genai
import json
import time
import random
import sqlite3
from datetime import datetime

# ==========================================
# [진단 모드] System Config
# ==========================================
st.set_page_config(page_title="FeynmanTic Diagnosis", page_icon="🩺", layout="centered")

st.markdown("""
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    .stApp { background-color: #0E1117; color: #E0E0E0; font-family: 'Pretendard', monospace; }
    .error-box { background-color: #FF4B4B; color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; font-weight: bold;}
    .success-box { background-color: #00E676; color: black; padding: 20px; border-radius: 10px; margin-bottom: 20px; font-weight: bold;}
    .stTextInput input { background-color: #1F2428 !important; color: white !important; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# [진단 로직]
# ==========================================
def test_connection(api_key):
    # 1. 공백 제거 (모바일 실수 방지)
    clean_key = api_key.strip()
    
    try:
        genai.configure(api_key=clean_key)
        
        # 2. 모델 테스트 (Pro -> Flash -> Legacy 순서)
        models_to_try = ['gemini-1.5-flash', 'gemini-pro']
        
        log_text = ""
        for model_name in models_to_try:
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content("Test")
                return True, f"성공! 연결된 모델: {model_name}", clean_key
            except Exception as e:
                log_text += f"❌ {model_name} 실패: {str(e)}\n"
        
        return False, log_text, clean_key
        
    except Exception as e:
        return False, f"치명적 오류: {str(e)}", clean_key

# ==========================================
# [UI] 화면 구성
# ==========================================
st.title("🩺 긴급 연결 진단소")
st.write(f"현재 설치된 구글 라이브러리 버전: **{genai.__version__}**")
st.info("☝️ 위 버전이 **0.7.2** 이상이어야 합니다. 낮으면 requirements.txt가 적용 안 된 겁니다.")

api_key_input = st.text_input("Google API Key를 입력하세요", type="password")

if st.button("진단 시작 (Diagnose)"):
    if not api_key_input:
        st.error("키를 입력해주세요.")
    else:
        with st.spinner("구글 서버에 노크하는 중..."):
            success, message, clean_key = test_connection(api_key_input)
            
            if success:
                st.markdown(f"<div class='success-box'>{message}</div>", unsafe_allow_html=True)
                st.balloons()
                st.success("이제 이 키로 채팅을 시작할 수 있습니다!")
                # 성공하면 세션에 저장
                st.session_state.valid_key = clean_key
            else:
                st.markdown(f"<div class='error-box'>연결 실패! 아래 로그를 확인하세요.</div>", unsafe_allow_html=True)
                st.code(message)
                st.warning("팁: 에러 메시지에 '400'이나 'INVALID'가 있으면 키 문제입니다. '404'가 계속 뜨면 서버 재부팅이 필요합니다.")

# 성공했을 때만 채팅창 보여주기
if "valid_key" in st.session_state:
    st.divider()
    st.subheader("💬 테스트 채팅")
    user_msg = st.text_input("아무 말이나 해보세요")
    if user_msg:
        genai.configure(api_key=st.session_state.valid_key)
        model = genai.GenerativeModel('gemini-pro')
        res = model.generate_content(user_msg)
        st.write(res.text)
