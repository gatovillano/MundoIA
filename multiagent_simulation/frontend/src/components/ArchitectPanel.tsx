"use client";

import React, { useState, useEffect } from "react";
import {
    CloudRain, Sun, CloudLightning, Zap, TrendingUp, TrendingDown,
    Skull, Heart, X, Coins, BookOpen, Users, Flag, Send, MessageSquare,
    Globe, Radio, MapPlus, ArrowUp, ArrowDown, ArrowLeft, ArrowRight, Wallet
} from "lucide-react";
import { motion } from "framer-motion";
import useGameStore from "@/store/useGameStore";

interface ArchitectPanelProps {
    userId: string;
    onClose: () => void;
}

export default function ArchitectPanel({ userId, onClose }: ArchitectPanelProps) {
    const { 
        agents, 
        selectAgent, 
        selectedAgentId, 
        lore, 
        sendArchitectMessage, 
        economy 
    } = useGameStore();

    const [globalMessage, setGlobalMessage] = useState("");
    const [localLore, setLocalLore] = useState(lore || "");
    const [missionTitle, setMissionTitle] = useState("");
    const [missionDesc, setMissionDesc] = useState("");
    const [spawnCount, setSpawnCount] = useState(1);
    const [isIndividual, setIsIndividual] = useState(false);
    const [isGlobalMessage, setIsGlobalMessage] = useState(true);
    const [assemblyTopic, setAssemblyTopic] = useState("");
    const [status, setStatus] = useState<{ type: 'idle' | 'loading' | 'success' | 'error', msg: string }>({ type: 'idle', msg: '' });
    const [landPurchaseDirection, setLandPurchaseDirection] = useState<'north' | 'south' | 'east' | 'west' | null>(null);
    const [landPurchaseCount, setLandPurchaseCount] = useState(1);
    const [selectedGroupId, setSelectedGroupId] = useState<string | null>(null);

    const selectedAgent = agents.find(a => a.id === selectedAgentId);

    useEffect(() => {
        if (lore) setLocalLore(lore);
    }, [lore]);

    useEffect(() => {
        if (selectedAgentId) {
            setIsGlobalMessage(false);
        }
    }, [selectedAgentId]);

    const sendGodAction = async (type: string, params: any) => {
        try {
            const protocol = window.location.protocol;
            let host = window.location.host;
            if (window.location.hostname === 'mundoia.cuerpolibre.cl') {
                host = 'api-mundoia.cuerpolibre.cl';
            } else if (window.location.hostname === 'localhost') {
                host = 'api-mundoia.cuerpolibre.cl';
            }

            const response = await fetch(`${protocol}//${host}/game/god-mode/${userId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    action_type: type,
                    params: params
                })
            });

            if (response.ok) {
                let fxType = '';
                if (type === 'SET_WEATHER') {
                    if (params.weather === 'storm') fxType = 'glitch';
                } else if (type === 'TRIGGER_EVENT') {
                    if (params.event === 'earthquake') fxType = 'shake';
                    if (params.event === 'plague') fxType = 'plague';
                } else if (type === 'MODIFY_ECONOMY') {
                    if (params.sub_action === 'inject_money') fxType = 'money';
                } else if (type === 'MODIFY_AGENT') {
                    if (params.effect === 'smite') fxType = 'smite';
                }

                if (fxType) {
                    window.dispatchEvent(new CustomEvent('divine-action-fx', { detail: { type: fxType, params } }));
                }
            }

            return response.ok;
        } catch (error) {
            console.error("Error ejecutando acción divina:", error);
            return false;
        }
    };

    const handleSendMessage = async () => {
        if (!globalMessage.trim()) return;

        const targetId = isGlobalMessage ? undefined : (selectedAgentId || undefined);
        setStatus({ type: 'loading', msg: 'Transmitiendo...' });

        try {
            await sendArchitectMessage(globalMessage, targetId);
            setStatus({ type: 'success', msg: isGlobalMessage ? 'Decreto Global enviado' : `Voz enviada al Ser ${targetId}` });
            setGlobalMessage("");
            setTimeout(() => setStatus({ type: 'idle', msg: '' }), 3000);
        } catch (error) {
            console.error("Error al enviar mensaje:", error);
            setStatus({ type: 'error', msg: 'Falla en la transmisión' });
            setTimeout(() => setStatus({ type: 'idle', msg: '' }), 3000);
        }
    };

    return (
        <div className="flex flex-col h-full">
            <div className="space-y-8 overflow-y-auto custom-scrollbar pr-1 pb-10">
                
                {/* 1. Transmisión Psíquica */}
                <Section title="Voz del Arquitecto">
                    <div className="space-y-4">
                        <div className="flex gap-1.5 p-1 bg-black/40 rounded-xl border border-white/5">
                            <button
                                onClick={() => setIsGlobalMessage(true)}
                                className={`flex-1 py-1.5 text-[9px] font-bold uppercase rounded-lg transition-all ${isGlobalMessage ? 'bg-yellow-500/20 text-yellow-500 border border-yellow-500/30' : 'text-gray-500 hover:text-gray-300'}`}
                            >
                                Decreto Global
                            </button>
                            <button
                                onClick={() => {
                                    if (selectedAgentId) setIsGlobalMessage(false);
                                    else alert("Selecciona un agente en el mapa.");
                                }}
                                className={`flex-1 py-1.5 text-[9px] font-bold uppercase rounded-lg transition-all ${!isGlobalMessage ? 'bg-yellow-500/20 text-yellow-500 border border-yellow-500/30' : 'text-gray-500 hover:text-gray-300'}`}
                            >
                                Susurro al Ser
                            </button>
                        </div>

                        {!isGlobalMessage && (
                            <div className="flex items-center justify-between px-3 py-2 bg-yellow-500/5 rounded-xl border border-yellow-500/10">
                                <span className="text-[9px] text-gray-500 font-mono uppercase">Receptor:</span>
                                {selectedAgentId ? (
                                    <div className="flex items-center gap-2">
                                        <span className="text-yellow-500 font-bold font-mono text-xs">{selectedAgentId}</span>
                                        <X className="w-3 h-3 text-red-400 cursor-pointer" onClick={() => selectAgent(null)} />
                                    </div>
                                ) : (
                                    <span className="text-red-400/60 text-[9px] font-bold animate-pulse">SIN SELECCIÓN</span>
                                )}
                            </div>
                        )}

                        <div className="relative group">
                            <textarea
                                value={globalMessage}
                                onChange={(e) => setGlobalMessage(e.target.value)}
                                placeholder={isGlobalMessage ? "Dictar voluntad a la creación..." : "Manifestar susurro al agente..."}
                                className="w-full h-24 bg-black/60 border border-white/10 rounded-2xl p-4 text-xs text-white placeholder:text-gray-600 focus:border-yellow-500/30 focus:outline-none transition-all resize-none font-mono"
                            />
                            <button
                                onClick={handleSendMessage}
                                disabled={!globalMessage.trim() || status.type === 'loading'}
                                className="absolute bottom-3 right-3 p-2 bg-yellow-500/20 hover:bg-yellow-500 text-yellow-500 hover:text-black rounded-xl transition-all border border-yellow-500/30 disabled:opacity-20"
                            >
                                {status.type === 'loading' ? <div className="w-4 h-4 border-2 border-yellow-500/30 border-t-yellow-500 rounded-full animate-spin" /> : <Send className="w-4 h-4" />}
                            </button>
                        </div>
                        {status.msg && (
                            <div className={`text-[9px] text-center font-bold tracking-widest uppercase ${status.type === 'error' ? 'text-red-400' : 'text-green-400'}`}>
                                {status.msg}
                            </div>
                        )}
                    </div>
                </Section>

                {/* 1.5 Realidad Narrativa (Lore) */}
                <Section title="Realidad Narrativa (Lore)">
                    <div className="space-y-3 group">
                        <textarea
                            value={localLore}
                            onChange={(e) => setLocalLore(e.target.value)}
                            placeholder="Ej: Una sociedad post-apocalíptica donde el agua es la moneda..."
                            className="w-full h-24 bg-black/40 border border-white/10 rounded-xl p-4 text-xs text-gray-400 focus:border-yellow-500/50 focus:bg-black/60 focus:outline-none transition-all resize-none font-mono leading-relaxed group-hover:border-white/20"
                        />
                        <button
                            onClick={() => sendGodAction("SET_GLOBAL_CONTEXT", { lore: localLore })}
                            className="w-full py-2.5 bg-yellow-500/10 hover:bg-yellow-500/20 text-yellow-500 border border-yellow-500/30 rounded-lg text-[10px] font-bold uppercase tracking-widest transition-all flex items-center justify-center gap-2"
                        >
                            <BookOpen className="w-3.5 h-3.5" />
                            Redefinir Realidad
                        </button>
                    </div>
                </Section>

                {/* 2. Clima y Origen */}
                <Section title="Control de la Realidad">
                    <div className="grid grid-cols-2 gap-3">
                        <WideBtn icon={Sun} label="Día Radiante" onClick={() => sendGodAction("SET_WEATHER", { weather: "sunny" })} color="text-yellow-400 border-yellow-400/20 hover:bg-yellow-500/10" />
                        <WideBtn icon={CloudRain} label="Diluvio" onClick={() => sendGodAction("SET_WEATHER", { weather: "rainy" })} color="text-blue-400 border-blue-400/20 hover:bg-blue-500/10" />
                        <WideBtn icon={CloudLightning} label="Tormenta Glitch" onClick={() => sendGodAction("SET_WEATHER", { weather: "storm" })} color="text-purple-400 border-purple-400/20 hover:bg-purple-500/10" />
                        <WideBtn icon={Skull} label="Plaga Viral" onClick={() => sendGodAction("TRIGGER_EVENT", { event: "plague" })} color="text-green-400 border-green-400/20 hover:bg-green-500/10" />
                    </div>
                </Section>

                {/* 3. Génesis */}
                <Section title="Génesis Artificial">
                    <div className="bg-black/20 p-4 rounded-2xl border border-white/5 space-y-4">
                        <div className="flex justify-between items-center px-1">
                            <span className="text-[10px] text-gray-400 font-mono tracking-widest uppercase">Cantidad</span>
                            <span className="text-sm font-bold text-yellow-500 font-mono">{spawnCount}</span>
                        </div>
                        <input
                            type="range" min="1" max="10" value={spawnCount}
                            onChange={(e) => setSpawnCount(parseInt(e.target.value))}
                            className="w-full h-1.5 bg-white/10 rounded-lg appearance-none cursor-pointer accent-yellow-500"
                        />
                        <button
                            onClick={() => sendGodAction("SPAWN_AGENT", { count: spawnCount })}
                            className="w-full py-3 bg-yellow-500/20 hover:bg-yellow-500 text-yellow-500 hover:text-black border border-yellow-500/30 rounded-xl text-[10px] font-bold uppercase tracking-widest transition-all shadow-lg shadow-yellow-500/5"
                        >
                            Manifestar Vida
                        </button>
                    </div>
                </Section>

                {/* 3.2 Expansión del Mundo */}
                <Section title="Expansión Territorial">
                    <div className="bg-black/20 p-4 rounded-2xl border border-white/5 space-y-4">
                        <div className="flex justify-between items-center px-1">
                            <span className="text-[10px] text-gray-400 font-mono tracking-widest uppercase">Costo por Casilla</span>
                            <span className="text-sm font-bold text-emerald-400 font-mono">{economy?.total_dinero ? (1000).toFixed(0) : 1000} MC</span>
                        </div>

                        {/* Selector de cantidad */}
                        <div className="flex justify-between items-center px-1">
                            <span className="text-[10px] text-gray-400 font-mono tracking-widest uppercase">Casillas</span>
                            <span className="text-sm font-bold text-yellow-500 font-mono">{landPurchaseCount}</span>
                        </div>
                        <input
                            type="range" min="1" max="10" value={landPurchaseCount}
                            onChange={(e) => setLandPurchaseCount(parseInt(e.target.value))}
                            className="w-full h-1.5 bg-white/10 rounded-lg appearance-none cursor-pointer accent-emerald-500"
                        />

                        {/* Selector de dirección */}
                        <div className="grid grid-cols-4 gap-2">
                            <DirectionBtn
                                icon={ArrowUp}
                                label="Norte"
                                active={landPurchaseDirection === 'north'}
                                onClick={() => setLandPurchaseDirection(landPurchaseDirection === 'north' ? null : 'north')}
                            />
                            <DirectionBtn
                                icon={ArrowDown}
                                label="Sur"
                                active={landPurchaseDirection === 'south'}
                                onClick={() => setLandPurchaseDirection(landPurchaseDirection === 'south' ? null : 'south')}
                            />
                            <DirectionBtn
                                icon={ArrowLeft}
                                label="Oeste"
                                active={landPurchaseDirection === 'west'}
                                onClick={() => setLandPurchaseDirection(landPurchaseDirection === 'west' ? null : 'west')}
                            />
                            <DirectionBtn
                                icon={ArrowRight}
                                label="Este"
                                active={landPurchaseDirection === 'east'}
                                onClick={() => setLandPurchaseDirection(landPurchaseDirection === 'east' ? null : 'east')}
                            />
                        </div>

                        <button
                            onClick={() => sendGodAction("EXPAND_WORLD", {
                                direccion: landPurchaseDirection,
                                cantidad: landPurchaseCount
                            })}
                            className="w-full py-3 bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-400 border border-emerald-500/30 rounded-xl text-[10px] font-bold uppercase tracking-widest transition-all flex items-center justify-center gap-2"
                        >
                            <MapPlus className="w-4 h-4" />
                            Expandir Mundo ({landPurchaseCount} casillas)
                        </button>

                        <div className="text-[8px] text-gray-500 font-mono text-center">
                            {landPurchaseDirection ? `Expansión hacia ${landPurchaseDirection.toUpperCase()}` : 'Expansión uniforme (todas direcciones)'}
                        </div>
                    </div>
                </Section>

                {/* 3.3 Compra de Terreno por Grupos */}
                <Section title="Compra de Terreno (Grupos)">
                    <div className="bg-black/20 p-4 rounded-2xl border border-white/5 space-y-4">
                        <div className="flex items-center gap-2 px-1">
                            <Wallet className="w-3.5 h-3.5 text-purple-400" />
                            <span className="text-[10px] text-gray-400 font-mono uppercase">Seleccionar Grupo</span>
                        </div>

                        {/* Lista de grupos disponibles */}
                        <GroupSelector
                            selectedGroupId={selectedGroupId}
                            onSelectGroupId={setSelectedGroupId}
                        />

                        {selectedGroupId && (
                            <>
                                <div className="flex justify-between items-center px-1">
                                    <span className="text-[10px] text-gray-400 font-mono tracking-widest uppercase">Casillas</span>
                                    <span className="text-sm font-bold text-yellow-500 font-mono">{landPurchaseCount}</span>
                                </div>
                                <input
                                    type="range" min="1" max="10" value={landPurchaseCount}
                                    onChange={(e) => setLandPurchaseCount(parseInt(e.target.value))}
                                    className="w-full h-1.5 bg-white/10 rounded-lg appearance-none cursor-pointer accent-purple-500"
                                />

                                <div className="flex justify-between items-center px-1 text-[9px] font-mono">
                                    <span className="text-gray-500">Costo Total:</span>
                                    <span className="text-purple-400 font-bold">{landPurchaseCount * 1000} MC</span>
                                </div>

                                <button
                                    onClick={() => sendGodAction("PURCHASE_LAND", {
                                        grupo_id: selectedGroupId,
                                        direccion: landPurchaseDirection,
                                        cantidad: landPurchaseCount
                                    })}
                                    className="w-full py-3 bg-purple-500/20 hover:bg-purple-500/30 text-purple-400 border border-purple-500/30 rounded-xl text-[10px] font-bold uppercase tracking-widest transition-all flex items-center justify-center gap-2"
                                >
                                    <MapPlus className="w-4 h-4" />
                                    Comprar Terreno
                                </button>
                            </>
                        )}

                        <div className="text-[8px] text-gray-500 font-mono text-center">
                            El grupo seleccionado compra terreno con sus fondos
                        </div>
                    </div>
                </Section>

                {/* 3.5 Gestión de Misiones */}
                <Section title="Objetivos Colectivos (Misiones)">
                    <div className="space-y-4">
                        <div className="bg-black/20 p-4 rounded-2xl border border-white/5 space-y-3">
                            <input 
                                type="text"
                                value={missionTitle}
                                onChange={(e) => setMissionTitle(e.target.value)}
                                placeholder="Título de la misión..."
                                className="w-full bg-black/60 border border-white/10 rounded-xl p-3 text-xs text-white placeholder:text-gray-600 focus:border-yellow-500/30 focus:outline-none transition-all font-mono"
                            />
                            <textarea 
                                value={missionDesc}
                                onChange={(e) => setMissionDesc(e.target.value)}
                                placeholder="Descripción del objetivo divino..."
                                className="w-full h-20 bg-black/60 border border-white/10 rounded-xl p-3 text-xs text-white placeholder:text-gray-600 focus:border-yellow-500/30 focus:outline-none transition-all font-mono resize-none"
                            />
                            <button
                                onClick={() => {
                                    if (!missionTitle || !missionDesc) return alert("Completa los datos de la misión.");
                                    sendGodAction("CREATE_MISSION", { title: missionTitle, description: missionDesc, target_type: 'global' });
                                    setMissionTitle("");
                                    setMissionDesc("");
                                }}
                                className="w-full py-3 bg-yellow-500/10 hover:bg-yellow-500/20 text-yellow-500 border border-yellow-500/30 rounded-xl text-[10px] font-bold uppercase tracking-widest transition-all"
                            >
                                Promulgar Misión
                            </button>
                        </div>
                    </div>
                </Section>

                {/* 4. Gobernanza */}
                <Section title="Gobernanza Divina">
                    <div className="space-y-4">
                        <div className="relative group">
                            <input
                                type="text"
                                value={assemblyTopic}
                                onChange={(e) => setAssemblyTopic(e.target.value)}
                                placeholder="Tema de discusión..."
                                className="w-full bg-black/60 border border-white/10 rounded-xl p-3 text-xs text-white placeholder:text-gray-600 focus:border-purple-500/30 focus:outline-none transition-all font-mono"
                            />
                            <div className="absolute top-3 right-3 text-purple-500/40">
                                <Radio className="w-3.5 h-3.5 animate-pulse" />
                            </div>
                        </div>
                        <button
                            onClick={() => {
                                if (!assemblyTopic.trim()) return alert("Define un tema para la asamblea.");
                                sendGodAction("START_ASSEMBLY", { topic: assemblyTopic });
                            }}
                            className="w-full py-3 bg-purple-500/20 hover:bg-purple-500 text-purple-400 hover:text-black border border-purple-500/30 rounded-xl text-[10px] font-bold uppercase tracking-widest transition-all"
                        >
                            Convocar Asamblea de Ciudadanos
                        </button>
                    </div>
                </Section>

                {/* 5. Economía */}
                <Section title="Arquitectura Económica">
                    <div className="bg-black/20 p-4 rounded-2xl border border-white/5 space-y-4">
                        <div className="flex justify-between items-center text-[10px] font-mono">
                            <span className="text-gray-500 uppercase">Reserva Federal</span>
                            <span className="text-green-400 font-bold">{economy?.total_dinero?.toFixed(1) || 0} MC</span>
                        </div>
                        <div className="grid grid-cols-2 gap-2">
                            <GodBtn icon={Coins} label="Inyectar MC" onClick={() => sendGodAction("MODIFY_ECONOMY", { sub_action: "inject_money" })} color="text-emerald-400" />
                            <GodBtn icon={TrendingDown} label="Market Crash" onClick={() => sendGodAction("MODIFY_ECONOMY", { sub_action: "crash_market" })} color="text-red-500" />
                        </div>
                    </div>
                </Section>

                 {/* 6. Juicio Individual (Solo si hay selección) */}
                 {selectedAgent && (
                     <Section title={`Decreto sobre Ser ${selectedAgentId}`}>
                        <div className="grid grid-cols-3 gap-2">
                            <GodBtn icon={Heart} label="Sanar" onClick={() => sendGodAction("MODIFY_AGENT", { agent_id: selectedAgentId, effect: "heal" })} color="text-pink-400" />
                            <GodBtn icon={Zap} label="Smite" onClick={() => sendGodAction("MODIFY_AGENT", { agent_id: selectedAgentId, effect: "smite" })} color="text-red-500" />
                            <GodBtn icon={Skull} label="Kill" onClick={() => sendGodAction("MODIFY_AGENT", { agent_id: selectedAgentId, effect: "kill" })} color="text-white" />
                        </div>
                     </Section>
                 )}

            </div>
        </div>
    );
}

// Subcomponentes Refinados
function Section({ title, children }: { title: string, children: React.ReactNode }) {
    return (
        <div className="space-y-4">
            <div className="flex items-center gap-4">
                <h3 className="text-[10px] font-black text-white/30 uppercase tracking-[0.3em] whitespace-nowrap">{title}</h3>
                <div className="h-px bg-white/5 w-full"></div>
            </div>
            {children}
        </div>
    );
}

function GodBtn({ icon: Icon, label, onClick, color }: any) {
    return (
        <button
            onClick={onClick}
            className="flex flex-col items-center justify-center p-3 rounded-2xl bg-white/[0.03] border border-white/5 hover:bg-white/[0.08] hover:border-white/20 transition-all group active:scale-95"
        >
            <Icon className={`w-5 h-5 mb-2 opacity-60 group-hover:opacity-100 transition-all ${color}`} />
            <span className="text-[8px] font-bold text-gray-500 group-hover:text-gray-300 uppercase tracking-widest">{label}</span>
        </button>
    )
}

function WideBtn({ icon: Icon, label, onClick, color }: any) {
    return (
        <button
            onClick={onClick}
            className={`w-full flex items-center justify-center gap-3 p-3 rounded-2xl border transition-all active:scale-95 group ${color}`}
        >
            <Icon className="w-3.5 h-3.5 opacity-60 group-hover:opacity-100" />
            <span className="text-[9px] font-bold uppercase tracking-widest">{label}</span>
        </button>
    )
}

function DirectionBtn({ icon: Icon, label, active, onClick }: any) {
    return (
        <button
            onClick={onClick}
            className={`flex flex-col items-center justify-center p-2 rounded-xl border transition-all active:scale-95 ${
                active
                    ? 'bg-emerald-500/20 border-emerald-500/50 text-emerald-400'
                    : 'bg-white/[0.03] border-white/5 hover:bg-white/[0.08] text-gray-500'
            }`}
        >
            <Icon className="w-4 h-4 mb-1" />
            <span className="text-[7px] font-bold uppercase tracking-widest">{label}</span>
        </button>
    )
}

function GroupSelector({ selectedGroupId, onSelectGroupId }: {
    selectedGroupId: string | null;
    onSelectGroupId: (id: string | null) => void;
}) {
    const { civilizaciones, gruposDinamicos } = useGameStore();

    const allGroups = [
        ...Object.entries(civilizaciones || {}).map(([id, data]: any) => ({ id, ...data, type: 'civilizacion' })),
        ...Object.entries(gruposDinamicos || {}).map(([id, data]: any) => ({ id, ...data, type: 'grupo' }))
    ];

    if (allGroups.length === 0) {
        return (
            <div className="text-[9px] text-gray-600 font-mono text-center py-4">
                No hay grupos o civilizaciones activas
            </div>
        );
    }

    return (
        <div className="max-h-40 overflow-y-auto custom-scrollbar space-y-1">
            {allGroups.map(group => (
                <button
                    key={group.id}
                    onClick={() => onSelectGroupId(selectedGroupId === group.id ? null : group.id)}
                    className={`w-full flex items-center justify-between p-2 rounded-lg border transition-all ${
                        selectedGroupId === group.id
                            ? 'bg-purple-500/20 border-purple-500/50'
                            : 'bg-white/[0.03] border-white/5 hover:bg-white/[0.08]'
                    }`}
                >
                    <div className="flex items-center gap-2">
                        <div
                            className="w-2 h-2 rounded-full"
                            style={{ backgroundColor: group.color || '#7c4dff' }}
                        />
                        <span className="text-[9px] font-bold text-gray-300">{group.id}</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <span className="text-[7px] text-gray-500 font-mono uppercase">{group.type}</span>
                        <span className="text-[8px] text-emerald-400 font-mono">{group.dinero?.toFixed(0) || 0} MC</span>
                    </div>
                </button>
            ))}
        </div>
    );
}
