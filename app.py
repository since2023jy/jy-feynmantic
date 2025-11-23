import streamlit as st
import sqlite3
import datetime
import pandas as pd
import streamlit.components.v1 as components
from openai import OpenAI

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
# [AI BRAIN] GPT-4o-mini 연결 (가성비 최적화)
# ==========================================
def generate_ai_insight(api_key, concept):
    """
    AI가 파인만과 포퍼가 되어 대신 작성해줍니다.
    """
    if not api_key:
        return "API Key가 필요합니다.", "API Key를 입력하세요.", "AI,Error"
    
    client = OpenAI(api_key=api_key)
    
    prompt = f"""
    당신은 '파인만틱 엔진'의 AI 코어입니다. 사용자가 입력한 개념인 '{concept}'에 대해 다음 형식으로 답변하세요.
    한국어로 답변해야 합니다.
    
    1. [Feynman]: 이 개념을 12살 아이도 이해할 수 있게 아주 쉽고 직관적인 비유를 들어 설명하세요. (3문장 이내)
    2. [Popper]: 이 개념이나 이론이 틀릴 수 있는 상황, 한계점, 혹은 반론을 날카롭게 지적하세요. (2문장 이내)
    3. [Tags]: 이 개념과 연관된 키워드 3개를 쉼표로 구분해 적으세요.
    
    형식 구분자: ||| (각 파트 사이를 |||로 구분하세요)
    예시 출력: 시간은 고무줄 같다... ||| 하지만 양자 역학에서는... ||| 물리,시간,상대성
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini", # 속도와 비용을 위해 mini 모델 사용
            messages=[{"role": "system", "content": "You are a helpful assistant."},
                      {"role": "user", "content": prompt}],
            temperature=0.7
        )
        content = response.choices[0].message.content
        parts = content.split('|||')
        
        if len(parts) >= 3:
            return parts[0].strip(), parts[1].strip(), parts[2].strip()
        else:
            return content, "AI 파싱 에러", "Error"
            
    except Exception as e:
        return f"에러 발생: {str(e)}", "AI 호출 실패", "Error"

# ==========================================
# [UI] Setup
# ==========================================
st.set_page_config(page_title="FeynmanTic OS", page_icon="🧠", layout="wide")
df = get_all_thoughts()

# 사이드바: API 키 입력
with st.sidebar:
    st.title("⚙️ Engine Room")
    openai_api_key = st.text_input("OpenAI API Key", type="password", placeholder="sk-...")
    st.caption("키가 없으면 수동 모드로 작동합니다.")
    st.markdown("---")
    st.metric(label="Total Nodes", value=len(df))

st.title("🧠 FeynmanTic OS v2.5")
st.caption("Feature: AI Co-Pilot (Auto-Drafting)")

# ==========================================
# [VISUALIZATION] Interactive Graph
# ==========================================
st.subheader("🕸 Living Knowledge Network")
if df.empty:
    st.info("지식이 없습니다. 아래 엔진을 가동하세요.")
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
# [ENGINE] AI-Powered Input Form
# ==========================================
st.markdown("---")
st.subheader("🚀 Engine Input (AI Powered)")

# 세션 상태 초기화 (AI 답변을 폼에 채워넣기 위함)
if 'ai_concept' not in st.session_state: st.session_state['ai_concept'] = ""
if 'ai_expl' not in st.session_state: st.session_state['ai_expl'] = ""
if 'ai_fals' not in st.session_state: st.session_state['ai_fals'] = ""
if 'ai_tags' not in st.session_state: st.session_state['ai_tags'] = ""

col_input, col_btn = st.columns([4, 1])
with col_input:
    target_concept = st.text_input("무엇을 공부하시겠습니까?", key="target_concept_input", placeholder="예: 엔트로피, 마케팅 깔때기...")

with col_btn:
    st.write("") # 줄맞춤용
    st.write("") 
    if st.button("🤖 AI 작성"):
        if not openai_api_key:
            st.error("API 키 필요")
        elif not target_concept:
            st.warning("개념을 입력하세요")
        else:
            with st.spinner("파인만과 포퍼가 회의 중입니다..."):
                expl, fals, tags = generate_ai_insight(openai_api_key, target_concept)
                st.session_state['ai_concept'] = target_concept
                st.session_state['ai_expl'] = expl
                st.session_state['ai_fals'] = fals
                st.session_state['ai_tags'] = tags
                st.success("초안 작성 완료! 아래 내용을 수정해서 저장하세요.")

# 탭 입력 폼 (AI가 채워준 내용이 default value로 들어감)
tab1, tab2, tab3 = st.tabs(["1. Feynman", "2. Popper", "3. Deutsch"])

with st.form(key='final_form'):
    with tab1:
        # session_state 값을 value로 설정
        c_in = st.text_input("Concept", value=st.session_state['ai_concept'])
        e_in = st.text_area("Redefinition (AI Draft)", value=st.session_state['ai_expl'], height=100)
    with tab2:
        f_in = st.text_area("Falsification (AI Draft)", value=st.session_state['ai_fals'], height=100)
    with tab3:
        t_in = st.text_input("Tags (AI Draft)", value=st.session_state['ai_tags'])
        
    if st.form_submit_button("💾 최종 저장 (Save to Grid)"):
        if not c_in:
            st.error("개념이 비어있습니다.")
        else:
            save_thought_to_db(c_in, e_in, f_in, t_in)
            # 저장 후 세션 초기화
            st.session_state['ai_concept'] = ""
            st.session_state['ai_expl'] = ""
            st.session_state['ai_fals'] = ""
            st.session_state['ai_tags'] = ""
            st.rerun()

# ==========================================
# [ARCHIVE]
# ==========================================
with st.expander("📂 지식 보관함"):
    if not df.empty:
        for index, row in df.iterrows():
            col1, col2 = st.columns([5, 1])
            with col1:
                st.write(f"**{row['concept']}**: {row['explanation'][:50]}...")
            with col2:
                if st.button("Del", key=f"del_{row['id']}"):
                    delete_thought_from_db(row['id'])
                    st.rerun()
