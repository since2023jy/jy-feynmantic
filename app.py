import streamlit as st
import datetime
import time

# ==========================================
# [DATA] 세션 상태 초기화
# ==========================================
if 'thoughts' not in st.session_state:
    st.session_state.thoughts = []

# ==========================================
# [UI] 헤더 및 설정
# ==========================================
st.set_page_config(page_title="FeynmanTic Engine", page_icon="🧠", layout="centered")

st.title("🧠 FeynmanTic Engine v0.5")
st.caption("Step 1: Simplify (Feynman) → Step 2: Falsify (Popper)")
st.markdown("---")

# ==========================================
# [ENGINE] 입력 프로세스 (파인만 + 포퍼)
# ==========================================
with st.container():
    st.subheader("⚡️ 지식 검증 프로세스")
    
    # 탭을 사용하여 단계별 사고 유도
    tab1, tab2 = st.tabs(["Step 1. 파인만 (단순화)", "Step 2. 포퍼 (반증)"])

    # 폼 시작
    with st.form(key='engine_form'):
        
        # [Step 1] 파인만: 개념과 쉬운 설명
        with tab1:
            st.markdown("#### 1. 무엇을 알게 되었나요?")
            concept_input = st.text_input("개념 키워드", placeholder="예: 진화론")
            
            st.markdown("#### 2. 12살에게 설명한다면?")
            explanation_input = st.text_area(
                "설명 입력",
                placeholder="전문 용어 금지. 누구나 알 수 있는 비유를 사용하세요.",
                height=100
            )
            st.info("💡 팁: 설명을 다 적은 후, 위쪽의 'Step 2' 탭을 눌러 검증을 진행하세요.")

        # [Step 2] 포퍼: 반증 시도 (핵심 기능 추가)
        with tab2:
            st.markdown("#### 3. 비판적 사고 (The Popper Filter)")
            st.markdown(
                """
                <div style='background-color: #fff3cd; padding: 10px; border-radius: 5px; border-left: 5px solid #ffc107; color: #856404;'>
                <b>🤖 엔진의 질문:</b> "당신의 설명이 틀릴 수 있는 상황은 언제인가요? 예외는 없나요?"
                </div>
                """, 
                unsafe_allow_html=True
            )
            falsification_input = st.text_area(
                "반례/한계점 입력",
                placeholder="예: '이 이론은 미시세계에서는 적용되지 않는다' 혹은 '특정 조건에서는 결과가 다를 수 있다.'",
                height=80
            )

        # 제출 버튼
        st.markdown("---")
        submit_button = st.form_submit_button(label="🚀 검증된 지식으로 저장")

    # [LOGIC] 엔진 검증 로직
    if submit_button:
        # 1. 파인만 필터
        if not concept_input or len(explanation_input) < 15:
            st.error("⛔️ [Step 1 경고] 설명이 너무 빈약합니다. 더 쉽게 풀어서 써보세요.")
        
        # 2. 포퍼 필터 (새로 추가된 엔진 부품)
        elif len(falsification_input) < 5:
            st.warning("🤔 [Step 2 경고] 비판적 사고가 빠졌습니다. 이 지식의 '한계'나 '예외'를 탭2에서 적어주세요.")
        
        # 3. 통과
        else:
            new_thought = {
                "concept": concept_input,
                "explanation": explanation_input,
                "falsification": falsification_input, # 반증 데이터 저장
                "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            }
            st.session_state.thoughts.insert(0, new_thought)
            
            st.success("✅ 완벽합니다! 단순화와 반증 과정을 모두 통과했습니다.")
            time.sleep(1.5)
            st.rerun()

# ==========================================
# [VIEW] 대시보드 (저장된 지식)
# ==========================================
st.markdown("---")
st.subheader(f"📚 검증된 지식 ({len(st.session_state.thoughts)})")

if not st.session_state.thoughts:
    st.write("아직 검증된 지식이 없습니다.")

for i, item in enumerate(st.session_state.thoughts):
    with st.expander(f"📌 {item['concept']} ({item['date']})", expanded=(i==0)):
        col_a, col_b = st.columns(2)
        with col_a:
            st.caption("✅ 정의 (Feynman)")
            st.info(item['explanation'])
        with col_b:
            st.caption("🛡️ 반례/한계 (Popper)")
            st.warning(item['falsification'])
            
        if st.button("삭제", key=f"del_{i}"):
            st.session_state.thoughts.pop(i)
            st.rerun()
