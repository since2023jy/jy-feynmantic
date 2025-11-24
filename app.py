import streamlit as st
import google.generativeai as genai
import json
import time
import random

# -----------------------------------------------------------------------------
# 1. Config & Hacker CSS
# -----------------------------------------------------------------------------
st.set_page_config(page_title="FeynmanTic: Glitch Hunter", page_icon="👾", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=VT323&family=Noto+Sans+KR:wght@700&display=swap');
    
    body { background-color: #0d0d0d; color: #00ff41; font-family: 'VT323', monospace; }
    
    .hacker-title { font-size: 60px; text-align: center; text-shadow: 2px 2px #003b00; margin-bottom: 20px; }
    
    /* 카드 스타일 */
    .sector-card {
        border: 2px solid #333; padding: 20px; margin: 10px; border-radius: 10px;
        background: #000; transition: 0.3s; position: relative;
    }
    .status-black { border-color: #555; color: #555; }
    .status-grey { border-color: #ff00de; color: #ff00de; animation: glitch-border 2s infinite; }
    .status-light { border-color: #00ff41; color: #00ff41; box-shadow: 0 0 15px #00ff41; }
    
    /* 글리치 조각 (오답 아이템) */
    .shard-box {
        background: #222; border: 1px dashed #ff00de; padding: 10px; margin-top: 10px;
        color: #ff00de; text-align: center; cursor: pointer;
    }
    .shard-box:hover { background: #330033; }
    
    /* 키워드 칩 */
    .chip {
        display: inline-block; padding: 8px 16px; margin: 4px; border: 1px solid #00ff41;
        color: #00ff41; cursor: pointer; border-radius: 4px; font-size: 20px;
    }
    .chip:hover { background: #00ff41; color: #000; }
    .chip-selected { background: #00ff41; color: #000; }
    
    /* 애니메이션 */
    @keyframes glitch-border {
        0% { box-shadow: 0 0 5px #ff00de; }
        50% { box-shadow: 0 0 15px #ff00de, inset 0 0 10px #ff00de; }
        100% { box-shadow: 0 0 5px #ff00de; }
    }
    
    /* Vault UI */
    .vault-screen { background: #111; border: 4px double #00ff41; padding: 30px; border-radius: 20px; }
    
    /* Progress Bar Custom */
    .stProgress > div > div > div > div { background-color: #00ff41; }
</style>
""", unsafe_allow_html=True)

# API Setup
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel("gemini-1.5-flash", generation_config={"response_mime_type": "application/json"})
except:
    pass

# -----------------------------------------------------------------------------
# 2. State & Data Structure
# -----------------------------------------------------------------------------
if "sectors" not in st.session_state:
    st.session_state.sectors = {
        "Def": {"name": "01_DEFINITION", "desc": "본질 정의 프로토콜", "state": "BLACK", "hp": 100}, 
        "Ing": {"name": "02_INGREDIENTS", "desc": "재료 합성 프로토콜", "state": "BLACK", "hp": 100}, 
        "Imp": {"name": "03_IMPACT", "desc": "인과 분석 프로토콜", "state": "BLACK", "hp": 100},
    }

# [핵심] 오답노트 보물창고 (Glitch Vault)
if "glitch_shards" not in st.session_state: st.session_state.glitch_shards = [] 
# 예: {"sector": "Def", "wrong_keywords": ["물", "불"], "correct_needed": ["빛"], "timestamp": ...}

if "view" not in st.session_state: st.session_state.view = "MAP"
if "buffer" not in st.session_state: st.session_state.buffer = []
if "curr_sector" not in st.session_state: st.session_state.curr_sector = None

# [DATA]
KEYWORD_MAP = {
    "Def": {"pool": ["☀️빛", "🍬포도당", "🏭합성", "🔥연소", "🍖소화", "🚮분해"], "ans": {"☀️빛", "🍬포도당", "🏭합성"}},
    "Ing": {"pool": ["💧물", "💨CO2", "💡빛에너지", "🧂나트륨", "🪨암석", "⚡전기"], "ans": {"💧물", "💨CO2", "💡빛에너지"}},
    "Imp": {"pool": ["🌬️산소배출", "🍔유기물생산", "🌍생태계유지", "📉기온하강", "💀독소생성"], "ans": {"🌬️산소배출", "🍔유기물생산", "🌍생태계유지"}}
}

# -----------------------------------------------------------------------------
# 3. Logic Engine
# -----------------------------------------------------------------------------
def analyze_glitch(shard):
    # 오답 분석 시뮬레이션
    return f"분석 결과: '{shard['wrong'][0]}'은(는) 이 섹터의 구성요소가 아닙니다. 정답 회로에는 '{list(KEYWORD_MAP[shard['sector']]['ans'])[0]}' 등이 필요합니다."

# -----------------------------------------------------------------------------
# 4. View Controller
# -----------------------------------------------------------------------------

# [SIDEBAR: The Glitch Vault (보물창고)]
with st.sidebar:
    st.markdown("## 🎒 GLITCH VAULT")
    st.caption("실패 데이터(오답)를 분석하여 보상을 얻으세요.")
    
    if len(st.session_state.glitch_shards) > 0:
        st.write(f"수집된 파편: {len(st.session_state.glitch_shards)}개")
        for i, shard in enumerate(st.session_state.glitch_shards):
            with st.expander(f"💥 파편 #{i+1} [{shard['sector']}]"):
                st.write(f"입력값: {shard['wrong']}")
                if st.button("🔍 디코딩(분석)", key=f"decode_{i}"):
                    analysis = analyze_glitch(shard)
                    st.info(analysis)
                    st.toast("데이터 정제 완료! 경험치 획득!", icon="💾")
                    # 여기서 실제로는 힌트 아이템을 줌
    else:
        st.info("수집된 오답 파편이 없습니다.\n완벽한 것도 좋지만, 실패도 자산입니다.")

# [SCENE 1] Dashboard (Sector Map)
if st.session_state.view == "MAP":
    st.markdown("<div class='hacker-title'>GLITCH HUNTER</div>", unsafe_allow_html=True)
    
    # Global Status
    cols = st.columns(3)
    for sid, data in st.session_state.sectors.items():
        css = "status-black"
        icon = "🔒"
        
        if data['state'] == "GREY": css = "status-grey"; icon = "⚠️"
        elif data['state'] == "LIGHT": css = "status-light"; icon = "🌟"
        
        with cols[list(st.session_state.sectors.keys()).index(sid)]:
            st.markdown(f"""
            <div class='sector-card {css}'>
                <h3>{icon} {data['name']}</h3>
                <p>{data['desc']}</p>
                <div style='font-size:12px; text-align:right;'>STATUS: {data['state']}</div>
            </div>
            """, unsafe_allow_html=True)
            
            if data['state'] == "BLACK":
                if st.button(f"HACK_IN ({sid})", key=f"btn_{sid}", use_container_width=True):
                    # O/X 생략하고 바로 Link 데모로 진입 (빠른 진행 위해)
                    st.session_state.curr_sector = sid
                    st.session_state.sectors[sid]['state'] = "GREY" 
                    st.session_state.view = "LINK"
                    st.rerun()
            elif data['state'] == "GREY":
                 if st.button(f"DEBUG ({sid})", key=f"btn_{sid}", use_container_width=True):
                    st.session_state.curr_sector = sid
                    st.session_state.view = "LINK"
                    st.rerun()

# [SCENE 2] Neural Debugging (Link Game)
elif st.session_state.view == "LINK":
    sid = st.session_state.curr_sector
    sec = st.session_state.sectors[sid]
    pool = KEYWORD_MAP[sid]['pool']
    random.shuffle(pool) # 난이도 UP
    
    st.markdown(f"<h2 style='text-align:center; color:#ff00de'>⚠️ DEBUGGING: {sec['name']}</h2>", unsafe_allow_html=True)
    st.info("회로를 연결할 올바른 '코드 조각' 3개를 순서대로 삽입하십시오.")
    
    # 1. Circuit Board (Visual Display)
    st.markdown("### 🔌 CIRCUIT LINE")
    
    # 시각적 회로도 (CSS Line)
    circuit_html = "<div style='display:flex; align-items:center; justify-content:center; gap:10px; margin:20px 0;'>"
    circuit_html += "<div style='font-size:30px'>🔋START</div>"
    circuit_html += "<div style='width:50px; height:2px; background:#555;'></div>"
    
    for k in st.session_state.buffer:
        circuit_html += f"<div class='chip chip-selected'>{k}</div>"
        circuit_html += "<div style='width:30px; height:2px; background:#00ff41;'></div>"
        
    for _ in range(3 - len(st.session_state.buffer)):
        circuit_html += "<div style='width:60px; height:40px; border:2px dashed #555; border-radius:5px;'></div>"
        circuit_html += "<div style='width:30px; height:2px; background:#555;'></div>"
        
    circuit_html += "<div style='font-size:30px'>END💡</div></div>"
    st.markdown(circuit_html, unsafe_allow_html=True)
    
    # 2. Controls
    c1, c2 = st.columns([1, 4])
    with c1:
        if st.button("RESET"):
            st.session_state.buffer = []
            st.rerun()
    with c2:
        can_submit = len(st.session_state.buffer) == 3
        if st.button("COMPILE & RUN (실행)", type="primary", disabled=not can_submit, use_container_width=True):
            # 채점
            user_set = set(st.session_state.buffer)
            ans_set = KEYWORD_MAP[sid]['ans']
            
            if user_set == ans_set:
                st.balloons()
                st.success("시스템 정상화! 보안 레벨 상승 (LIGHT ZONE)")
                st.session_state.sectors[sid]['state'] = "LIGHT"
                time.sleep(2)
                st.session_state.buffer = []
                st.session_state.view = "MAP"
                st.rerun()
            else:
                # [여기가 핵심] 실패 시 오답노트(Glitch Shard) 생성
                st.error("치명적 오류! 합선 발생! (데이터 파편이 생성되었습니다)")
                
                # 틀린 데이터 수집
                shard_data = {
                    "sector": sid,
                    "wrong": list(user_set),
                    "timestamp": time.time()
                }
                st.session_state.glitch_shards.append(shard_data)
                
                # 강등 로직
                st.session_state.sectors[sid]['state'] = "BLACK"
                st.markdown("### 💥 CRITICAL FAILURE DETECTED")
                st.markdown("데이터 파편을 [GLITCH VAULT]에 보관했습니다. 분석하여 복구하십시오.")
                
                time.sleep(3)
                st.session_state.buffer = []
                st.session_state.view = "MAP"
                st.rerun()

    # 3. Code Fragments (Buttons)
    st.markdown("### 🧩 CODE FRAGMENTS")
    cols = st.columns(3)
    for i, word in enumerate(pool):
        with cols[i%3]:
            disabled = word in st.session_state.buffer or len(st.session_state.buffer) >= 3
            if st.button(word, key=f"frag_{i}", disabled=disabled, use_container_width=True):
                st.session_state.buffer.append(word)
                st.rerun()
