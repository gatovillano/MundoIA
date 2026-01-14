'use client';

import React, { useState } from 'react';
import { useSimulationWebSocket } from '../hooks/useSimulationWebSocket';
import { useSimulationStore } from '../store/useSimulationStore';
import { Activity, LayoutDashboard, Settings, User, Play, Pause, RotateCcw } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import SimulationView from './SimulationView';
import AnalyticsDashboard from './AnalyticsDashboard';
import ArchitectPanel from './ArchitectPanel';
import AgentDetail from './AgentDetail';
import LogPanel from './LogPanel';

export default function MainLayout({ children }: { children: React.ReactNode }) {
    const [activeTab, setActiveTab] = useState('simulation');
    useSimulationWebSocket('ws://localhost:8001/ws');
    const { currentStep, isPaused, togglePause } = useSimulationStore();

    const tabs = [
        { id: 'simulation', icon: Activity, label: 'Simulación' },
        { id: 'analytics', icon: LayoutDashboard, label: 'Analíticas' },
        { id: 'architect', icon: Settings, label: 'Arquitecto' },
    ];

    return (
        <div className="flex h-screen w-screen overflow-hidden bg-[#05060a] text-slate-200">
            {/* Scanline Effect */}
            <div className="scanline" />

            {/* Sidebar HUD */}
            <aside className="w-20 flex flex-col items-center py-8 border-r border-cyan-500/20 bg-black/40 backdrop-blur-2xl z-50">
                <div className="mb-12">
                    <motion.div
                        animate={{ rotate: 360 }}
                        transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
                        className="w-12 h-12 rounded-lg border-2 border-cyan-500/50 flex items-center justify-center shadow-[0_0_15px_rgba(0,242,255,0.3)]"
                    >
                        <Activity className="text-cyan-400" size={24} />
                    </motion.div>
                </div>

                <nav className="flex flex-col gap-8 flex-1">
                    {tabs.map((tab) => (
                        <button
                            key={tab.id}
                            onClick={() => setActiveTab(tab.id)}
                            className={`p-3 rounded-lg transition-all duration-300 group relative border ${activeTab === tab.id
                                ? 'bg-cyan-500/20 border-cyan-500 text-cyan-400 shadow-[0_0_10px_rgba(0,242,255,0.2)]'
                                : 'border-transparent text-slate-500 hover:text-cyan-300 hover:bg-cyan-500/5'
                                }`}
                        >
                            <tab.icon size={24} />
                            <span className="absolute left-full ml-4 px-3 py-1 bg-black/80 border border-cyan-500/30 text-cyan-400 text-[10px] font-cyber rounded opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity whitespace-nowrap z-[100]">
                                {tab.label}
                            </span>
                        </button>
                    ))}
                </nav>

                <div className="mt-auto flex flex-col gap-6">
                    <button className="text-slate-500 hover:text-cyan-400 transition-colors p-2 rounded-lg border border-transparent hover:border-cyan-500/30">
                        <User size={24} />
                    </button>
                </div>
            </aside>

            {/* Main Content */}
            <main className="flex-1 relative flex flex-col overflow-hidden">
                {/* Header HUD */}
                <header className="h-16 border-b border-cyan-500/20 flex items-center justify-between px-8 bg-black/30 backdrop-blur-xl z-40">
                    <div className="flex items-center gap-6">
                        <div className="flex flex-col">
                            <h1 className="text-lg font-cyber gradient-text tracking-tighter">
                                MUNDO.IA <span className="text-[10px] text-cyan-500/70 ml-1 opacity-70">SYSTEM_v2.0</span>
                            </h1>
                            <div className="h-[2px] w-full bg-gradient-to-r from-cyan-500 to-transparent" />
                        </div>

                        <div className="flex items-center gap-4 bg-cyan-500/5 border border-cyan-500/20 px-4 py-1.5 rounded-md">
                            <div className="flex items-center gap-2 text-[11px] font-cyber text-cyan-400/80">
                                <span className="w-1.5 h-1.5 rounded-full bg-cyan-500 animate-pulse shadow-[0_0_5px_rgba(0,242,255,0.8)]" />
                                STATUS: <span className="text-cyan-400">ONLINE</span>
                            </div>
                            <div className="w-[1px] h-3 bg-cyan-500/20" />
                            <div className="text-[11px] font-cyber text-cyan-400/80">
                                STEP: <span className="text-white">{currentStep}</span>
                            </div>
                        </div>
                    </div>

                    <div className="flex items-center gap-4">
                        <div className="flex items-center gap-2">
                            <button
                                onClick={togglePause}
                                className={`flex items-center gap-2 px-4 py-1.5 rounded border transition-all font-cyber text-[10px] ${isPaused
                                    ? 'bg-cyan-500 text-black border-cyan-400 shadow-[0_0_15px_rgba(0,242,255,0.4)]'
                                    : 'bg-black/40 border-cyan-500/30 text-cyan-400 hover:border-cyan-500'
                                    }`}
                            >
                                {isPaused ? <Play size={14} fill="currentColor" /> : <Pause size={14} fill="currentColor" />}
                                {isPaused ? 'RESUME' : 'PAUSE'}
                            </button>

                            <button
                                onClick={async () => {
                                    if (confirm('¿REBOOT SYSTEM? ALL DATA WILL BE WIPED.')) {
                                        await fetch('http://localhost:8001/reset', { method: 'POST' });
                                    }
                                }}
                                className="flex items-center gap-2 px-4 py-1.5 rounded border border-rose-500/30 text-rose-500 hover:bg-rose-500/10 transition-all font-cyber text-[10px]"
                            >
                                <RotateCcw size={14} />
                                RESET
                            </button>
                        </div>
                    </div>
                </header>

                {/* Content Area */}
                <div className="flex-1 overflow-hidden relative">
                    <AnimatePresence mode="wait">
                        <motion.div
                            key={activeTab}
                            initial={{ opacity: 0, scale: 0.98 }}
                            animate={{ opacity: 1, scale: 1 }}
                            exit={{ opacity: 0, scale: 1.02 }}
                            transition={{ duration: 0.3, ease: "easeOut" }}
                            className="h-full w-full"
                        >
                            {activeTab === 'simulation' && <SimulationView />}
                            {activeTab === 'analytics' && <AnalyticsDashboard />}
                            {activeTab === 'architect' && <ArchitectPanel />}
                        </motion.div>
                    </AnimatePresence>

                    <AgentDetail />
                    <LogPanel />
                </div>
            </main>
        </div>
    );
}
