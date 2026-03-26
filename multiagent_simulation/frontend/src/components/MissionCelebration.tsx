'use client';

import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Trophy, Star, Award, Zap } from 'lucide-react';

interface MissionCelebrationProps {
    mission: {
        id: string;
        titulo: string;
        descripcion: string;
        recompensa_puntos: number;
        dificultad: string;
    } | null;
    onComplete: () => void;
}

export default function MissionCelebration({ mission, onComplete }: MissionCelebrationProps) {
    const [isVisible, setIsVisible] = useState(false);

    useEffect(() => {
        if (mission) {
            setIsVisible(true);

            let confettiInterval: any;

            // Disparar confeti con importación dinámica
            const runConfetti = async () => {
                try {
                    const { default: confetti } = await import('canvas-confetti');
                    const duration = 3 * 1000;
                    const animationEnd = Date.now() + duration;
                    const defaults = { startVelocity: 30, spread: 360, ticks: 60, zIndex: 99999, disableForReducedMotion: true };

                    const randomInRange = (min: number, max: number) => Math.random() * (max - min) + min;

                    confettiInterval = setInterval(function () {
                        const timeLeft = animationEnd - Date.now();

                        if (timeLeft <= 0) {
                            clearInterval(confettiInterval);
                            return;
                        }

                        const particleCount = 50 * (timeLeft / duration);

                        confetti({
                            ...defaults,
                            particleCount,
                            origin: { x: randomInRange(0.1, 0.3), y: Math.random() - 0.2 }
                        });
                        confetti({
                            ...defaults,
                            particleCount,
                            origin: { x: randomInRange(0.7, 0.9), y: Math.random() - 0.2 }
                        });
                    }, 250);
                } catch (err) {
                    console.error("No se pudo cargar canvas-confetti:", err);
                }
            };

            runConfetti();

            // Cerrar automáticamente después de 5 segundos
            const timer = setTimeout(() => {
                setIsVisible(false);
                setTimeout(onComplete, 500); // Dar tiempo a la animación de salida
            }, 5000);

            return () => {
                clearTimeout(timer);
                if (confettiInterval) clearInterval(confettiInterval);
                // Limpiar cualquier canvas residual de confeti
                setTimeout(() => {
                    document.querySelectorAll('canvas').forEach(canvas => {
                        if (canvas.style.position === 'fixed' && canvas.style.zIndex === '99999') {
                            canvas.remove();
                        }
                    });
                }, 100);
            };
        }
    }, [mission]);

    if (!mission) return null;

    const difficultyColors: Record<string, string> = {
        facil: "from-green-400 to-emerald-600",
        media: "from-blue-400 to-indigo-600",
        dificil: "from-purple-400 to-fuchsia-600",
        epica: "from-yellow-400 to-orange-600 shadow-[0_0_30px_rgba(250,204,21,0.5)]"
    };

    const bgColor = difficultyColors[mission.dificultad] || "from-blue-400 to-indigo-600";

    return (
        <AnimatePresence>
            {isVisible && (
                <div className="fixed inset-0 z-[9999] flex items-center justify-center pointer-events-none">
                    <motion.div
                        initial={{ scale: 0.5, opacity: 0, y: 50 }}
                        animate={{ scale: 1, opacity: 1, y: 0 }}
                        exit={{ scale: 1.2, opacity: 0, y: -50 }}
                        transition={{ type: "spring", damping: 12, stiffness: 200 }}
                        className="bg-black/80 backdrop-blur-2xl border border-white/20 p-8 rounded-[40px] flex flex-col items-center max-w-md w-full relative overflow-hidden"
                    >
                        {/* Fondo brillante */}
                        <div className={`absolute inset-0 bg-gradient-to-br ${bgColor} opacity-10`} />

                        {/* Icono Principal */}
                        <motion.div
                            initial={{ rotate: -20, scale: 0 }}
                            animate={{ rotate: 0, scale: 1 }}
                            transition={{ delay: 0.2, type: "spring" }}
                            className={`w-24 h-24 rounded-full bg-gradient-to-br ${bgColor} flex items-center justify-center mb-6 shadow-xl border-4 border-white/30`}
                        >
                            <Trophy className="w-12 h-12 text-white" strokeWidth={2.5} />
                        </motion.div>

                        {/* Texto */}
                        <motion.div
                            initial={{ y: 20, opacity: 0 }}
                            animate={{ y: 0, opacity: 1 }}
                            transition={{ delay: 0.3 }}
                            className="text-center"
                        >
                            <h2 className="text-3xl font-black text-white mb-2 tracking-tight uppercase">
                                ¡Misión Completada!
                            </h2>
                            <p className={`text-xl font-bold bg-gradient-to-r ${bgColor} bg-clip-text text-transparent mb-4`}>
                                {mission.titulo}
                            </p>
                            <div className="bg-white/5 border border-white/10 rounded-2xl p-4 mb-6">
                                <p className="text-gray-300 text-sm leading-relaxed">
                                    {mission.descripcion}
                                </p>
                            </div>
                        </motion.div>

                        {/* Recompensa */}
                        <motion.div
                            initial={{ scale: 0 }}
                            animate={{ scale: 1 }}
                            transition={{ delay: 0.5, type: "spring" }}
                            className="flex items-center gap-3 bg-white text-black px-6 py-3 rounded-full font-black text-xl shadow-2xl"
                        >
                            <Star className="w-6 h-6 fill-yellow-400 text-yellow-500" />
                            <span>+{mission.recompensa_puntos} PUNTOS</span>
                            <Zap className="w-6 h-6 text-blue-500 fill-blue-500" />
                        </motion.div>

                        {/* Partículas flotantes decorativas */}
                        <div className="absolute top-4 left-4">
                            <Star className="w-4 h-4 text-yellow-400 opacity-40 animate-pulse" />
                        </div>
                        <div className="absolute top-10 right-10">
                            <Award className="w-6 h-6 text-purple-400 opacity-40 animate-bounce" />
                        </div>
                        <div className="absolute bottom-10 left-10">
                            <Zap className="w-5 h-5 text-blue-400 opacity-40 animate-pulse" />
                        </div>
                    </motion.div>
                </div>
            )}
        </AnimatePresence>
    );
}
