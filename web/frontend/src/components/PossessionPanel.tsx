"use client";

import React, { useState } from "react";
import { 
    MessageSquare, Send, Move, Vote, Gavel, 
    Hand, Users, Construction, X, ChevronUp, 
    ChevronDown, ChevronLeft, ChevronRight,
    Users2, Globe, Ghost, Heart, Zap, Moon,
    Coffee, Compass, Crosshair, Book, Microscope,
    Shield, TrendingUp, Handshake
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import useGameStore from "@/store/useGameStore";
import { Agent } from "@/types/agent";

export default function PossessionPanel() {
    const { agents, agentePoseidoId, sendGodAction, userId, isConnected } = useGameStore();
    const agent = agents.find(a => a.id === agentePoseidoId);

    const [message, setMessage] = useState("");
    const [scope, setScope] = useState<'global' | 'group' | 'direct'>('global');
    const [targetAgentId, setTargetAgentId] = useState("");
    const [lawDescription, setLawDescription] = useState("");
    const [activeTab, setActiveTab] = useState<'chat' | 'vital' | 'social' | 'construction' | 'reglas' | 'move'>('chat');

    if (!agentePoseidoId || !agent) return null;

    const executeAction = async (action: string, payload: any = {}) => {
        await sendGodAction("AGENT_EXECUTE_ACTION", {
            agent_id: agentePoseidoId,
            action,
            payload
        });
    };

    const handleSendMessage = () => {
        if (!message.trim()) return;
        
        if (scope === 'global') {
            executeAction("decir", { mensaje: message, global_broadcast: true });
        } else if (scope === 'group') {
            executeAction("decir", { mensaje: message, para_grupo: true });
        } else {
            executeAction("decir", { mensaje: message, privado_para: targetAgentId });
        }
        setMessage("");
    };

    const moveAgent = (dx: number, dy: number) => {
        executeAction("mover", { x: agent.x + dx, y: agent.y + dy });
    };

    return (
        <motion.div 
            initial={{ y: 100, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: 100, opacity: 0 }}
            className="fixed bottom-2 sm:bottom-6 left-1/2 -translate-x-1/2 w-[95vw] sm:w-[600px] max-w-[95vw] z-[100]"
        >
            <div className="bg-[#0a0b10]/95 backdrop-blur-xl border border-yellow-500/30 rounded-3xl shadow-2xl shadow-yellow-500/10 overflow-hidden">
                {/* Header */}
                <div className="bg-yellow-500/10 border-b border-yellow-500/20 px-6 py-3 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="p-1.5 bg-yellow-500/20 rounded-lg text-yellow-500 animate-pulse">
                            <Ghost className="w-4 h-4" />
                        </div>
                        <span className="text-[10px] font-black uppercase tracking-[0.2em] text-yellow-500">
                            Interfaz de Posesión: Agente {agent.id.substring(0, 6)}
                        </span>
                    </div>
                    <div className="flex gap-1 overflow-x-auto custom-scrollbar-hide max-w-[calc(100vw-8rem)] sm:max-w-[350px]">
                        <TabBtn active={activeTab === 'chat'} icon={MessageSquare} label="Comms" onClick={() => setActiveTab('chat')} />
                        <TabBtn active={activeTab === 'vital'} icon={Heart} label="Vital" onClick={() => setActiveTab('vital')} />
                        <TabBtn active={activeTab === 'social'} icon={Users2} label="Social" onClick={() => setActiveTab('social')} />
                        <TabBtn active={activeTab === 'construction'} icon={Construction} label="Obras/Eco" onClick={() => setActiveTab('construction')} />
                        <TabBtn active={activeTab === 'reglas'} icon={Gavel} label="Reglas" onClick={() => setActiveTab('reglas')} />
                        <TabBtn active={activeTab === 'move'} icon={Move} label="Move" onClick={() => setActiveTab('move')} />
                    </div>
                </div>

                {/* Content */}
                <div className="p-4 sm:p-6 h-48 sm:h-64 overflow-y-auto custom-scrollbar">
                    <AnimatePresence mode="wait">
                        {activeTab === 'chat' && (
                            <motion.div 
                                key="chat"
                                initial={{ opacity: 0, x: 10 }}
                                animate={{ opacity: 1, x: 0 }}
                                exit={{ opacity: 0, x: -10 }}
                                className="space-y-4"
                            >
                                <div className="flex gap-2 p-1 bg-white/5 rounded-xl border border-white/5">
                                    <ScopeBtn active={scope === 'global'} icon={Globe} label="Global" onClick={() => setScope('global')} />
                                    <ScopeBtn active={scope === 'group'} icon={Users2} label="Grupo" onClick={() => setScope('group')} />
                                    <ScopeBtn active={scope === 'direct'} icon={MessageSquare} label="Susurro" onClick={() => setScope('direct')} />
                                </div>

                                {scope === 'direct' && (
                                    <input 
                                        type="text" 
                                        placeholder="ID del agente objetivo..."
                                        value={targetAgentId}
                                        onChange={(e) => setTargetAgentId(e.target.value)}
                                        className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-2 text-xs text-white focus:outline-none focus:border-yellow-500/50"
                                    />
                                )}

                                <div className="relative group">
                                    <textarea 
                                        value={message}
                                        onChange={(e) => setMessage(e.target.value)}
                                        placeholder={`Enviar mensaje ${scope}...`}
                                        className="w-full h-24 bg-black/40 border border-white/10 rounded-2xl p-4 text-sm text-white placeholder:text-gray-600 focus:outline-none focus:border-yellow-500/50 resize-none font-mono"
                                    />
                                    <button 
                                        onClick={handleSendMessage}
                                        disabled={!message.trim()}
                                        className="absolute bottom-3 right-3 p-3 bg-yellow-500 text-black rounded-xl hover:scale-105 active:scale-95 transition-all disabled:opacity-50"
                                    >
                                        <Send className="w-5 h-5" />
                                    </button>
                                </div>
                            </motion.div>
                        )}

                        {activeTab === 'vital' && (
                            <motion.div 
                                key="vital"
                                initial={{ opacity: 0, x: 10 }}
                                animate={{ opacity: 1, x: 0 }}
                                exit={{ opacity: 0, x: -10 }}
                                className="grid grid-cols-1 sm:grid-cols-2 gap-4"
                            >
                                <ActionCard icon={Coffee} title="Comer" desc="Consumir alimentos" onClick={() => executeAction("comer")} />
                                <ActionCard icon={Heart} title="Curarse" desc="Usar medicinas" onClick={() => executeAction("curarse")} />
                                <ActionCard icon={Moon} title="Descansar" desc="Reponer energías" onClick={() => executeAction("descansar")} />
                                <ActionCard icon={Compass} title="Explorar" desc="Buscar por la zona" onClick={() => executeAction("explorar")} />
                                <ActionCard icon={Book} title="Estudiar" desc="Aprender en Universidad" onClick={() => executeAction("estudiar")} />
                                <ActionCard icon={Microscope} title="Investigar" desc="Desarrollar teorías" onClick={() => executeAction("investigar")} />
                                <ActionCard icon={Hand} title="Recolectar" desc="Extraer del suelo" onClick={() => executeAction("recolectar")} />
                            </motion.div>
                        )}

                        {activeTab === 'social' && (
                            <motion.div 
                                key="social"
                                initial={{ opacity: 0, x: 10 }}
                                animate={{ opacity: 1, x: 0 }}
                                exit={{ opacity: 0, x: -10 }}
                                className="grid grid-cols-1 sm:grid-cols-2 gap-4"
                            >
                                <div className="col-span-2 flex flex-col gap-2 mb-2">
                                    <span className="text-[10px] text-gray-500 font-bold uppercase tracking-wider">Objetivo de Interacción</span>
                                    <input 
                                        type="text" 
                                        placeholder="ID de otro agente..."
                                        value={targetAgentId}
                                        onChange={(e) => setTargetAgentId(e.target.value)}
                                        className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-2 text-xs text-white focus:outline-none focus:border-yellow-500/50"
                                    />
                                </div>
                                <ActionCard 
                                    icon={MessageSquare} 
                                    title="Opinar" 
                                    desc="Hablar en Asamblea" 
                                    onClick={() => {
                                        const msg = prompt("Tu opinión para la asamblea:");
                                        if (msg) executeAction("opinar", { mensaje: msg });
                                    }}
                                />
                                <ActionCard 
                                    icon={Handshake} 
                                    title="Socializar" 
                                    desc="Mejorar relación" 
                                    onClick={() => {
                                        const target = targetAgentId || prompt("ID del agente:");
                                        if (target) executeAction("socializar", { otro_agente_id: target });
                                    }}
                                />
                                <ActionCard 
                                    icon={Crosshair} 
                                    title="Atacar" 
                                    desc="Iniciar combate" 
                                    onClick={() => {
                                        const target = targetAgentId || prompt("ID del agente a atacar:");
                                        if (target) executeAction("atacar", { otro_agente_id: target });
                                    }}
                                />
                                <ActionCard 
                                    icon={Users} 
                                    title="Alianza" 
                                    desc="Firmar pacto" 
                                    onClick={() => {
                                        const target = targetAgentId || prompt("ID del socio:");
                                        if (target) executeAction("formar_alianza", { otro_agente_id: target });
                                    }}
                                />
                            </motion.div>
                        )}

                        {activeTab === 'construction' && (
                            <motion.div 
                                key="construction"
                                initial={{ opacity: 0, x: 10 }}
                                animate={{ opacity: 1, x: 0 }}
                                exit={{ opacity: 0, x: -10 }}
                                className="grid grid-cols-1 sm:grid-cols-2 gap-4"
                            >
                                <ActionCard 
                                    icon={Construction} 
                                    title="Construir" 
                                    desc="Estructura (60 MC)" 
                                    onClick={() => {
                                        const type = prompt("Tipo (Granja, Hospital, Universidad, Mina, Mercado, Templo, Estación Recarga):", "Granja");
                                        if (type) executeAction("construir", { tipo: type });
                                    }}
                                />
                                <ActionCard 
                                    icon={TrendingUp} 
                                    title="Invertir" 
                                    desc="Mercado bursátil" 
                                    onClick={() => {
                                        const monto = prompt("Monto a invertir:", "10");
                                        if (monto) executeAction("invertir", { monto });
                                    }}
                                />
                                <ActionCard 
                                    icon={Shield} 
                                    title="Seguridad" 
                                    desc="Rango (25 MC)" 
                                    onClick={() => executeAction("mejorar_seguridad")}
                                />
                            </motion.div>
                        )}

                        {activeTab === 'reglas' && (
                            <motion.div 
                                key="reglas"
                                initial={{ opacity: 0, x: 10 }}
                                animate={{ opacity: 1, x: 0 }}
                                exit={{ opacity: 0, x: -10 }}
                                className="grid grid-cols-1 sm:grid-cols-2 gap-4"
                            >
                                <ActionCard 
                                    icon={Users2} 
                                    title="Fundar Grupo" 
                                    desc="Nueva facción" 
                                    onClick={() => {
                                        const name = prompt("Nombre:");
                                        const desc = prompt("Objetivo/Descripción:");
                                        if (name && desc) executeAction("fundar_grupo", { nombre: name, descripcion: desc });
                                    }}
                                />
                                <ActionCard 
                                    icon={Globe} 
                                    title="Institución" 
                                    desc="Fundar (100 MC)" 
                                    onClick={() => {
                                        const name = prompt("Nombre de la institución:");
                                        const type = prompt("Tipo (Ciencia, Salud, Seguridad, Economía, Arte):", "Ciencia");
                                        if (name && type) executeAction("fundar_institucion", { nombre: name, tipo: type });
                                    }}
                                />
                                <ActionCard 
                                    icon={Gavel} 
                                    title="Proponer Ley" 
                                    desc="Nuevo decreto" 
                                    onClick={() => {
                                        const tit = prompt("Título de la ley:");
                                        const desc = prompt("Descripción:");
                                        if (tit && desc) executeAction("proponer_ley", { titulo: tit, descripcion: desc, tipo: "LEY" });
                                    }}
                                />
                                <ActionCard 
                                    icon={Vote} 
                                    title="Votar" 
                                    desc="Participar en ley" 
                                    onClick={() => {
                                        const pId = prompt("ID de propuesta:");
                                        const v = prompt("Voto (si/no):", "si");
                                        if (pId && v) executeAction("votar", { propuesta_id: pId, voto: v });
                                    }}
                                />
                            </motion.div>
                        )}

                        {activeTab === 'move' && (
                            <motion.div 
                                key="move"
                                initial={{ opacity: 0, x: 10 }}
                                animate={{ opacity: 1, x: 0 }}
                                exit={{ opacity: 0, x: -10 }}
                                className="flex flex-col items-center justify-center h-full gap-4"
                            >
                                <div className="grid grid-cols-3 gap-1 sm:gap-2">
                                    <div />
                                    <MoveBtn icon={ChevronUp} onClick={() => moveAgent(0, -1)} />
                                    <div />
                                    <MoveBtn icon={ChevronLeft} onClick={() => moveAgent(-1, 0)} />
                                    <div className="flex items-center justify-center p-3 text-yellow-500/40 font-mono text-xs">
                                        ({agent.x}, {agent.y})
                                    </div>
                                    <MoveBtn icon={ChevronRight} onClick={() => moveAgent(1, 0)} />
                                    <div />
                                    <MoveBtn icon={ChevronDown} onClick={() => moveAgent(0, 1)} />
                                    <div />
                                </div>
                                <span className="text-[10px] text-gray-500 font-bold uppercase tracking-widest">
                                    Control de Locomoción
                                </span>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>
            </div>
        </motion.div>
    );
}

function TabBtn({ active, icon: Icon, label, onClick }: any) {
    return (
        <button 
            onClick={onClick}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg transition-all ${
                active ? 'bg-yellow-500 text-black' : 'text-gray-400 hover:text-white hover:bg-white/5'
            }`}
        >
            <Icon className="w-3.5 h-3.5" />
            <span className="text-[9px] font-bold uppercase tracking-wider">{label}</span>
        </button>
    );
}

function ScopeBtn({ active, icon: Icon, label, onClick }: any) {
    return (
        <button 
            onClick={onClick}
            className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-lg transition-all ${
                active ? 'bg-yellow-500/20 text-yellow-500 border border-yellow-500/30' : 'text-gray-500 hover:text-gray-300'
            }`}
        >
            <Icon className="w-3.5 h-3.5" />
            <span className="text-[9px] font-bold uppercase">{label}</span>
        </button>
    );
}

function MoveBtn({ icon: Icon, onClick }: any) {
    return (
        <button 
            onClick={onClick}
            className="p-4 bg-white/5 border border-white/10 rounded-2xl hover:bg-yellow-500/10 hover:border-yellow-500/30 group transition-all active:scale-95"
        >
            <Icon className="w-6 h-6 text-gray-400 group-hover:text-yellow-500 transition-colors" />
        </button>
    );
}

function ActionCard({ icon: Icon, title, desc, onClick }: any) {
    return (
        <button 
            onClick={onClick}
            className="flex items-start gap-4 p-4 bg-white/5 border border-white/10 rounded-2xl hover:bg-white/10 hover:border-white/20 transition-all text-left group active:scale-[0.98]"
        >
            <div className="p-3 bg-white/5 rounded-xl group-hover:bg-yellow-500/20 group-hover:text-yellow-500 transition-all">
                <Icon className="w-5 h-5" />
            </div>
            <div>
                <h4 className="text-xs font-bold text-white uppercase tracking-wider mb-1">{title}</h4>
                <p className="text-[10px] text-gray-500 leading-tight">{desc}</p>
            </div>
        </button>
    );
}
