"use client";

import useGameStore from "@/store/useGameStore";
import { getHttpUrl } from "@/utils/apiConfig";
import { replaceIdsWithNames } from "@/utils/nameUtils";
import { X, Shield, Heart, Zap, Users, Wallet, Brain, MessageSquare, Send, Moon, Music, ListTodo, Code, Terminal, Ghost, Clock, Swords, Handshake, Globe, Lock, Eye, Target, Compass, Trophy, Play, ChevronRight, Microscope } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useState, useMemo } from "react";
import { Agent, Plan } from "@/types/agent";

type TabType = 'perfil' | 'historial' | 'alma' | 'creaciones';

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
        
        const agents = useGameStore.getState().agents;
        return replaceIdsWithNames(msg, agents);
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

import ControlAgentePanel from "./ControlAgentePanel";

// ... (rest of helper functions)

export default function AgentSidebar() {
    const { agents, selectedAgentId, selectAgent, sendArchitectMessage, sendGodAction, agentePoseidoId, poseerAgente, liberarAgente, logs, userId } = useGameStore();
    const [directMessage, setDirectMessage] = useState("");
    const [status, setStatus] = useState<'idle' | 'sending' | 'success' | 'error'>('idle');
    const [activeTab, setActiveTab] = useState<TabType>('perfil');
    const [executingApp, setExecutingApp] = useState<any | null>(null);
    const [executingSkill, setExecutingSkill] = useState<any | null>(null);
    const [isControlling, setIsControlling] = useState(false);
    const agent: Agent | undefined = agents.find((a) => a.id === selectedAgentId);

    const agentHistory = useMemo(() => {
        if (!selectedAgentId) return [];
        return filterAgentLogs(logs, selectedAgentId);
    }, [logs, selectedAgentId]);

    if (!agent) return null;

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
                    <AnimatePresence mode="wait">
                        {isControlling ? (
                            <motion.div 
                                key="control-panel"
                                initial={{ opacity: 0, x: 20 }}
                                animate={{ opacity: 1, x: 0 }}
                                exit={{ opacity: 0, x: -20 }}
                                className="h-full"
                            >
                                <ControlAgentePanel agent={agent} onClose={() => setIsControlling(false)} />
                            </motion.div>
                        ) : (
                            <motion.div 
                                key="info-panel"
                                initial={{ opacity: 0, x: -20 }}
                                animate={{ opacity: 1, x: 0 }}
                                exit={{ opacity: 0, x: 20 }}
                                className="h-full flex flex-col"
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
                                                    {agent.identidad?.emoji || "🤖"}
                                                </span>
                                            </div>
                                        </div>
                                        <div className="flex-1">
                                            <div className="flex justify-between items-start">
                                                <h2 className="text-2xl font-bold text-white tracking-tight mb-1 uppercase">
                                                    {agent.identidad?.nombre || agent.alma?.nombre_propio || "AGENTE"}
                                                </h2>
                                            </div>
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
                                    <div 
                                        className="flex gap-1 mt-4 bg-black/30 rounded-lg p-1 overflow-x-auto no-scrollbar"
                                        style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}
                                    >
                                        <button
                                            onClick={() => setActiveTab('perfil')}
                                            className={`flex-1 min-w-max py-2 px-2.5 rounded-md text-[10px] font-black uppercase tracking-wider transition-all ${
                                                activeTab === 'perfil'
                                                    ? 'bg-[#7c4dff]/20 text-[#7c4dff] border border-[#7c4dff]/30'
                                                    : 'text-gray-500 hover:text-gray-300'
                                            }`}
                                        >
                                            Perfil
                                        </button>
                                        <button
                                            onClick={() => setActiveTab('alma')}
                                            className={`flex-1 min-w-max py-2 px-2.5 rounded-md text-[10px] font-black uppercase tracking-wider transition-all flex items-center justify-center gap-1.5 ${
                                                activeTab === 'alma'
                                                    ? 'bg-[#7c4dff]/20 text-[#7c4dff] border border-[#7c4dff]/30'
                                                    : 'text-gray-500 hover:text-gray-300'
                                            }`}
                                        >
                                            <Heart className="w-3 h-3" />
                                            Alma
                                        </button>
                                        <button
                                            onClick={() => setActiveTab('historial')}
                                            className={`flex-1 min-w-max py-2 px-2.5 rounded-md text-[10px] font-black uppercase tracking-wider transition-all flex items-center justify-center gap-1.5 ${
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
                                            onClick={() => setActiveTab('creaciones')}
                                            className={`flex-1 min-w-max py-2 px-2.5 rounded-md text-[10px] font-black uppercase tracking-wider transition-all flex items-center justify-center gap-1.5 ${
                                                activeTab === 'creaciones'
                                                    ? 'bg-[#7c4dff]/20 text-[#7c4dff] border border-[#7c4dff]/30'
                                                    : 'text-gray-500 hover:text-gray-300'
                                            }`}
                                        >
                                            <Terminal className="w-3 h-3" />
                                            Apps
                                        </button>
                                    </div>
                                </div>

                                {/* Content */}
                                <div className="flex-1 overflow-y-auto custom-scrollbar">
                                    {activeTab === 'historial' ? (
                                        <HistorialTab agentId={selectedAgentId} history={agentHistory} />
                                    ) : activeTab === 'alma' ? (
                                        <AlmaTab agent={agent} />
                                    ) : activeTab === 'creaciones' ? (
                                        <CreacionesTab agent={agent} onRunApp={(app) => setExecutingApp(app)} onRunSkill={(skill) => setExecutingSkill(skill)} />
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
                                            onStartControl={() => setIsControlling(true)}
                                        />
                                    )}
                                </div>
                            </motion.div>
                        )}
                    </AnimatePresence>

                     <AppExecutionModal 
                        app={executingApp} 
                        skill={executingSkill} 
                        agentId={agent.id}
                        userId={userId}
                        onClose={() => { setExecutingApp(null); setExecutingSkill(null); }} 
                     />
                </motion.div>
            )}
        </AnimatePresence>
    );
}

// --- Perfil Tab ---
function PerfilTab({ 
    agent, directMessage, setDirectMessage, status, setStatus, 
    sendArchitectMessage, sendGodAction, agentePoseidoId,
    poseerAgente, liberarAgente, onStartControl
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
    onStartControl: () => void;
}) {
    const [chatMessages, setChatMessages] = useState<Array<{role: 'user' | 'agent', content: string}>>([]);
    const [beliefsCollapsed, setBeliefsCollapsed] = useState(false);
    const [desiresCollapsed, setDesiresCollapsed] = useState(false);

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
            {/* 1. CONTROL DE ENTIDAD - Herramientas del Arquitecto (al inicio) */}
            <section className="space-y-4">
                <SectionTitle title="Control de Entidad" />
                <div className="grid grid-cols-1 gap-3">
                    {/* Botón Poseer */}
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
                        </button>
                    </div>

                    {/* Botón Control Total */}
                    <div className="relative group overflow-hidden rounded-2xl">
                        <div className="absolute -inset-[1px] bg-gradient-to-r from-indigo-500 to-purple-500 opacity-30 group-hover:opacity-100 transition-opacity blur-[2px]" />
                        <button
                            onClick={onStartControl}
                            className="relative w-full py-4 px-6 flex items-center justify-between transition-all bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-400"
                        >
                            <div className="flex items-center gap-4">
                                <div className="p-3 rounded-xl bg-indigo-500/20">
                                    <Zap className="w-6 h-6 group-hover:animate-pulse" />
                                </div>
                                <div className="text-left">
                                    <h4 className="text-sm font-black uppercase tracking-widest leading-none mb-1">
                                        Panel de Control
                                    </h4>
                                    <p className="text-[10px] opacity-60 font-medium">
                                        Acceder al centro de comando del agente
                                    </p>
                                </div>
                            </div>
                        </button>
                    </div>
                </div>
            </section>

            {/* 2. CÓRTEX NEURAL - Lo que está pasando por su cabeza ahora mismo */}
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

            {/* 2. PLANES E INTENCIONES - ¿Qué está intentando hacer? */}
            <section className="space-y-6">
                <SectionTitle title="Objetivos e Intenciones" />
                
                {/* Intenciones Actuales (BDI) */}
                <div className="space-y-3">
                    <div className="flex items-center gap-2 px-1">
                        <Compass className="w-4 h-4 text-emerald-400" />
                        <span className="text-[10px] font-bold text-emerald-400 uppercase tracking-widest">Plan de Intención (BDI)</span>
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

                {/* Planes (Motor) */}
                {agent?.planes && agent.planes.length > 0 && (
                    <div className="glass-card p-5 rounded-xl space-y-3">
                        <div className="flex items-center gap-2 mb-1">
                            <ListTodo className="w-4 h-4 text-[#00e676]" />
                            <span className="text-[10px] font-bold text-[#00e676] uppercase tracking-widest">Planes del Motor</span>
                        </div>
                        {agent.planes.map((plan: Plan, index) => (
                            <div key={index} className="flex items-start gap-3">
                                <ChevronRight className="w-3 h-3 text-gray-500 mt-1 flex-shrink-0" />
                                <p className="text-sm text-gray-300 leading-snug">{plan.objetivo}</p>
                            </div>
                        ))}
                    </div>
                )}
            </section>

            {/* 3. ESTADO FÍSICO Y RECURSOS */}
            <section className="space-y-4">
                <SectionTitle title="Métricas y Necesidades" />
                <div className="grid grid-cols-2 gap-3">
                    <StatCard icon={Heart} label="Salud" value={agent?.necesidades?.salud} color="text-[#ff1744]" />
                    <StatCard icon={Zap} label="Recursos" value={agent?.resources} color="text-[#ffd600]" />
                    <StatCard icon={Brain} label="Aprendizaje" value={(agent?.skill_factor || 0) * 100} unit="%" color="text-[#7c4dff]" />
                    <StatCard icon={Wallet} label="MundoCoins" value={agent?.money} unit="MC" color="text-[#ffd600]" />
                </div>
                <div className="glass-card p-5 rounded-xl space-y-4">
                    <ProgressBar icon={Heart} label="Salud" value={agent?.necesidades?.salud} color="bg-[#ff1744]" />
                    <ProgressBar icon={Shield} label="Seguridad" value={agent?.necesidades?.seguridad} color="bg-[#2979ff]" />
                    <ProgressBar icon={Users} label="Social" value={agent?.necesidades?.social} color="bg-[#00e676]" />
                    <ProgressBar icon={Zap} label="Alimento" value={agent?.necesidades?.alimento} color="bg-[#ffa000]" />
                    <ProgressBar icon={Moon} label="Descanso" value={agent?.necesidades?.descanso} color="bg-[#7c4dff]" />
                    <ProgressBar icon={Music} label="Ocio" value={agent?.necesidades?.entretenimiento} color="bg-[#ec4899]" />
                </div>
            </section>

            {/* 4. INVENTARIO DE RECURSOS */}
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

            {/* 5. MATRIZ FUNCIONAL (Personalidad y Skills) */}
            <section className="space-y-6">
                <SectionTitle title="Matriz Funcional" />
                
                {/* Personalidad */}
                <div className="space-y-3">
                    <div className="flex items-center gap-2 px-1">
                        <Ghost className="w-4 h-4 text-[#00e676]" />
                        <span className="text-[10px] font-bold text-[#00e676] uppercase tracking-widest">Rasgos de Personalidad</span>
                    </div>
                    <div className="glass-card p-5 rounded-xl space-y-4">
                        {Object.entries(agent?.personalidad || {}).map(([trait, value]) => (
                            <div key={trait} className="space-y-1.5">
                                <div className="flex justify-between text-[10px] items-center">
                                    <span className="text-gray-400 capitalize font-bold tracking-wider">{trait}</span>
                                    <span className="text-[#00e676] font-mono">{(value as number * 100).toFixed(0)}%</span>
                                </div>
                                <div className="h-1 w-full bg-white/5 rounded-full overflow-hidden">
                                    <motion.div
                                        initial={{ width: 0 }}
                                        animate={{ width: `${(value as number) * 100}%` }}
                                        className="h-full bg-gradient-to-r from-[#7c4dff] to-[#00e676]"
                                    />
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Habilidades */}
                <div className="space-y-3">
                    <div className="flex items-center gap-2 px-1">
                        <Zap className="w-4 h-4 text-[#ff9100]" />
                        <span className="text-[10px] font-bold text-[#ff9100] uppercase tracking-widest">Habilidades y Experiencia</span>
                    </div>
                    <div className="glass-card p-5 rounded-xl space-y-4">
                        {Object.entries(agent?.experiencia || {}).map(([skill, value]) => (
                            <div key={skill} className="space-y-1.5">
                                <div className="flex justify-between text-[10px] items-center">
                                    <span className="text-gray-400 capitalize font-bold tracking-wider">{skill}</span>
                                    <span className="text-[#ff9100] font-mono">Nivel {value as number}</span>
                                </div>
                                <div className="h-1 w-full bg-white/5 rounded-full overflow-hidden">
                                    <motion.div
                                        initial={{ width: 0 }}
                                        animate={{ width: `${((value as number) / 20) * 100}%` }}
                                        className="h-full bg-gradient-to-r from-[#ffea00] to-[#ff9100]"
                                    />
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* 6. CONTEXTO SOCIAL Y ESTRUCTURA */}
            <section className="space-y-6">
                <SectionTitle title="Sociedad y Estructura" />
                
                {/* Capital Social */}
                <div className="glass-card p-5 rounded-xl space-y-4">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className="p-2 rounded-lg bg-[#00e5ff]/20 text-[#00e5ff]">
                                <Globe className="w-5 h-5" />
                            </div>
                            <div>
                                <span className="text-xs font-bold text-white uppercase">Influencia Social</span>
                                <div className="text-[10px] text-gray-500">{agent?.social_metrics?.nivel_influencia || "Desconocido"}</div>
                            </div>
                        </div>
                        <div className="text-right">
                            <span className="text-2xl font-bold text-[#00e5ff]">{agent?.social_metrics?.capital_social?.toFixed(0) || "10"}</span>
                            <span className="text-xs text-gray-500">/100</span>
                        </div>
                    </div>
                    <div className="w-full h-3 bg-white/10 rounded-full overflow-hidden">
                        <div 
                            className="h-full bg-gradient-to-r from-[#00e5ff] to-[#7c4dff] transition-all duration-500"
                            style={{ width: `${Math.min(100, agent?.social_metrics?.capital_social || 10)}%` }}
                        />
                    </div>
                    <div className="grid grid-cols-2 gap-3 text-[10px]">
                        <div className="bg-white/[0.03] rounded-lg p-2 flex items-center gap-2">
                            <Users className="w-3 h-3 text-[#00e676]" />
                            <span className="text-gray-400">Seguidores:</span>
                            <span className="text-white font-bold">{agent?.social_metrics?.seguidores || 0}</span>
                        </div>
                        <div className="bg-white/[0.03] rounded-lg p-2 flex items-center gap-2">
                            <Users className="w-3 h-3 text-gray-400" />
                            <span className="text-gray-400">Siguiendo:</span>
                            <span className="text-white font-bold">{agent?.social_metrics?.siguiendo || 0}</span>
                        </div>
                        <div className="bg-white/[0.03] rounded-lg p-2 flex items-center gap-2">
                            <MessageSquare className="w-3 h-3 text-[#ffa000]" />
                            <span className="text-gray-400">Posts:</span>
                            <span className="text-white font-bold">{agent?.social_metrics?.posts_publicados || 0}</span>
                        </div>
                        <div className="bg-white/[0.03] rounded-lg p-2 flex items-center gap-2">
                            <Heart className="w-3 h-3 text-[#ec4899]" />
                            <span className="text-gray-400">Likes:</span>
                            <span className="text-white font-bold">{agent?.social_metrics?.likes_recibidos || 0}</span>
                        </div>
                    </div>
                </div>

                {/* Estructura */}
                <div className="grid grid-cols-2 gap-3">
                    <InfoBlock label="Grupo" value={agent?.grupo_id || "Neutral"} />
                    <InfoBlock label="Profesión" value={agent?.profesion || "Ciudadano"} />
                    <InfoBlock label="Rol" value={agent?.rol || "Miembro"} />
                    <InfoBlock label="Reputación" value={`${((agent?.reputacion || 0) * 100).toFixed(0)}%`} />
                </div>
            </section>

            {/* 7. PSIQUE PROFUNDA (BDI) */}
            <section className="space-y-6">
                <SectionTitle title="Psicología Profunda (BDI)" />
                
                {/* Necesidades Intelectuales */}
                <div className="glass-card p-5 rounded-xl space-y-3">
                    <div className="flex items-center gap-2 mb-1">
                        <Microscope className="w-4 h-4 text-[#7c4dff]" />
                        <span className="text-[10px] font-bold text-[#7c4dff] uppercase tracking-widest">Inquietudes Intelectuales</span>
                    </div>
                    <ProgressBar icon={Compass} label="Curiosidad" value={agent?.necesidades_intelectuales?.curiosidad ?? 6} color="bg-[#7c4dff]" />
                    <ProgressBar icon={MessageSquare} label="Expresión" value={agent?.necesidades_intelectuales?.expresion ?? 6} color="bg-[#00e5ff]" />
                    <ProgressBar icon={Trophy} label="Debate" value={agent?.necesidades_intelectuales?.debate ?? 5} color="bg-[#ffa000]" />
                    <ProgressBar icon={Brain} label="Aprendizaje" value={agent?.necesidades_intelectuales?.aprendizaje ?? 6} color="bg-[#00e676]" />
                </div>
                
                {/* Creencias (Beliefs) */}
                <div className="space-y-3">
                    <div className="flex items-center gap-2 px-1">
                        <Eye className="w-4 h-4 text-cyan-400" />
                        <span className="text-[10px] font-bold text-cyan-400 uppercase tracking-widest">Sistema de Creencias</span>
                        <button
                            onClick={() => setBeliefsCollapsed(!beliefsCollapsed)}
                            className="ml-auto p-1.5 rounded-full hover:bg-white/5 transition-transform"
                        >
                            <ChevronRight className={`w-4 h-4 text-gray-300 ${beliefsCollapsed ? 'rotate-0' : 'rotate-90'} transition-transform`} />
                        </button>
                    </div>

                    {!beliefsCollapsed ? (
                        <div className="grid grid-cols-1 gap-2">
                            {agent.creencias && Object.values(agent.creencias).length > 0 ? (
                                Object.values(agent.creencias).map((c: any, i) => (
                                    <div key={i} className="bg-white/[0.02] border border-white/5 rounded-lg p-2.5 flex items-center justify-between group hover:bg-white/5 transition-colors">
                                        <div className="flex flex-col">
                                            <span className="text-[11px] text-gray-300 font-medium capitalize">{(c.proposicion || "").replace(/_/g, ' ')}</span>
                                            <span className="text-[9px] text-gray-500 uppercase tracking-tighter">Fuente: {c.fuente}</span>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <div className="text-[11px] font-mono font-bold text-cyan-400">{(c.probabilidad * 100).toFixed(0)}%</div>
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
                    ) : (
                        <div className="px-2">
                            <p className="text-[10px] text-gray-500 italic">Creencias ocultas ({Object.values(agent.creencias || {}).length})</p>
                        </div>
                    )}
                </div>

                {/* Deseos (Desires) */}
                <div className="space-y-3">
                    <div className="flex items-center gap-2 px-1">
                        <Target className="w-4 h-4 text-rose-400" />
                        <span className="text-[10px] font-bold text-rose-400 uppercase tracking-widest">Matriz de Deseos</span>
                        <button
                            onClick={() => setDesiresCollapsed(!desiresCollapsed)}
                            className="ml-auto p-1.5 rounded-full hover:bg-white/5 transition-transform"
                        >
                            <ChevronRight className={`w-4 h-4 text-gray-300 ${desiresCollapsed ? 'rotate-0' : 'rotate-90'} transition-transform`} />
                        </button>
                    </div>

                    {!desiresCollapsed ? (
                        <div className="glass-card p-4 rounded-xl space-y-3">
                            {agent.deseos?.deseos && Object.values(agent.deseos.deseos).map((d: any, i) => (
                                <div key={i} className="space-y-1.5 bg-white/5 p-2 rounded-lg border border-white/[0.05]">
                                    <div className="flex justify-between text-[10px] items-center mb-1">
                                        <span className="text-gray-300 capitalize font-black tracking-wider">{(d.tipo || "").replace(/_/g, ' ')}</span>
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
                    ) : (
                        <div className="px-2">
                            <p className="text-[10px] text-gray-500 italic">Deseos ocultos ({Object.values(agent.deseos?.deseos || {}).length})</p>
                        </div>
                    )}
                </div>
            </section>

            {/* 8. CONVERSACIÓN DIRECTA */}
            <section className="space-y-4">
                <SectionTitle title="Canal de Consciencia Directo" />
                <div className="glass-card p-4 rounded-xl border border-indigo-500/30 bg-indigo-500/5">
                    {/* Chat Messages */}
                    <div className="mb-4 h-64 overflow-y-auto custom-scrollbar space-y-3 pr-1">
                        {chatMessages.length === 0 ? (
                                <div className="flex flex-col items-center justify-center h-full text-center text-gray-500">
                                    <MessageSquare className="w-8 h-8 mb-2 opacity-30" />
                                    <p className="text-xs">Inicia una conversación<br />con {agent.identidad?.nombre || "este agente"}</p>
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
                            placeholder={status === 'sending' ? "Enviando..." : `Escribe a ${agent.identidad?.nombre || "el agente"}...`}
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


            {/* Las habilidades creadas se muestran en la pestaña "Apps" → "Skills" */}
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
                        <h3 className="text-lg font-bold text-white mb-1">{agent.identidad?.nombre || alma.nombre_propio || 'Sin nombre propio'}</h3>
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

            {/* Reflexiones Recientes */}
            {alma.reflexiones && alma.reflexiones.length > 0 && (
                <section className="space-y-3">
                    <h3 className="text-sm font-bold text-white uppercase tracking-wider mb-3">Reflexiones Recientes</h3>
                    <div className="glass-card p-3 rounded-lg border border-white/5 bg-white/[0.02]">
                        {alma.reflexiones.slice(-3).reverse().map((r: any, i: number) => (
                            <p key={i} className="text-[10px] text-gray-300 italic mb-1">• {r.descripcion || r.leccion || r.texto || String(r)}</p>
                        ))}
                    </div>
                </section>
            )}

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

// --- Creaciones Tab ---
function CreacionesTab({ 
    agent, 
    onRunApp, 
    onRunSkill 
}: { 
    agent: Agent; 
    onRunApp: (app: any) => void; 
    onRunSkill: (skill: any) => void;
}) {
    const apps = Object.values(agent.apps || {});
    const skills = Object.values(agent.skills || {}).filter(s => s.author_id === agent.id || s.name === 'crear_app' || s.name === 'ejecutar_codigo');

    return (
        <div className="p-6 space-y-8">
            {/* Apps */}
            <section className="space-y-4">
                <div className="flex items-center justify-between mb-4">
                    <h3 className="text-sm font-black text-white uppercase tracking-[0.2em] flex items-center gap-2">
                        <Terminal className="w-4 h-4 text-indigo-400" />
                        Aplicaciones ({apps.length})
                    </h3>
                </div>
                
                {apps.length === 0 ? (
                    <div className="bg-white/[0.02] border border-white/5 rounded-2xl p-8 flex flex-col items-center justify-center text-center">
                        <Code className="w-8 h-8 text-gray-700 mb-3" />
                        <p className="text-xs text-gray-500 italic">Este agente aún no ha creado aplicaciones persistentes.</p>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 gap-3">
                        {apps.map((app, i) => (
                            <div key={i} className="group relative bg-white/[0.03] hover:bg-white/[0.06] border border-white/5 hover:border-indigo-500/30 rounded-2xl p-4 transition-all overflow-hidden">
                                <div className="absolute top-0 right-0 p-3 opacity-0 group-hover:opacity-100 transition-opacity">
                                    <button 
                                        onClick={() => onRunApp(app)}
                                        className="p-2 bg-indigo-500 hover:bg-indigo-400 text-white rounded-xl shadow-lg shadow-indigo-500/20 transition-all active:scale-95"
                                    >
                                        <Play className="w-4 h-4" />
                                    </button>
                                </div>
                                <div className="flex flex-col gap-1">
                                    <h4 className="text-sm font-bold text-white group-hover:text-indigo-400 transition-colors">{app.name}</h4>
                                    <p className="text-[10px] text-gray-500 font-mono truncate max-w-[200px]">{app.file_path || `${app.name}.py`}</p>
                                    <div className="flex items-center gap-2 mt-2">
                                        <span className="text-[9px] px-2 py-0.5 bg-indigo-500/10 text-indigo-400 rounded-full border border-indigo-500/20">Python 3.11</span>
                                        <span className="text-[9px] text-gray-600">{new Date(app.created_at).toLocaleDateString()}</span>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </section>

            {/* Habilidades Personalizadas */}
            <section className="space-y-4">
                <div className="flex items-center justify-between mb-4">
                    <h3 className="text-sm font-black text-white uppercase tracking-[0.2em] flex items-center gap-2">
                        <Brain className="w-4 h-4 text-[#00e676]" />
                        Skills Evolutivas ({skills.length})
                    </h3>
                </div>

                <div className="grid grid-cols-1 gap-3">
                    {skills.map((skill, i) => (
                        <div key={i} className="group relative bg-white/[0.03] hover:bg-white/[0.06] border border-white/5 hover:border-[#00e676]/30 rounded-2xl p-4 transition-all overflow-hidden">
                            <div className="absolute top-0 right-0 p-3 opacity-0 group-hover:opacity-100 transition-opacity">
                                <button 
                                    onClick={() => onRunSkill(skill)}
                                    className="p-2 bg-[#00e676] hover:bg-[#00e676]/80 text-black rounded-xl shadow-lg shadow-[#00e676]/20 transition-all active:scale-95"
                                >
                                    <Play className="w-4 h-4" />
                                </button>
                            </div>
                            <div className="flex flex-col gap-1">
                                <h4 className="text-sm font-bold text-white group-hover:text-[#00e676] transition-colors">{skill.name}</h4>
                                <p className="text-[10px] text-gray-500 leading-relaxed">{skill.description}</p>
                                <div className="flex items-center gap-2 mt-2">
                                    <span className="text-[9px] px-2 py-0.5 bg-[#00e676]/10 text-[#00e676] rounded-full border border-[#00e676]/20">Cognitiva</span>
                                    {skill.author_id === agent.id && <span className="text-[9px] text-indigo-400 font-bold tracking-widest uppercase">Autoría Propia</span>}
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            </section>
        </div>
    );
}

// --- App Execution Modal (Sandbox Dialog) ---
function AppExecutionModal({ app, skill, agentId, userId, onClose }: { app: any, skill: any, agentId: string, userId: string | null, onClose: () => void }) {
    const { sendGodAction } = useGameStore();
    const [status, setStatus] = useState<'idle' | 'executing' | 'success' | 'error'>('idle');
    const [result, setResult] = useState<any>(null);
    const [stdout, setStdout] = useState<string>("");

    const isSkill = !!skill;
    const target = isSkill ? skill : app;

    const handleExecute = async () => {
        setStatus('executing');
        setResult(null);
        setStdout("");
        
        try {
            const actionType = isSkill ? "EXECUTE_SKILL" : "EXECUTE_APP";
            const params = isSkill ? {
                agent_id: agentId,
                skill_name: skill.name,
                argumentos: {} // Por ahora argumentos vacíos desde el botón rápido
            } : {
                agent_id: agentId,
                app_name: app.name
            };

            const targetUser = userId || 'arquitecto';
            const res = await fetch(getHttpUrl(`/game/god-mode/${targetUser}`), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action_type: actionType, params })
            });

            if (res.ok) {
                const data = await res.json();
                const resData = data.resultado?.resultado || data.resultado;
                
                if (typeof resData === 'object' && resData !== null) {
                    setResult(resData);
                    if (resData._stdout) setStdout(resData._stdout);
                } else {
                    setResult(resData);
                }
                setStatus('success');
            } else {
                const err = await res.json();
                setResult(err.detail || "Error desconocido");
                setStatus('error');
            }
        } catch (e) {
            setResult(String(e));
            setStatus('error');
        }
    };

    if (!app && !skill) return null;

    return (
        <AnimatePresence>
            <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
                <motion.div 
                    initial={{ opacity: 0 }} 
                    animate={{ opacity: 1 }} 
                    exit={{ opacity: 0 }}
                    onClick={onClose}
                    className="absolute inset-0 bg-black/80 backdrop-blur-md"
                />
                
                <motion.div
                    initial={{ scale: 0.9, opacity: 0, y: 20 }}
                    animate={{ scale: 1, opacity: 1, y: 0 }}
                    exit={{ scale: 0.9, opacity: 0, y: 20 }}
                    className="relative w-full max-w-2xl bg-[#0a0b10] border border-white/10 rounded-3xl shadow-2xl overflow-hidden flex flex-col max-h-[80vh]"
                >
                    {/* Header */}
                    <div className="p-6 border-b border-white/5 flex items-center justify-between bg-gradient-to-r from-indigo-500/10 to-transparent">
                        <div className="flex items-center gap-4">
                            <div className={`p-3 rounded-2xl ${isSkill ? 'bg-[#00e676]/20' : 'bg-indigo-500/20'}`}>
                                {isSkill ? <Brain className="w-6 h-6 text-[#00e676]" /> : <Terminal className="w-6 h-6 text-indigo-400" />}
                            </div>
                            <div>
                                <h3 className="text-xl font-black text-white uppercase tracking-tighter">
                                    {isSkill ? 'Ejecutar Skill' : 'Ejecutar App'}
                                </h3>
                                <p className="text-xs text-gray-500 font-mono">{target.name}</p>
                            </div>
                        </div>
                        <button onClick={onClose} className="p-2 hover:bg-white/5 rounded-full transition-colors">
                            <X className="w-5 h-5 text-gray-500" />
                        </button>
                    </div>

                    {/* Body */}
                    <div className="flex-1 overflow-y-auto p-6 custom-scrollbar">
                        {status === 'idle' && (
                            <div className="space-y-6">
                                <div className="bg-white/[0.02] border border-white/5 rounded-2xl p-6">
                                    <h4 className="text-xs font-bold text-gray-500 uppercase tracking-widest mb-4">Código Fuente</h4>
                                    <pre className="text-[11px] font-mono text-indigo-300/80 leading-relaxed overflow-x-auto p-4 bg-black/40 rounded-xl border border-white/5">
                                        {target.code}
                                    </pre>
                                </div>
                                <button 
                                    onClick={handleExecute}
                                    className="w-full py-4 bg-indigo-500 hover:bg-indigo-400 text-white font-black uppercase tracking-[0.2em] rounded-2xl shadow-xl shadow-indigo-500/20 transition-all active:scale-[0.98] flex items-center justify-center gap-3"
                                >
                                    <Play className="w-5 h-5 fill-current" />
                                    Iniciar Ejecución
                                </button>
                            </div>
                        )}

                        {status === 'executing' && (
                            <div className="py-20 flex flex-col items-center justify-center space-y-4">
                                <div className="w-12 h-12 border-4 border-indigo-500/20 border-t-indigo-500 rounded-full animate-spin" />
                                <p className="text-sm text-gray-400 animate-pulse font-mono">Invocando sandbox en el backend...</p>
                            </div>
                        )}

                        {(status === 'success' || status === 'error') && (
                            <div className="space-y-6">
                                {/* GUI Area if result is GUI */}
                                {result && result.type === 'gui' && result.html && (
                                    <div className="bg-white rounded-2xl overflow-hidden border-4 border-white/10 shadow-2xl">
                                        <div className="bg-gray-100 p-2 border-b flex items-center gap-2">
                                            <div className="flex gap-1">
                                                <div className="w-2 h-2 rounded-full bg-red-400" />
                                                <div className="w-2 h-2 rounded-full bg-yellow-400" />
                                                <div className="w-2 h-2 rounded-full bg-green-400" />
                                            </div>
                                            <span className="text-[10px] text-gray-400 font-bold uppercase tracking-widest">{target.name} UI</span>
                                        </div>
                                        <iframe 
                                            srcDoc={result.html} 
                                            className="w-full h-[400px] border-none"
                                            sandbox="allow-scripts allow-forms allow-popups"
                                        />
                                    </div>
                                )}

                                {/* Console / Standard Result */}
                                <div className={`rounded-2xl border ${status === 'error' ? 'border-red-500/20 bg-red-500/5' : 'border-white/5 bg-black/40'} p-6`}>
                                    <div className="flex items-center justify-between mb-4">
                                        <h4 className="text-xs font-bold text-gray-500 uppercase tracking-widest flex items-center gap-2">
                                            <Terminal className="w-3 h-3" />
                                            Resultado de Ejecución
                                        </h4>
                                        <span className={`text-[10px] font-bold uppercase ${status === 'error' ? 'text-red-400' : 'text-[#00e676]'}`}>
                                            {status === 'error' ? 'Error' : 'Éxito'}
                                        </span>
                                    </div>
                                    <div className="text-xs font-mono text-gray-300 whitespace-pre-wrap leading-relaxed">
                                        {typeof result === 'object' ? JSON.stringify(result, null, 2) : result}
                                    </div>
                                </div>

                                {stdout && (
                                    <div className="bg-black border border-white/5 rounded-2xl p-6">
                                        <h4 className="text-xs font-bold text-gray-600 uppercase tracking-widest mb-4">Standard Output (Logs)</h4>
                                        <div className="text-[11px] font-mono text-gray-400 whitespace-pre-wrap">
                                            {stdout}
                                        </div>
                                    </div>
                                )}

                                <button 
                                    onClick={() => setStatus('idle')}
                                    className="w-full py-4 bg-white/5 hover:bg-white/10 text-white font-bold uppercase tracking-[0.2em] rounded-2xl transition-all"
                                >
                                    Reiniciar Sandbox
                                </button>
                            </div>
                        )}
                    </div>
                </motion.div>
            </div>
        </AnimatePresence>
    );
}


