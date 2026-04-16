import React from 'react';
import { motion } from 'framer-motion';
import { Target, Award, CheckCircle, Clock } from 'lucide-react';
import useGameStore from '@/store/useGameStore';

export default function MissionsPanel() {
    const { misiones } = useGameStore();

    // Extraer misiones activas y completadas del nuevo formato de objeto
    const activeMissions = misiones?.misiones_activas || [];
    const completedMissions = misiones?.misiones_completadas || [];
    const allMissions = [...activeMissions, ...completedMissions];

    return (
        <div className="flex flex-col h-full space-y-6">
            {/* Header info moved to UnifiedPanel's subtitle or integrated here */}
            <div className="flex items-center justify-between px-1">
                <div className="text-[10px] font-bold text-gray-500 uppercase tracking-widest flex items-center gap-2">
                    <Target className="w-3 h-3" />
                    Progreso Global
                </div>
                <div className="flex gap-2">
                    <span className="text-[10px] bg-white/5 border border-white/5 px-2 py-0.5 rounded-lg text-white font-mono">
                        {activeMissions.length} Activas
                    </span>
                    <span className="text-[10px] bg-[#00e676]/10 border border-[#00e676]/10 px-2 py-0.5 rounded-lg text-[#00e676] font-mono">
                        {completedMissions.length} Completadas
                    </span>
                </div>
            </div>

            <div className="flex-1 overflow-y-auto custom-scrollbar space-y-4 pr-1">
                {allMissions.length === 0 ? (
                    <div className="py-20 text-center border border-dashed border-white/10 rounded-2xl bg-white/[0.02]">
                        <Target className="w-12 h-12 text-white/10 mx-auto mb-4" />
                        <p className="text-xs text-gray-500 font-mono tracking-wider uppercase">
                            Sincronizando objetivos globales...
                        </p>
                    </div>
                ) : (
                    allMissions.map((mision) => (
                        <MissionCard key={mision.id} mission={mision} />
                    ))
                )}
            </div>
        </div>
    );
}

function MissionCard({ mission }: { mission: any }) {
    const isCompleted = mission.estado === 'completada';
    const progress = Math.min(100, (((mission.objetivo?.actual || 0) / (mission.objetivo?.cantidad || 1))) * 100);

    const difficultyStyles: Record<string, string> = {
        facil: "text-green-400 border-green-400/30",
        media: "text-blue-400 border-blue-400/30",
        dificil: "text-purple-400 border-purple-400/30",
        epica: "text-yellow-400 border-yellow-400/30"
    };

    const diffStyle = difficultyStyles[mission.dificultad] || "text-gray-400 border-gray-400/30";

    return (
        <div className={`p-3 rounded-xl border relative overflow-hidden group transition-all ${isCompleted
            ? 'bg-[#00e676]/10 border-[#00e676]/30 opacity-70'
            : 'bg-white/5 border-white/10 hover:bg-white/10 hover:border-white/20'
            }`}>

            <div className="flex justify-between items-start mb-1.5 gap-2">
                <div className="flex flex-col">
                    <span className={`text-[9px] uppercase font-black px-1.5 py-0.5 rounded border mb-1 w-fit ${diffStyle}`}>
                        {mission.dificultad || 'misión'}
                    </span>
                    <h3 className={`text-sm font-bold ${isCompleted ? 'text-[#00e676]' : 'text-white'}`}>
                        {mission.titulo}
                    </h3>
                </div>
                {isCompleted ? (
                    <CheckCircle className="w-5 h-5 text-[#00e676]" />
                ) : (
                    <div className="relative w-5 h-5">
                        <CircleDashed className="w-5 h-5 text-white/20 animate-spin" />
                        <div className="absolute inset-0 flex items-center justify-center text-[8px] font-bold">
                            {Math.floor(progress)}
                        </div>
                    </div>
                )}
            </div>

            <p className="text-[11px] text-gray-400 mb-2.5 leading-relaxed pr-2">
                {mission.descripcion}
            </p>

            {/* Progress Bar Container */}
            {!isCompleted && (
                <div className="h-1.5 w-full bg-white/5 rounded-full mb-3 overflow-hidden">
                    <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${progress}%` }}
                        className={`h-full bg-gradient-to-r ${isCompleted ? 'from-green-500 to-emerald-600' : 'from-blue-500 to-indigo-600'}`}
                    />
                </div>
            )}

            <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5 text-[10px] text-white/60 font-black">
                    <Award className="w-3 h-3 text-[#ffd600]" />
                    <span>+{mission.recompensa_puntos} PTS</span>
                </div>

                <span className="text-[10px] font-mono text-gray-500">
                    {mission.objetivo.actual} / {mission.objetivo.cantidad}
                </span>
            </div>
        </div>
    );
}

// Import dynamic symbols to fix the missing icon error
import { CircleDashed } from 'lucide-react';
