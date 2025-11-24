import streamlit as st
import google.generativeai as genai
import json
import time

# -----------------------------------------------------------------------------
# 1. Configuration & Setup
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="FeynmanTic: Save the Forest",
    page_icon="🌳",
    layout="centered"
)

# [중요] API 키 설정 (Streamlit Cloud Secrets 혹은 로컬 환경변수 사용 권장)
# 로컬에서 테스트할 땐 아래 "YOUR_API_KEY" 자리에 직접 키를 넣으셔도 됩니다.
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
except:
    # st.secrets가 없을 경우를 대비한 하드코딩 (보안 주의) 혹은 사용자 입력 유도
    # genai.configure(api_key="여기에_API_키를_넣으세요")
    pass

# Gemini 모델 설정 (JSON 모드 활성화)
generation_config = {
    "temperature": 0.7,
    "top_p": 0.95,
    "top_k": 40,
    "response_mime_type": "application/json", 
}

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash", # 속도 빠른 모델 권장
    generation_config=generation_config,
)

# -----------------------------------------------------------------------------
# 2. Game State Management (Session State)
# -----------------------------------------------------------------------------
if "gate" not in st.session_state:
    st.session_state.gate = 1
if "hp" not in st.session_state:
    st.session_state.hp = 100
if "visual_state" not in st.session_state:
    st.session_state.visual_state = "🌑 죽은 회색 숲 (Dead Forest)"
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        {"role": "assistant", "content": "으아아... 배고파... 내 눈앞이 깜깜해... 너, 인간이니? 나 밥 좀 줘... '광합성'이 뭔지 설명해주면 힘이 날 것 같아..."}
    ]
if "game_status" not in st.session_state:
    st.session_state.game_status = "PLAYING" # PLAYING, CLEAR, GAMEOVER

# -----------------------------------------------------------------------------
# 3. The Logic Engine (AI Persona)
# -----------------------------------------------------------------------------
def get_enty_response(user_input):
    system_prompt = f"""
    You are "Enty," the Tree Spirit. A user (Middle school student) is trying to save you by explaining "Photosynthesis."
    Current State -> Gate: {st.session_state.gate}/4, HP: {st.session_state.hp}
    
    # Rules
    1. Act like a hungry, slightly cranky giant. Speak Korean.
    2. Be strict logic checker. 
    3. Output JSON ONLY.

    # Gates Logic
    - Gate 1 (Definition): Explain simply. No jargon like "Chloroplast". Fail if too hard.
    - Gate 2 (Mechanism): Needs Water + CO2 + Light. Fail if ingredients missing.
    - Gate 3 (Falsification): User must deny "Night Photosynthesis". Light is energy!
    - Gate 4 (Insight): User must link plants -> oxygen -> human survival.

    # JSON Structure
    {{
        "message": "Enty's spoken response (max 2 sentences)",
        "result": "PASS" (Advance Gate) | "FAIL" (Damage User) | "KEEP_TALKING" (Need more info),
        "damage": Integer (0 for PASS/KEEP, 10-20 for FAIL),
        "visual_desc": "Short description of forest change (e.g., 'Leaf spouts', 'Sun rises')"
    }}
    """
    
    chat_content = f"User said: {user_input}"
    
    try:
        response = model.generate_content([system_prompt, chat_content])
        return json.loads(response.text)
    except Exception as e:
        return {"message": "으윽... 머리가 아파... (AI 오류)", "result": "KEEP_TALKING", "damage": 0, "visual_desc": "변화 없음"}

# -----------------------------------------------------------------------------
# 4. UI & Interaction Layer
# -----------------------------------------------------------------------------

# [Header] Dashboard (Mario Style)
col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="🛡️ GATE LEVEL", value=f"{st.session_state.gate} / 4")
with col2:
    st.metric(label="❤️ HP", value=st.session_state.hp, delta_color="inverse")
with col3:
    st.info(f"🌲 {st.session_state.visual_state}")

st.markdown("---")

# [Main] Chat Display
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# [Input] User Action
if st.session_state.game_status == "PLAYING":
    user_input = st.chat_input("정령에게 설명하기 (예: 광합성은 햇빛 요리야!)")
    
    if user_input:
        # 1. User Message Add
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.write(user_input)
            
        # 2. AI Processing
        with st.spinner("나무 정령이 당신의 논리를 맛보는 중..."):
            ai_data = get_enty_response(user_input)
            time.sleep(1) # 긴장감 조성
            
        # 3. Game State Update
        st.session_state.hp -= ai_data.get("damage", 0)
        st.session_state.visual_state = ai_data.get("visual_desc", st.session_state.visual_state)
        
        # 4. Result Handling
        if ai_data["result"] == "PASS":
            st.balloons() # 축하 효과
            st.session_state.gate += 1
            if st.session_state.gate > 4:
                st.session_state.game_status = "CLEAR"
                ai_data["message"] += " \n\n 🎉 [THE END] 숲이 완전히 살아났어! 너 정말 똑똑하구나!"
        
        elif ai_data["result"] == "FAIL":
            st.toast(f"💥 데미지를 입었습니다! HP -{ai_data['damage']}")
            if st.session_state.hp <= 0:
                st.session_state.game_status = "GAMEOVER"
                ai_data["message"] += " \n\n 💀 [GAME OVER] 정령이 배고파서 잠들었습니다..."

        # 5. AI Message Add
        st.session_state.chat_history.append({"role": "assistant", "content": ai_data["message"]})
        st.rerun()

# [Ending Screen]
elif st.session_state.game_status == "CLEAR":
    st.success("🏆 축하합니다! 당신의 논리가 숲을 구했습니다!")
    if st.button("다시 도전하기"):
        st.session_state.clear()
        st.rerun()

elif st.session_state.game_status == "GAMEOVER":
    st.error("💀 게임 오버... 논리를 더 다듬어서 다시 오세요.")
    if st.button("다시 도전하기"):
        st.session_state.clear()
        st.rerun()
