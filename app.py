import streamlit as st
import sqlite3
import datetime
import pandas as pd
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
    c.execute('''
        CREATE TABLE IF NOT EXISTS thoughts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            concept TEXT NOT NULL,
            explanation TEXT,
            falsification TEXT,
            tags TEXT,
            created_at TEXT,
            status TEXT DEFAULT 'active'
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS chat_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT,
            content TEXT,
            created_at TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_thought(concept, expl, fals, tags):
    conn = sqlite3.connect('feynman.db', check_same_thread=False)
    c = conn.cursor()
    created_at = dt.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute('''
        INSERT INTO thoughts (concept, explanation, falsification, tags, created_at, status)
        VALUES (?, ?, ?, ?, ?, 'active')
    ''', (concept, expl, fals, tags, created_at))
    conn.commit()
    conn.close()

def save_chat(role, content):
    conn = sqlite3.connect('feynman.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("INSERT INTO chat_logs (role, content, created_at) VALUES (?, ?, ?)", 
              (role, content, dt.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def get_chat_history():
    conn = sqlite3.connect('feynman.db', check_same_thread=False)
    df = pd.read_sql_query("SELECT * FROM chat_logs ORDER BY id ASC", conn)
    conn.close()
    return df

def get_recent_thoughts():
    conn = sqlite3.connect('feynman.db', check_same_thread=False)
    df = pd.read_sql_query("SELECT * FROM thoughts ORDER BY id DESC LIMIT 5", conn)
    conn.close()
    return df

init_db()

# ==========================================
# [AI AGENT] Debugged Version
# ==========================================
def analyze_and_archive(api_key, user_input):
    if not api_key: return None, "사이드바에 API Key를 먼저 입력해주세요."
    
    prompt = f"""
    You are an intelligent Knowledge Archivist.
    Analyze the user's input: "{user_input}"
    
    If it contains knowledge worth saving, extract it into this JSON:
    {{
        "is_knowledge": true,
        "concept": "Topic",
        "explanation": "Simple explanation",
        "falsification": "Limitation",
        "tags": "3 keywords",
        "reply": "Short confirmation."
    }}
    
    If it's casual chat, return this JSON:
    {{
        "is_knowledge": false,
        "reply": "Natural response."
    }}
    
    Output ONLY the JSON string.
    """
    
    # [FIX] 모델 리스트 최신화 (안정성 확보)
    models = ["gemini-1.5-flash", "gemini-1.5-flash-latest", "gemini-1.0-pro"]
    
    data = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode('utf-8')
    headers = {'Content-Type': 'application/json'}
    
    last_error = ""
    
    for model in models:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            req = urllib.request.Request(url, data=data, headers=headers)
            
            with urllib.request.urlopen(req) as res:
                res_text = json.loads(res.read().decode('utf-8'))['candidates'][0]['content']['parts'][0]['text'].strip()
                
                # JSON 정제 (마크다운 제거)
                clean_text = res_text.replace("```json", "").replace("```", "").strip()
                
                try:
                    return json.loads(clean_text), None
                except json.JSONDecodeError:
                    last_error = f"JSON 파싱 실패 (모델 응답이 이상함): {clean_text[:50]}..."
                    continue # 다음 모델 시도

        except urllib.error.HTTPError as e:
            last_error = f"HTTP Error {e.code}: {e.reason}"
            continue
        except Exception as e:
            last_error = f"System Error: {str(e)}"
            continue
            
    return None, f"AI 연결 실패 ({last_error})"

# ==========================================
# [UI] Chat Interface
# ==========================================
st.set_page_config(page_title="FeynmanTic Chat", page_icon="💬", layout="centered")

# 사이드바
with st.sidebar:
    st.title("⚙️ 설정")
    # [중요] 키 입력 강조
    google_api_key = st.text_input("Google API Key", type="password", placeholder="여기에 키를 입력하세요")
    if not google_api_key:
        st.warning("👈 여기에 키를 넣어야 작동합니다!")
        
    if st.button("🗑 대화 초기화"):
        conn = sqlite3.connect('feynman.db', check_same_thread=False)
        conn.execute("DELETE FROM chat_logs")
        conn.commit()
        conn.close()
        st.rerun()
        
    st.divider()
    st.caption("최근 지식")
    recent = get_recent_thoughts()
    if not recent.empty:
        for _, row in recent.iterrows():
            st.text(f"🔹 {row['concept']}")

# 메인
st.title("🧠 FeynmanTic OS")
st.caption("v12.1 Debug Edition")

# 기록
history = get_chat_history()
for _, row in history.iterrows():
    with st.chat_message(row['role']):
        st.write(row['content'])

# 입력
if prompt := st.chat_input("생각을 입력하세요..."):
    with st.chat_message("user"):
        st.write(prompt)
    save_chat("user", prompt)
    
    if google_api_key:
        with st.chat_message("assistant"):
            with st.spinner("Analyzing..."):
                result_json, error = analyze_and_archive(google_api_key, prompt)
                
                if error:
                    st.error(f"⚠️ {error}")
                    save_chat("assistant", f"Error: {error}")
                else:
                    reply = result_json.get("reply", "...")
                    st.write(reply)
                    save_chat("assistant", reply)
                    
                    if result_json.get("is_knowledge"):
                        c = result_json.get("concept")
                        e = result_json.get("explanation")
                        f = result_json.get("falsification")
                        t = result_json.get("tags")
                        save_thought(c, e, f, t)
                        st.toast(f"💾 지식 저장 완료: {c}", icon="✅")
                        with st.expander("저장된 카드 보기"):
                            st.info(e)
                            st.caption(f"반론: {f}")
    else:
        st.error("좌측 사이드바를 열어 API Key를 입력해주세요!")
