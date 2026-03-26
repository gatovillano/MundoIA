'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { Landmark, GraduationCap, Cross, FlaskConical, Building2, Users, TrendingUp, MapPin } from 'lucide-react';
import useGameStore from '../store/useGameStore';

export default function InstitutionsPanel() {
    const { instituciones } = useGameStore();

    const instList = Object.values(instituciones || {});

    const getIcon = (tipo: string) => {
        switch (tipo) {
            case 'EDUCATIVA': return GraduationCap;
            case 'FINANCIERA': return Landmark;
            case 'SANITARIA': return Cross;
            case 'CIENTIFICA': return FlaskConical;
            case 'RELIGIOSA': return Cross;
            default: return Building2;
        }
    };

    const getColor = (tipo: string) => {
        switch (tipo) {
            case 'EDUCATIVA': return 'text-blue-400 bg-blue-500/10 border-blue-500/20';
            case 'FINANCIERA': return 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20';
            case 'SANITARIA': return 'text-rose-400 bg-rose-500/10 border-rose-500/20';
            case 'CIENTIFICA': return 'text-cyan-400 bg-cyan-500/10 border-cyan-500/20';
            case 'RELIGIOSA': return 'text-amber-400 bg-amber-500/10 border-amber-500/20';
            default: return 'text-gray-400 bg-gray-500/10 border-gray-500/20';
        }
    };

    return (
        <div className="flex flex-col h-full">
            <header className="mb-6">
                <h2 className="text-2xl font-bold text-white mb-2 font-outfit">Instituciones</h2>
                <p className="text-gray-400 text-sm">Organizaciones formales y pilares de la civilización.</p>
            </header>

            <div className="flex-1 overflow-y-auto custom-scrollbar space-y-4 pr-1">
                {instList.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-12 px-6 text-center bg-white/5 rounded-3xl border border-white/5 border-dashed">
                        <div className="w-16 h-16 rounded-2xl bg-white/5 flex items-center justify-center mb-4">
                            <Building2 className="w-8 h-8 text-white/20" />
                        </div>
                        <h3 className="text-white font-bold mb-1">Sin instituciones aún</h3>
                        <p className="text-gray-500 text-xs">Los agentes deben alcanzar suficiente prosperidad para fundar organizaciones formales.</p>
                    </div>
                ) : (
                    instList.map((inst: any) => {
                        const Icon = getIcon(inst.tipo);
                        const colorClass = getColor(inst.tipo);

                        return (
                            <motion.div
                                key={inst.id}
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                className="glass-card p-0 rounded-2xl overflow-hidden border border-white/5 group"
                            >
                                <div className="p-5 flex items-start justify-between">
                                    <div className="flex gap-4">
                                        <div className={`w-12 h-12 rounded-xl flex items-center justify-center border ${colorClass}`}>
                                            <Icon className="w-6 h-6" />
                                        </div>
                                        <div>
                                            <h3 className="text-lg font-bold text-white font-outfit group-hover:text-[#7c4dff] transition-colors">
                                                {inst.nombre}
                                            </h3>
                                            <div className="flex items-center gap-2 mt-1">
                                                <span className={`px-2 py-0.5 text-[8px] font-bold rounded border uppercase tracking-widest ${colorClass}`}>
                                                    {inst.tipo}
                                                </span>
                                                <span className="text-[10px] font-mono text-gray-500 uppercase tracking-wider">{inst.id}</span>
                                            </div>
                                        </div>
                                    </div>
                                    
                                    <div className="text-right">
                                        <div className="text-xl font-mono font-bold text-white">Nivel {inst.nivel}</div>
                                        <div className="text-[9px] text-gray-500 uppercase font-bold tracking-wider">Desarrollo</div>
                                    </div>
                                </div>

                                <div className="bg-black/40 p-4 flex gap-6 border-t border-white/5">
                                    <div className="flex items-center gap-2">
                                        <Users className="w-3.5 h-3.5 text-blue-400" />
                                        <div className="flex flex-col">
                                            <span className="text-[9px] text-gray-500 uppercase font-medium">Miembros</span>
                                            <span className="text-xs font-mono text-blue-400">
                                                {inst.miembros?.length || 0}
                                            </span>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <TrendingUp className="w-3.5 h-3.5 text-emerald-400" />
                                        <div className="flex flex-col">
                                            <span className="text-[9px] text-gray-500 uppercase font-medium">Recursos</span>
                                            <span className="text-xs font-mono text-emerald-400">
                                                {Number(inst.recursos).toFixed(0)} MC
                                            </span>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <MapPin className="w-3.5 h-3.5 text-gray-400" />
                                        <div className="flex flex-col">
                                            <span className="text-[9px] text-gray-500 uppercase font-medium">Ubicación</span>
                                            <span className="text-xs font-mono text-gray-300">
                                                ({inst.x}, {inst.y})
                                            </span>
                                        </div>
                                    </div>
                                </div>
                            </motion.div>
                        );
                    })
                )}
            </div>
        </div>
    );
}
