import streamlit as st
import sqlite3
import datetime
import pandas as pd
import streamlit.components.v1 as components
import json
import urllib.request # 👈 핵심: 라이브러리 설치 없이 API 호출하는 내장 모듈

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
# [AI BRAIN] 설치가 필요 없는 REST API 호출 방식
# ==========================================
def call_gemini_raw(api_key, concept):
    """
    google-generativeai 라이브러리 없이, http 요청으로 직접 Gemini를 부릅니다.
    """
    if not api_key:
        return "키 없음", "API Key를 입력하세요.", "Error"

    # Gemini 1.5 Flash 엔드포인트
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    # 프롬프트 구성
    prompt_text = f"""
    당신은 '파인만틱 엔진'의 AI 코어입니다. 개념 '{concept}'에 대해 한국어로 다음 형식에 맞춰 답변하세요.
    
    1. [Feynman]: 12살 아이에게 설명하듯 쉬운 비유 (3문장 이내)
    2. [Popper]: 이 이론의 한계, 반론, 혹은 예외 상황 (2문장 이내)
    3. [Tags]: 연관 키워드 3개 (쉼표 구분)
    
    구분자: |||
    """
    
    # 데이터 패키징
    data = {
        "contents": [{
            "parts": [{"text": prompt_text}]
        }]
    }
    
    try:
        # Python 내장 기능으로 요청 전송 (No pip install needed)
        req = urllib.request.Request(
            url, 
            data=json.dumps(data).encode('utf-8'), 
            headers={'Content-Type': 'application/json'}
        )
        
        with urllib.request.urlopen(req) as response:
            res_body = response.read().decode('utf-8')
            res_json = json.loads(res_body)
            
            # 응답 파싱
            content = res_json['candidates'][0]['content']['parts'][0]['text']
            parts = content.split('|||')
            
            if len(parts) >= 3:
                return parts[0].strip(), parts[1].strip(), parts[2].strip()
            else:
                return content, "형식 파싱 실패", "Error"

    except Exception as e:
        return f"통신 에러: {str(e)}", "API Key를 확인하세요.", "Error"

# ==========================================
# [UI] Setup
# ==========================================
st.set_page_config(page_title="FeynmanTic OS", page_icon="🧠", layout="wide")
df = get_all_thoughts()

with st.sidebar:
    st.title("⚙️ Setup")
    google_api_key = st.text_input("Google API Key", type="password", placeholder="AI Studio Key")
    if not google_api_key:
        st.warning("키가 없으면 AI가 작동하지 않습니다.")
        st.markdown("[👉 키 무료 발급받기](https://aistudio.google.com/app/apikey)")
    else:
        st.success("시스템 가동 준비 완료")
    
    st.markdown("---")
    st.metric("Total Knowledge", len(df))

st.title("🧠 FeynmanTic OS v3.5")
st.caption("No-Install Edition: Pure Python & REST API")

# ==========================================
# [VISUALIZATION] Interactive Graph
# ==========================================
st.subheader("🕸 Living Knowledge Network")
if df.empty:
    st.info("데이터가 없습니다. 지식을 입력하세요.")
else:
    nodes = []
    edges = []
    existing_nodes = set()
    for index, row in df.iterrows():
        concept = row['concept']
        if concept not in existing_nodes:
            nodes.append(f"{{id: '{concept}', label: '{concept}', group: 'concept'}}")
            existing_nodes.add(concept)
        if row['tags']:
            tags = [t.strip() for t in row['tags'].split(',')]
            for tag in tags:
                if tag:
                    if tag not in existing_nodes:
                        nodes.append(f"{{id: '{tag}', label: '{tag}', group: 'tag'}}")
                        existing_nodes.add(tag)
                    edges.append(f"{{from: '{concept}', to: '{tag}'}}")

    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
      <style>#mynetwork {{ width: 100%; height: 400px; background: white; border: 1px solid #eee; }}</style>
    </head>
    <body>
    <div id="mynetwork"></div>
    <script>
      var nodes = new vis.DataSet([{','.join(nodes)}]);
      var edges = new vis.DataSet([{','.join(edges)}]);
      var container = document.getElementById('mynetwork');
      var data = {{ nodes: nodes, edges: edges }};
      var options = {{
        nodes: {{ shape: 'dot', size: 20, font: {{ size: 14 }} }},
        groups: {{ concept: {{ color: '#3498db' }}, tag: {{ color: '#bdc3c7', shape: 'ellipse' }} }},
        physics: {{ stabilization: false, solver: 'forceAtlas2Based' }}
      }};
      new vis.Network(container, data, options);
    </script>
    </body>
    </html>
    """
    components.html(html_code, height=420)

# ==========================================
# [ENGINE] Input
# ==========================================
st.markdown("---")
st.subheader("🚀 Engine Input")

if 'ai_c' not in st.session_state: st.session_state['ai_c'] = ""
if 'ai_e' not in st.session_state: st.session_state['ai_e'] = ""
if 'ai_f' not in st.session_state: st.session_state['ai_f'] = ""
if 'ai_t' not in st.session_state: st.session_state['ai_t'] = ""

col1, col2 = st.columns([4, 1])
with col1:
    target = st.text_input("공부할 주제", placeholder="예: 블랙홀")
with col2:
    st.write("")
    st.write("")
    if st.button("✨ Gemini"):
        if not google_api_key:
            st.error("키 필요")
        elif not target:
            st.warning("주제 필요")
        else:
            with st.spinner("Thinking..."):
                e, f, t = call_gemini_raw(google_api_key, target)
                st.session_state['ai_c'] = target
                st.session_state['ai_e'] = e
                st.session_state['ai_f'] = f
                st.session_state['ai_t'] = t
                st.success("완료")

tab1, tab2, tab3 = st.tabs(["Feynman", "Popper", "Deutsch"])
with st.form("main_form"):
    with tab1:
        c_in = st.text_input("Concept", value=st.session_state['ai_c'])
        e_in = st.text_area("Explanation", value=st.session_state['ai_e'])
    with tab2:
        f_in = st.text_area("Falsification", value=st.session_state['ai_f'])
    with tab3:
        t_in = st.text_input("Tags", value=st.session_state['ai_t'])
    
    if st.form_submit_button("Save"):
        if c_in:
            save_thought_to_db(c_in, e_in, f_in, t_in)
            # 초기화
            for key in ['ai_c', 'ai_e', 'ai_f', 'ai_t']:
                st.session_state[key] = ""
            st.rerun()
        else:
            st.error("내용 없음")

# ==========================================
# [ARCHIVE]
# ==========================================
with st.expander("📂 Archive"):
    if not df.empty:
        for idx, row in df.iterrows():
            c1, c2 = st.columns([5,1])
            c1.write(f"**{row['concept']}**")
            if c2.button("Del", key=f"d_{row['id']}"):
                delete_thought_from_db(row['id'])
                st.rerun()
