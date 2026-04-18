"use client";

import React, { useState, useMemo } from "react";
import { 
    MessageSquare, Send, Move, Vote, Gavel, 
    Hand, Users, Construction, X, ChevronUp, 
    ChevronDown, ChevronLeft, ChevronRight,
    Users2, Globe, Ghost, Heart, Zap, Moon,
    Coffee, Compass, Crosshair, Book, Microscope,
    Shield, TrendingUp, Handshake, Play, Trash2,
    Search, Code, Layout, Hammer, Sword, GraduationCap,
    Target, Wallet, Swords, Brain
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import useGameStore from "@/store/useGameStore";
import { Agent } from "@/types/agent";

interface ActionOption {
    label: string;
    value: any;
}

interface ActionDefinition {
    id: string;
    name: string;
    description: string;
    icon: any;
    category: 'survival' | 'social' | 'construction' | 'knowledge' | 'political' | 'technical' | 'movement' | 'conflict';
    options?: ActionOption[];
    paramName?: string;
}

const ALL_ACTIONS: ActionDefinition[] = [
    // SURVIVAL
    { id: 'comer', name: 'Comer', description: 'Consumir alimentos', icon: Coffee, category: 'survival' },
    { id: 'descansar', name: 'Descansar', description: 'Reponer energía', icon: Moon, category: 'survival' },
    { id: 'recolectar', name: 'Recolectar', description: 'Extraer recursos', icon: Hand, category: 'survival' },
    { id: 'cultivar', name: 'Cultivar', description: 'Plantar/Cosechar', icon: Zap, category: 'survival' },
    { id: 'cazar', name: 'Cazar', description: 'Obtener comida', icon: Sword, category: 'survival' },
    { id: 'curarse', name: 'Curarse', description: 'Usar medicinas', icon: Heart, category: 'survival' },
    
    // SOCIAL (Sin inputs, el LLM decide el mensaje)
    { id: 'decir', name: 'Comunicar', description: 'Hablar con otros', icon: MessageSquare, category: 'social' },
    { id: 'socializar', name: 'Socializar', description: 'Mejorar relación', icon: Handshake, category: 'social' },
    { id: 'formar_alianza', name: 'Alianza', description: 'Pacto cooperación', icon: Users, category: 'social' },
    { id: 'opinar', name: 'Opinar', description: 'Hablar en asamblea', icon: MessageSquare, category: 'social' },
    
    // CONSTRUCTION & ECONOMY
    { 
        id: 'construir', name: 'Construir', description: 'Erigir estructura', icon: Construction, category: 'construction',
        paramName: 'tipo',
        options: [
            { label: 'Granja', value: 'Granja' },
            { label: 'Hospital', value: 'Hospital' },
            { label: 'Universidad', value: 'Universidad' },
            { label: 'Mina', value: 'Mina' },
            { label: 'C. Descanso', value: 'Centro de Descanso' },
            { label: 'C. Comunitario', value: 'Centro Comunitario' }
        ]
    },
    { id: 'comerciar', name: 'Comerciar', description: 'Intercambiar recursos', icon: Wallet, category: 'construction' },
    { id: 'consultar_mercado', name: 'Ver Precios', description: 'Consultar mercado', icon: Search, category: 'construction' },
    
    // KNOWLEDGE
    { 
        id: 'investigar', name: 'Investigar', description: 'Desarrollar teorías', icon: Microscope, category: 'knowledge',
        paramName: 'tema',
        options: [
            { label: 'Medicina', value: 'medicina' },
            { label: 'Ingeniería', value: 'ingeniería' },
            { label: 'Agricultura', value: 'agricultura' },
            { label: 'I.A.', value: 'inteligencia artificial' },
            { label: 'Astronomía', value: 'astronomía' }
        ]
    },
    { 
        id: 'estudiar', name: 'Estudiar', description: 'Aprender profesión', icon: GraduationCap, category: 'knowledge',
        paramName: 'profesion',
        options: [
            { label: 'Médico', value: 'Médico' },
            { label: 'Ingeniero', value: 'Ingeniero' },
            { label: 'Científico', value: 'Científico' },
            { label: 'Artista', value: 'Artista' },
            { label: 'Político', value: 'Político' },
            { label: 'Militar', value: 'Militar' }
        ]
    },
    { id: 'reflexionar', name: 'Reflexionar', description: 'Meditar sobre el alma', icon: Brain, category: 'knowledge' },
    
    // POLITICAL
    { id: 'fundar_grupo', name: 'Fundar Grupo', description: 'Crear facción', icon: Users2, category: 'political' },
    { 
        id: 'votar', name: 'Votar', description: 'Votación de ley', icon: Vote, category: 'political',
        paramName: 'voto',
        options: [
            { label: 'A FAVOR', value: 'si' },
            { label: 'EN CONTRA', value: 'no' }
        ]
    },
    { 
        id: 'fundar_institucion', name: 'Institución', description: 'Fundar organización', icon: Shield, category: 'political',
        paramName: 'tipo',
        options: [
            { label: 'Educativa', value: 'Educativa' },
            { label: 'Sanitaria', value: 'Sanitaria' },
            { label: 'Científica', value: 'Científica' },
            { label: 'Justicia', value: 'Justicia' }
        ]
    },
    
    // MOVEMENT
    { 
        id: 'mover', name: 'Mover', description: 'Desplazarse', icon: Move, category: 'movement',
        paramName: 'direccion',
        options: [
            { label: 'NORTE (↑)', value: 'norte' },
            { label: 'SUR (↓)', value: 'sur' },
            { label: 'ESTE (→)', value: 'este' },
            { label: 'OESTE (←)', value: 'oeste' },
            { label: 'CENTRO', value: 'centro' }
        ]
    },
    { id: 'explorar', name: 'Explorar', description: 'Viajar lejos', icon: Compass, category: 'movement' },
    
    // SOCIAL NETWORK
    { id: 'social_post', name: 'Crear Post', description: 'Publicar pensamiento', icon: Send, category: 'social_net' },
    { id: 'social_comment', name: 'Comentar', description: 'Responder a tendencia', icon: MessageSquare, category: 'social_net' },
    { id: 'social_like', name: 'Like', description: 'Reaccionar positivamente', icon: Heart, category: 'social_net' },
    
    // CONFLICT
    { id: 'atacar', name: 'Atacar', description: 'Combatir rival', icon: Sword, category: 'conflict' },
    { id: 'competir', name: 'Competir', description: 'Rivalidad recursos', icon: Target, category: 'conflict' },
];

const CATEGORIES = [
    { id: 'survival', label: 'Vital', icon: Heart },
    { id: 'social', label: 'Social', icon: Users },
    { id: 'construction', label: 'Eco', icon: Construction },
    { id: 'knowledge', label: 'Saber', icon: Microscope },
    { id: 'political', label: 'Leyes', icon: Gavel },
    { id: 'movement', label: 'Move', icon: Compass },
    { id: 'social_net', label: 'Social', icon: Globe },
    { id: 'conflict', label: 'War', icon: Sword },
];

export default function ControlAgentePanel({ agent, onClose }: { agent: Agent, onClose: () => void }) {
    const { sendGodAction, modoControlTotal } = useGameStore();
    const [queue, setQueue] = useState<any[]>([]);
    const [activeCat, setActiveCat] = useState('survival');
    const [sending, setSending] = useState(false);
    const [selectingArgsFor, setSelectingArgsFor] = useState<ActionDefinition | null>(null);

    const filteredActions = useMemo(() => {
        return ALL_ACTIONS.filter(a => a.category === activeCat);
    }, [activeCat]);

    const addToQueue = (action: ActionDefinition, paramValue?: any) => {
        if (queue.length >= 3) return;
        
        // Si la acción tiene opciones y no se ha pasado un valor, abrir submenú
        if (action.options && paramValue === undefined) {
            setSelectingArgsFor(action);
            return;
        }

        const args = action.paramName && paramValue !== undefined 
            ? { [action.paramName]: paramValue } 
            : {};

        setQueue([...queue, { 
            tipo: action.id, 
            nombre: action.name.toUpperCase(), 
            parametros: args,
            argumentos: args,
            icon: action.icon,
            displayValue: paramValue
        }]);
        
        setSelectingArgsFor(null);
    };

    const removeFromQueue = (index: number) => {
        setQueue(queue.filter((_, i) => i !== index));
    };

    const sendPlan = async () => {
        if (queue.length === 0) return;
        setSending(true);
        
        if (modoControlTotal) {
            // En modo Control Total, ejecutar inmediatamente una tras otra
            for (const q of queue) {
                await sendGodAction("AGENT_EXECUTE_ACTION", {
                    agent_id: agent.id,
                    action: q.tipo,
                    payload: q.parametros
                });
            }
            setQueue([]);
            onClose();
        } else {
            // En modo Observador, enviar el plan para el próximo turno
            const success = await sendGodAction("SET_CONTROL_ACTIONS", {
                agent_id: agent.id,
                actions: queue.map(q => ({
                    tipo: q.tipo,
                    nombre: q.nombre,
                    parametros: q.parametros,
                    argumentos: q.argumentos
                }))
            });

            if (success) {
                setQueue([]);
                onClose();
            } else {
                alert("Error al enviar el plan de control.");
            }
        }
        setSending(false);
    };

    return (
        <div className="flex flex-col h-full bg-[#0a0b10] text-white">
            {/* Header */}
            <div className="p-4 border-b border-white/10 flex items-center justify-between bg-white/[0.02]">
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-indigo-500/20 rounded-xl text-indigo-400">
                        <Zap className="w-5 h-5 animate-pulse" />
                    </div>
                    <div>
                        <h3 className="text-sm font-black uppercase tracking-widest leading-none mb-1">Control de Turno</h3>
                        <p className="text-[10px] text-gray-500 font-bold uppercase tracking-tighter">
                            {agent.identidad?.nombre || agent.id.substring(0, 8)}
                        </p>
                    </div>
                </div>
                <button onClick={onClose} className="p-2 hover:bg-white/5 rounded-full text-gray-500">
                    <X className="w-5 h-5" />
                </button>
            </div>

            {/* Queue Visualization */}
            <div className="p-4 bg-black/40 border-b border-white/5">
                <div className="flex justify-between items-center mb-3">
                    <span className="text-[10px] font-black uppercase tracking-widest text-indigo-400">Secuencia de Acciones ({queue.length}/3)</span>
                    {queue.length > 0 && (
                        <button onClick={() => setQueue([])} className="text-[9px] text-gray-500 hover:text-red-400 uppercase font-bold transition-colors">Limpiar</button>
                    )}
                </div>
                <div className="grid grid-cols-3 gap-2">
                    {[0, 1, 2].map((idx) => {
                        const item = queue[idx];
                        return (
                            <div 
                                key={idx} 
                                className={`h-16 rounded-xl border-2 border-dashed transition-all flex flex-col items-center justify-center p-2 text-center relative ${
                                    item ? 'bg-indigo-500/10 border-indigo-500/50 shadow-lg shadow-indigo-500/5' : 'bg-white/[0.02] border-white/5 opacity-40'
                                }`}
                            >
                                {item ? (
                                    <>
                                        <button 
                                            onClick={() => removeFromQueue(idx)}
                                            className="absolute -top-1.5 -right-1.5 p-1 bg-red-500 text-white rounded-full hover:scale-110 active:scale-90 transition-transform shadow-lg z-10"
                                        >
                                            <X className="w-2.5 h-2.5" />
                                        </button>
                                        <item.icon className="w-4 h-4 text-indigo-400 mb-1" />
                                        <span className="text-[9px] font-black uppercase tracking-tighter truncate w-full leading-none">{item.nombre}</span>
                                        {item.displayValue && (
                                            <span className="text-[7px] text-gray-400 uppercase font-bold truncate w-full mt-0.5">{item.displayValue}</span>
                                        )}
                                    </>
                                ) : (
                                    <span className="text-[8px] font-bold text-gray-600 uppercase">Paso {idx + 1}</span>
                                )}
                            </div>
                        );
                    })}
                </div>
            </div>

            {/* Submenu Overlay for options */}
            <AnimatePresence>
                {selectingArgsFor && (
                    <motion.div 
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: 10 }}
                        className="p-4 bg-indigo-600/10 border-b border-indigo-500/30"
                    >
                        <div className="flex justify-between items-center mb-3">
                            <span className="text-[10px] font-black uppercase tracking-widest text-white">Elegir {selectingArgsFor.name}:</span>
                            <button onClick={() => setSelectingArgsFor(null)} className="text-[9px] text-white/50 hover:text-white uppercase font-bold">Cancelar</button>
                        </div>
                        <div className="flex flex-wrap gap-2">
                            {selectingArgsFor.options?.map((opt) => (
                                <button
                                    key={opt.label}
                                    onClick={() => addToQueue(selectingArgsFor, opt.value)}
                                    className="px-3 py-2 bg-indigo-500 hover:bg-indigo-400 text-white rounded-lg text-[10px] font-black uppercase tracking-tighter transition-all active:scale-95 shadow-lg shadow-indigo-500/20"
                                >
                                    {opt.label}
                                </button>
                            ))}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Category Switcher */}
            <div className="flex gap-1 overflow-x-auto p-3 bg-black/20 custom-scrollbar-hide border-b border-white/5">
                {CATEGORIES.map((cat) => (
                    <button
                        key={cat.id}
                        onClick={() => { setActiveCat(cat.id); setSelectingArgsFor(null); }}
                        className={`flex flex-col items-center justify-center min-w-[56px] h-14 rounded-xl transition-all gap-1.5 border ${
                            activeCat === cat.id 
                            ? 'bg-indigo-500 text-white border-indigo-400 shadow-lg shadow-indigo-500/20 scale-105 z-10' 
                            : 'bg-white/[0.03] text-gray-500 border-white/5 hover:bg-white/5'
                        }`}
                    >
                        <cat.icon className="w-4 h-4" />
                        <span className="text-[8px] font-black uppercase tracking-tighter">{cat.label}</span>
                    </button>
                ))}
            </div>

            {/* Actions List */}
            <div className="flex-1 overflow-y-auto p-4 custom-scrollbar space-y-2">
                {filteredActions.map((action) => (
                    <button
                        key={action.id}
                        onClick={() => addToQueue(action)}
                        disabled={queue.length >= 3 || (selectingArgsFor !== null && selectingArgsFor.id !== action.id)}
                        className="w-full flex items-center gap-4 p-3 bg-white/[0.03] hover:bg-white/[0.07] border border-white/5 rounded-2xl transition-all group active:scale-[0.98] disabled:opacity-30"
                    >
                        <div className="p-2.5 bg-white/5 rounded-xl group-hover:bg-indigo-500/20 group-hover:text-indigo-400 transition-all">
                            <action.icon className="w-4 h-4" />
                        </div>
                        <div className="text-left">
                            <h4 className="text-[11px] font-black text-white uppercase tracking-wider mb-0.5">{action.name}</h4>
                            <p className="text-[9px] text-gray-500 leading-tight">{action.description}</p>
                        </div>
                    </button>
                ))}
            </div>

            {/* Footer */}
            <div className="p-4 border-t border-white/10 bg-white/[0.02]">
                <button
                    onClick={sendPlan}
                    disabled={queue.length === 0 || sending}
                    className="w-full py-4 bg-indigo-500 hover:bg-indigo-400 text-white font-black uppercase tracking-[0.2em] rounded-2xl shadow-xl shadow-indigo-500/20 transition-all active:scale-[0.98] disabled:opacity-50 disabled:grayscale flex items-center justify-center gap-3"
                >
                    {sending ? (
                        <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    ) : (
                        <>
                            <Play className="w-4 h-4 fill-current" />
                            EJECUTAR PLAN
                        </>
                    )}
                </button>
                <p className="text-[9px] text-gray-600 text-center mt-3 uppercase font-bold tracking-widest leading-relaxed">
                    El agente usará su IA para realizar estas acciones<br/>según su personalidad y contexto actual
                </p>
            </div>
        </div>
    );
}
