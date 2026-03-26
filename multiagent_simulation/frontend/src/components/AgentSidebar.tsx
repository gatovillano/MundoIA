"use client";

import useGameStore from "@/store/useGameStore";
import { X, Shield, Heart, Zap, Users, Wallet, Brain, MessageSquare, Send, Moon, Music, ListTodo, Code, Terminal, Ghost } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useState } from "react";
import { Agent, Plan } from "@/types/agent"; // Importar la interfaz Agent

export default function AgentSidebar() {
    const { agents, selectedAgentId, selectAgent, sendArchitectMessage, sendGodAction, agentePoseidoId } = useGameStore();
    const [directMessage, setDirectMessage] = useState("");
    const [status, setStatus] = useState<'idle' | 'sending' | 'success'>('idle');
    const agent: Agent | undefined = agents.find((a) => a.id === selectedAgentId); // Usar la interfaz Agent

    if (agent) {
        console.log('DEBUG: Datos del agente en el componente Sidebar', agent);
    }

    return (
        <AnimatePresence>
            {selectedAgentId && agent && (
                <motion.div
                    initial={{ x: 400, opacity: 0 }}
                    animate={{ x: 0, opacity: 1 }}
                    exit={{ x: 400, opacity: 0 }}
                    transition={{ type: "spring", damping: 30, stiffness: 300 }}
                    className="absolute right-6 top-6 bottom-6 w-[400px] solid-panel rounded-2xl z-[60] flex flex-col overflow-hidden"
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
                                    {agent.is_possessed && (
                                        <Badge text="Poseído" color="bg-yellow-500/20 text-yellow-500 border-yellow-500/30 animate-pulse" />
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Content */}
                    <div className="flex-1 overflow-y-auto p-6 space-y-8 custom-scrollbar">

                        <section className="space-y-4">
                            <SectionTitle title="Métricas Principales" />
                            <div className="grid grid-cols-2 gap-3">
                                <StatCard icon={Heart} label="Salud" value={agent?.necesidades?.salud} color="text-[#ff1744]" />
                                <StatCard icon={Zap} label="Recursos" value={agent?.resources} color="text-[#ffd600]" />
                                <StatCard icon={Brain} label="Aprendizaje" value={(agent?.skill_factor || 0) * 100} unit="%" color="text-[#7c4dff]" />
                                <StatCard icon={Wallet} label="MundoCoins" value={agent?.money} unit="MC" color="text-[#ffd600]" />
                            </div>
                        </section>

                        {/* Necesidades Detalladas */}
                        <section className="space-y-4">
                            <SectionTitle title="Necesidades Vitales" />
                            <div className="glass-card p-5 rounded-xl space-y-4">
                                <ProgressBar icon={Shield} label="Seguridad" value={agent?.necesidades?.seguridad} color="bg-[#2979ff]" />
                                <ProgressBar icon={Users} label="Social" value={agent?.necesidades?.social} color="bg-[#00e676]" />
                                <ProgressBar icon={Zap} label="Alimento" value={agent?.necesidades?.alimento} color="bg-[#ffa000]" />
                                <ProgressBar icon={Moon} label="Descanso" value={agent?.necesidades?.descanso} color="bg-[#7c4dff]" />
                                <ProgressBar icon={Music} label="Ocio" value={agent?.necesidades?.entretenimiento} color="bg-[#ec4899]" />
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
                                    "{agent?.pensamiento || "Procesando flujo de datos del entorno..."}"
                                </p>
                            </div>
                        </section>

                        {/* Planes Activos */}
                        {agent?.planes && agent.planes.length > 0 && (
                            <section className="space-y-4">
                                <SectionTitle title="Planes Activos" />
                                <div className="glass-card p-5 rounded-xl space-y-3">
                                    {agent.planes.map((plan: Plan, index) => (
                                        <div key={index} className="flex items-start gap-3">
                                            <ListTodo className="w-4 h-4 text-[#00e676] mt-1 flex-shrink-0" />
                                            <p className="text-sm text-gray-300 leading-snug">{plan.objetivo}</p>
                                        </div>
                                    ))}
                                </div>
                            </section>
                        )}

                        {/* Intervención Divina (Mensaje Privado) */}
                        <section className="space-y-4">
                            <SectionTitle title="Intervención Divina" />
                            <div className="glass-card p-4 rounded-xl border border-[#7c4dff]/30 bg-[#7c4dff]/5">
                                <div className="flex gap-2">
                                    <input
                                        type="text"
                                        value={directMessage}
                                        onChange={(e) => setDirectMessage(e.target.value)}
                                        placeholder={status === 'success' ? "¡Mensaje enviado!" : "Dictar orden divina..."}
                                        disabled={status === 'sending'}
                                        className="flex-1 bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder:text-gray-600 focus:outline-none focus:border-[#7c4dff]/50 transition-colors"
                                        onKeyDown={async (e) => {
                                            if (e.key === 'Enter' && directMessage.trim()) {
                                                setStatus('sending');
                                                await sendArchitectMessage(directMessage, agent?.id);
                                                setDirectMessage("");
                                                setStatus('success');
                                                setTimeout(() => setStatus('idle'), 2000);
                                            }
                                        }}
                                    />
                                    <button
                                        onClick={async () => {
                                            if (directMessage.trim()) {
                                                setStatus('sending');
                                                await sendArchitectMessage(directMessage, agent?.id);
                                                setDirectMessage("");
                                                setStatus('success');
                                                setTimeout(() => setStatus('idle'), 2000);
                                            }
                                        }}
                                        disabled={!directMessage.trim() || status === 'sending'}
                                        className={`p-2 rounded-lg transition-all shadow-lg ${status === 'success' ? 'bg-[#00e676] text-white shadow-[#00e676]/20' :
                                            status === 'sending' ? 'bg-[#7c4dff]/50 text-white cursor-wait' :
                                                'bg-[#7c4dff] text-white hover:bg-[#6c3eee] shadow-[#7c4dff]/20'
                                            }`}
                                    >
                                        {status === 'sending' ? (
                                            <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                        ) : (
                                            <Send className="w-4 h-4" />
                                        )}
                                    </button>
                                </div>
                                <p className="text-[10px] text-gray-500 mt-2 italic px-1">
                                    "Tu voz resonará directamente en su psique."
                                </p>

                                {/* Botón de Posesión */}
                                <div className="mt-4 pt-4 border-t border-white/5">
                                    <button
                                        onClick={async () => {
                                            const isCurrentlyPossessed = agentePoseidoId === agent.id;
                                            await sendGodAction("POSSESS_AGENT", { agent_id: isCurrentlyPossessed ? null : agent.id });
                                        }}
                                        className={`w-full py-3 rounded-xl font-bold uppercase tracking-widest text-[10px] flex items-center justify-center gap-2 transition-all ${agentePoseidoId === agent.id
                                                ? 'bg-red-500/20 text-red-500 border border-red-500/30 hover:bg-red-500 hover:text-white'
                                                : 'bg-yellow-500/20 text-yellow-500 border border-yellow-500/30 hover:bg-yellow-500 hover:text-black'
                                            }`}
                                    >
                                        <Ghost className={`w-4 h-4 ${agentePoseidoId === agent.id ? 'animate-bounce' : ''}`} />
                                        {agentePoseidoId === agent.id ? "Liberar Ser" : "Descender y Poseer"}
                                    </button>
                                </div>
                            </div>
                        </section>

                        {/* Datos Estructurales (Facciones & Economía) */}
                        <section className="space-y-4">
                            <SectionTitle title="Datos Estructurales" />
                            <div className="grid grid-cols-2 gap-3">
                                <InfoBlock label="Grupo" value={agent?.grupo_id || "Neutral"} />
                                <InfoBlock label="Profesión" value={agent?.profesion || "Ciudadano"} />
                                <InfoBlock label="Rol" value={agent?.rol || "Miembro"} />
                                <InfoBlock label="Reputación" value={`${((agent?.reputacion || 0) * 100).toFixed(0)}%`} />
                            </div>
                        </section>

                        {/* Personalidad */}
                        <section className="space-y-4">
                            <SectionTitle title="Matriz de Personalidad" />
                            <div className="glass-card p-5 rounded-xl space-y-4">
                                {Object.entries(agent?.personalidad || {}).map(([trait, value]) => (
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

                        {/* Experiencia */}
                        <section className="space-y-4">
                            <SectionTitle title="Habilidades y Experiencia" />
                            <div className="glass-card p-5 rounded-xl space-y-4">
                                {Object.entries(agent?.experiencia || {}).map(([skill, value]) => (
                                    <div key={skill} className="space-y-1.5">
                                        <div className="flex justify-between text-xs items-center">
                                            <span className="text-gray-400 capitalize font-medium">{skill}</span>
                                            <span className="text-[#ff9100] font-mono">Nivel {value as number}</span>
                                        </div>
                                        <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                                            <motion.div
                                                initial={{ width: 0 }}
                                                animate={{ width: `${((value as number) / 20) * 100}%` }} // Assuming max level 20 for visualization
                                                transition={{ duration: 1, ease: "circOut" }}
                                                className="h-full bg-gradient-to-r from-[#ffea00] to-[#ff9100]"
                                            />
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </section>

                        {/* Inventario Detallado (NUEVO) */}
                        {agent?.inventario && Object.keys(agent.inventario).length > 0 && (
                            <section className="space-y-4">
                                <SectionTitle title="Inventario de Recursos" />
                                <div className="grid grid-cols-2 gap-3">
                                    {Object.entries(agent.inventario).map(([item, count]) => (
                                        <div key={item} className="glass-card p-3 rounded-xl flex items-center justify-between border border-white/5 bg-white/[0.02]">
                                            <div className="flex items-center gap-2">
                                                <div className="p-1.5 rounded-lg bg-white/5 text-gray-400 capitalize text-[10px] font-bold">
                                                    {item.substring(0, 3)}
                                                </div>
                                                <span className="text-xs text-gray-300 capitalize">{item}</span>
                                            </div>
                                            <span className="text-sm font-mono font-bold text-[#00e676]">{count}</span>
                                        </div>
                                    ))}
                                </div>
                            </section>
                        )}

                        {/* Habilidades Creadas (Dinámicas) */}
                        {agent?.skills && Object.keys(agent.skills).length > 0 && (
                            <section className="space-y-4">
                                <SectionTitle title="Módulos de Habilidad Creados" />
                                <div className="space-y-4">
                                    {Object.entries(agent.skills).map(([skillName, skillData]) => (
                                        <div key={skillName} className="relative group">
                                            {/* Efecto de borde brillante */}
                                            <div className="absolute -inset-[1px] bg-gradient-to-r from-[#7c4dff] to-[#00e676] rounded-xl opacity-20 group-hover:opacity-100 transition-opacity blur-[2px]" />

                                            <div className="relative glass-card p-5 rounded-xl bg-[#0a0b10] border border-white/5 overflow-hidden">
                                                {/* Meta-info */}
                                                <div className="flex items-center justify-between mb-4">
                                                    <div className="flex items-center gap-2">
                                                        <div className="p-2 rounded-lg bg-[#7c4dff]/20 text-[#7c4dff]">
                                                            <Code className="w-4 h-4" />
                                                        </div>
                                                        <span className="text-xs font-bold text-white uppercase tracking-wider font-mono">
                                                            {skillData.name}
                                                        </span>
                                                    </div>
                                                    <div className="flex items-center gap-2">
                                                        <span className="text-[9px] text-gray-500 font-mono">v{skillData.version || "1.0.0"}</span>
                                                        <div className="w-1.5 h-1.5 rounded-full bg-[#00e676] animate-pulse" />
                                                    </div>
                                                </div>

                                                <p className="text-xs text-gray-400 mb-4 leading-relaxed line-clamp-2 italic">
                                                    {skillData.description}
                                                </p>

                                                {/* Code Viewer */}
                                                <div className="rounded-lg bg-black/60 border border-white/5 p-3 font-mono text-[9px] text-[#00e676]/70 group-hover:text-[#00e676] transition-colors overflow-x-auto custom-scrollbar">
                                                    <div className="flex items-center gap-2 mb-2 pb-2 border-b border-white/5 opacity-50">
                                                        <Terminal className="w-3 h-3" />
                                                        <span className="text-[8px] uppercase tracking-tighter">python_module.py</span>
                                                    </div>
                                                    <pre className="whitespace-pre">
                                                        <code>{skillData.code}</code>
                                                    </pre>
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </section>
                        )}

                    </div>
                </motion.div>
            )}
        </AnimatePresence>
    );
}

// Sub-componentes estilizados
function StatCard({ icon: Icon, label, value, unit, color }: any) {
    return (
        <div className="bg-white/[0.03] border border-white/10 p-4 rounded-xl flex flex-col gap-3 hover:bg-white/[0.06] transition-colors group">
            <div className={`flex items-center gap-2 text-[10px] font-bold uppercase tracking-wider ${color}`}>
                <Icon className="w-3.5 h-3.5 opacity-80 group-hover:opacity-100 transition-opacity" /> {label}
            </div>
            <div className="text-xl font-mono font-bold text-white flex items-baseline gap-1">
                {typeof value === 'number' ? value.toFixed(unit === '%' ? 0 : 1) : '0.0'}
                {unit && <span className="text-[10px] opacity-50">{unit}</span>}
            </div>
        </div>
    )
}

function ProgressBar({ icon: Icon, label, value, color }: { icon: any, label: string, value: number, color: string }) {
    // Normalizar valor (asumiendo 0-10)
    const percentage = Math.max(0, Math.min(100, (value || 0) * 10));

    return (
        <div className="space-y-1.5">
            <div className="flex justify-between text-[10px] items-center">
                <div className="flex items-center gap-1.5 text-gray-400 uppercase font-bold tracking-wider">
                    <Icon className="w-3 h-3 opacity-70" />
                    {label}
                </div>
                <span className="text-white font-mono font-bold">{(value || 0).toFixed(1)}</span>
            </div>
            <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden border border-white/5">
                <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${percentage}%` }}
                    transition={{ duration: 1, ease: "circOut" }}
                    className={`h-full ${color} shadow-[0_0_10px_rgba(255,255,255,0.1)]`}
                />
            </div>
        </div>
    );
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
