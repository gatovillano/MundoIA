"use client";

import React, { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import useGameStore from "@/store/useGameStore";
import { getHttpUrl } from "@/utils/apiConfig";
import { Play, Pause, RefreshCw, LogOut, Map as MapIcon, Share2, Zap, Brain, Users, Box, ChevronDown, Clock, Activity, BarChart3, Terminal, X, Flag, CircleDashed, Star, Sun, CloudRain, Landmark, MessageCircle } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

import WorldViewport from "@/components/WorldViewport";
import WorldViewport3D from "@/components/WorldViewport3D";
import NetworkView from "@/components/NetworkView";
import ArchitectPanel from "@/components/ArchitectPanel";
import AgentSidebar from "@/components/AgentSidebar";
import FactionsPanel from "@/components/FactionsPanel";
import InstructionOverlay from "@/components/InstructionOverlay";
import DivineFX from "@/components/DivineFX";
import MissionsPanel from "@/components/MissionsPanel";
import MissionCelebration from "@/components/MissionCelebration";
import SocietyChronicle from "@/components/SocietyChronicle";
import ConfigPanel from "@/components/ConfigPanel";
import InstitutionsPanel from "@/components/InstitutionsPanel";
import MainSidebar from "@/components/MainSidebar";
import UnifiedPanel from "@/components/UnifiedPanel";
import PossessionPanel from "@/components/PossessionPanel";
import StatsPanel from "@/components/StatsPanel";
import ChatPanel from "@/components/ChatPanel";
import SocialPanel from "@/components/SocialPanel";
import { Book, Settings as SettingsIcon, Globe } from "lucide-react";

export default function GamePage() {
    const router = useRouter();
    const [isClient, setIsClient] = useState(false);
    const {
        connect,
        disconnect,
        isConnected,
        step,
        agents,
        weather,
        logs,
        lore,
        economy,
        mapa,
        relationships,
        speechBubbles,
        selectAgent,
        selectedAgentId,
        civilizaciones,
        gruposDinamicos,
        propuestas,
        showThoughts,
        toggleThoughts,
        isAuthenticated,
        userId,
        username,
        logout,
        _handleSessionExpiredResponse,
        userScore,
        recentCompletedMissions,
        agentePoseidoId
    } = useGameStore();

    const [viewMode, setViewMode] = useState<"map" | "3d" | "graph">("map");
    const [activePanel, setActivePanel] = useState<string | null>(null);
    const [showStatsPanel, setShowStatsPanel] = useState(false);
    const logsContainerRef = useRef<HTMLDivElement>(null);
    const lastLogRef = useRef<HTMLDivElement>(null);
    const [showLogs, setShowLogs] = useState(false);
    const [autoScrollEnabled, setAutoScrollEnabled] = useState(true);
    const [currentCelebratingMission, setCurrentCelebratingMission] = useState<any>(null);
    const [showInstructions, setShowInstructions] = useState(false);

    // Initial connection and auth check
    useEffect(() => {
        setIsClient(true);
        if (!isAuthenticated) {
            router.push("/auth");
        } else {
            connect();
            const instructionsSeen = localStorage.getItem("instructions_seen");
            if (!instructionsSeen && typeof window !== 'undefined') {
                setShowInstructions(true);
            }
        }
        return () => disconnect();
    }, [isAuthenticated, router, connect, disconnect]);

    // Monitor for new completed missions to celebrate
    const lastCelebratedMissionRef = useRef<string | null>(null);
    useEffect(() => {
        if (recentCompletedMissions && recentCompletedMissions.length > 0) {
            const latestMission = recentCompletedMissions[0];
            if (latestMission.id !== lastCelebratedMissionRef.current) {
                lastCelebratedMissionRef.current = latestMission.id;
                setCurrentCelebratingMission(latestMission);
            }
        }
    }, [recentCompletedMissions]);

    // Auto-scroll logic for logs
    useEffect(() => {
        if (autoScrollEnabled && lastLogRef.current && showLogs) {
            lastLogRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' });
        }
    }, [logs, autoScrollEnabled, showLogs]);

    const handleControl = async (action: "start" | "pause" | "reset") => {
        if (!userId) return;

        if (action === "reset") {
            const confirmed = window.confirm("¿Estás seguro de que deseas reiniciar la simulación? Se perderán todos los agentes, grupos y leyes actuales.");
            if (!confirmed) return;
        }

        try {
            const response = await fetch(getHttpUrl("/game/control"), {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ user_id: userId, action }),
            });

            if (await _handleSessionExpiredResponse(response)) {
                return;
            }

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
        } catch (e) {
            console.error("Error controlling game:", e);
        }
    };

    const handleSave = async () => {
        if (!userId) return;
        try {
            const response = await fetch(getHttpUrl("/games/save"), {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ user_id: userId }),
            });
            if (await _handleSessionExpiredResponse(response)) return;
            if (!response.ok) throw new Error('Save failed');
            const data = await response.json();
            alert(`Partida guardada. Puntos: ${data.score || 'N/A'}`);
        } catch (e) {
            console.error("Error saving game:", e);
            alert('No se pudo guardar la partida');
        }
    };

    if (!isClient || !isAuthenticated) {
        return <div className="h-screen w-full flex items-center justify-center bg-[#0a0b10] text-white font-mono uppercase tracking-[0.4em] animate-pulse">Inicializando Realidad...</div>;
    }

    return (
        <div className="h-screen w-full bg-[#030305] text-white overflow-hidden flex font-sans selection:bg-[#7c4dff]/30">
            {/* Minimalist Sidebar Navigation */}
            <MainSidebar
                viewMode={viewMode}
                setViewMode={setViewMode}
                activePanel={activePanel}
                setActivePanel={(panel) => {
                    setActivePanel(panel);
                    if (panel !== null) selectAgent(null);
                }}
                showThoughts={showThoughts}
                toggleThoughts={toggleThoughts}
                onControl={handleControl}
            />

            <div className="flex-1 min-w-0 flex flex-col relative overflow-hidden">
                {/* Integrated Header / Status Bar */}
                <header className="absolute top-0 left-0 right-0 h-20 pointer-events-none z-50 flex items-center justify-between px-8">
                    <div className="flex items-center gap-12 pointer-events-auto">
                        <div className="flex flex-col">
                            <h1 className="text-xl font-black font-mono tracking-tighter flex items-center gap-3 text-white">
                                <span className="bg-clip-text text-transparent bg-gradient-to-r from-white to-white/40">MUNDO</span>
                                <span className="text-[#00e676] drop-shadow-[0_0_10px_rgba(0,230,118,0.3)]">IA</span>
                                <div className={`w-1.5 h-1.5 rounded-full ${isConnected ? 'bg-[#00e676] animate-pulse shadow-[0_0_10px_#00e676]' : 'bg-red-500'}`} />
                            </h1>
                        </div>

                        {/* Global Lore */}
                        <div className="hidden 2xl:flex items-center gap-4 py-2 px-6 border-l border-white/5 pointer-events-auto">
                            <Book className="w-3.5 h-3.5 text-white/20" />
                            <p className="max-w-md text-[10px] text-white/50 leading-relaxed font-mono italic truncate" title={lore}>
                                "{lore || "La simulación fluye. Los hilos del destino se entrelazan."}"
                            </p>
                        </div>
                    </div>

                    <div className="flex items-center gap-8 pointer-events-auto">
                        <div className="hidden xl:flex items-center gap-6 py-2 px-6 glass-panel rounded-2xl border border-white/5 bg-black/20 backdrop-blur-md">
                            <HeaderStat icon={Clock} label="Turno" value={step.toString()} />
                            <div className="w-px h-4 bg-white/5" />
                            <HeaderStat icon={weather === 'sunny' ? Sun : CloudRain} label="Clima" value={weather === 'sunny' ? 'Despejado' : 'Tormenta'} />
                            <div className="w-px h-4 bg-white/5" />
                            <HeaderStat icon={Star} label="Puntos" value={userScore.toString()} highlight />
                        </div>

                        <div className="flex items-center gap-4 pl-4 border-l border-white/5">
                            <div className="flex flex-col items-end">
                                <span className="text-[10px] font-bold text-white tracking-widest uppercase">{username}</span>
                                <span className="text-[7px] text-[#00e676] uppercase font-black tracking-[0.2em] opacity-80">Observador Lvl 4</span>
                            </div>
                            <div className="flex items-center gap-3">
                                <button
                                    onClick={handleSave}
                                    className="p-3 bg-white/5 hover:bg-white/10 text-white rounded-2xl transition-all border border-white/5"
                                    title="Guardar partida"
                                >
                                    <Share2 className="w-4 h-4" />
                                </button>
                                <button
                                    onClick={logout}
                                    className="p-3 bg-white/5 hover:bg-red-500/20 text-white/40 hover:text-red-400 rounded-2xl transition-all border border-white/5 active:scale-90 group"
                                    title="Desconectar"
                                >
                                    <LogOut className="w-4 h-4 group-hover:rotate-12 transition-transform" />
                                </button>
                            </div>
                        </div>
                    </div>
                </header>

                {/* Simulation Canvas */}
                <main className="flex-1 relative">
                    <div className="absolute inset-0">
                        {viewMode === "map" && <WorldViewport hideBubbles={!!activePanel} />}
                        {viewMode === "3d" && <WorldViewport3D />}
                        {viewMode === "graph" && <NetworkView />}
                    </div>

                    {/* Integrated Event Logs (Toggleable) */}
                    <div className="absolute bottom-6 left-6 z-40 flex flex-col items-start gap-2 max-w-[440px]">
                        <button
                            onClick={() => setShowLogs(!showLogs)}
                            className={`px-4 py-2 glass-panel border border-white/10 rounded-2xl text-[10px] font-bold uppercase tracking-widest flex items-center gap-2 transition-all ${showLogs ? 'bg-white/10' : 'bg-black/60 hover:bg-black/80'}`}
                        >
                            <Terminal className={`w-3.5 h-3.5 ${showLogs ? 'text-[#00e676]' : 'text-gray-500'}`} />
                            Terminal de Eventos
                            <ChevronDown className={`w-3 h-3 transition-transform ${showLogs ? 'rotate-180' : ''}`} />
                        </button>

                        <AnimatePresence>
                            {showLogs && (
                                <motion.div
                                    initial={{ height: 0, opacity: 0 }}
                                    animate={{ height: 560, opacity: 1 }}
                                    exit={{ height: 0, opacity: 0 }}
                                    className="w-full glass-panel rounded-2xl overflow-hidden border border-white/10 shadow-2xl flex flex-col"
                                >
                                    <div className="flex items-center justify-between p-2 border-b border-white/5 bg-black/20">
                                        <span className="text-[9px] font-bold uppercase tracking-widest text-white/50 pl-2">Registro de eventos</span>
                                        <div
                                            onClick={() => setAutoScrollEnabled(!autoScrollEnabled)}
                                            className="flex items-center gap-2 cursor-pointer p-1 rounded-md hover:bg-white/10 transition-colors"
                                        >
                                            <div className={`w-3 h-3 rounded-sm border-2 ${autoScrollEnabled ? 'bg-[#00e676] border-[#00e676]' : 'border-white/30'}`} />
                                            <span className="text-[9px] font-mono text-white/50">Auto-Scroll</span>
                                        </div>
                                    </div>
                                    <LogList logs={logs} showThoughts={showThoughts} step={step} logsContainerRef={logsContainerRef} lastLogRef={lastLogRef} />
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>
                </main>

                <RightPanelManager
                    activePanel={activePanel}
                    onClose={() => setActivePanel(null)}
                    selectedAgentId={selectedAgentId}
                    userId={userId || ""}
                />

                {!activePanel && <AgentSidebar />}

                <AnimatePresence>
                    {agentePoseidoId && <PossessionPanel />}
                </AnimatePresence>

                <SocietyChronicle
                    isOpen={activePanel === 'chronicle'}
                    onClose={() => setActivePanel(null)}
                />

                <MissionCelebration
                    mission={currentCelebratingMission}
                    onComplete={() => setCurrentCelebratingMission(null)}
                />

                <DivineFX />

                {showInstructions && (
                    <InstructionOverlay onComplete={() => {
                        setShowInstructions(false);
                        localStorage.setItem("instructions_seen", "true");
                    }} />
                )}
            </div>
        </div>
    );
}

const HeaderStat = React.memo(({ icon: Icon, label, value, highlight }: any) => {
    return (
        <div className="flex items-center gap-2.5">
            <Icon className={`w-3.5 h-3.5 ${highlight ? 'text-[#ffea00] drop-shadow-[0_0_5px_rgba(255,234,0,0.5)]' : 'text-white/40'}`} />
            <div className="flex flex-col">
                <span className="text-[8px] font-black font-mono text-white/40 leading-none uppercase tracking-tighter mb-0.5">{label}</span>
                <span className={`text-[11px] font-bold font-mono tracking-tighter leading-none ${highlight ? 'text-[#ffea00]' : 'text-white/90'}`}>{value}</span>
            </div>
        </div>
    );
});

const LogList = React.memo(({ logs, showThoughts, step, logsContainerRef, lastLogRef }: any) => {
    const visibleLogs = logs.slice(-200);

    return (
        <div
            ref={logsContainerRef}
            className="flex-1 overflow-y-auto p-4 space-y-3 custom-scrollbar font-mono text-xs"
        >
            {visibleLogs.map((log: any, i: number) => {
                const logText = typeof log === 'string' ? log : (log.message || '');
                if (logText.includes('🧠') && !showThoughts) return null;

                let borderColor = 'border-[#7c4dff]/40';
                const isGlobal = (
                    logText.includes('📢') ||
                    logText.includes('[DIVINO]') ||
                    logText.includes('[NARRATIVA]') ||
                    logText.includes('[SISTEMA]') ||
                    logText.includes('⚠️') ||
                    log.category === 'evento' ||
                    log.category === 'ambiente'
                );

                if (isGlobal) {
                    borderColor = 'border-yellow-400/80';
                } else if (log.private_for || logText.includes('👥') || logText.includes('🔒')) {
                    if ((log.private_for && log.private_for.startsWith('GRUPO:')) || logText.includes('👥')) {
                        borderColor = 'border-emerald-400/80';
                    } else {
                        borderColor = 'border-cyan-400/80';
                    }
                }

                const isLastLog = i === visibleLogs.length - 1;
                return (
                    <div key={log.timestamp || i} ref={isLastLog ? lastLogRef : null} className={`p-2 rounded bg-white/5 border-l-2 ${borderColor} animate-in fade-in slide-in-from-bottom-1`}>
                        <span className="text-[8px] text-white/30 block mb-0.5 uppercase tracking-tighter">Turno {log.step || step}</span>
                        <span className="text-white/80 leading-relaxed font-sans">{logText}</span>
                    </div>
                );
            })}
        </div>
    );
});

const RightPanelManager = React.memo(({ activePanel, onClose, selectedAgentId, userId }: any) => {
    if (!activePanel) return null;

    switch (activePanel) {
        case 'chat':
            return (
                <UnifiedPanel isOpen={true} onClose={onClose} title="Chat con Agentes" subtitle="Conversaciones Directas" icon={MessageCircle} color="text-cyan-400">
                    <ChatPanel userId={userId} onClose={onClose} />
                </UnifiedPanel>
            );
        case 'social':
            return (
                <UnifiedPanel isOpen={true} onClose={onClose} title="Red Social" subtitle="MundoIA Social" icon={Globe} color="text-[#00e5ff]">
                    <SocialPanel />
                </UnifiedPanel>
            );
        case 'architect':
            return (
                <UnifiedPanel isOpen={true} onClose={onClose} title="Arquitecto" subtitle="Modo Dios Activo" icon={Terminal} color="text-yellow-500">
                    <ArchitectPanel userId={userId} onClose={onClose} />
                </UnifiedPanel>
            );
        case 'factions':
            return (
                <UnifiedPanel isOpen={true} onClose={onClose} title="Sociedades" subtitle="Estructuras de Poder" icon={Flag} color="text-[#ffd600]">
                    <FactionsPanel isOpen={true} onClose={onClose} />
                </UnifiedPanel>
            );
        case 'missions':
            return (
                <UnifiedPanel isOpen={true} onClose={onClose} title="Misiones" subtitle="Objetivos de Civilización" icon={Zap} color="text-[#ffea00]">
                    <MissionsPanel />
                </UnifiedPanel>
            );
        case 'institutions':
            return (
                <UnifiedPanel isOpen={true} onClose={onClose} title="Instituciones" subtitle="Pilares de la Sociedad" icon={Landmark} color="text-emerald-400">
                    <InstitutionsPanel />
                </UnifiedPanel>
            );
        case 'config':
            return (
                <UnifiedPanel isOpen={true} onClose={onClose} title="Configuración" subtitle="Cerebro LLM Global" icon={SettingsIcon} color="text-indigo-400">
                    <ConfigPanel isOpen={true} onClose={onClose} />
                </UnifiedPanel>
            );
        case 'stats':
            return <StatsPanel isOpen={true} onClose={onClose} />;
        default:
            return null;
    }
});