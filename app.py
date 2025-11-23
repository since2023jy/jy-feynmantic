import streamlit as st
import datetime
import time

# ==========================================
# 1. 엔진 설정 (Session State) - 데이터 저장소
# ==========================================
if 'thoughts' not in st.session_state:
    # 초기 데이터 (예시)
    st.session_state.thoughts = [
        {
            "concept": "FeynmanTic (파인만틱)",
            "explanation": "어려운 말을 쓰지 않고 설명하는 것이 진짜 지식이다. 이 원리를 소프트웨어로 만든 생각 엔진.",
            "date": "2025-11-23"
        }
    ]

# ==========================================
# 2. UI 디자인 & 헤더
# ==========================================
st.set_page_config(page_title="FeynmanTic Engine", page_icon="🧠", layout="centered")

st.title("🧠 FeynmanTic Engine")
st.caption("Thought Operating System v1.0 (Python Edition)")

st.markdown("---")

# ==========================================
# 3. 입력 엔진 (The Simplifier Input)
# ==========================================
with st.container():
    st.subheader("⚡️ 지식 변환 엔진 가동")
    
    # 입력 폼
    with st.form(key='feynman_form'):
        col1, col2 = st.columns([1, 2])
        
        with col1:
            concept_input = st.text_input(
                "1. 무엇을 공부했나요?", 
                placeholder="예: 양자역학, 마케팅..."
            )
            
        with col2:
            explanation_input = st.text_area(
                "2. 12살 조카에게 설명한다면?",
                placeholder="전문 용어를 빼고, 쉬운 비유를 들어서 설명해주세요.\n(설명이 너무 짧거나 어려우면 엔진이 경고를 보냅니다.)",
                height=100
            )

        # 엔진 피드백 로직 (실시간 느낌)
        feedback_placeholder = st.empty()
        
        # 저장 버튼
        submit_button = st.form_submit_button(label="지식으로 변환 (Save Insight)")

    # 폼 제출 후 검증 로직
    if submit_button:
        if not concept_input:
            st.error("⚠️ 개념(키워드)이 입력되지 않았습니다.")
        elif len(explanation_input) < 20:
            st.warning("🤔 설명이 너무 짧습니다. 진짜 이해했다면 더 쉽게 풀어쓸 수 있습니다.")
        else:
            # 성공 시 저장
            new_thought = {
                "concept": concept_input,
                "explanation": explanation_input,
                "date": datetime.datetime.now().strftime("%Y-%m-%d")
            }
            st.session_state.thoughts.insert(0, new_thought) # 최신순 저장
            
            st.success("✅ 엔진이 정상적으로 지식을 정제했습니다!")
            time.sleep(1) # 잠시 성공 메시지 보여줌
            st.rerun() # 화면 새로고침

# ==========================================
# 4. 대시보드 (저장된 지식 리스트)
# ==========================================
st.markdown("---")
st.subheader("📚 정제된 지식 보관소")

if len(st.session_state.thoughts) == 0:
    st.info("아직 저장된 지식이 없습니다. 위 엔진을 가동해주세요.")
else:
    for i, item in enumerate(st.session_state.thoughts):
        with st.expander(f"📌 {item['concept']} ({item['date']})", expanded=(i==0)):
            st.markdown(f"**설명:**")
            st.info(f"{item['explanation']}")
            
            # 삭제 버튼 (옵션)
            if st.button("삭제", key=f"del_{i}"):
                st.session_state.thoughts.pop(i)
                st.rerun()

