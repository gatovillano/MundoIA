// frontend/src/types/agent.d.ts

export interface Plan {
    id: string;
    objetivo: string;
    contenido: string;
    paso_inicio: number;
    paso_fin_estimado: number;
    estado: string;
    acciones: any[];
    participantes: string[];
}

export interface SocialMetrics {
    capital_social: number;
    nivel_influencia: string;
    seguidores: number;
    siguiendo: number;
    posts_publicados: number;
    comentarios_realizados: number;
    likes_recibidos: number;
    likes_dados: number;
    debates_ganados: number;
    debates_perdidos: number;
    intereses: string[];
    opiniones_fuertes: { [tema: string]: number };
}

export interface IntellectualNeeds {
    curiosidad: number;
    expresion: number;
    debate: number;
    aprendizaje: number;
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
    necesidades_intelectuales?: IntellectualNeeds;
    social_metrics?: SocialMetrics;
    alianzas: any[];
    personalidad: {
        [key: string]: number;
    };
    experiencia: {
        [key: string]: number;
    };
    mensajes_enviados_count: number;
    pensamiento: string;
    planes: Plan[];
    skills?: {
        [key: string]: {
            name: string;
            description: string;
            code: string;
            author_id?: string;
            version?: string;
        }
    };
    apps?: {
        [key: string]: {
            name: string;
            code: string;
            file_path?: string;
            created_at: string;
        }
    };
    skill_factor?: number;
    inventario?: {
        [key: string]: number;
    };
    color?: string;
    is_possessed?: boolean;
    creencias?: {
        [proposicion: string]: {
            proposicion: string;
            probabilidad: number;
            fuerza: number;
            fuente: string;
            ultimo_update: number;
        }
    };
    deseos?: {
        deseos: {
            [tipo: string]: {
                tipo: string;
                intensidad: number;
                estabilidad: number;
            }
        };
        pesos: { [tipo: string]: number };
    };
     intenciones?: {
         plan_actual: {
             acciones: {
                 nombre: string;
                 objetivo?: string;
                 argumentos: any;
                 costo_estimado: number;
                 probabilidad_exito: number;
                 meta: string;
             }[];
             meta: string;
             prioridad: number;
             tiempo_maximo: number;
             tiempo_actual: number;
         } | null;
         historial_planes: any[];
     };
     alma?: {
         arquetipo: string;
         nombre_propio: string;
         tono_comunicativo: string;
         valores: {
             [key: string]: {
                 nombre: string;
                 peso: number;
                 definicion_propia: string;
             };
         };
          tabues: string[];
           narrativa_personal: string;
           traumas: any[];
           epifanias: any[];
           triumphs: any[];
           triumphs?: any[];
           triumphs?: any[];
           triumphs?: any[];
           triunfos?: any[];
           relacion_con_arquitecto: string;
         filosofia_existencial: string;
         nivel_conciencia: number;
         capacidad_reflexion: number;
     };
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
    apps?: {
        [key: string]: {
            name: string;
            code: string;
            file_path?: string;
            created_at: string;
        }
    };
    skill_factor?: number;
    inventario?: {
        [key: string]: number;
    };
    color?: string;
    is_possessed?: boolean;
    creencias?: {
        [proposicion: string]: {
            proposicion: string;
            probabilidad: number;
            fuerza: number;
            fuente: string;
            ultimo_update: number;
        }
    };
    deseos?: {
        deseos: {
            [tipo: string]: {
                tipo: string;
                intensidad: number;
                estabilidad: number;
            }
        };
        pesos: { [tipo: string]: number };
    };
     intenciones?: {
         plan_actual: {
             acciones: {
                 nombre: string;
                 objetivo?: string;
                 argumentos: any;
                 costo_estimado: number;
                 probabilidad_exito: number;
                 meta: string;
             }[];
             meta: string;
             prioridad: number;
             tiempo_maximo: number;
             tiempo_actual: number;
         } | null;
         historial_planes: any[];
     };
     alma?: {
         arquetipo: string;
         nombre_propio: string;
         tono_comunicativo: string;
         valores: {
             [key: string]: {
                 nombre: string;
                 peso: number;
                 definicion_propia: string;
             };
         };
         tabues: string[];
         narrativa_personal: string;
         traumas: any[];
         epifanias: any[];
         triunfos: any[];
         relacion_con_arquitecto: string;
         filosofia_existencial: string;
         nivel_conciencia: number;
         capacidad_reflexion: number;
     };
 }
