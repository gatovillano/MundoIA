"use client";

import useGameStore from "@/store/useGameStore";
import { X, Shield, Heart, Zap, Users, Wallet, Brain, MessageSquare, Send, Moon, Music, ListTodo, Code, Terminal, Ghost, Clock, Swords, Handshake, Globe, Lock } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useState, useMemo } from "react";
import { Agent, Plan } from "@/types/agent";

type TabType = 'perfil' | 'historial';

interface HistoryEntry {
    step: number;
    message: string;
    category: string;
    thought?: string;
    timestamp: number;
    tipo: 'mensaje' | 'interaccion' | 'sistema';
    scope?: 'global' | 'grupo' | 'privado' | 'directo';
}

function filterAgentLogs(logs: any[], agentId: string): HistoryEntry[] {
    // Pre-filtro rápido con String.includes() (~100x más rápido que RegExp)
    // antes de aplicar la regex más costosa
    const quickCheck = `[${agentId}]`;
    const quickCheckAlt = `Agente ${agentId}`;

    return logs
        .filter((l: any) => {
            if (!l.message) return false;
            return l.message.includes(quickCheck) || l.message.includes(quickCheckAlt);
        })
        .map((l: any): HistoryEntry => {
            const msg: string = l.message;
            let tipo: HistoryEntry['tipo'] = 'sistema';
            let scope: HistoryEntry['scope'] = undefined;

            // Detect if it's a dialogue message from this agent
            if (msg.includes(quickCheck)) {
                tipo = 'mensaje';
                if (msg.includes('ANUNCIO GLOBAL') || msg.includes('(ANUNCIO)')) {
                    scope = 'global';
                } else if (msg.includes('Para Facción') || msg.includes('(Para Grupo')) {
                    scope = 'grupo';
                } else if (msg.includes('Privado para')) {
                    scope = 'privado';
                } else {
                    scope = 'directo';
                }
            }
            // Detect interaction logs where agent is involved
            else if (l.category === 'social' || l.category === 'conflict' || l.category === 'economia' || msg.includes('[SOCIAL]') || msg.includes('[CONFLICTO]') || msg.includes('[COMERCIO]')) {
                tipo = 'interaccion';
            } else if (l.category && ['construccion', 'movimiento', 'accion', 'consenso'].includes(l.category)) {
                tipo = 'interaccion';
            }

            return {
                step: l.step || 0,
                message: msg,
                category: l.category || 'general',
                thought: l.thought,
                timestamp: l.timestamp || Date.now(),
                tipo,
                scope,
            };
        });
}

// --- Historial Tab y componentes auxiliares ---
function HistorialTab({ agentId, history }: { agentId: string; history: HistoryEntry[] }) {
    const [filter, setFilter] = useState<'todos' | 'mensajes' | 'interacciones'>('todos');

    const filtered = useMemo(() => {
        if (filter === 'mensajes') return history.filter(h => h.tipo === 'mensaje');
        if (filter === 'interacciones') return history.filter(h => h.tipo === 'interaccion');
        return history;
    }, [history, filter]);

    const reversed = useMemo(() => [...filtered].reverse(), [filtered]);

    const counts = useMemo(() => ({
        total: history.length,
        mensajes: history.filter(h => h.tipo === 'mensaje').length,
        interacciones: history.filter(h => h.tipo === 'interaccion').length,
    }), [history]);

    return (
        <div className="flex flex-col h-full">
            <div className="flex gap-1 p-4 pb-2">
                <FilterPill active={filter === 'todos'} onClick={() => setFilter('todos')} label="Todos" count={counts.total} color="text-[#7c4dff]" activeColor="bg-[#7c4dff]/10 border-[#7c4dff]/30" />
                <FilterPill active={filter === 'mensajes'} onClick={() => setFilter('mensajes')} label="Mensajes" count={counts.mensajes} color="text-[#00e676]" activeColor="bg-[#00e676]/10 border-[#00e676]/30" />
                <FilterPill active={filter === 'interacciones'} onClick={() => setFilter('interacciones')} label="Acciones" count={counts.interacciones} color="text-[#ff9100]" activeColor="bg-[#ff9100]/10 border-[#ff9100]/30" />
            </div>
            <div className="flex-1 overflow-y-auto px-4 pb-4 space-y-2 custom-scrollbar">
                {reversed.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-16 text-gray-600">
                        <Clock className="w-8 h-8 mb-3 opacity-30" />
                        <p className="text-xs text-center">Sin historial registrado<br />para este agente.</p>
                    </div>
                ) : (
                    reversed.map((entry, i) => (
                        <HistoryCard key={`${entry.step}-${i}`} entry={entry} agentId={agentId} />
                    ))
                )}
            </div>
        </div>
    );
}

function FilterPill({ active, onClick, label, count, color, activeColor }: {
    active: boolean; onClick: () => void; label: string; count: number; color: string; activeColor: string;
}) {
    return (
        <button onClick={onClick} className={`flex-1 py-1.5 px-2 rounded-lg text-[10px] font-bold uppercase tracking-wider transition-all flex items-center justify-center gap-1 ${active ? `${activeColor} ${color} border` : 'text-gray-500 hover:text-gray-300 bg-white/[0.02]'}`}>
            {label}<span className="font-mono text-[9px] opacity-60">{count}</span>
        </button>
    );
}

function HistoryCard({ entry, agentId }: { entry: HistoryEntry; agentId: string }) {
    const cleanMessage = useMemo(() => {
        let msg = entry.message;
        const colonIdx = msg.indexOf(']: "');
        if (colonIdx !== -1) { msg = msg.substring(colonIdx + 4); if (msg.endsWith('"')) msg = msg.slice(0, -1); }
        return msg;
    }, [entry.message]);

    const meta = useMemo(() => {
        if (entry.tipo !== 'mensaje') return null;
        const msg = entry.message;
        if (msg.includes('ANUNCIO GLOBAL')) return { icon: Globe, label: 'Anuncio Global', color: 'text-yellow-400', bg: 'bg-yellow-500/10 border-yellow-500/20' };
        if (msg.includes('Para Facción') || msg.includes('Para Grupo')) return { icon: Users, label: 'Mensaje Grupal', color: 'text-blue-400', bg: 'bg-blue-500/10 border-blue-500/20' };
        if (msg.includes('Privado para')) return { icon: Lock, label: 'Mensaje Privado', color: 'text-purple-400', bg: 'bg-purple-500/10 border-purple-500/20' };
        return { icon: MessageSquare, label: 'Mensaje', color: 'text-[#00e676]', bg: 'bg-[#00e676]/10 border-[#00e676]/20' };
    }, [entry]);

    const interactionMeta = useMemo(() => {
        if (entry.tipo !== 'interaccion') return null;
        const cat = entry.category; const msg = entry.message;
        if (cat === 'social' || msg.includes('[SOCIAL]')) return { icon: Handshake, label: 'Social', color: 'text-purple-400', bg: 'bg-purple-500/10 border-purple-500/20' };
        if (cat === 'conflict' || cat === 'conflicto' || msg.includes('[CONFLICTO]')) return { icon: Swords, label: 'Conflicto', color: 'text-red-400', bg: 'bg-red-500/10 border-red-500/20' };
        if (cat === 'economia' || msg.includes('[COMERCIO]')) return { icon: Wallet, label: 'Economía', color: 'text-emerald-400', bg: 'bg-emerald-500/10 border-emerald-500/20' };
        if (cat === 'construccion') return { icon: Code, label: 'Construcción', color: 'text-orange-400', bg: 'bg-orange-500/10 border-orange-500/20' };
        if (cat === 'movimiento') return { icon: Zap, label: 'Movimiento', color: 'text-cyan-400', bg: 'bg-cyan-500/10 border-cyan-500/20' };
        if (cat === 'consenso') return { icon: Users, label: 'Consenso', color: 'text-indigo-400', bg: 'bg-indigo-500/10 border-indigo-500/20' };
        return { icon: Zap, label: cat || 'Acción', color: 'text-gray-400', bg: 'bg-white/[0.02] border-white/5' };
    }, [entry]);

    const info = entry.tipo === 'mensaje' ? meta : interactionMeta;
    const IconComp = info?.icon || Zap;

    return (
        <div className={`rounded-xl p-3 border ${info?.bg || 'bg-white/[0.02] border-white/5'} transition-colors hover:brightness-110`}>
            <div className="flex items-start gap-2.5">
                <div className={`flex-shrink-0 w-7 h-7 rounded-lg flex items-center justify-center mt-0.5 ${info?.bg || 'bg-white/5'} ${info?.color || 'text-gray-400'}`}>
                    <IconComp className="w-3.5 h-3.5" />
                </div>
                <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-1">
                        <span className={`text-[9px] font-bold uppercase tracking-wider ${info?.color || 'text-gray-500'}`}>{info?.label || entry.category}</span>
                        <span className="text-[9px] font-mono text-gray-600">paso {entry.step}</span>
                    </div>
                    <p className="text-xs text-gray-200 leading-relaxed break-words">{cleanMessage}</p>
                    {entry.thought && (<p className="text-[10px] text-gray-500 mt-1.5 italic border-l-2 border-white/10 pl-2 leading-relaxed">{entry.thought}</p>)}
                </div>
            </div>
        </div>
    );
}

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
    const percentage = Math.max(0, Math.min(100, (value || 0) * 10));
    return (
        <div className="space-y-1.5">
            <div className="flex justify-between text-[10px] items-center">
                <div className="flex items-center gap-1.5 text-gray-400 uppercase font-bold tracking-wider">
                    <Icon className="w-3 h-3 opacity-70" />{label}
                </div>
                <span className="text-white font-mono font-bold">{(value || 0).toFixed(1)}</span>
            </div>
            <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden border border-white/5">
                <motion.div initial={{ width: 0 }} animate={{ width: `${percentage}%` }} transition={{ duration: 1, ease: "circOut" }} className={`h-full ${color} shadow-[0_0_10px_rgba(255,255,255,0.1)]`} />
            </div>
        </div>
    );
}

function SectionTitle({ title }: { title: string }) {
    return (<div className="flex items-center gap-2 mb-2"><div className="h-px bg-white/10 flex-1" /><h3 className="text-[10px] font-bold text-gray-500 uppercase tracking-[0.2em]">{title}</h3><div className="h-px bg-white/10 flex-1" /></div>)
}
function Badge({ text, color }: { text: string, color: string }) {
    return (<span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider border ${color}`}>{text}</span>)
}
function InfoBlock({ label, value, subValue }: { label: string, value: string, subValue?: string }) {
    return (<div className="bg-white/[0.03] border border-white/10 rounded-xl p-4 flex flex-col justify-center"><span className="text-[10px] text-gray-500 uppercase tracking-wider font-bold mb-1">{label}</span><span className="font-bold text-white truncate" title={value}>{value}</span>{subValue && <span className="text-xs text-gray-500 mt-1">{subValue}</span>}</div>)
}

export default function AgentSidebar() {
    const { agents, selectedAgentId, selectAgent, sendArchitectMessage, sendGodAction, agentePoseidoId, logs } = useGameStore();
    const [directMessage, setDirectMessage] = useState("");
    const [status, setStatus] = useState<'idle' | 'sending' | 'success' | 'error'>('idle');
    const [activeTab, setActiveTab] = useState<TabType>('perfil');
    const agent: Agent | undefined = agents.find((a) => a.id === selectedAgentId);

    const agentHistory = useMemo(() => {
        if (!selectedAgentId) return [];
        return filterAgentLogs(logs, selectedAgentId);
    }, [logs, selectedAgentId]);

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
                    <div className="relative p-6 pb-4 border-b border-white/5 bg-gradient-to-b from-white/5 to-transparent">
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

                        {/* Tabs */}
                        <div className="flex gap-1 mt-4 bg-black/30 rounded-lg p-1">
                            <button
                                onClick={() => setActiveTab('perfil')}
                                className={`flex-1 py-2 px-3 rounded-md text-xs font-bold uppercase tracking-wider transition-all ${
                                    activeTab === 'perfil'
                                        ? 'bg-[#7c4dff]/20 text-[#7c4dff] border border-[#7c4dff]/30'
                                        : 'text-gray-500 hover:text-gray-300'
                                }`}
                            >
                                Perfil
                            </button>
                            <button
                                onClick={() => setActiveTab('historial')}
                                className={`flex-1 py-2 px-3 rounded-md text-xs font-bold uppercase tracking-wider transition-all flex items-center justify-center gap-1.5 ${
                                    activeTab === 'historial'
                                        ? 'bg-[#7c4dff]/20 text-[#7c4dff] border border-[#7c4dff]/30'
                                        : 'text-gray-500 hover:text-gray-300'
                                }`}
                            >
                                <Clock className="w-3 h-3" />
                                Historial
                                {agentHistory.length > 0 && (
                                    <span className="ml-1 text-[9px] bg-[#7c4dff]/30 px-1.5 py-0.5 rounded-full font-mono">
                                        {agentHistory.length}
                                    </span>
                                )}
                            </button>
                        </div>
                    </div>

                    {/* Content */}
                    <div className="flex-1 overflow-y-auto custom-scrollbar">
                        {activeTab === 'historial' ? (
                            <HistorialTab agentId={selectedAgentId} history={agentHistory} />
                        ) : (
                            <PerfilTab
                                agent={agent}
                                directMessage={directMessage}
                                setDirectMessage={setDirectMessage}
                                status={status}
                                setStatus={setStatus}
                                sendArchitectMessage={sendArchitectMessage}
                                sendGodAction={sendGodAction}
                                agentePoseidoId={agentePoseidoId}
                            />
                        )}
                    </div>
                </motion.div>
            )}
        </AnimatePresence>
    );
}

// --- Perfil Tab ---
function PerfilTab({ agent, directMessage, setDirectMessage, status, setStatus, sendArchitectMessage, sendGodAction, agentePoseidoId }: {
    agent: Agent;
    directMessage: string;
    setDirectMessage: (v: string) => void;
    status: 'idle' | 'sending' | 'success' | 'error';
    setStatus: (s: 'idle' | 'sending' | 'success' | 'error') => void;
    sendArchitectMessage: (msg: string, agentId?: string) => Promise<string>;
    sendGodAction: (type: string, params: any) => Promise<boolean>;
    agentePoseidoId: string | null;
}) {
    const [chatMessages, setChatMessages] = useState<Array<{role: 'user' | 'agent', content: string}>>([]);

    const handleSend = async () => {
        if (!directMessage.trim()) return;

        const userMsg = directMessage.trim();
        setChatMessages(prev => [...prev, { role: 'user', content: userMsg }]);
        setDirectMessage("");
        setStatus('sending');

        try {
            const response = await sendArchitectMessage(userMsg, agent.id);
            setChatMessages(prev => [...prev, { role: 'agent', content: response }]);
            setStatus('success');
            setTimeout(() => setStatus('idle'), 2000);
        } catch (error: any) {
            console.error('Error sending message:', error);
            setStatus('error');
            setChatMessages(prev => [...prev, { role: 'agent', content: `*Error: ${error.message}*` }]);
            setTimeout(() => setStatus('idle'), 3000);
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && directMessage.trim() && status !== 'sending') {
            e.preventDefault();
            handleSend();
        }
    };

    return (
        <div className="p-6 space-y-8">
            <section className="space-y-4">
                <SectionTitle title="Métricas Principales" />
                <div className="grid grid-cols-2 gap-3">
                    <StatCard icon={Heart} label="Salud" value={agent?.necesidades?.salud} color="text-[#ff1744]" />
                    <StatCard icon={Zap} label="Recursos" value={agent?.resources} color="text-[#ffd600]" />
                    <StatCard icon={Brain} label="Aprendizaje" value={(agent?.skill_factor || 0) * 100} unit="%" color="text-[#7c4dff]" />
                    <StatCard icon={Wallet} label="MundoCoins" value={agent?.money} unit="MC" color="text-[#ffd600]" />
                </div>
            </section>

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
                        &ldquo;{agent?.pensamiento || "Procesando flujo de datos del entorno..."}&rdquo;
                    </p>
                </div>
            </section>

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

            <section className="space-y-4">
                <SectionTitle title="Conversación Directa" />
                <div className="glass-card p-4 rounded-xl border border-[#7c4dff]/30 bg-[#7c4dff]/5">
                    {/* Chat Messages */}
                    <div className="mb-4 h-64 overflow-y-auto custom-scrollbar space-y-3 pr-1">
                        {chatMessages.length === 0 ? (
                            <div className="flex flex-col items-center justify-center h-full text-center text-gray-500">
                                <MessageSquare className="w-8 h-8 mb-2 opacity-30" />
                                <p className="text-xs">Inicia una conversación<br />con {agent.id}</p>
                            </div>
                        ) : (
                            chatMessages.map((msg, i) => (
                                <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                                    <div className={`max-w-[85%] rounded-xl px-3 py-2 text-xs ${
                                        msg.role === 'user'
                                            ? 'bg-[#7c4dff]/20 border border-[#7c4dff]/30 text-[#7c4dff]'
                                            : 'bg-white/5 border border-white/10 text-gray-200'
                                    }`}>
                                        <p className="leading-relaxed">{msg.content}</p>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>

                    {/* Input */}
                    <div className="flex gap-2">
                        <input
                            type="text"
                            value={directMessage}
                            onChange={(e) => setDirectMessage(e.target.value)}
                            onKeyDown={handleKeyDown}
                            placeholder={status === 'sending' ? "Enviando..." : `Escribe a ${agent.id}...`}
                            disabled={status === 'sending'}
                            className="flex-1 bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-xs text-white placeholder:text-gray-600 focus:outline-none focus:border-[#7c4dff]/50 transition-colors disabled:opacity-50"
                        />
                        <button
                            onClick={handleSend}
                            disabled={!directMessage.trim() || status === 'sending'}
                            className={`px-3 py-2 rounded-lg transition-all ${
                                status === 'sending'
                                    ? 'bg-[#7c4dff]/50 cursor-wait'
                                    : status === 'error'
                                    ? 'bg-red-500/20 text-red-400 border border-red-500/30'
                                    : status === 'success'
                                    ? 'bg-[#00e676] text-white'
                                    : 'bg-[#7c4dff] text-white hover:bg-[#6c3eee]'
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
                        &ldquo;Conversa directamente con el agente usando LLM.&rdquo;
                    </p>
                </div>
            </section>

            <section className="space-y-4">
                <SectionTitle title="Datos Estructurales" />
                <div className="grid grid-cols-2 gap-3">
                    <InfoBlock label="Grupo" value={agent?.grupo_id || "Neutral"} />
                    <InfoBlock label="Profesión" value={agent?.profesion || "Ciudadano"} />
                    <InfoBlock label="Rol" value={agent?.rol || "Miembro"} />
                    <InfoBlock label="Reputación" value={`${((agent?.reputacion || 0) * 100).toFixed(0)}%`} />
                </div>
            </section>

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
                                    animate={{ width: `${((value as number) / 20) * 100}%` }}
                                    transition={{ duration: 1, ease: "circOut" }}
                                    className="h-full bg-gradient-to-r from-[#ffea00] to-[#ff9100]"
                                />
                            </div>
                        </div>
                    ))}
                </div>
            </section>

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

            {agent?.skills && Object.keys(agent.skills).length > 0 && (
                <section className="space-y-4">
                    <SectionTitle title="Módulos de Habilidad Creados" />
                    <div className="space-y-4">
                        {Object.entries(agent.skills).map(([skillName, skillData]) => (
                            <div key={skillName} className="relative group">
                                <div className="absolute -inset-[1px] bg-gradient-to-r from-[#7c4dff] to-[#00e676] rounded-xl opacity-20 group-hover:opacity-100 transition-opacity blur-[2px]" />
                                <div className="relative glass-card p-5 rounded-xl bg-[#0a0b10] border border-white/5 overflow-hidden">
                                    <div className="flex items-center justify-between mb-4">
                                        <div className="flex items-center gap-2">
                                            <div className="p-2 rounded-lg bg-[#7c4dff]/20 text-[#7c4dff]">
                                                <Code className="w-4 h-4" />
                                            </div>
                                            <span className="text-xs font-bold text-white uppercase tracking-wider font-mono">{skillData.name}</span>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <span className="text-[9px] text-gray-500 font-mono">v{skillData.version || "1.0.0"}</span>
                                            <div className="w-1.5 h-1.5 rounded-full bg-[#00e676] animate-pulse" />
                                        </div>
                                    </div>
                                    <p className="text-xs text-gray-400 mb-4 leading-relaxed line-clamp-2 italic">{skillData.description}</p>
                                    <div className="rounded-lg bg-black/60 border border-white/5 p-3 font-mono text-[9px] text-[#00e676]/70 group-hover:text-[#00e676] transition-colors overflow-x-auto custom-scrollbar">
                                        <div className="flex items-center gap-2 mb-2 pb-2 border-b border-white/5 opacity-50">
                                            <Terminal className="w-3 h-3" />
                                            <span className="text-[8px] uppercase tracking-tighter">python_module.py</span>
                                        </div>
                                        <pre className="whitespace-pre"><code>{skillData.code}</code></pre>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </section>
            )}
        </div>
    );
}

