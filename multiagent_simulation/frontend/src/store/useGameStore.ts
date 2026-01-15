import { create } from 'zustand';

interface Agent {
    id: string;
    x: number;
    y: number;
    civilizacion_id?: string;
    resources: number;
    money: number;
    grupo_id?: string;
    rol?: string;
    profesion?: string;
    reputacion: number;
    necesidades: Record<string, number>;
    personalidad?: Record<string, number>;
    alianzas: string[];
    pensamiento?: string;
}

interface Proposal {
    id: number;
    user_id: string;
    grupo_id: string;
    proponente_id: string;
    texto: string;
    tipo: string;
    votos: Record<string, string>;
    estado: string;
    paso_creacion: number;
}

interface Faction {
    id: string;
    nombre: string;
    color: string;
    recursos: number;
}

interface Log {
    step: number;
    message: string;
    category: string;
    timestamp: number;
}

interface Tile {
    x: number;
    y: number;
    terrain: string;
    resource?: { type: string; amount: number };
    owner?: string;
    buildings?: any[];
}

interface GameState {
    isConnected: boolean;
    step: number;
    agents: Agent[];
    logs: Log[];
    weather: string;
    lore: string;
    economy: any;
    mapa: any[][];
    relationships: any[];
    speechBubbles: Record<string, { text: string; timestamp: number }>;
    selectedAgentId: string | null;
    civilizaciones: Record<string, Faction>;
    gruposDinamicos: Record<string, Faction>;
    propuestas: Proposal[];
    showThoughts: boolean;
    toggleThoughts: () => void;

    connect: (userId: string) => void;
    disconnect: () => void;
    selectAgent: (agentId: string | null) => void;
    socket: WebSocket | null;
}

const useGameStore = create<GameState>((set, get) => ({
    isConnected: false,
    step: 0,
    agents: [],
    logs: [],
    weather: "sunny",
    lore: "",
    economy: {},
    mapa: [],
    relationships: [],
    speechBubbles: {},
    selectedAgentId: null,
    civilizaciones: {},
    gruposDinamicos: {},
    propuestas: [],
    showThoughts: true,
    socket: null,

    toggleThoughts: () => set((state) => ({ showThoughts: !state.showThoughts })),

    selectAgent: (agentId) => set({ selectedAgentId: agentId }),

    connect: (userId: string) => {
        if (get().socket) return;

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        // Lógica de host inteligente: si estamos en producción, usar el subdominio de API
        let host = window.location.host;
        if (window.location.hostname === 'mundoia.gatoslibres.art') {
            host = 'api-mundoia.gatoslibres.art';
        } else if (window.location.hostname === 'localhost') {
            host = 'localhost:8000';
        }

        const wsUrl = `${protocol}//${host}/ws/${userId}`;
        const socket = new WebSocket(wsUrl);

        socket.onopen = () => {
            console.log('WebSocket Connected');
            set({ isConnected: true });
        };

        socket.onmessage = (event) => {
            const data = JSON.parse(event.data);

            if (data.type === 'initial_state' || data.type === 'stats') {
                set({
                    step: data.step,
                    economy: data.economy,
                    mapa: data.mapa,
                    weather: data.weather,
                    lore: data.lore || "",
                    civilizaciones: data.civilizaciones || {},
                    gruposDinamicos: data.grupos_dinamicos || {},
                    propuestas: data.propuestas || []
                });
            }

            if (data.type === 'agent_update') {
                set({ agents: data.agents });
            }

            if (data.type === 'relationships') {
                set({ relationships: data.data });
            }

            if (data.type === 'log') {
                set((state) => {
                    const newBubbles = { ...state.speechBubbles };
                    // Intentar extraer ID del agente si el mensaje es de diálogo
                    // Formato usual: "Agente X: Hola..."
                    if (data.category === 'dialogo' && data.message.includes(':')) {
                        // Extraer el ID dentro de los corchetes [A-123]
                        const match = data.message.match(/\[(A-?\d+)\]/);
                        const agentId = match ? match[1] : null;

                        const content = data.message.split(':').slice(1).join(':').trim();

                        if (agentId) {
                            newBubbles[agentId] = { text: content, timestamp: Date.now() };
                        }
                    } else if (data.category === 'dialogo') {
                        // Fallback: Asignar a un agente aleatorio cercano al evento si pudiéramos saberlo, 
                        // o simplemente ignorar la burbuja si no hay ID claro.
                    }

                    // Limpiar burbujas viejas (> 5s)
                    const now = Date.now();
                    Object.keys(newBubbles).forEach(key => {
                        if (now - newBubbles[key].timestamp > 5000) {
                            delete newBubbles[key];
                        }
                    });

                    return {
                        logs: [
                            {
                                step: data.step,
                                message: data.message,
                                category: data.category,
                                timestamp: Date.now(),
                            },
                            ...state.logs
                        ].slice(0, 100),
                        speechBubbles: newBubbles
                    };
                });
            }
        };

        socket.onclose = () => {
            console.log('WebSocket Disconnected');
            set({ isConnected: false, socket: null });
        };

        set({ socket });
    },

    disconnect: () => {
        const { socket } = get();
        if (socket) {
            socket.close();
            set({ socket: null, isConnected: false });
        }
    },
}));

export default useGameStore;
