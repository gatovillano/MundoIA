'use client';

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Info,
    Zap,
    Users,
    Shield,
    Map,
    Heart,
    Hammer,
    Globe,
    ChevronRight,
    ChevronLeft,
    Play
} from 'lucide-react';

interface Slide {
    id: number;
    title: string;
    description: string;
    icon: React.ReactNode;
    color: string;
    details: string[];
}

const slides: Slide[] = [
    {
        id: 0,
        title: "Bienvenido, Arquitecto",
        description: "Estás ante un simulador de vida multi-agente impulsado por IA. Tu misión es observar, influir y expandir este ecosistema digital.",
        icon: <Globe size={48} />,
        color: "#7c4dff",
        details: [
            "Terrenos Dinámicos: Montañas ⛰️, Bosques 🌲 y Lagos 🌊.",
            "Recursos: El alimento y los materiales son la base de la economía.",
            "Ecosistema Real-Time: El mundo nunca duerme."
        ]
    },
    {
        id: 1,
        title: "Agentes y Supervivencia",
        description: "Cada punto de luz es un agente autónomo con su propio cerebro, personalidad y necesidades vitales.",
        icon: <Users size={48} />,
        color: "#00e676",
        details: [
            "Constantes Vitales: Monitorea la barra de salud sobre sus cabezas. Si llega a cero, el agente muere 🪦.",
            "Instinto: Los agentes buscan comida y hospitales automáticamente si están heridos.",
            "Facciones: Los agentes forman grupos con colores únicos, firman tratados y patrullan juntos en formación 🛡️."
        ]
    },
    {
        id: 2,
        title: "El Poder del Arquitecto",
        description: "Abre el Panel del Arquitecto para manifestar tu voluntad divina sobre el tablero.",
        icon: <Hammer size={48} />,
        color: "#ffd600",
        details: [
            "Control Climático: Desata tormentas 🌪️ o cielos despejados ☀️ para afectar el movimiento.",
            "Creación de Vida: Spawnea nuevos agentes en cualquier punto del mapa.",
            "Diplomacia: Observa cómo las facciones cooperan o compiten por el territorio en tiempo real."
        ]
    }
];

export default function InstructionOverlay({ onComplete }: { onComplete: () => void }) {
    const [currentSlide, setCurrentSlide] = useState(0);

    const nextSlide = () => {
        if (currentSlide < slides.length - 1) {
            setCurrentSlide(currentSlide + 1);
        } else {
            onComplete();
        }
    };

    const prevSlide = () => {
        if (currentSlide > 0) {
            setCurrentSlide(currentSlide - 1);
        }
    };

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/60 backdrop-blur-md">
            <motion.div
                initial={{ opacity: 0, scale: 0.9, y: 20 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                className="relative w-full max-w-2xl bg-[#0a0a0f]/80 border border-[#7c4dff]/30 rounded-3xl overflow-hidden shadow-[0_0_50px_rgba(124,77,255,0.2)] backdrop-blur-xl"
            >
                {/* HUD Header Decor */}
                <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-transparent via-[#7c4dff] to-transparent opacity-50" />

                <div className="p-8 md:p-12">
                    <AnimatePresence mode="wait">
                        <motion.div
                            key={currentSlide}
                            initial={{ opacity: 0, x: 20 }}
                            animate={{ opacity: 1, x: 0 }}
                            exit={{ opacity: 0, x: -20 }}
                            transition={{ duration: 0.3 }}
                            className="flex flex-col items-center text-center space-y-6"
                        >
                            <div
                                className="p-4 rounded-2xl bg-white/5 border border-white/10 shadow-inner"
                                style={{ color: slides[currentSlide].color }}
                            >
                                {slides[currentSlide].icon}
                            </div>

                            <div className="space-y-2">
                                <h2 className="text-3xl md:text-4xl font-bold text-white tracking-tight">
                                    {slides[currentSlide].title}
                                </h2>
                                <p className="text-gray-400 text-lg max-w-lg mx-auto leading-relaxed">
                                    {slides[currentSlide].description}
                                </p>
                            </div>

                            <div className="w-full space-y-3 pt-4">
                                {slides[currentSlide].details.map((detail, idx) => (
                                    <motion.div
                                        key={idx}
                                        initial={{ opacity: 0, y: 10 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        transition={{ delay: 0.2 + idx * 0.1 }}
                                        className="flex items-center space-x-3 text-left p-3 rounded-xl bg-white/5 border border-white/5"
                                    >
                                        <div className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: slides[currentSlide].color }} />
                                        <span className="text-gray-300 text-sm md:text-base">{detail}</span>
                                    </motion.div>
                                ))}
                            </div>
                        </motion.div>
                    </AnimatePresence>

                    {/* Navigation */}
                    <div className="flex items-center justify-between mt-12 pt-6 border-t border-white/10">
                        <div className="flex space-x-2">
                            {slides.map((_, idx) => (
                                <div
                                    key={idx}
                                    className={`h-1.5 rounded-full transition-all duration-300 ${idx === currentSlide ? 'w-8' : 'w-2 bg-white/20'}`}
                                    style={{ backgroundColor: idx === currentSlide ? slides[currentSlide].color : undefined }}
                                />
                            ))}
                        </div>

                        <div className="flex space-x-3">
                            {currentSlide > 0 && (
                                <button
                                    onClick={prevSlide}
                                    className="p-3 rounded-full bg-white/5 text-gray-400 hover:text-white transition-colors"
                                >
                                    <ChevronLeft size={24} />
                                </button>
                            )}

                            <button
                                onClick={nextSlide}
                                className="px-6 py-3 rounded-full flex items-center space-x-2 font-bold transition-all transform hover:scale-105 active:scale-95"
                                style={{
                                    backgroundColor: slides[currentSlide].color,
                                    color: '#000',
                                    boxShadow: `0 0 20px ${slides[currentSlide].color}66`
                                }}
                            >
                                <span>{currentSlide === slides.length - 1 ? 'Iniciar Simulación' : 'Siguiente'}</span>
                                {currentSlide === slides.length - 1 ? <Play size={18} fill="currentColor" /> : <ChevronRight size={18} />}
                            </button>
                        </div>
                    </div>
                </div>

                {/* Scanline Effect Overlay */}
                <div className="absolute inset-0 pointer-events-none opacity-[0.03] overflow-hidden">
                    <div className="absolute inset-0 bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.25)_50%),linear-gradient(90deg,rgba(255,0,0,0.06),rgba(0,255,0,0.02),rgba(0,0,255,0.06))] bg-[length:100%_2px,3px_100%]" />
                </div>
            </motion.div>
        </div>
    );
}
