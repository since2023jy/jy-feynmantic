import streamlit as st
import time
import html
import re
import streamlit.components.v1 as components
from dataclasses import dataclass

# ==========================================
# 1. CONFIG & CONSTANTS
# ==========================================
@dataclass(frozen=True)
class AppConfig:
    VERSION = "15.0.0 (Middle School Edition)"
    MAX_CHARS = 3000
    STORAGE_KEY = "feynman_v15_middle"
    # 중학생용 컬러: 활기차고 게임 같은 느낌
    COLOR_THEME = "#fbbf24" # Amber (Coin Color)
    COLOR_ACCENT = "#ef4444" # Mario Red
    BG_GRADIENT = "linear-gradient(180deg, #2dd4bf 0%, #0f172a 100%)" # Sky to Dark

st.set_page_config(
    page_title="FeynmanTic: Logic Adventure",
    page_icon="🎮",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ==========================================
# 2. LOGIC ENGINE (Middle School Logic)
# ==========================================
class MiddleSchoolEngine:
    """중학생 논리 구조 분석 엔진"""
    
    @staticmethod
    def analyze(text: str):
        # 1. 기본 데이터
        clean_text = text.strip()
        length = len(clean_text)
        sentences = re.split(r'[.?!]\s*', clean_text)
        sentences = [s for s in sentences if s] # 빈 문장 제거
        
        # 2. 논리 키워드 탐지
        has_reason = any(w in clean_text for w in ["왜냐하면", "때문", "이유는"])
        has_example = any(w in clean_text for w in ["예를", "예시", "가령", "비유"])
        has_concl = any(w in clean_text for w in ["따라서", "결론", "요약", "그러므로", "결국"])
        
        # 3. 스테이지 판정 (Game Logic)
        # Stage 0: 시작 전
        # Stage 1: 주장 (글자수 20자 이상)
        # Stage 2: 근거 (이유 관련 접속사 포함)
        # Stage 3: 예시 (예시 관련 접속사 포함)
        # Stage 4: 완결 (결론 포함 + 충분한 길이)
        
        stage = 0
        feedback = "생각의 모험을 떠나볼까요? 주제를 적어보세요!"
        progress = 0
        
        if length > 20:
            stage = 1
            progress = 25
            feedback = "좋아요! 주장이 시작됐어요. 왜 그렇게 생각하나요? ('왜냐하면'을 써보세요)"
            
            if has_reason:
                stage = 2
                progress = 50
                feedback = "근거가 생겼네요! 이해를 돕기 위한 예시가 있나요? ('예를 들어'를 써보세요)"
                
                if has_example:
                    stage = 3
                    progress = 75
                    feedback = "훌륭한 예시입니다! 이제 결론을 지어볼까요? ('따라서'를 써보세요)"
                    
                    if has_concl and length > 100:
                        stage = 4
                        progress = 100
                        feedback = "🎉 완벽한 논리입니다! 스테이지 클리어!"

        return {
            "stage": stage,
            "progress": progress,
            "feedback": feedback,
            "has_reason": has_reason,
            "has_example": has_example,
            "has_concl": has_concl
        }

# ==========================================
# 3. STATE MANAGEMENT
# ==========================================
if 'analysis' not in st.session_state:
    st.session_state.analysis = MiddleSchoolEngine.analyze("")
if 'input_text' not in st.session_state:
    st.session_state.input_text = ""

# ==========================================
# 4. VISUAL SYSTEM (Mario Map CSS)
# ==========================================
def render_css(stage):
    # 스테이지별 캐릭터 위치 계산 (0% ~ 90%)
    mario_pos = f"{min(stage * 23, 90)}%"
    
    # 스테이지별 활성화 컬러
    s1_color = "#fbbf24" if stage >= 1 else "#ffffff50"
    s2_color = "#fbbf24" if stage >= 2 else "#ffffff50"
    s3_color = "#fbbf24" if stage >= 3 else "#ffffff50"
    s4_color = "#fbbf24" if stage >= 4 else "#ffffff50"

    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Black+Han+Sans&family=Noto+Sans+KR:wght@400;700&display=swap');
    
    /* 배경 & 기본 폰트 */
    .stApp {{ background: {AppConfig.BG_GRADIENT}; background-attachment: fixed; }}
    html, body, p, div, textarea {{ font-family: 'Noto Sans KR', sans-serif !important; }}
    h1, h2, .game-font {{ font-family: 'Black Han Sans', sans-serif !important; letter-spacing: 1px; }}
    
    /* UI 숨김 */
    #MainMenu, header, footer {{ display: none !important; }}
    
    /* [Visual] The Mario Map Container */
    .map-container {{
        position: relative; width: 100%; height: 120px; 
        background: rgba(0,0,0,0.3); border-radius: 20px; 
        margin-top: 20px; padding: 20px;
        border: 4px solid #4ade80; /* Ground Color */
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        overflow: hidden;
    }}
    
    /* The Path Lines */
    .path-line {{
        position: absolute; top: 60px; left: 10%; width: 80%; height: 4px; 
        background: rgba(255,255,255,0.2); z-index: 0;
    }}
    
    /* Nodes (Stages) */
    .node {{
        position: absolute; top: 45px; width: 30px; height: 30px; 
        border-radius: 50%; background: #333; border: 3px solid #fff;
        z-index: 1; display: flex; align-items: center; justify-content: center;
        font-size: 12px; font-weight: bold; color: white;
        transition: all 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    }}
    .node.active {{ background: #ef4444; border-color: #fbbf24; transform: scale(1.2); box-shadow: 0 0 15px #fbbf24; }}
    
    /* Labels */
    .node-label {{
        position: absolute; top: 80px; font-size: 12px; color: white; 
        text-shadow: 0 2px 4px rgba(0,0,0,0.8); width: 60px; text-align: center;
        transform: translateX(-15px); font-family: 'Black Han Sans';
    }}

    /* The Player (Mario) */
    .player {{
        position: absolute; top: 25px; left: {mario_pos}; 
        font-size: 40px; z-index: 10;
        transition: left 0.8s cubic-bezier(0.68, -0.55, 0.265, 1.55);
        filter: drop-shadow(0 5px 5px rgba(0,0,0,0.5));
        animation: bounce 1s infinite alternate;
    }}
    @keyframes bounce {{ from {{ transform: translateY(0); }} to {{ transform: translateY(-5px); }} }}

    /* Input Area (Game Panel) */
    .stTextArea textarea {{
        background-color: rgba(255, 255, 255, 0.9) !important;
        color: #333 !important;
        border: 4px solid #3b82f6 !important;
        border-radius: 15px !important;
        font-size: 18px !important; line-height: 1.6 !important;
        padding: 20px !important; min-height: 200px !important;
        box-shadow: inset 0 5px 10px rgba(0,0,0,0.1);
    }}
    .stTextArea textarea:focus {{ border-color: #fbbf24 !important; }}

    /* Feedback Box (NPC Dialogue) */
    .npc-box {{
        background: white; border: 4px solid #333; border-radius: 15px;
        padding: 15px 20px; margin-bottom: 20px; position: relative;
        box-shadow: 5px 5px 0px rgba(0,0,0,0.2);
        display: flex; align-items: center; gap: 15px;
    }}
    .npc-box::after {{
        content: ""; position: absolute; bottom: -10px; left: 30px;
        border-width: 10px 10px 0; border-style: solid;
        border-color: #333 transparent; display: block; width: 0;
    }}
    
    .check-badge {{
        background: #22c55e; color: white; padding: 2px 8px; border-radius: 10px; font-size: 10px; margin-right: 5px;
    }}
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 5. LOGIC HANDLER
# ==========================================
def on_text_change():
    text = st.session_state.input_text
    st.session_state.analysis = MiddleSchoolEngine.analyze(text)

# CSS 적용 (State 기반)
render_css(st.session_state.analysis['stage'])

# ==========================================
# 6. MAIN UI
# ==========================================

# Title Area
col1, col2 = st.columns([1, 4])
with col1:
    st.markdown("<div style='font-size:40px;'>🍄</div>", unsafe_allow_html=True)
with col2:
    st.markdown("<h1 style='color:white; text-shadow: 3px 3px 0 #000;'>논리 어드벤처</h1>", unsafe_allow_html=True)
    st.markdown("<div style='color:#fbbf24; font-weight:bold;'>Level: 중학교 1학년</div>", unsafe_allow_html=True)

# 1. NPC Feedback Area
feedback = st.session_state.analysis['feedback']
st.markdown(f"""
<div class="npc-box">
    <div style="font-size:30px;">🧙‍♂️</div>
    <div style="color:#333; font-weight:bold;">{feedback}</div>
</div>
""", unsafe_allow_html=True)

# 2. The Visual Map (Mario Style)
# 노드 상태 계산
s = st.session_state.analysis['stage']
c1 = "active" if s >= 1 else ""
c2 = "active" if s >= 2 else ""
c3 = "active" if s >= 3 else ""
c4 = "active" if s >= 4 else ""

# 아바타 선택 (스테이지별로 변신)
avatar = "🚶"
if s == 1: avatar = "🏃"
if s == 2: avatar = "🧗"
if s == 3: avatar = "🚴"
if s == 4: avatar = "🦸"

st.markdown(f"""
<div class="map-container">
    <div class="path-line"></div>
    
    <div class="node {c1}" style="left:10%;">1</div>
    <div class="node-label" style="left:10%;">주장</div>
    
    <div class="node {c2}" style="left:35%;">2</div>
    <div class="node-label" style="left:35%;">근거</div>
    
    <div class="node {c3}" style="left:60%;">3</div>
    <div class="node-label" style="left:60%;">예시</div>
    
    <div class="node {c4}" style="left:85%;">🏁</div>
    <div class="node-label" style="left:85%;">결론</div>
    
    <div class="player">{avatar}</div>
</div>
""", unsafe_allow_html=True)

# 3. Logic Check (Sub-goals)
cols = st.columns(3)
res = st.session_state.analysis
with cols[0]:
    if res['has_reason']: st.markdown("✅ **근거** 확보")
    else: st.markdown("⬜ **근거** ('왜냐하면')")
with cols[1]:
    if res['has_example']: st.markdown("✅ **예시** 확보")
    else: st.markdown("⬜ **예시** ('예를 들어')")
with cols[2]:
    if res['has_concl']: st.markdown("✅ **결론** 확보")
    else: st.markdown("⬜ **결론** ('따라서')")

st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

# 4. Input Area (실시간 반응형)
st.text_area(
    "Input",
    key="input_text",
    placeholder="여기에 글을 쓰면 캐릭터가 움직여요!",
    height=250,
    label_visibility="collapsed",
    on_change=on_text_change
)

# 5. Cheat Button (힌트)
if st.button("💡 힌트 보기 (자동 완성)"):
    st.session_state.input_text = "나는 학교 급식을 개선해야 한다고 생각한다. 왜냐하면 맛있는 밥은 학생들의 행복이기 때문이다. 예를 들어, 수요일마다 나오는 스파게티는 모두가 좋아한다. 따라서 급식 메뉴에 학생들의 의견을 더 반영해야 한다."
    on_text_change()
    st.rerun()

# JS: Auto-Save & Enter Logic
components.html("""
<script>
    const textArea = parent.document.querySelector('textarea');
    if (textArea) {
        // Auto-Save Logic
        textArea.addEventListener('input', function() {
            localStorage.setItem('feynman_v15_middle', textArea.value);
        });
        
        // Restore Logic
        const saved = localStorage.getItem('feynman_v15_middle');
        if (saved && textArea.value === "") {
            const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value").set;
            nativeInputValueSetter.call(textArea, saved);
            textArea.dispatchEvent(new Event('input', { bubbles: true }));
        }
    }
</script>
""", height=0)
