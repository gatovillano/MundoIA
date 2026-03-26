'use client';

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Users, Scale, Flag, Brain, X, TrendingUp, Shield, Handshake } from 'lucide-react';
import useGameStore from '../store/useGameStore';

interface FactionsPanelProps {
    isOpen: boolean;
    onClose: () => void;
}

export default function FactionsPanel({ isOpen, onClose }: FactionsPanelProps) {
    const { civilizaciones, gruposDinamicos, propuestas, relacionesGrupos, agents, step, relationships } = useGameStore();
    const [activeTab, setActiveTab] = useState<'groups' | 'proposals' | 'diplomacy'>('groups');

    const civFactions = Object.entries(civilizaciones || {}).map(([id, data]: [string, any]) => ({
        ...data,
        id,
        tipo: data.tipo || 'civilizacion',
        members: typeof data.members === 'number' ? data.members : Array.isArray(data.members) ? data.members.length : agents.filter(a => a.civilizacion_id === id || a.grupo_id === id).length
    }));

    const civFactionIds = new Set(civFactions.map(f => f.id));

    const grupoFactions = Object.entries(gruposDinamicos || {}).filter(([id]) => !civFactionIds.has(id)).map(([id, data]: [string, any]) => ({
        ...data,
        id,
        tipo: data.tipo || 'grupo_dinamico',
        members: typeof data.members === 'number' ? data.members : Array.isArray(data.members) ? data.members.length : agents.filter(a => a.grupo_id === id).length
    }));

    const factionsList = [...civFactions, ...grupoFactions];

    return (
        <div className="flex flex-col h-full">
            {/* Tabs */}
            <div className="p-1 bg-black/20 rounded-xl mb-6 flex gap-1 border border-white/5">
                <TabButton active={activeTab === 'groups'} onClick={() => setActiveTab('groups')} icon={Flag} label="Grupos" />
                <TabButton active={activeTab === 'proposals'} onClick={() => setActiveTab('proposals')} icon={Scale} label="Leyes" />
                <TabButton active={activeTab === 'diplomacy'} onClick={() => setActiveTab('diplomacy')} icon={Handshake} label="Diplomacia" />
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto custom-scrollbar space-y-4 pr-1">
                {activeTab === 'groups' && (
                    <div className="space-y-4">
                        {factionsList.length === 0 ? (
                            <EmptyState icon={Users} message="No se han detectado grupos activos." />
                        ) : (
                            factionsList.map((faction) => {
                                const membersCount = Array.isArray(faction.members) ? faction.members.length : faction.members;
                                const factionName = faction.nombre || faction.name || faction.id;
                                const resources = faction.recursos || faction.resources || faction.recursos_actuales || 0;

                                return (
                                    <motion.div
                                        key={faction.id}
                                        initial={{ opacity: 0, y: 10 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        className="glass-card p-0 rounded-2xl overflow-hidden group border border-white/5"
                                    >
                                        <div className="p-5 flex items-center justify-between relative">
                                            <div className="absolute top-0 left-0 w-1 h-full" style={{ backgroundColor: faction.color || '#7c4dff' }} />
                                            <div>
                                                <div className="flex items-center gap-2 mb-0.5">
                                                    <h3 className="text-lg font-bold text-white font-outfit">{factionName}</h3>
                                                    {faction.tipo === 'grupo_dinamico' && (
                                                        <span className="px-2 py-0.5 text-[8px] font-bold bg-purple-500/20 text-purple-300 rounded border border-purple-500/30 uppercase tracking-widest">
                                                            Dinámico
                                                        </span>
                                                    )}
                                                </div>
                                                {faction.descripcion && (
                                                    <p className="text-[10px] text-gray-400 italic mb-1 line-clamp-2 max-w-[200px]">
                                                        "{faction.descripcion}"
                                                    </p>
                                                )}
                                                <span className="text-[10px] font-mono text-gray-500 uppercase tracking-wider">{faction.id}</span>
                                            </div>
                                            <div className="text-right">
                                                <div className="text-2xl font-mono font-bold text-white">{membersCount}</div>
                                                <div className="text-[9px] text-[#7c4dff] uppercase font-bold tracking-wider opacity-60">Miembros</div>
                                            </div>
                                        </div>
                                        <div className="bg-black/40 p-4 flex gap-6 border-t border-white/5">
                                            <div className="flex items-center gap-2">
                                                <TrendingUp className="w-3.5 h-3.5 text-[#00e676]" />
                                                <div className="flex flex-col">
                                                    <span className="text-[9px] text-gray-500 uppercase font-medium">Recursos</span>
                                                    <span className="text-xs font-mono text-[#00e676]">
                                                        {Number(resources).toFixed(0)}
                                                    </span>
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-2">
                                                <Shield className="w-3.5 h-3.5 text-[#ff1744]" />
                                                <div className="flex flex-col">
                                                    <span className="text-[9px] text-gray-500 uppercase font-medium">Estabilidad</span>
                                                    <span className="text-xs font-mono text-[#ff1744]">
                                                        {(faction.estabilidad || 1.0) * 100}%
                                                    </span>
                                                </div>
                                            </div>
                                        </div>
                                    </motion.div>
                                );
                            })
                        )}
                    </div>
                )}

                {activeTab === 'proposals' && (
                    <div className="space-y-4">
                        {(!propuestas || propuestas.length === 0) ? (
                            <EmptyState icon={Scale} message="Sin actividad legislativa." />
                        ) : (
                            propuestas.map((prop: any) => (
                                <motion.div
                                    key={prop.id}
                                    initial={{ opacity: 0, x: 20 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    className="glass-card p-5 rounded-2xl border border-white/5 space-y-4 group"
                                >
                                    <div className="flex justify-between items-start">
                                        <div className="flex items-center gap-2">
                                            <div className="p-1.5 rounded bg-[#7c4dff]/20 text-[#7c4dff]">
                                                <Scale className="w-3.5 h-3.5" />
                                            </div>
                                            <span className="text-[10px] font-bold text-[#7c4dff] uppercase tracking-widest">{prop.tipo === 'asamblea' ? 'ASAMBLEA' : (prop.tipo || 'LEY')}</span>
                                        </div>
                                        <StatusBadge status={prop.estado || 'pendiente'} />
                                    </div>

                                    <div className="space-y-2">
                                        <h4 className="text-sm font-bold text-white leading-tight font-outfit">
                                            {prop.tipo === 'asamblea' ? `Debate: ${prop.texto}` : (prop.titulo || "Propuesta de Ley")}
                                        </h4>
                                        <p className="text-[11px] text-gray-400 leading-relaxed font-mono pl-4 border-l border-white/10 italic">
                                            {prop.tipo === 'asamblea' ? prop.texto : (prop.contenido || prop.texto)}
                                        </p>
                                    </div>

                                    <div className="pt-4 border-t border-white/5 flex justify-between items-end">
                                        <div className="flex items-center gap-2">
                                            <Brain className="w-3.5 h-3.5 text-gray-500" />
                                            <span className="text-xs text-gray-400 font-mono">Proponente: {prop.proponente_id || 'MundoIA'}</span>
                                        </div>
                                        {/* Votos */}
                                        <div className="flex items-center gap-3">
                                            <div className="flex items-center gap-1.5 text-[#00e676] text-xs font-mono">
                                                <span>SI</span>
                                                <span className="font-bold">{prop.tipo === 'asamblea' ? prop.votos_si : Object.values(prop.votos || {}).filter(v => v === 'si' || v === 'yes' || v === true).length}</span>
                                            </div>
                                            <div className="w-px h-3 bg-white/20" />
                                            <div className="flex items-center gap-1.5 text-[#ff1744] text-xs font-mono">
                                                <span>NO</span>
                                                <span className="font-bold">{prop.tipo === 'asamblea' ? prop.votos_no : Object.values(prop.votos || {}).filter(v => v === 'no' || v === false).length}</span>
                                            </div>
                                        </div>
                                    </div>
                                </motion.div>
                            ))
                        )}
                    </div>
                )}

                {activeTab === 'diplomacy' && (
                    <div className="space-y-4">
                        {(!relationships || relationships.filter((r: any) => r.type === 'alianza' || r.type === 'alliance').length === 0) && (!relacionesGrupos || Object.keys(relacionesGrupos).length === 0) ? (
                            <EmptyState icon={Handshake} message="No hay alianzas formadas." />
                        ) : (
                            <div className="space-y-4">
                                {/* Relaciones entre Grupos (Tratados) */}
                                {Object.entries(relacionesGrupos || {}).map(([key, affinity], idx) => {
                                    const [g1, g2] = key.split(':');
                                    const n1 = civilizaciones[g1]?.nombre || gruposDinamicos[g1]?.nombre || g1;
                                    const n2 = civilizaciones[g2]?.nombre || gruposDinamicos[g2]?.nombre || g2;
                                    const c1 = civilizaciones[g1]?.color || gruposDinamicos[g1]?.color || '#fff';
                                    const c2 = civilizaciones[g2]?.color || gruposDinamicos[g2]?.color || '#fff';

                                    return (
                                        <motion.div
                                            key={`group-rel-${idx}`}
                                            initial={{ opacity: 0, scale: 0.95 }}
                                            animate={{ opacity: 1, scale: 1 }}
                                            className="glass-card p-4 rounded-2xl border border-white/5 flex flex-col gap-3"
                                        >
                                            <div className="flex items-center justify-between">
                                                <div className="flex items-center gap-2">
                                                    <div className="w-2 h-2 rounded-full" style={{ backgroundColor: c1 }} />
                                                    <span className="text-xs font-bold text-white uppercase">{n1}</span>
                                                </div>
                                                <div className="px-2 py-0.5 rounded bg-white/5 text-[9px] font-mono text-gray-400">TRATADO</div>
                                                <div className="flex items-center gap-2">
                                                    <span className="text-xs font-bold text-white uppercase">{n2}</span>
                                                    <div className="w-2 h-2 rounded-full" style={{ backgroundColor: c2 }} />
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-3">
                                                <div className="flex-1 h-1 bg-white/10 rounded-full overflow-hidden">
                                                    <motion.div
                                                        className={`h-full ${affinity > 0 ? 'bg-[#00e676]' : 'bg-[#ff1744]'}`}
                                                        initial={{ width: 0 }}
                                                        animate={{ width: `${Math.abs(affinity) * 100}%` }}
                                                    />
                                                </div>
                                                <span className={`text-[10px] font-mono font-bold ${affinity > 0 ? 'text-[#00e676]' : 'text-[#ff1744]'}`}>
                                                    {affinity > 0 ? '+' : ''}{(affinity * 100).toFixed(0)}%
                                                </span>
                                            </div>
                                        </motion.div>
                                    );
                                })}

                                {/* Alianzas entre Agentes */}
                                {relationships.filter((r: any) => r.type === 'alianza' || r.type === 'alliance').map((rel: any, idx: number) => (
                                    <motion.div
                                        key={`agent-rel-${idx}`}
                                        initial={{ opacity: 0, x: -20 }}
                                        animate={{ opacity: 1, x: 0 }}
                                        className="glass-card p-4 rounded-2xl border border-white/5 flex items-center justify-between"
                                    >
                                        <div className="flex items-center gap-4">
                                            <div className="p-2 bg-[#ffd600]/20 rounded-full text-[#ffd600]">
                                                <Handshake className="w-4 h-4" />
                                            </div>
                                            <div className="flex flex-col">
                                                <div className="flex items-center gap-2 text-sm font-bold text-white">
                                                    <span>Agente {rel.source}</span>
                                                    <span className="text-gray-500 text-xs">↔</span>
                                                    <span>Agente {rel.target}</span>
                                                </div>
                                                <span className="text-[10px] text-gray-400 uppercase tracking-widest mt-0.5">Alianza Estratégica</span>
                                            </div>
                                        </div>
                                        <div className="px-2.5 py-1 rounded-lg bg-[#ffd600]/10 border border-[#ffd600]/20 text-[#ffd600] text-[9px] font-bold">
                                            ACTIVA
                                        </div>
                                    </motion.div>
                                ))}
                            </div>
                        )}
                    </div>
                )}
            </div>

            {/* Footer Info */}
            <div className="pt-6 mt-auto border-t border-white/5 flex justify-between items-center text-[10px] text-gray-500 font-mono tracking-wider">
                <span>Turno: <span className="text-white">{step}</span></span>
                <div className="flex gap-2 items-center">
                    <div className="w-1.5 h-1.5 rounded-full bg-[#00e676] animate-pulse" />
                    <span className="opacity-60">SISTEMA NOMINAL</span>
                </div>
            </div>
        </div>
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
