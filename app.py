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

st.title("🧠 FeynmanTic Engine v0.5.1")
st.caption("Patch: 데이터 호환성 문제 해결됨")
st.markdown("---")

# ==========================================
# [ENGINE] 입력 프로세스 (파인만 + 포퍼)
# ==========================================
with st.container():
    st.subheader("⚡️ 지식 검증 프로세스")
    
    tab1, tab2 = st.tabs(["Step 1. 파인만 (단순화)", "Step 2. 포퍼 (반증)"])

    with st.form(key='engine_form'):
        
        # [Step 1] 파인만
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

        # [Step 2] 포퍼
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

        st.markdown("---")
        submit_button = st.form_submit_button(label="🚀 검증된 지식으로 저장")

    # [LOGIC]
    if submit_button:
        if not concept_input or len(explanation_input) < 5: # 테스트 위해 길이 제한 완화
            st.error("⛔️ [Step 1 경고] 설명이 너무 빈약합니다.")
        elif len(falsification_input) < 2: # 테스트 위해 길이 제한 완화
            st.warning("🤔 [Step 2 경고] 반증(예외상황)을 입력해야 엔진이 승인합니다.")
        else:
            new_thought = {
                "concept": concept_input,
                "explanation": explanation_input,
                "falsification": falsification_input,
                "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            }
            st.session_state.thoughts.insert(0, new_thought)
            
            st.success("✅ 완벽합니다! 단순화와 반증 과정을 모두 통과했습니다.")
            time.sleep(1)
            st.rerun()

# ==========================================
# [VIEW] 대시보드 (수정된 부분)
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
            # [FIX] 여기서 에러가 났었습니다. .get()을 사용하여 데이터가 없으면 기본 문구를 띄웁니다.
            falsification_text = item.get('falsification', '🚫 이전 버전 데이터라 반증 내용이 없습니다.')
            st.warning(falsification_text)
            
        if st.button("삭제", key=f"del_{i}"):
            st.session_state.thoughts.pop(i)
            st.rerun()
