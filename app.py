import streamlit as st
import sqlite3
import datetime
import pandas as pd
import streamlit.components.v1 as components

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
# [UI] Setup
# ==========================================
st.set_page_config(page_title="FeynmanTic OS", page_icon="🧠", layout="wide")
df = get_all_thoughts()
total_thoughts = len(df)

st.title("🧠 FeynmanTic OS v2.0")
st.caption("Update: Interactive Physics Graph (Vis.js Implementation)")

# ==========================================
# [INTERACTIVE GRAPH] 핵심 업그레이드
# ==========================================
st.subheader("🕸 Living Knowledge Network")

if df.empty:
    st.info("데이터가 없습니다. 아래 엔진을 가동하여 지식을 주입하세요.")
else:
    # 1. 그래프 데이터 구성 (Nodes & Edges)
    nodes = []
    edges = []
    
    existing_nodes = set()
    
    for index, row in df.iterrows():
        concept = row['concept']
        # 개념 노드 (파란색)
        if concept not in existing_nodes:
            nodes.append(f"{{id: '{concept}', label: '{concept}', group: 'concept'}}")
            existing_nodes.add(concept)
            
        if row['tags']:
            tags = [t.strip() for t in row['tags'].split(',')]
            for tag in tags:
                if tag:
                    # 태그 노드 (회색)
                    if tag not in existing_nodes:
                        nodes.append(f"{{id: '{tag}', label: '{tag}', group: 'tag'}}")
                        existing_nodes.add(tag)
                    # 엣지 연결
                    edges.append(f"{{from: '{concept}', to: '{tag}'}}")

    # 2. HTML/JS 템플릿 생성 (Vis.js 라이브러리 CDN 사용)
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
      <style type="text/css">
        #mynetwork {{
          width: 100%;
          height: 500px;
          border: 1px solid #lightgray;
          background-color: #ffffff;
        }}
      </style>
    </head>
    <body>
    <div id="mynetwork"></div>
    <script type="text/javascript">
      // 데이터 주입
      var nodes = new vis.DataSet([{','.join(nodes)}]);
      var edges = new vis.DataSet([{','.join(edges)}]);

      var container = document.getElementById('mynetwork');
      var data = {{
        nodes: nodes,
        edges: edges
      }};
      
      var options = {{
        nodes: {{
          shape: 'dot',
          size: 20,
          font: {{ size: 16 }}
        }},
        groups: {{
          concept: {{ color: {{ background: '#3498db', border: '#2980b9' }}, font: {{ color: 'black' }} }},
          tag: {{ color: {{ background: '#ecf0f1', border: '#bdc3c7' }}, shape: 'ellipse', font: {{ size: 12, color: '#7f8c8d' }} }}
        }},
        physics: {{
          enabled: true,
          stabilization: false,
          solver: 'forceAtlas2Based', // 물리 엔진 알고리즘
          forceAtlas2Based: {{
            gravitationalConstant: -50,
            centralGravity: 0.005,
            springLength: 100,
            springConstant: 0.08
          }}
        }},
        interaction: {{ hover: true, zoomView: true, dragView: true }}
      }};
      
      var network = new vis.Network(container, data, options);
    </script>
    </body>
    </html>
    """
    
    # 3. 렌더링 (iframe으로 삽입)
    components.html(html_code, height=520)

# ==========================================
# [ENGINE] Input
# ==========================================
st.markdown("---")
st.subheader("🚀 Engine Input")
tab1, tab2, tab3 = st.tabs(["1. Feynman", "2. Popper", "3. Deutsch"])

with st.form(key='engine_form', clear_on_submit=True):
    with tab1:
        c_in = st.text_input("Concept", placeholder="핵심 개념")
        e_in = st.text_area("Redefinition", placeholder="쉬운 설명", height=80)
    with tab2:
        f_in = st.text_area("Falsification", placeholder="반증/한계", height=80)
    with tab3:
        t_in = st.text_input("Tags", placeholder="연결 고리 (콤마로 구분)")
        
    if st.form_submit_button("Inject to Network"):
        if not c_in: st.error("개념을 입력하세요.")
        else:
            save_thought_to_db(c_in, e_in, f_in, t_in)
            st.success("지식이 네트워크에 통합되었습니다.")
            st.rerun()

# ==========================================
# [ARCHIVE] List
# ==========================================
with st.expander("📂 Data List View"):
    if not df.empty:
        for index, row in df.iterrows():
            col1, col2 = st.columns([5, 1])
            with col1:
                st.markdown(f"**{row['concept']}** : {row['explanation']}")
            with col2:
                if st.button("Del", key=f"del_{row['id']}"):
                    delete_thought_from_db(row['id'])
                    st.rerun()
