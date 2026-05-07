"use client";

import React, { useState, useEffect } from "react";
import {
    CloudRain, Sun, CloudLightning, Zap, TrendingUp, TrendingDown,
    Skull, Heart, X, Coins, BookOpen, Users, Flag, Send, MessageSquare,
    Globe, Radio, MapPlus, ArrowUp, ArrowDown, ArrowLeft, ArrowRight, Wallet,
    RefreshCw, CheckCircle2, AlertCircle, Clock, FastForward, Gauge
} from "lucide-react";
import { motion } from "framer-motion";
import useGameStore from "@/store/useGameStore";
import { getHttpUrl } from "@/utils/apiConfig";

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
            const response = await fetch(getHttpUrl(`/game/god-mode/${userId}`), {
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
            const response = await sendArchitectMessage(globalMessage, targetId);
            setStatus({ type: 'success', msg: 'Mensaje Entregado' });
            setGlobalMessage("");
            setTimeout(() => setStatus({ type: 'idle', msg: '' }), 3000);
        } catch (error: any) {
            setStatus({ type: 'error', msg: error.message || 'Error de Conexión' });
        }
    };

    const handleUpdateLore = async () => {
        setStatus({ type: 'loading', msg: 'Actualizando Lore...' });
        const success = await sendGodAction('UPDATE_LORE', { lore: localLore });
        if (success) {
            setStatus({ type: 'success', msg: 'Realidad Actualizada' });
            setTimeout(() => setStatus({ type: 'idle', msg: '' }), 3000);
        } else {
            setStatus({ type: 'error', msg: 'Error de Sincronización' });
        }
    };

    const handleSpawnAgents = async () => {
        setStatus({ type: 'loading', msg: 'Invocando Agentes...' });
        const success = await sendGodAction('SPAWN_AGENT', { count: spawnCount });
        if (success) {
            setStatus({ type: 'success', msg: `${spawnCount} Agentes Invocados` });
            setTimeout(() => setStatus({ type: 'idle', msg: '' }), 3000);
        } else {
            setStatus({ type: 'error', msg: 'Fallo en la Invocación' });
        }
    };

    const handleCreateMission = async () => {
        if (!missionTitle || !missionDesc) return;
        setStatus({ type: 'loading', msg: 'Creando Misión...' });
        const success = await sendGodAction('CREATE_MISSION', { 
            title: missionTitle, 
            description: missionDesc 
        });
        if (success) {
            setStatus({ type: 'success', msg: 'Misión Publicada' });
            setMissionTitle("");
            setMissionDesc("");
            setTimeout(() => setStatus({ type: 'idle', msg: '' }), 3000);
        } else {
            setStatus({ type: 'error', msg: 'Error al Publicar' });
        }
    };

    const handleBuyLand = async () => {
        if (!landPurchaseDirection) return;
        setStatus({ type: 'loading', msg: 'Expandiendo Territorio...' });
        const success = await sendGodAction('BUY_LAND', {
            direction: landPurchaseDirection,
            count: landPurchaseCount
        });
        if (success) {
            setStatus({ type: 'success', msg: 'Tierra Adquirida' });
            setLandPurchaseDirection(null);
            setTimeout(() => setStatus({ type: 'idle', msg: '' }), 3000);
        } else {
            setStatus({ type: 'error', msg: 'Fallo en Compra' });
        }
    };

    const handleSetSpeed = async (ritmo: number) => {
        setStatus({ type: 'loading', msg: 'Ajustando Tiempo...' });
        try {
            const response = await fetch(getHttpUrl(`/game/speed`), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: userId,
                    ritmo: ritmo
                })
            });

            if (response.ok) {
                setStatus({ type: 'success', msg: 'Relatividad Ajustada' });
                setTimeout(() => setStatus({ type: 'idle', msg: '' }), 3000);
            } else {
                setStatus({ type: 'error', msg: 'Error al cambiar velocidad' });
            }
        } catch (error) {
            setStatus({ type: 'error', msg: 'Fallo en el control temporal' });
        }
    };

    return (
        <div className="flex flex-col h-full space-y-8 pb-8">
            {/* Mensajería Divina */}
            <Section title="Voz del Arquitecto" icon={Radio}>
                <div className="space-y-4">
                    <div className="flex p-1 bg-black/40 rounded-xl border border-white/5">
                        <button
                            onClick={() => setIsGlobalMessage(true)}
                            className={`flex-1 py-2 text-[9px] font-bold uppercase rounded-lg transition-all ${isGlobalMessage ? 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/30' : 'text-gray-500'}`}
                        >
                            Global
                        </button>
                        <button
                            onClick={() => setIsGlobalMessage(false)}
                            disabled={!selectedAgentId}
                            className={`flex-1 py-2 text-[9px] font-bold uppercase rounded-lg transition-all ${!isGlobalMessage ? 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/30' : 'text-gray-500'} disabled:opacity-20`}
                        >
                            Privado {selectedAgent && `(${selectedAgent?.identidad?.nombre})`}
                        </button>
                    </div>

                    <div className="relative">
                        <textarea
                            value={globalMessage}
                            onChange={(e) => setGlobalMessage(e.target.value)}
                            placeholder={isGlobalMessage ? "Escribe un mensaje para todos los agentes..." : `Mensaje privado para ${selectedAgent?.identidad?.nombre}...`}
                            className="w-full bg-black/60 border border-white/10 rounded-2xl p-4 text-xs text-white placeholder:text-gray-700 focus:border-indigo-500/40 focus:outline-none transition-all resize-none h-24 font-mono"
                        />
                        <button
                            onClick={handleSendMessage}
                            disabled={status.type === 'loading' || !globalMessage.trim()}
                            className="absolute bottom-3 right-3 p-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl transition-all shadow-lg shadow-indigo-600/20 disabled:opacity-20"
                        >
                            <Send className="w-4 h-4" />
                        </button>
                    </div>
                </div>
            </Section>

            {/* Control Ambiental */}
            <Section title="Manipulación de la Realidad" icon={Globe}>
                <div className="grid grid-cols-2 gap-3">
                    <ActionButton
                        icon={Sun}
                        label="Día Despejado"
                        onClick={() => sendGodAction('SET_WEATHER', { weather: 'sunny' })}
                        color="hover:text-yellow-400"
                    />
                    <ActionButton
                        icon={CloudRain}
                        label="Lluvia"
                        onClick={() => sendGodAction('SET_WEATHER', { weather: 'rainy' })}
                        color="hover:text-blue-400"
                    />
                    <ActionButton
                        icon={CloudLightning}
                        label="Tormenta Eléctrica"
                        onClick={() => sendGodAction('SET_WEATHER', { weather: 'storm' })}
                        color="hover:text-indigo-400"
                    />
                     <ActionButton
                        icon={Skull}
                        label="Desatar Plaga"
                        onClick={() => sendGodAction('TRIGGER_EVENT', { event: 'plague' })}
                        color="hover:text-red-500"
                    />
                </div>
            </Section>

            {/* Control Temporal */}
            <Section title="Dilatación Temporal" icon={Clock}>
                <div className="grid grid-cols-4 gap-2">
                    <ActionButton
                        icon={Zap}
                        label="Máximo"
                        onClick={() => handleSetSpeed(0.0)}
                        color="hover:text-cyan-400"
                    />
                    <ActionButton
                        icon={FastForward}
                        label="Rápido"
                        onClick={() => handleSetSpeed(0.1)}
                        color="hover:text-indigo-400"
                    />
                    <ActionButton
                        icon={Gauge}
                        label="Normal"
                        onClick={() => handleSetSpeed(0.5)}
                        color="hover:text-green-400"
                    />
                    <ActionButton
                        icon={Clock}
                        label="Lento"
                        onClick={() => handleSetSpeed(1.5)}
                        color="hover:text-orange-400"
                    />
                </div>
            </Section>

            {/* Expansión y Población */}
            <Section title="Expansión y Población" icon={Users}>
                <div className="space-y-4">
                    <div className="bg-black/40 rounded-2xl p-4 border border-white/5 space-y-4">
                        <div className="flex items-center justify-between">
                            <span className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">Invocación masiva</span>
                            <div className="flex items-center gap-3 bg-black/40 rounded-lg p-1 border border-white/5">
                                <button onClick={() => setSpawnCount(Math.max(1, spawnCount - 1))} className="p-1 hover:text-indigo-400"><ArrowLeft className="w-3 h-3" /></button>
                                <span className="text-xs font-mono w-4 text-center">{spawnCount}</span>
                                <button onClick={() => setSpawnCount(Math.min(10, spawnCount + 1))} className="p-1 hover:text-indigo-400"><ArrowRight className="w-3 h-3" /></button>
                            </div>
                        </div>
                        <button
                            onClick={handleSpawnAgents}
                            className="w-full py-3 bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 rounded-xl text-[9px] font-black uppercase tracking-widest transition-all flex items-center justify-center gap-2"
                        >
                            <MapPlus className="w-3.5 h-3.5" /> Generar Agentes
                        </button>
                    </div>

                    <div className="bg-black/40 rounded-2xl p-4 border border-white/5 space-y-4">
                        <span className="text-[10px] font-bold text-gray-500 uppercase tracking-widest block mb-2">Comprar Tierras</span>
                        <div className="grid grid-cols-4 gap-2">
                             {(['north', 'south', 'east', 'west'] as const).map(dir => (
                                <button
                                    key={dir}
                                    onClick={() => setLandPurchaseDirection(dir)}
                                    className={`p-3 rounded-xl border transition-all flex items-center justify-center ${landPurchaseDirection === dir ? 'bg-indigo-500/20 border-indigo-500 text-indigo-400' : 'bg-black/40 border-white/5 text-gray-600 hover:text-gray-400'}`}
                                >
                                    {dir === 'north' && <ArrowUp className="w-4 h-4" />}
                                    {dir === 'south' && <ArrowDown className="w-4 h-4" />}
                                    {dir === 'east' && <ArrowRight className="w-4 h-4" />}
                                    {dir === 'west' && <ArrowLeft className="w-4 h-4" />}
                                </button>
                             ))}
                        </div>
                        <button
                            onClick={handleBuyLand}
                            disabled={!landPurchaseDirection}
                            className="w-full py-3 bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 rounded-xl text-[9px] font-black uppercase tracking-widest transition-all flex items-center justify-center gap-2 disabled:opacity-10"
                        >
                            <Wallet className="w-3.5 h-3.5" /> Adquirir {landPurchaseCount} Terreno(s)
                        </button>
                    </div>
                </div>
            </Section>

            {/* Misiones y Objetivos */}
            <Section title="Decretos de Misión" icon={Zap}>
                <div className="space-y-3">
                    <input
                        type="text"
                        value={missionTitle}
                        onChange={(e) => setMissionTitle(e.target.value)}
                        placeholder="Título de la Misión..."
                        className="w-full bg-black/60 border border-white/10 rounded-xl p-3 text-[10px] text-white focus:border-indigo-500/40 focus:outline-none transition-all font-mono"
                    />
                    <textarea
                        value={missionDesc}
                        onChange={(e) => setMissionDesc(e.target.value)}
                        placeholder="Descripción y objetivos..."
                        className="w-full bg-black/60 border border-white/10 rounded-xl p-3 text-[10px] text-white focus:border-indigo-500/40 focus:outline-none transition-all resize-none h-20 font-mono"
                    />
                    <button
                        onClick={handleCreateMission}
                        disabled={!missionTitle || !missionDesc}
                        className="w-full py-3 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-[9px] font-black uppercase tracking-widest transition-all shadow-lg shadow-indigo-600/20 disabled:opacity-20"
                    >
                        Publicar Misión Global
                    </button>
                </div>
            </Section>

            {/* Economía */}
            <Section title="Flujos Económicos" icon={Coins}>
                <div className="grid grid-cols-2 gap-3">
                    <ActionButton
                        icon={TrendingUp}
                        label="Inyectar Capital"
                        onClick={() => sendGodAction('MODIFY_ECONOMY', { sub_action: 'inject_money', amount: 1000 })}
                        color="hover:text-green-400"
                    />
                    <ActionButton
                        icon={TrendingDown}
                        label="Drenar Capital"
                        onClick={() => sendGodAction('MODIFY_ECONOMY', { sub_action: 'drain_money', amount: 1000 })}
                        color="hover:text-orange-400"
                    />
                </div>
            </Section>

            {/* El Lore Metafísico */}
            <Section title="La Historiografía" icon={BookOpen}>
                <div className="space-y-4">
                    <textarea
                        value={localLore}
                        onChange={(e) => setLocalLore(e.target.value)}
                        placeholder="Define la base de la realidad actual..."
                        className="w-full bg-black/60 border border-white/10 rounded-2xl p-4 text-xs text-white placeholder:text-gray-700 focus:border-indigo-500/40 focus:outline-none transition-all resize-none h-40 font-mono"
                    />
                    <button
                        onClick={handleUpdateLore}
                        className="w-full py-4 bg-white/5 hover:bg-white/10 text-white border border-white/10 rounded-2xl text-[10px] font-black uppercase tracking-[0.2em] transition-all flex items-center justify-center gap-3"
                    >
                        <RefreshCw className={`w-4 h-4 ${status.type === 'loading' ? 'animate-spin' : ''}`} />
                        Reescribir el Destino
                    </button>
                </div>
            </Section>

            {/* Status Feedback */}
            {status.type !== 'idle' && (
                <div className={`fixed bottom-8 right-8 px-6 py-4 rounded-2xl border flex items-center gap-4 shadow-2xl z-[100] animate-in slide-in-from-right fade-in ${status.type === 'success' ? 'bg-green-500/20 border-green-500/30 text-green-400' :
                    status.type === 'error' ? 'bg-red-500/20 border-red-500/30 text-red-400' :
                        'bg-indigo-500/20 border-indigo-500/30 text-indigo-400'
                    }`}>
                    {status.type === 'loading' ? <RefreshCw className="w-5 h-5 animate-spin" /> :
                        status.type === 'success' ? <CheckCircle2 className="w-5 h-5" /> : <AlertCircle className="w-5 h-5" />}
                    <span className="text-[10px] font-black uppercase tracking-widest">{status.msg}</span>
                </div>
            )}
        </div>
    );
}

function Section({ title, icon: Icon, children }: { title: string, icon: any, children: React.ReactNode }) {
    return (
        <div className="space-y-4">
            <div className="flex items-center gap-4">
                <div className="p-2 rounded-lg bg-white/5 border border-white/5">
                    <Icon className="w-3.5 h-3.5 text-indigo-400/60" />
                </div>
                <h3 className="text-[9px] font-black text-white/20 uppercase tracking-[0.3em] whitespace-nowrap">{title}</h3>
                <div className="h-px bg-white/5 w-full"></div>
            </div>
            {children}
        </div>
    );
}

function ActionButton({ icon: Icon, label, onClick, color }: { icon: any, label: string, onClick: () => void, color: string }) {
    return (
        <button
            onClick={onClick}
            className={`flex flex-col items-center justify-center p-4 bg-black/40 border border-white/5 rounded-2xl hover:bg-white/[0.03] hover:border-white/10 transition-all gap-2 group ${color}`}
        >
            <Icon className="w-5 h-5 text-gray-600 transition-colors group-hover:text-inherit" />
            <span className="text-[8px] font-black uppercase tracking-widest text-gray-500 group-hover:text-white/80">{label}</span>
        </button>
    );
}
