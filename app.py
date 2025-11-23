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
from datetime import datetime as dt, timedelta

# ==========================================
# [CTO] DATABASE MIGRATION (v11.0)
# ==========================================
def init_db():
    conn = sqlite3.connect('feynman.db', check_same_thread=False)
    c = conn.cursor()
    # 테이블 생성 (기존 테이블이 있으면 무시되지만, 컬럼 추가를 위해 체크)
    c.execute('''
        CREATE TABLE IF NOT EXISTS thoughts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            concept TEXT NOT NULL,
            explanation TEXT NOT NULL,
            falsification TEXT,
            tags TEXT,
            created_at TEXT,
            updated_at TEXT,
            status TEXT DEFAULT 'active', 
            health INTEGER DEFAULT 100
        )
    ''')
    
    # v11.0 마이그레이션: 컬럼이 없을 경우 추가 (SQLite 특성상 try-except로 처리)
    try:
        c.execute("ALTER TABLE thoughts ADD COLUMN status TEXT DEFAULT 'active'")
    except: pass
    try:
        c.execute("ALTER TABLE thoughts ADD COLUMN health INTEGER DEFAULT 100") # 지식의 건강 상태 (0~100)
    except: pass
    try:
        c.execute("ALTER TABLE thoughts ADD COLUMN updated_at TEXT")
    except: pass
    
    conn.commit()
    conn.close()

# 지식 저장 (Inbox로 보냄)
def save_to_inbox(concept, expl, fals, tags, source="manual"):
    conn = sqlite3.connect('feynman.db', check_same_thread=False)
    c = conn.cursor()
    now = dt.now().strftime("%Y-%m-%d %H:%M:%S")
    # AI가 만든건 pending(보류), 내가 만든건 active(활성)
    status = 'pending' if source == "ai" else 'active'
    
    c.execute('''
        INSERT INTO thoughts (concept, explanation, falsification, tags, created_at, updated_at, status, health)
        VALUES (?, ?, ?, ?, ?, ?, ?, 100)
    ''', (concept, expl, fals, tags, now, now, status))
    conn.commit()
    conn.close()

# 지식 승인 (Pending -> Active)
def approve_thought(thought_id):
    conn = sqlite3.connect('feynman.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("UPDATE thoughts SET status = 'active', health = 100, updated_at = ? WHERE id = ?", 
              (dt.now().strftime("%Y-%m-%d %H:%M:%S"), thought_id))
    conn.commit()
    conn.close()

# 지식 복습 (Watering) - 건강 회복
def water_thought(thought_id):
    conn = sqlite3.connect('feynman.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("UPDATE thoughts SET health = 100, updated_at = ? WHERE id = ?", 
              (dt.now().strftime("%Y-%m-%d %H:%M:%S"), thought_id))
    conn.commit()
    conn.close()

def delete_thought(thought_id):
    conn = sqlite3.connect('feynman.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("DELETE FROM thoughts WHERE id = ?", (thought_id,))
    conn.commit()
    conn.close()

def get_thoughts(status='active'):
    conn = sqlite3.connect('feynman.db', check_same_thread=False)
    # health 계산 로직 포함
    df = pd.read_sql_query(f"SELECT * FROM thoughts WHERE status = '{status}' ORDER BY id DESC", conn)
    conn.close()
    return df

# [Duolingo Logic] 지식 부패 시뮬레이션
def calculate_decay():
    conn = sqlite3.connect('feynman.db', check_same_thread=False)
    c = conn.cursor()
    # 하루에 10씩 건강 감소
    c.execute("UPDATE thoughts SET health = health - 5 WHERE health > 0 AND status = 'active'")
    conn.commit()
    conn.close()

init_db()

# ==========================================
# [PALANTIR] AI INTELLIGENCE
# ==========================================
@st.cache_data(ttl=3600)
def get_google_news_kr():
    url = "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko"
    try:
        with urllib.request.urlopen(url) as response:
            xml_data = response.read()
            root = ET.fromstring(xml_data)
            return [item.find('title').text.split(' - ')[0] for item in root.findall('.//item')[:5]]
    except: return ["AI", "경제", "과학"]

def call_gemini(api_key, prompt):
    if not api_key: return "API Key 없음"
    models = ["gemini-1.5-flash", "gemini-pro", "gemini-1.0-pro"]
    data = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode('utf-8')
    headers = {'Content-Type': 'application/json'}
    for model in models:
        try:
            req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}", data=data, headers=headers)
            with urllib.request.urlopen(req) as res:
                return json.loads(res.read().decode('utf-8'))['candidates'][0]['content']['parts'][0]['text'].strip()
        except: continue
    return "연결 실패"

def auto_generate(api_key, concept):
    expl = call_gemini(api_key, f"'{concept}' 12살 설명 (2문장)")
    fals = call_gemini(api_key, f"'{concept}' 반론/예외 (1문장)")
    tags = call_gemini(api_key, f"'{concept}' 태그 2개 (쉼표구분)")
    return expl, fals, tags

# ==========================================
# [UI] DASHBOARD
# ==========================================
st.set_page_config(page_title="FeynmanTic Garden", page_icon="🌿", layout="wide")

# 사이드바 설정
with st.sidebar:
    st.title("🌿 Digital Garden")
    google_api_key = st.text_input("Google API Key", type="password")
    
    st.markdown("---")
    
    # [GOD MODE] 관전 스위치
    spectator = st.toggle("👁️ 관전 모드 (Auto-Gather)", value=False)
    if spectator and google_api_key:
        st.success("🤖 AI가 검역소(Inbox)로 지식을 나르고 있습니다...")
        
        # 자동 수집 로직 (백그라운드 실행 흉내)
        if st.button("수동 트리거: 뉴스 수집 1회 실행"):
            news_item = random.choice(get_google_news_kr())
            with st.spinner(f"AI가 '{news_item}' 분석 중..."):
                e, f, t = auto_generate(google_api_key, news_item)
                save_to_inbox(news_item, e, f, t, source="ai")
                st.toast(f"📦 '{news_item}' 검역소 도착!", icon="🚚")
                time.sleep(1)

    st.markdown("---")
    # [Duolingo] 부패 시스템
    if st.button("⏳ 시간 경과 시뮬레이션 (Decay)"):
        calculate_decay()
        st.toast("시간이 흘러 지식들이 낡았습니다...", icon="🥀")
        time.sleep(1); st.rerun()

# 메인 화면
st.title("🧠 FeynmanTic v11.0")

# 탭 구조 개편: 정원(뇌) -> 검역소(보류) -> 연구실(입력)
tab_garden, tab_inbox, tab_lab = st.tabs(["🌳 나의 뇌 (Garden)", "📦 검역소 (Inbox)", "🔬 연구실 (Lab)"])

# ==========================================
# 1. THE GARDEN (메인 그래프 & 리스트)
# ==========================================
with tab_garden:
    active_df = get_thoughts('active')
    
    # [Palantir Logic] 그래프 시각화 (건강 상태 반영)
    if not active_df.empty:
        nodes, edges, exist = [], [], set()
        
        for _, r in active_df.iterrows():
            # 건강 상태에 따른 색상 변화 (싱싱함=파랑, 썩음=회색)
            health = r.get('health', 100)
            if health is None: health = 100
            
            # Duolingo Style: 건강이 나쁘면 회색으로 변하고 작아짐
            if health > 70: color, size = "#3498db", 25 # Blue
            elif health > 30: color, size = "#f1c40f", 20 # Yellow
            else: color, size = "#95a5a6", 15 # Gray (Dying)
            
            c_id = r['concept']
            if c_id not in exist:
                nodes.append(f"{{id:'{c_id}', label:'{c_id}', group:'concept', color:'{color}', size:{size}}}")
                exist.add(c_id)
            
            if r['tags']:
                for t in r['tags'].split(','):
                    t = t.strip()
                    if t and t not in exist:
                        nodes.append(f"{{id:'{t}', label:'{t}', group:'tag'}}")
                        exist.add(t)
                    edges.append(f"{{from:'{c_id}', to:'{t}'}}")

        html = f"""<script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
        <div id="mynetwork" style="height:500px; border:1px solid #eee; background:#fafafa;"></div>
        <script>
        var data = {{nodes: new vis.DataSet([{','.join(nodes)}]), edges: new vis.DataSet([{','.join(edges)}])}};
        var options = {{
            nodes: {{ font: {{ face:'Helvetica', color:'#333' }} }},
            groups: {{ tag: {{ color:'#e0e0e0', shape:'ellipse', size:10 }} }},
            physics: {{ solver:'forceAtlas2Based', stabilization:{{iterations:150}} }},
            interaction: {{ hover:true }}
        }};
        new vis.Network(document.getElementById('mynetwork'), data, options);
        </script>"""
        components.html(html, height=520)
        
        # 리스트 뷰 (물주기 기능)
        st.subheader("🥀 관리 필요한 지식 (클릭해서 물주기)")
        
        # 건강 나쁜 순으로 정렬
        dying_df = active_df.sort_values(by='health', ascending=True)
        
        for idx, row in dying_df.iterrows():
            health = row.get('health', 100)
            if health is None: health = 100
            
            # 카드 스타일
            border_color = "#eee" if health > 70 else "#ffcccc" # 죽어가면 빨간 테두리
            
            with st.expander(f"{'🥀' if health < 50 else '🌿'} {row['concept']} (건강: {health}%)"):
                st.write(f"**설명:** {row['explanation']}")
                st.write(f"**반증:** {row['falsification']}")
                
                c1, c2 = st.columns([1, 4])
                with c1:
                    if st.button("💧 물주기 (복습)", key=f"water_{row['id']}"):
                        water_thought(row['id'])
                        st.toast(f"'{row['concept']}' 지식이 생생해졌습니다!", icon="✨")
                        time.sleep(1); st.rerun()
                with c2:
                    if st.button("🗑 삭제", key=f"del_{row['id']}"):
                        delete_thought(row['id']); st.rerun()

    else:
        st.info("정원이 비어있습니다. '연구실'이나 '검역소'에서 지식을 심으세요.")

# ==========================================
# 2. THE INBOX (검역소 - AI 생성 데이터)
# ==========================================
with tab_inbox:
    st.subheader("📦 지식 검역소 (Pending Knowledge)")
    st.caption("AI가 수집한 지식입니다. 승인하지 않으면 내 것이 아닙니다.")
    
    pending_df = get_thoughts('pending')
    
    if not pending_df.empty:
        for idx, row in pending_df.iterrows():
            with st.container():
                st.markdown(f"#### 🗞 {row['concept']}")
                st.info(f"**설명:** {row['explanation']}")
                st.warning(f"**반증:** {row['falsification']}")
                st.caption(f"Tags: {row['tags']}")
                
                c1, c2, c3 = st.columns([1, 1, 3])
                with c1:
                    if st.button("✅ 승인 (내 뇌로 이동)", key=f"app_{row['id']}", type="primary"):
                        approve_thought(row['id'])
                        st.toast("지식이 정원에 심어졌습니다!", icon="🌳")
                        time.sleep(1); st.rerun()
                with c2:
                    if st.button("❌ 거절 (삭제)", key=f"rej_{row['id']}"):
                        delete_thought(row['id'])
                        st.rerun()
                st.divider()
    else:
        st.success("검역소가 깨끗합니다. 관전 모드를 켜서 AI에게 수집을 시키세요.")

# ==========================================
# 3. THE LAB (직접 입력)
# ==========================================
with tab_lab:
    st.subheader("🔬 지식 연구실 (Manual Input)")
    
    # 간소화된 위저드
    c1, c2 = st.columns([2, 1])
    with c1:
        lc = st.text_input("개념 (Concept)")
    with c2:
        if st.button("✨ AI 자동완성 요청"):
            if lc and google_api_key:
                le, lf, lt = auto_generate(google_api_key, lc)
                st.session_state.temp_e = le
                st.session_state.temp_f = lf
                st.session_state.temp_t = lt
                st.rerun()
    
    le = st.text_area("설명 (Feynman)", value=st.session_state.get('temp_e', ''))
    lf = st.text_input("반증 (Popper)", value=st.session_state.get('temp_f', ''))
    lt = st.text_input("태그 (Deutsch)", value=st.session_state.get('temp_t', ''))
    
    if st.button("💾 연구 완료 (정원에 바로 심기)", type="primary"):
        if lc and le:
            save_to_inbox(lc, le, lf, lt, source="manual") # manual은 내부 로직에서 active로 처리됨
            st.session_state.temp_e = ""
            st.session_state.temp_f = ""
            st.session_state.temp_t = ""
            st.toast("연구 성공! 정원에 등록되었습니다.")
            time.sleep(1); st.rerun()
