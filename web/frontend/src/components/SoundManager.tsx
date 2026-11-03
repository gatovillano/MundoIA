'use client';

import { useEffect, useRef } from 'react';
import useGameStore from '@/store/useGameStore';
import { synthesizer } from '@/utils/SoundSynthesizer';

export default function SoundManager() {
    const selectedAgentId = useGameStore(state => state.selectedAgentId);
    const logs = useGameStore(state => state.logs);
    const isConnected = useGameStore(state => state.isConnected);
    const musicEnabled = useGameStore(state => state.musicEnabled);

    const prevAgentId = useRef<string | null>(null);
    const prevLogTime = useRef<number>(0);
    const prevConnected = useRef<boolean>(false);
    const hasMounted = useRef(false);

    useEffect(() => {
        if (prevLogTime.current === 0) {
            prevLogTime.current = Date.now();
        }
    }, []);

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
            const latestLog = logs[logs.length - 1];
            // Only play for new logs that arrived after our last check
            if (latestLog.timestamp > prevLogTime.current) {

                const message = latestLog.message.toLowerCase();

                if (latestLog.category === 'error' || latestLog.category === 'warning') {
                    synthesizer.playAlert();
                } else {
                    // For dialogue messages, always play the base message sound first
                    if (latestLog.category === 'dialogo') {
                        synthesizer.playMessage();
                    }

                    // Contextual sound detection (applies to ALL categories)
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
                    } else if (latestLog.category !== 'dialogo') {
                        // Generic hover sound for info logs with no keyword match
                        // (dialogue already plays playMessage above)
                        synthesizer.playHover();
                    }
                }

                prevLogTime.current = latestLog.timestamp;
            }
        }
    }, [logs]);

    // --- Playlist de música de fondo (reproducción secuencial) ---
    const PLAYLIST = [
        '/background-music.mp3',
        '/village-theme.mp3',
        '/menu-theme.mp3',
    ];

    const audioRef = useRef<HTMLAudioElement | null>(null);
    const musicStartedRef = useRef(false);
    const currentTrackRef = useRef(0);
    const musicEnabledRef = useRef(musicEnabled);
    const isConnectedRef = useRef(isConnected);

    useEffect(() => {
        musicEnabledRef.current = musicEnabled;
    }, [musicEnabled]);

    useEffect(() => {
        isConnectedRef.current = isConnected;
    }, [isConnected]);

    // Carga y configura una pista de la playlist
    const loadTrack = (index: number) => {
        if (!audioRef.current) return;
        const track = PLAYLIST[index % PLAYLIST.length];
        audioRef.current.src = track;
        audioRef.current.load();
        audioRef.current.volume = 0.15;
    };

    // Avanza a la siguiente pista al terminar la actual
    const handleEnded = () => {
        currentTrackRef.current = (currentTrackRef.current + 1) % PLAYLIST.length;
        loadTrack(currentTrackRef.current);
        if (musicEnabledRef.current && isConnectedRef.current) {
            audioRef.current?.play().catch(() => {});
        }
    };

    // Inicializar audio de fondo con la primera pista
    useEffect(() => {
        if (!audioRef.current) {
            const audio = new Audio();
            audio.preload = 'auto';
            audio.volume = 0.15;
            audio.addEventListener('ended', handleEnded);
            audioRef.current = audio;
            loadTrack(0);
        }
        return () => {
            if (audioRef.current) {
                audioRef.current.removeEventListener('ended', handleEnded);
                audioRef.current.pause();
                audioRef.current.src = '';
                audioRef.current = null;
                musicStartedRef.current = false;
            }
        };
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    // Reproducir o pausar según conexión y estado de musicEnabled
    useEffect(() => {
        if (!audioRef.current) return;

        let interactionCleanup: (() => void) | null = null;

        const tryPlay = () => {
            if (audioRef.current && musicEnabledRef.current && isConnectedRef.current) {
                audioRef.current.play().then(() => {
                    musicStartedRef.current = true;
                }).catch(e => {
                    console.log("Background music autoplay blocked, will retry on user interaction:", e);
                    const handleInteraction = () => {
                        if (interactionCleanup) {
                            interactionCleanup();
                            interactionCleanup = null;
                        }
                        if (audioRef.current && musicEnabledRef.current && isConnectedRef.current) {
                            audioRef.current.play().then(() => {
                                musicStartedRef.current = true;
                            }).catch(() => {});
                        }
                    };
                    interactionCleanup = () => {
                        document.removeEventListener('click', handleInteraction);
                        document.removeEventListener('keydown', handleInteraction);
                    };
                    document.addEventListener('click', handleInteraction, { once: true });
                    document.addEventListener('keydown', handleInteraction, { once: true });
                });
            }
        };

        if (isConnected && musicEnabled) {
            tryPlay();
        } else {
            if (audioRef.current) {
                audioRef.current.pause();
                musicStartedRef.current = false;
            }
        }

        return () => {
            if (interactionCleanup) {
                interactionCleanup();
            }
        };
    }, [isConnected, musicEnabled]);

    return null;
}

