import streamlit as st
import sqlite3
import datetime
import time

# ==========================================
# [DATABASE] 엔진의 기억장치 (SQLite)
# ==========================================
def init_db():
    """데이터베이스와 테이블을 초기화합니다."""
    conn = sqlite3.connect('feynman.db', check_same_thread=False)
    c = conn.cursor()
    # 테이블 생성: id, 개념, 설명, 반증, 태그, 날짜
    c.execute('''
        CREATE TABLE IF NOT EXISTS thoughts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            concept TEXT NOT NULL,
            explanation TEXT NOT NULL,
            falsification TEXT,
            tags TEXT,
            created_at TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_thought_to_db(concept, explanation, falsification, tags):
    """지식을 영구 저장합니다."""
    conn = sqlite3.connect('feynman.db', check_same_thread=False)
    c = conn.cursor()
    created_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    c.execute('''
        INSERT INTO thoughts (concept, explanation, falsification, tags, created_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (concept, explanation, falsification, tags, created_at))
    conn.commit()
    conn.close()

def get_all_thoughts():
    """저장된 모든 지식을 불러옵니다 (최신순)."""
    conn = sqlite3.connect('feynman.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row # 딕셔너리처럼 접근 가능하게 설정
    c = conn.cursor()
    c.execute('SELECT * FROM thoughts ORDER BY id DESC')
    rows = c.fetchall()
    conn.close()
    return rows

def delete_thought_from_db(thought_id):
    """지식을 삭제합니다."""
    conn = sqlite3.connect('feynman.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('DELETE FROM thoughts WHERE id = ?', (thought_id,))
    conn.commit()
    conn.close()

# 앱 시작 시 DB 초기화 (한 번만 실행됨)
init_db()

# ==========================================
# [UI] 앱 설정 및 헤더
# ==========================================
st.set_page_config(page_title="FeynmanTic Engine", page_icon="🧠", layout="centered")

st.title("🧠 FeynmanTic Engine v1.0")
st.caption("Simplify (Feynman) • Falsify (Popper) • Connect (Deutsch)")
st.markdown("---")

# ==========================================
# [ENGINE] 입력 프로세스
# ==========================================
with st.container():
    st.subheader("⚡️ 지식 생성 엔진")
    
    # 탭 구성: 파이프라인 식 사고 유도
    tab1, tab2, tab3 = st.tabs(["1. 정의(Feynman)", "2. 반증(Popper)", "3. 연결(Deutsch)"])

    with st.form(key='engine_form', clear_on_submit=True):
        
        # [Tab 1] 파인만: 개념 정의
        with tab1:
            st.markdown("#### 🎯 무엇을 알게 되었나요?")
            concept_input = st.text_input("개념 키워드", placeholder="예: 엔트로피")
            
            st.markdown("#### 🗣 12살에게 설명한다면?")
            explanation_input = st.text_area(
                "쉬운 설명",
                placeholder="전문 용어를 쓰지 않고, 비유를 들어서 설명해보세요.",
                height=150
            )

        # [Tab 2] 포퍼: 비판적 사고
        with tab2:
            st.markdown("#### 🛡 내 생각이 틀릴 가능성은?")
            st.markdown(
                "<div style='color: #856404; background-color: #fff3cd; padding: 10px; border-radius: 5px; font-size: 0.9em;'>🤖 이 이론의 한계점이나 예외 상황을 적어야 지식이 단단해집니다.</div>", 
                unsafe_allow_html=True
            )
            falsification_input = st.text_area(
                "반례/한계점",
                placeholder="예: 이 방식은 데이터가 적을 때는 작동하지 않는다.",
                height=100
            )

        # [Tab 3] 도이치: 맥락 연결 (태그)
        with tab3:
            st.markdown("#### 🔗 무엇과 연결되나요?")
            tags_input = st.text_input("태그 (콤마로 구분)", placeholder="예: 물리, 정보이론, 무질서")

        st.markdown("---")
        submit_button = st.form_submit_button(label="🚀 영구 저장 (Save to DB)")

    # [LOGIC] 저장 로직
    if submit_button:
        if not concept_input or len(explanation_input) < 5:
            st.error("⛔️ [거부] 개념과 설명이 너무 빈약합니다. 다시 시도하세요.")
        elif len(falsification_input) < 2:
            st.warning("🤔 [경고] 반증(한계점)을 입력하지 않았습니다. 완벽한 지식이 아닙니다.")
            # 경고를 주지만 저장은 허용 (유연성)
            save_thought_to_db(concept_input, explanation_input, falsification_input, tags_input)
            st.success("⚠️ 반증이 부족하지만 저장되었습니다. 나중에 보완하세요.")
            time.sleep(1)
            st.rerun()
        else:
            # DB 저장 호출
            save_thought_to_db(concept_input, explanation_input, falsification_input, tags_input)
            st.success("✅ 완벽합니다! 엔진이 지식을 DB에 각인했습니다.")
            time.sleep(1)
            st.rerun()

# ==========================================
# [VIEW] 대시보드 (DB 연동)
# ==========================================
st.markdown("---")
st.subheader("📚 지식 저장소 (Database)")

# DB에서 데이터 가져오기
thoughts_data = get_all_thoughts()

if not thoughts_data:
    st.info("📭 저장된 지식이 없습니다. 위 엔진을 가동하여 첫 지식을 만들어보세요.")
else:
    for row in thoughts_data:
        # row는 딕셔너리처럼 사용 가능 (row['concept'], row['explanation']...)
        with st.expander(f"📌 {row['concept']}  |  🏷 {row['tags'] if row['tags'] else 'No Tag'}", expanded=False):
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.caption("✅ Feynman (단순화)")
                st.info(row['explanation'])
                
            with col2:
                st.caption("🛡 Popper (반증/한계)")
                # 데이터가 없거나 비어있을 경우 처리
                fals_text = row['falsification'] if row['falsification'] else "🚫 기록된 반증 없음"
                st.warning(fals_text)
            
            st.caption(f"🕒 작성일: {row['created_at']}")
            
            # 삭제 버튼 (DB 반영)
            if st.button("영구 삭제", key=f"del_{row['id']}"):
                delete_thought_from_db(row['id'])
                st.rerun()
