"use client";

import useGameStore from "@/store/useGameStore";
import { X, Shield, Heart, Zap, Users, Wallet, Brain, MessageSquare, Send, Moon, Music, ListTodo, Code, Terminal, Ghost, Clock, Swords, Handshake, Globe, Lock, Eye, Target, Compass, Trophy } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useState, useMemo } from "react";
import { Agent, Plan } from "@/types/agent";

type TabType = 'perfil' | 'historial' | 'alma';

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

function getDesireDescription(tipo: string, intensidad: number): string {
    const i = intensidad;
    switch(tipo) {
        case 'supervivencia':
            if (i > 0.8) return "Deseo fervientemente asegurar mi vida y cubrir mis necesidades vitales críticas ya mismo.";
            if (i > 0.4) return "Mantengo una preocupación por mi bienestar físico y mis reservas de alimento.";
            return "Me siento a salvo y mis necesidades vitales están plenamente cubiertas.";
        case 'estatus_social':
            if (i > 0.8) return "Tengo una enorme ambición por mejorar mi poder y reputación frente al grupo urgentemente.";
            if (i > 0.4) return "Deseo interactuar para mantener mi influencia y buen nombre en la comunidad.";
            return "No me importa especialmente mi estatus en este momento. Estoy en paz con mi posición.";
        case 'acumulacion_recursos':
            if (i > 0.8) return "Mi máxima prioridad es amasar riqueza y recolectar materiales incansablemente.";
            if (i > 0.4) return "Busco asegurar un capital estable recolectando o comerciando lo necesario.";
            return "Estoy satisfecho con lo que tengo, la codicia no me mueve en este instante.";
        case 'armonia_grupal':
            if (i > 0.8) return "Me desespera ver conflictos; necesito fomentar alianzas y paz en mi entorno.";
            if (i > 0.4) return "Valoro la diplomacia y prefiero interactuar para ayudar a mis compañeros.";
            return "No priorizo las relaciones interpersonales ahora mismo, soy indiferente al grupo.";
        case 'aprendizaje':
            if (i > 0.8) return "Siento una intensa e insaciable curiosidad por observar, aprender y expandir mi intelecto a toda costa.";
            if (i > 0.4) return "Me gustaría observar mi entorno y adquirir alguna habilidad nueva.";
            return "Mis ganas de investigar y aprender cosas nuevas son bastante bajas.";
        case 'autonomia':
            if (i > 0.8) return "Necesito espacio y libertad desesperadamente, repudio las aglomeraciones y la quietud.";
            if (i > 0.4) return "Valoro mi independencia y disfrutaría explorando o moviéndome libremente.";
            return "Me siento muy cómodo con mi situación actual y siguiendo la inercia.";
        case 'reproduccion':
            if (i > 0.8) return "Siento una poderosa necesidad natural de buscar interacciones íntimas o forjar un legado.";
            if (i > 0.4) return "Tengo un interés claro en buscar interacciones sociales orientadas a vínculos muy cercanos.";
            return "Mis impulsos primales reproductivos o de intimidad están inactivos ahora mismo.";
        default:
            return "Tengo un impulso abstracto hacia este aspecto del mundo.";
    }
}

export default function AgentSidebar() {
    const { agents, selectedAgentId, selectAgent, sendArchitectMessage, sendGodAction, agentePoseidoId, poseerAgente, liberarAgente, logs } = useGameStore();
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
                             <button
                                 onClick={() => setActiveTab('alma')}
                                 className={`flex-1 py-2 px-3 rounded-md text-xs font-bold uppercase tracking-wider transition-all flex items-center justify-center gap-1.5 ${
                                     activeTab === 'alma'
                                         ? 'bg-[#7c4dff]/20 text-[#7c4dff] border border-[#7c4dff]/30'
                                         : 'text-gray-500 hover:text-gray-300'
                                 }`}
                             >
                                 <Heart className="w-3 h-3" />
                                 Alma
                             </button>
                         </div>
                    </div>

                     {/* Content */}
                     <div className="flex-1 overflow-y-auto custom-scrollbar">
                         {activeTab === 'historial' ? (
                             <HistorialTab agentId={selectedAgentId} history={agentHistory} />
                         ) : activeTab === 'alma' ? (
                             <AlmaTab agent={agent} />
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
                                 poseerAgente={poseerAgente}
                                 liberarAgente={liberarAgente}
                             />
                         )}
                     </div>
                </motion.div>
            )}
        </AnimatePresence>
    );
}

// --- Perfil Tab ---
function PerfilTab({ 
    agent, directMessage, setDirectMessage, status, setStatus, 
    sendArchitectMessage, sendGodAction, agentePoseidoId,
    poseerAgente, liberarAgente
}: {
    agent: Agent;
    directMessage: string;
    setDirectMessage: (v: string) => void;
    status: 'idle' | 'sending' | 'success' | 'error';
    setStatus: (s: 'idle' | 'sending' | 'success' | 'error') => void;
    sendArchitectMessage: (msg: string, agentId?: string) => Promise<string>;
    sendGodAction: (type: string, params: any) => Promise<boolean>;
    agentePoseidoId: string | null;
    poseerAgente: (agentId: string) => Promise<boolean>;
    liberarAgente: () => Promise<boolean>;
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
            {/* Botón de Posesión - Prioritario */}
            <section className="space-y-4">
                <SectionTitle title="Control de Entidad" />
                <div className="relative group overflow-hidden rounded-2xl">
                    <div className={`absolute -inset-[1px] bg-gradient-to-r ${agentePoseidoId === agent.id ? 'from-red-500 to-orange-500' : 'from-yellow-500 to-orange-500'} opacity-30 group-hover:opacity-100 transition-opacity blur-[2px]`} />
                    <button
                        onClick={() => agentePoseidoId === agent.id ? liberarAgente() : poseerAgente(agent.id)}
                        className={`relative w-full py-4 px-6 flex items-center justify-between transition-all ${
                            agentePoseidoId === agent.id 
                            ? 'bg-red-500/10 hover:bg-red-500/20 text-red-400' 
                            : 'bg-yellow-500/10 hover:bg-yellow-500/20 text-yellow-500'
                        }`}
                    >
                        <div className="flex items-center gap-4">
                            <div className={`p-3 rounded-xl ${agentePoseidoId === agent.id ? 'bg-red-500/20' : 'bg-yellow-500/20'}`}>
                                <Ghost className={`w-6 h-6 ${agentePoseidoId === agent.id ? 'animate-pulse' : ''}`} />
                            </div>
                            <div className="text-left">
                                <h4 className="text-sm font-black uppercase tracking-widest leading-none mb-1">
                                    {agentePoseidoId === agent.id ? 'Liberar Entidad' : 'Poseer Agente'}
                                </h4>
                                <p className="text-[10px] opacity-60 font-medium">
                                    {agentePoseidoId === agent.id 
                                        ? 'Cerrar enlace de consciencia' 
                                        : 'Tomar control directo del córtex'}
                                </p>
                            </div>
                        </div>
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center border ${
                            agentePoseidoId === agent.id ? 'border-red-500/30' : 'border-yellow-500/30'
                        }`}>
                            <div className={`w-2 h-2 rounded-full ${
                                agentePoseidoId === agent.id ? 'bg-red-500 shadow-[0_0_10px_#ef4444]' : 'bg-yellow-500'
                            }`} />
                        </div>
                    </button>
                </div>
            </section>

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
                    <SectionTitle title="Planes (Motor)" />
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

            {/* SECCIÓN BDI */}
            <section className="space-y-6">
                <SectionTitle title="Sistema de Razonamiento BDI" />
                
                {/* Creencias (Beliefs) */}
                <div className="space-y-3">
                    <div className="flex items-center gap-2 px-1">
                        <Eye className="w-4 h-4 text-cyan-400" />
                        <span className="text-[10px] font-bold text-cyan-400 uppercase tracking-widest">Sistema de Creencias</span>
                    </div>
                    <div className="grid grid-cols-1 gap-2">
                        {agent.creencias && Object.values(agent.creencias).length > 0 ? (
                            Object.values(agent.creencias).map((c: any, i) => (
                                <div key={i} className="bg-white/[0.02] border border-white/5 rounded-lg p-2.5 flex items-center justify-between group hover:bg-white/5 transition-colors">
                                    <div className="flex flex-col">
                                        <span className="text-[11px] text-gray-300 font-medium capitalize">{c.proposicion.replace(/_/g, ' ')}</span>
                                        <span className="text-[9px] text-gray-500 uppercase tracking-tighter">Fuente: {c.fuente}</span>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <div className="text-right">
                                            <div className="text-[11px] font-mono font-bold text-cyan-400">{(c.probabilidad * 100).toFixed(0)}%</div>
                                        </div>
                                        <div className="w-12 h-1.5 bg-white/5 rounded-full overflow-hidden">
                                            <div className="h-full bg-cyan-500/50" style={{ width: `${c.probabilidad * 100}%` }} />
                                        </div>
                                    </div>
                                </div>
                            ))
                        ) : (
                            <p className="text-[10px] text-gray-600 italic px-2">Sin creencias formadas...</p>
                        )}
                    </div>
                </div>

                {/* Deseos (Desires) */}
                <div className="space-y-3">
                    <div className="flex items-center gap-2 px-1">
                        <Target className="w-4 h-4 text-rose-400" />
                        <span className="text-[10px] font-bold text-rose-400 uppercase tracking-widest">Matriz de Deseos</span>
                    </div>
                    <div className="glass-card p-4 rounded-xl space-y-3">
                        {agent.deseos?.deseos && Object.values(agent.deseos.deseos).map((d: any, i) => (
                            <div key={i} className="space-y-1.5 bg-white/5 p-2 rounded-lg border border-white/[0.05]">
                                <div className="flex justify-between text-[10px] items-center mb-1">
                                    <span className="text-gray-300 capitalize font-black tracking-wider">{d.tipo.replace(/_/g, ' ')}</span>
                                    <span className="text-rose-400 font-mono">{(d.intensidad * 100).toFixed(0)}%</span>
                                </div>
                                <p className="text-[10px] text-rose-200/80 italic mb-1.5 border-l-2 border-rose-500/50 pl-2 leading-tight">
                                    {getDesireDescription(d.tipo, d.intensidad)}
                                </p>
                                <div className="h-1 w-full bg-black/50 rounded-full overflow-hidden">
                                    <motion.div 
                                        initial={{ width: 0 }} 
                                        animate={{ width: `${d.intensidad * 100}%` }} 
                                        className="h-full bg-gradient-to-r from-rose-600 to-rose-400" 
                                    />
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Intenciones Actuales (Intentions) */}
                <div className="space-y-3">
                    <div className="flex items-center gap-2 px-1">
                        <Compass className="w-4 h-4 text-emerald-400" />
                        <span className="text-[10px] font-bold text-emerald-400 uppercase tracking-widest">Plan de Intención</span>
                    </div>
                    {agent.intenciones?.plan_actual ? (
                        <div className="relative p-5 rounded-2xl bg-emerald-500/5 border border-emerald-500/20 overflow-hidden">
                            <div className="flex items-center justify-between mb-4">
                                <h4 className="text-xs font-bold text-white uppercase tracking-tight">{agent.intenciones.plan_actual.meta}</h4>
                                <span className="text-[9px] font-mono text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/20">PRIORIDAD {agent.intenciones.plan_actual.prioridad}</span>
                            </div>
                            <div className="space-y-3 ml-2 border-l border-white/5 pl-4">
                                {agent.intenciones.plan_actual.acciones.map((acc: any, i: number) => {
                                    const isCurrent = i === agent.intenciones?.plan_actual?.tiempo_actual;
                                    const isDone = i < (agent.intenciones?.plan_actual?.tiempo_actual || 0);
                                    
                                    return (
                                        <div key={i} className={`relative flex items-center gap-3 ${isDone ? 'opacity-40' : ''}`}>
                                            <div className={`absolute -left-[21px] w-2 h-2 rounded-full border ${
                                                isCurrent ? 'bg-emerald-500 border-emerald-400 scale-125 shadow-[0_0_8px_#10b981]' : 
                                                isDone ? 'bg-gray-600 border-gray-500' : 'bg-[#0a0b10] border-white/20'
                                            }`} />
                                            <div className="flex-1 min-w-0">
                                                <p className={`text-[11px] font-bold ${isCurrent ? 'text-white' : 'text-gray-400'}`}>
                                                    {acc.nombre}
                                                </p>
                                                <p className="text-[9px] text-gray-500 truncate">{acc.meta}</p>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                            <div className="mt-4 pt-3 border-t border-white/5 flex justify-between items-center">
                                <span className="text-[9px] text-gray-500 font-mono italic">Paso {agent.intenciones.plan_actual.tiempo_actual + 1} de {agent.intenciones.plan_actual.acciones.length}</span>
                                <Trophy className="w-3 h-3 text-emerald-500/30" />
                            </div>
                        </div>
                    ) : (
                        <div className="glass-card p-4 rounded-xl text-center">
                            <p className="text-[10px] text-gray-500 italic">No hay un plan activo en el sistema BDI.</p>
                        </div>
                    )}
                </div>
            </section>

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

// --- Alma Tab ---
function AlmaTab({ agent }: { agent: Agent }) {
    const alma = agent.alma;
    if (!alma) {
        return (
            <div className="flex flex-col items-center justify-center py-16 text-gray-500">
                <Heart className="w-12 h-12 mb-4 opacity-20" />
                <p className="text-sm">Este agente aún no ha desarrollado un Alma.</p>
            </div>
        );
    }

    return (
        <div className="flex-1 overflow-y-auto custom-scrollbar p-4 space-y-6">
            {/* Header del Alma */}
            <section className="glass-card p-5 rounded-xl border border-white/5 bg-gradient-to-br from-[#7c4dff]/10 to-[#ff00ff]/10">
                <div className="flex items-start justify-between mb-4">
                    <div>
                        <h3 className="text-lg font-bold text-white mb-1">{alma.nombre_propio || 'Sin nombre propio'}</h3>
                        <p className="text-xs text-gray-400">{alma.arquetipo} • {alma.tono_comunicativo}</p>
                    </div>
                    <div className="text-2xl">
                        {alma.arquetipo === 'Explorador' && '🧭'}
                        {alma.arquetipo === 'Sanador' && '💚'}
                        {alma.arquetipo === 'Guerrero' && '⚔️'}
                        {alma.arquetipo === 'Sabio' && '📚'}
                        {alma.arquetipo === 'Constructor' && '🔨'}
                        {alma.arquetipo === 'Mercader' && '💰'}
                        {alma.arquetipo === 'Diplomático' && '🤝'}
                        {alma.arquetipo === 'Rebelde' && '🔥'}
                        {alma.arquetipo === 'Ermitaño' && '🌑'}
                        {alma.arquetipo === 'Visionario' && '👁️'}
                        {alma.arquetipo === 'Historiador' && '📜'}
                        {alma.arquetipo === 'Guardián' && '🛡️'}
                    </div>
                </div>
                {alma.narrativa_personal && (
                    <p className="text-sm text-gray-300 italic leading-relaxed mb-4">"{alma.narrativa_personal}"</p>
                )}
                <div className="flex gap-4 text-xs">
                    <div className="flex-1 bg-black/30 rounded-lg p-3 border border-white/5">
                        <div className="text-gray-500 mb-1">Nivel de Conciencia</div>
                        <div className="text-white font-mono font-bold">{(alma.nivel_conciencia * 100).toFixed(0)}%</div>
                        <div className="w-full bg-gray-700 h-1.5 mt-2 rounded-full overflow-hidden">
                            <div className="bg-gradient-to-r from-[#7c4dff] to-[#00e676] h-full" style={{ width: `${alma.nivel_conciencia * 100}%` }} />
                        </div>
                    </div>
                    <div className="flex-1 bg-black/30 rounded-lg p-3 border border-white/5">
                        <div className="text-gray-500 mb-1">Capacidad de Reflexión</div>
                        <div className="text-white font-mono font-bold">{(alma.capacidad_reflexion * 100).toFixed(0)}%</div>
                        <div className="w-full bg-gray-700 h-1.5 mt-2 rounded-full overflow-hidden">
                            <div className="bg-gradient-to-r from-[#ff9100] to-[#ff00ff] h-full" style={{ width: `${alma.capacidad_reflexion * 100}%` }} />
                        </div>
                    </div>
                </div>
            </section>

            {/* Valores */}
            <section className="space-y-3">
                <h3 className="text-sm font-bold text-white uppercase tracking-wider mb-3">Valores Principales</h3>
                <div className="space-y-2">
                    {Object.values(alma.valores || {})
                        .sort((a: any, b: any) => b.peso - a.peso)
                        .slice(0, 5)
                        .map((valor: any, idx: number) => (
                            <div key={idx} className="glass-card p-3 rounded-lg border border-white/5 bg-white/[0.02]">
                                <div className="flex justify-between items-center mb-2">
                                    <span className="text-sm font-bold text-white capitalize">{valor.nombre}</span>
                                    <span className="text-xs font-mono text-[#7c4dff]">{(valor.peso * 100).toFixed(0)}%</span>
                                </div>
                                <div className="w-full bg-gray-700 h-1.5 rounded-full overflow-hidden">
                                    <div className="bg-gradient-to-r from-[#7c4dff] to-[#00e676] h-full" style={{ width: `${valor.peso * 100}%` }} />
                                </div>
                                {valor.definicion_propia && (
                                    <p className="text-xs text-gray-500 mt-2 italic">"{valor.definicion_propia}"</p>
                                )}
                            </div>
                        ))}
                </div>
            </section>

            {/* Límites (Tabúes) */}
            {alma.tabues && alma.tabues.length > 0 && (
                <section className="space-y-3">
                    <h3 className="text-sm font-bold text-white uppercase tracking-wider mb-3">Límites (Tabúes)</h3>
                    <div className="space-y-2">
                        {alma.tabues.map((tabu: string, idx: number) => (
                            <div key={idx} className="glass-card p-3 rounded-lg border border-red-500/20 bg-red-500/5">
                                <p className="text-xs text-red-300">❌ {tabu}</p>
                            </div>
                        ))}
                    </div>
                </section>
            )}

            {/* Historia Personal */}
            <section className="space-y-3">
                <h3 className="text-sm font-bold text-white uppercase tracking-wider mb-3">Historia Personal</h3>
                <div className="grid grid-cols-2 gap-3">
                    {alma.traumas && alma.traumas.length > 0 && (
                        <div className="glass-card p-3 rounded-lg border border-orange-500/20 bg-orange-500/5">
                            <h4 className="text-xs font-bold text-orange-400 mb-2">Heridas</h4>
                            {alma.traumas.slice(-2).map((t: any, i: number) => (
                                <p key={i} className="text-[10px] text-gray-400 italic mb-1">• {t.descripcion}</p>
                            ))}
                        </div>
                    )}
                    {alma.epifanias && alma.epifanias.length > 0 && (
                        <div className="glass-card p-3 rounded-lg border border-[#00e676]/20 bg-[#00e676]/5">
                            <h4 className="text-xs font-bold text-[#00e676] mb-2">Revelaciones</h4>
                            {alma.epifanias.slice(-2).map((e: any, i: number) => (
                                <p key={i} className="text-[10px] text-gray-300 italic mb-1">• {e.descripcion}</p>
                            ))}
                        </div>
                    )}
                    {alma.triunfos && alma.triunfos.length > 0 && (
                        <div className="glass-card p-3 rounded-lg border border-[#7c4dff]/20 bg-[#7c4dff]/5">
                            <h4 className="text-xs font-bold text-[#7c4dff] mb-2">Triunfos</h4>
                            {alma.triunfos.slice(-2).map((t: any, i: number) => (
                                <p key={i} className="text-[10px] text-gray-300 italic mb-1">• {t.descripcion}</p>
                            ))}
                        </div>
                    )}
                </div>
            </section>

            {/* Filosofía y Relación con el Arquitecto */}
            <section className="space-y-3">
                <h3 className="text-sm font-bold text-white uppercase tracking-wider mb-3">Filosofía Existencial</h3>
                {alma.filosofia_existencial && (
                    <div className="glass-card p-4 rounded-xl border border-white/5 bg-gradient-to-r from-[#7c4dff]/5 to-transparent">
                        <p className="text-sm text-gray-300 italic leading-relaxed">"{alma.filosofia_existencial}"</p>
                    </div>
                )}
                <div className="glass-card p-3 rounded-lg border border-white/5 bg-white/[0.02]">
                    <div className="flex justify-between items-center">
                        <span className="text-xs text-gray-500">Relación con el Arquitecto</span>
                        <span className={`text-xs font-bold capitalize ${
                            alma.relacion_con_arquitecto === 'devoto' ? 'text-[#00e676]' :
                            alma.relacion_con_arquitecto === 'rebelde' ? 'text-red-400' :
                            alma.relacion_con_arquitecto === 'protector' ? 'text-blue-400' :
                            'text-gray-300'
                        }`}>{alma.relacion_con_arquitecto}</span>
                    </div>
                </div>
            </section>
        </div>
    );
}


