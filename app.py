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
# [AI PT LOGIC]
# ==========================================
def run_mental_gym(api_key, history):
    if not api_key: return None, "회원님, PT 등록(API Key)부터 하시죠."
    
    # 시스템 프롬프트: AI는 친절하지만 엄격한 퍼스널 트레이너
    system_prompt = """
    당신은 'FeynmanTic Gym'의 악명 높은 AI 트레이너입니다.
    당신의 목표는 유저가 지식을 '대충' 저장하지 못하게 막고, 질문을 통해 '뇌 근육'을 찢어주는 것입니다.

    [규칙]
    1. 유저의 설명이 빈약하거나 전문용어만 나열하면 "더 쉽게 설명해보세요"라고 반려하세요. (절대 바로 저장해주지 마세요)
    2. 유저가 파인만 기법(쉬운 비유)으로 잘 설명하고, 포퍼의 반증(한계점)까지 언급했다면 그때 비로소 '합격'을 선언하세요.
    3. 합격 시에는 JSON 형식으로 데이터를 출력하여 저장을 승인하세요.
    
    [JSON 출력 조건]
    유저가 충분히 훌륭한 설명을 했을 때만 아래 JSON을 출력하세요. 그 전까지는 그냥 텍스트로 코칭하세요.
    {
        "status": "passed",
        "concept": "...",
        "explanation": "...",
        "falsification": "...",
        "tags": "...",
        "praise": "축하합니다! 3대 500급 지식이네요. 저장했습니다."
    }
    """
    
    # 대화 맥락 구성
    messages = [{"role": "system", "content": system_prompt}]
    for msg in history[-5:]: # 최근 5개 대화만 참조 (토큰 절약)
        messages.append({"role": "user" if msg['role']=='user' else "model", "parts": [{"text": msg['content']}]})
    
    # JSON 변환용 데이터 구조
    request_data = {
        "contents": messages
    }
    
    models = ["gemini-1.5-flash", "gemini-1.5-flash-latest", "gemini-1.0-pro"]
    headers = {'Content-Type': 'application/json'}
    
    for model in models:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            req = urllib.request.Request(url, data=json.dumps(request_data).encode('utf-8'), headers=headers)
            with urllib.request.urlopen(req) as res:
                response = json.loads(res.read().decode('utf-8'))
                text = response['candidates'][0]['content']['parts'][0]['text']
                
                # JSON이 포함되어 있는지 확인 (합격 신호)
                if "{" in text and "passed" in text:
                    try:
                        # JSON 추출
                        json_str = text[text.find('{'):text.rfind('}')+1]
                        return json.loads(json_str), None
                    except:
                        return {"status": "coaching", "text": text}, None
                else:
                    return {"status": "coaching", "text": text}, None
        except: continue
    return None, "PT 선생님이 응답하지 않습니다. (연결 오류)"

# ==========================================
# [UI] GYM INTERFACE
# ==========================================
st.set_page_config(page_title="FeynmanTic Gym", page_icon="🏋️", layout="wide")

# Sidebar
with st.sidebar:
    st.title("🏋️ FeynmanTic Gym")
    st.caption("No Pain, No Brain.")
    google_api_key = st.text_input("Gym Pass (API Key)", type="password")
    
    st.markdown("---")
    if st.button("🧹 라커룸 청소 (초기화)"):
        conn = sqlite3.connect('feynman.db', check_same_thread=False)
        conn.execute("DELETE FROM chat_logs")
        conn.commit(); conn.close()
        st.rerun()

# Layout
col_graph, col_chat = st.columns([1, 1])

# 1. 지식 근육도 (Graph)
with col_graph:
    st.subheader("💪 나의 뇌 근육 (Knowledge Muscles)")
    thoughts_df, chats_df = get_data()
    
    if not thoughts_df.empty:
        nodes, edges, exist = [], [], set()
        for _, r in thoughts_df.iterrows():
            c = r['concept']
            if c not in exist:
                nodes.append(f"{{id:'{c}', label:'{c}', color:'#e74c3c', size:25}}") # 빨간색 근육
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
        st.info("아직 근육이 없습니다. 오른쪽 채팅창에서 훈련을 시작하세요.")
        st.image("https://media.giphy.com/media/26tjZqONCYC73Y0JG/giphy.gif", caption="Get Ready to Sweat!")

# 2. PT 채팅방 (Chat)
with col_chat:
    st.subheader("🥊 1:1 PT Session")
    
    # 기록 표시
    for _, row in chats_df.iterrows():
        avatar = "🏋️" if row['role'] == "assistant" else "🥵"
        with st.chat_message(row['role'], avatar=avatar):
            st.write(row['content'])
            
    # 입력
    if prompt := st.chat_input("오늘 훈련할 지식은 무엇입니까?"):
        with st.chat_message("user", avatar="🥵"):
            st.write(prompt)
        save_chat("user", prompt)
        
        if google_api_key:
            with st.chat_message("assistant", avatar="🏋️"):
                message_placeholder = st.empty()
                message_placeholder.markdown("🔥 자세 교정 중...")
                
                # 대화 기록 구성 (최근 5턴)
                history_data = []
                for _, r in chats_df.tail(5).iterrows():
                    history_data.append({"role": r['role'], "content": r['content']})
                history_data.append({"role": "user", "content": prompt})
                
                # AI 호출
                res, err = run_mental_gym(google_api_key, history_data)
                
                if err:
                    st.error(err)
                else:
                    if res.get("status") == "passed":
                        # 합격 -> 저장
                        reply = res.get("praise")
                        save_thought(res['concept'], res['explanation'], res['falsification'], res['tags'])
                        st.balloons()
                        st.success(f"✅ 훈련 완료! '{res['concept']}' 근육이 생성되었습니다.")
                        save_chat("assistant", reply)
                        message_placeholder.markdown(reply)
                        time.sleep(1); st.rerun() # 그래프 갱신
                    else:
                        # 불합격 -> 코칭 계속
                        reply = res.get("text")
                        save_chat("assistant", reply)
                        message_placeholder.markdown(reply)
        else:
            st.error("PT 이용권(API Key)이 없습니다.")

