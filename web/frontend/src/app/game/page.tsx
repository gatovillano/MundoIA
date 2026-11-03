"use client";

/* eslint-disable @typescript-eslint/no-explicit-any */

import React, { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import useGameStore from "@/store/useGameStore";
import { getHttpUrl } from "@/utils/apiConfig";
import { Play, Pause, RefreshCw, LogOut, Map as MapIcon, Share2, Zap, Brain, Users, Box, ChevronDown, ChevronRight, Clock, Activity, BarChart3, Terminal, X, Flag, CircleDashed, Star, Sun, CloudRain, Landmark, MessageCircle, ShieldCheck, DollarSign, Home } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { getAgentName, replaceIdsWithNames } from "@/utils/nameUtils";

import dynamic from "next/dynamic";

const WorldViewport = dynamic(() => import("@/components/WorldViewport"), {
    ssr: false,
    loading: () => (
        <div className="w-full h-full flex items-center justify-center bg-[#1c2128]">
            <span className="text-gray-400 font-mono text-sm animate-pulse">CARGANDO MAPA ISOMÉTRICO (D3)...</span>
        </div>
    )
});

const WorldViewport3D = dynamic(() => import("@/components/WorldViewport3D"), {
    ssr: false,
    loading: () => (
        <div className="w-full h-full flex items-center justify-center bg-[#1c2128]">
            <span className="text-gray-400 font-mono text-sm animate-pulse">INICIALIZANDO MOTOR 3D (THREE.JS)...</span>
        </div>
    )
});

const NetworkView = dynamic(() => import("@/components/NetworkView"), {
    ssr: false,
    loading: () => (
        <div className="w-full h-full flex items-center justify-center bg-[#1c2128]">
            <span className="text-gray-400 font-mono text-sm animate-pulse">GENERANDO RED SOCIAL GRAFO...</span>
        </div>
    )
});
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
        reconnect,
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
        enableStreaming,
        toggleStreaming,
        isAuthenticated,
        userId,
        gameId,
        username,
        logout,
        _handleSessionExpiredResponse,
        userScore,
        recentCompletedMissions,
        agentePoseidoId,
        sendGodAction,
        connectedPlayers,
        roomInfo,
        setRoomInfo,
        modoControlTotal,
        setModoControlTotal
    } = useGameStore();

    const uid = gameId || userId;

    const architectMoney = React.useMemo(() => {
        try {
            // Preferir suma de dinero de agentes (compatibilidad con backend)
            const sumAgents = (agents || []).reduce((s: number, a: any) => s + (typeof a.money === 'number' ? a.money : (typeof a.dinero === 'number' ? a.dinero : 0)), 0);
            // Si existe economy.total_dinero y es un número, usarlo como fallback/override
            const econTotal = economy && typeof economy.total_dinero === 'number' ? economy.total_dinero : null;
            return econTotal !== null ? econTotal : sumAgents;
        } catch (e) {
            return 0;
        }
    }, [economy, agents]);

    const [viewMode, setViewMode] = useState<"map" | "3d" | "graph">("map");
    const [activePanel, setActivePanel] = useState<string | null>(null);
    const [showStatsPanel, setShowStatsPanel] = useState(false);
    const logsContainerRef = useRef<HTMLDivElement>(null);
    const lastLogRef = useRef<HTMLDivElement>(null);
    const [showLogs, setShowLogs] = useState(false);
    const [autoScrollEnabled, setAutoScrollEnabled] = useState(true);
    const [currentCelebratingMission, setCurrentCelebratingMission] = useState<any>(null);
    const [showInstructions, setShowInstructions] = useState(false);
    const [showModeSelection, setShowModeSelection] = useState(true);
    const [protocolStep, setProtocolStep] = useState<'intervention' | 'operation'>('intervention');
    const [loadingAction, setLoading] = useState(false);
    const [savedGames, setSavedGames] = useState<any[]>([]);
    const [showPlayersMenu, setShowPlayersMenu] = useState(false);
    const [copiedCode, setCopiedCode] = useState(false);

    // Sincronizar metadatos de sala multijugador si aplica
    useEffect(() => {
        if (!uid) return;
        if (uid.startsWith('mp_') || roomInfo) {
            fetch(getHttpUrl(`/multiplayer/rooms/${encodeURIComponent(uid)}`))
                .then((r) => (r.ok ? r.json() : null))
                .then((data) => {
                    if (data?.room) {
                        setRoomInfo(data.room);
                        // Si el jugador se une como invitado a una sala activa, entrar directo al mapa
                        if (data.room.host_user_id && data.room.host_user_id !== userId) {
                            setShowModeSelection(false);
                        }
                    }
                })
                .catch(() => {});
        }
    }, [uid, userId, setRoomInfo]);

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

    const handleControl = async (action: "start" | "pause" | "reset", forcedMode?: boolean) => {
        if (!uid) return;

        if (action === "reset") {
            const confirmed = window.confirm("¿Estás seguro de que deseas reiniciar la simulación? Se perderán todos los agentes, grupos y leyes actuales.");
            if (!confirmed) return;
        }

        try {
            const modeToUse = forcedMode !== undefined ? forcedMode : useGameStore.getState().modoControlTotal;
            
            const response = await fetch(getHttpUrl('/game/control'), {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ 
                    user_id: uid,
                    action, 
                    modo_control_total: modeToUse 
                }),
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

    const handleSelectIntervention = (isControlTotal: boolean) => {
        useGameStore.setState({ modoControlTotal: isControlTotal });
        // Si venimos desde la pantalla de inicio y ya se ejecutó la operación (new/load/quick),
        // no pasar al paso de 'operation' (evitamos preguntar de nuevo). Cerramos el modal.
        const startupDone = useGameStore.getState().startupOperationDone;
        if (startupDone) {
            useGameStore.setState({ startupOperationDone: false });
            setShowModeSelection(false);
            return;
        }

        setProtocolStep('operation');
        fetchSavedGames();
    };

    const fetchSavedGames = async () => {
        if (!uid) return;
        try {
            // Utilizamos el userId base para listar todos los slots guardados
            const res = await fetch(getHttpUrl(`/games/list/${userId}`));
            if (res.ok) {
                const data = await res.json();
                setSavedGames(data.games || []);
            }
        } catch (e) { console.error(e); }
    };

    const handleOperation = async (type: 'continue' | 'new' | 'quick') => {
        if (!uid) return;
        setLoading(true);
        try {
            if (type === 'continue') {
                await fetch(getHttpUrl('/games/load'), {
                    method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ user_id: uid })
                });
            } else if (type === 'new') {
                await fetch(getHttpUrl('/game/control'), {
                    method: 'POST', 
                    headers: {'Content-Type': 'application/json'}, 
                    body: JSON.stringify({ user_id: uid, action: 'reset' })
                });
            } else if (type === 'quick') {
                await fetch(getHttpUrl('/games/quickplay'), {
                    method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ user_id: uid, num_agents: 12, save: true })
                });
            }
            setShowModeSelection(false);
        } catch (e) {
            console.error(e);
            alert("Error en la operación de inicio.");
        } finally {
            setLoading(false);
        }
    };

    const handleSave = async () => {
        if (!uid) return;
        try {
            const response = await fetch(getHttpUrl("/games/save"), {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ user_id: uid }),
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

    // === Auto-save: periodically POST /games/save and attempt sendBeacon on unload ===
    React.useEffect(() => {
        const autosaveSec = parseInt(process.env.NEXT_PUBLIC_AUTOSAVE_INTERVAL || '60', 10);
        const autosaveMs = Math.max(5, autosaveSec) * 1000; // mínimo 5s
        if (!isClient || !isAuthenticated || !uid) return;

        const tick = async () => {
            try {
                await fetch(getHttpUrl('/games/save'), {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ user_id: uid }),
                });
            } catch (err) {
                console.error('Autosave failed:', err);
            }
        };

        const id = setInterval(tick, autosaveMs);

        const onBeforeUnload = () => {
            try {
                const payload = JSON.stringify({ user_id: uid });
                const url = getHttpUrl('/games/save');
                if (navigator && typeof navigator.sendBeacon === 'function') {
                    const blob = new Blob([payload], { type: 'application/json' });
                    navigator.sendBeacon(url, blob);
                } else {
                    // best-effort final save
                    fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: payload, keepalive: true });
                }
            } catch (e) {
                console.warn('beforeunload autosave failed', e);
            }
        };

        window.addEventListener('beforeunload', onBeforeUnload);

        // kick an immediate save when opening the page
        tick();

        return () => {
            clearInterval(id);
            window.removeEventListener('beforeunload', onBeforeUnload);
        };
    }, [isClient, isAuthenticated, uid]);

    // === Auto-scroll para la Terminal de Eventos ===
    useEffect(() => {
        if (autoScrollEnabled && showLogs && lastLogRef.current) {
            lastLogRef.current.scrollIntoView({ behavior: "smooth" });
        }
    }, [logs, autoScrollEnabled, showLogs]);

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
                enableStreaming={enableStreaming}
                toggleStreaming={toggleStreaming}
                onControl={handleControl}
                modoControlTotal={modoControlTotal}
                onToggleMode={() => {
                    const newMode = !modoControlTotal;
                    setModoControlTotal(newMode);
                    handleControl("start", newMode);
                }}
                userId={uid || ""}
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
                                {`"${lore || "La simulación fluye. Los hilos del destino se entrelazan."}"`}
                            </p>
                        </div>
                    </div>

                    <div className="flex items-center gap-6 pointer-events-auto">
                        {/* Badge Multijugador (Código de Nexo + Jugadores Conectados) */}
                        {(roomInfo || (uid && uid.startsWith('mp_')) || (connectedPlayers && connectedPlayers.length > 1)) && (
                            <div className="relative flex items-center gap-2 py-1.5 px-3.5 glass-panel rounded-2xl border border-[#00e676]/30 bg-[#00e676]/5 backdrop-blur-md">
                                {roomInfo?.codigo_acceso && (
                                    <button
                                        onClick={() => {
                                            navigator.clipboard?.writeText(roomInfo.codigo_acceso);
                                            setCopiedCode(true);
                                            setTimeout(() => setCopiedCode(false), 2000);
                                        }}
                                        className="px-2.5 py-1 rounded-xl bg-black/40 hover:bg-black/60 border border-white/10 text-[10px] font-mono font-bold text-[#00e676] tracking-wider transition-all"
                                        title="Clic para copiar código de invitación"
                                    >
                                        {copiedCode ? '✓ COPIADO' : `NEXO: ${roomInfo.codigo_acceso}`}
                                    </button>
                                )}
                                <button
                                    onClick={() => setShowPlayersMenu(!showPlayersMenu)}
                                    className="flex items-center gap-2 px-2 py-1 rounded-xl hover:bg-white/5 text-xs font-mono font-bold text-white transition-all"
                                    title="Ver jugadores conectados en esta sala"
                                >
                                    <span className="w-2 h-2 rounded-full bg-[#00e676] animate-pulse" />
                                    <Users className="w-3.5 h-3.5 text-[#00e676]" />
                                    <span>{Math.max(1, connectedPlayers?.length || 1)}</span>
                                </button>
                                <button
                                    onClick={async () => {
                                        await sendGodAction("SPAWN_PLAYER_AVATAR", {});
                                    }}
                                    className="flex items-center gap-1.5 px-2.5 py-1 rounded-xl bg-amber-500/20 hover:bg-amber-500/30 border border-amber-400/40 text-[10px] font-mono font-bold text-amber-300 transition-all"
                                    title="Encarnar / Centrar mi Avatar en el tablero"
                                >
                                    <span>👑 MI AVATAR</span>
                                </button>

                                {showPlayersMenu && (
                                    <div className="absolute top-14 right-0 w-72 p-4 glass-panel rounded-2xl border border-white/15 bg-[#0a0c12]/95 backdrop-blur-xl shadow-2xl z-50 space-y-3">
                                        <div className="flex items-center justify-between border-b border-white/10 pb-2">
                                            <div>
                                                <p className="text-[10px] font-mono uppercase tracking-widest text-[#00e676] font-bold">
                                                    {roomInfo?.nombre || 'Realidad Compartida'}
                                                </p>
                                                {roomInfo?.codigo_acceso && (
                                                    <p className="text-[9px] font-mono text-gray-400">
                                                        Código: {roomInfo.codigo_acceso}
                                                    </p>
                                                )}
                                            </div>
                                            <button
                                                onClick={() => setShowPlayersMenu(false)}
                                                className="text-gray-400 hover:text-white"
                                            >
                                                <X className="w-3.5 h-3.5" />
                                            </button>
                                        </div>
                                        <div className="space-y-2 max-h-48 overflow-y-auto">
                                            {(connectedPlayers && connectedPlayers.length > 0
                                                ? connectedPlayers
                                                : [{ player_id: userId || 'local', username: username || 'Arquitecto' }]
                                            ).map((p: any) => (
                                                <div
                                                    key={p.player_id}
                                                    className="flex items-center justify-between p-2 rounded-xl bg-white/5 border border-white/5 text-xs"
                                                >
                                                    <div className="flex items-center gap-2">
                                                        <span className="w-2 h-2 rounded-full bg-[#00e676]" />
                                                        <span className="font-mono font-bold text-white">
                                                            {p.username}
                                                            {p.player_id === userId ? ' (Tú)' : ''}
                                                        </span>
                                                    </div>
                                                    {p.possessed_agent_name ? (
                                                        <span className="px-2 py-0.5 rounded-md bg-amber-500/20 text-amber-300 font-mono text-[9px]">
                                                            👻 {p.possessed_agent_name}
                                                        </span>
                                                    ) : (
                                                        <span className="text-[9px] font-mono text-gray-500 uppercase">
                                                            Arquitecto
                                                        </span>
                                                    )}
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}

                        <div className="hidden xl:flex items-center gap-6 py-2 px-6 glass-panel rounded-2xl border border-white/5 bg-black/20 backdrop-blur-md">
                            <HeaderStat icon={Clock} label="Turno" value={step.toString()} />
                            <div className="w-px h-4 bg-white/5" />
                            <HeaderStat icon={weather === 'sunny' ? Sun : CloudRain} label="Clima" value={weather === 'sunny' ? 'Despejado' : 'Tormenta'} />
                            <div className="w-px h-4 bg-white/5" />
                            <HeaderStat icon={DollarSign} label="Dinero" value={(Math.round(architectMoney) || 0).toString() + ' MC'} />
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
                                    onClick={() => router.push('/start')}
                                    className="p-3 bg-white/5 hover:bg-indigo-500/20 text-white/40 hover:text-indigo-400 rounded-2xl transition-all border border-white/5 active:scale-90 group"
                                    title="Volver al Inicio"
                                >
                                    <Home className="w-4 h-4 group-hover:-translate-y-0.5 transition-transform" />
                                </button>

                                <button
                                    onClick={handleSave}
                                    className="p-3 bg-white/5 hover:bg-white/10 text-white rounded-2xl transition-all border border-white/5"
                                    title="Guardar partida"
                                >
                                    <Share2 className="w-4 h-4" />
                                </button>

                                <button
                                    onClick={() => reconnect()}
                                    className="p-3 bg-white/5 hover:bg-white/10 text-white rounded-2xl transition-all border border-white/5"
                                    title="Reconectar WebSocket"
                                >
                                    <RefreshCw className={`w-4 h-4 ${isConnected ? '' : 'animate-spin'}`} />
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
                                    <LogList agents={agents} showThoughts={showThoughts} step={step} logsContainerRef={logsContainerRef} lastLogRef={lastLogRef} />
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>
                </main>

                <RightPanelManager
                    activePanel={activePanel}
                    onClose={() => setActivePanel(null)}
                    selectedAgentId={selectedAgentId}
                    userId={uid || ""}
                />

                <AnimatePresence>
                    {showModeSelection && (
                        <motion.div 
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="fixed inset-0 z-[100] flex items-center justify-center bg-[#030305]/95 backdrop-blur-3xl p-6"
                        >
                            <motion.div 
                                initial={{ scale: 0.98, opacity: 0, y: 10 }}
                                animate={{ scale: 1, opacity: 1, y: 0 }}
                                className="w-full max-w-5xl bg-[#0a0b10] border border-white/10 rounded-[40px] overflow-hidden shadow-[0_0_100px_rgba(124,77,255,0.1)] flex flex-col lg:flex-row"
                            >
                                <div className="flex-1 p-12 lg:p-16 space-y-10 relative">
                                    {/* Loading Overlay for Actions */}
                                    <AnimatePresence>
                                        {loadingAction && (
                                            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="absolute inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center">
                                                <div className="flex flex-col items-center gap-4">
                                                    <div className="w-12 h-12 border-4 border-indigo-500/20 border-t-indigo-500 rounded-full animate-spin" />
                                                    <span className="text-[10px] font-mono text-indigo-400 uppercase tracking-[0.4em] animate-pulse">Procesando Realidad...</span>
                                                </div>
                                            </motion.div>
                                        )}
                                    </AnimatePresence>

                                    <div className="flex items-center justify-between border-b border-white/5 pb-8">
                                        <div>
                                            <div className="flex items-center gap-3 mb-2">
                                                <div className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse" />
                                                <span className="text-[#7c4dff] font-mono text-[10px] uppercase tracking-[0.5em] font-black">Protocolo de Inicio</span>
                                            </div>
                                            <h2 className="text-4xl font-black text-white tracking-tighter uppercase">
                                                {protocolStep === 'intervention' ? 'Nivel de Intervención' : 'Modo de Operación'}
                                            </h2>
                                        </div>
                                        <div className="flex gap-2">
                                            <div className={`w-12 h-1 rounded-full ${protocolStep === 'intervention' ? 'bg-[#7c4dff]' : 'bg-white/10'}`} />
                                            <div className={`w-12 h-1 rounded-full ${protocolStep === 'operation' ? 'bg-[#7c4dff]' : 'bg-white/10'}`} />
                                        </div>
                                    </div>

                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                                        {protocolStep === 'intervention' ? (
                                            <>
                                                <ProtocolCard 
                                                    onClick={() => handleSelectIntervention(false)}
                                                    icon={Globe}
                                                    title="Observador"
                                                    desc="La civilización evoluciona orgánicamente. Tu rol es guiar el destino mediante sugerencias y observar el flujo natural."
                                                    tag="Autonomía"
                                                />
                                                <ProtocolCard 
                                                    onClick={() => handleSelectIntervention(true)}
                                                    icon={Zap}
                                                    title="Arquitecto"
                                                    desc="Toma el control táctico. La simulación espera tus órdenes para avanzar. Tú dictas cada paso de la historia."
                                                    tag="Control Total"
                                                    highlight
                                                />
                                            </>
                                        ) : (
                                            <>
                                                {/* Operation options */}
                                                <div className="space-y-4">
                                                    <h3 className="text-[10px] font-mono text-white/30 uppercase tracking-[0.3em] mb-6">Secuencia de Carga</h3>
                                                    
                                                    <OperationButton 
                                                        disabled={savedGames.length === 0}
                                                        onClick={() => handleOperation('continue')}
                                                        icon={Play}
                                                        title="Continuar Simulación"
                                                        desc={savedGames.length > 0 ? `Reanudar desde turno ${savedGames[0].paso_actual}` : 'No hay partidas guardadas'}
                                                    />
                                                    
                                                    <OperationButton 
                                                        onClick={() => handleOperation('new')}
                                                        icon={RefreshCw}
                                                        title="Nueva Partida"
                                                        desc="Colapsar la realidad actual y comenzar un nuevo Big Bang desde cero."
                                                    />

                                                    <button 
                                                        onClick={() => setProtocolStep('intervention')}
                                                        className="text-[10px] font-mono text-gray-500 hover:text-white transition-colors flex items-center gap-2 mt-8 group"
                                                    >
                                                        <ChevronRight className="w-3 h-3 rotate-180" />
                                                        VOLVER AL PASO ANTERIOR
                                                    </button>
                                                </div>

                                                <div className="p-8 bg-indigo-500/5 border border-indigo-500/10 rounded-[32px] space-y-6">
                                                    <div className="flex items-center gap-4">
                                                        <div className="p-3 bg-indigo-500/20 rounded-xl text-indigo-400">
                                                            <Activity className="w-5 h-5" />
                                                        </div>
                                                        <h3 className="text-lg font-bold text-white uppercase tracking-tight">Partida Rápida</h3>
                                                    </div>
                                                    <p className="text-xs text-gray-500 leading-relaxed">Inyecta inmediatamente 12 agentes aleatorios y un mapa base para comenzar a experimentar sin esperas.</p>
                                                    
                                                    <button 
                                                        onClick={() => handleOperation('quick')}
                                                        className="w-full py-4 bg-indigo-500 hover:bg-indigo-400 text-white font-black text-xs uppercase tracking-widest rounded-2xl transition-all shadow-xl shadow-indigo-500/10 active:scale-95 flex items-center justify-center gap-3"
                                                    >
                                                        <Zap className="w-4 h-4 fill-current" />
                                                        Lanzar Protocolo Rápido
                                                    </button>
                                                </div>
                                            </>
                                        )}
                                    </div>
                                </div>

                                <div className="hidden lg:flex w-80 bg-[#07080c] p-12 flex-col justify-between border-l border-white/5 relative">
                                    <div className="absolute inset-0 bg-[url('/grid.svg')] opacity-10" />
                                    <div className="relative z-10 space-y-8">
                                        <div className="w-12 h-12 rounded-2xl border border-white/10 flex items-center justify-center bg-white/[0.02]">
                                            <ShieldCheck className="w-6 h-6 text-indigo-500" />
                                        </div>
                                        <div>
                                            <h4 className="text-[10px] font-black text-white/40 uppercase tracking-[0.2em] mb-4">Autenticación</h4>
                                            <div className="flex items-center gap-3">
                                                <div className="w-8 h-8 rounded-full bg-[#00e676]/10 flex items-center justify-center">
                                                    <div className="w-1.5 h-1.5 rounded-full bg-[#00e676]" />
                                                </div>
                                                <span className="text-[10px] font-mono text-white/80 uppercase tracking-widest">{username}</span>
                                            </div>
                                        </div>
                                    </div>

                                    <div className="relative z-10 space-y-4">
                                        <div className="w-8 h-1 bg-white/20 rounded-full" />
                                        <p className="text-white/40 font-mono text-[9px] leading-relaxed uppercase tracking-wider">
                                            {protocolStep === 'intervention' 
                                                ? 'ESPERANDO DEFINICIÓN DE INTERVENCIÓN...' 
                                                : 'ESPERANDO SELECCIÓN DE OPERACIÓN...'}
                                        </p>
                                    </div>
                                </div>
                            </motion.div>
                        </motion.div>
                    )}
                </AnimatePresence>

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

// --- SUBCOMPONENTS FOR PROTOCOL MODAL ---

function ProtocolCard({ icon: Icon, title, desc, tag, onClick, highlight = false }: any) {
    return (
        <button 
            onClick={onClick}
            className={`group relative p-10 text-left flex flex-col justify-between min-h-[320px] overflow-hidden rounded-[35px] transition-all duration-500 border ${
                highlight 
                ? 'bg-indigo-500/[0.03] border-indigo-500/10 hover:border-[#7c4dff] hover:bg-indigo-500/[0.07]' 
                : 'bg-white/[0.02] border-white/5 hover:border-indigo-500/30 hover:bg-white/[0.04]'
            }`}
        >
            {highlight && <div className="absolute inset-0 bg-gradient-to-br from-[#7c4dff]/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />}
            
            <div className="space-y-6 relative z-10">
                <div className={`w-16 h-16 rounded-2xl flex items-center justify-center transition-all duration-500 border ${
                    highlight 
                    ? 'bg-[#7c4dff] text-white border-white/10 shadow-xl shadow-[#7c4dff]/20' 
                    : 'bg-white/5 text-gray-400 group-hover:text-indigo-400 group-hover:bg-indigo-500/10 border-white/5 group-hover:border-indigo-500/20'
                }`}>
                    <Icon className={`w-8 h-8 ${highlight ? 'fill-current' : ''}`} />
                </div>
                <div>
                    <h3 className="text-2xl font-bold text-white uppercase tracking-tight mb-3">{title}</h3>
                    <p className="text-sm text-gray-500 leading-relaxed font-medium">{desc}</p>
                </div>
            </div>

            <div className={`pt-6 border-t flex items-center justify-between relative z-10 ${highlight ? 'border-indigo-500/20' : 'border-white/5'}`}>
                <div className="flex gap-1">
                    {[1,2,3].map(i => (
                        <div 
                            key={i} 
                            className={`w-3 h-1 rounded-full ${highlight ? 'bg-[#7c4dff]' : 'bg-white/10'}`} 
                        />
                    ))}
                </div>
                <span className={`text-[9px] font-mono uppercase tracking-widest font-black ${highlight ? 'text-[#7c4dff]' : 'text-indigo-400/60'}`}>
                    {tag}
                </span>
            </div>
        </button>
    );
}

function OperationButton({ icon: Icon, title, desc, onClick, disabled = false }: any) {
    return (
        <button 
            disabled={disabled}
            onClick={onClick}
            className="w-full group p-6 bg-white/[0.02] hover:bg-white/[0.05] border border-white/5 hover:border-white/10 rounded-2xl transition-all text-left flex items-start gap-5 disabled:opacity-30 disabled:grayscale disabled:pointer-events-none"
        >
            <div className="p-3 bg-white/5 rounded-xl text-gray-500 group-hover:text-white transition-colors">
                <Icon className="w-5 h-5" />
            </div>
            <div>
                <h4 className="text-sm font-bold text-white uppercase tracking-wider mb-1">{title}</h4>
                <p className="text-[11px] text-gray-500 leading-tight">{desc}</p>
            </div>
            <ChevronRight className="ml-auto w-4 h-4 text-white/0 group-hover:text-white/20 transition-all group-hover:translate-x-1" />
        </button>
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
HeaderStat.displayName = "HeaderStat";

const LogList = React.memo(({ agents, showThoughts, step, logsContainerRef, lastLogRef }: any) => {
    const logs = useGameStore((state) => state.logs);
    const visibleLogs = logs.slice(-1000);

    return (
        <div
            ref={logsContainerRef}
            className="flex-1 overflow-y-auto p-4 space-y-3 custom-scrollbar font-mono text-xs"
        >
            {visibleLogs.map((log: any, i: number) => {
                let logText = typeof log === 'string' ? log : (log.message || '');
                if (logText.includes('🧠') && !showThoughts) return null;

                // Reemplazar IDs por nombres
                logText = replaceIdsWithNames(logText, agents);

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
                    <div key={`${log.timestamp ?? ''}_${i}`} ref={isLastLog ? lastLogRef : null} className={`p-2 rounded bg-white/5 border-l-2 ${borderColor} animate-in fade-in slide-in-from-bottom-1`}>
                        <span className="text-[8px] text-white/30 block mb-0.5 uppercase tracking-tighter">Turno {log.step || step}</span>
                        <span className="text-white/80 leading-relaxed font-sans">{logText}</span>
                    </div>
                );
            })}
        </div>
    );
});
LogList.displayName = "LogList";

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
RightPanelManager.displayName = "RightPanelManager";