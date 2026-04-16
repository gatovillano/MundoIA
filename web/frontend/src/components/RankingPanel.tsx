'use client';

import React from 'react';
import { Trophy, Star, Award, TrendingUp, User } from 'lucide-react';
import { motion } from 'framer-motion';
import useGameStore from '@/store/useGameStore';

export default function RankingPanel() {
    const { ranking } = useGameStore();

    // Si no hay ranking, mostrar un estado vacío elegante
    if (!ranking || ranking.length === 0) {
        return (
            <div className="glass-panel p-6 rounded-2xl border border-white/10 bg-black/20 backdrop-blur-md">
                <div className="flex items-center gap-2 mb-4">
                    <Trophy className="w-5 h-5 text-[#ffea00]" />
                    <h3 className="text-lg font-bold text-white tracking-widest font-mono">TOP ARQUITECTOS</h3>
                </div>
                <div className="flex flex-col items-center justify-center py-8 opacity-30 italic">
                    <TrendingUp className="w-12 h-12 mb-2" />
                    <p className="text-sm">Iniciando temporada...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="glass-panel p-6 rounded-2xl border border-white/10 bg-black/20 backdrop-blur-md shadow-2xl">
            <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-2">
                    <Trophy className="w-6 h-6 text-[#ffea00] drop-shadow-[0_0_8px_rgba(255,234,0,0.5)]" />
                    <h3 className="text-lg font-bold text-white tracking-widest font-mono">RANKING GLOBAL</h3>
                </div>
                <div className="bg-white/5 px-2 py-1 rounded text-[10px] text-gray-400 font-mono">
                    LIVE
                </div>
            </div>

            <div className="space-y-4">
                {ranking.map((user, index) => (
                    <motion.div
                        key={user.user_id}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: index * 0.1 }}
                        className={`group relative flex items-center gap-4 p-3 rounded-xl border transition-all ${index === 0
                                ? 'bg-gradient-to-r from-[#ffea00]/10 to-transparent border-[#ffea00]/30 shadow-[0_0_20px_rgba(255,234,0,0.1)]'
                                : 'bg-white/5 border-white/5 hover:border-white/20'
                            }`}
                    >
                        {/* Posición */}
                        <div className={`flex items-center justify-center w-8 h-8 rounded-lg font-black text-sm ${index === 0 ? 'bg-[#ffea00] text-black' :
                                index === 1 ? 'bg-[#e0e0e0] text-black' :
                                    index === 2 ? 'bg-[#cd7f32] text-black' :
                                        'bg-white/10 text-white/50'
                            }`}>
                            {index + 1}
                        </div>

                        {/* Avatar / Icono */}
                        <div className="p-2 rounded-full bg-white/5 border border-white/10">
                            <User className={`w-4 h-4 ${index === 0 ? 'text-[#ffea00]' : 'text-white/70'}`} />
                        </div>

                        {/* Info Usuario */}
                        <div className="flex-1 min-w-0">
                            <h4 className="text-sm font-bold text-white truncate font-mono">
                                {user.username ? user.username.toUpperCase() : (user.user_id === 'default' ? 'ANÓNIMO' : user.user_id.toUpperCase())}
                            </h4>
                            <div className="flex items-center gap-1 text-[10px] text-gray-500 font-bold">
                                <Award className="w-3 h-3" />
                                <span>ARQUITECTO NIVEL {Math.floor(user.puntos / 1000) + 1}</span>
                            </div>
                        </div>

                        {/* Puntaje */}
                        <div className="text-right">
                            <div className="flex items-center gap-1.5 text-[#ffea00] font-black font-mono">
                                <Star className="w-3.5 h-3.5 fill-[#ffea00]" />
                                <span className="text-lg tracking-tighter">{user.puntos.toLocaleString()}</span>
                            </div>
                            <div className="text-[9px] text-gray-500 font-bold tracking-widest uppercase">
                                Puntos
                            </div>
                        </div>

                        {/* Decoración primer lugar */}
                        {index === 0 && (
                            <div className="absolute -top-1 -right-1">
                                <span className="relative flex h-3 w-3">
                                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#ffea00] opacity-75"></span>
                                    <span className="relative inline-flex rounded-full h-3 w-3 bg-[#ffea00]"></span>
                                </span>
                            </div>
                        )}
                    </motion.div>
                ))}
            </div>

            <div className="mt-6 flex items-center justify-center gap-2 opacity-30">
                <div className="h-px flex-1 bg-gradient-to-r from-transparent to-white/20" />
                <span className="text-[9px] font-mono tracking-[0.2em] text-white">LEGADO IA</span>
                <div className="h-px flex-1 bg-gradient-to-l from-transparent to-white/20" />
            </div>
        </div>
    );
}
