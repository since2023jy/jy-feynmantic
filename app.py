import streamlit as st
import json
import random
import time
# (Gemini API는 이 환경에서 직접 연동되지 않으므로, 로직 판정은 로컬에서 시뮬레이션됩니다.)

# -----------------------------------------------------------------------------
# 1. Config & CSS (Syntax Error Fixed)
# -----------------------------------------------------------------------------
st.set_page_config(layout="wide", page_title="FeynmanTic Glitch Hunter")

st.markdown("""
<style>
    /* 1. 기본 스타일 */
    .stApp { background-color: #0d0d0d; color: #00ff41; font-family: monospace; }
    .stButton>button { 
        border: 2px solid #00ff41; background: #111; color: #00ff41; 
        transition: 0.2s; /* 쫀득함 추가 */
    }
    .stButton>button:hover { background: #00ff41; color: #000; box-shadow: 0 0 10px #00ff41; }

    /* 2. 섹터 카드 스타일 */
    .sector-card {
        padding: 20px; border-radius: 10px; margin-bottom: 15px; 
        border-left: 5px solid; 
        transition: 0.5s;
    }
    .state-BLACK { border-color: #555; color: #666; background: #1a1a1a; }
    .state-GREY { border-color: #ff00de; color: #ff00de; background: #221122; box-shadow: 0 0 15px rgba(255, 0, 222, 0.4); }
    .state-LIGHT { border-color: #ffd700; color: #ffd700; background: #222010; box-shadow: 0 0 15px rgba(255, 215, 0, 0.4); }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. State & Data Structure
# -----------------------------------------------------------------------------
if "sectors" not in st.session_state:
    st.session_state.sectors = {
        "Def": {"name": "01_정의 프로토콜", "desc": "광합성의 본질적 정의", "state": "BLACK"}, # BLACK -> GREY -> LIGHT
        "Ing": {"name": "02_재료 프로토콜", "desc": "필요 요소 3가지", "state": "BLACK"},
        "Imp": {"name": "03_인과 프로토콜", "desc": "생명 유지의 영향력", "state": "BLACK"},
    }
if "view" not in st.session_state: st.session_state.view = "MAP"
if "buffer" not in st.session_state: st.session_state.buffer = [] 
if "curr_sector" not in st.session_state: st.session_state.curr_sector = None
if "glitch_shards" not in st.session_state: st.session_state.glitch_shards = [] 
if "feedback_msg" not in st.session_state: st.session_state.feedback_msg = "시스템 온라인."

# [핵심 로직 데이터] 한국어 키워드로 변경 및 통일
KEYWORD_MAP = {
    "Def": {"pool": ["빛에너지", "포도당", "합성", "연소", "소화", "흙"], "ans": {"빛에너지", "포도당", "합성"}},
    "Ing": {"pool": ["물", "이산화탄소", "빛", "소금", "전기", "바람"], "ans": {"물", "이산화탄소", "빛"}},
    "Imp": {"pool": ["산소", "호흡", "생태계", "수면", "독소", "자동차"], "ans": {"산소", "호흡", "생태계"}}
}

# -----------------------------------------------------------------------------
# 3. Logic Functions
# -----------------------------------------------------------------------------

def go_map():
    """맵 화면으로 돌아가며 버퍼를 비웁니다."""
    st.session_state.view = "MAP"
    st.session_state.buffer = []
    st.session_state.curr_sector = None

def start_debug(sid):
    """디버깅(키워드 연결) 화면으로 진입합니다."""
    st.session_state.curr_sector = sid
    st.session_state.view = "LINK"
    st.session_state.buffer = []

def select_chip(word):
    """키워드 칩을 선택 버퍼에 추가합니다."""
    if len(st.session_state.buffer) < 3 and word not in st.session_state.buffer:
        st.session_state.buffer.append(word)

def remove_chip(word):
    """키워드 칩을 선택 버퍼에서 제거합니다."""
    if word in st.session_state.buffer:
        st.session_state.buffer.remove(word)

def compile_logic():
    """핵심 로직: 키워드 연결 결과를 판정합니다."""
    sid = st.session_state.curr_sector
    user_set = set(st.session_state.buffer)
    ans_set = KEYWORD_MAP[sid]['ans']
    
    match_count = len(user_set.intersection(ans_set))
    
    # 0.5초 딜레이 (UI 깜빡임 연출)
    time.sleep(0.5)

    if match_count == 3:
        # 성공: GREY -> LIGHT
        st.session_state.sectors[sid]['state'] = "LIGHT"
        st.session_state.feedback_msg = f"✅ 시스템 복구 완료! ({st.session_state.sectors[sid]['name']})"
        st.balloons()
        go_map()
    else:
        # 실패: GREY -> BLACK (루프 발생)
        # 1. 오답 파편 생성
        wrong_answers = list(user_set - ans_set)
        if wrong_answers:
             st.session_state.glitch_shards.append({
                "sector": sid,
                "wrong": wrong_answers,
                "reason": f"{match_count}/3개 일치. 입력값: {', '.join(wrong_answers)}가 잘못됨.",
                "timestamp": time.time()
            })
        
        # 2. 강등 및 피드백 (다음 리로드 때 출력)
        st.session_state.sectors[sid]['state'] = "BLACK"
        st.session_state.feedback_msg = f"💥 FATAL ERROR! 데이터 붕괴. (오답 파편 획득!)"
        go_map()


def init_sector_action(sid):
    """맵에서 섹터를 클릭했을 때의 액션 (O/X 단계를 생략하고 바로 GREY로 만듦)"""
    state = st.session_state.sectors[sid]['state']
    if state == "BLACK":
        st.session_state.sectors[sid]['state'] = "GREY"
        st.session_state.feedback_msg = f"⚡ {st.session_state.sectors[sid]['name']} 활성화! (UNSTABLE)"
    elif state == "GREY":
        start_debug(sid)
    st.rerun() # 상태가 바뀌었으므로 리렌더링

# -----------------------------------------------------------------------------
# 4. UI Rendering
# -----------------------------------------------------------------------------

st.header("GLITCH HUNTER v1.1 (Final Prototype)")
st.caption(st.session_state.feedback_msg)
st.markdown("---")


# --- 사이드바 (Glitch Vault) ---
with st.sidebar:
    st.header("🎒 GLITCH VAULT")
    
    if st.session_state.glitch_shards:
        st.info(f"수집된 오답 파편: {len(st.session_state.glitch_shards)}개")
        for i, shard in enumerate(st.session_state.glitch_shards):
            with st.expander(f"💥 파편 #{i+1} [{shard['sector']}]"):
                st.write(f"입력 오류: {', '.join(shard['wrong'])}")
                st.caption(f"시스템 로그: {shard['reason']}")
    else:
        st.info("수집된 오답 파편이 없습니다.")


# --- Scene: MAP ---
if st.session_state.view == "MAP":
    st.subheader("🗺️ NEURAL MAP STATUS")
    
    cols = st.columns(3)
    keys = list(st.session_state.sectors.keys())
    
    for i, sid in enumerate(keys):
        data = st.session_state.sectors[sid]
        
        status_color = "black"
        status_label = "LOCKED"
        
        if data['state'] == "GREY": status_color = "pink"; status_label = "UNSTABLE"
        elif data['state'] == "LIGHT": status_color = "gold"; status_label = "SECURE"
        
        with cols[i]:
            # CSS를 활용한 섹터 카드 디자인
            st.markdown(f"""
            <div class='sector-card state-{data['state']}'>
                <h3 style='margin:0; font-size:18px;'>{data['name']}</h3>
                <p style='font-size:12px; margin-top:5px; color:{status_color};'>[{status_label}]</p>
            </div>
            """, unsafe_allow_html=True)
            
            # 액션 버튼
            btn_label = "⚡ STABILIZE" if data['state'] == "GREY" else "🔓 ACTIVATE"
            btn_disabled = data['state'] == "LIGHT"
            
            # 상태 변경 로직을 on_click에 연결
            if st.button(btn_label, key=f"action_{sid}", disabled=btn_disabled, use_container_width=True, on_click=init_sector_action, args=(sid,)):
                pass


# --- Scene: LINK GAME (핵심 루프) ---
elif st.session_state.view == "LINK":
    sid = st.session_state.curr_sector
    data = st.session_state.sectors[sid]
    pool = KEYWORD_MAP[sid]['pool']
    random.shuffle(pool) 
    
    st.subheader(f"🔗 DEBUG: {data['name']}")
    st.warning("경고: 올바른 핵심 키워드 3개를 연결해야 합니다. 실패 시 초기화됩니다.")
    
    # 1. 조합 슬롯 시각화
    st.markdown("### 🛠️ 논리 회로 슬롯")
    slot_html = "<div style='display:flex; gap:10px;'>"
    
    for i in range(3):
        item = st.session_state.buffer[i] if i < len(st.session_state.buffer) else "EMPTY"
        color = "#00ff41" if item != "EMPTY" else "#444"
        slot_html += f"<div style='flex:1; padding:10px; border:2px dashed {color}; text-align:center; color:{color}; font-size:14px;'>{item}</div>"
    
    slot_html += "</div>"
    st.markdown(slot_html, unsafe_allow_html=True)
    st.markdown("---")

    # 2. 키워드 선택 풀
    st.subheader("🧩 사용 가능한 키워드 (클릭하여 슬롯에 삽입)")
    cols = st.columns(3)
    for i, word in enumerate(pool):
        with cols[i % 3]:
            is_selected = word in st.session_state.buffer
            
            if is_selected:
                # 선택된 키워드는 제거 버튼으로 작동
                if st.button(word, key=f"chip_{i}", use_container_width=True, on_click=remove_chip, args=(word,)):
                    pass
            else:
                # 미선택 키워드는 추가 버튼으로 작동
                if st.button(word, key=f"chip_{i}", use_container_width=True, disabled=len(st.session_state.buffer) >= 3, on_click=select_chip, args=(word,)):
                    pass

    st.markdown("---")
    
    # 3. 실행 및 복귀 버튼
    can_compile = len(st.session_state.buffer) == 3
    
    st.button("🔥 COMPILE & RUN", disabled=not can_compile, on_click=compile_logic, use_container_width=True)
    st.button("🔙 MAP으로 돌아가기", on_click=go_map, use_container_width=True)

