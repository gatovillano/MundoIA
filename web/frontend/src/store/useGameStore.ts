import { create } from 'zustand';
import { persist, PersistStorage } from 'zustand/middleware';
import { Agent } from '../types/agent'; // Importar la interfaz Agent
import { getHttpUrl, getWsUrl, getApiBase } from '@/utils/apiConfig';

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
    showBubbles: boolean;
    // Buffers temporales para streams LLM por agente (no siempre visibles)
    llmBuffers: Record<string, string>;
    // Controla si se muestran actualizaciones incrementales (streams) en la UI
    enableStreaming: boolean;
    // Toggle para activar/desactivar streaming en tiempo real
    toggleStreaming: () => void;
    toggleBubbles: () => void;
    toggleThoughts: () => void;
    historia: { historiador_id: string | null, entradas: any[], num_entradas: number };
    ranking: any[];
    instituciones: Record<string, any>;
    agentePoseidoId: string | null;
    socialMode: 'twitter' | 'reddit';
    modoControlTotal: boolean;
    startupOperationDone: boolean;
    socialFeed: any[];
    setSocialMode: (mode: 'twitter' | 'reddit') => void;
    setModoControlTotal: (mode: boolean) => void;
    selectAgent: (agentId: string | null) => void;
    poseerAgente: (agentId: string) => Promise<boolean>;
    liberarAgente: () => Promise<boolean>;
    sendArchitectMessage: (message: string, agentId?: string) => Promise<string>;
    sendGodAction: (type: string, params: any) => Promise<boolean>;
    socket: WebSocket | null;
    bubbleCleanupInterval: ReturnType<typeof setInterval> | null;
    userId: string | null;
    gameId: string | null;
    isAuthenticated: boolean;
    username: string | null;
    login: (userId: string, username: string) => void;
    setGameId: (gameId: string | null) => void;
    logout: () => void;
    connect: () => void;
    disconnect: () => void;
    apiHost: string;
    setApiHost: (host: string) => void;
    reconnect: () => void;
    reconnecting: boolean;
    reconnectAttempts: number;
    reconnectTimer: number | null;
    _handleSessionExpiredResponse: (response: Response) => Promise<boolean>;
}

interface PersistedState {
    isAuthenticated: boolean;
    userId: string | null;
    gameId: string | null;
    username: string | null;
    mapa: any[][];
    lore: string;
    logs?: any[];
    apiHost: string;
    socialMode: 'twitter' | 'reddit';
    modoControlTotal: boolean;
    startupOperationDone: boolean;
    showBubbles: boolean;
}

const customStorage: PersistStorage<GameState> = {
    getItem: (name) => {
        const item = localStorage.getItem(name);
        if (item) {
            const parsed = JSON.parse(item);
            if (parsed?.state) {
                parsed.state.apiHost = getApiBase();
            }
            return parsed;
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
                    gameId: value.state.gameId,
                    username: value.state.username,
                    mapa: value.state.mapa,
                    lore: value.state.lore,
                    // Persistir solo los últimos 1000 logs para evitar crecer indefinidamente
                    logs: Array.isArray(value.state.logs) ? value.state.logs.slice(-1000) : [],
                    apiHost: value.state.apiHost,
                    socialMode: value.state.socialMode || 'twitter',
                    modoControlTotal: value.state.modoControlTotal || false,
                    startupOperationDone: value.state.startupOperationDone || false,
                    showBubbles: value.state.showBubbles !== undefined ? value.state.showBubbles : true
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
            showBubbles: true,
            llmBuffers: {},
            enableStreaming: true,
            historia: { historiador_id: null, entradas: [], num_entradas: 0 },
            ranking: [],
            instituciones: {},
            agentePoseidoId: null,
            // Flag temporal para indicar que la operación (new/load/quick) ya se ejecutó
            // desde la pantalla de inicio y por lo tanto el modal de operación
            // en /game debe evitar volver a preguntar.
            startupOperationDone: false,
            socialFeed: [],  // === RED SOCIAL OASIS ===
            socialMode: 'twitter',
            modoControlTotal: false,
            setSocialMode: (mode) => set({ socialMode: mode }),
            setModoControlTotal: (mode) => set({ modoControlTotal: mode }),
            socket: null,
            bubbleCleanupInterval: null,
            reconnecting: false,
            reconnectAttempts: 0,
            reconnectTimer: null,
            userId: null,
    gameId: null,
            isAuthenticated: false,
            username: null,
            apiHost: getApiBase(),

            setApiHost: (host) => {
                const trimmed = (host || '').trim();
                if (typeof window !== 'undefined') {
                    if (trimmed) {
                        localStorage.setItem('MUNDOIA_API_HOST', trimmed);
                    } else {
                        localStorage.removeItem('MUNDOIA_API_HOST');
                    }
                }
                const resolvedHost = getApiBase();
                set({ apiHost: resolvedHost });
                // Reconnect if already connected
                if (get().socket) {
                    get().disconnect();
                    setTimeout(() => get().connect(), 500);
                }
            },


            login: (userId, username) => set({ isAuthenticated: true, userId, username }),
            setGameId: (gameId) => set({ gameId }),
            logout: () => {
                get().disconnect();
                set({ isAuthenticated: false, userId: null, username: null });
            },

            // Detecta sesión inválida y fuerza regreso al login.
            _handleSessionExpiredResponse: async (response: Response): Promise<boolean> => {
                let detail = '';
                try {
                    const data = await response.clone().json();
                    detail = String(data?.detail || data?.message || '').toLowerCase();
                } catch {
                    detail = '';
                }

                const isAuthError = response.status === 401 || response.status === 403;
                const isMissingSimulation = response.status === 404 && detail.includes('simulaci') && detail.includes('no encontrada');

                if (isAuthError || isMissingSimulation) {
                    get().logout();
                    if (typeof window !== 'undefined' && window.location.pathname !== '/auth') {
                        window.location.href = '/auth';
                    }
                    return true;
                }

                return false;
            },

            toggleThoughts: () => set((state) => ({ showThoughts: !state.showThoughts })),
            toggleStreaming: () => set((state) => ({ enableStreaming: !state.enableStreaming })),
            toggleBubbles: () => set((state) => ({ showBubbles: !state.showBubbles })),

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
                const { userId, gameId, socket } = get();
                if (!userId || !gameId || socket) return;

                const wsUrl = getWsUrl(`/ws/${gameId}`);
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
                        // No limpiar logs entre pasos – la terminal es persistente
                        // Solo se limpia en world_reset (nueva partida)
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
                            // Limpiar feed social para evitar mostrar posts de partidas anteriores
                            socialFeed: [],
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
                        // Normalizar y ordenar socialFeed (asegurar timestamps numéricos en segundos)
                        const normalizeFeed = (feed: any[]) => {
                            if (!Array.isArray(feed)) return [];
                            return (feed || []).map(p => {
                                const raw = p?.timestamp;
                                let ts = 0;
                                if (typeof raw === 'string') {
                                    const parsed = Date.parse(raw);
                                    ts = isNaN(parsed) ? 0 : parsed / 1000;
                                } else if (typeof raw === 'number') {
                                    ts = Number(raw);
                                    // Si parece estar en ms ( > 1e12 ), convertir a segundos
                                    if (ts > 1e12) ts = ts / 1000;
                                } else {
                                    ts = 0;
                                }
                                return { ...p, timestamp: ts };
                            }).sort((a, b) => (b.timestamp || 0) - (a.timestamp || 0));
                        };

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
                                socialFeed: normalizeFeed(data.socialFeed),  // === RED SOCIAL OASIS ===
                            };

                        if (data.mapa) {
                            updates.mapa = data.mapa;
                        }

                        if (data.lore) {
                            updates.lore = data.lore || "";
                        }

                        // Acumular logs sin reemplazar – la terminal es persistente en toda la partida
                        if (data.logs && data.logs.length > 0) {
                            const incoming = data.logs.map((l: any) => ({
                                step: l.step || l.paso || 0,
                                message: l.message || l.mensaje || "",
                                category: l.category || l.categoria || "info",
                                private_for: l.private_for || l.privado_para,
                                thought: l.thought || l.pensamiento,
                                timestamp: l.timestamp || Date.now()
                            }));
                            // Fusionar evitando duplicados (mismo step + message)
                            const existingKeys = new Set(
                                (get().logs || []).map((l: any) => `${l.step}|${l.message}`)
                            );
                            const newLogs = incoming.filter(
                                (l: any) => !existingKeys.has(`${l.step}|${l.message}`)
                            );
                            if (newLogs.length > 0) {
                                updates.logs = [...(get().logs || []), ...newLogs].slice(-2000);
                            }
                        }

                        set(updates);
                    }

                    if (data.type === 'stats_delta') {
                        // Preprocesar delta para normalizar socialFeed si existe
                        const deltaToApply: any = { ...(data.delta || {}) };
                        if (deltaToApply.socialFeed && Array.isArray(deltaToApply.socialFeed)) {
                            deltaToApply.socialFeed = (deltaToApply.socialFeed || []).map((p: any) => {
                                const raw = p?.timestamp;
                                let ts = 0;
                                if (typeof raw === 'string') {
                                    const parsed = Date.parse(raw);
                                    ts = isNaN(parsed) ? 0 : parsed / 1000;
                                } else if (typeof raw === 'number') {
                                    ts = Number(raw);
                                    if (ts > 1e12) ts = ts / 1000;
                                } else {
                                    ts = 0;
                                }
                                return { ...p, timestamp: ts };
                            }).sort((a: any, b: any) => (b.timestamp || 0) - (a.timestamp || 0));
                        }

                        // Evitar que un delta con `logs: []` borre los logs del cliente.
                        // Si vienen logs no vacíos, normalizarlos y fusionarlos evitando duplicados.
                        if (Array.isArray(deltaToApply.logs)) {
                            if (deltaToApply.logs.length === 0) {
                                // No aplicar reemplazo vacío
                                delete deltaToApply.logs;
                            } else {
                                const incoming = (deltaToApply.logs || []).map((l: any) => ({
                                    step: l.step || l.paso || 0,
                                    message: l.message || l.mensaje || "",
                                    category: l.category || l.categoria || "info",
                                    private_for: l.private_for || l.privado_para,
                                    thought: l.thought || l.pensamiento,
                                    timestamp: l.timestamp || Date.now()
                                }));

                                const existingKeys = new Set(
                                    (get().logs || []).map((l: any) => `${l.step}|${l.message}`)
                                );

                                const newLogs = incoming.filter((l: any) => !existingKeys.has(`${l.step}|${l.message}`));

                                if (newLogs.length > 0) {
                                    deltaToApply.logs = [...(get().logs || []), ...newLogs].slice(-2000);
                                } else {
                                    delete deltaToApply.logs;
                                }
                            }
                        }

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

                            const mergedDelta = mergeRecursive(state, deltaToApply);
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
                        try {
                            console.debug && console.debug(`[WS] relationships received: ${Array.isArray(data.data) ? data.data.length : 'N/A'}`);
                        } catch (e) {}
                        set({ relationships: data.data || [] });
                    }

                    if (data.type === 'llm_stream') {
                        // El backend emite chunks con { agent_id, chunk, reset, done }.
                        // Si `enableStreaming` está desactivado, ignoramos los chunks
                        // intermedios y solo mostramos el texto cuando `done` === true.
                        const streamingEnabled = get().enableStreaming;
                        set((state) => {
                            const agentId = String(data.agent_id);
                            const chunk = String(data.chunk || '');
                            if (!agentId) return state;

                            const prevBuf = data.reset ? '' : (state.llmBuffers?.[agentId] || '');
                            const newBuf = (prevBuf + chunk).slice(-1200);

                            const newBuffers = { ...(state.llmBuffers || {}), [agentId]: newBuf };

                            // Decidir si actualizamos las burbujas visibles
                            let newSpeech = { ...state.speechBubbles };
                            if (streamingEnabled || data.done) {
                                newSpeech[agentId] = { text: newBuf, timestamp: Date.now() };
                            }

                            // Si el stream finalizó, limpiamos el buffer
                            if (data.done) {
                                delete newBuffers[agentId];
                            }

                            return {
                                llmBuffers: newBuffers,
                                speechBubbles: newSpeech,
                            };
                        });
                        return;
                    }

                    if (data.type === 'action_event') {
                        // Evitar mostrar logs intermedios de acciones cuando el usuario
                        // ha desactivado el streaming. Solo mostrar el evento final.
                        const streamingEnabled = get().enableStreaming;
                        const status = String(data.status || '').toLowerCase();
                        const isFinal = ['done', 'completed', 'finished', 'completed'].includes(status);
                        if (!streamingEnabled && !isFinal) return;

                        set((state) => ({
                            logs: [
                                ...state.logs,
                                {
                                    step: data.step || state.step || 0,
                                    message: `⚙️ [${data.agent_id}] acción ${String(data.action_name || 'N/A')} (${String(data.status || 'unknown')})`,
                                    category: 'sistema',
                                    timestamp: Date.now(),
                                },
                            ].slice(-1000),
                        }));
                        return;
                    }

                    if (data.type === 'social_event') {
                        // Construir autor/contenido a partir de distintos posibles campos
                        const authorName = data.agent_name || (data.post && (data.post.autor || data.post.autor_id)) || data.agent_id || '';
                        const contentText = data.content || (data.post && (data.post.contenido || data.post.content)) || '';

                        set((state) => ({
                            logs: [
                                ...state.logs,
                                {
                                    step: data.step || state.step || 0,
                                    message: `📱 [${authorName || 'social'}] ${String(contentText || '').slice(0, 160)}`,
                                    category: 'social',
                                    timestamp: Date.now(),
                                },
                            ].slice(-1000),
                        }));

                        // Si viene el objeto `post`, insertarlo directamente en el socialFeed local
                        try {
                            const postObj = data.post || null;
                            if (postObj) {
                                // Normalizar timestamp a segundos
                                let ts: number = (postObj.timestamp as any) || Date.now() / 1000;
                                if (typeof ts === 'string') {
                                    const parsed = Date.parse(ts);
                                    ts = isNaN(parsed) ? 0 : parsed / 1000;
                                } else if (typeof ts === 'number' && ts > 1e12) {
                                    ts = ts / 1000;
                                }
                                const normalizedPost = { ...postObj, timestamp: Number(ts) };

                                set((state) => {
                                    const existing = state.socialFeed || [];
                                    const existingIndex = existing.findIndex((p: any) => p.id === normalizedPost.id);
                                    let newFeed;
                                    if (existingIndex >= 0) {
                                        // Actualizar post existente
                                        const updated = { ...existing[existingIndex], ...normalizedPost };
                                        newFeed = [...existing.slice(0, existingIndex), updated, ...existing.slice(existingIndex + 1)];
                                    } else {
                                        // Añadir nuevo post al inicio
                                        newFeed = [normalizedPost, ...existing];
                                    }
                                    newFeed = newFeed.sort((a: any, b: any) => (b.timestamp || 0) - (a.timestamp || 0));
                                    return { socialFeed: newFeed.slice(0, 1000) } as any;
                                });
                            } else if (data.action === 'new_post' || data.event === 'post_created') {
                                // Compatibilidad antigua: solicitar refresh si no recibimos el post completo
                                const uid = get().gameId || get().userId;
                                if (uid) {
                                    fetch(getHttpUrl(`/games/refresh/${uid}`), { method: 'POST' }).catch((err) => console.warn('Refresh failed', err));
                                }
                            }
                        } catch (e) {
                            console.warn('Error handling social_event payload', e);
                        }

                        return;
                    }

                    // Actualizar historia si viene en cualquier mensaje
                    if (data.historia) {
                        console.log("Recibiendo historia:", JSON.stringify(data.historia));
                        set({ historia: data.historia });
                    }

                    if (data.type === 'log') {
                        set((state) => {
                            const newBubbles = { ...state.speechBubbles };
                            
                            if (data.category === 'dialogo' || data.category === 'chat') {
                                let agentId = data.agent_id;
                                let content = data.message;
                                
                                // Extraer contenido después de los dos puntos
                                if (content.includes(':')) {
                                    content = content.split(':').slice(1).join(':').trim();
                                }
                                
                                // Limpiar comillas
                                content = content.replace(/^["']|["']$/g, '');
                                
                                // Si no tenemos agentId explícito, intentamos extraerlo
                                if (!agentId) {
                                    const match = data.message.match(/\[([^\]]+)\]/);
                                    if (match && match[1] !== 'CHAT') {
                                        agentId = match[1].trim();
                                    } else if (data.category === 'chat') {
                                        const chatMatch = data.message.match(/CHAT\]\s+\[?([^\s\]]+)\]?\s+responde/);
                                        if (chatMatch) agentId = chatMatch[1];
                                    }
                                }

                                if (agentId && content) {
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

                newSocket.onclose = (event) => {
                    console.log('WebSocket Disconnected');
                    set({ isConnected: false, socket: null });

                    const reason = (event.reason || '').toLowerCase();
                    const authCloseCodes = [1008, 4401, 4403];
                    const isAuthClosure = authCloseCodes.includes(event.code)
                        || reason.includes('auth')
                        || reason.includes('unauthorized')
                        || reason.includes('sesi');

                    if (isAuthClosure) {
                        get().logout();
                        if (typeof window !== 'undefined' && window.location.pathname !== '/auth') {
                            window.location.href = '/auth';
                        }
                        return;
                    }

                    // Auto-reconexión si el usuario sigue autenticado en una partida activa
                    if (get().isAuthenticated && (get().gameId || get().userId) && typeof window !== 'undefined') {
                        const existingTimer = get().reconnectTimer;
                        if (!existingTimer) {
                            const timer = window.setTimeout(() => {
                                set({ reconnectTimer: null });
                                if (!get().socket && get().isAuthenticated) {
                                    get().connect();
                                }
                            }, 1500);
                            set({ reconnectTimer: timer });
                        }
                    }
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
                const { socket, bubbleCleanupInterval, reconnectTimer } = get();
                if (bubbleCleanupInterval) {
                    clearInterval(bubbleCleanupInterval);
                }
                if (reconnectTimer) {
                    try { clearTimeout(reconnectTimer as any); } catch (e) {}
                }
                if (socket) {
                    socket.onclose = null;
                    socket.close();
                }
                set({ socket: null, isConnected: false, bubbleCleanupInterval: null, reconnecting: false, reconnectAttempts: 0, reconnectTimer: null });
            },

            reconnect: () => {
                const uid = get().gameId || get().userId;
                if (!uid) return;

                // Cancelar temporizador previo
                const prev = get().reconnectTimer;
                if (prev) {
                    try { clearTimeout(prev as any); } catch (e) {}
                    set({ reconnectTimer: null });
                }

                // Reiniciar contador y marcar reconexión en curso
                set({ reconnectAttempts: 0, reconnecting: true });

                // Intento inmediato suave
                const t = window.setTimeout(() => {
                    set({ reconnectTimer: null });
                    try { get().connect(); } catch (e) { console.warn('Error initiating reconnect', e); }
                }, 300);
                set({ reconnectTimer: t });
            },

            sendArchitectMessage: async (message, agentId) => {
                const uid = get().gameId || get().userId;
                if (!uid) {
                    console.error("❌ sendArchitectMessage: No gameId/userId found in store");
                    throw new Error("No user/game id found");
                }

                try {
                    const url = getHttpUrl(`/game/god-mode/${uid}`);
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

                    if (await (get() as any)._handleSessionExpiredResponse(response)) {
                        throw new Error('Sesión expirada');
                    }

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
                const uid = get().gameId || get().userId;
                if (!uid) return false;

                try {
                    const response = await fetch(getHttpUrl(`/game/god-mode/${uid}`), {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            action_type: type,
                            params: params
                        })
                    });

                    if (await (get() as any)._handleSessionExpiredResponse(response)) {
                        return false;
                    }

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
