// frontend/src/types/agent.d.ts

export interface Plan {
    id: string;
    objetivo: string;
    contenido: string;
    paso_inicio: number;
    paso_fin_estimado: number;
    estado: string;
    acciones: any[]; // Se puede especificar más si se conoce la estructura
    participantes: string[];
}

export interface Agent {
    id: string;
    x: number;
    y: number;
    civilizacion_id: string;
    resources: number;
    money: number;
    grupo_id: string;
    rol: string;
    profesion?: string;
    reputacion: number;
    necesidades: {
        salud: number;
        seguridad: number;
        social: number;
        alimento: number;
        descanso: number;
        entretenimiento: number;
    };
    alianzas: any[]; // Considerar tipar esto más específicamente si es necesario
    personalidad: {
        [key: string]: number; // Ejemplo: { "agresividad": 0.5, "curiosidad": 0.7 }
    };
    experiencia: {
        [key: string]: number; // Ejemplo: { "combate": 5, "comercio": 3 }
    };
    mensajes_enviados_count: number;
    pensamiento: string;
    planes: Plan[]; // Array de objetos Plan
    skills?: {
        [key: string]: {
            name: string;
            description: string;
            code: string;
            author_id?: string;
            version?: string;
        }
    };
    skill_factor?: number;
    inventario?: {
        [key: string]: number;
    };
    color?: string;
    is_possessed?: boolean;
}
