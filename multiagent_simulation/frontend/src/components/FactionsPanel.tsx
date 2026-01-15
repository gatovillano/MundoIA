'use client';

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Users, Scale, Flag, Brain, X, TrendingUp, Shield } from 'lucide-react';
import useGameStore from '../store/useGameStore';

interface FactionsPanelProps {
    isOpen: boolean;
    onClose: () => void;
}

export default function FactionsPanel({ isOpen, onClose }: FactionsPanelProps) {
    const { civilizaciones, gruposDinamicos, propuestas, agents, step } = useGameStore();
    const [activeTab, setActiveTab] = useState<'factions' | 'proposals'>('factions');

    // Combinar civilizaciones y grupos dinámicos
    const todasLasFacciones = {
        ...civilizaciones,
        ...gruposDinamicos
    };

    const factionsList = Object.entries(todasLasFacciones).map(([id, data]) => ({
        ...data,
        id,
        members: agents.filter(a => a.grupo_id === id || a.civilizacion_id === id).length
    }));

    return (
        <AnimatePresence>
            {isOpen && (
                <motion.div
                    initial={{ x: '100%', opacity: 0 }}
                    animate={{ x: 0, opacity: 1 }}
                    exit={{ x: '100%', opacity: 0 }}
                    transition={{ type: 'spring', damping: 30, stiffness: 300 }}
                    className="fixed right-0 top-0 h-full w-[450px] glass-panel border-l border-white/10 z-[80] flex flex-col shadow-2xl backdrop-blur-3xl"
                >
                    {/* Header */}
                    <div className="p-8 border-b border-white/5 bg-gradient-to-r from-[#7c4dff]/5 to-transparent">
                        <div className="flex justify-between items-start mb-6">
                            <div>
                                <h2 className="text-3xl font-bold text-white tracking-tight font-mono mb-1">DATA <span className="text-[#00e676]">SOCIETAL</span></h2>
                                <p className="text-[10px] text-gray-400 uppercase tracking-[0.2em] font-medium">Panel de Control de Facciones y Leyes</p>
                            </div>
                            <button
                                onClick={onClose}
                                className="p-2 hover:bg-white/10 rounded-full transition-colors text-white/50 hover:text-white"
                            >
                                <X className="w-5 h-5" />
                            </button>
                        </div>

                        {/* Tabs */}
                        <div className="flex gap-1 p-1 bg-black/20 rounded-lg">
                            <TabButton active={activeTab === 'factions'} onClick={() => setActiveTab('factions')} icon={Flag} label="Facciones" />
                            <TabButton active={activeTab === 'proposals'} onClick={() => setActiveTab('proposals')} icon={Scale} label="Legislación" />
                        </div>
                    </div>

                    {/* Content */}
                    <div className="flex-1 overflow-y-auto p-8 custom-scrollbar space-y-4">
                        {activeTab === 'factions' ? (
                            <div className="space-y-4">
                                {factionsList.length === 0 ? (
                                    <EmptyState icon={Users} message="No se han formado facciones." />
                                ) : (
                                    factionsList.map((faction) => (
                                        <motion.div
                                            key={faction.id}
                                            initial={{ opacity: 0, y: 10 }}
                                            animate={{ opacity: 1, y: 0 }}
                                            className="glass-card hover:bg-white/[0.02] p-0 rounded-xl overflow-hidden group border border-white/5"
                                        >
                                            <div className="p-5 flex items-center justify-between relative overflow-hidden">
                                                <div className="absolute top-0 left-0 w-1 h-full" style={{ backgroundColor: faction.color }} />
                                                <div className="relative z-10">
                                                    <div className="flex items-center gap-2 mb-0.5">
                                                        <h3 className="text-lg font-bold text-white">{faction.nombre}</h3>
                                                        {faction.tipo === 'grupo_dinamico' && (
                                                            <span className="px-2 py-0.5 text-[8px] font-bold bg-purple-500/20 text-purple-300 rounded border border-purple-500/30 uppercase tracking-wider">
                                                                Dinámico
                                                            </span>
                                                        )}
                                                    </div>
                                                    <span className="text-[10px] font-mono text-gray-500 uppercase tracking-wider">{faction.id}</span>
                                                </div>
                                                <div className="text-right">
                                                    <div className="text-2xl font-mono font-bold text-white">{faction.members}</div>
                                                    <div className="text-[9px] text-[#7c4dff] uppercase font-bold tracking-wider">Miembros</div>
                                                </div>
                                            </div>
                                            <div className="bg-black/20 p-4 flex gap-6">
                                                <div className="flex items-center gap-2">
                                                    <TrendingUp className="w-3.5 h-3.5 text-[#00e676]" />
                                                    <div className="flex flex-col">
                                                        <span className="text-[9px] text-gray-500 uppercase font-medium">Recursos</span>
                                                        <span className="text-xs font-mono text-[#00e676]">{faction.recursos.toFixed(0)}</span>
                                                    </div>
                                                </div>
                                                <div className="flex items-center gap-2">
                                                    <Shield className="w-3.5 h-3.5 text-[#ff1744]" />
                                                    <div className="flex flex-col">
                                                        <span className="text-[9px] text-gray-500 uppercase font-medium">Influencia</span>
                                                        <span className="text-xs font-mono text-[#ff1744]">NIVEL 1</span>
                                                    </div>
                                                </div>
                                            </div>
                                        </motion.div>
                                    ))
                                )}
                            </div>
                        ) : (
                            <div className="space-y-4">
                                {propuestas.length === 0 ? (
                                    <EmptyState icon={Scale} message="Sin actividad legislativa." />
                                ) : (
                                    propuestas.map((prop) => (
                                        <motion.div
                                            key={prop.id}
                                            initial={{ opacity: 0, x: 20 }}
                                            animate={{ opacity: 1, x: 0 }}
                                            className="glass-card p-5 rounded-xl border border-white/5 space-y-4 group"
                                        >
                                            <div className="flex justify-between items-start">
                                                <div className="flex items-center gap-2">
                                                    <div className="p-1.5 rounded bg-[#7c4dff]/20 text-[#7c4dff]">
                                                        <Scale className="w-3.5 h-3.5" />
                                                    </div>
                                                    <span className="text-[10px] font-bold text-[#7c4dff] uppercase tracking-widest">{prop.tipo}</span>
                                                </div>
                                                <StatusBadge status={prop.estado} />
                                            </div>

                                            <p className="text-sm text-gray-300 leading-relaxed font-mono pl-4 border-l-2 border-white/10 italic">
                                                "{prop.texto}"
                                            </p>

                                            <div className="pt-4 border-t border-white/5 flex justify-between items-end">
                                                <div className="flex items-center gap-2">
                                                    <Brain className="w-3.5 h-3.5 text-gray-500" />
                                                    <span className="text-xs text-gray-400 font-mono">Agente {prop.proponente_id}</span>
                                                </div>
                                                <div className="flex items-center gap-3">
                                                    <div className="flex items-center gap-1.5 text-[#00e676] text-xs font-mono">
                                                        <span>SI</span>
                                                        <span className="font-bold">{Object.values(prop.votos).filter(v => v === 'si').length}</span>
                                                    </div>
                                                    <div className="w-px h-3 bg-white/20" />
                                                    <div className="flex items-center gap-1.5 text-[#ff1744] text-xs font-mono">
                                                        <span>NO</span>
                                                        <span className="font-bold">{Object.values(prop.votos).filter(v => v === 'no').length}</span>
                                                    </div>
                                                </div>
                                            </div>
                                        </motion.div>
                                    ))
                                )}
                            </div>
                        )}
                    </div>

                    {/* Footer Info */}
                    <div className="p-6 border-t border-white/5 bg-black/40 text-[10px] flex justify-between items-center text-gray-500 font-mono tracking-wider">
                        <span>Paso de Simulación: <span className="text-white">{step}</span></span>
                        <div className="flex gap-2 items-center">
                            <div className="w-1.5 h-1.5 rounded-full bg-[#00e676] animate-pulse" />
                            <span>SISTEMA ACTIVO</span>
                        </div>
                    </div>
                </motion.div>
            )}
        </AnimatePresence>
    );
}

// Subcomponentes
function TabButton({ active, onClick, icon: Icon, label }: any) {
    return (
        <button
            onClick={onClick}
            className={`flex-1 py-3 rounded-md text-xs font-bold uppercase tracking-wider transition-all flex items-center justify-center gap-2 ${active
                ? 'bg-white/10 text-white shadow-sm'
                : 'text-gray-500 hover:text-gray-300 hover:bg-white/5'
                }`}
        >
            <Icon className="w-4 h-4" />
            {label}
        </button>
    )
}

function EmptyState({ icon: Icon, message }: any) {
    return (
        <div className="py-20 text-center border border-dashed border-white/10 rounded-xl">
            <Icon className="w-10 h-10 text-gray-700 mx-auto mb-4 opacity-50" />
            <p className="text-gray-500 text-xs font-mono uppercase tracking-wider">{message}</p>
        </div>
    )
}

function StatusBadge({ status }: { status: string }) {
    let colors = "";
    switch (status) {
        case 'aprobada': colors = "bg-[#00e676]/20 border-[#00e676]/30 text-[#00e676]"; break;
        case 'rechazada': colors = "bg-[#ff1744]/20 border-[#ff1744]/30 text-[#ff1744]"; break;
        default: colors = "bg-[#ffd600]/20 border-[#ffd600]/30 text-[#ffd600]";
    }
    return (
        <span className={`px-2.5 py-1 rounded border text-[9px] font-bold uppercase tracking-widest ${colors}`}>
            {status}
        </span>
    )
}
