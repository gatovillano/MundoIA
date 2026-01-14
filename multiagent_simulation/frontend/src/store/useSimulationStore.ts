import { create } from 'zustand';

interface Agent {
  id: string;
  recursos: number;
  money: number;
  grupo_id: string | null;
  rol: string;
  profesion: string | null;
  rango: number;
  reputacion: number;
  personalidad: any;
  necesidades: any;
  mision_grupal: string | null;
  alianzas: string[];
  memorias?: any[];
}

interface Relationship {
  source: string;
  target: string;
  type: string;
  strength: number;
}

interface SimulationState {
  agents: Map<string, Agent>;
  relationships: Relationship[];
  currentStep: number;
  isPaused: boolean;
  speed: number;
  metrics: {
    gini: number;
    happiness: number;
    conflict_rate: number;
  };
  logs: any[];
  economy: any;
  selectedAgentId: string | null;

  // Actions
  setAgents: (agents: Agent[]) => void;
  updateAgents: (agents: Partial<Agent>[]) => void;
  setRelationships: (relationships: Relationship[]) => void;
  setStep: (step: number) => void;
  setMetrics: (metrics: any) => void;
  addLog: (log: any) => void;
  setEconomy: (economy: any) => void;
  setSelectedAgent: (id: string | null) => void;
  togglePause: () => void;
  setSpeed: (speed: number) => void;
}

export const useSimulationStore = create<SimulationState>((set) => ({
  agents: new Map(),
  relationships: [],
  currentStep: 0,
  isPaused: false,
  speed: 1,
  metrics: {
    gini: 0,
    happiness: 0,
    conflict_rate: 0,
  },
  logs: [],
  economy: {},
  selectedAgentId: null,

  setAgents: (agents) => set((state) => {
    const newMap = new Map();
    agents.forEach(a => newMap.set(a.id, a));
    return { agents: newMap };
  }),

  updateAgents: (updates) => set((state) => {
    const newMap = new Map(state.agents);
    updates.forEach(update => {
      if (update.id) {
        const existing = newMap.get(update.id) || {
          id: update.id,
          recursos: 0,
          money: 0,
          grupo_id: null,
          rol: 'Ciudadano',
          profesion: null,
          rango: 1,
          reputacion: 1,
          personalidad: {},
          necesidades: {},
          mision_grupal: null,
          alianzas: [],
          memorias: []
        };
        newMap.set(update.id, { ...existing, ...update } as Agent);
      }
    });
    return { agents: newMap };
  }),

  setRelationships: (relationships) => set({ relationships }),
  setStep: (step) => set({ currentStep: step }),
  setMetrics: (metrics) => set({ metrics }),
  addLog: (log) => set((state) => ({ logs: [log, ...state.logs].slice(0, 100) })),
  setEconomy: (economy) => set({ economy }),
  setSelectedAgent: (id) => set({ selectedAgentId: id }),
  togglePause: () => set((state) => ({ isPaused: !state.isPaused })),
  setSpeed: (speed) => set({ speed }),
}));
