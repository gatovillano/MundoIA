import { useEffect, useRef } from 'react';
import { useSimulationStore } from '../store/useSimulationStore';

export const useSimulationWebSocket = (url: string) => {
    const ws = useRef<WebSocket | null>(null);
    const {
        setAgents,
        updateAgents,
        setRelationships,
        setStep,
        setMetrics,
        addLog,
        setEconomy
    } = useSimulationStore();

    useEffect(() => {
        ws.current = new WebSocket(url);

        ws.current.onmessage = (event) => {
            const data = JSON.parse(event.data);

            switch (data.type) {
                case 'initial_state':
                    setAgents(data.agents);
                    setStep(data.step);
                    setEconomy(data.economy);
                    break;
                case 'agent_update':
                    updateAgents(data.agents);
                    break;
                case 'relationships':
                    setRelationships(data.data);
                    break;
                case 'stats':
                    setStep(data.step);
                    setEconomy(data.economy);
                    if (data.metrics) setMetrics(data.metrics);
                    break;
                case 'log':
                    addLog(data);
                    break;
                case 'reset':
                    window.location.reload();
                    break;
            }
        };

        return () => {
            ws.current?.close();
        };
    }, [url]);

    return ws.current;
};
