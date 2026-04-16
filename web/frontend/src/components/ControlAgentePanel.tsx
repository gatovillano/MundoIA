"use client";

import React, { useState, useMemo } from "react";
import { 
    MessageSquare, Send, Move, Vote, Gavel, 
    Hand, Users, Construction, X, ChevronUp, 
    ChevronDown, ChevronLeft, ChevronRight,
    Users2, Globe, Ghost, Heart, Zap, Moon,
    Coffee, Compass, Crosshair, Book, Microscope,
    Shield, TrendingUp, Handshake, Play, Trash2,
    Search, Code, Layout, Hammer, Sword, GraduationCap
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import useGameStore from "@/store/useGameStore";
import { Agent } from "@/types/agent";

interface ActionDefinition {
    id: string;
    name: string;
    description: string;
    icon: any;
    category: 'survival' | 'social' | 'construction' | 'knowledge' | 'political' | 'technical' | 'movement' | 'conflict';
    needsArgs?: boolean;
    argPlaceholder?: string;
    defaultArgs?: any;
}

const ALL_ACTIONS: ActionDefinition[] = [
    // SURVIVAL
    { id: 'comer', name: 'Comer', description: 'Consumir alimentos del inventario', icon: Coffee, category: 'survival' },
    { id: 'descansar', name: 'Descansar', description: 'Reponer energía (descanso)', icon: Moon, category: 'survival' },
    { id: 'recolectar', name: 'Recolectar', description: 'Extraer recursos del terreno', icon: Hand, category: 'survival' },
    { id: 'cultivar', name: 'Cultivar', description: 'Plantar y cosechar en una parcela', icon: Zap, category: 'survival' },
    { id: 'cazar', name: 'Cazar', description: 'Obtener comida mediante la caza', icon: Sword, category: 'survival' },
    { id: 'curarse', name: 'Curarse', description: 'Usar medicinas para recuperar salud', icon: Heart, category: 'survival' },
    
    // SOCIAL
    { id: 'decir', name: 'Comunicar', description: 'Enviar un mensaje a otros', icon: MessageSquare, category: 'social', needsArgs: true, argPlaceholder: 'Tu mensaje...', defaultArgs: { mensaje: "" } },
    { id: 'socializar', name: 'Socializar', description: 'Mejorar relación con un agente', icon: Handshake, category: 'social', needsArgs: true, argPlaceholder: 'ID del agente...', defaultArgs: { otro_agente_id: "" } },
    { id: 'formar_alianza', name: 'Alianza', description: 'Firmar pacto de cooperación', icon: Users, category: 'social', needsArgs: true, argPlaceholder: 'ID del socio...', defaultArgs: { otro_agente_id: "" } },
    { id: 'opinar', name: 'Opinar', description: 'Hablar en una asamblea activa', icon: MessageSquare, category: 'social', needsArgs: true, argPlaceholder: 'Tu opinión...', defaultArgs: { mensaje: "" } },
    { id: 'compartir_conocimiento', name: 'Enseñar', description: 'Compartir saberes con otro', icon: Book, category: 'social', needsArgs: true, argPlaceholder: 'Conocimiento e ID...', defaultArgs: { conocimiento: "", destinatario_id: "" } },
    
    // CONSTRUCTION & ECONOMY
    { id: 'construir', name: 'Construir', description: 'Erigir estructuras (Granja, Hospital...)', icon: Construction, category: 'construction', needsArgs: true, argPlaceholder: 'Tipo de edificio...', defaultArgs: { tipo: "Granja" } },
    { id: 'invertir', name: 'Invertir', description: 'Colocar MC en el mercado', icon: TrendingUp, category: 'construction', needsArgs: true, argPlaceholder: 'Monto...', defaultArgs: { monto: 10 } },
    { id: 'comerciar', name: 'Comerciar', description: 'Intercambiar con mercaderes', icon: Wallet, category: 'construction' },
    { id: 'consultar_mercado', name: 'Ver Precios', description: 'Consultar valor de recursos', icon: Search, category: 'construction' },
    
    // KNOWLEDGE
    { id: 'investigar', name: 'Investigar', description: 'Desarrollar teorías sobre un tema', icon: Microscope, category: 'knowledge', needsArgs: true, argPlaceholder: 'Tema...', defaultArgs: { tema: "medicina" } },
    { id: 'estudiar', name: 'Estudiar', description: 'Aprender en la Universidad', icon: GraduationCap, category: 'knowledge', needsArgs: true, argPlaceholder: 'Profesión...', defaultArgs: { profesion: "Médico" } },
    { id: 'reflexionar', name: 'Reflexionar', description: 'Meditar para evolucionar el Alma', icon: Brain, category: 'knowledge', needsArgs: true, argPlaceholder: 'Tema...', defaultArgs: { tema: "propósito" } },
    { id: 'web_search', name: 'Web Search', description: 'Buscar información real en Internet', icon: Globe, category: 'knowledge', needsArgs: true, argPlaceholder: 'Query de búsqueda...', defaultArgs: { query: "" } },
    { id: 'scrapear_url', name: 'Scrapear URL', description: 'Extraer contenido de una web', icon: Layout, category: 'knowledge', needsArgs: true, argPlaceholder: 'URL...', defaultArgs: { url: "" } },
    
    // POLITICAL
    { id: 'fundar_grupo', name: 'Fundar Grupo', description: 'Crear una nueva facción', icon: Users2, category: 'political', needsArgs: true, argPlaceholder: 'Nombre y Desc...', defaultArgs: { nombre: "", descripcion: "" } },
    { id: 'proponer_ley', name: 'Proponer Ley', description: 'Sugerir un nuevo decreto global', icon: Gavel, category: 'political', needsArgs: true, argPlaceholder: 'Título y Desc...', defaultArgs: { titulo: "", descripcion: "" } },
    { id: 'votar', name: 'Votar', description: 'Participar en votación de ley', icon: Vote, category: 'political', needsArgs: true, argPlaceholder: 'ID y Voto (si/no)...', defaultArgs: { propuesta_id: "", voto: "si" } },
    { id: 'fundar_institucion', name: 'Institución', description: 'Fundar organización formal', icon: Shield, category: 'political', needsArgs: true, argPlaceholder: 'Nombre y Tipo...', defaultArgs: { nombre: "", tipo: "Ciencia" } },
    
    // TECHNICAL
    { id: 'ejecutar_codigo', name: 'Run Code', description: 'Ejecutar script Python puntual', icon: Code, category: 'technical', needsArgs: true, argPlaceholder: 'Código...', defaultArgs: { codigo: "" } },
    { id: 'crear_app', name: 'Crear App', description: 'Desarrollar app persistente', icon: Layout, category: 'technical', needsArgs: true, argPlaceholder: 'Nombre y Código...', defaultArgs: { nombre: "", codigo: "" } },
    { id: 'crear_habilidad', name: 'Nueva Skill', description: 'Extender capacidades permanentes', icon: Hammer, category: 'technical', needsArgs: true, argPlaceholder: 'Nombre y Lógica...', defaultArgs: { nombre: "", descripcion: "", codigo: "" } },
    
    // MOVEMENT
    { id: 'mover', name: 'Mover', description: 'Desplazarse a coordenadas (x,y)', icon: Move, category: 'movement', needsArgs: true, argPlaceholder: 'x, y...', defaultArgs: { x: 0, y: 0 } },
    { id: 'explorar', name: 'Explorar', description: 'Viajar a lo desconocido', icon: Compass, category: 'movement' },
    
    // CONFLICT
    { id: 'atacar', name: 'Atacar', description: 'Iniciar combate con un agente', icon: Swords, category: 'conflict', needsArgs: true, argPlaceholder: 'ID del objetivo...', defaultArgs: { otro_agente_id: "" } },
    { id: 'competir', name: 'Competir', description: 'Rivalidad por recursos/estatus', icon: Target, category: 'conflict', needsArgs: true, argPlaceholder: 'ID del rival...', defaultArgs: { otro_agente_id: "" } },
];

const CATEGORIES = [
    { id: 'survival', label: 'Vital', icon: Heart },
    { id: 'social', label: 'Social', icon: Users },
    { id: 'construction', label: 'Eco', icon: Construction },
    { id: 'knowledge', label: 'Saber', icon: Microscope },
    { id: 'political', label: 'Leyes', icon: Gavel },
    { id: 'technical', label: 'Dev', icon: Code },
    { id: 'movement', label: 'Move', icon: Compass },
    { id: 'conflict', label: 'War', icon: Sword },
];

export default function ControlAgentePanel({ agent, onClose }: { agent: Agent, onClose: () => void }) {
    const { sendGodAction } = useGameStore();
    const [queue, setQueue] = useState<any[]>([]);
    const [activeCat, setActiveCat] = useState('survival');
    const [sending, setSending] = useState(false);

    const filteredActions = useMemo(() => {
        return ALL_ACTIONS.filter(a => a.category === activeCat);
    }, [activeCat]);

    const addToQueue = (action: ActionDefinition) => {
        if (queue.length >= 3) return;
        
        let args = action.defaultArgs || {};
        if (action.needsArgs) {
            const input = prompt(`Configura argumentos para ${action.name}:\n${action.argPlaceholder}`, JSON.stringify(args));
            if (input === null) return;
            try {
                // Intentar parsear como JSON, si falla, usar como string para el campo principal
                args = JSON.parse(input);
            } catch (e) {
                // Fallback: si es un string simple y la acción tiene un campo principal
                if (action.id === 'decir' || action.id === 'opinar' || action.id === 'reflexionar' || action.id === 'web_search') {
                    const key = action.id === 'web_search' ? 'query' : (action.id === 'reflexionar' ? 'tema' : 'mensaje');
                    args = { ...args, [key]: input };
                } else if (action.id === 'mover') {
                    const parts = input.split(',').map(p => parseInt(p.trim()));
                    if (parts.length === 2) args = { x: parts[0], y: parts[1] };
                } else {
                    args = input;
                }
            }
        }

        setQueue([...queue, { 
            tipo: action.id, 
            nombre: action.name.toUpperCase(), 
            parametros: args,
            argumentos: args, // Por compatibilidad con ambos formatos
            icon: action.icon
        }]);
    };

    const removeFromQueue = (index: number) => {
        setQueue(queue.filter((_, i) => i !== index));
    };

    const sendPlan = async () => {
        if (queue.length === 0) return;
        setSending(true);
        
        // El backend espera una lista de acciones en 'actions'
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
        setSending(false);
    };

    return (
        <div className="flex flex-col h-full bg-[#0a0b10] text-white">
            {/* Header del Panel de Control */}
            <div className="p-4 border-b border-white/10 flex items-center justify-between bg-white/[0.02]">
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-indigo-500/20 rounded-xl text-indigo-400">
                        <Zap className="w-5 h-5 animate-pulse" />
                    </div>
                    <div>
                        <h3 className="text-sm font-black uppercase tracking-widest leading-none mb-1">Control de Turno</h3>
                        <p className="text-[10px] text-gray-500 font-bold uppercase tracking-tighter">
                            Agente {agent.id.substring(0, 6)}
                        </p>
                    </div>
                </div>
                <button onClick={onClose} className="p-2 hover:bg-white/5 rounded-full text-gray-500">
                    <X className="w-5 h-5" />
                </button>
            </div>

            {/* Cola de Acciones (Max 3) */}
            <div className="p-4 bg-black/40 border-b border-white/5">
                <div className="flex justify-between items-center mb-3">
                    <span className="text-[10px] font-black uppercase tracking-widest text-indigo-400">Cola de Ejecución ({queue.length}/3)</span>
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
                                    item ? 'bg-indigo-500/10 border-indigo-500/50' : 'bg-white/[0.02] border-white/5 opacity-40'
                                }`}
                            >
                                {item ? (
                                    <>
                                        <button 
                                            onClick={() => removeFromQueue(idx)}
                                            className="absolute -top-1.5 -right-1.5 p-1 bg-red-500 text-white rounded-full hover:scale-110 active:scale-90 transition-transform shadow-lg"
                                        >
                                            <X className="w-2.5 h-2.5" />
                                        </button>
                                        <item.icon className="w-4 h-4 text-indigo-400 mb-1" />
                                        <span className="text-[9px] font-black uppercase tracking-tighter truncate w-full">{item.nombre}</span>
                                    </>
                                ) : (
                                    <span className="text-[8px] font-bold text-gray-600 uppercase">Paso {idx + 1}</span>
                                )}
                            </div>
                        );
                    })}
                </div>
            </div>

            {/* Selector de Categorías */}
            <div className="flex gap-1 overflow-x-auto p-3 bg-black/20 custom-scrollbar-hide border-b border-white/5">
                {CATEGORIES.map((cat) => (
                    <button
                        key={cat.id}
                        onClick={() => setActiveCat(cat.id)}
                        className={`flex flex-col items-center justify-center min-w-[56px] h-14 rounded-xl transition-all gap-1.5 border ${
                            activeCat === cat.id 
                            ? 'bg-indigo-500 text-white border-indigo-400 shadow-lg shadow-indigo-500/20' 
                            : 'bg-white/[0.03] text-gray-500 border-white/5 hover:bg-white/5'
                        }`}
                    >
                        <cat.icon className="w-4 h-4" />
                        <span className="text-[8px] font-black uppercase tracking-tighter">{cat.label}</span>
                    </button>
                ))}
            </div>

            {/* Lista de Acciones Filtradas */}
            <div className="flex-1 overflow-y-auto p-4 custom-scrollbar space-y-2">
                {filteredActions.map((action) => (
                    <button
                        key={action.id}
                        onClick={() => addToQueue(action)}
                        disabled={queue.length >= 3}
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

            {/* Footer con Botón de Envío */}
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
                            Dictar Plan de Turno
                        </>
                    )}
                </button>
                <p className="text-[9px] text-gray-600 text-center mt-3 uppercase font-bold tracking-widest">
                    El agente integrará estas acciones en su narrativa
                </p>
            </div>
        </div>
    );
}
