import streamlit as st
import sqlite3
import datetime
import pandas as pd
import streamlit.components.v1 as components
import json
import urllib.request
import time
import xml.etree.ElementTree as ET # 👈 [NEW] 뉴스 파싱을 위한 내장 라이브러리

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
# [NEWS SCRAPER] 설치 필요 없는 구글 뉴스 파서
# ==========================================
@st.cache_data(ttl=3600) # 1시간마다 갱신
def get_google_news_kr():
    """
    구글 뉴스 RSS(한국)를 긁어와서 최신 헤드라인 5개를 반환합니다.
    No Install Required (xml.etree 사용)
    """
    url = "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko"
    try:
        with urllib.request.urlopen(url) as response:
            xml_data = response.read()
            root = ET.fromstring(xml_data)
            
            news_items = []
            # item 태그 안의 title 추출
            for item in root.findall('.//item')[:5]:
                title = item.find('title').text
                # 매체명 제거 (예: "제목 - 조선일보" -> "제목")
                if ' - ' in title:
                    title = title.split(' - ')[0]
                news_items.append(title)
            return news_items
    except Exception:
        return ["뉴스 로딩 실패: 직접 주제를 입력하세요."]

# ==========================================
# [AI BRAIN] Gemini API
# ==========================================
def call_gemini_step(api_key, concept, step_type):
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
# [STATE MANAGEMENT]
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
st.set_page_config(page_title="FeynmanTic News", page_icon="📰", layout="wide")
df = get_all_thoughts()

with st.sidebar:
    st.title("📰 News Injection")
    google_api_key = st.text_input("Google API Key", type="password", placeholder="AI Studio Key")
    if not google_api_key:
        st.info("AI 힌트 기능은 키가 필요합니다.")
        st.markdown("[👉 키 발급받기](https://aistudio.google.com/app/apikey)")
    
    st.markdown("---")
    st.write(f"**Total Insights:** {len(df)}")
    
    # Progress
    progress = (st.session_state.step - 1) / 4
    st.progress(progress)
    st.caption(f"Current Level: Step {st.session_state.step}")

# ==========================================
# [MAIN] Wizard UI
# ==========================================
st.title("🧠 FeynmanTic v5.0")

# --- STEP 1: 뉴스 스크랩 & 개념 선정 ---
if st.session_state.step == 1:
    st.header("🎯 오늘의 연료 (Today's Fuel)")
    
    col_news, col_manual = st.columns([1, 1])
    
    # [왼쪽] 뉴스 피드 (자동 추천)
    with col_news:
        st.subheader("🔥 실시간 트렌드 (Click to Start)")
        news_list = get_google_news_kr()
        
        for news in news_list:
            # 뉴스 버튼 클릭 시 바로 주제 선정됨
            if st.button(f"🗞 {news}", key=news, use_container_width=True):
                st.session_state.w_concept = news
                next_step()
                st.rerun()
        st.caption("Google News RSS 기반 실시간 데이터")

    # [오른쪽] 수동 입력
    with col_manual:
        st.subheader("✍️ 직접 입력")
        st.write("혹은, 지금 머릿속에 있는 주제를 적으세요.")
        manual_input = st.text_input("주제 입력", value=st.session_state.w_concept, placeholder="예: 도파민 중독")
        
        if st.button("엔진 가동 ➡️", type="primary", use_container_width=True):
            if manual_input:
                st.session_state.w_concept = manual_input
                next_step()
                st.rerun()
            else:
                st.warning("주제를 입력하거나 왼쪽 뉴스를 클릭하세요.")

# --- STEP 2: 파인만 (설명) ---
elif st.session_state.step == 2:
    st.header(f"🗣 '{st.session_state.w_concept}' 재정의하기")
    st.info("12살 아이에게 설명할 수 없다면, 이해한 것이 아닙니다.")
    
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("✨ AI 힌트"):
            if google_api_key:
                with st.spinner("AI Thinking..."):
                    hint = call_gemini_step(google_api_key, st.session_state.w_concept, "feynman")
                    st.session_state.w_expl = hint
                    st.rerun()
            else: st.error("API Key 필요")

    with col1:
        st.session_state.w_expl = st.text_area("쉽게 설명해보기", value=st.session_state.w_expl, height=150)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("⬅️ Back"): prev_step(); st.rerun()
    with c2:
        if st.button("Next: 검증하기 ➡️", type="primary"):
            if len(st.session_state.w_expl) > 5: next_step(); st.rerun()
            else: st.warning("설명이 너무 짧습니다.")

# --- STEP 3: 포퍼 (반증) ---
elif st.session_state.step == 3:
    st.header("🛡 비판적 사고 (Popper's Razor)")
    st.warning("이 지식이 틀릴 수 있는 상황이나 한계점은 무엇입니까?")
    
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("✨ AI 공격"):
            if google_api_key:
                with st.spinner("AI Attacking..."):
                    hint = call_gemini_step(google_api_key, st.session_state.w_concept, "popper")
                    st.session_state.w_fals = hint
                    st.rerun()
            else: st.error("API Key 필요")

    with col1:
        st.session_state.w_fals = st.text_area("한계/반론 입력", value=st.session_state.w_fals, height=150)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("⬅️ Back"): prev_step(); st.rerun()
    with c2:
        if st.button("Next: 연결하기 ➡️", type="primary"): next_step(); st.rerun()

# --- STEP 4: 도이치 (연결 & 저장) ---
elif st.session_state.step == 4:
    st.header("🔗 지식 네트워크 통합")
    st.success("이 지식을 기존의 어떤 개념들과 연결하시겠습니까?")
    
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
        if st.button("🎉 시스템 저장 (Commit)", type="primary"):
            save_thought_to_db(
                st.session_state.w_concept,
                st.session_state.w_expl,
                st.session_state.w_fals,
                st.session_state.w_tags
            )
            st.balloons()
            time.sleep(1.5)
            reset_wizard()
            st.rerun()

# ==========================================
# [VISUALIZATION]
# ==========================================
st.markdown("---")
with st.expander("🕸 Knowledge Graph (Physics Enabled)", expanded=True):
    if df.empty:
        st.write("데이터가 없습니다.")
    else:
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

with st.expander("📂 Archive"):
    for _, row in df.iterrows():
        c1, c2 = st.columns([5,1])
        c1.write(f"**{row['concept']}**: {row['explanation'][:30]}...")
        if c2.button("Del", key=f"d_{row['id']}"):
            delete_thought_from_db(row['id']); st.rerun()
