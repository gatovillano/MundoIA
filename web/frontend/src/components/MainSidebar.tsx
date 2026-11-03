"use client";

import { motion } from "framer-motion";
import { 
    Map as MapIcon, 
    Box, 
    Share2, 
    Flag, 
    Zap, 
    Terminal, 
    Settings, 
    Book,
    Play,
    Pause,
    RefreshCw,
    Brain,
    Landmark,
    Activity,
    MessageCircle,
    Music,
    VolumeX,
    Globe,
    TrendingUp
} from "lucide-react";

import { useState, useCallback } from "react";
import { getHttpUrl } from "@/utils/apiConfig";
import useGameStore from "@/store/useGameStore";

// Speed presets: [label, ritmo_seconds, icon_symbol, color]
const SPEED_PRESETS = [
    { label: "MAX",  ritmo: 0.0, symbol: "⚡", color: "text-cyan-400",   bg: "bg-cyan-400/20",   border: "border-cyan-400/40" },
    { label: "FAST", ritmo: 0.1, symbol: "⏩", color: "text-indigo-400", bg: "bg-indigo-400/20", border: "border-indigo-400/40" },
    { label: "NORM", ritmo: 0.5, symbol: "📊", color: "text-green-400",  bg: "bg-green-400/20",  border: "border-green-400/40" },
    { label: "SLOW", ritmo: 1.5, symbol: "⏳", color: "text-orange-400", bg: "bg-orange-400/20", border: "border-orange-400/40" },
];

interface MainSidebarProps {
    viewMode: "map" | "3d" | "graph";
    setViewMode: (mode: "map" | "3d" | "graph") => void;
    activePanel: string | null;
    setActivePanel: (panel: string | null) => void;
    showThoughts: boolean;
    toggleThoughts: () => void;
    onControl: (action: "start" | "pause" | "reset") => void;
    modoControlTotal: boolean;
    onToggleMode: () => void;
    // Mostrar actualizaciones incrementales (streams)
    enableStreaming: boolean;
    toggleStreaming: () => void;
    userId: string;
}

export default function MainSidebar({
    viewMode,
    setViewMode,
    activePanel,
    setActivePanel,
    showThoughts,
    toggleThoughts,
    enableStreaming,
    toggleStreaming,
    onControl,
    modoControlTotal,
    onToggleMode,
    userId,
}: MainSidebarProps) {
    const musicEnabled = useGameStore(state => state.musicEnabled);
    const toggleMusic = useGameStore(state => state.toggleMusic);
    const [speedIdx, setSpeedIdx] = useState(1); // default FAST
    const [speedStatus, setSpeedStatus] = useState<'idle' | 'ok' | 'err'>('idle');

    const cycleSpeed = useCallback(async () => {
        const nextIdx = (speedIdx + 1) % SPEED_PRESETS.length;
        setSpeedIdx(nextIdx);
        const preset = SPEED_PRESETS[nextIdx];
        try {
            await fetch(getHttpUrl('/game/speed'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: userId, ritmo: preset.ritmo })
            });
            setSpeedStatus('ok');
        } catch {
            setSpeedStatus('err');
        } finally {
            setTimeout(() => setSpeedStatus('idle'), 1500);
        }
    }, [speedIdx, userId]);

    
    const navItems = [
        { id: "map", icon: MapIcon, label: "Mapa 2D", type: "view" },
        { id: "3d", icon: Box, label: "Vista 3D", type: "view" },
        { id: "graph", icon: Share2, label: "Red Neural", type: "view" },
    ];

    const actionItems = [
        { id: "chat", icon: MessageCircle, label: "Chat", color: "text-cyan-400" },
        { id: "social", icon: Globe, label: "Red Social", color: "text-[#00e5ff]" },
        { id: "factions", icon: Flag, label: "Sociedades", color: "text-[#ffd600]" },
        { id: "institutions", icon: Landmark, label: "Instituciones", color: "text-emerald-400" },
        { id: "missions", icon: Zap, label: "Misiones", color: "text-[#ffea00]" },
        { id: "architect", icon: Terminal, label: "Arquitecto", color: "text-[#7c4dff]" },
        { id: "chronicle", icon: Book, label: "Crónica", color: "text-[#8d6e63]" },
        { id: "stats", icon: Activity, label: "Estadísticas", color: "text-cyan-400" },
        { id: "config", icon: Settings, label: "Config", color: "text-indigo-400" },
    ];

    return (
        <aside className="w-10 sm:w-12 md:w-16 lg:w-20 bg-black/40 backdrop-blur-xl border-r border-white/5 flex flex-col items-center py-1 sm:py-1.5 md:py-2 gap-0.5 sm:gap-1 md:gap-1.5 z-[60]">
            <div className="flex flex-col items-center gap-0.5 mb-1 shrink-0">
                <div className="w-5 h-5 sm:w-6 sm:h-6 md:w-8 md:h-8 rounded-lg bg-gradient-to-br from-[#7c4dff] to-[#00e676] flex items-center justify-center shadow-[0_0_15px_rgba(124,77,255,0.3)]">
                    <span className="text-black font-black text-[7px] sm:text-[8px] md:text-[10px]">MIA</span>
                </div>
            </div>

            {/* View Switcher */}
            <div className="flex flex-col gap-1 sm:gap-1.5 md:gap-2 shrink-0">
                {navItems.map((item) => (
                    <NavButton 
                        key={item.id}
                        active={viewMode === item.id}
                        onClick={() => setViewMode(item.id as any)}
                        icon={item.icon}
                        label={item.label}
                    />
                ))}
            </div>

            <div className="w-2 sm:w-3 md:w-4 h-px bg-white/10 shrink-0 my-1 sm:my-1.5 md:my-2" />

            {/* Panels Switcher */}
            <div className="flex flex-col gap-1 sm:gap-1.5 md:gap-2 shrink-0">
                {actionItems.map((item) => (
                    <NavButton 
                        key={item.id}
                        active={activePanel === item.id}
                        onClick={() => setActivePanel(activePanel === item.id ? null : item.id)}
                        icon={item.icon}
                        label={item.label}
                        color={item.color}
                    />
                ))}
            </div>

            <div className="mt-auto flex flex-col gap-1.5 sm:gap-2 pb-3 shrink-0">
                {/* Mind Toggle */}
                <button
                    onClick={toggleThoughts}
                    className={`p-1 sm:p-1.5 rounded-lg border transition-all duration-500 shadow-lg flex flex-col items-center ${showThoughts ? 'bg-[#7c4dff]/20 border-[#7c4dff]/40 text-[#7c4dff]' : 'bg-white/5 border-white/10 text-white/30 hover:text-white/60'}`}
                    title={showThoughts ? 'Mind ON' : 'Mind OFF'}
                >
                    <Brain className={`w-3 h-3 sm:w-3.5 sm:h-3.5 ${showThoughts ? 'animate-pulse' : ''}`} />
                </button>

                {/* Streaming Toggle */}
                <button
                    onClick={toggleStreaming}
                    className={`p-1 sm:p-1.5 rounded-lg border transition-all duration-500 shadow-lg flex flex-col items-center ${enableStreaming ? 'bg-[#00e676]/20 border-[#00e676]/40 text-[#00e676]' : 'bg-white/5 border-white/10 text-white/30 hover:text-white/60'}`}
                    title={enableStreaming ? 'Streaming ON' : 'Streaming OFF'}
                >
                    <Activity className={`w-3 h-3 sm:w-3.5 sm:h-3.5 ${enableStreaming ? 'animate-pulse' : ''}`} />
                </button>

                {/* Simulation Controls */}
                <div className="flex flex-col bg-white/5 border border-white/10 p-1 rounded-xl shadow-lg">
                    {/* Mode Toggle Button */}
                    <button
                        onClick={onToggleMode}
                        className={`p-1 sm:p-1.5 mb-1 rounded flex justify-center items-center transition-all ${modoControlTotal ? 'text-[#7c4dff] bg-[#7c4dff]/20' : 'text-[#00e676] bg-[#00e676]/20'}`}
                        title={modoControlTotal ? 'Modo actual: Arquitecto (Control Total)' : 'Modo actual: Observador (Autonomía)'}
                    >
                        {modoControlTotal ? <Zap className="w-3.5 h-3.5" /> : <Globe className="w-3.5 h-3.5" />}
                    </button>
                    <ControlButton onClick={() => onControl("start")} icon={Play} color="text-green-500" />
                    <ControlButton onClick={() => onControl("pause")} icon={Pause} color="text-yellow-500" />
                    <ControlButton onClick={() => onControl("reset")} icon={RefreshCw} color="text-red-500" />
                </div>

                {/* Speed Control */}
                <button
                    onClick={cycleSpeed}
                    title={`Velocidad: ${SPEED_PRESETS[speedIdx].label} (${SPEED_PRESETS[speedIdx].ritmo}s) — click para cambiar`}
                    className={`w-full mt-1 flex flex-col items-center justify-center p-1 sm:p-1.5 rounded-lg border transition-all duration-300 ${
                        speedStatus === 'ok'  ? 'bg-green-400/10 border-green-400/30' :
                        speedStatus === 'err' ? 'bg-red-400/10 border-red-400/30' :
                        `${SPEED_PRESETS[speedIdx].bg} ${SPEED_PRESETS[speedIdx].border}`
                    }`}
                >
                    <span className="text-[9px] leading-none">{SPEED_PRESETS[speedIdx].symbol}</span>
                    <span className={`text-[6px] sm:text-[7px] font-black uppercase tracking-widest leading-none mt-0.5 ${SPEED_PRESETS[speedIdx].color}`}>
                        {SPEED_PRESETS[speedIdx].label}
                    </span>
                </button>
                
                {/* Music Control */}
                <button
                    onClick={toggleMusic}
                    className={`p-1 mt-1 sm:p-1.5 rounded-lg border transition-all duration-300 shadow-lg flex flex-col items-center ${musicEnabled ? 'bg-cyan-500/20 border-cyan-500/40 text-cyan-400' : 'bg-white/5 border-white/10 text-white/30 hover:text-white/60'}`}
                    title={musicEnabled ? 'Pausar Música' : 'Reproducir Música'}
                >
                    {musicEnabled ? <Music className="w-3 h-3 sm:w-3.5 sm:h-3.5 animate-pulse" /> : <VolumeX className="w-3 h-3 sm:w-3.5 sm:h-3.5" />}
                </button>
            </div>
        </aside>
    );
}

function NavButton({ active, onClick, icon: Icon, label, color }: any) {
    return (
        <div className="relative">
            <button
                onClick={onClick}
                className={`p-1 sm:p-1.5 md:p-2 rounded-lg sm:rounded-xl transition-all group ${active ? 'bg-white/10 text-white shadow-[0_0_15px_rgba(255,255,255,0.05)]' : 'hover:bg-white/5 text-gray-500'}`}
                title={label}
            >
                <Icon className={`w-3 h-3 sm:w-3.5 sm:h-3.5 md:w-4 md:h-4 ${active ? (color || 'text-[#00e676]') : ''}`} />
                {active && (
                    <motion.div
                        layoutId="sidebar-active"
                        className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-3 sm:h-4 md:h-5 bg-[#00e676] rounded-r-full shadow-[0_0_8px_#00e676]"
                    />
                )}
            </button>

            {/* Tooltip posicionado fuera del sidebar */}
            <div className="absolute left-full ml-1.5 top-1/2 -translate-y-1/2 px-1 py-0.5 bg-black border border-white/10 rounded text-[6px] sm:text-[7px] md:text-[8px] font-bold uppercase tracking-wide sm:tracking-wider text-white opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity whitespace-nowrap z-[200]">
                {label}
            </div>
        </div>
    );
}

function ControlButton({ onClick, icon: Icon, color }: any) {
    return (
        <button 
            onClick={onClick} 
            className={`p-0.5 sm:p-1 md:p-1.5 hover:bg-white/5 rounded transition-all ${color} active:scale-90`}
        >
            <Icon className="w-3 h-3 sm:w-3.5 sm:h-3.5 md:w-4 md:h-4" />
        </button>
    );
}
