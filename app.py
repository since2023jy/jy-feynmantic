import streamlit as st
import google.generativeai as genai
import json

# ==========================================
# [Layer 0] Config
# ==========================================
st.set_page_config(page_title="FeynmanTic Final", page_icon="⚡", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #E0E0E0; }
    .chat-message { padding: 1rem; border-radius: 0.5rem; margin-bottom: 1rem; background-color: #1F2428; border-left: 4px solid #FF4B4B; }
    .stTextInput input { background-color: #0d1117 !important; color: white !important; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# [Layer 1] Logic (Gemini Pro Only)
# ==========================================
def call_gemini(api_key, user_input):
    try:
        genai.configure(api_key=api_key)
        # 가장 안전한 구형 모델 강제 사용
        model = genai.GenerativeModel('gemini-pro') 
        response = model.generate_content(user_input)
        return response.text
    except Exception as e:
        return f"Error: {str(e)}"

# ==========================================
# [Layer 2] UI
# ==========================================
if "messages" not in st.session_state: st.session_state.messages = []

with st.sidebar:
    st.title("⚡ FeynmanTic Lite")
    st.caption("Emergency Mode")
    api_key = st.text_input("Google API Key", type="password")
    if st.button("Reset"): st.session_state.messages = []; st.rerun()

st.markdown("<h1 style='text-align: center;'>ARENA OF THOUGHT</h1>", unsafe_allow_html=True)

for msg in st.session_state.messages:
    st.markdown(f"<div class='chat-message'>{msg}</div>", unsafe_allow_html=True)

if prompt := st.chat_input("논리를 입력하세요..."):
    st.session_state.messages.append(f"🧑‍💻 User: {prompt}")
    if not api_key:
        st.error("API Key가 필요합니다.")
    else:
        with st.spinner("Thinking..."):
            res = call_gemini(api_key, f"당신은 파인만틱 논리 검증관입니다. 다음 문장에 대해 반박하세요: {prompt}")
            st.session_state.messages.append(f"🤖 AI: {res}")
            st.rerun()
