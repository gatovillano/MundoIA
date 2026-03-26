"use client";

import React, { useState } from "react";
import { 
    MessageSquare, Send, Move, Vote, Gavel, 
    Hand, Users, Construction, X, ChevronUp, 
    ChevronDown, ChevronLeft, ChevronRight,
    Users2, Globe, Ghost
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
    const [activeTab, setActiveTab] = useState<'chat' | 'actions' | 'move'>('chat');

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
            className="fixed bottom-6 left-1/2 -translate-x-1/2 w-[600px] z-[100]"
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
                    <div className="flex gap-1">
                        <TabBtn active={activeTab === 'chat'} icon={MessageSquare} label="Comunicación" onClick={() => setActiveTab('chat')} />
                        <TabBtn active={activeTab === 'actions'} icon={Hand} label="Acciones" onClick={() => setActiveTab('actions')} />
                        <TabBtn active={activeTab === 'move'} icon={Move} label="Movimiento" onClick={() => setActiveTab('move')} />
                    </div>
                </div>

                {/* Content */}
                <div className="p-6 h-64 overflow-y-auto custom-scrollbar">
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

                        {activeTab === 'actions' && (
                            <motion.div 
                                key="actions"
                                initial={{ opacity: 0, x: 10 }}
                                animate={{ opacity: 1, x: 0 }}
                                exit={{ opacity: 0, x: -10 }}
                                className="grid grid-cols-2 gap-4"
                            >
                                <ActionCard 
                                    icon={Hand} 
                                    title="Recolectar" 
                                    desc="Extraer recursos del suelo" 
                                    onClick={() => executeAction("recolectar")}
                                />
                                <ActionCard 
                                    icon={Users} 
                                    title="Fundar Grupo" 
                                    desc="Crear una nueva facción" 
                                    onClick={() => {
                                        const name = prompt("Nombre de la nueva facción:");
                                        if (name) executeAction("fundar_grupo", { nombre: name });
                                    }}
                                />
                                <ActionCard 
                                    icon={Gavel} 
                                    title="Proponer Ley" 
                                    desc="Decretar una nueva regla" 
                                    onClick={() => {
                                        const desc = prompt("Descripción de la ley (texto):");
                                        if (desc) executeAction("proponer_ley", { texto: desc, tipo: "ley" });
                                    }}
                                />
                                <ActionCard 
                                    icon={Vote} 
                                    title="Votar" 
                                    desc="Participar en decisiones" 
                                    onClick={() => {
                                        const pId = prompt("ID de la propuesta:");
                                        const v = prompt("Voto (si/no):");
                                        if (pId && v) executeAction("votar", { propuesta_id: pId, voto: v });
                                    }}
                                />
                                <ActionCard 
                                    icon={Construction} 
                                    title="Construir" 
                                    desc="Levantar una estructura" 
                                    onClick={() => {
                                        const type = prompt("Edificio (Casa, Mercado, Templo, Hospital, Granja, Universidad, Mina, Farmacia):", "Casa");
                                        if (type) executeAction("construir", { tipo: type });
                                    }}
                                />
                                <ActionCard 
                                    icon={Users} 
                                    title="Socializar" 
                                    desc="Mejorar relación con otro" 
                                    onClick={() => {
                                        const target = targetAgentId || prompt("ID del agente objetivo:");
                                        if (target) executeAction("socializar", { otro_agente_id: target });
                                    }}
                                />
                                <ActionCard 
                                    icon={X} 
                                    title="Competir" 
                                    desc="Desafiar a otro agente" 
                                    onClick={() => {
                                        const target = targetAgentId || prompt("ID del agente objetivo:");
                                        if (target) executeAction("competir", { otro_agente_id: target });
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
                                <div className="grid grid-cols-3 gap-2">
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
