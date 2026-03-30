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
    MessageCircle
} from "lucide-react";

interface MainSidebarProps {
    viewMode: "map" | "3d" | "graph";
    setViewMode: (mode: "map" | "3d" | "graph") => void;
    activePanel: string | null;
    setActivePanel: (panel: string | null) => void;
    showThoughts: boolean;
    toggleThoughts: () => void;
    onControl: (action: "start" | "pause" | "reset") => void;
}

export default function MainSidebar({
    viewMode,
    setViewMode,
    activePanel,
    setActivePanel,
    showThoughts,
    toggleThoughts,
    onControl
}: MainSidebarProps) {
    
    const navItems = [
        { id: "map", icon: MapIcon, label: "Mapa 2D", type: "view" },
        { id: "3d", icon: Box, label: "Vista 3D", type: "view" },
        { id: "graph", icon: Share2, label: "Red Neural", type: "view" },
    ];

    const actionItems = [
        { id: "chat", icon: MessageCircle, label: "Chat", color: "text-cyan-400" },
        { id: "factions", icon: Flag, label: "Sociedades", color: "text-[#ffd600]" },
        { id: "institutions", icon: Landmark, label: "Instituciones", color: "text-emerald-400" },
        { id: "missions", icon: Zap, label: "Misiones", color: "text-[#ffea00]" },
        { id: "architect", icon: Terminal, label: "Arquitecto", color: "text-[#7c4dff]" },
        { id: "chronicle", icon: Book, label: "Crónica", color: "text-[#8d6e63]" },
        { id: "stats", icon: Activity, label: "Estadísticas", color: "text-cyan-400" },
        { id: "config", icon: Settings, label: "Config", color: "text-indigo-400" },
    ];

    return (
        <aside className="w-10 sm:w-12 md:w-16 lg:w-20 bg-black/40 backdrop-blur-xl border-r border-white/5 flex flex-col items-center py-1.5 sm:py-2 md:py-3 gap-0.5 sm:gap-1 md:gap-1.5 z-[60] overflow-y-auto max-h-screen scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent">
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

                {/* Simulation Controls */}
                <div className="flex flex-col bg-white/5 border border-white/10 p-1 rounded-xl shadow-lg">
                    <ControlButton onClick={() => onControl("start")} icon={Play} color="text-green-500" />
                    <ControlButton onClick={() => onControl("pause")} icon={Pause} color="text-yellow-500" />
                    <ControlButton onClick={() => onControl("reset")} icon={RefreshCw} color="text-red-500" />
                </div>
            </div>
        </aside>
    );
}

function NavButton({ active, onClick, icon: Icon, label, color }: any) {
    return (
        <button
            onClick={onClick}
            className={`p-1 sm:p-1.5 md:p-2 rounded-lg sm:rounded-xl transition-all relative group ${active ? 'bg-white/10 text-white shadow-[0_0_15px_rgba(255,255,255,0.05)]' : 'hover:bg-white/5 text-gray-500'}`}
            title={label}
        >
            <Icon className={`w-3 h-3 sm:w-3.5 sm:h-3.5 md:w-4 md:h-4 ${active ? (color || 'text-[#00e676]') : ''}`} />
            {active && (
                <motion.div 
                    layoutId="sidebar-active"
                    className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-3 sm:h-4 md:h-5 bg-[#00e676] rounded-r-full shadow-[0_0_8px_#00e676]"
                />
            )}
            
            <div className="absolute left-full ml-1.5 top-1/2 -translate-y-1/2 px-1 py-0.5 bg-black border border-white/10 rounded text-[6px] sm:text-[7px] md:text-[8px] font-bold uppercase tracking-wide sm:tracking-wider text-white opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity whitespace-normal max-w-[100px] sm:max-w-[120px] z-50">
                {label}
            </div>
        </button>
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
