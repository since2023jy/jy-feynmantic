import streamlit as st
import sqlite3
import datetime
import time
import pandas as pd

# ==========================================
# [DATABASE & LOGIC] 뇌관(Logic Core)
# ==========================================
def init_db():
    conn = sqlite3.connect('feynman.db', check_same_thread=False)
    c = conn.cursor()
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
    conn = sqlite3.connect('feynman.db', check_same_thread=False)
    c = conn.cursor()
    created_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute('''
        INSERT INTO thoughts (concept, explanation, falsification, tags, created_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (concept, explanation, falsification, tags, created_at))
    conn.commit()
    conn.close()

def get_all_thoughts():
    conn = sqlite3.connect('feynman.db', check_same_thread=False)
    query = "SELECT * FROM thoughts ORDER BY id DESC"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def delete_thought_from_db(thought_id):
    conn = sqlite3.connect('feynman.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('DELETE FROM thoughts WHERE id = ?', (thought_id,))
    conn.commit()
    conn.close()

# 스트릭(연속 학습일) 계산 로직 (듀오링고 스타일)
def calculate_streak(df):
    if df.empty:
        return 0
    
    # 날짜 데이터만 추출 (시간 제외)
    df['date'] = pd.to_datetime(df['created_at']).dt.date
    unique_dates = sorted(df['date'].unique(), reverse=True)
    
    if not unique_dates:
        return 0
        
    today = datetime.date.today()
    streak = 0
    
    # 오늘 공부했는지 확인
    if unique_dates[0] == today:
        streak = 1
        check_date = today - datetime.timedelta(days=1)
        idx = 1
    else:
        # 오늘은 안 했지만 어제 했는지 확인
        if unique_dates[0] == today - datetime.timedelta(days=1):
            streak = 0 # 오늘 안했으면 일단 0으로 보이고, 어제부터 카운트 하거나.. 
            # 로직 수정: 연속일수만 중요하므로 어제 했으면 스트릭 유지
            check_date = today - datetime.timedelta(days=1)
            idx = 0
        else:
            return 0 # 어제도 안했으면 스트릭 깨짐

    while idx < len(unique_dates):
        if unique_dates[idx] == check_date:
            streak += 1
            check_date -= datetime.timedelta(days=1)
            idx += 1
        else:
            break
            
    return streak

init_db()

# ==========================================
# [UI] 팔란티어 스타일 대시보드
# ==========================================
st.set_page_config(page_title="FeynmanTic OS", page_icon="🧠", layout="wide")

# 데이터 로딩
df = get_all_thoughts()
streak_count = calculate_streak(df)
total_thoughts = len(df)
today_count = len(df[pd.to_datetime(df['created_at']).dt.date == datetime.date.today()]) if not df.empty else 0

# [SIDEBAR] 프로필 & 상태창
with st.sidebar:
    st.header(f"🔥 Streak: {streak_count}일")
    if streak_count > 0:
        st.success("뇌가 뜨겁게 가동 중입니다!")
    else:
        st.warning("엔진이 식었습니다. 재가동하세요.")
    
    st.metric(label="총 축적된 지식", value=f"{total_thoughts}개", delta=f"+{today_count} 오늘")
    st.markdown("---")
    st.markdown("**Core Philosophy**")
    st.caption("1. Feynman (Simplify)\n2. Popper (Falsify)\n3. Deutsch (Connect)")

# [MAIN] 헤더
st.title("🧠 FeynmanTic OS")
st.caption("Intelligence Augmentation System v1.5")

# [DASHBOARD] 상단 메트릭 (팔란티어 느낌)
col1, col2, col3 = st.columns(3)
with col1:
    st.info(f"⚡️ **오늘의 엔진 출력**: {today_count}건")
with col2:
    # 반증 비율 계산 (데이터가 있는 경우만)
    if not df.empty and 'falsification' in df.columns:
        valid_fals = df['falsification'].apply(lambda x: len(str(x)) > 5).sum()
        ratio = int((valid_fals / total_thoughts) * 100)
    else:
        ratio = 0
    st.warning(f"🛡 **비판적 사고율**: {ratio}%")
with col3:
    # 태그 분석
    if not df.empty and 'tags' in df.columns:
        all_tags = ','.join(df['tags'].dropna()).split(',')
        clean_tags = [t.strip() for t in all_tags if t.strip()]
        top_tag = max(set(clean_tags), key=clean_tags.count) if clean_tags else "없음"
    else:
        top_tag = "데이터 부족"
    st.success(f"🔗 **주요 관심사**: #{top_tag}")

st.markdown("---")

# ==========================================
# [ENGINE] 입력 섹션 (3-Step Pipeline)
# ==========================================
with st.expander("🚀 새로운 지식 입력 엔진 가동 (Click to Open)", expanded=True):
    tab1, tab2, tab3 = st.tabs(["1. 정의(Feynman)", "2. 반증(Popper)", "3. 연결(Deutsch)"])

    with st.form(key='engine_form', clear_on_submit=True):
        with tab1:
            c_in = st.text_input("개념 (Concept)", placeholder="무엇을 배웠습니까?")
            e_in = st.text_area("재정의 (Redefinition)", placeholder="12살에게 설명하듯 쉽게.", height=100)
        with tab2:
            f_in = st.text_area("반증 (Falsification)", placeholder="이 지식이 틀릴 수 있는 조건은?", height=100)
        with tab3:
            t_in = st.text_input("태그 (Tags)", placeholder="예: #경제, #심리 (콤마 구분)")

        submitted = st.form_submit_button("SYSTEM SAVE")
        
        if submitted:
            if not c_in or len(e_in) < 5:
                st.error("입력 데이터 불충분: 개념과 설명은 필수입니다.")
            else:
                save_thought_to_db(c_in, e_in, f_in, t_in)
                st.toast("✅ 지식이 시스템에 통합되었습니다!", icon="💾")
                time.sleep(1)
                st.rerun()

# ==========================================
# [VIEW] 지식 매트릭스 (Table View)
# ==========================================
st.subheader("📂 Intelligence Archive")

if not df.empty:
    # 데이터프레임 가공 (보기 좋게)
    display_df = df[['concept', 'explanation', 'falsification', 'tags', 'created_at']].copy()
    display_df.columns = ['개념', '파인만 설명', '포퍼 반증', '태그', '생성일']
    
    # 인터랙티브 테이블 (정렬/검색 가능)
    st.dataframe(
        display_df, 
        use_container_width=True,
        hide_index=True,
        column_config={
            "생성일": st.column_config.DatetimeColumn(format="YYYY-MM-DD HH:mm"),
        }
    )

    # 개별 카드 뷰 (삭제 기능 포함)
    with st.expander("🗑 데이터 관리 (삭제 모드)"):
        for index, row in df.iterrows():
            col_a, col_b = st.columns([4, 1])
            with col_a:
                st.text(f"{row['created_at']} | {row['concept']}")
            with col_b:
                if st.button("삭제", key=f"del_{row['id']}"):
                    delete_thought_from_db(row['id'])
                    st.rerun()
else:
    st.info("데이터베이스가 비어있습니다. 엔진을 가동하십시오.")
