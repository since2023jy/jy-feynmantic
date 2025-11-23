import streamlit as st
import sqlite3
import datetime
import pandas as pd
import streamlit.components.v1 as components
import json
import urllib.request
import time
import xml.etree.ElementTree as ET

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
# [AI & NEWS]
# ==========================================
@st.cache_data(ttl=3600)
def get_google_news_kr():
    url = "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko"
    try:
        with urllib.request.urlopen(url) as response:
            xml_data = response.read()
            root = ET.fromstring(xml_data)
            news_items = []
            for item in root.findall('.//item')[:5]:
                title = item.find('title').text
                if ' - ' in title: title = title.split(' - ')[0]
                news_items.append(title)
            return news_items
    except: return ["뉴스 로딩 실패"]

def call_gemini_step(api_key, concept, step_type):
    if not api_key: return "키 없음"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    # 프롬프트 설계
    if step_type == "briefing":
        # [NEW] 학습 모드: 선생님이 개념을 요약해줌
        prompt = f"사용자가 '{concept}'에 대해 공부하려고 해. 이 주제의 핵심 내용, 배경, 중요한 사실 3가지를 요약해서 '브리핑'해줘. 사용자가 읽고 이해할 수 있게 명확한 한국어로 설명해."
    elif step_type == "feynman":
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
# 위저드 데이터
if 'w_concept' not in st.session_state: st.session_state.w_concept = ""
if 'w_briefing' not in st.session_state: st.session_state.w_briefing = "" # [NEW] 브리핑 내용
if 'w_expl' not in st.session_state: st.session_state.w_expl = ""
if 'w_fals' not in st.session_state: st.session_state.w_fals = ""
if 'w_tags' not in st.session_state: st.session_state.w_tags = ""

def next_step(): st.session_state.step += 1
def prev_step(): st.session_state.step -= 1
def reset_wizard():
    st.session_state.step = 1
    st.session_state.w_concept = ""
    st.session_state.w_briefing = ""
    st.session_state.w_expl = ""
    st.session_state.w_fals = ""
    st.session_state.w_tags = ""

# ==========================================
# [UI] Setup
# ==========================================
st.set_page_config(page_title="FeynmanTic Learning", page_icon="🏫", layout="wide")
df = get_all_thoughts()

with st.sidebar:
    st.title("🏫 Learning Mode")
    google_api_key = st.text_input("Google API Key", type="password", placeholder="AI Studio Key")
    if not google_api_key:
        st.error("AI 브리핑을 위해 키가 필수입니다.")
        st.markdown("[👉 키 발급받기](https://aistudio.google.com/app/apikey)")
    
    st.markdown("---")
    # 진행 상황 표시 (총 5단계로 변경)
    progress = (st.session_state.step - 1) / 5
    st.progress(progress)
    st.caption(f"Phase {st.session_state.step}/5")

# ==========================================
# [MAIN] Wizard UI
# ==========================================
st.title("🧠 FeynmanTic v7.0")

# --- STEP 1: 주제 선정 ---
if st.session_state.step == 1:
    st.header("Step 1. 학습 주제 선정")
    st.info("오늘 공부할 뉴스나 주제를 선택하세요.")
    
    col_news, col_manual = st.columns(2)
    with col_news:
        st.subheader("📰 실시간 뉴스 피드")
        news_list = get_google_news_kr()
        for news in news_list:
            if st.button(f"👉 {news}", key=news, use_container_width=True):
                st.session_state.w_concept = news
                next_step(); st.rerun()
    with col_manual:
        st.subheader("✍️ 관심 주제 입력")
        manual = st.text_input("주제", placeholder="예: 양자역학")
        if st.button("Start ➡️", type="primary"):
            if manual:
                st.session_state.w_concept = manual
                next_step(); st.rerun()

# --- STEP 2: [NEW] AI 브리핑 (학습 단계) ---
elif st.session_state.step == 2:
    st.header(f"Step 2. '{st.session_state.w_concept}' 학습하기")
    
    # 브리핑 생성 (최초 1회만)
    if not st.session_state.w_briefing:
        if google_api_key:
            with st.spinner(f"AI 선생님이 '{st.session_state.w_concept}'에 대한 핵심 요약 노트를 만들고 있습니다..."):
                briefing = call_gemini_step(google_api_key, st.session_state.w_concept, "briefing")
                st.session_state.w_briefing = briefing
                st.rerun()
        else:
            st.warning("API 키가 없어서 브리핑을 건너뜁니다.")
            st.session_state.w_briefing = "API 키를 입력하면 AI 요약을 볼 수 있습니다."

    # 브리핑 출력 (읽기 모드)
    st.markdown("""
    <div style="background-color:#f0f7ff; padding:20px; border-radius:10px; border-left: 5px solid #3498db;">
        <h4>🤖 AI Summary Note</h4>
        <p>설명하기 전에, 이 내용을 먼저 읽고 이해해보세요.</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown(f"### 📝 {st.session_state.w_concept}")
    st.write(st.session_state.w_briefing)
    
    st.markdown("---")
    st.caption("충분히 읽으셨나요? 이제 이해한 내용을 바탕으로 직접 설명해볼 차례입니다.")
    
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("⬅️ 다시 선택"): prev_step(); st.rerun()
    with col2:
        if st.button("이해했습니다! 설명하러 가기 ➡️", type="primary"):
            next_step(); st.rerun()

# --- STEP 3: 파인만 (설명) ---
elif st.session_state.step == 3:
    st.header("Step 3. 나만의 언어로 재정의")
    st.success("방금 읽은 내용을 바탕으로, 빈칸을 채워보세요.")
    
    st.markdown(f"### **{st.session_state.w_concept}**(은)는 마치...")
    
    col_a, col_b = st.columns(2)
    with col_a:
        analogy = st.text_input("무엇과 비슷한가요? (비유)", placeholder="예: 도서관 사서")
    with col_b:
        reason = st.text_input("왜냐하면...", placeholder="예: 책(정보)을 찾아서 주니까")
        
    preview = f"**{st.session_state.w_concept}**은(는) 마치 **{analogy}**와(과) 같습니다. 왜냐하면 **{reason}** 때문입니다."
    
    if analogy and reason:
        st.info(f"⬇️ 작성된 문장:\n\n{preview.replace('**','')}")
        if st.button("입력 완료 ➡️", type="primary"):
            st.session_state.w_expl = preview.replace("**","")
            next_step(); st.rerun()
            
    with st.expander("직접 길게 쓰고 싶다면?"):
        long_text = st.text_area("서술형 입력", value=st.session_state.w_expl)
        if st.button("서술형으로 저장"):
            st.session_state.w_expl = long_text
            next_step(); st.rerun()

# --- STEP 4: 포퍼 (검증) ---
elif st.session_state.step == 4:
    st.header("Step 4. 비판적 검증")
    st.warning("AI 브리핑 내용이나 내 생각에서 빠진 점은 없을까요?")
    
    q1 = st.text_input("이 이론/개념이 적용되지 않는 예외 상황은?", placeholder="예: 전기가 끊겼을 때")
    
    if st.button("검증 완료 ➡️", type="primary"):
        st.session_state.w_fals = f"예외상황: {q1}" if q1 else "검증 내용 없음"
        next_step(); st.rerun()
        
    if google_api_key:
        if st.button("🤖 AI에게 반론 요청"):
            st.session_state.w_fals = call_gemini_step(google_api_key, st.session_state.w_concept, "popper")
            next_step(); st.rerun()

# --- STEP 5: 연결 (저장) ---
elif st.session_state.step == 5:
    st.header("Step 5. 저장 및 연결")
    
    if not st.session_state.w_tags and google_api_key:
        if st.button("✨ 태그 자동 추천"):
            st.session_state.w_tags = call_gemini_step(google_api_key, st.session_state.w_concept, "tags")
            st.rerun()
            
    tags = st.text_input("태그", value=st.session_state.w_tags)
    
    if st.button("🎉 지식 저장 (Finish)", type="primary"):
        save_thought_to_db(st.session_state.w_concept, st.session_state.w_expl, st.session_state.w_fals, tags)
        st.balloons()
        time.sleep(1.5)
        reset_wizard()
        st.rerun()

# ==========================================
# [VISUALIZATION]
# ==========================================
st.markdown("---")
with st.expander("🕸 Knowledge Graph", expanded=True):
    if not df.empty:
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
    else:
        st.info("저장된 지식이 없습니다.")
        
with st.expander("📂 Archive"):
    for _, row in df.iterrows():
        c1, c2 = st.columns([5,1])
        c1.write(f"**{row['concept']}**")
        if c2.button("Del", key=f"d_{row['id']}"):
            delete_thought_from_db(row['id']); st.rerun()
