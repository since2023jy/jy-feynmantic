'use client';

import React, { useState, useRef, useEffect, useLayoutEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Brain, Rocket, Map, GitMerge, Stars, Zap, ShieldAlert, CheckCircle, Lock, CloudOff, BatteryCharging } from 'lucide-react';

type ViewMode = 'STUDENT' | 'PRO' | 'EXPLORER';
type EntropyState = 'CHAOS' | 'PROCESSING' | 'CRYSTAL';

interface ModeBtnProps {
  label: string;
  icon: React.ReactNode;
  active: boolean;
  onClick: () => void;
  hardcore: boolean;
}

export default function FeynmanTicApp() {
  const [viewMode, setViewMode] = useState<ViewMode>('STUDENT');
  const [input, setInput] = useState('');
  const [entropyState, setEntropyState] = useState<EntropyState>('CHAOS');
  const [feedback, setFeedback] = useState('사고의 엔트로피가 높습니다.');
  const [isHardcore, setIsHardcore] = useState(false);
  const [isStorageAvailable, setIsStorageAvailable] = useState(true);
  const [isVisible, setIsVisible] = useState(true);

  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const safeLocalStorage = {
    getItem: (key: string) => { try { return localStorage.getItem(key); } catch (e) { return null; } },
    setItem: (key: string, value: string) => { try { localStorage.setItem(key, value); } catch (e) { setIsStorageAvailable(false); } },
    removeItem: (key: string) => { try { localStorage.removeItem(key); } catch (e) { /* Ignore */ } }
  };

  useEffect(() => {
    const savedThought = safeLocalStorage.getItem('feynman_draft');
    if (savedThought) setInput(savedThought);

    const savedMode = safeLocalStorage.getItem('feynman_mode');
    if (savedMode === 'ruthless') {
        setIsHardcore(true);
        setFeedback('논리를 증명하십시오.');
    }
    
    document.body.style.overscrollBehavior = 'none';

    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'feynman_draft' && e.newValue !== null) {
        setInput(e.newValue);
        adjustHeight();
      }
      if (e.key === 'feynman_mode') {
        const newMode = e.newValue === 'ruthless';
        setIsHardcore(newMode);
        setFeedback(newMode ? 'Ruthless Mode Activated' : 'Assistant Mode');
      }
    };

    const handleVisibilityChange = () => setIsVisible(document.visibilityState === 'visible');

    window.addEventListener('storage', handleStorageChange);
    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      document.body.style.overscrollBehavior = 'auto';
      window.removeEventListener('storage', handleStorageChange);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  const adjustHeight = () => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`;
    }
  };

  useLayoutEffect(() => adjustHeight(), [input]);

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const val = e.target.value;
    setInput(val);
    requestAnimationFrame(() => safeLocalStorage.setItem('feynman_draft', val));
    if (entropyState === 'CRYSTAL') {
        setEntropyState('CHAOS');
        setFeedback(isHardcore ? '완벽해질 때까지 수정하십시오.' : '생각을 다듬고 계시군요.');
    }
  };

  const toggleHardcoreMode = () => {
    const nextMode = !isHardcore;
    setIsHardcore(nextMode);
    safeLocalStorage.setItem('feynman_mode', nextMode ? 'ruthless' : 'assistant');
    if (timerRef.current) { clearTimeout(timerRef.current); timerRef.current = null; }
    setEntropyState('CHAOS');
    setFeedback(nextMode ? '감당할 수 있겠습니까?' : '편하게 말씀하세요.');
    setTimeout(() => textareaRef.current?.focus(), 10);
  };

  const handleAnalyze = () => {
    if (!input.replace(/\s/g, '').length || entropyState === 'PROCESSING') return;
    if (timerRef.current) clearTimeout(timerRef.current);

    setEntropyState('PROCESSING');
    setFeedback("Processing Logic...");

    const dynamicDelay = Math.min(Math.max(input.length * 20, 1500), 4000);

    timerRef.current = setTimeout(() => {
      setEntropyState('CRYSTAL');
      setFeedback(isHardcore ? "결정체 획득. 논리가 견고합니다." : "아주 명확하게 정리되었습니다!");
      timerRef.current = null;
    }, dynamicDelay);
  };

  const reset = () => {
    if (timerRef.current) { clearTimeout(timerRef.current); timerRef.current = null; }
    setEntropyState('CHAOS');
    setInput('');
    safeLocalStorage.removeItem('feynman_draft'); 
    setFeedback(isHardcore ? '다음 논리를 가져오십시오.' : '새로운 생각을 입력하세요.');
    const isTouchDevice = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
    if (!isTouchDevice) setTimeout(() => textareaRef.current?.focus(), 10);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault(); 
      if (e.nativeEvent.isComposing) return;
      if (entropyState === 'CRYSTAL') { reset(); return; }
      handleAnalyze();
    }
  };

  return (
    <div className="min-h-[100dvh] text-white flex flex-col overflow-hidden relative">
      
      {/* [Design Fix 1] 배경 레이어 크로스페이드 (부드러운 전환) */}
      <div className={`absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-indigo-900 via-slate-900 to-black transition-opacity duration-1000 ${isHardcore ? 'opacity-0' : 'opacity-100'}`} />
      <div className={`absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-slate-900 via-red-950 to-black transition-opacity duration-1000 ${isHardcore ? 'opacity-100' : 'opacity-0'}`} />
      <div className="absolute inset-0 pointer-events-none bg-[radial-gradient(circle_at_center,transparent_0%,rgba(0,0,0,0.4)_100%)] z-0" />

      {/* Header */}
      <header className="p-6 flex justify-between items-center border-b border-white/5 bg-white/5 backdrop-blur-md select-none relative z-50 shrink-0">
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg bg-white/5 border border-white/10 transition-all duration-700 ${isHardcore ? "shadow-[0_0_20px_rgba(220,38,38,0.4)]" : "shadow-[0_0_20px_rgba(34,211,238,0.4)]"}`}>
             <Brain className={`w-5 h-5 transition-colors duration-700 ${isHardcore ? "text-red-500" : "text-cyan-400"}`} />
          </div>
          <h1 className="text-lg font-bold tracking-[0.2em] font-mono text-white/90">
            FEYNMANTIC
          </h1>
        </div>
        
        <div className="flex items-center gap-3 cursor-pointer group" onClick={toggleHardcoreMode}>
            {!isStorageAvailable && <CloudOff size={14} className="text-yellow-500 animate-pulse" />}
            {!isVisible && <BatteryCharging size={14} className="text-green-500" />}
            
            <div className="relative flex items-center bg-black/40 rounded-full p-1 border border-white/10 shadow-inner">
                <span className={`text-[10px] font-bold px-2 transition-colors duration-500 ${!isHardcore ? 'text-cyan-400' : 'text-white/20'}`}>AST</span>
                <div className={`w-8 h-4 rounded-full shadow-inner transition-colors duration-500 ${isHardcore ? 'bg-red-900/50' : 'bg-cyan-900/50'}`}>
                    <motion.div 
                        className={`w-4 h-4 rounded-full shadow-md ${isHardcore ? 'bg-red-500' : 'bg-cyan-400'}`}
                        animate={{ x: isHardcore ? 16 : 0 }}
                        transition={{ type: "spring", stiffness: 500, damping: 30 }}
                    />
                </div>
                <span className={`text-[10px] font-bold px-2 transition-colors duration-500 ${isHardcore ? 'text-red-500' : 'text-white/20'}`}>RTH</span>
            </div>
        </div>
      </header>

      <main className="container mx-auto p-4 max-w-4xl flex-1 flex flex-col justify-between relative z-10">
        
        {/* Visual Engine */}
        {isVisible && (
            <div className="flex-1 flex flex-col items-center justify-center relative min-h-[250px] pointer-events-none">
                <AnimatePresence mode='wait'>
                    {entropyState === 'CHAOS' && (
                        <motion.div 
                            key="chaos"
                            initial={{ opacity: 0, scale: 0.9 }}
                            animate={{ scale: [1, 1.1, 0.95], opacity: [0.4, 0.6, 0.4] }}
                            exit={{ opacity: 0, scale: 0 }}
                            transition={{ repeat: Infinity, duration: 5, ease: "easeInOut" }}
                            className={`w-80 h-80 rounded-full absolute blur-[90px] transition-colors duration-1000 ${isHardcore ? 'bg-red-600/30' : 'bg-cyan-600/30'}`}
                        />
                    )}
                    {entropyState === 'PROCESSING' && (
                         <div className="relative">
                            <motion.div 
                                animate={{ rotate: 360 }}
                                transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                                className={`w-24 h-24 rounded-full border border-dashed ${isHardcore ? 'border-red-500/50' : 'border-cyan-400/50'}`}
                            />
                            <motion.div 
                                animate={{ rotate: -360 }}
                                transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
                                className={`absolute inset-2 rounded-full border border-dotted ${isHardcore ? 'border-red-500/30' : 'border-cyan-400/30'}`}
                            />
                         </div>
                    )}
                    {entropyState === 'CRYSTAL' && (
                        <motion.div 
                            key="crystal"
                            initial={{ scale: 0, rotate: -45, opacity: 0 }}
                            animate={{ scale: 1, rotate: 0, opacity: 1 }}
                            transition={{ type: "spring", stiffness: 200, damping: 15 }}
                            className="relative z-10"
                        >
                            <div className={`w-32 h-32 rotate-45 flex items-center justify-center backdrop-blur-xl border border-white/20 shadow-[0_0_50px_rgba(255,255,255,0.1)] ${isHardcore ? 'bg-red-500/10' : 'bg-cyan-500/10'}`}>
                                <CheckCircle className={`w-12 h-12 ${isHardcore ? 'text-red-400' : 'text-cyan-400'}`} />
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
                
                {/* [Design Fix 2] 살아 숨쉬는 텍스트 애니메이션 */}
                <div className="mt-12 h-8 relative overflow-hidden flex items-center justify-center">
                    <AnimatePresence mode='wait'>
                        <motion.div 
                            key={feedback}
                            initial={{ y: 20, opacity: 0 }}
                            animate={{ y: 0, opacity: 1 }}
                            exit={{ y: -20, opacity: 0 }}
                            transition={{ duration: 0.3 }}
                            className={`px-6 py-2 rounded-full backdrop-blur-md border border-white/10 shadow-lg text-sm font-mono tracking-wide ${isHardcore ? 'bg-red-950/30 text-red-100 border-red-500/20' : 'bg-indigo-950/30 text-cyan-100 border-cyan-500/20'}`}
                        >
                            {feedback}
                        </motion.div>
                    </AnimatePresence>
                </div>
            </div>
        )}

        <div className="flex justify-center gap-4 mb-6 z-10 shrink-0">
            <ModeBtn label="Student" icon={<Map size={14} />} active={viewMode === 'STUDENT'} onClick={() => setViewMode('STUDENT')} hardcore={isHardcore}/>
            <ModeBtn label="Pro" icon={<GitMerge size={14} />} active={viewMode === 'PRO'} onClick={() => setViewMode('PRO')} hardcore={isHardcore}/>
            <ModeBtn label="Explorer" icon={<Stars size={14} />} active={viewMode === 'EXPLORER'} onClick={() => setViewMode('EXPLORER')} hardcore={isHardcore}/>
        </div>

        <div className="bg-white/5 backdrop-blur-sm rounded-2xl p-6 h-48 sm:h-64 border border-white/10 relative overflow-hidden mb-6 shadow-inner z-0 shrink-0 transition-colors duration-700 group">
            <div className="absolute inset-0 bg-gradient-to-b from-transparent to-black/40 pointer-events-none" />
            {viewMode === 'STUDENT' && <StudentView unlocked={entropyState === 'CRYSTAL'} />}
            {viewMode === 'PRO' && <ProView warning={isHardcore && entropyState === 'CHAOS'} />}
            {viewMode === 'EXPLORER' && <ExplorerView connected={entropyState === 'CRYSTAL'} hardcore={isHardcore} />}
        </div>

        <div className="relative w-full max-w-2xl mx-auto mb-0 pb-[calc(env(safe-area-inset-bottom)+1.5rem)] z-20 shrink-0 group">
            {/* [Design Fix 3] 반응형 빛(Glow) - focus-within일 때 빛이 더 강해짐 */}
            <div className={`absolute -inset-0.5 rounded-3xl blur opacity-20 group-focus-within:opacity-50 transition-opacity duration-700 ${isHardcore ? 'bg-red-500' : 'bg-cyan-400'}`} />
            
            <textarea 
                ref={textareaRef} 
                value={input}
                autoFocus 
                rows={1}
                onChange={handleInputChange} 
                disabled={entropyState === 'PROCESSING'}
                placeholder={isHardcore ? "논리를 증명하십시오..." : "생각을 입력하세요."}
                className={`relative w-full bg-black/40 backdrop-blur-xl border border-white/10 rounded-3xl py-4 px-6 pr-14 text-[16px] text-white placeholder-white/30 focus:outline-none shadow-2xl tracking-wide transition-all duration-700 resize-none overflow-hidden ${isHardcore ? 'focus:border-red-500/50' : 'focus:border-cyan-400/50'}`}
                onKeyDown={handleKeyDown}
                style={{ minHeight: '60px' }}
            />
            <button 
                onClick={entropyState === 'CRYSTAL' ? reset : handleAnalyze}
                disabled={(!input.replace(/\s/g, '').length && entropyState !== 'CRYSTAL')}
                className={`absolute right-3 top-3 p-2.5 rounded-full transition-all duration-300 disabled:opacity-30 disabled:cursor-not-allowed ${
                    entropyState === 'CRYSTAL' 
                    ? 'bg-green-500 hover:bg-green-400 text-black shadow-[0_0_15px_rgba(34,197,94,0.6)]' 
                    : isHardcore ? 'bg-red-600 hover:bg-red-500 text-white shadow-[0_0_15px_rgba(220,38,38,0.4)]' : 'bg-cyan-600 hover:bg-cyan-500 text-white shadow-[0_0_15px_rgba(8,145,178,0.4)]'
                }`}
            >
                {entropyState === 'CRYSTAL' ? <Zap size={20} fill="currentColor" /> : <Rocket size={20} />}
            </button>
        </div>

      </main>
    </div>
  );
}

function ModeBtn({ label, icon, active, onClick, hardcore }: any) {
    return (
        <button 
            onClick={onClick}
            className={`flex items-center gap-2 px-5 py-2.5 rounded-full text-xs font-bold tracking-wider uppercase transition-all duration-300 border ${
                active 
                ? `bg-white text-black border-white shadow-[0_0_20px_rgba(255,255,255,0.3)] scale-105` 
                : `bg-transparent text-white/40 border-transparent hover:bg-white/5 hover:text-white`
            }`}
        >
            {icon} {label}
        </button>
    )
}

function StudentView({ unlocked }: any) {
    return (
        <div className="flex items-center justify-around h-full select-none">
            <div className="flex flex-col items-center">
                <div className="w-12 h-12 bg-green-500 rounded-xl flex items-center justify-center mb-2 shadow-[0_0_15px_rgba(34,197,94,0.5)] text-black font-black text-lg">1</div>
            </div>
            <div className={`h-1 flex-1 mx-4 rounded-full ${unlocked ? 'bg-green-500/50' : 'bg-white/10'}`} />
            <div className={`w-16 h-16 rounded-2xl flex items-center justify-center border transition-all duration-500 ${unlocked ? 'bg-white/10 border-white/50 text-white shadow-[0_0_30px_rgba(255,255,255,0.2)]' : 'bg-white/5 border-white/5 text-white/20'}`}>
                {unlocked ? <span className="font-bold text-xl">2</span> : <Lock size={20}/>}
            </div>
            <div className="h-1 flex-1 mx-4 bg-white/10 rounded-full" />
            <div className="w-12 h-12 border border-white/5 rounded-xl flex items-center justify-center text-white/10">3</div>
        </div>
    )
}

function ProView({ warning }: any) {
    return (
        <div className="flex flex-col items-center justify-center h-full gap-6 select-none opacity-80">
            <div className="px-4 py-2 bg-white/5 rounded border border-white/10 text-xs font-mono">STRATEGY</div>
            <div className="w-px h-8 bg-gradient-to-b from-white/20 to-transparent" />
             <div className="flex gap-8">
                <div className={`px-4 py-2 rounded border text-xs font-mono transition-all ${warning ? 'bg-red-500/10 border-red-500/50 text-red-200' : 'bg-white/5 border-white/10 text-white/40'}`}>
                    {warning ? 'LOGIC ERROR' : 'MARKET'}
                </div>
                <div className="px-4 py-2 bg-white/5 rounded border border-white/10 text-xs font-mono text-white/40">TECH</div>
            </div>
        </div>
    )
}

function ExplorerView({ connected, hardcore }: any) {
    return (
        <div className="h-full w-full relative opacity-80">
             <div className="absolute top-1/4 left-1/4 w-1 h-1 bg-white rounded-full shadow-[0_0_10px_white]" />
             <div className={`absolute top-1/2 left-1/2 w-3 h-3 rounded-full shadow-[0_0_20px_currentColor] z-10 ${hardcore ? 'bg-red-500 text-red-500' : 'bg-cyan-400 text-cyan-400'}`} />
             
             <svg className="absolute inset-0 w-full h-full pointer-events-none">
                 {connected && (
                    <motion.line 
                        x1="25%" y1="25%" x2="50%" y2="50%" 
                        stroke="rgba(255,255,255,0.1)" strokeWidth="1"
                        initial={{ pathLength: 0 }} animate={{ pathLength: 1 }}
                    />
                 )}
             </svg>
        </div>
    )
}
