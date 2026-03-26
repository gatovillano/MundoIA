'use client';

import { useEffect, useRef } from 'react';
import useGameStore from '@/store/useGameStore';
import { synthesizer } from '@/utils/SoundSynthesizer';

export default function SoundManager() {
    const selectedAgentId = useGameStore(state => state.selectedAgentId);
    const logs = useGameStore(state => state.logs);
    const isConnected = useGameStore(state => state.isConnected);

    const prevAgentId = useRef<string | null>(null);
    const prevLogTime = useRef<number>(Date.now());
    const prevConnected = useRef<boolean>(false);
    const hasMounted = useRef(false);

    // Monitor connection status
    useEffect(() => {
        if (!hasMounted.current) {
            hasMounted.current = true;
            prevConnected.current = isConnected;
            return;
        }

        if (isConnected && !prevConnected.current) {
            synthesizer.playSuccess();
        } else if (!isConnected && prevConnected.current) {
            synthesizer.playAlert();
        }
        prevConnected.current = isConnected;
    }, [isConnected]);

    // Monitor Agent Selection
    useEffect(() => {
        if (selectedAgentId !== prevAgentId.current) {
            if (selectedAgentId) {
                synthesizer.playSelect();
            } else if (prevAgentId.current) {
                // Play a softer sound when deselecting
                synthesizer.playHover();
            }
        }
        prevAgentId.current = selectedAgentId;
    }, [selectedAgentId]);

    // Monitor Logs
    useEffect(() => {
        if (logs.length > 0) {
            const latestLog = logs[0];
            // Only play for new logs that arrived after our last check
            if (latestLog.timestamp > prevLogTime.current) {

                // Debounce slightly to avoid sound chaos if many logs arrive at once
                // But usually logs come one by one in this loop

                // Text analysis for specific event sounds
                const message = latestLog.message.toLowerCase();

                if (latestLog.category === 'error' || latestLog.category === 'warning') {
                    synthesizer.playAlert();
                } else if (latestLog.category === 'dialogo') {
                    synthesizer.playMessage();
                } else {
                    // Specific Event Detection
                    if (message.includes('come') || message.includes('alimenta') || message.includes('recupera energía')) {
                        synthesizer.playEat();
                    } else if (message.includes('ataca') || message.includes('daño') || message.includes('combate') || message.includes('atacado') || message.includes('⚔️')) {
                        synthesizer.playCombat();
                    } else if (message.includes('funda') && (message.includes('grupo') || message.includes('facción'))) {
                        synthesizer.playFoundGroup();
                    } else if (message.includes('funda') && (message.includes('institución') || message.includes('institucion'))) {
                        synthesizer.playFoundInstitution();
                    } else if (message.includes('asamble') || message.includes('reunión general') || message.includes('conferencia mundial')) {
                        synthesizer.playAssemblyStart();
                    } else if (message.includes('trabaja') || message.includes('recolecta') || message.includes('construye') || message.includes('construido') || message.includes('construcción') || message.includes('🏗️')) {
                        if (message.includes('construye') || message.includes('construido') || message.includes('construcción') || message.includes('🏗️')) {
                            synthesizer.playBuild();
                        } else {
                            synthesizer.playWork();
                        }
                    } else if (message.includes('muere') || message.includes('eliminado')) {
                        synthesizer.playDeath();
                    } else if (latestLog.category === 'info') {
                        // Generic info sound if no specific keyword matched
                        synthesizer.playHover();
                    }
                }

                prevLogTime.current = latestLog.timestamp;
            }
        }
    }, [logs]);

    return null;
}
