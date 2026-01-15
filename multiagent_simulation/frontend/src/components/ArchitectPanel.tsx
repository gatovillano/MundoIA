"use client";

import { CloudRain, Sun, CloudLightning, Zap, TrendingUp, TrendingDown, Skull, Heart, X, Coins, BookOpen } from "lucide-react";
import useGameStore from "@/store/useGameStore";
import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";

interface ArchitectPanelProps {
    userId: string;
    onClose: () => void;
}

export default function ArchitectPanel({ userId, onClose }: ArchitectPanelProps) {
    const { selectedAgentId, lore } = useGameStore();
    const [localLore, setLocalLore] = useState(lore || "");
    const [spawnCount, setSpawnCount] = useState(1);
    const [isIndividual, setIsIndividual] = useState(false);

    // Parámetros de personalidad
    const [pers, setPers] = useState({
        extroversion: 0.5,
        amabilidad: 0.5,
        competitividad: 0.5,
        curiosidad: 0.5,
        hostilidad: 0.2
    });

    useEffect(() => {
        if (lore) setLocalLore(lore);
    }, [lore]);

    const sendGodAction = async (type: string, params: any) => {
        try {
            const protocol = window.location.protocol;
            let host = window.location.host;
            if (window.location.hostname === 'mundoia.gatoslibres.art') {
                host = 'api-mundoia.gatoslibres.art';
            } else if (window.location.hostname === 'localhost') {
                host = 'localhost:8000';
            }

            await fetch(`${protocol}//${host}/game/god-mode/${userId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    action_type: type,
                    params: params
                })
            });
        } catch (error) {
            console.error("Error ejecutando acción divina:", error);
        }
    };

    return (
        <motion.div
            initial={{ opacity: 0, x: -20, scale: 0.95 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            exit={{ opacity: 0, x: -20, scale: 0.95 }}
            transition={{ duration: 0.3, ease: "easeOut" }}
            className="absolute left-6 top-24 z-[70] w-[340px]"
        >
            <div className="glass-panel rounded-2xl flex flex-col overflow-hidden shadow-2xl border border-yellow-500/20 shadow-yellow-500/5">
                {/* Header Divino */}
                <div className="relative p-6 pb-4 bg-gradient-to-r from-yellow-500/10 to-transparent border-b border-yellow-500/20">
                    <button
                        onClick={onClose}
                        className="absolute top-4 right-4 p-1.5 hover:bg-white/10 rounded-full transition-colors text-yellow-500/50 hover:text-yellow-500"
                    >
                        <X className="w-4 h-4" />
                    </button>
                    <div className="flex items-center gap-4">
                        <div className="p-2.5 rounded-xl bg-yellow-500/20 text-yellow-500 border border-yellow-500/30 shadow-[0_0_15px_rgba(234,179,8,0.3)] animate-pulse-slow">
                            <Zap className="w-5 h-5" />
                        </div>
                        <div>
                            <h2 className="text-xl font-bold text-white tracking-widest uppercase font-mono leading-none mb-1">Arquitecto</h2>
                            <div className="text-[10px] text-yellow-500/80 tracking-[0.2em] font-bold">MODO DIOS ACTIVO</div>
                        </div>
                    </div>
                </div>

                <div className="p-6 space-y-8 max-h-[70vh] overflow-y-auto custom-scrollbar">

                    {/* Lore Global */}
                    <Section title="Realidad Narrativa (Lore)">
                        <div className="space-y-3 group">
                            <textarea
                                value={localLore}
                                onChange={(e) => setLocalLore(e.target.value)}
                                placeholder="Ej: Una sociedad post-apocalíptica..."
                                className="w-full h-24 bg-black/40 border border-white/10 rounded-xl p-4 text-xs text-gray-300 focus:border-yellow-500/50 focus:bg-black/60 focus:outline-none transition-all resize-none font-mono leading-relaxed group-hover:border-white/20"
                            />
                            <button
                                onClick={() => sendGodAction("SET_GLOBAL_CONTEXT", { lore: localLore })}
                                className="w-full py-2.5 bg-yellow-500/10 hover:bg-yellow-500/20 text-yellow-500 border border-yellow-500/30 rounded-lg text-[10px] font-bold uppercase tracking-widest transition-all flex items-center justify-center gap-2 hover:shadow-[0_0_10px_rgba(234,179,8,0.2)]"
                            >
                                <BookOpen className="w-3.5 h-3.5" />
                                Redefinir Realidad
                            </button>
                        </div>
                    </Section>

                    {/* Generación de Vida (Spawning) */}
                    <Section title="Génesis Artificial">
                        <div className="bg-white/[0.02] rounded-xl p-1 space-y-4 border border-white/5">
                            <div className="grid grid-cols-2 gap-1 p-1 bg-black/20 rounded-lg">
                                <button
                                    onClick={() => setIsIndividual(false)}
                                    className={`py-1.5 text-[10px] font-bold uppercase rounded-md transition-all ${!isIndividual ? 'bg-yellow-500/20 text-yellow-500 shadow-sm' : 'text-gray-500 hover:text-gray-300'}`}
                                >
                                    Masivo
                                </button>
                                <button
                                    onClick={() => setIsIndividual(true)}
                                    className={`py-1.5 text-[10px] font-bold uppercase rounded-md transition-all ${isIndividual ? 'bg-yellow-500/20 text-yellow-500 shadow-sm' : 'text-gray-500 hover:text-gray-300'}`}
                                >
                                    Individual
                                </button>
                            </div>

                            <div className="px-3 pb-3">
                                {!isIndividual ? (
                                    <div className="space-y-4">
                                        <div className="flex justify-between items-center">
                                            <label className="text-[10px] text-gray-400 font-mono tracking-wider">CANTIDAD</label>
                                            <span className="text-sm font-mono font-bold text-yellow-500">{spawnCount}</span>
                                        </div>
                                        <input
                                            type="range" min="1" max="10" value={spawnCount}
                                            onChange={(e) => setSpawnCount(parseInt(e.target.value))}
                                            className="w-full accent-yellow-500 h-1.5 bg-white/10 rounded-lg appearance-none cursor-pointer hover:bg-white/20 transition-colors"
                                        />
                                        <button
                                            onClick={() => sendGodAction("SPAWN_AGENT", { count: spawnCount })}
                                            className="w-full py-2.5 mt-2 bg-gradient-to-r from-yellow-500/20 to-orange-500/20 hover:from-yellow-500/30 hover:to-orange-500/30 text-yellow-500 border border-yellow-500/30 rounded-lg text-[10px] font-bold uppercase tracking-widest transition-all"
                                        >
                                            Manifestar Agentes
                                        </button>
                                    </div>
                                ) : (
                                    <div className="space-y-4">
                                        {Object.entries(pers).map(([key, value]) => (
                                            <div key={key} className="space-y-1.5">
                                                <div className="flex justify-between items-center">
                                                    <label className="text-[9px] text-gray-400 uppercase tracking-wider">{key}</label>
                                                    <span className="text-[9px] font-mono text-yellow-500">{value.toFixed(1)}</span>
                                                </div>
                                                <input
                                                    type="range" min="0" max="1" step="0.1" value={value}
                                                    onChange={(e) => setPers({ ...pers, [key]: parseFloat(e.target.value) })}
                                                    className="w-full accent-yellow-500 h-1 bg-white/10 rounded-lg appearance-none cursor-pointer"
                                                />
                                            </div>
                                        ))}
                                        <button
                                            onClick={() => sendGodAction("SPAWN_AGENT", { count: 1, config: { personality: pers } })}
                                            className="w-full py-2.5 mt-2 bg-gradient-to-r from-yellow-500/20 to-orange-500/20 hover:from-yellow-500/30 hover:to-orange-500/30 text-yellow-500 border border-yellow-500/30 rounded-lg text-[10px] font-bold uppercase tracking-widest transition-all"
                                        >
                                            Crear Individuo
                                        </button>
                                    </div>
                                )}
                            </div>
                        </div>
                    </Section>

                    {/* Control de Clima */}
                    <Section title="Manipulación Atmosférica">
                        <div className="grid grid-cols-2 gap-3">
                            <GodBtn icon={Sun} label="Soleado" onClick={() => sendGodAction("SET_WEATHER", { weather: "sunny" })} color="text-yellow-400 group-hover:drop-shadow-[0_0_8px_rgba(250,204,21,0.5)]" />
                            <GodBtn icon={CloudRain} label="Lluvia" onClick={() => sendGodAction("SET_WEATHER", { weather: "rainy" })} color="text-blue-400 group-hover:drop-shadow-[0_0_8px_rgba(96,165,250,0.5)]" />
                            <GodBtn icon={CloudLightning} label="Tormenta" onClick={() => sendGodAction("SET_WEATHER", { weather: "storm" })} color="text-purple-400" />
                            <GodBtn icon={Zap} label="Ola Calor" onClick={() => sendGodAction("SET_WEATHER", { weather: "orange-500" })} color="text-orange-500" />
                        </div>
                    </Section>

                    {/* Eventos Globales */}
                    <Section title="Eventos Cataclísmicos">
                        <div className="space-y-3">
                            <WideBtn icon={Skull} label="Desatar Plaga Global" onClick={() => sendGodAction("TRIGGER_EVENT", { event: "plague" })} color="bg-green-900/20 text-green-400 border-green-500/30 hover:bg-green-900/40 hover:border-green-500/50" />
                            <WideBtn icon={TrendingDown} label="Terremoto Masivo" onClick={() => sendGodAction("TRIGGER_EVENT", { event: "earthquake" })} color="bg-red-900/20 text-red-400 border-red-500/30 hover:bg-red-900/40 hover:border-red-500/50" />
                        </div>
                    </Section>

                    {/* Economía */}
                    <Section title="Ingeniería Económica">
                        <div className="grid grid-cols-2 gap-3">
                            <GodBtn icon={Coins} label="Inyección $" onClick={() => sendGodAction("MODIFY_ECONOMY", { sub_action: "inject_money" })} color="text-emerald-400" />
                            <GodBtn icon={TrendingDown} label="Colapso" onClick={() => sendGodAction("MODIFY_ECONOMY", { sub_action: "crash_market" })} color="text-red-500" />
                        </div>
                    </Section>

                    {/* Intervención Directa */}
                    <Section title="Juicio Individual">
                        {selectedAgentId ? (
                            <div className="space-y-3 bg-white/[0.02] p-3 rounded-xl border border-white/5">
                                <div className="flex items-center justify-between text-[10px] text-gray-400 font-mono tracking-widest border-b border-white/5 pb-2 mb-1">
                                    <span>OBJETIVO</span>
                                    <span className="text-white font-bold">{selectedAgentId}</span>
                                </div>
                                <div className="grid grid-cols-3 gap-2">
                                    <GodBtn icon={Heart} label="Sanar" onClick={() => sendGodAction("MODIFY_AGENT", { agent_id: selectedAgentId, effect: "heal" })} color="text-pink-400" />
                                    <GodBtn icon={Zap} label="Castigar" onClick={() => sendGodAction("MODIFY_AGENT", { agent_id: selectedAgentId, effect: "smite" })} color="text-red-500" />
                                    <GodBtn icon={Coins} label="Enriquecer" onClick={() => sendGodAction("MODIFY_AGENT", { agent_id: selectedAgentId, effect: "enrich" })} color="text-yellow-400" />
                                </div>
                            </div>
                        ) : (
                            <div className="flex flex-col items-center justify-center text-xs text-center text-gray-500 italic py-6 border border-dashed border-white/10 rounded-xl bg-black/20">
                                <span>Selecciona un agente en el mapa</span>
                                <span className="text-[10px] mt-1 opacity-50">para intervenir directamente</span>
                            </div>
                        )}
                    </Section>

                </div>
            </div>
        </motion.div>
    );
}

function Section({ title, children }: { title: string, children: React.ReactNode }) {
    return (
        <div className="space-y-4">
            <div className="flex items-center gap-4">
                <h3 className="text-[10px] font-bold text-gray-500 uppercase tracking-[0.2em] whitespace-nowrap">{title}</h3>
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
            className={`flex flex-col items-center justify-center p-4 rounded-xl bg-white/[0.03] border border-white/5 hover:bg-white/[0.08] hover:border-white/20 transition-all group active:scale-95 hover:shadow-lg`}
        >
            <Icon className={`w-5 h-5 mb-2 opacity-60 group-hover:opacity-100 transition-all duration-300 ${color}`} />
            <span className="text-[9px] font-bold text-gray-500 group-hover:text-gray-300 uppercase tracking-wider">{label}</span>
        </button>
    )
}

function WideBtn({ icon: Icon, label, onClick, color }: any) {
    return (
        <button
            onClick={onClick}
            className={`w-full flex items-center justify-center gap-3 p-3.5 rounded-xl border transition-all active:scale-95 group ${color}`}
        >
            <Icon className="w-4 h-4 opacity-70 group-hover:opacity-100" />
            <span className="text-[10px] font-bold uppercase tracking-[0.15em]">{label}</span>
        </button>
    )
}
