import streamlit as st
import sqlite3
import datetime
import pandas as pd
import streamlit.components.v1 as components
import json
import urllib.request
import urllib.error
import time
import xml.etree.ElementTree as ET
import random

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
# [AI LOGIC]
# ==========================================
@st.cache_data(ttl=3600)
def get_google_news_kr():
    url = "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko"
    try:
        with urllib.request.urlopen(url) as response:
            xml_data = response.read()
            root = ET.fromstring(xml_data)
            news_items = []
            for item in root.findall('.//item')[:10]: # 10개로 늘림
                title = item.find('title').text
                if ' - ' in title: title = title.split(' - ')[0]
                news_items.append(title)
            return news_items
    except: return ["인공지능", "양자역학", "경제 위기", "기후 변화"]

def call_gemini_brain(api_key, prompt):
    if not api_key: return "API Key 없음"
    models = ["gemini-1.5-flash", "gemini-pro", "gemini-1.0-pro"]
    data = {"contents": [{"parts": [{"text": prompt}]}]}
    encoded_data = json.dumps(data).encode('utf-8')
    headers = {'Content-Type': 'application/json'}
    
    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        try:
            req = urllib.request.Request(url, data=encoded_data, headers=headers)
            with urllib.request.urlopen(req) as response:
                res_json = json.loads(response.read().decode('utf-8'))
                return res_json['candidates'][0]['content']['parts'][0]['text'].strip()
        except: continue
    return "AI 연결 실패"

def auto_think_process(api_key, concept):
    """
    관전 모드용: 한 번에 파인만-포퍼-도이치를 수행하여 결과 반환
    """
    # 1. 파인만 (설명)
    expl = call_gemini_brain(api_key, f"개념 '{concept}'을 12살 아이에게 설명하듯 쉬운 비유를 들어 2문장으로 설명해줘. (한국어)")
    # 2. 포퍼 (반증)
    fals = call_gemini_brain(api_key, f"개념 '{concept}'의 치명적인 한계점이나 예외 상황 1가지만 짧게 지적해줘.")
    # 3. 도이치 (태그)
    tags = call_gemini_brain(api_key, f"개념 '{concept}' 관련 핵심 태그 2개만 쉼표로 구분해줘.")
    
    return expl, fals, tags

# ==========================================
# [STATE]
# ==========================================
if 'step' not in st.session_state: st.session_state.step = 1
# 위저드 상태들...
for key in ['w_concept', 'w_briefing', 'w_expl', 'w_fals', 'w_tags', 'exam_score', 'exam_feedback', 'broker_result']:
    if key not in st.session_state: st.session_state[key] = ""

def next_step(): st.session_state.step += 1
def prev_step(): st.session_state.step -= 1
def reset_wizard():
    st.session_state.step = 1
    for key in ['w_concept', 'w_briefing', 'w_expl', 'w_fals', 'w_tags', 'exam_score', 'exam_feedback', 'broker_result']:
        st.session_state[key] = ""

# ==========================================
# [UI SETUP]
# ==========================================
st.set_page_config(page_title="FeynmanTic Spectator", page_icon="👁️", layout="wide")
df = get_all_thoughts()

# 사이드바
with st.sidebar:
    st.title("👁️ Control Tower")
    google_api_key = st.text_input("Google API Key", type="password", placeholder="AI Studio Key")
    
    st.markdown("---")
    
    # [NEW] 관전 모드 토글
    spectator_mode = st.toggle("👁️ 관전 모드 (Auto-Play)", value=False)
    
    if spectator_mode and not google_api_key:
        st.error("관전 모드는 AI 키가 필요합니다.")
    
    st.markdown("---")
    st.metric("Total Insights", len(df))
    st.caption("FeynmanTic v10.0 God Mode")

# ==========================================
# [SPECTATOR MODE LOGIC]
# ==========================================
if spectator_mode and google_api_key:
    st.title("🌌 The Spectator Mode")
    st.info("엔진이 스스로 지식을 탐식하고 확장하는 중입니다... (자동 실행 중)")
    
    # 1. 주제 선정 (랜덤)
    status_text = st.empty()
    status_text.markdown("### 📡 1. 뉴스 데이터 스캔 중...")
    
    news_pool = get_google_news_kr()
    target_concept = random.choice(news_pool)
    
    # 중복 방지 (이미 있는 건 패스하려 노력)
    existing_concepts = df['concept'].tolist() if not df.empty else []
    if target_concept in existing_concepts:
        target_concept = f"{target_concept} (심화)"
    
    time.sleep(1)
    status_text.markdown(f"### 🎯 2. 목표 포착: **{target_concept}**")
    
    # 2. AI 사고 과정 시각화
    col1, col2, col3 = st.columns(3)
    with col1:
        st.caption("🗣 Feynman (Simplicity)")
        f_box = st.empty()
        f_box.info("Thinking...")
    with col2:
        st.caption("🛡 Popper (Falsification)")
        p_box = st.empty()
        p_box.info("Waiting...")
    with col3:
        st.caption("🔗 Deutsch (Connection)")
        d_box = st.empty()
        d_box.info("Waiting...")
        
    # 실제 AI 호출
    expl, fals, tags = auto_think_process(google_api_key, target_concept)
    
    # 결과 순차적 표시 (애니메이션 효과)
    time.sleep(1)
    f_box.success(expl)
    time.sleep(1)
    p_box.warning(fals)
    time.sleep(1)
    d_box.success(f"#{tags}")
    
    status_text.markdown(f"### 💾 3. 지식 저장소 동기화 중...")
    save_thought_to_db(target_concept, expl, fals, tags)
    
    time.sleep(2)
    st.rerun() # 무한 루프 (새로고침)

# ==========================================
# [MANUAL MODE] (관전 모드가 꺼져있을 때)
# ==========================================
elif not spectator_mode:
    st.title("🧠 FeynmanTic v10.0")
    
    # Wizard UI (기존 수동 모드)
    # --- STEP 1 ---
    if st.session_state.step == 1:
        st.header("Step 1. 주제 선정")
        c1, c2 = st.columns(2)
        with c1:
            st.caption("News Feed")
            for news in get_google_news_kr()[:4]:
                if st.button(f"👉 {news}", key=news):
                    st.session_state.w_concept = news
                    next_step(); st.rerun()
        with c2:
            st.caption("Manual Input")
            m = st.text_input("주제")
            if st.button("Start"):
                st.session_state.w_concept = m
                next_step(); st.rerun()

    # --- STEP 2 (Briefing) ---
    elif st.session_state.step == 2:
        st.header(f"Step 2. 학습: {st.session_state.w_concept}")
        if not st.session_state.w_briefing and google_api_key:
            with st.spinner("AI Briefing..."):
                st.session_state.w_briefing = call_gemini_brain(google_api_key, f"'{st.session_state.w_concept}' 핵심 요약 3줄")
                st.rerun()
        st.info(st.session_state.w_briefing)
        if st.button("Next"): next_step(); st.rerun()

    # --- STEP 3 (Feynman) ---
    elif st.session_state.step == 3:
        st.header("Step 3. 설명")
        c1, c2 = st.columns(2)
        a = c1.text_input("비유 (A는 B다)", placeholder="예: API는 웨이터다")
        r = c2.text_input("이유 (왜냐하면)", placeholder="주문을 전달하니까")
        if a and r:
            curr = f"**{st.session_state.w_concept}**은(는) **{a}**와 같다. 왜냐하면 **{r}** 때문이다."
            st.write(curr.replace("**",""))
            if st.button("AI 검사"):
                if google_api_key:
                    res = call_gemini_brain(google_api_key, f"설명 평가: {curr}. 점수(0-100)와 피드백 1줄 줘.")
                    st.session_state.exam_feedback = res
                    st.rerun()
            if st.session_state.exam_feedback:
                st.caption(st.session_state.exam_feedback)
                if st.button("Pass"): st.session_state.w_expl=curr.replace("**",""); next_step(); st.rerun()

    # --- STEP 4 (Popper) ---
    elif st.session_state.step == 4:
        st.header("Step 4. 반증")
        q = st.text_input("예외 상황은?")
        if st.button("Next"): st.session_state.w_fals=q; next_step(); st.rerun()

    # --- STEP 5 (Save) ---
    elif st.session_state.step == 5:
        st.header("Step 5. 저장")
        t = st.text_input("태그")
        if st.button("Save"):
            save_thought_to_db(st.session_state.w_concept, st.session_state.w_expl, st.session_state.w_fals, t)
            st.balloons(); reset_wizard(); st.rerun()

# ==========================================
# [GRAPH VISUALIZATION] (Always Visible)
# ==========================================
st.markdown("---")
with st.expander("🕸 Living Knowledge Universe", expanded=True):
    if not df.empty:
        nodes, edges, exist = [], [], set()
        for _, r in df.iterrows():
            if r['concept'] not in exist:
                nodes.append(f"{{id:'{r['concept']}', label:'{r['concept']}', group:'concept'}}")
                exist.add(r['concept'])
            if r['tags']:
                for tg in r['tags'].split(','):
                    tg = tg.strip()
                    if tg and tg not in exist:
                        nodes.append(f"{{id:'{tg}', label:'{tg}', group:'tag'}}")
                        exist.add(tg)
                    edges.append(f"{{from:'{r['concept']}', to:'{tg}'}}")
        
        # 그래프 높이를 좀 더 키우고, 물리 엔진 설정을 부드럽게 조정
        html = f"""<script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
        <div id="mynetwork" style="height:500px; border:1px solid #eee; background-color: #f8f9fa;"></div>
        <script>
        var container = document.getElementById('mynetwork');
        var data = {{nodes: new vis.DataSet([{','.join(nodes)}]), edges: new vis.DataSet([{','.join(edges)}])}};
        var options = {{
            nodes: {{ shape: 'dot', size: 20, font: {{ size: 14, face: 'Helvetica' }} }},
            groups: {{ 
                concept: {{ color: {{ background: '#3498db', border: '#2980b9' }} }}, 
                tag: {{ color: {{ background: '#bdc3c7', border: '#95a5a6' }}, shape: 'ellipse' }} 
            }},
            physics: {{ 
                enabled: true,
                solver: 'forceAtlas2Based',
                forceAtlas2Based: {{ gravitationalConstant: -50, centralGravity: 0.005, springLength: 100, springConstant: 0.08 }},
                stabilization: {{ iterations: 200 }} 
            }},
            layout: {{ randomSeed: 2 }}
        }};
        new vis.Network(container, data, options);
        </script>"""
        components.html(html, height=520)
    else: st.info("데이터가 없습니다.")
