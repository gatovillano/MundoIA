'use client';

import React from 'react';
import { useSimulationStore } from '../store/useSimulationStore';
import { X, Heart, Zap, Shield, Users, Brain, Target, TrendingUp, User } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export default function AgentDetail() {
    const { agents, selectedAgentId, setSelectedAgent } = useSimulationStore();
    const agent = selectedAgentId ? agents.get(selectedAgentId) : null;

    if (!agent) return null;

    const stats = [
        { label: 'SALUD', value: agent.necesidades.salud || 100, icon: Heart, color: 'text-rose-500', bg: 'bg-rose-500' },
        { label: 'RECURSOS', value: agent.recursos, icon: Zap, color: 'text-amber-500', bg: 'bg-amber-500' },
        { label: 'SEGURIDAD', value: agent.necesidades.seguridad || 50, icon: Shield, color: 'text-blue-500', bg: 'bg-blue-500' },
        { label: 'SOCIAL', value: agent.necesidades.social || 50, icon: Users, color: 'text-cyan-500', bg: 'bg-cyan-500' },
    ];

    return (
        <AnimatePresence>
            {agent && (
                <motion.div
                    initial={{ x: 400, opacity: 0 }}
                    animate={{ x: 0, opacity: 1 }}
                    exit={{ x: 400, opacity: 0 }}
                    className="absolute top-20 right-8 w-80 glass border-cyan-500/30 z-50 flex flex-col max-h-[calc(100vh-120px)]"
                >
                    {/* Header */}
                    <div className="p-4 border-b border-cyan-500/20 flex items-center justify-between bg-cyan-500/5">
                        <div className="flex flex-col">
                            <span className="text-[10px] font-cyber text-cyan-500/50">AGENT_PROFILE</span>
                            <h2 className="text-lg font-cyber text-cyan-400">{agent.id}</h2>
                        </div>
                        <button
                            onClick={() => setSelectedAgent(null)}
                            className="p-1 hover:bg-rose-500/20 text-slate-400 hover:text-rose-500 rounded transition-colors border-none"
                        >
                            <X size={18} />
                        </button>
                    </div>

                    <div className="flex-1 overflow-y-auto custom-scrollbar p-4 space-y-6">
                        {/* Identity Card */}
                        <div className="space-y-3">
                            <div className="flex items-center gap-3 p-3 bg-white/5 rounded-lg border border-white/10">
                                <div className="w-12 h-12 rounded bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center">
                                    <User className="text-cyan-400" size={24} />
                                </div>
                                <div>
                                    <div className="text-[10px] font-cyber text-slate-500">ROLE_ASSIGNMENT</div>
                                    <div className="text-sm font-cyber text-white">{agent.rol || 'UNASSIGNED'}</div>
                                    <div className="text-[10px] font-cyber text-cyan-500/70">{agent.grupo_id || 'NO_FACTION'}</div>
                                </div>
                            </div>
                        </div>

                        {/* Stats Grid */}
                        <div className="grid grid-cols-2 gap-3">
                            {stats.map((stat) => (
                                <div key={stat.label} className="p-3 bg-white/5 rounded-lg border border-white/5 space-y-2">
                                    <div className="flex items-center gap-2">
                                        <stat.icon size={14} className={stat.color} />
                                        <span className="text-[9px] font-cyber text-slate-500">{stat.label}</span>
                                    </div>
                                    <div className="flex flex-col gap-1">
                                        <span className="text-sm font-mono text-white">{stat.value.toFixed(1)}</span>
                                        <div className="h-1 w-full bg-white/10 rounded-full overflow-hidden">
                                            <motion.div
                                                initial={{ width: 0 }}
                                                animate={{ width: `${Math.min(100, stat.value)}%` }}
                                                className={`h-full ${stat.bg} shadow-[0_0_5px_rgba(0,0,0,0.5)]`}
                                            />
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>

                        {/* Personality & Traits */}
                        <div className="space-y-3">
                            <div className="flex items-center gap-2 text-[10px] font-cyber text-cyan-500/50">
                                <Brain size={12} />
                                <span>COGNITIVE_TRAITS</span>
                            </div>
                            <div className="flex flex-wrap gap-2">
                                {Object.entries(agent.personalidad).map(([trait, value]: [string, any]) => (
                                    <div key={trait} className="px-2 py-1 bg-cyan-500/5 border border-cyan-500/20 rounded text-[9px] font-cyber text-cyan-400">
                                        {trait.toUpperCase()}: {(value * 100).toFixed(0)}%
                                    </div>
                                ))}
                            </div>
                        </div>

                        {/* Recent Memories */}
                        <div className="space-y-3">
                            <div className="flex items-center gap-2 text-[10px] font-cyber text-cyan-500/50">
                                <Target size={12} />
                                <span>MEMORY_LOGS</span>
                            </div>
                            <div className="space-y-2">
                                {agent.memorias?.slice(-3).reverse().map((mem, i) => (
                                    <div key={i} className="p-2 bg-white/5 border-l-2 border-cyan-500 rounded-r text-[10px] text-slate-400 leading-relaxed">
                                        {mem.contenido}
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>

                    {/* Footer Stats */}
                    <div className="p-4 border-t border-cyan-500/20 bg-black/40 flex justify-between items-center">
                        <div className="flex items-center gap-2">
                            <TrendingUp size={14} className="text-cyan-400" />
                            <span className="text-[10px] font-cyber text-slate-500">RANK: <span className="text-white">{agent.rango.toFixed(2)}</span></span>
                        </div>
                        <div className="text-[10px] font-cyber text-cyan-500/50 animate-pulse">SYSTEM_SYNC_ACTIVE</div>
                    </div>
                </motion.div>
            )}
        </AnimatePresence>
    );
}
