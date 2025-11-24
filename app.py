import streamlit as st
import time
import html
import random
from dataclasses import dataclass, field
from typing import List, Dict
import streamlit.components.v1 as components

# ==========================================
# 1. CONFIGURATION
# ==========================================
@dataclass(frozen=True)
class AppConfig:
    VERSION = "14.0.0 (Live Logic)"
    MAX_CHARS = 5000
    STORAGE_KEY = "feynman_v14_data"
    COLOR_RUTHLESS = "#ff4545"
    COLOR_ASSISTANT = "#00f2ff"
    BG_RUTHLESS = "radial-gradient(circle at 50% 0%, #450a0a 0%, #020617 60%, #000000 100%)"
    BG_ASSISTANT = "radial-gradient(circle at 50% 0%, #0e4a5a 0%, #020617 60%, #000000 100%)"

# ==========================================
# 2. LOGIC ENGINE (The Brain)
# ==========================================
class LogicEngine:
    """입력값을 분석하여 시각화 상태를 결정하는 가상의 뇌"""
    
    @staticmethod
    def analyze(text: str, mode: str) -> Dict:
        # 입력 텍스트 길이와 키워드에 따라 결과가 달라짐
        length = len(text)
        keywords = text.lower()
        
        result = {
            "score": min(length // 5, 100),  # 길이에 비례한 점수
            "stage": 1,
            "active_nodes": [],
            "stars": [],
            "feedback": ""
        }

        # 1. Student Mode Logic (Mario Map)
        if length > 100: result["stage"] = 3
        elif length > 50: result["stage"] = 2
        else: result["stage"] = 1

        # 2. Pro Mode Logic (Tech Tree)
        # 키워드에 따라 트리가 켜짐
        if "돈" in keywords or "money" in keywords or "매출" in keywords:
            result["active_nodes"].append("Sales")
        if "코딩" in keywords or "code" in keywords or "개발" in keywords:
            result["active_nodes"].append("Tech")
        if "사람" in keywords or "user" in keywords:
            result["active_nodes"].append("Product")
            
        # 3. Explorer Mode Logic (Galaxy)
        # 입력 길이만큼 별 생성
        num_stars = min(length // 10, 20)
        result["stars"] = [{"x": random.randint(10, 90), "y": random.randint(10, 90), "size": random.randint(2, 6)} for _ in range(num_stars)]

        # 4. Feedback Generation
        if mode == "ruthless":
            if length < 20: result["feedback"] = "논리가 빈약합니다. 더 구체적으로 서술하십시오."
            else: result["feedback"] = "가설이 검증되었습니다. 논리적 구조가 견고합니다."
        else:
            if length < 20: result["feedback"] = "좋은 시작이에요! 조금 더 자세히 적어볼까요?"
            else: result["feedback"] = "아주 훌륭한 생각입니다! 명확하게 정리되었어요."
            
        return result

# ==========================================
# 3. SYSTEM SETUP
# ==========================================
st.set_page_config(
    page_title="FeynmanTic",
    page_icon="💠",
    layout="centered",
    initial_sidebar_state="collapsed",
    menu_items={'About': f"v{AppConfig.VERSION}"}
)

def init_state():
    defaults = {
        'entropy_state': 'CHAOS',
        'is_hardcore': st.query_params.get("mode") == "ruthless",
        'feedback': "AWAITING INPUT...",
        'input_text': "",
        'analysis_result': {  # [New] 분석 결과 저장소
            "stage": 1, 
            "active_nodes": [], 
            "stars": [], 
            "score": 0 
        },
        'student_level': 'High School',
        'is_spectator': False
    }
    for k, v in defaults.items():
        if k not in st.session_state: st.session_state[k] = v

init_state()

# ==========================================
# 4. DYNAMIC CSS GENERATOR
# ==========================================
def get_css(is_hardcore: bool, result: Dict) -> str:
    primary = AppConfig.COLOR_RUTHLESS if is_hardcore else AppConfig.COLOR_ASSISTANT
    bg = AppConfig.BG_RUTHLESS if is_hardcore else AppConfig.BG_ASSISTANT
    
    # [Dynamic] Mario Map Styling based on Stage
    stage = result.get("stage", 1)
    node_1_bg = primary if stage >= 1 else "rgba(255,255,255,0.1)"
    node_2_bg = primary if stage >= 2 else "rgba(255,255,255,0.1)"
    node_3_bg = primary if stage >= 3 else "rgba(255,255,255,0.1)"
    
    # [Dynamic] Tech Tree Styling
    active_nodes = result.get("active_nodes", [])
    sales_border = primary if "Sales" in active_nodes else "rgba(255,255,255,0.2)"
    tech_border = primary if "Tech" in active_nodes else "rgba(255,255,255,0.2)"
    prod_border = primary if "Product" in active_nodes else "rgba(255,255,255,0.2)"

    return f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Inter:wght@300;400;600&display=swap');
    :root {{ --primary: {primary}; --bg-gradient: {bg}; }}
    
    html, body {{ background-color: #000000 !important; overscroll-behavior: none; }}
    .stApp {{ background: var(--bg-gradient); background-attachment: fixed; min-height: 100dvh; }}
    #MainMenu, header, footer, div[data-testid="stDecoration"] {{ display: none !important; }}

    /* Mario Map Nodes */
    .node-1 {{ background: {node_1_bg}; box-shadow: 0 0 15px {node_1_bg}; }}
    .node-2 {{ background: {node_2_bg}; box-shadow: 0 0 15px {node_2_bg}; }}
    .node-3 {{ background: {node_3_bg}; box-shadow: 0 0 15px {node_3_bg}; }}
    
    /* Tech Tree Nodes */
    .tree-sales {{ border-color: {sales_border} !important; color: {sales_border} !important; }}
    .tree-tech {{ border-color: {tech_border} !important; color: {tech_border} !important; }}
    .tree-prod {{ border-color: {prod_border} !important; color: {prod_border} !important; }}

    /* Common UI */
    h1, h2, .mono {{ font-family: 'JetBrains Mono', monospace !important; }}
    p, textarea, button, div {{ font-family: 'Inter', sans-serif !important; }}
    
    .stTextArea textarea {{
        background-color: rgba(20, 20, 20, 0.4) !important; color: #fff !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important; border-radius: 16px;
        backdrop-filter: blur(20px); padding: 1.5rem; font-size: 16px; resize: none; min-height: 140px;
        caret-color: var(--primary); transition: all 0.3s ease;
    }}
    .stTextArea textarea:focus {{ border-color: var(--primary) !important; box-shadow: 0 0 30px rgba({primary}, 0.2) !important; }}

    div.stButton > button {{
        width: 100%; height: 56px; border-radius: 14px; background: linear-gradient(180deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0) 100%);
        border: 1px solid rgba(255,255,255,0.1); color: var(--primary); font-family: 'JetBrains Mono', monospace !important; font-weight: 700;
        transition: all 0.2s; margin-top: 10px;
    }}
    div.stButton > button:hover {{ border-color: var(--primary); transform: translateY(-2px); }}

    .hud-box {{
        background: rgba(10, 10, 10, 0.6); border: 1px solid rgba(255,255,255,0.08); border-left: 3px solid var(--primary);
        padding: 1rem 1.5rem; border-radius: 12px; color: var(--primary); font-family: 'JetBrains Mono';
        backdrop-filter: blur(15px); min-height: 60px; display: flex; align-items: center; gap: 12px;
    }}
    
    .map-container {{ display: flex; justify-content: space-between; position: relative; padding: 20px; margin-top: 20px; }}
    .map-line {{ position: absolute; top: 50%; left: 10%; width: 80%; height: 2px; background: rgba(255,255,255,0.1); z-index: 0; }}
    .map-circle {{ width: 40px; height: 40px; border-radius: 50%; border: 2px solid rgba(255,255,255,0.2); display: flex; align-items: center; justify-content: center; z-index: 1; transition: all 0.5s; color: white; font-weight: bold; }}

    .spectator-overlay {{
        position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.9); z-index: 9999;
        display: flex; flex-direction: column; align-items: center; justify-content: center; color: var(--primary); font-family: 'JetBrains Mono';
    }}
    
    .block-container {{ padding-top: 3rem; padding-bottom: 5rem; max-width: 680px; }}
    </style>
    """

st.markdown(get_css(st.session_state.is_hardcore, st.session_state.analysis_result), unsafe_allow_html=True)

# ==========================================
# 5. LOGIC HANDLERS
# ==========================================
def handle_analyze():
    text = st.session_state.input_text.strip()
    if not text: return
    
    st.session_state.entropy_state = 'PROCESSING'
    
    # [Logic] 여기서 텍스트를 분석해서 시각화 데이터를 만듭니다
    mode = "ruthless" if st.session_state.is_hardcore else "assistant"
    result = LogicEngine.analyze(text, mode)
    
    # 결과 저장 (세션에 저장되어야 리런 후에도 반영됨)
    st.session_state.analysis_result = result
    st.session_state.feedback = result["feedback"]

def handle_reset():
    st.session_state.entropy_state = 'CHAOS'
    st.session_state.input_text = ""
    st.session_state.feedback = "SYSTEM RESET."
    st.session_state.analysis_result = {"stage": 1, "active_nodes": [], "stars": [], "score": 0}

def apply_cheat():
    # 컨닝 모드: 랜덤한 '있어 보이는' 문장 자동 입력
    cheats = [
        "돈을 벌기 위해 매출 파이프라인을 구조화해야 한다.",
        "사용자 경험을 위해 리액트 네이티브 코드를 최적화한다.",
        "엔트로피 감소를 위해 불필요한 프로세스를 제거한다."
    ]
    st.session_state.input_text = random.choice(cheats)

# ==========================================
# 6. UI COMPONENTS
# ==========================================

# Header
c1, c2 = st.columns([6, 4])
with c1:
    color = AppConfig.COLOR_RUTHLESS if st.session_state.is_hardcore else AppConfig.COLOR_ASSISTANT
    st.markdown(f"<div class='mono' style='font-weight:900; font-size:1.5rem;'>FEYNMANTIC<span style='color:{color}; font-size:0.6em; margin-left:4px;'>OS v14</span></div>", unsafe_allow_html=True)
with c2:
    c2_1, c2_2 = st.columns(2)
    with c2_1:
        if st.button("👁️", help="관전 모드 (Spectator)"): st.session_state.is_spectator = not st.session_state.is_spectator
    with c2_2:
        btn_text = "🔥" if st.session_state.is_hardcore else "💎"
        if st.button(btn_text, help="모드 전환"):
            st.session_state.is_hardcore = not st.session_state.is_hardcore
            st.query_params["mode"] = "ruthless" if st.session_state.is_hardcore else "assistant"
            st.rerun()

st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

# Spectator Overlay
if st.session_state.is_spectator:
    st.markdown(f"""
    <div class="spectator-overlay">
        <div style="font-size:4rem; animation:pulse 2s infinite;">👁️</div>
        <div style="margin-top:20px; letter-spacing:2px;">SPECTATOR MODE</div>
        <div style="font-size:0.8rem; opacity:0.6; margin-top:10px;">Watching Neural Activity...</div>
        <div style="margin-top:30px; color:white; font-size:0.8rem;">User-8291: "Quantum Mechanics..."</div>
    </div>
    <style>@keyframes pulse {{ 0% {{opacity:0.3}} 50% {{opacity:1}} 100% {{opacity:0.3}} }}</style>
    """, unsafe_allow_html=True)

# Status Area
status_area = st.empty()
if st.session_state.entropy_state == 'CHAOS':
    with status_area.container():
        st.markdown(f"""<div class="hud-box"><span style="animation:blink 1s infinite">_</span> {st.session_state.feedback}</div>""", unsafe_allow_html=True)
elif st.session_state.entropy_state == 'PROCESSING':
    loader = st.empty()
    color = AppConfig.COLOR_RUTHLESS if st.session_state.is_hardcore else AppConfig.COLOR_ASSISTANT
    for i in range(31):
        loader.markdown(f"""<div style="background:rgba(0,0,0,0.9); padding:20px 40px; border-radius:50px; border:1px solid {color}50; position:fixed; top:50%; left:50%; transform:translate(-50%,-50%); z-index:9999;"><span class='mono' style='color:white;'>ANALYZING... {int(i*3.33)}%</span></div>""", unsafe_allow_html=True)
        time.sleep(0.02)
    st.session_state.entropy_state = 'CRYSTAL'
    st.rerun()
elif st.session_state.entropy_state == 'CRYSTAL':
    with status_area.container():
        st.markdown(f"""<div class="hud-box" style="border-color:#10b981; color:#10b981;"><span>✓</span> {st.session_state.feedback}</div>""", unsafe_allow_html=True)

# --- TABS: Dynamic Visualizations ---
t1, t2, t3 = st.tabs(["🎓 STUDENT", "💼 PRO", "🚀 EXPLORER"])

# 1. Student Tab (Mario Map)
with t1:
    cols = st.columns([2, 1])
    with cols[0]: st.caption("ACADEMIC ROADMAP")
    with cols[1]: st.selectbox("Grade", ["Elementary", "Middle", "High", "Univ"], label_visibility="collapsed")
    
    # 입력 길이에 따라 node class가 바뀜 (CSS 연동)
    st.markdown(f"""
    <div class="map-container">
        <div class="map-line"></div>
        <div class="map-circle node-1">1</div>
        <div class="map-circle node-2">2</div>
        <div class="map-circle node-3">3</div>
    </div>
    <div style="text-align:center; font-size:0.8rem; opacity:0.6; margin-top:10px;">
        Current Stage: {st.session_state.analysis_result['stage']} / 3
    </div>
    """, unsafe_allow_html=True)

# 2. Pro Tab (Tech Tree)
with t2:
    st.caption("PROJECT DEPENDENCIES")
    # 키워드에 따라 border class가 바뀜
    st.markdown(f"""
    <div style="display:flex; justify-content:center; gap:20px; margin-top:20px;">
        <div style="padding:10px 20px; border:1px solid rgba(255,255,255,0.2); border-radius:8px; text-align:center;" class="tree-prod">
            <div style="font-size:1.2rem;">📦</div><div style="font-size:0.8rem;">Product</div>
        </div>
        <div style="padding:10px 20px; border:1px solid rgba(255,255,255,0.2); border-radius:8px; text-align:center;" class="tree-sales">
            <div style="font-size:1.2rem;">💰</div><div style="font-size:0.8rem;">Sales</div>
        </div>
        <div style="padding:10px 20px; border:1px solid rgba(255,255,255,0.2); border-radius:8px; text-align:center;" class="tree-tech">
            <div style="font-size:1.2rem;">💻</div><div style="font-size:0.8rem;">Tech</div>
        </div>
    </div>
    <div style="text-align:center; margin-top:15px; font-size:0.8rem; color:#666;">
        Tip: Try typing 'money', 'code', or 'user'
    </div>
    """, unsafe_allow_html=True)

# 3. Explorer Tab (Galaxy)
with t3:
    st.caption("IDEA CONSTELLATION")
    # 입력 길이에 따라 별(점)이 생성됨
    stars_html = ""
    for star in st.session_state.analysis_result['stars']:
        stars_html += f'<div style="position:absolute; top:{star["y"]}%; left:{star["x"]}%; width:{star["size"]}px; height:{star["size"]}px; background:white; border-radius:50%; box-shadow:0 0 5px white;"></div>'
    
    st.markdown(f"""
    <div style="position:relative; width:100%; height:200px; background:rgba(0,0,0,0.3); border-radius:10px; overflow:hidden; margin-top:10px;">
        {stars_html}
        <div style="position:absolute; top:50%; left:50%; transform:translate(-50%,-50%); width:50px; height:50px; border:1px solid var(--primary); border-radius:50%; animation:pulse 2s infinite;"></div>
    </div>
    <style>@keyframes pulse {{ 0% {{box-shadow:0 0 0 0 var(--primary);}} 70% {{box-shadow:0 0 0 20px rgba(0,0,0,0);}} 100% {{box-shadow:0 0 0 0 rgba(0,0,0,0);}} }}</style>
    """, unsafe_allow_html=True)

st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

# Input Area
c_input, c_cheat = st.columns([8, 1])
with c_input:
    st.text_area(
        "Input",
        key="input_text",
        placeholder="Type your thoughts...",
        height=140,
        label_visibility="collapsed",
        disabled=st.session_state.entropy_state == 'PROCESSING'
    )
with c_cheat:
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    if st.button("🦊", help="Cunning Mode (Auto-Fill)"):
        apply_cheat()
        st.rerun()

# Buttons
if st.session_state.entropy_state == 'CRYSTAL':
    if st.button("⚡ RESET SYSTEM", type="primary"):
        handle_reset()
        st.rerun()
else:
    if st.button("🚀 EXECUTE", disabled=st.session_state.entropy_state == 'PROCESSING', type="primary"):
        handle_analyze()
        st.rerun()

# JS Bridge (유지)
components.html(f"""
<script>
    const STORAGE_KEY = '{AppConfig.STORAGE_KEY}';
    const textArea = parent.document.querySelector('textarea');
    const buttons = parent.document.querySelectorAll('button');
    let executeBtn = null;
    buttons.forEach(b => {{ if(b.innerText.includes("EXECUTE")) executeBtn = b; }});

    if(textArea && !textArea.dataset.bound) {{
        textArea.dataset.bound = "true";
        textArea.addEventListener('input', () => {{
            try {{ localStorage.setItem(STORAGE_KEY, textArea.value); }} catch(e){{}}
        }});
        try {{
            const saved = localStorage.getItem(STORAGE_KEY);
            if(saved && textArea.value === "") {{
                const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value").set;
                setter.call(textArea, saved);
                textArea.dispatchEvent(new Event('input', {{ bubbles: true }}));
            }}
        }} catch(e){{}}
        const isMobile = ('ontouchstart' in window) && (window.innerWidth < 768);
        textArea.addEventListener('keydown', (e) => {{
            if(e.key === 'Enter' && !e.shiftKey && !e.isComposing) {{
                if(!isMobile && executeBtn && !executeBtn.disabled) {{
                    e.preventDefault();
                    executeBtn.click();
                }}
            }}
        }});
    }}
    if(executeBtn) executeBtn.onclick = () => {{ if(document.activeElement) document.activeElement.blur(); }};
    if(textArea && textArea.value === "") try {{ localStorage.removeItem(STORAGE_KEY); }} catch(e){{}}
</script>
""", height=0, width=0)
