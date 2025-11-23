import streamlit as st
import sqlite3
import datetime
import pandas as pd
import streamlit.components.v1 as components
import json
import urllib.request
import urllib.error
import time
from datetime import datetime as dt

# ==========================================
# [DATABASE]
# ==========================================
def init_db():
    conn = sqlite3.connect('feynman.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS thoughts (
        id INTEGER PRIMARY KEY AUTOINCREMENT, concept TEXT NOT NULL, explanation TEXT, 
        falsification TEXT, tags TEXT, created_at TEXT, status TEXT DEFAULT 'active')''')
    c.execute('''CREATE TABLE IF NOT EXISTS chat_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, role TEXT, content TEXT, created_at TEXT)''')
    conn.commit(); conn.close()

def save_thought(c, e, f, t):
    conn = sqlite3.connect('feynman.db', check_same_thread=False)
    conn.execute("INSERT INTO thoughts (concept, explanation, falsification, tags, created_at) VALUES (?,?,?,?,?)", 
                 (c, e, f, t, dt.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit(); conn.close()

def save_chat(r, c):
    conn = sqlite3.connect('feynman.db', check_same_thread=False)
    conn.execute("INSERT INTO chat_logs (role, content, created_at) VALUES (?,?,?)", 
                 (r, c, dt.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit(); conn.close()

def get_data():
    conn = sqlite3.connect('feynman.db', check_same_thread=False)
    thoughts = pd.read_sql_query("SELECT * FROM thoughts ORDER BY id DESC", conn)
    chats = pd.read_sql_query("SELECT * FROM chat_logs ORDER BY id ASC", conn)
    conn.close()
    return thoughts, chats

init_db()

# ==========================================
# [AI LOGIC]
# ==========================================
def analyze_input(api_key, text):
    if not api_key: return None, "키 없음"
    prompt = f"""
    Analyze user input: "{text}"
    If it's knowledge, extract to JSON: {{ "is_knowledge": true, "concept": "...", "explanation": "...", "falsification": "...", "tags": "...", "reply": "..." }}
    If casual, JSON: {{ "is_knowledge": false, "reply": "..." }}
    Output ONLY JSON.
    """
    models = ["gemini-1.5-flash", "gemini-1.5-flash-latest", "gemini-1.0-pro"]
    data = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode('utf-8')
    headers = {'Content-Type': 'application/json'}
    
    for model in models:
        try:
            req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}", data=data, headers=headers)
            with urllib.request.urlopen(req) as res:
                txt = json.loads(res.read().decode('utf-8'))['candidates'][0]['content']['parts'][0]['text']
                clean = txt.replace("```json", "").replace("```", "").strip()
                return json.loads(clean), None
        except: continue
    return None, "연결 실패"

# ==========================================
# [UI] THE FUSION LAYOUT
# ==========================================
st.set_page_config(page_title="FeynmanTic Ultimate", page_icon="🧠", layout="wide")

# 1. Sidebar (Settings)
with st.sidebar:
    st.title("⚙️ System Core")
    google_api_key = st.text_input("Google API Key", type="password")
    if st.button("Reset System"):
        conn = sqlite3.connect('feynman.db', check_same_thread=False)
        conn.execute("DELETE FROM chat_logs"); conn.execute("DELETE FROM thoughts"); conn.commit(); conn.close()
        st.rerun()

st.title("🧠 FeynmanTic OS v13.0")
st.caption("Chat Interface + Dynamic Knowledge Graph")

# 데이터 로드
thoughts_df, chats_df = get_data()

# ==========================================
# 2. TOP SECTION: VISUALIZATION (THE UNIVERSE)
# ==========================================
# 채팅창 위에 그래프를 배치하여 '내 뇌가 변하는 모습'을 실시간으로 보여줌
with st.container():
    if not thoughts_df.empty:
        nodes, edges, exist = [], [], set()
        for _, r in thoughts_df.iterrows():
            c = r['concept']
            if c not in exist:
                nodes.append(f"{{id:'{c}', label:'{c}', group:'concept', value: 20}}")
                exist.add(c)
            if r['tags']:
                for t in r['tags'].split(','):
                    t = t.strip()
                    if t and t not in exist:
                        nodes.append(f"{{id:'{t}', label:'{t}', group:'tag', value: 10}}")
                        exist.add(t)
                    edges.append(f"{{from:'{c}', to:'{t}'}}")
        
        # 그래프 렌더링 (높이 조절)
        html = f"""
        <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
        <div id="mynetwork" style="width: 100%; height: 350px; background-color: #f8f9fa; border-radius: 10px; border: 1px solid #ddd;"></div>
        <script>
        var data = {{ nodes: new vis.DataSet([{','.join(nodes)}]), edges: new vis.DataSet([{','.join(edges)}]) }};
        var options = {{
            nodes: {{ font: {{ face: 'Helvetica', color: '#333' }}, shape: 'dot' }},
            groups: {{ 
                concept: {{ color: '#3498db' }}, 
                tag: {{ color: '#95a5a6' }} 
            }},
            physics: {{ 
                stabilization: false,
                solver: 'forceAtlas2Based',
                forceAtlas2Based: {{ gravitationalConstant: -30, springLength: 80 }}
            }},
            interaction: {{ zoomView: true, dragView: true }}
        }};
        new vis.Network(document.getElementById('mynetwork'), data, options);
        </script>
        """
        components.html(html, height=370)
    else:
        st.info("👆 위 공간은 당신의 '지식 우주'입니다. 아래 채팅으로 지식을 채워보세요.")

# ==========================================
# 3. BOTTOM SECTION: CHAT INTERFACE (INPUT)
# ==========================================
st.divider()

# 채팅 기록 출력
for _, row in chats_df.iterrows():
    with st.chat_message(row['role']):
        st.write(row['content'])

# 입력 처리
if prompt := st.chat_input("무엇을 배우셨나요? (예: 상대성 이론은 시간의 왜곡이다)"):
    # 유저 메시지 즉시 표시
    with st.chat_message("user"):
        st.write(prompt)
    save_chat("user", prompt)
    
    # AI 처리
    if google_api_key:
        with st.chat_message("assistant"):
            with st.spinner("지식 구조화 중..."):
                res_json, err = analyze_input(google_api_key, prompt)
                
                if err:
                    st.error(err)
                    save_chat("assistant", f"Error: {err}")
                else:
                    reply = res_json.get("reply", "...")
                    st.write(reply)
                    save_chat("assistant", reply)
                    
                    if res_json.get("is_knowledge"):
                        c = res_json.get("concept")
                        save_thought(c, res_json.get("explanation"), res_json.get("falsification"), res_json.get("tags"))
                        st.toast(f"✨ 그래프 업데이트: {c}", icon="🕸")
                        time.sleep(1)
                        st.rerun() # 그래프 갱신을 위해 리로딩
    else:
        st.error("API Key를 입력해주세요.")
