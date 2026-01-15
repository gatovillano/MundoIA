"use client";

import useGameStore from "@/store/useGameStore";
import { X, Shield, Heart, Zap, Users, Wallet, Brain } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

export default function AgentSidebar() {
    const { agents, selectedAgentId, selectAgent } = useGameStore();
    const agent = agents.find((a) => a.id === selectedAgentId);

    return (
        <AnimatePresence>
            {selectedAgentId && agent && (
                <motion.div
                    initial={{ x: 400, opacity: 0 }}
                    animate={{ x: 0, opacity: 1 }}
                    exit={{ x: 400, opacity: 0 }}
                    transition={{ type: "spring", damping: 30, stiffness: 300 }}
                    className="absolute right-6 top-6 bottom-6 w-[400px] glass-panel rounded-2xl z-[60] flex flex-col overflow-hidden"
                >
                    {/* Header con Efecto Glass */}
                    <div className="relative p-6 pb-8 border-b border-white/5 bg-gradient-to-b from-white/5 to-transparent">
                        <button
                            onClick={() => selectAgent(null)}
                            className="absolute top-4 right-4 p-2 hover:bg-white/10 rounded-full transition-colors text-white/50 hover:text-white"
                        >
                            <X className="w-5 h-5" />
                        </button>

                        <div className="flex items-center gap-5">
                            <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-[#7c4dff] to-[#00e676] p-[2px] shadow-lg shadow-[#7c4dff]/20">
                                <div className="w-full h-full bg-[#0a0b10] rounded-[14px] flex items-center justify-center relative overflow-hidden">
                                    <div className="absolute inset-0 bg-gradient-to-br from-[#7c4dff]/20 to-[#00e676]/20 opacity-50" />
                                    <span className="text-3xl font-bold text-white relative z-10 font-mono">
                                        {agent.id.substring(0, 2)}
                                    </span>
                                </div>
                            </div>
                            <div>
                                <h2 className="text-2xl font-bold text-white tracking-tight mb-1">
                                    AGENTE <span className="font-mono text-[#7c4dff]">{agent.id.substring(0, 4)}</span>
                                </h2>
                                <div className="flex flex-wrap gap-2">
                                    <Badge text={agent.profesion || "CIUDADANO"} color="bg-[#7c4dff]/20 text-[#7c4dff] border-[#7c4dff]/30" />
                                    <Badge text="Activo" color="bg-[#00e676]/20 text-[#00e676] border-[#00e676]/30" />
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Content */}
                    <div className="flex-1 overflow-y-auto p-6 space-y-8 custom-scrollbar">

                        {/* Estado Vital (Stats) */}
                        <section className="space-y-4">
                            <SectionTitle title="Métricas Vitales" />
                            <div className="grid grid-cols-2 gap-3">
                                <StatCard icon={Heart} label="Salud" value={agent.necesidades?.salud} color="text-[#ff1744]" />
                                <StatCard icon={Zap} label="Energía" value={agent.resources} color="text-[#ffd600]" />
                                <StatCard icon={Shield} label="Seguridad" value={agent.necesidades?.seguridad} color="text-[#2979ff]" />
                                <StatCard icon={Users} label="Social" value={agent.necesidades?.social} color="text-[#00e676]" />
                            </div>
                        </section>

                        {/* Procesamiento Mental (Destacado) */}
                        <section className="space-y-4">
                            <SectionTitle title="Córtex Neural" />
                            <div className="relative p-6 rounded-2xl bg-gradient-to-br from-[#7c4dff]/10 to-transparent border border-[#7c4dff]/20 overflow-hidden group">
                                <div className="absolute top-0 right-0 w-32 h-32 bg-[#7c4dff] rounded-full blur-[80px] opacity-10 group-hover:opacity-20 transition-opacity" />

                                <div className="flex items-center gap-3 mb-4">
                                    <div className="p-2 rounded-lg bg-[#7c4dff]/20 text-[#7c4dff]">
                                        <Brain className="w-5 h-5" />
                                    </div>
                                    <span className="text-xs font-bold text-[#7c4dff] uppercase tracking-widest">Pensamiento Activo</span>
                                    <div className="ml-auto w-2 h-2 rounded-full bg-[#7c4dff] animate-pulse shadow-[0_0_10px_#7c4dff]" />
                                </div>

                                <p className="text-sm text-gray-200 leading-relaxed font-mono border-l-2 border-[#7c4dff]/30 pl-4 py-1 italic">
                                    "{agent.pensamiento || "Procesando flujo de datos del entorno..."}"
                                </p>
                            </div>
                        </section>

                        {/* Datos Estructurales (Facciones & Economía) */}
                        <section className="space-y-4">
                            <SectionTitle title="Datos Estructurales" />
                            <div className="grid grid-cols-2 gap-3">
                                <InfoBlock label="Facción" value={agent.grupo_id || "Neutral"} subValue={agent.rol} />
                                <div className="bg-white/[0.03] border border-white/10 rounded-xl p-4 flex flex-col justify-center relative overflow-hidden">
                                    <div className="absolute top-0 right-0 p-3 opacity-10">
                                        <Wallet className="w-12 h-12 text-[#ffd600]" />
                                    </div>
                                    <span className="text-[10px] text-gray-500 uppercase tracking-wider font-bold mb-1">Créditos</span>
                                    <span className="text-2xl font-mono font-bold text-white text-glow">
                                        {agent.money?.toFixed(0)} <span className="text-xs text-[#ffd600] align-top">CR</span>
                                    </span>
                                </div>
                            </div>
                        </section>

                        {/* Personalidad */}
                        <section className="space-y-4">
                            <SectionTitle title="Matriz de Personalidad" />
                            <div className="glass-card p-5 rounded-xl space-y-4">
                                {Object.entries(agent.personalidad || {}).map(([trait, value]) => (
                                    <div key={trait} className="space-y-1.5">
                                        <div className="flex justify-between text-xs items-center">
                                            <span className="text-gray-400 capitalize font-medium">{trait}</span>
                                            <span className="text-[#00e676] font-mono">{(value as number * 100).toFixed(0)}%</span>
                                        </div>
                                        <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                                            <motion.div
                                                initial={{ width: 0 }}
                                                animate={{ width: `${(value as number) * 100}%` }}
                                                transition={{ duration: 1, ease: "circOut" }}
                                                className="h-full bg-gradient-to-r from-[#7c4dff] to-[#00e676]"
                                            />
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </section>

                    </div>
                </motion.div>
            )}
        </AnimatePresence>
    );
}

// Sub-componentes estilizados
function StatCard({ icon: Icon, label, value, color }: any) {
    return (
        <div className="bg-white/[0.03] border border-white/10 p-4 rounded-xl flex flex-col gap-3 hover:bg-white/[0.06] transition-colors group">
            <div className={`flex items-center gap-2 text-xs font-bold uppercase tracking-wider ${color}`}>
                <Icon className="w-4 h-4 opacity-80 group-hover:opacity-100 transition-opacity" /> {label}
            </div>
            <div className="text-2xl font-mono font-bold text-white">
                {typeof value === 'number' ? value.toFixed(0) : '0'}
            </div>
        </div>
    )
}

function SectionTitle({ title }: { title: string }) {
    return (
        <div className="flex items-center gap-2 mb-2">
            <div className="h-px bg-white/10 flex-1" />
            <h3 className="text-[10px] font-bold text-gray-500 uppercase tracking-[0.2em]">
                {title}
            </h3>
            <div className="h-px bg-white/10 flex-1" />
        </div>
    )
}

function Badge({ text, color }: { text: string, color: string }) {
    return (
        <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider border ${color}`}>
            {text}
        </span>
    )
}

function InfoBlock({ label, value, subValue }: { label: string, value: string, subValue?: string }) {
    return (
        <div className="bg-white/[0.03] border border-white/10 rounded-xl p-4 flex flex-col justify-center">
            <span className="text-[10px] text-gray-500 uppercase tracking-wider font-bold mb-1">{label}</span>
            <span className="font-bold text-white truncate" title={value}>{value}</span>
            {subValue && <span className="text-xs text-gray-500 mt-1">{subValue}</span>}
        </div>
    )
}

