import streamlit as st
import sqlite3
import datetime
import pandas as pd
import streamlit.components.v1 as components
import json
import urllib.request
import time

# ==========================================
# [DATABASE]
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

init_db()

# ==========================================
# [AI BRAIN] Gemini API (No-Install)
# ==========================================
def call_gemini_step(api_key, concept, step_type):
    """
    단계별로 필요한 도움만 줍니다. (토큰 절약 + 집중력 향상)
    """
    if not api_key: return "키 없음"

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    if step_type == "feynman":
        prompt = f"개념 '{concept}'을 12살 아이에게 설명하듯 쉬운 비유를 들어 3문장으로 설명해줘. (한국어)"
    elif step_type == "popper":
        prompt = f"개념 '{concept}'의 한계점, 반론, 혹은 예외 상황을 날카롭게 2문장으로 지적해줘. (한국어)"
    elif step_type == "tags":
        prompt = f"개념 '{concept}'과 연관된 핵심 키워드 3개만 쉼표(,)로 구분해서 적어줘."
    
    data = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req) as response:
            res_json = json.loads(response.read().decode('utf-8'))
            return res_json['candidates'][0]['content']['parts'][0]['text'].strip()
    except Exception as e:
        return f"AI 에러: {str(e)}"

# ==========================================
# [STATE MANAGEMENT] 위저드 상태 관리
# ==========================================
if 'step' not in st.session_state: st.session_state.step = 1
if 'w_concept' not in st.session_state: st.session_state.w_concept = ""
if 'w_expl' not in st.session_state: st.session_state.w_expl = ""
if 'w_fals' not in st.session_state: st.session_state.w_fals = ""
if 'w_tags' not in st.session_state: st.session_state.w_tags = ""

def next_step(): st.session_state.step += 1
def prev_step(): st.session_state.step -= 1
def reset_wizard():
    st.session_state.step = 1
    st.session_state.w_concept = ""
    st.session_state.w_expl = ""
    st.session_state.w_fals = ""
    st.session_state.w_tags = ""

# ==========================================
# [UI] Setup
# ==========================================
st.set_page_config(page_title="FeynmanTic Flow", page_icon="🌊", layout="wide")
df = get_all_thoughts()

with st.sidebar:
    st.title("🌊 Flow Mode")
    google_api_key = st.text_input("Google API Key", type="password", placeholder="AI Studio Key")
    if not google_api_key:
        st.info("AI 기능을 쓰려면 키를 입력하세요.")
        st.markdown("[👉 키 발급받기](https://aistudio.google.com/app/apikey)")
    
    st.markdown("---")
    st.write(f"**Total Insights:** {len(df)}")
    
    # 미니맵 (진행도 표시)
    st.write("### 🚀 Progress")
    progress = (st.session_state.step - 1) / 4
    st.progress(progress)
    if st.session_state.step == 1: st.caption("Step 1: Concept (Ready)")
    elif st.session_state.step == 2: st.caption("Step 2: Feynman (Simplicity)")
    elif st.session_state.step == 3: st.caption("Step 3: Popper (Critical)")
    elif st.session_state.step >= 4: st.caption("Step 4: Deutsch (Connection)")

# ==========================================
# [MAIN] Wizard UI (단계별 몰입 화면)
# ==========================================
st.title("🧠 FeynmanTic Flow")

# --- STEP 1: 개념 정의 ---
if st.session_state.step == 1:
    st.header("🎯 무엇을 파헤쳐 볼까요?")
    st.write("공부하고 싶은 주제나 개념을 입력하세요. 여행의 시작입니다.")
    
    st.session_state.w_concept = st.text_input("주제 입력", value=st.session_state.w_concept, placeholder="예: 양자 얽힘", key="input_step1")
    
    if st.button("Next: 파인만 레이어 돌파 ➡️", type="primary"):
        if st.session_state.w_concept:
            next_step()
            st.rerun()
        else:
            st.warning("주제를 입력해주세요!")

# --- STEP 2: 파인만 (설명) ---
elif st.session_state.step == 2:
    st.header(f"🗣 '{st.session_state.w_concept}' 재정의하기")
    st.info("파인만 기법: 12살 아이에게 설명할 수 없다면, 이해한 것이 아닙니다.")
    
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("✨ AI 힌트 받기"):
            if google_api_key:
                with st.spinner("비유를 찾는 중..."):
                    hint = call_gemini_step(google_api_key, st.session_state.w_concept, "feynman")
                    st.session_state.w_expl = hint
                    st.rerun()
            else:
                st.error("API 키가 필요합니다.")

    with col1:
        st.session_state.w_expl = st.text_area("쉽게 설명해보기", value=st.session_state.w_expl, height=150)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("⬅️ Back"): prev_step(); st.rerun()
    with c2:
        if st.button("Next: 포퍼 레이어 돌파 ➡️", type="primary"):
            if len(st.session_state.w_expl) > 5:
                next_step()
                st.rerun()
            else:
                st.warning("설명이 너무 짧아요. 조금 더 적어보세요.")

# --- STEP 3: 포퍼 (반증) ---
elif st.session_state.step == 3:
    st.header("🛡 내 생각이 틀릴 수 있을까?")
    st.warning("포퍼의 반증주의: 반대되는 사례를 찾을 수 있어야 진짜 과학입니다.")
    
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("✨ AI 공격 받기"):
            if google_api_key:
                with st.spinner("허점을 찾는 중..."):
                    hint = call_gemini_step(google_api_key, st.session_state.w_concept, "popper")
                    st.session_state.w_fals = hint
                    st.rerun()
            else: st.error("키 필요")

    with col1:
        st.session_state.w_fals = st.text_area("한계점/반론 적어보기", value=st.session_state.w_fals, height=150)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("⬅️ Back"): prev_step(); st.rerun()
    with c2:
        if st.button("Next: 지식 연결하기 ➡️", type="primary"):
            next_step()
            st.rerun()

# --- STEP 4: 도이치 (연결 & 완료) ---
elif st.session_state.step == 4:
    st.header("🔗 지식의 네트워크 연결")
    st.success("마지막 단계입니다! 이 지식을 어디에 연결할까요?")
    
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("✨ 태그 추천"):
            if google_api_key:
                hint = call_gemini_step(google_api_key, st.session_state.w_concept, "tags")
                st.session_state.w_tags = hint
                st.rerun()

    with col1:
        st.session_state.w_tags = st.text_input("태그 (콤마로 구분)", value=st.session_state.w_tags)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("⬅️ Back"): prev_step(); st.rerun()
    with c2:
        if st.button("🎉 최종 저장 (Finish)", type="primary"):
            save_thought_to_db(
                st.session_state.w_concept,
                st.session_state.w_expl,
                st.session_state.w_fals,
                st.session_state.w_tags
            )
            st.balloons() # 축하 효과
            time.sleep(2)
            reset_wizard()
            st.rerun()

# ==========================================
# [VISUALIZATION] 하단 그래프
# ==========================================
st.markdown("---")
with st.expander("🕸 나의 뇌지도 (Knowledge Graph)", expanded=True):
    if df.empty:
        st.write("아직 데이터가 없습니다.")
    else:
        # 간단한 그래프 렌더링
        nodes = []
        edges = []
        existing = set()
        for _, row in df.iterrows():
            c = row['concept']
            if c not in existing:
                nodes.append(f"{{id: '{c}', label: '{c}', group: 'concept'}}")
                existing.add(c)
            if row['tags']:
                for t in row['tags'].split(','):
                    t = t.strip()
                    if t:
                        if t not in existing:
                            nodes.append(f"{{id: '{t}', label: '{t}', group: 'tag'}}")
                            existing.add(t)
                        edges.append(f"{{from: '{c}', to: '{t}'}}")

        html = f"""
        <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
        <div id="mynetwork" style="height:400px; background:white; border:1px solid #eee;"></div>
        <script>
          var data = {{
            nodes: new vis.DataSet([{','.join(nodes)}]),
            edges: new vis.DataSet([{','.join(edges)}])
          }};
          var options = {{
            nodes: {{ shape: 'dot', size: 20, font: {{ size: 14 }} }},
            groups: {{ concept: {{ color: '#3498db' }}, tag: {{ color: '#bdc3c7', shape: 'ellipse' }} }},
            physics: {{ stabilization: false, solver: 'forceAtlas2Based' }}
          }};
          new vis.Network(document.getElementById('mynetwork'), data, options);
        </script>
        """
        components.html(html, height=420)

# [ARCHIVE]
with st.expander("📂 지식 보관함"):
    for _, row in df.iterrows():
        c1, c2 = st.columns([5,1])
        c1.write(f"**{row['concept']}**: {row['explanation'][:30]}...")
        if c2.button("Del", key=f"d_{row['id']}"):
            delete_thought_from_db(row['id']); st.rerun()
