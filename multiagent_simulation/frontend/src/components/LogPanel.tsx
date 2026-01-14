'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useSimulationStore } from '../store/useSimulationStore';
import { MessageSquare, Terminal, ChevronDown, ChevronUp, Filter } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export default function LogPanel() {
    const { logs } = useSimulationStore();
    const [isExpanded, setIsExpanded] = useState(false);
    const [filter, setFilter] = useState<'all' | 'dialogo'>('all');
    const scrollRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [logs, isExpanded]);

    // Group logs by step
    const groupedLogs: { [key: number]: any[] } = {};
    logs.forEach(log => {
        const step = log.paso || 0;
        if (!groupedLogs[step]) groupedLogs[step] = [];
        groupedLogs[step].push(log);
    });

    const steps = Object.keys(groupedLogs).map(Number).sort((a, b) => b - a);

    return (
        <motion.div
            initial={false}
            animate={{ height: isExpanded ? '400px' : '48px' }}
            className="absolute bottom-0 left-20 right-0 glass border-t border-cyan-500/30 z-40 flex flex-col transition-all duration-300"
        >
            {/* Header */}
            <div className="h-12 px-6 flex items-center justify-between bg-cyan-500/5 cursor-pointer" onClick={() => setIsExpanded(!isExpanded)}>
                <div className="flex items-center gap-4">
                    <div className="flex items-center gap-2 text-cyan-400 font-cyber text-[10px]">
                        <Terminal size={14} />
                        <span>SYSTEM_LOG_STREAM</span>
                    </div>
                    <div className="h-3 w-[1px] bg-cyan-500/20" />
                    <div className="flex items-center gap-2">
                        <button 
                            onClick={(e) => { e.stopPropagation(); setFilter(filter === 'all' ? 'dialogo' : 'all'); }}
                            className={`px-2 py-0.5 rounded text-[9px] font-cyber border transition-all ${filter === 'dialogo' 
                                ? 'bg-cyan-500 text-black border-cyan-400' 
                                : 'bg-black/40 border-cyan-500/30 text-cyan-500/70'}`}
                        >
                            <Filter size={10} className="inline mr-1" />
                            {filter === 'dialogo' ? 'MODE: DIALOGUE' : 'MODE: ALL_EVENTS'}
                        </button>
                    </div>
                </div>
                {isExpanded ? <ChevronDown size={18} className="text-cyan-500" /> : <ChevronUp size={18} className="text-cyan-500" />}
            </div>

            {/* Content */}
            <div ref={scrollRef} className="flex-1 overflow-y-auto custom-scrollbar p-4 space-y-6 bg-black/20">
                <AnimatePresence>
                    {steps.map((step) => {
                        const stepLogs = groupedLogs[step].filter(l => filter === 'all' || l.categoria === 'dialogo');
                        if (stepLogs.length === 0) return null;

                        return (
                            <motion.div 
                                key={step}
                                initial={{ opacity: 0, x: -10 }}
                                animate={{ opacity: 1, x: 0 }}
                                className="space-y-2"
                            >
                                <div className="flex items-center gap-2">
                                    <div className="px-2 py-0.5 bg-cyan-500/10 border border-cyan-500/30 rounded text-[9px] font-cyber text-cyan-500">
                                        STEP_{step.toString().padStart(4, '0')}
                                    </div>
                                    <div className="flex-1 h-[1px] bg-gradient-to-r from-cyan-500/20 to-transparent" />
                                </div>
                                
                                <div className="space-y-1.5 pl-2">
                                    {stepLogs.map((log, i) => (
                                        <div key={i} className="flex gap-3 text-[11px] group">
                                            <span className="text-slate-600 font-mono shrink-0">[{new Date().toLocaleTimeString([], { hour12: false })}]</span>
                                            <div className="flex flex-col gap-0.5">
                                                <div className="flex items-center gap-2">
                                                    {log.categoria === 'dialogo' && <MessageSquare size={10} className="text-cyan-400" />}
                                                    <span className={`font-medium ${
                                                        log.categoria === 'social' ? 'text-emerald-400' :
                                                        log.categoria === 'conflict' ? 'text-rose-400' :
                                                        log.categoria === 'dialogo' ? 'text-cyan-300' :
                                                        'text-slate-400'
                                                    }`}>
                                                        {log.mensaje}
                                                    </span>
                                                </div>
                                                {log.pensamiento && (
                                                    <div className="text-[10px] text-slate-500 italic pl-4 border-l border-white/5 bg-white/2 py-0.5 rounded-r">
                                                        <span className="text-cyan-500/30 font-cyber mr-1">THOUGHT:</span>
                                                        {log.pensamiento}
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </motion.div>
                        );
                    })}
                </AnimatePresence>
            </div>
        </motion.div>
    );
}
