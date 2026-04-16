import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import AsyncStorage from '@react-native-async-storage/async-storage';

interface GameState {
    isConnected: boolean;
    step: number;
    agents: any[];
    logs: any[];
    weather: string;
    lore: string;
    mapa: any[][];
    apiHost: string;
    selectedAgentId: string | null;
    socket: WebSocket | null;
    userId: string | null;
    isAuthenticated: boolean;
    username: string | null;
    
    setApiHost: (host: string) => void;
    connect: () => void;
    disconnect: () => void;
    selectAgent: (id: string | null) => void;
    login: (userId: string, username: string) => void;
    logout: () => void;
    sendAction: (action: string, params?: any) => Promise<void>;
}

const useNativeStore = create(
    persist<GameState>(
        (set, get) => ({
            isConnected: false,
            step: 0,
            agents: [],
            logs: [],
            weather: "sunny",
            lore: "",
            mapa: [],
            apiHost: 'api-mundoia.cuerpolibre.cl',
            selectedAgentId: null,
            socket: null,
            userId: null,
            isAuthenticated: false,
            username: null,

            setApiHost: (host) => {
                set({ apiHost: host });
                if (get().socket) {
                    get().disconnect();
                    setTimeout(() => get().connect(), 500);
                }
            },

            login: (userId, username) => set({ isAuthenticated: true, userId, username }),
            logout: () => {
                get().disconnect();
                set({ isAuthenticated: false, userId: null, username: null, agents: [], logs: [] });
            },

            selectAgent: (id) => set({ selectedAgentId: id }),

            sendAction: async (action, params = {}) => {
                const { apiHost, userId } = get();
                const isProd = apiHost.includes('cuerpolibre.cl');
                const protocol = isProd ? 'https' : 'http';
                const cleanHost = apiHost.replace('http://', '').replace('https://', '');
                
                try {
                    await fetch(`${protocol}://${cleanHost}/game/control`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ user_id: userId, action, ...params }),
                    });
                } catch (e) {
                    console.error("Error sending action:", e);
                }
            },

            connect: () => {
                const { userId, apiHost, socket } = get();
                if (!userId || socket) return;

                const isProd = apiHost.includes('cuerpolibre.cl');
                const protocol = isProd ? 'wss' : 'ws';
                const cleanHost = apiHost.replace('http://', '').replace('https://', '');
                
                const wsUrl = `${protocol}://${cleanHost}/ws/${userId}`;
                console.log(`🔌 Native Connection: ${wsUrl}`);
                
                try {
                    const newSocket = new WebSocket(wsUrl);

                    newSocket.onopen = () => {
                        console.log('✅ WebSocket Native Connected');
                        set({ isConnected: true });
                    };

                    newSocket.onmessage = (event) => {
                        const data = JSON.parse(event.data);
                        
                        switch (data.type) {
                            case 'initial_state':
                            case 'stats':
                                set({
                                    step: data.step,
                                    weather: data.weather,
                                    mapa: data.mapa || get().mapa,
                                    lore: data.lore || get().lore,
                                    logs: data.logs || get().logs
                                });
                                break;
                            
                            case 'stats_delta':
                                set((state) => ({
                                    step: data.step || state.step,
                                    weather: data.delta?.weather || state.weather,
                                    lore: data.delta?.lore || state.lore
                                    // Expandir aquí otros stats si es necesario
                                }));
                                break;

                            case 'agent_update':
                                if (data.agents) set({ agents: data.agents });
                                break;

                            case 'agent_delta':
                                set((state) => {
                                    const newAgents = [...state.agents];
                                    // Aplicar actualizaciones
                                    Object.entries(data.updates || {}).forEach(([id, delta]) => {
                                        const idx = newAgents.findIndex(a => a.id === id);
                                        if (idx !== -1) {
                                            newAgents[idx] = { ...newAgents[idx], ...(delta as any) };
                                        } else {
                                            newAgents.push({ id, ...(delta as any) });
                                        }
                                    });
                                    // Aplicar eliminaciones
                                    const filtered = newAgents.filter(a => !(data.removals || []).includes(a.id));
                                    return { agents: filtered };
                                });
                                break;

                            case 'log':
                                set((state) => ({
                                    logs: [...state.logs, data].slice(-100)
                                }));
                                break;
                            
                            case 'world_reset':
                                set({ agents: [], logs: [], step: 0 });
                                break;
                        }
                    };

                    newSocket.onclose = () => {
                        console.log('❌ WebSocket Native Disconnected');
                        set({ isConnected: false, socket: null });
                        setTimeout(() => get().connect(), 3000);
                    };

                    newSocket.onerror = (e) => {
                        console.error('WebSocket Error:', e);
                    };

                    set({ socket: newSocket });
                } catch (error) {
                    console.error('Failed to create WebSocket:', error);
                }
            },

            disconnect: () => {
                const { socket } = get();
                if (socket) {
                    socket.close();
                }
                set({ socket: null, isConnected: false });
            },
        }),
        {
            name: 'mundoia-native-auth',
            storage: createJSONStorage(() => AsyncStorage),
            partialize: (state) => ({
                isAuthenticated: state.isAuthenticated,
                userId: state.userId,
                username: state.username,
                apiHost: state.apiHost,
                mapa: state.mapa,
                lore: state.lore
            }) as any,
        }
    )
);

export default useNativeStore;
