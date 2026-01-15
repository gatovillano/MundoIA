"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import useGameStore from "@/store/useGameStore";
import { Play, Pause, RefreshCw, LogOut, Map as MapIcon, Share2, Zap, Brain, Users, Box } from "lucide-react";
import { motion } from "framer-motion";
import WorldViewport from "@/components/WorldViewport";
import WorldViewport3D from "@/components/WorldViewport3D";
import NetworkView from "@/components/NetworkView";
import ArchitectPanel from "@/components/ArchitectPanel";
import AgentSidebar from "@/components/AgentSidebar";
import FactionsPanel from "@/components/FactionsPanel";
import InstructionOverlay from "@/components/InstructionOverlay";

export default function GamePage() {
    const router = useRouter();
    const [isClient, setIsClient] = useState(false);
    const { connect, disconnect, isConnected, step, weather, logs, economy, showThoughts, toggleThoughts } = useGameStore();
    const [userId, setUserId] = useState<string | null>(null);
    const [viewMode, setViewMode] = useState<"map" | "3d" | "graph">("map");
    const [showArchitect, setShowArchitect] = useState(false);
    const [isFactionsOpen, setIsFactionsOpen] = useState(false);
    const logsContainerRef = useRef<HTMLDivElement>(null);
    const [autoScroll, setAutoScroll] = useState(true);
    const [showInstructions, setShowInstructions] = useState(false);

    useEffect(() => {
        setIsClient(true);
        const storedUserId = localStorage.getItem("user_id");
        if (!storedUserId) {
            router.push("/");
        } else {
            setUserId(storedUserId);
            connect(storedUserId);

            // Comprobar si ya vio las instrucciones
            const instructionsSeen = localStorage.getItem("instructions_seen");
            if (!instructionsSeen) {
                setShowInstructions(true);
            }
        }

        return () => {
            disconnect();
        };
    }, [router, connect, disconnect]);

    // Auto-scroll suave cuando llegan nuevos logs
    useEffect(() => {
        if (autoScroll && logsContainerRef.current && logs.length > 0) {
            const container = logsContainerRef.current;
            const targetScroll = container.scrollHeight - container.clientHeight;
            const currentScroll = container.scrollTop;
            const distance = targetScroll - currentScroll;

            // Solo hacer scroll si hay una distancia significativa
            if (Math.abs(distance) > 5) {
                // Scroll suave y gradual (2000ms de duración para lectura cómoda)
                const duration = 2000;
                const startTime = performance.now();

                const animateScroll = (currentTime: number) => {
                    const elapsed = currentTime - startTime;
                    const progress = Math.min(elapsed / duration, 1);

                    // Función de easing suave (ease-out)
                    const easeOut = 1 - Math.pow(1 - progress, 3);

                    container.scrollTop = currentScroll + (distance * easeOut);

                    if (progress < 1) {
                        requestAnimationFrame(animateScroll);
                    }
                };

                requestAnimationFrame(animateScroll);
            }
        }
    }, [logs, autoScroll]);

    // Detectar cuando el usuario scrollea manualmente
    const handleScroll = () => {
        if (logsContainerRef.current) {
            const container = logsContainerRef.current;
            const isAtBottom = Math.abs(
                container.scrollHeight - container.clientHeight - container.scrollTop
            ) < 50;

            // Reactivar auto-scroll si el usuario vuelve al final
            if (isAtBottom && !autoScroll) {
                setAutoScroll(true);
            } else if (!isAtBottom && autoScroll) {
                // Desactivar auto-scroll si el usuario scrollea hacia arriba
                setAutoScroll(false);
            }
        }
    };

    const handleControl = async (action: "start" | "pause" | "reset") => {
        if (!userId) return;
        try {
            const protocol = window.location.protocol;
            let host = window.location.host;
            if (window.location.hostname === 'mundoia.gatoslibres.art') {
                host = 'api-mundoia.gatoslibres.art';
            } else if (window.location.hostname === 'localhost') {
                host = 'localhost:8000';
            }

            await fetch(`${protocol}//${host}/game/control`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ user_id: userId, action }),
            });
        } catch (e) {
            console.error("Error controlling game:", e);
        }
    };

    const handleLogout = () => {
        localStorage.removeItem("user_id");
        localStorage.removeItem("username");
        router.push("/");
    };

    if (!isClient) return null;

    return (
        <div className="flex flex-col h-screen w-screen bg-[#0a0b10] text-[#e0e0e0] overflow-hidden">

            {/* Header Fijo */}
            <header className="flex items-center justify-between px-6 py-3 bg-[#0a0b10] border-b border-white/10 shrink-0 h-16">
                <div className="flex items-center gap-4">
                    <h1 className="text-xl font-bold tracking-wide text-white">
                        MUNDO <span className="text-[#7c4dff]">GENESIS</span>
                    </h1>
                    <div className={`px-2 py-0.5 rounded text-[10px] font-bold border ${isConnected ? 'bg-green-500/10 text-green-500 border-green-500/50' : 'bg-red-500/10 text-red-500 border-red-500/50'}`}>
                        {isConnected ? 'ONLINE' : 'OFFLINE'}
                    </div>
                </div>

                {/* Selector de Vistas Central */}
                <div className="absolute left-1/2 transform -translate-x-1/2 flex bg-white/5 rounded-lg p-1 border border-white/10 gap-1">
                    <button
                        onClick={() => setViewMode("map")}
                        className={`px-3 py-1.5 rounded flex items-center gap-2 text-xs font-bold transition-all ${viewMode === 'map' ? 'bg-[#7c4dff] text-white shadow-lg shadow-purple-500/20' : 'text-gray-400 hover:text-white hover:bg-white/5'}`}
                    >
                        <MapIcon className="w-3 h-3" />
                        2D
                    </button>
                    <button
                        onClick={() => setViewMode("3d")}
                        className={`px-3 py-1.5 rounded flex items-center gap-2 text-xs font-bold transition-all ${viewMode === '3d' ? 'bg-[#7c4dff] text-white shadow-lg shadow-purple-500/20' : 'text-gray-400 hover:text-white hover:bg-white/5'}`}
                    >
                        <Box className="w-3 h-3" />
                        3D
                    </button>
                    <button
                        onClick={() => setViewMode("graph")}
                        className={`px-3 py-1.5 rounded flex items-center gap-2 text-xs font-bold transition-all ${viewMode === 'graph' ? 'bg-[#7c4dff] text-white shadow-lg shadow-purple-500/20' : 'text-gray-400 hover:text-white hover:bg-white/5'}`}
                    >
                        <Share2 className="w-3 h-3" />
                        Relaciones
                    </button>
                </div>

                <div className="flex items-center gap-4">
                    <button
                        onClick={() => setShowArchitect(!showArchitect)}
                        className={`p-2 rounded-lg transition-colors flex items-center gap-2 ${showArchitect ? 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/50' : 'bg-white/5 text-gray-400 hover:text-yellow-400 hover:bg-yellow-500/10'}`}
                        title="Panel de Arquitecto"
                    >
                        <Zap className="w-5 h-5" />
                    </button>

                    <button
                        onClick={() => setIsFactionsOpen(!isFactionsOpen)}
                        className={`p-2 rounded-lg transition-colors flex items-center gap-2 ${isFactionsOpen ? 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/50' : 'bg-white/5 text-gray-400 hover:text-indigo-400 hover:bg-indigo-500/10'}`}
                        title="Panel de Facciones"
                    >
                        <Users className="w-5 h-5" />
                    </button>

                    <div className="flex bg-white/5 rounded-lg p-1 border border-white/10">
                        <button onClick={() => handleControl("start")} className="p-2 hover:bg-white/10 rounded text-white hover:text-green-400 transition-colors">
                            <Play className="w-4 h-4 fill-current" />
                        </button>
                        <button onClick={() => handleControl("pause")} className="p-2 hover:bg-white/10 rounded text-white hover:text-yellow-400 transition-colors">
                            <Pause className="w-4 h-4 fill-current" />
                        </button>
                        <button onClick={() => handleControl("reset")} className="p-2 hover:bg-white/10 rounded text-white hover:text-red-400 transition-colors">
                            <RefreshCw className="w-4 h-4" />
                        </button>
                    </div>

                    <button onClick={handleLogout} className="p-2 hover:bg-white/10 rounded-lg text-gray-400 hover:text-white transition-colors">
                        <LogOut className="w-5 h-5" />
                    </button>
                </div>
            </header>

            {/* Contenido Principal - Grid Layout */}
            <main className="flex-1 flex overflow-hidden relative">

                {/* Área Central: Mapa */}
                <div className="flex-1 relative bg-[#050508] flex flex-col">
                    <div className="absolute inset-0">
                        {viewMode === "map" ? <WorldViewport /> : viewMode === "3d" ? <WorldViewport3D /> : <NetworkView />}
                    </div>

                    {/* Panel de Arquitecto Overlay */}
                    {showArchitect && userId && (
                        <ArchitectPanel userId={userId} onClose={() => setShowArchitect(false)} />
                    )}

                    {/* Panel de Facciones Overlay */}
                    {isFactionsOpen && (
                        <FactionsPanel isOpen={isFactionsOpen} onClose={() => setIsFactionsOpen(false)} />
                    )}

                    {/* Overlay de Stats (Top Right) */}
                    <div className="absolute top-4 right-4 flex flex-col gap-2 w-64 pointer-events-none">
                        <div className="bg-black/80 backdrop-blur border border-white/10 p-3 rounded-lg flex justify-between items-center">
                            <span className="text-xs text-gray-400 uppercase font-bold">Paso</span>
                            <span className="text-xl font-mono font-bold text-white">{step}</span>
                        </div>
                        <div className="bg-black/80 backdrop-blur border border-white/10 p-3 rounded-lg flex justify-between items-center">
                            <span className="text-xs text-gray-400 uppercase font-bold">Clima</span>
                            <span className="text-sm font-bold text-white uppercase">{weather}</span>
                        </div>
                        <div className="bg-black/80 backdrop-blur border border-white/10 p-3 rounded-lg flex justify-between items-center">
                            <span className="text-xs text-gray-400 uppercase font-bold">Economía</span>
                            <span className="text-sm font-mono font-bold text-[#ffd600]">{economy?.total_dinero?.toFixed(0) || 0} MC</span>
                        </div>
                    </div>

                    {/* Overlay de Logs (Bottom Left) - AJUSTADO PARA NO TAPAR */}
                    <div className="absolute bottom-6 left-6 w-[500px] h-[350px] bg-black/60 backdrop-blur-3xl border border-white/20 rounded-2xl flex flex-col overflow-hidden pointer-events-auto shadow-[0_0_50px_rgba(0,0,0,0.8)] z-30">
                        <div className="px-5 py-4 border-b border-white/10 bg-gradient-to-r from-blue-500/10 to-transparent flex items-center justify-between">
                            <div className="flex items-center gap-3">
                                <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
                                <span className="text-[11px] font-bold text-blue-400 uppercase tracking-[0.25em]">Monitor de Eventos Mundiales</span>
                            </div>
                            <button
                                onClick={() => toggleThoughts()}
                                className={`flex items-center gap-2 px-2 py-1 rounded border transition-all ${showThoughts ? 'bg-indigo-500/20 border-indigo-500 text-indigo-300 shadow-[0_0_10px_rgba(99,102,241,0.2)]' : 'bg-white/5 border-white/10 text-gray-500'}`}
                                title="Mostrar/Ocultar Pensamientos"
                            >
                                <Brain className="w-3 h-3" />
                                <span className="text-[9px] font-bold uppercase tracking-tighter">Telepatía</span>
                            </button>
                        </div>
                        <div
                            ref={logsContainerRef}
                            onScroll={handleScroll}
                            className="p-5 overflow-y-auto font-mono text-[12px] space-y-3 custom-scrollbar flex-1"
                        >
                            {logs.length === 0 && <div className="text-gray-600 italic text-center p-8">Sincronizando con la red de agentes...</div>}
                            {logs.filter(log => log.category !== 'pensamiento' || showThoughts).map((log, i) => (
                                <motion.div
                                    initial={{ opacity: 0, x: -10 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    key={i}
                                    className={`flex gap-4 leading-relaxed group ${log.category === 'pensamiento' ? 'p-3 bg-indigo-500/10 border border-indigo-500/30 rounded-xl shadow-[0_0_15px_rgba(99,102,241,0.1)]' :
                                        log.category === 'dialogo' ? 'text-blue-300' :
                                            log.category === 'conflict' ? 'text-red-400 bg-red-400/5 -mx-2 px-2 rounded' :
                                                log.category === 'social' ? 'text-green-300' :
                                                    log.category === 'sistema' ? 'text-yellow-400/90 italic' :
                                                        'text-gray-400'
                                        }`}
                                >
                                    <span className={`opacity-20 shrink-0 select-none group-hover:opacity-50 transition-opacity ${log.category === 'pensamiento' ? 'text-indigo-400' : ''}`}>
                                        [{log.step.toString().padStart(3, '0')}]
                                    </span>
                                    <span className="break-words">
                                        {log.category === 'dialogo' && <strong className="text-blue-400 mr-1 font-bold">💬</strong>}
                                        {log.category === 'pensamiento' && <strong className="text-indigo-400 mr-1 font-bold">🧠</strong>}
                                        {log.message}
                                    </span>
                                </motion.div>
                            ))}
                        </div>
                    </div>
                </div>

                {/* Sidebar de Agente (Overlay) - Z-INDEX SUPERIOR */}
                <div className="z-50 relative">
                    <AgentSidebar />
                </div>

            </main>
            {/* Overlay de instrucciones */}
            {showInstructions && (
                <InstructionOverlay
                    onComplete={() => {
                        setShowInstructions(false);
                        localStorage.setItem("instructions_seen", "true");
                    }}
                />
            )}
        </div>
    );
}
