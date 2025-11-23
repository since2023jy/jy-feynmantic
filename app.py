import streamlit as st
import sqlite3
import datetime
import pandas as pd
import json
import urllib.request
import urllib.error
import time
from datetime import datetime as dt
import streamlit.components.v1 as components

# ==========================================
# [DATABASE]
# ==========================================
def init_db():
    conn = sqlite3.connect('feynman.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS thoughts (
        id INTEGER PRIMARY KEY AUTOINCREMENT, concept TEXT, explanation TEXT, 
        falsification TEXT, tags TEXT, created_at TEXT, status TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS chat_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, role TEXT, content TEXT, created_at TEXT)''')
    conn.commit(); conn.close()

def save_thought(c, e, f, t):
    conn = sqlite3.connect('feynman.db', check_same_thread=False)
    conn.execute("INSERT INTO thoughts (concept, explanation, falsification, tags, created_at, status) VALUES (?,?,?,?,?,?, 'active')", 
                 (c, e, f, t, dt.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit(); conn.close()

def save_chat(r, c):
    conn = sqlite3.connect('feynman.db', check_same_thread=False)
    conn.execute("INSERT INTO chat_logs (role, content, created_at) VALUES (?,?,?)", (r, c, dt.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit(); conn.close()

def get_data():
    conn = sqlite3.connect('feynman.db', check_same_thread=False)
    t = pd.read_sql_query("SELECT * FROM thoughts ORDER BY id DESC", conn)
    c = pd.read_sql_query("SELECT * FROM chat_logs ORDER BY id ASC", conn)
    conn.close()
    return t, c

init_db()

# ==========================================
# [AI PT LOGIC - ROBUST CONNECTION]
# ==========================================
def run_mental_gym(api_key, history):
    if not api_key: return None, "🚫 API Key가 없습니다."
    
    # 1. 시스템 프롬프트
    system_instruction = {
        "parts": [{ "text": """
            당신은 'FeynmanTic Gym'의 악독한 AI 트레이너입니다.
            목표: 유저가 대충 설명하면 '반려'하고, 질문을 던져서 더 구체적으로 설명하게 만드세요.
            
            규칙:
            1. 유저의 설명이 짧거나 추상적이면 "구체적인 비유를 들어보세요"라며 다시 시키세요.
            2. 유저가 '파인만 식 설명(비유)'과 '포퍼 식 반증(한계)'을 모두 말했을 때만 '합격'을 주세요.
            3. 합격 시에는 오직 JSON만 출력하세요.
            
            합격 시 출력 포맷(JSON):
            {
                "status": "passed",
                "concept": "개념명",
                "explanation": "유저의 설명 요약",
                "falsification": "유저의 반증 요약",
                "tags": "태그3개",
                "praise": "축하합니다! 저장되었습니다."
            }
        """}]
    }
    
    # 2. 대화 내역 구성
    contents = []
    for msg in history[-5:]: 
        role = "user" if msg['role'] == "user" else "model"
        contents.append({
            "role": role,
            "parts": [{"text": msg['content']}]
        })
    
    request_data = {
        "system_instruction": system_instruction,
        "contents": contents
    }
    
    # [FIX] 가능한 모든 모델명 리스트 (순서대로 시도)
    # gemini-pro는 가장 범용적이라 성공 확률이 높습니다.
    models_to_try = [
        "gemini-1.5-flash",
        "gemini-pro", 
        "gemini-1.5-pro-latest",
        "gemini-1.0-pro"
    ]
    
    headers = {'Content-Type': 'application/json'}
    last_error_msg = ""

    for model in models_to_try:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            req = urllib.request.Request(url, data=json.dumps(request_data).encode('utf-8'), headers=headers)
            
            with urllib.request.urlopen(req) as res:
                response = json.loads(res.read().decode('utf-8'))
                
                if 'candidates' in response and response['candidates']:
                    text = response['candidates'][0]['content']['parts'][0]['text']
                    
                    if "{" in text and "passed" in text:
                        try:
                            clean_json = text[text.find('{'):text.rfind('}')+1]
                            return json.loads(clean_json), None
                        except:
                            return {"status": "coaching", "text": text}, None
                    else:
                        return {"status": "coaching", "text": text}, None
                else:
                    last_error_msg = "빈 응답"
                    continue # 다음 모델 시도

        except urllib.error.HTTPError as e:
            # 404면 모델이 없는 것이니 다음 모델 시도 (continue)
            if e.code == 404:
                last_error_msg = f"{model} 모델 없음(404), 다음 시도..."
                continue
            elif e.code == 400:
                # 400 에러는 요청 형식이 안맞는 경우일 수 있음. gemini-pro로 넘어가서 시도
                last_error_msg = f"{model} 요청 오류(400), 다음 시도..."
                continue
            elif e.code == 401:
                return None, "🚫 API Key가 틀렸습니다. (401 Unauthorized)"
            else:
                last_error_msg = f"HTTP Error {e.code}"
                continue
        except Exception as e:
            last_error_msg = str(e)
            continue
            
    return None, f"모든 AI 모델 연결 실패. (마지막 에러: {last_error_msg})"

# ==========================================
# [UI] GYM INTERFACE
# ==========================================
st.set_page_config(page_title="FeynmanTic Gym", page_icon="🏋️", layout="wide")

with st.sidebar:
    st.title("🏋️ FeynmanTic Gym")
    st.caption("No Pain, No Brain.")
    google_api_key = st.text_input("Gym Pass (API Key)", type="password")
    
    st.markdown("---")
    if st.button("🧹 라커룸 청소 (대화 초기화)"):
        conn = sqlite3.connect('feynman.db', check_same_thread=False)
        conn.execute("DELETE FROM chat_logs")
        conn.commit(); conn.close()
        st.rerun()

col_graph, col_chat = st.columns([1, 1])

# 1. Graph
with col_graph:
    st.subheader("💪 Knowledge Muscles")
    thoughts_df, chats_df = get_data()
    
    if not thoughts_df.empty:
        nodes, edges, exist = [], [], set()
        for _, r in thoughts_df.iterrows():
            c = r['concept']
            if c not in exist:
                nodes.append(f"{{id:'{c}', label:'{c}', color:'#e74c3c', size:25}}")
                exist.add(c)
            if r['tags']:
                for t in r['tags'].split(','):
                    t = t.strip()
                    if t and t not in exist:
                        nodes.append(f"{{id:'{t}', label:'{t}', color:'#bdc3c7', size:15}}")
                        exist.add(t)
                    edges.append(f"{{from:'{c}', to:'{t}'}}")
        html = f"""
        <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
        <div id="mynetwork" style="height:600px; border:1px solid #ddd; background:#fdfdfd;"></div>
        <script>
        var data = {{nodes: new vis.DataSet([{','.join(nodes)}]), edges: new vis.DataSet([{','.join(edges)}])}};
        var options = {{
            nodes: {{ shape: 'dot', font: {{ face: 'Helvetica', size: 16 }} }},
            physics: {{ stabilization: false, solver: 'forceAtlas2Based', forceAtlas2Based: {{ springLength: 100 }} }}
        }};
        new vis.Network(document.getElementById('mynetwork'), data, options);
        </script>"""
        components.html(html, height=620)
    else:
        st.info("아직 근육이 없습니다. 오른쪽에서 훈련하세요.")

# 2. Chat
with col_chat:
    st.subheader("🥊 1:1 PT Session")
    
    for _, row in chats_df.iterrows():
        avatar = "🏋️" if row['role'] == "assistant" else "🥵"
        with st.chat_message(row['role'], avatar=avatar):
            st.write(row['content'])
            
    if prompt := st.chat_input("훈련 시작 (예: 상대성 이론)"):
        with st.chat_message("user", avatar="🥵"):
            st.write(prompt)
        save_chat("user", prompt)
        
        if google_api_key:
            with st.chat_message("assistant", avatar="🏋️"):
                message_placeholder = st.empty()
                message_placeholder.markdown("🔥 자세 분석 중...")
                
                history_data = []
                for _, r in chats_df.tail(5).iterrows():
                    history_data.append({"role": r['role'], "content": r['content']})
                history_data.append({"role": "user", "content": prompt})
                
                res, err = run_mental_gym(google_api_key, history_data)
                
                if err:
                    st.error(err)
                    save_chat("assistant", f"Error: {err}")
                else:
                    if res.get("status") == "passed":
                        reply = res.get("praise", "저장 완료.")
                        save_thought(res['concept'], res['explanation'], res['falsification'], res['tags'])
                        st.balloons()
                        st.success(f"✅ 저장됨: {res['concept']}")
                        save_chat("assistant", reply)
                        message_placeholder.markdown(reply)
                        time.sleep(1); st.rerun()
                    else:
                        reply = res.get("text", "...")
                        save_chat("assistant", reply)
                        message_placeholder.markdown(reply)
        else:
            st.error("사이드바에 API Key를 입력해주세요!")
