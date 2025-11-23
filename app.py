import streamlit as st
import sqlite3
import datetime
import pandas as pd
import json
import urllib.request
import urllib.error
import time
import random
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
    # 채팅 로그 저장을 위한 테이블 추가
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
# [AI AGENT] The Librarian (사서)
# ==========================================
def analyze_and_archive(api_key, user_input):
    """
    유저의 채팅을 분석해서, 지식으로 저장할 가치가 있으면 JSON으로 추출함.
    """
    if not api_key: return None, "API Key가 없습니다."
    
    # 1. 일반 대화인지, 지식 입력인지 판단 & 추출
    # 시스템 프롬프트: 넌 지식 관리자야. 유저 말에서 개념/설명/반증/태그를 추출해.
    prompt = f"""
    You are an intelligent Knowledge Archivist.
    Analyze the user's input: "{user_input}"
    
    If the input contains a piece of knowledge or an idea worth saving, extract it into this JSON format:
    {{
        "is_knowledge": true,
        "concept": "Core topic (short)",
        "explanation": "Simple explanation (Feynman style)",
        "falsification": "Counter-argument or limitation (Popper style) - infer if not present",
        "tags": "3 keywords (Deutsch style)",
        "reply": "A brief, encouraging response to the user acknowledging the save."
    }}
    
    If it's just casual chat (hello, thanks, etc.), return this JSON:
    {{
        "is_knowledge": false,
        "reply": "Reply naturally to the conversation."
    }}
    
    Output ONLY the JSON string.
    """
    
    models = ["gemini-1.5-flash", "gemini-pro"]
    data = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode('utf-8')
    headers = {'Content-Type': 'application/json'}
    
    for model in models:
        try:
            req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}", data=data, headers=headers)
            with urllib.request.urlopen(req) as res:
                res_text = json.loads(res.read().decode('utf-8'))['candidates'][0]['content']['parts'][0]['text'].strip()
                # JSON 파싱 (마크다운 코드블록 제거)
                if "```json" in res_text:
                    res_text = res_text.split("```json")[1].split("```")[0]
                elif "```" in res_text:
                    res_text = res_text.split("```")[1].split("```")[0]
                return json.loads(res_text), None
        except Exception as e:
            continue
    return None, "AI 연결 실패"

# ==========================================
# [UI] Chat Interface
# ==========================================
st.set_page_config(page_title="FeynmanTic Chat", page_icon="💬", layout="centered") # 모바일 친화적 centered

# 사이드바 (설정)
with st.sidebar:
    st.title("⚙️ Settings")
    google_api_key = st.text_input("Google API Key", type="password")
    if st.button("🗑 대화 내용 초기화"):
        conn = sqlite3.connect('feynman.db', check_same_thread=False)
        conn.execute("DELETE FROM chat_logs")
        conn.commit()
        conn.close()
        st.rerun()
        
    st.divider()
    st.subheader("📚 최근 저장된 지식")
    recent = get_recent_thoughts()
    if not recent.empty:
        for _, row in recent.iterrows():
            st.caption(f"🔹 {row['concept']}")
            with st.popover("내용 보기"):
                st.write(f"**설명:** {row['explanation']}")
                st.write(f"**반증:** {row['falsification']}")
                st.write(f"**태그:** {row['tags']}")

# 메인 채팅 화면
st.title("🧠 FeynmanTic OS")
st.caption("Just talk. I'll organize your thoughts.")

# 1. 채팅 기록 표시
history = get_chat_history()
for _, row in history.iterrows():
    with st.chat_message(row['role']):
        st.write(row['content'])

# 2. 사용자 입력
if prompt := st.chat_input("생각나는 것을 자유롭게 말해보세요..."):
    # 유저 메시지 표시 및 저장
    with st.chat_message("user"):
        st.write(prompt)
    save_chat("user", prompt)
    
    # 3. AI 처리
    if google_api_key:
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            message_placeholder.markdown("Thinking...")
            
            # AI 분석
            result_json, error = analyze_and_archive(google_api_key, prompt)
            
            if error:
                response_text = f"⚠️ 오류: {error}"
            else:
                response_text = result_json.get("reply", "...")
                
                # 지식이면 DB 저장 액션 수행
                if result_json.get("is_knowledge"):
                    c = result_json.get("concept")
                    e = result_json.get("explanation")
                    f = result_json.get("falsification")
                    t = result_json.get("tags")
                    
                    save_thought(c, e, f, t)
                    
                    # 저장 확인 UI (채팅방 내에 카드처럼 표시)
                    st.success(f"💾 **지식 저장됨:** {c}")
                    with st.expander("저장된 내용 확인"):
                        st.markdown(f"**Feynman:** {e}")
                        st.markdown(f"**Popper:** {f}")
                        st.caption(f"#{t}")
            
            # AI 응답 표시 및 저장
            message_placeholder.markdown(response_text)
            save_chat("assistant", response_text)
    else:
        st.error("API 키를 먼저 입력해주세요.")
