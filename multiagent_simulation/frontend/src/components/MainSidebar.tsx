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
        <aside className="w-20 bg-black/40 backdrop-blur-xl border-r border-white/5 flex flex-col items-center py-8 gap-10 z-[60]">
            <div className="flex flex-col items-center gap-2 mb-4">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#7c4dff] to-[#00e676] flex items-center justify-center shadow-[0_0_20px_rgba(124,77,255,0.3)]">
                    <span className="text-black font-black text-xs">MIA</span>
                </div>
            </div>

            {/* View Switcher */}
            <div className="flex flex-col gap-3">
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

            <div className="w-8 h-px bg-white/10" />

            {/* Panels Switcher */}
            <div className="flex flex-col gap-3">
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

            <div className="mt-auto flex flex-col gap-6 pb-4">
                {/* Mind Toggle */}
                <button
                    onClick={toggleThoughts}
                    className={`p-3 rounded-xl border transition-all duration-500 shadow-lg flex flex-col items-center gap-1.5 ${showThoughts ? 'bg-[#7c4dff]/20 border-[#7c4dff]/40 text-[#7c4dff]' : 'bg-white/5 border-white/10 text-white/30 hover:text-white/60'}`}
                    title={showThoughts ? 'Mind ON' : 'Mind OFF'}
                >
                    <Brain className={`w-5 h-5 ${showThoughts ? 'animate-pulse' : ''}`} />
                </button>

                {/* Simulation Controls */}
                <div className="flex flex-col bg-white/5 border border-white/10 p-1 rounded-2xl shadow-xl">
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
            className={`p-3.5 rounded-2xl transition-all relative group ${active ? 'bg-white/10 text-white shadow-[0_0_15px_rgba(255,255,255,0.05)]' : 'hover:bg-white/5 text-gray-500'}`}
            title={label}
        >
            <Icon className={`w-5 h-5 ${active ? (color || 'text-[#00e676]') : ''}`} />
            {active && (
                <motion.div 
                    layoutId="sidebar-active"
                    className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 bg-[#00e676] rounded-r-full shadow-[0_0_8px_#00e676]"
                />
            )}
            
            <div className="absolute left-full ml-4 px-3 py-1.5 bg-black border border-white/10 rounded-lg text-[10px] font-bold uppercase tracking-widest text-white opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity whitespace-nowrap z-50">
                {label}
            </div>
        </button>
    );
}

function ControlButton({ onClick, icon: Icon, color }: any) {
    return (
        <button 
            onClick={onClick} 
            className={`p-3 hover:bg-white/5 rounded-xl transition-all ${color} active:scale-90`}
        >
            <Icon className="w-4 h-4" />
        </button>
    );
}
