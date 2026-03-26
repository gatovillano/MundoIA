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
    toggleThoughts: () => void;
    selectAgent: (agentId: string | null) => void;
    sendArchitectMessage: (message: string, agentId?: string) => Promise<void>;
    sendGodAction: (type: string, params: any) => Promise<boolean>;
    socket: WebSocket | null;
    userId: string | null;
    isAuthenticated: boolean;
    username: string | null;
    login: (userId: string, username: string) => void;
    logout: () => void;
    connect: () => void;
    disconnect: () => void;
}

interface PersistedState {
    isAuthenticated: boolean;
    userId: string | null;
    username: string | null;
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
            // Solo persistir campos de autenticación para evitar saturar localStorage
            const stateToPersist = {
                state: {
                    isAuthenticated: value.state.isAuthenticated,
                    userId: value.state.userId,
                    username: value.state.username
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
            socket: null,
            userId: null,
            isAuthenticated: false,
            username: null,

            login: (userId, username) => set({ isAuthenticated: true, userId, username }),
            logout: () => {
                get().disconnect();
                set({ isAuthenticated: false, userId: null, username: null });
            },

            toggleThoughts: () => set((state) => ({ showThoughts: !state.showThoughts })),

            selectAgent: (agentId) => set({ selectedAgentId: agentId }),

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
                    // Si el usuario ya definió una IP en el localStorage (para celular), la usamos.
                    // Si no, por defecto usamos localhost:8005 para desarrollo en PC.
                    const customHost = localStorage.getItem('MUNDOIA_API_HOST') || 'localhost:8005';
                    host = customHost;
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
                        });
                        return;
                    }
                    if (data.type === 'initial_state' || data.type === 'stats') {
                        set({
                            step: data.step,
                            economy: data.economy,
                            mapa: data.mapa,
                            weather: data.weather,
                            lore: data.lore || "",
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
                            // Sincronizar logs históricos al conectar o reconectar
                            logs: (data.logs && data.logs.length > 0) ? data.logs.map((l: any) => ({
                                step: l.step || l.paso || 0,
                                message: l.message || l.mensaje || "",
                                category: l.category || l.categoria || "info",
                                private_for: l.private_for || l.privado_para,
                                thought: l.thought || l.pensamiento,
                                timestamp: l.timestamp || Date.now()
                            })) : get().logs
                        });
                    }

                    if (data.type === 'agent_update') {
                        set({ agents: data.agents });
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
                                const match = data.message.match(/\[(A-?\d+)\]/);
                                const agentId = match ? match[1] : null;
                                const content = data.message.split(':').slice(1).join(':').trim();
                                if (agentId) {
                                    newBubbles[agentId] = { text: content, timestamp: Date.now() };
                                }
                            }

                            const now = Date.now();
                            Object.keys(newBubbles).forEach(key => {
                                if (now - newBubbles[key].timestamp > 5000) {
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
            },

            disconnect: () => {
                const { socket } = get();
                if (socket) {
                    socket.close();
                    set({ socket: null, isConnected: false });
                }
            },

            sendArchitectMessage: async (message, agentId) => {
                const { userId } = get();
                if (!userId) {
                    console.error("❌ sendArchitectMessage: No userId found in store");
                    return;
                }

                try {
                    const protocol = window.location.protocol;
                    let host = window.location.host;
                    
                    if (window.location.hostname === 'mundoia.cuerpolibre.cl') {
                        host = 'api-mundoia.cuerpolibre.cl';
                    } else if (window.location.hostname === 'localhost' || window.location.hostname.includes('capacitor')) {
                        host = localStorage.getItem('MUNDOIA_API_HOST') || 'localhost:8005';
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
                    if (!response.ok) {
                        const errorData = await response.json();
                        throw new Error(errorData.detail || 'Failed to send message');
                    }
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
                        host = localStorage.getItem('MUNDOIA_API_HOST') || 'localhost:8005';
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
            name: 'mundoia-auth', // name of the item in the storage (must be unique)
            storage: customStorage, // Use localStorage as the storage medium
            // Custom serializer/deserializer if needed, but default JSON.stringify/parse is usually fine
            // migrate: (persistedState, version) => { ... } // Optional migration logic
        }
    )
);

export default useGameStore;
