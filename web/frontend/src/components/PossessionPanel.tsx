"use client";

import React, { useState, useEffect } from "react";
import {
    MessageSquare, Send, Move, Vote, Gavel,
    Hand, Users, Construction, ChevronUp,
    ChevronDown, ChevronLeft, ChevronRight,
    Users2, Globe, Ghost, Heart,
    Coffee, Compass, Crosshair, Book, Microscope,
    Shield, TrendingUp, Handshake, Crown, Sparkles,
    Share2, Sprout, Flame, Building2, LogOut
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import useGameStore from "@/store/useGameStore";

export default function PossessionPanel() {
    const { agents, factions, institutions, agentePoseidoId, sendGodAction, selectAgent } = useGameStore();
    const agent = agents.find((a) => a.id === agentePoseidoId);

    const [activeTab, setActiveTab] = useState<'move' | 'chat' | 'vital' | 'social' | 'construction' | 'reglas'>('move');
    const [message, setMessage] = useState("");
    const [scope, setScope] = useState<'global' | 'group' | 'direct' | 'social_post'>('global');
    const [targetAgentId, setTargetAgentId] = useState("");
    const [buildingType, setBuildingType] = useState("Granja");
    const [investAmount, setInvestAmount] = useState("25");
    const [groupName, setGroupName] = useState("");
    const [groupDesc, setGroupDesc] = useState("");
    const [joinGroupId, setJoinGroupId] = useState("");
    const [instName, setInstName] = useState("");
    const [instType, setInstType] = useState("Ciencia");
    const [selectedInstId, setSelectedInstId] = useState("");
    const [lawTitle, setLawTitle] = useState("");
    const [lawContent, setLawContent] = useState("");
    const [opinionScore, setOpinionScore] = useState("0.5");

    const isPlayerAvatar = Boolean(
        agent && ((agent as any).is_player_avatar || String(agent.id || "").startsWith("av_"))
    );

    const executeAction = async (action: string, payload: any = {}) => {
        if (!agentePoseidoId) return;
        await sendGodAction("AGENT_EXECUTE_ACTION", {
            agent_id: agentePoseidoId,
            action,
            payload,
        });
    };

    const moveAgent = (dx: number, dy: number) => {
        if (!agent) return;
        executeAction("mover", { x: agent.x + dx, y: agent.y + dy });
    };

    // Soporte de movimiento con teclado (WASD / Flechas) cuando no se está escribiendo en un input
    useEffect(() => {
        if (!agentePoseidoId || !agent) return;
        const handleKeyDown = (e: KeyboardEvent) => {
            const tag = (e.target as HTMLElement)?.tagName?.toLowerCase();
            if (tag === "input" || tag === "textarea" || tag === "select" || (e.target as HTMLElement)?.isContentEditable) {
                return;
            }
            if (e.key === "ArrowUp" || e.key === "w" || e.key === "W") {
                e.preventDefault();
                moveAgent(0, -1);
            } else if (e.key === "ArrowDown" || e.key === "s" || e.key === "S") {
                e.preventDefault();
                moveAgent(0, 1);
            } else if (e.key === "ArrowLeft" || e.key === "a" || e.key === "A") {
                e.preventDefault();
                moveAgent(-1, 0);
            } else if (e.key === "ArrowRight" || e.key === "d" || e.key === "D") {
                e.preventDefault();
                moveAgent(1, 0);
            }
        };
        window.addEventListener("keydown", handleKeyDown);
        return () => window.removeEventListener("keydown", handleKeyDown);
    }, [agentePoseidoId, agent?.x, agent?.y]);

    if (!agentePoseidoId || !agent) return null;

    const agentDisplayName = agent.identidad?.nombre || agent.alma?.nombre_propio || agent.id;
    const otherAgents = agents.filter((a) => a.id !== agent.id);
    const factionList = Object.entries(factions || {});
    const instList = Object.entries(institutions || {});

    const handleSendMessage = () => {
        if (!message.trim()) return;
        if (scope === "social_post") {
            executeAction("social_post", { contenido: message.trim() });
        } else if (scope === "global") {
            executeAction("decir", { mensaje: message.trim(), global_broadcast: true });
        } else if (scope === "group") {
            executeAction("decir", { mensaje: message.trim(), para_grupo: true });
        } else {
            executeAction("decir", { mensaje: message.trim(), privado_para: targetAgentId });
        }
        setMessage("");
    };

    return (
        <motion.div
            initial={{ y: 100, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: 100, opacity: 0 }}
            className="fixed bottom-2 sm:bottom-5 left-1/2 -translate-x-1/2 w-[96vw] sm:w-[680px] max-w-[96vw] z-[100]"
        >
            <div className="bg-[#0a0b10]/95 backdrop-blur-xl border border-emerald-500/35 rounded-3xl shadow-2xl shadow-emerald-500/10 overflow-hidden">
                {/* Header con estado del Avatar / Agente */}
                <div className="bg-gradient-to-r from-emerald-500/15 via-yellow-500/10 to-transparent border-b border-white/10 px-4 sm:px-6 py-2.5 flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2.5">
                        <button
                            onClick={() => selectAgent(agent.id)}
                            className="p-1.5 bg-emerald-500/20 border border-emerald-500/40 rounded-xl text-emerald-400 hover:bg-emerald-500/30 transition-all"
                            title="Centrar en mi Avatar"
                        >
                            {isPlayerAvatar ? <Crown className="w-4 h-4 text-yellow-400" /> : <Ghost className="w-4 h-4" />}
                        </button>
                        <div>
                            <div className="flex items-center gap-2">
                                <span className="text-xs font-black tracking-wide text-white">
                                    {isPlayerAvatar ? `👑 ${agentDisplayName}` : `⚡ ${agentDisplayName}`}
                                </span>
                                <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 uppercase">
                                    {isPlayerAvatar ? "Tu Avatar" : "Poseído"}
                                </span>
                            </div>
                            <div className="flex items-center gap-3 text-[10px] font-mono text-gray-400 mt-0.5">
                                <span>📍({agent.x},{agent.y})</span>
                                <span>❤️ {(agent.necesidades?.salud ?? 10).toFixed(1)}</span>
                                <span>🍖 {(agent.necesidades?.alimento ?? 10).toFixed(1)}</span>
                                <span>💤 {(agent.necesidades?.descanso ?? 10).toFixed(1)}</span>
                                <span className="text-yellow-400">💰 {Number(agent.dinero ?? 0).toFixed(0)} MC</span>
                                <span className="text-emerald-400">📦 {Number(agent.recursos ?? 0).toFixed(0)}</span>
                            </div>
                        </div>
                    </div>

                    <div className="flex items-center gap-1 overflow-x-auto custom-scrollbar-hide">
                        <TabBtn active={activeTab === 'move'} icon={Move} label="Mover" onClick={() => setActiveTab('move')} />
                        <TabBtn active={activeTab === 'vital'} icon={Heart} label="Vital/Saberes" onClick={() => setActiveTab('vital')} />
                        <TabBtn active={activeTab === 'chat'} icon={MessageSquare} label="Voz/Red" onClick={() => setActiveTab('chat')} />
                        <TabBtn active={activeTab === 'social'} icon={Users2} label="Social/Lucha" onClick={() => setActiveTab('social')} />
                        <TabBtn active={activeTab === 'construction'} icon={Construction} label="Obras/Eco" onClick={() => setActiveTab('construction')} />
                        <TabBtn active={activeTab === 'reglas'} icon={Gavel} label="Política" onClick={() => setActiveTab('reglas')} />
                    </div>
                </div>

                {/* Content */}
                <div className="p-4 sm:p-5 h-56 sm:h-64 overflow-y-auto custom-scrollbar">
                    <AnimatePresence mode="wait">
                        {activeTab === 'move' && (
                            <motion.div
                                key="move"
                                initial={{ opacity: 0, x: 10 }}
                                animate={{ opacity: 1, x: 0 }}
                                exit={{ opacity: 0, x: -10 }}
                                className="flex flex-col sm:flex-row items-center justify-between h-full gap-4"
                            >
                                <div className="flex flex-col items-center justify-center flex-1">
                                    <div className="grid grid-cols-3 gap-1.5">
                                        <MoveBtn label="↖" onClick={() => moveAgent(-1, -1)} />
                                        <MoveBtn icon={ChevronUp} onClick={() => moveAgent(0, -1)} />
                                        <MoveBtn label="↗" onClick={() => moveAgent(1, -1)} />
                                        <MoveBtn icon={ChevronLeft} onClick={() => moveAgent(-1, 0)} />
                                        <div className="flex flex-col items-center justify-center px-3 py-2 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-emerald-300 font-mono text-xs font-bold">
                                            <span>({agent.x}, {agent.y})</span>
                                            <span className="text-[8px] text-gray-400 uppercase">WASD</span>
                                        </div>
                                        <MoveBtn icon={ChevronRight} onClick={() => moveAgent(1, 0)} />
                                        <MoveBtn label="↙" onClick={() => moveAgent(-1, 1)} />
                                        <MoveBtn icon={ChevronDown} onClick={() => moveAgent(0, 1)} />
                                        <MoveBtn label="↘" onClick={() => moveAgent(1, 1)} />
                                    </div>
                                </div>

                                <div className="flex-1 grid grid-cols-2 gap-2 w-full">
                                    <ActionCard icon={Compass} title="Explorar" desc="Explorar casilla" onClick={() => executeAction("explorar")} />
                                    <ActionCard icon={Hand} title="Recolectar" desc="Extraer recursos" onClick={() => executeAction("recolectar")} />
                                    <ActionCard icon={Sprout} title="Cultivar" desc="Sembrar alimento" onClick={() => executeAction("cultivar")} />
                                    <ActionCard icon={Coffee} title="Comer" desc="Recuperar energía" onClick={() => executeAction("comer")} />
                                </div>
                            </motion.div>
                        )}

                        {activeTab === 'vital' && (
                            <motion.div
                                key="vital"
                                initial={{ opacity: 0, x: 10 }}
                                animate={{ opacity: 1, x: 0 }}
                                exit={{ opacity: 0, x: -10 }}
                                className="grid grid-cols-2 sm:grid-cols-3 gap-2.5"
                            >
                                <ActionCard icon={Coffee} title="Comer" desc="Consumir alimento" onClick={() => executeAction("comer")} />
                                <ActionCard icon={Heart} title="Curarse" desc="Sanar (+2 salud)" onClick={() => executeAction("curarse")} />
                                <ActionCard icon={Sparkles} title="Descansar" desc="Reponer energías" onClick={() => executeAction("descansar")} />
                                <ActionCard icon={Hand} title="Recolectar" desc="Extraer del terreno" onClick={() => executeAction("recolectar")} />
                                <ActionCard icon={Sprout} title="Cultivar" desc="Producir comida" onClick={() => executeAction("cultivar")} />
                                <ActionCard icon={Flame} title="Cazar" desc="Buscar sustento" onClick={() => executeAction("cazar")} />
                                <ActionCard icon={Compass} title="Explorar" desc="Reconocer región" onClick={() => executeAction("explorar")} />
                                <ActionCard icon={Book} title="Estudiar" desc="Ganar sabiduría" onClick={() => executeAction("estudiar")} />
                                <ActionCard icon={Microscope} title="Investigar" desc="Ciencia y tecnología" onClick={() => executeAction("investigar")} />
                                <ActionCard icon={Sparkles} title="Reflexionar" desc="Evolución espiritual" onClick={() => executeAction("reflexionar")} />
                                <ActionCard icon={Construction} title="Forjar Skill" desc="Crear herramienta" onClick={() => executeAction("skill_factory")} />
                            </motion.div>
                        )}

                        {activeTab === 'chat' && (
                            <motion.div
                                key="chat"
                                initial={{ opacity: 0, x: 10 }}
                                animate={{ opacity: 1, x: 0 }}
                                exit={{ opacity: 0, x: -10 }}
                                className="space-y-3"
                            >
                                <div className="flex gap-1.5 p-1 bg-white/5 rounded-xl border border-white/5">
                                    <ScopeBtn active={scope === 'global'} icon={Globe} label="Global" onClick={() => setScope('global')} />
                                    <ScopeBtn active={scope === 'group'} icon={Users2} label="Facción" onClick={() => setScope('group')} />
                                    <ScopeBtn active={scope === 'direct'} icon={MessageSquare} label="Susurro" onClick={() => setScope('direct')} />
                                    <ScopeBtn active={scope === 'social_post'} icon={Share2} label="Red Social" onClick={() => setScope('social_post')} />
                                </div>

                                {scope === 'direct' && (
                                    <select
                                        value={targetAgentId}
                                        onChange={(e) => setTargetAgentId(e.target.value)}
                                        className="w-full bg-black/60 border border-white/15 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-emerald-500/50"
                                    >
                                        <option value="">Selecciona destinatario del susurro...</option>
                                        {otherAgents.map((a) => (
                                            <option key={a.id} value={a.id}>
                                                {a.identidad?.nombre || a.id} ({a.id}) - ({a.x},{a.y})
                                            </option>
                                        ))}
                                    </select>
                                )}

                                <div className="relative">
                                    <textarea
                                        value={message}
                                        onChange={(e) => setMessage(e.target.value)}
                                        onKeyDown={(e) => {
                                            if (e.key === "Enter" && !e.shiftKey) {
                                                e.preventDefault();
                                                handleSendMessage();
                                            }
                                        }}
                                        placeholder={
                                            scope === "social_post"
                                                ? "Publicar post en la red social del mundo..."
                                                : `Hablar como ${agentDisplayName} (${scope})...`
                                        }
                                        className="w-full h-24 bg-black/40 border border-white/10 rounded-2xl p-3.5 pr-14 text-xs text-white placeholder:text-gray-500 focus:outline-none focus:border-emerald-500/50 resize-none font-mono"
                                    />
                                    <button
                                        onClick={handleSendMessage}
                                        disabled={!message.trim() || (scope === "direct" && !targetAgentId)}
                                        className="absolute bottom-3 right-3 p-2.5 bg-emerald-500 text-black rounded-xl hover:bg-emerald-400 transition-all disabled:opacity-40"
                                    >
                                        <Send className="w-4 h-4" />
                                    </button>
                                </div>
                            </motion.div>
                        )}

                        {activeTab === 'social' && (
                            <motion.div
                                key="social"
                                initial={{ opacity: 0, x: 10 }}
                                animate={{ opacity: 1, x: 0 }}
                                exit={{ opacity: 0, x: -10 }}
                                className="space-y-3"
                            >
                                <div className="flex flex-col sm:flex-row gap-2">
                                    <select
                                        value={targetAgentId}
                                        onChange={(e) => setTargetAgentId(e.target.value)}
                                        className="flex-1 bg-black/60 border border-white/15 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-emerald-500/50"
                                    >
                                        <option value="">Agente más cercano (o elige objetivo)...</option>
                                        {otherAgents.map((a) => (
                                            <option key={a.id} value={a.id}>
                                                {(a as any).is_player_avatar ? "👑 " : ""}{a.identidad?.nombre || a.id} ({a.id}) — 📍({a.x},{a.y})
                                            </option>
                                        ))}
                                    </select>

                                    <div className="flex items-center gap-1.5 bg-white/5 border border-white/10 rounded-xl px-2.5 py-1">
                                        <span className="text-[10px] text-gray-400 font-mono">Afinidad:</span>
                                        <input
                                            type="number"
                                            min="-1"
                                            max="1"
                                            step="0.2"
                                            value={opinionScore}
                                            onChange={(e) => setOpinionScore(e.target.value)}
                                            className="w-14 bg-black/50 border border-white/10 rounded px-1.5 py-1 text-xs text-white font-mono"
                                        />
                                        <button
                                            onClick={() => targetAgentId && executeAction("opinar", { target_id: targetAgentId, opinion: parseFloat(opinionScore) })}
                                            disabled={!targetAgentId}
                                            className="px-2 py-1 bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 rounded text-[10px] font-bold uppercase disabled:opacity-40"
                                        >
                                            Juzgar
                                        </button>
                                    </div>
                                </div>

                                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
                                    <ActionCard
                                        icon={Handshake}
                                        title="Socializar"
                                        desc="Charlar y ganar vínculo"
                                        onClick={() => executeAction("socializar", targetAgentId ? { target_id: targetAgentId } : {})}
                                    />
                                    <ActionCard
                                        icon={Users}
                                        title="Formar Alianza"
                                        desc="Sellar pacto"
                                        onClick={() => executeAction("formar_alianza", targetAgentId ? { target_id: targetAgentId } : {})}
                                    />
                                    <ActionCard
                                        icon={TrendingUp}
                                        title="Comerciar"
                                        desc="Intercambiar recursos"
                                        onClick={() => executeAction("comerciar", targetAgentId ? { target_id: targetAgentId } : {})}
                                    />
                                    <ActionCard
                                        icon={Crosshair}
                                        title="Atacar"
                                        desc="Combate directo"
                                        onClick={() => executeAction("atacar", targetAgentId ? { target_id: targetAgentId } : {})}
                                    />
                                    <ActionCard
                                        icon={Share2}
                                        title="Dar Like Social"
                                        desc="Interactuar en red"
                                        onClick={() => executeAction("social_like", {})}
                                    />
                                    <ActionCard
                                        icon={Heart}
                                        title="Negociar Paz"
                                        desc="Reconciliar conflicto"
                                        onClick={() => executeAction("negociar_paz", targetAgentId ? { target_id: targetAgentId } : {})}
                                    />
                                </div>
                            </motion.div>
                        )}

                        {activeTab === 'construction' && (
                            <motion.div
                                key="construction"
                                initial={{ opacity: 0, x: 10 }}
                                animate={{ opacity: 1, x: 0 }}
                                exit={{ opacity: 0, x: -10 }}
                                className="space-y-3"
                            >
                                <div className="flex flex-col sm:flex-row gap-2 bg-white/5 p-3 rounded-2xl border border-white/10">
                                    <select
                                        value={buildingType}
                                        onChange={(e) => setBuildingType(e.target.value)}
                                        className="flex-1 bg-black/60 border border-white/15 rounded-xl px-3 py-2 text-xs text-white"
                                    >
                                        <option value="Granja">🌾 Granja (Alimentos)</option>
                                        <option value="Centro de Descanso">🛏️ Centro de Descanso</option>
                                        <option value="Centro Comunitario">🏛️ Centro Comunitario</option>
                                        <option value="Hospital">🏥 Hospital (Salud)</option>
                                        <option value="Universidad">🎓 Universidad (Sabiduría)</option>
                                        <option value="Mina">⛏️ Mina (Recursos)</option>
                                        <option value="Mercado">⚖️ Mercado (Comercio)</option>
                                        <option value="Templo">⛩️ Templo (Espiritualidad)</option>
                                    </select>
                                    <button
                                        onClick={() => executeAction("construir", { tipo: buildingType })}
                                        className="px-4 py-2 bg-emerald-500 hover:bg-emerald-400 text-black font-bold text-xs rounded-xl uppercase tracking-wider transition-all"
                                    >
                                        Construir Aquí
                                    </button>
                                </div>

                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                                    <div className="flex items-center justify-between gap-2 p-3 bg-white/5 border border-white/10 rounded-2xl">
                                        <div>
                                            <h4 className="text-xs font-bold text-white uppercase">Invertir MC</h4>
                                            <p className="text-[10px] text-gray-400">Retorno en 5 turnos</p>
                                        </div>
                                        <div className="flex items-center gap-1.5">
                                            <input
                                                type="number"
                                                min="5"
                                                max="200"
                                                value={investAmount}
                                                onChange={(e) => setInvestAmount(e.target.value)}
                                                className="w-16 bg-black/60 border border-white/15 rounded-lg px-2 py-1 text-xs text-white font-mono"
                                            />
                                            <button
                                                onClick={() => executeAction("invertir", { monto: parseFloat(investAmount) || 20 })}
                                                className="px-3 py-1.5 bg-yellow-500/20 hover:bg-yellow-500/30 text-yellow-300 border border-yellow-500/30 rounded-lg text-[10px] font-bold uppercase"
                                            >
                                                Invertir
                                            </button>
                                        </div>
                                    </div>

                                    <ActionCard
                                        icon={Shield}
                                        title="Mejorar Seguridad"
                                        desc="Aumentar rango y defensa (25 MC)"
                                        onClick={() => executeAction("mejorar_seguridad")}
                                    />
                                </div>
                            </motion.div>
                        )}

                        {activeTab === 'reglas' && (
                            <motion.div
                                key="reglas"
                                initial={{ opacity: 0, x: 10 }}
                                animate={{ opacity: 1, x: 0 }}
                                exit={{ opacity: 0, x: -10 }}
                                className="space-y-3"
                            >
                                {/* Facciones y Asentamientos */}
                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                                    <div className="p-3 bg-white/5 border border-white/10 rounded-2xl space-y-2">
                                        <div className="text-[10px] font-bold uppercase text-emerald-400">Fundar Nueva Facción</div>
                                        <input
                                            type="text"
                                            placeholder="Nombre de la facción..."
                                            value={groupName}
                                            onChange={(e) => setGroupName(e.target.value)}
                                            className="w-full bg-black/50 border border-white/10 rounded-lg px-2.5 py-1.5 text-xs text-white"
                                        />
                                        <div className="flex gap-1.5">
                                            <input
                                                type="text"
                                                placeholder="Lema o propósito..."
                                                value={groupDesc}
                                                onChange={(e) => setGroupDesc(e.target.value)}
                                                className="flex-1 bg-black/50 border border-white/10 rounded-lg px-2.5 py-1.5 text-xs text-white"
                                            />
                                            <button
                                                onClick={() => {
                                                    executeAction("fundar_grupo", {
                                                        nombre: groupName || undefined,
                                                        descripcion: groupDesc || undefined,
                                                    });
                                                    setGroupName("");
                                                    setGroupDesc("");
                                                }}
                                                className="px-3 py-1.5 bg-emerald-500 text-black font-bold text-[10px] rounded-lg uppercase"
                                            >
                                                Fundar
                                            </button>
                                        </div>
                                    </div>

                                    <div className="p-3 bg-white/5 border border-white/10 rounded-2xl space-y-2">
                                        <div className="text-[10px] font-bold uppercase text-blue-400">Facciones y Pueblos</div>
                                        <div className="flex gap-1.5">
                                            <select
                                                value={joinGroupId}
                                                onChange={(e) => setJoinGroupId(e.target.value)}
                                                className="flex-1 bg-black/50 border border-white/10 rounded-lg px-2 py-1.5 text-xs text-white"
                                            >
                                                <option value="">Facción cercana...</option>
                                                {factionList.map(([fid, f]: [string, any]) => (
                                                    <option key={fid} value={fid}>{f.nombre || fid}</option>
                                                ))}
                                            </select>
                                            <button
                                                onClick={() => executeAction("unirse_grupo", joinGroupId ? { grupo_id: joinGroupId } : {})}
                                                className="px-2.5 py-1.5 bg-blue-500/20 text-blue-300 border border-blue-500/30 rounded-lg text-[10px] font-bold uppercase"
                                            >
                                                Unirse
                                            </button>
                                        </div>
                                        <div className="flex gap-1.5">
                                            <button
                                                onClick={() => executeAction("fundar_pueblo")}
                                                className="flex-1 py-1.5 bg-yellow-500/20 text-yellow-300 border border-yellow-500/30 rounded-lg text-[10px] font-bold uppercase"
                                            >
                                                🏘️ Fundar Pueblo
                                            </button>
                                            {agent.grupo_id && (
                                                <button
                                                    onClick={() => executeAction("abandonar_grupo")}
                                                    className="px-2.5 py-1.5 bg-red-500/20 text-red-300 border border-red-500/30 rounded-lg text-[10px] font-bold uppercase"
                                                    title="Abandonar facción actual"
                                                >
                                                    <LogOut className="w-3.5 h-3.5" />
                                                </button>
                                            )}
                                        </div>
                                    </div>
                                </div>

                                {/* Instituciones y Leyes */}
                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                                    <div className="p-3 bg-white/5 border border-white/10 rounded-2xl space-y-2">
                                        <div className="text-[10px] font-bold uppercase text-purple-400">Instituciones</div>
                                        <div className="flex gap-1.5">
                                            <input
                                                type="text"
                                                placeholder="Nombre institución..."
                                                value={instName}
                                                onChange={(e) => setInstName(e.target.value)}
                                                className="flex-1 bg-black/50 border border-white/10 rounded-lg px-2 py-1 text-xs text-white"
                                            />
                                            <select
                                                value={instType}
                                                onChange={(e) => setInstType(e.target.value)}
                                                className="bg-black/50 border border-white/10 rounded-lg px-2 py-1 text-xs text-white"
                                            >
                                                <option value="Hospital">Hospital</option>
                                                <option value="Universidad">Universidad</option>
                                                <option value="Banco">Banco</option>
                                                <option value="Seguridad">Seguridad</option>
                                            </select>
                                            <button
                                                onClick={() => {
                                                    if (!instName.trim()) return;
                                                    executeAction("fundar_institucion", { nombre: instName.trim(), tipo: instType });
                                                    setInstName("");
                                                }}
                                                className="px-2.5 py-1 bg-purple-500/30 text-purple-200 rounded-lg text-[10px] font-bold uppercase"
                                            >
                                                Crear
                                            </button>
                                        </div>
                                        {instList.length > 0 && (
                                            <div className="flex gap-1.5">
                                                <select
                                                    value={selectedInstId}
                                                    onChange={(e) => setSelectedInstId(e.target.value)}
                                                    className="flex-1 bg-black/50 border border-white/10 rounded-lg px-2 py-1 text-xs text-white"
                                                >
                                                    <option value="">En mi casilla / Elegir...</option>
                                                    {instList.map(([iid, inst]: [string, any]) => (
                                                        <option key={iid} value={iid}>{inst.nombre} ({inst.tipo})</option>
                                                    ))}
                                                </select>
                                                <button
                                                    onClick={() => executeAction("unirse_institucion", selectedInstId ? { institucion_id: selectedInstId } : {})}
                                                    className="px-2 py-1 bg-white/10 hover:bg-white/20 text-white rounded-lg text-[10px] font-bold uppercase"
                                                >
                                                    Unirse
                                                </button>
                                                <button
                                                    onClick={() => executeAction("usar_institucion", selectedInstId ? { institucion_id: selectedInstId } : {})}
                                                    className="px-2 py-1 bg-emerald-500/20 text-emerald-300 rounded-lg text-[10px] font-bold uppercase"
                                                >
                                                    Usar
                                                </button>
                                            </div>
                                        )}
                                    </div>

                                    <div className="p-3 bg-white/5 border border-white/10 rounded-2xl space-y-2">
                                        <div className="text-[10px] font-bold uppercase text-yellow-400">Leyes y Asamblea</div>
                                        <div className="flex gap-1.5">
                                            <input
                                                type="text"
                                                placeholder="Título de ley..."
                                                value={lawTitle}
                                                onChange={(e) => setLawTitle(e.target.value)}
                                                className="w-1/3 bg-black/50 border border-white/10 rounded-lg px-2 py-1 text-xs text-white"
                                            />
                                            <input
                                                type="text"
                                                placeholder="Contenido del decreto..."
                                                value={lawContent}
                                                onChange={(e) => setLawContent(e.target.value)}
                                                className="flex-1 bg-black/50 border border-white/10 rounded-lg px-2 py-1 text-xs text-white"
                                            />
                                            <button
                                                onClick={() => {
                                                    if (!lawTitle.trim() || !lawContent.trim()) return;
                                                    executeAction("proponer_ley", { titulo: lawTitle.trim(), contenido: lawContent.trim() });
                                                    setLawTitle("");
                                                    setLawContent("");
                                                }}
                                                className="px-2.5 py-1 bg-yellow-500 text-black rounded-lg text-[10px] font-bold uppercase"
                                            >
                                                Ley
                                            </button>
                                        </div>
                                        <div className="flex gap-1.5">
                                            <button
                                                onClick={() => executeAction("votar", { voto: "si" })}
                                                className="flex-1 py-1 bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 rounded-lg text-[10px] font-bold uppercase"
                                            >
                                                👍 Votar SÍ en Asamblea
                                            </button>
                                            <button
                                                onClick={() => executeAction("votar", { voto: "no" })}
                                                className="flex-1 py-1 bg-red-500/20 text-red-300 border border-red-500/30 rounded-lg text-[10px] font-bold uppercase"
                                            >
                                                👎 Votar NO
                                            </button>
                                        </div>
                                    </div>
                                </div>
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
            className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg transition-all whitespace-nowrap ${
                active ? "bg-emerald-500 text-black font-black" : "text-gray-400 hover:text-white hover:bg-white/5"
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
            className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-lg transition-all ${
                active
                    ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                    : "text-gray-500 hover:text-gray-300"
            }`}
        >
            <Icon className="w-3.5 h-3.5" />
            <span className="text-[9px] font-bold uppercase">{label}</span>
        </button>
    );
}

function MoveBtn({ icon: Icon, label, onClick }: any) {
    return (
        <button
            onClick={onClick}
            className="p-2.5 sm:p-3 bg-white/5 border border-white/10 rounded-xl hover:bg-emerald-500/15 hover:border-emerald-500/40 group transition-all active:scale-95 flex items-center justify-center"
        >
            {Icon ? (
                <Icon className="w-5 h-5 text-gray-300 group-hover:text-emerald-400 transition-colors" />
            ) : (
                <span className="text-xs font-bold text-gray-400 group-hover:text-emerald-400">{label}</span>
            )}
        </button>
    );
}

function ActionCard({ icon: Icon, title, desc, onClick }: any) {
    return (
        <button
            onClick={onClick}
            className="flex items-start gap-2.5 p-2.5 bg-white/5 border border-white/10 rounded-xl hover:bg-emerald-500/10 hover:border-emerald-500/30 transition-all text-left group active:scale-[0.98]"
        >
            <div className="p-2 bg-white/5 rounded-lg group-hover:bg-emerald-500/20 group-hover:text-emerald-400 transition-all shrink-0">
                <Icon className="w-4 h-4" />
            </div>
            <div className="min-w-0">
                <h4 className="text-[11px] font-bold text-white uppercase tracking-wider truncate">{title}</h4>
                <p className="text-[9px] text-gray-400 leading-tight truncate">{desc}</p>
            </div>
        </button>
    );
}
