import { create } from 'zustand';
import { persist, PersistStorage } from 'zustand/middleware';
import { Agent } from '../types/agent'; // Importar la interfaz Agent

// ... (interfaces existentes)

interface GameState {
    isConnected: boolean;
    step: number;
    agents: Agent[];
    logs: any[];
    weather: string;
    lore: string;
    economy: any;
    mapa: any[][];
    misiones: { misiones_activas: any[], misiones_completadas: any[] };
    relationships: any[];
    speechBubbles: Record<string, { text: string; timestamp: number }>;
    selectedAgentId: string | null;
    civilizaciones: Record<string, any>;
    gruposDinamicos: Record<string, any>;
    propuestas: any[];
    relacionesGrupos: Record<string, number>;
    userScore: number;
    recentCompletedMissions: any[];
    showThoughts: boolean;
    historia: { historiador_id: string | null, entradas: any[], num_entradas: number };
    ranking: any[];
    instituciones: Record<string, any>;
    agentePoseidoId: string | null;
    socialFeed: any[];  // === RED SOCIAL OASIS ===
    socialMode: 'twitter' | 'reddit';
    setSocialMode: (mode: 'twitter' | 'reddit') => void;
    toggleThoughts: () => void;
    selectAgent: (agentId: string | null) => void;
    poseerAgente: (agentId: string) => Promise<boolean>;
    liberarAgente: () => Promise<boolean>;
    sendArchitectMessage: (message: string, agentId?: string) => Promise<string>;
    sendGodAction: (type: string, params: any) => Promise<boolean>;
    socket: WebSocket | null;
    bubbleCleanupInterval: ReturnType<typeof setInterval> | null;
    userId: string | null;
    isAuthenticated: boolean;
    username: string | null;
    login: (userId: string, username: string) => void;
    logout: () => void;
    connect: () => void;
    disconnect: () => void;
    apiHost: string;
    setApiHost: (host: string) => void;
}

interface PersistedState {
    isAuthenticated: boolean;
    userId: string | null;
    username: string | null;
    mapa: any[][];
    lore: string;
    apiHost: string;
    socialMode: 'twitter' | 'reddit';
}

const customStorage: PersistStorage<GameState> = {
    getItem: (name) => {
        const item = localStorage.getItem(name);
        if (item) {
            return JSON.parse(item);
        }
        return null;
    },
    setItem: (name, value) => {
        try {
            // Persistir campos de autenticación, el mapa y el lore
            const stateToPersist = {
                state: {
                    isAuthenticated: value.state.isAuthenticated,
                    userId: value.state.userId,
                    username: value.state.username,
                    mapa: value.state.mapa,
                    lore: value.state.lore,
                    apiHost: value.state.apiHost,
                    socialMode: value.state.socialMode || 'twitter'
                },
                version: value.version
            };
            localStorage.setItem(name, JSON.stringify(stateToPersist));
        } catch (error) {
            console.warn("⚠️ LocalStorage lleno, no se pudo persistir la sesión:", error);
        }
    },
    removeItem: (name) => {
        localStorage.removeItem(name);
    },
};

const useGameStore = create(
    persist<GameState>(
        (set, get) => ({
            isConnected: false,
            step: 0,
            agents: [],
            logs: [],
            weather: "sunny",
            lore: "",
            economy: {},
            mapa: [],
            misiones: { misiones_activas: [], misiones_completadas: [] },
            relationships: [],
            speechBubbles: {},
            selectedAgentId: null,
            civilizaciones: {},
            gruposDinamicos: {},
            propuestas: [],
            relacionesGrupos: {},
            userScore: 0,
            recentCompletedMissions: [],
            showThoughts: true,
            historia: { historiador_id: null, entradas: [], num_entradas: 0 },
            ranking: [],
            instituciones: {},
            agentePoseidoId: null,
            socialFeed: [],  // === RED SOCIAL OASIS ===
            socialMode: 'twitter',
            setSocialMode: (mode) => set({ socialMode: mode }),
            socket: null,
            bubbleCleanupInterval: null,
            userId: null,
            isAuthenticated: false,
            username: null,
            apiHost: 'api-mundoia.cuerpolibre.cl',

            setApiHost: (host) => {
                set({ apiHost: host });
                // Reconnect if already connected
                if (get().socket) {
                    get().disconnect();
                    setTimeout(() => get().connect(), 500);
                }
            },


            login: (userId, username) => set({ isAuthenticated: true, userId, username }),
            logout: () => {
                get().disconnect();
                set({ isAuthenticated: false, userId: null, username: null });
            },

            toggleThoughts: () => set((state) => ({ showThoughts: !state.showThoughts })),

            selectAgent: (agentId) => set({ selectedAgentId: agentId }),

            poseerAgente: async (agentId) => {
                const success = await get().sendGodAction("POSSESS_AGENT", { agent_id: agentId });
                if (success) set({ agentePoseidoId: agentId });
                return success;
            },

            liberarAgente: async () => {
                const success = await get().sendGodAction("POSSESS_AGENT", { agent_id: null });
                if (success) set({ agentePoseidoId: null });
                return success;
            },

            connect: () => {
                const { userId, socket } = get();
                if (!userId || socket) return;

                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                let host = window.location.host;
                
                // Si estamos en producción (dominio real)
                if (window.location.hostname === 'mundoia.cuerpolibre.cl') {
                    host = 'api-mundoia.cuerpolibre.cl';
                } 
                // Si estamos en desarrollo local (PC o Capacitor)
                else if (window.location.hostname === 'localhost' || window.location.hostname.includes('capacitor')) {
                    host = get().apiHost || 'api-mundoia.cuerpolibre.cl';
                }

                const wsUrl = `${protocol}//${host}/ws/${userId}`;
                console.log(`🔌 Intentando conectar a WebSocket en: ${wsUrl}`);
                const newSocket = new WebSocket(wsUrl);

                newSocket.onopen = () => {
                    console.log('WebSocket Connected');
                    set({ isConnected: true });
                };

                newSocket.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    
                    if (data.type === 'stats' || data.type === 'initial_state') {
                        console.log("📊 [WS] Recibiendo estado inicial/stats. Mapa presente:", !!data.mapa);
                        if (data.mapa) {
                            console.log(`🗺️ [WS] Dimensiones del mapa recibido: ${data.mapa.length}x${data.mapa[0]?.length || 0}`);
                        }
                    }

                    if (data.type === 'clear_logs') {
                        set({ logs: [], speechBubbles: {} });
                        return;
                    }

                    // Emitido por el backend justo antes de crear la nueva simulación en un reset.
                    // Limpia TODO el estado visual para que el frontend muestre una pizarra en blanco.
                    if (data.type === 'world_reset') {
                        set({
                            agents: [],
                            logs: [],
                            speechBubbles: {},
                            civilizaciones: {},
                            gruposDinamicos: {},
                            propuestas: [],
                            relacionesGrupos: {},
                            relationships: [],
                            instituciones: {},
                            misiones: { misiones_activas: [], misiones_completadas: [] },
                            historia: { historiador_id: null, entradas: [], num_entradas: 0 },
                            step: 0,
                            selectedAgentId: null,
                            mapa: [],
                            lore: "",
                        });
                        return;
                    }
                    if (data.type === 'initial_state' || data.type === 'stats') {
                        const updates: any = {
                            step: data.step,
                            economy: data.economy,
                            weather: data.weather,
                            civilizaciones: data.civilizaciones || {},
                            gruposDinamicos: data.grupos_dinamicos || {},
                            propuestas: data.propuestas || [],
                            relacionesGrupos: data.relaciones_grupos || {},
                            misiones: data.misiones || { misiones_activas: [], misiones_completadas: [] },
                            userScore: data.user_score || 0,
                            recentCompletedMissions: data.recent_completed_missions || [],
                            historia: data.historia || { historiador_id: null, entradas: [], num_entradas: 0 },
                            ranking: data.ranking || [],
                            instituciones: data.instituciones || {},
                            agentePoseidoId: data.agente_poseido_id || null,
                            socialFeed: data.socialFeed || [],  // === RED SOCIAL OASIS ===
                        };

                        if (data.mapa) {
                             updates.mapa = data.mapa;
                        }

                        if (data.lore) {
                             updates.lore = data.lore || "";
                        }
                        
                        // Solo actualizar logs si vienen en el mensaje (usualmente solo en initial_state)
                        if (data.logs && data.logs.length > 0) {
                            updates.logs = data.logs.map((l: any) => ({
                                step: l.step || l.paso || 0,
                                message: l.message || l.mensaje || "",
                                category: l.category || l.categoria || "info",
                                private_for: l.private_for || l.privado_para,
                                thought: l.thought || l.pensamiento,
                                timestamp: l.timestamp || Date.now()
                            }));
                        }

                        set(updates);
                    }

                    if (data.type === 'stats_delta') {
                        set((state) => {
                            const newStats: any = { step: data.step };
                            
                            const mergeRecursive = (target: any, delta: any) => {
                                const result = { ...target };
                                Object.keys(delta).forEach(key => {
                                    if (delta[key] !== null && typeof delta[key] === 'object' && !Array.isArray(delta[key]) && target[key]) {
                                        result[key] = mergeRecursive(target[key], delta[key]);
                                    } else {
                                        result[key] = delta[key];
                                    }
                                });
                                return result;
                            };

                            const mergedDelta = mergeRecursive(state, data.delta);
                            return { ...mergedDelta, step: data.step };
                        });
                    }

                    if (data.type === 'agent_update') {
                        set({ agents: data.agents });
                    }

                    if (data.type === 'agent_delta') {
                        set((state) => {
                            const newAgents = [...state.agents];
                            
                            // Procesar actualizaciones
                            if (data.updates) {
                                Object.keys(data.updates).forEach(agentId => {
                                    const index = newAgents.findIndex(a => a.id === agentId);
                                    const delta = data.updates[agentId];
                                    
                                    if (index !== -1) {
                                        // Merge profundo para planes, necesidades, etc.
                                        const mergeAgent = (target: any, source: any) => {
                                            Object.keys(source).forEach(key => {
                                                if (source[key] !== null && typeof source[key] === 'object' && !Array.isArray(source[key]) && target[key]) {
                                                    mergeAgent(target[key], source[key]);
                                                } else {
                                                    target[key] = source[key];
                                                }
                                            });
                                        };
                                        
                                        const updatedAgent = { ...newAgents[index] };
                                        mergeAgent(updatedAgent, delta);
                                        newAgents[index] = updatedAgent;
                                    } else {
                                        // Es un agente nuevo que no teníamos (posible spawn_agent)
                                        newAgents.push(delta as Agent);
                                    }
                                });
                            }
                            
                            // Procesar eliminaciones
                            if (data.removals && data.removals.length > 0) {
                                return {
                                    agents: newAgents.filter(a => !data.removals.includes(a.id))
                                };
                            }
                            
                            return { agents: newAgents };
                        });
                    }

                    if (data.type === 'relationships') {
                        set({ relationships: data.data });
                    }

                    // Actualizar historia si viene en cualquier mensaje
                    if (data.historia) {
                        console.log("Recibiendo historia:", JSON.stringify(data.historia));
                        set({ historia: data.historia });
                    }

                    if (data.type === 'log') {
                        set((state) => {
                            const newBubbles = { ...state.speechBubbles };
                            if (data.category === 'dialogo' && data.message.includes(':')) {
                                const match = data.message.match(/\[([^\]]+)\]\s*:/);
                                const agentId = match ? match[1].trim() : null;
                                const content = data.message.split(':').slice(1).join(':').trim();
                                if (agentId) {
                                    newBubbles[agentId] = { text: content, timestamp: Date.now() };
                                }
                            }
                            const now = Date.now();
                            Object.keys(newBubbles).forEach(key => {
                                if (now - newBubbles[key].timestamp > 20000) {
                                    delete newBubbles[key];
                                }
                            });

                            return {
                                logs: [
                                    ...state.logs,
                                    {
                                        step: data.step,
                                        message: data.message,
                                        category: data.category,
                                        private_for: data.private_for,
                                        thought: data.thought,
                                        timestamp: Date.now(),
                                    },
                                ].slice(-1000),
                                speechBubbles: newBubbles
                            };
                        });
                    }
                };

                newSocket.onclose = () => {
                    console.log('WebSocket Disconnected');
                    set({ isConnected: false, socket: null });
                };

                set({ socket: newSocket });

                // Limpiar speechBubbles expirados periódicamente (cada 2s),
                // las burbujas durarán 20 segundos antes de borrarse.
                const bubbleCleanupInterval = setInterval(() => {
                    const state = get();
                    const now = Date.now();
                    const bubbles = { ...state.speechBubbles };
                    let changed = false;
                    Object.keys(bubbles).forEach(key => {
                        if (now - bubbles[key].timestamp > 20000) {
                            delete bubbles[key];
                            changed = true;
                        }
                    });
                    if (changed) set({ speechBubbles: bubbles });
                }, 2000);
                set({ bubbleCleanupInterval });

            },

            disconnect: () => {
                const { socket, bubbleCleanupInterval } = get();
                if (bubbleCleanupInterval) {
                    clearInterval(bubbleCleanupInterval);
                }
                if (socket) {
                    socket.close();
                }
                set({ socket: null, isConnected: false, bubbleCleanupInterval: null });
            },

            sendArchitectMessage: async (message, agentId) => {
                const { userId } = get();
                if (!userId) {
                    console.error("❌ sendArchitectMessage: No userId found in store");
                    throw new Error("No userId found");
                }

                try {
                    const protocol = window.location.protocol;
                    let host = window.location.host;
                    
                    if (window.location.hostname === 'mundoia.cuerpolibre.cl') {
                        host = 'api-mundoia.cuerpolibre.cl';
                    } else if (window.location.hostname === 'localhost' || window.location.hostname.includes('capacitor')) {
                        host = get().apiHost || 'api-mundoia.cuerpolibre.cl';
                    }

                    const url = `${protocol}//${host}/game/god-mode/${userId}`;
                    const response = await fetch(url, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            action_type: 'ARCHITECT_MESSAGE',
                            params: {
                                mensaje: message,
                                agent_id: agentId
                            }
                        })
                    });
                    
                    const data = await response.json();
                    if (!response.ok) {
                        throw new Error(data.detail || data.message || 'Failed to send message');
                    }
                    return data.response; // Devolver la respuesta del agente
                } catch (error) {
                    console.error('Error sending architect message:', error);
                    throw error;
                }
            },

            sendGodAction: async (type, params) => {
                const { userId } = get();
                if (!userId) return false;

                try {
                    const protocol = window.location.protocol;
                    let host = window.location.host;
                    
                    if (window.location.hostname === 'mundoia.cuerpolibre.cl') {
                        host = 'api-mundoia.cuerpolibre.cl';
                    } else if (window.location.hostname === 'localhost' || window.location.hostname.includes('capacitor')) {
                        host = get().apiHost || 'api-mundoia.cuerpolibre.cl';
                    }

                    const response = await fetch(`${protocol}//${host}/game/god-mode/${userId}`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            action_type: type,
                            params: params
                        })
                    });
                    return response.ok;
                } catch (error) {
                    console.error("Error ejecutando acción divina:", error);
                    return false;
                }
            }
        }),
        {
            name: 'mundoia-auth',
            storage: customStorage,
        }
    )
);

export default useGameStore;
