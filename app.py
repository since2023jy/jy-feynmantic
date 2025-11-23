import streamlit as st
import sqlite3
import datetime
import time
import pandas as pd

# ==========================================
# [DATABASE] 뇌관 (Logic Core)
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

def calculate_streak(df):
    if df.empty: return 0
    df['date'] = pd.to_datetime(df['created_at']).dt.date
    unique_dates = sorted(df['date'].unique(), reverse=True)
    if not unique_dates: return 0
    today = datetime.date.today()
    streak = 0
    if unique_dates[0] == today:
        streak = 1
        check_date = today - datetime.timedelta(days=1)
        idx = 1
    else:
        if unique_dates[0] == today - datetime.timedelta(days=1):
            check_date = today - datetime.timedelta(days=1)
            idx = 0
        else: return 0
    while idx < len(unique_dates):
        if unique_dates[idx] == check_date:
            streak += 1
            check_date -= datetime.timedelta(days=1)
            idx += 1
        else: break
    return streak

init_db()

# ==========================================
# [UI] Dashboard
# ==========================================
st.set_page_config(page_title="FeynmanTic OS", page_icon="🧠", layout="wide")

df = get_all_thoughts()
streak_count = calculate_streak(df)
total_thoughts = len(df)
today_count = len(df[pd.to_datetime(df['created_at']).dt.date == datetime.date.today()]) if not df.empty else 0

with st.sidebar:
    st.title("FeynmanTic")
    st.metric(label="🔥 Streak", value=f"{streak_count} Days")
    st.metric(label="Total Nodes", value=f"{total_thoughts}")
    st.markdown("---")
    st.info("Input -> Process -> Network")

st.title("🧠 FeynmanTic OS v1.9")
st.caption("No-Install Edition: Knowledge Graph Active")

col1, col2 = st.columns([2, 1])
with col1:
    st.markdown(f"### ⚡️ Today's Output: **{today_count}** Insights")
with col2:
    if not df.empty and 'falsification' in df.columns:
        valid_fals = df['falsification'].apply(lambda x: len(str(x)) > 5).sum()
        ratio = int((valid_fals / total_thoughts) * 100)
    else: ratio = 0
    st.markdown(f"### 🛡 Critical Rate: **{ratio}%**")

st.markdown("---")

# ==========================================
# [VISUALIZATION] Native Graph (DOT String)
# ==========================================
if not df.empty:
    with st.expander("🕸 지식 네트워크 지도 (Knowledge Graph)", expanded=True):
        
        # 1. DOT 언어로 그래프 정의 시작
        dot_source = """
        digraph {
            rankdir="LR";
            bgcolor="transparent";
            node [shape="box", style="filled", fillcolor="#f0f2f6", fontname="Helvetica"];
            edge [color="#bdc3c7"];
        """
        
        # 2. 데이터를 순회하며 노드와 엣지(연결선) 텍스트 생성
        for index, row in df.iterrows():
            concept = row['concept'].replace('"', "'") # 에러 방지용 따옴표 처리
            
            # 개념 노드 (파란색)
            dot_source += f'    "{concept}" [style="filled", fillcolor="#d4e6f1", color="#3498db", penwidth="2"];\n'
            
            # 태그 연결
            if row['tags']:
                tags = [t.strip() for t in row['tags'].split(',')]
                for tag in tags:
                    if tag:
                        tag_clean = tag.replace('"', "'")
                        # 태그 노드 (타원형) 및 연결
                        dot_source += f'    "{tag_clean}" [shape="ellipse", style="filled", fillcolor="#eaecee", color="#95a5a6"];\n'
                        dot_source += f'    "{concept}" -> "{tag_clean}";\n'

        # 3. 그래프 닫기
        dot_source += "}"
        
        # 4. Streamlit 내장 함수로 렌더링 (라이브러리 불필요)
        st.graphviz_chart(dot_source, use_container_width=True)
        st.caption("💡 개념(Blue)과 태그(Grey)가 어떻게 연결되는지 보여줍니다.")

# ==========================================
# [ENGINE] Input Form
# ==========================================
with st.container():
    st.subheader("🚀 Engine Input")
    tab1, tab2, tab3 = st.tabs(["1. Feynman", "2. Popper", "3. Deutsch"])
    
    with st.form(key='engine_form', clear_on_submit=True):
        with tab1:
            c_in = st.text_input("Concept", placeholder="핵심 개념")
            e_in = st.text_area("Redefinition", placeholder="쉬운 설명", height=80)
        with tab2:
            f_in = st.text_area("Falsification", placeholder="반증/한계", height=80)
        with tab3:
            t_in = st.text_input("Tags", placeholder="연결 고리 (콤마 구분)")
            
        if st.form_submit_button("Save to Grid"):
            if not c_in: st.error("개념을 입력하세요.")
            else:
                save_thought_to_db(c_in, e_in, f_in, t_in)
                st.success("Network Updated.")
                time.sleep(0.5)
                st.rerun()

# ==========================================
# [ARCHIVE] List View
# ==========================================
st.markdown("---")
with st.expander("📂 Raw Data Archive"):
    if not df.empty:
        for index, row in df.iterrows():
            col_a, col_b = st.columns([5, 1])
            with col_a:
                st.markdown(f"**{row['concept']}** ({row['created_at']})")
                st.caption(f"{row['explanation'][:50]}... | Tags: {row['tags']}")
            with col_b:
                if st.button("Del", key=f"del_{row['id']}"):
                    delete_thought_from_db(row['id'])
                    st.rerun()
