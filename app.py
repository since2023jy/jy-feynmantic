<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>GLITCH HUNTER: PROTOCOL</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Black+Ops+One&family=Share+Tech+Mono&display=swap');

        :root {
            --neon-green: #00ff41;
            --neon-pink: #ff00de;
            --dark-bg: #050505;
            --glass: rgba(20, 20, 20, 0.9);
        }

        body {
            background-color: var(--dark-bg);
            color: var(--neon-green);
            font-family: 'Share Tech Mono', monospace;
            margin: 0;
            padding: 20px;
            overflow: hidden; /* 스크롤 방지 */
            height: 100vh;
            /* 배경 그리드 효과 */
            background-image: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.25) 50%), linear-gradient(90deg, rgba(255, 0, 0, 0.06), rgba(0, 255, 0, 0.02), rgba(0, 0, 255, 0.06));
            background-size: 100% 2px, 3px 100%;
            user-select: none; /* 텍스트 선택 방지 (게임 느낌) */
            -webkit-tap-highlight-color: transparent; /* 모바일 터치 하이라이트 제거 */
        }

        /* CRT Scanline Effect */
        body::after {
            content: " ";
            display: block;
            position: absolute;
            top: 0; left: 0; bottom: 0; right: 0;
            background: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.1) 50%), linear-gradient(90deg, rgba(255, 0, 0, 0.06), rgba(0, 255, 0, 0.02), rgba(0, 0, 255, 0.06));
            z-index: 2;
            background-size: 100% 2px, 3px 100%;
            pointer-events: none;
        }

        h1 {
            font-family: 'Black Ops One', cursive;
            text-align: center;
            font-size: 40px;
            margin-bottom: 20px;
            text-shadow: 2px 2px 0px var(--neon-pink);
            animation: glitch 1s infinite alternate;
        }

        /* Screen Container */
        #game-screen {
            max-width: 500px;
            margin: 0 auto;
            position: relative;
            z-index: 10;
        }

        /* Sector Cards */
        .card {
            background: var(--glass);
            border: 1px solid #333;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 15px;
            transition: 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.275); /* 쫀득한 텐션 */
            cursor: pointer;
            position: relative;
        }

        .card:active { transform: scale(0.95); } /* 누르는 느낌 */

        .status-badge {
            position: absolute; top: 10px; right: 10px;
            font-size: 10px; padding: 3px 8px; border-radius: 4px;
            font-weight: bold; color: #000;
        }

        /* States */
        .black { border-color: #555; color: #777; }
        .black .status-badge { background: #555; color: #fff; }
        
        .grey { 
            border-color: var(--neon-pink); color: var(--neon-pink); 
            box-shadow: 0 0 10px var(--neon-pink);
            animation: shake 2s infinite; /* ⚠️ 불안정하게 흔들림 */
        }
        .grey .status-badge { background: var(--neon-pink); }

        .light { 
            border-color: #ffd700; color: #ffd700; 
            box-shadow: 0 0 15px #ffd700;
        }
        .light .status-badge { background: #ffd700; }

        /* Link Game UI */
        .slot-container {
            display: flex; gap: 10px; justify-content: center; margin: 30px 0;
            min-height: 60px;
        }

        .slot {
            width: 80px; height: 50px;
            border: 2px dashed #444;
            display: flex; align-items: center; justify-content: center;
            font-size: 14px; color: #fff;
            transition: 0.3s;
        }

        .chip {
            background: #000; border: 1px solid var(--neon-green); color: var(--neon-green);
            padding: 10px; margin: 5px; display: inline-block;
            cursor: pointer; border-radius: 5px;
            transition: 0.1s;
        }
        .chip:active { background: var(--neon-green); color: #000; transform: scale(0.9); }
        .chip.used { opacity: 0.3; pointer-events: none; border-style: dashed; }

        .filled-slot {
            background: var(--neon-green); color: #000; border: none;
            font-weight: bold; animation: popIn 0.3s;
        }

        .btn-action {
            width: 100%; padding: 15px; font-family: inherit; font-size: 20px; font-weight: bold;
            background: #000; color: var(--neon-green); border: 2px solid var(--neon-green);
            cursor: pointer; margin-top: 20px;
            transition: 0.2s;
        }
        .btn-action:active { background: var(--neon-green); color: #000; }
        .btn-action:disabled { border-color: #333; color: #333; pointer-events: none; }

        /* Animations */
        @keyframes glitch { 0% { transform: skew(0deg); } 20% { transform: skew(-2deg); } 100% { transform: skew(0deg); } }
        @keyframes shake { 0%, 100% { transform: translate(0); } 10% { transform: translate(-1px, 1px); } }
        @keyframes popIn { 0% { transform: scale(0); } 80% { transform: scale(1.2); } 100% { transform: scale(1); } }
        @keyframes flashRed { 0% { background: rgba(255,0,0,0.5); } 100% { background: transparent; } }

        .hidden { display: none; }
        .damage-flash { animation: flashRed 0.5s; }

    </style>
</head>
<body>

    <div id="game-screen">
        <div id="scene-map">
            <h1>GLITCH HUNTER</h1>
            <div id="sectors-list">
                </div>
        </div>

        <div id="scene-link" class="hidden">
            <button onclick="goMap()" style="background:none; border:none; color:#555; cursor:pointer;">&lt; BACK TO MAP</button>
            <h2 id="link-title" style="text-align:center; color:var(--neon-pink); animation:glitch 0.5s infinite;">DEBUG MODE</h2>
            <p style="text-align:center; font-size:12px;">CORE MODULES REQUIRED: 3</p>

            <div class="slot-container" id="slots">
                <div class="slot">EMPTY</div>
                <div class="slot">EMPTY</div>
                <div class="slot">EMPTY</div>
            </div>

            <div id="chip-pool" style="text-align:center;">
                </div>

            <button id="btn-exec" class="action-btn" disabled onclick="executeLink()">COMPILE & RUN</button>
            <div id="feedback-msg" style="text-align:center; margin-top:10px; height:20px; font-weight:bold;"></div>
        </div>
    </div>

    <script>
        // Game State (서버 없이 로컬에서 즉시 구동)
        const sectors = {
            "Def": { name: "PROTOCOL: DEFINE", desc: "광합성의 본질적 정의", state: "BLACK", ans: ["빛에너지", "포도당", "합성"] },
            "Ing": { name: "PROTOCOL: INGREDIENT", desc: "필요 재료 3요소", state: "BLACK", ans: ["물", "이산화탄소", "빛"] },
            "Imp": { name: "PROTOCOL: IMPACT", desc: "생명 유지 인과성", state: "BLACK", ans: ["산소", "호흡", "생태계"] }
        };

        const keywordPool = {
            "Def": ["빛에너지", "포도당", "합성", "소화", "불", "흙"],
            "Ing": ["물", "이산화탄소", "빛", "소금", "전기", "바람"],
            "Imp": ["산소", "호흡", "생태계", "수면", "온도", "독소"]
        };

        let currentSectorId = null;
        let buffer = [];

        // --- View Logic (No Reload) ---

        function renderMap() {
            const list = document.getElementById('sectors-list');
            list.innerHTML = '';
            
            for (let id in sectors) {
                const s = sectors[id];
                const el = document.createElement('div');
                let cssClass = s.state.toLowerCase();
                let badgeText = s.state === "BLACK" ? "LOCKED" : (s.state === "GREY" ? "UNSTABLE" : "SECURE");
                
                el.className = `card ${cssClass}`;
                el.innerHTML = `
                    <div class="status-badge">${badgeText}</div>
                    <h3>${s.name}</h3>
                    <p style="margin:0; font-size:12px; opacity:0.7">${s.desc}</p>
                `;

                // Interaction Event
                el.onclick = () => {
                    if (s.state === "BLACK") {
                        // O/X 게임 생략, 바로 해킹 연출
                        s.state = "GREY";
                        renderMap();
                        if(navigator.vibrate) navigator.vibrate(50); // Haptic
                    } else if (s.state === "GREY") {
                        startLinkGame(id);
                    }
                };
                list.appendChild(el);
            }
        }

        function goMap() {
            document.getElementById('scene-map').classList.remove('hidden');
            document.getElementById('scene-link').classList.add('hidden');
            renderMap();
        }

        function startLinkGame(id) {
            currentSectorId = id;
            buffer = [];
            document.getElementById('scene-map').classList.add('hidden');
            document.getElementById('scene-link').classList.remove('hidden');
            document.getElementById('link-title').innerText = `DEBUG: ${sectors[id].name}`;
            renderLinkUI();
        }

        function renderLinkUI() {
            const slotContainer = document.getElementById('slots');
            const chipContainer = document.getElementById('chip-pool');
            const btnExec = document.getElementById('btn-exec');
            const msg = document.getElementById('feedback-msg');

            msg.innerText = ""; // 메시지 초기화

            // Render Slots
            slotContainer.innerHTML = '';
            for (let i = 0; i < 3; i++) {
                const el = document.createElement('div');
                if (buffer[i]) {
                    el.className = 'slot filled-slot';
                    el.innerText = buffer[i];
                    el.onclick = () => { removeChip(i); }; // Click to remove
                } else {
                    el.className = 'slot';
                    el.innerText = 'EMPTY';
                }
                slotContainer.appendChild(el);
            }

            // Render Chips
            chipContainer.innerHTML = '';
            const pool = keywordPool[currentSectorId];
            pool.forEach(word => {
                const el = document.createElement('div');
                el.className = `chip ${buffer.includes(word) ? 'used' : ''}`;
                el.innerText = word;
                el.onclick = () => { addChip(word); };
                chipContainer.appendChild(el);
            });

            btnExec.disabled = buffer.length !== 3;
            btnExec.style.opacity = buffer.length === 3 ? "1" : "0.5";
        }

        function addChip(word) {
            if (buffer.length < 3 && !buffer.includes(word)) {
                buffer.push(word);
                if(navigator.vibrate) navigator.vibrate(10); // Light haptic
                renderLinkUI();
            }
        }

        function removeChip(index) {
            buffer.splice(index, 1);
            renderLinkUI();
        }

        function executeLink() {
            const correctAns = sectors[currentSectorId].ans;
            // 로직 판정 (집합 비교)
            const isCorrect = correctAns.every(val => buffer.includes(val));
            const msg = document.getElementById('feedback-msg');

            if (isCorrect) {
                // 성공 연출
                msg.innerText = "SYSTEM RESTORED // ACCESS GRANTED";
                msg.style.color = "#00ff41";
                sectors[currentSectorId].state = "LIGHT";
                if(navigator.vibrate) navigator.vibrate([50, 50, 50]); 
                setTimeout(goMap, 1500);
            } else {
                // 실패 연출 (글리치)
                msg.innerText = "FATAL ERROR // GLITCH DETECTED";
                msg.style.color = "#ff00de";
                sectors[currentSectorId].state = "BLACK"; // 강등
                document.body.classList.add('damage-flash');
                if(navigator.vibrate) navigator.vibrate(500); 
                setTimeout(() => document.body.classList.remove('damage-flash'), 500);
                setTimeout(goMap, 1500);
            }
        }

        // 초기 실행
        renderMap();

    </script>
</body>
</html>
