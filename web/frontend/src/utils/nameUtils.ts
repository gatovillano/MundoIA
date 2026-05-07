import { Agent } from "@/types/agent";

/**
 * Busca el nombre de un agente por su ID en la lista de agentes.
 * Si no lo encuentra, devuelve el ID original.
 */
export function getAgentName(id: string | null | undefined, agents: Agent[]): string {
    if (!id) return "Desconocido";
    if (id.startsWith("arquitecto_")) return "Arquitecto";
    
    const agent = agents.find(a => a.id === id);
    if (agent) {
        return agent.identidad?.nombre || agent.alma?.nombre_propio || agent.id;
    }
    return id;
}

/**
 * Reemplaza patrones de IDs de agentes (ej: [A1], A1) con sus nombres reales en un texto.
 */
export function replaceIdsWithNames(text: string, agents: Agent[]): string {
    if (!text) return "";
    
    // Reemplazar identificadores entre corchetes: [ag_abc], [arquitecto_...], etc.
    let result = text.replace(/\[([^\]]+)\]/g, (match, id) => {
        // Solo sustituir si el contenido es un token razonable (sin espacios)
        if (typeof id === 'string' && !id.includes(' ') && id.length <= 128) {
            const name = getAgentName(id, agents);
            return `[${name}]`;
        }
        return match;
    });

    // Reemplazar IDs aislados del tipo ag_xxx o arquitecto_xxx en el texto plano
    result = result.replace(/\b(ag_[A-Za-z0-9_:-]+|arquitecto_[A-Za-z0-9_:-]+)\b/g, (match, id) => {
        return getAgentName(id, agents);
    });

    return result;
}
