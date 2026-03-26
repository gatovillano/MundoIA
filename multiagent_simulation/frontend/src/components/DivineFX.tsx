"use client";

import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

type FXType = 'shake' | 'smite' | 'money' | 'plague' | 'glitch';

interface FXEvent {
    id: string;
    type: FXType;
    params?: any;
    timestamp: number;
}

export default function DivineFX() {
    const [activeFX, setActiveFX] = useState<FXEvent[]>([]);
    const [isShaking, setIsShaking] = useState(false);

    useEffect(() => {
        const handleDivineAction = (event: any) => {
            const { type, params } = event.detail;
            const newFX: FXEvent = {
                id: Math.random().toString(36).substr(2, 9),
                type,
                params,
                timestamp: Date.now()
            };

            setActiveFX(prev => [...prev, newFX]);

            if (type === 'shake' || type === 'earthquake') {
                setIsShaking(true);
                setTimeout(() => setIsShaking(false), 1000);
            }

            // Auto-remover efectos temporales
            setTimeout(() => {
                setActiveFX(prev => prev.filter(fx => fx.id !== newFX.id));
            }, 3000);
        };

        window.addEventListener('divine-action-fx', handleDivineAction);
        return () => window.removeEventListener('divine-action-fx', handleDivineAction);
    }, []);

    return (
        <>
            {/* Contenedor de Sacudida Global */}
            <style jsx global>{`
                body {
                    transition: transform 0.1s ease-out;
                    ${isShaking ? 'animation: shake 0.5s cubic-bezier(.36,.07,.19,.97) both;' : ''}
                }

                @keyframes shake {
                    10%, 90% { transform: translate3d(-1px, 0, 0); }
                    20%, 80% { transform: translate3d(2px, 0, 0); }
                    30%, 50%, 70% { transform: translate3d(-4px, 0, 0); }
                    40%, 60% { transform: translate3d(4px, 0, 0); }
                }

                .rayo-divino {
                    background: linear-gradient(to bottom, rgba(255,255,255,0) 0%, rgba(255,255,255,0.8) 50%, rgba(255,255,255,0) 100%);
                    width: 4px;
                    filter: blur(2px) drop-shadow(0 0 10px #fff);
                }
            `}</style>

            <div className="fixed inset-0 pointer-events-none z-[100] overflow-hidden">
                <AnimatePresence>
                    {activeFX.map(fx => (
                        <div key={fx.id}>
                            {/* Efecto de Rayo Divino */}
                            {fx.type === 'smite' && (
                                <motion.div
                                    initial={{ opacity: 0, height: 0, top: 0 }}
                                    animate={{ opacity: [0, 1, 1, 0], height: ['100vh', '100vh'], top: 0 }}
                                    exit={{ opacity: 0 }}
                                    transition={{ duration: 0.6, times: [0, 0.1, 0.8, 1] }}
                                    className="absolute left-1/2 -translate-x-1/2 rayo-divino"
                                    style={{ left: fx.params?.x ? `${fx.params.x}%` : '50%' }}
                                />
                            )}

                            {/* Efecto de Inyección de Dinero (Partículas Doradas) */}
                            {fx.type === 'money' && (
                                <div className="absolute inset-0">
                                    {[...Array(20)].map((_, i) => (
                                        <motion.div
                                            key={i}
                                            initial={{ y: -20, x: Math.random() * 100 + '%', opacity: 1, rotate: 0 }}
                                            animate={{ y: '110vh', rotate: 360, opacity: 0 }}
                                            transition={{ duration: 1.5 + Math.random(), ease: "easeIn", delay: Math.random() * 0.5 }}
                                            className="absolute text-yellow-500 text-xl"
                                        >
                                            💰
                                        </motion.div>
                                    ))}
                                </div>
                            )}

                            {/* Efecto de Plaga (Viñeta verde/oscura) */}
                            {fx.type === 'plague' && (
                                <motion.div
                                    initial={{ opacity: 0 }}
                                    animate={{ opacity: [0, 0.4, 0.4, 0] }}
                                    transition={{ duration: 3 }}
                                    className="absolute inset-0 bg-gradient-to-b from-green-900/40 via-transparent to-green-900/40 mix-blend-multiply"
                                />
                            )}
                        </div>
                    ))}
                </AnimatePresence>
            </div>
        </>
    );
}
