'use client';

import React, { useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Book, X, History, User, Calendar } from 'lucide-react';
import useGameStore from '@/store/useGameStore';

interface SocietyChronicleProps {
    isOpen: boolean;
    onClose: () => void;
}

export default function SocietyChronicle({ isOpen, onClose }: SocietyChronicleProps) {
    const { historia } = useGameStore();
    
    // Debug: mostrar datos crudos cada vez que cambia
    useEffect(() => {
        if (isOpen) {
            console.log("=== CRONICAS DEBUG ===");
            console.log("historia:", historia);
            console.log("entradas:", historia?.entradas);
            console.log("tipo:", typeof historia?.entradas);
            console.log("es array:", Array.isArray(historia?.entradas));
        }
    }, [isOpen, historia]);
    
    const entradas = [...(historia?.entradas || [])].reverse();
    const numEntradas = historia?.num_entradas || 0;

    return (
        <AnimatePresence>
            {isOpen && (
                <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
                    <motion.div
                        initial={{ opacity: 0, scale: 0.9, y: 20 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.9, y: 20 }}
                        className="relative w-full max-w-2xl max-h-[80vh] bg-[#fdfaf1] rounded-lg shadow-2xl overflow-hidden flex flex-col border-4 border-[#8d6e63]"
                    >
                        {/* Header estilo antiguo */}
                        <div className="bg-[#8d6e63] p-4 flex items-center justify-between text-[#fdfaf1]">
                            <div className="flex items-center gap-3">
                                <Book className="w-6 h-6" />
                                <h2 className="text-2xl font-serif font-bold tracking-tight">Crónica de la Sociedad</h2>
                            </div>
                            <button
                                onClick={onClose}
                                className="p-1 hover:bg-white/20 rounded-full transition-colors"
                            >
                                <X className="w-6 h-6" />
                            </button>
                        </div>

                        {/* Contenido (Hojas de la libreta) */}
                        <div className="flex-1 overflow-y-auto p-8 custom-scrollbar-paper">
                            {entradas.length === 0 ? (
                                <div className="flex flex-col items-center justify-center h-full opacity-40 italic font-serif">
                                    <History className="w-16 h-16 mb-4" />
                                    <p className="text-xl">Las hojas aún están en blanco...</p>
                                    <p className="text-sm">El historiador aún no ha escrito ninguna crónica.</p>
                                    <div className="mt-6 text-center text-xs text-[#8d6e63]">
                                        <p>El Historiador (Agente {historia?.historiador_id || "?"})</p>
                                        <p>total de entradas: {numEntradas}</p>
                                    </div>
                                </div>
                            ) : (
                                <div className="space-y-10">
                                    {entradas.map((entrada, idx) => (
                                        <motion.article
                                            key={idx}
                                            initial={{ opacity: 0, x: -10 }}
                                            animate={{ opacity: 1, x: 0 }}
                                            transition={{ delay: idx * 0.1 }}
                                            className="relative pb-8 border-b border-[#8d6e63]/20 last:border-0"
                                        >
                                            <div className="flex items-center justify-between mb-4">
                                                <h3 className="text-xl font-serif font-black text-[#5d4037]">
                                                    {entrada.titulo}
                                                </h3>
                                                <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-[#8d6e63]">
                                                    <Calendar className="w-3 h-3" />
                                                    Paso {entrada.turno}
                                                </div>
                                            </div>

                                            <p className="font-serif text-lg leading-relaxed text-[#3e2723] italic whitespace-pre-wrap">
                                                "{entrada.contenido}"
                                            </p>

                                            <div className="mt-4 flex items-center gap-2 text-xs font-serif text-[#8d6e63]">
                                                <User className="w-3 h-3" />
                                                Escrito por el Historiador (Agente {entrada.autor_id})
                                            </div>

                                            {/* Decoración lateral */}
                                            <div className="absolute -left-4 top-0 bottom-0 w-1 bg-[#8d6e63]/10" />
                                        </motion.article>
                                    ))}
                                </div>
                            )}
                        </div>

                        {/* Footer con textura de papel */}
                        <div className="bg-[#f5f1e3] p-4 text-center border-t border-[#8d6e63]/20">
                            <p className="text-[#8d6e63] font-serif text-sm italic">
                                — Preservando el legado de la civilización para la posteridad —
                            </p>
                        </div>
                    </motion.div>

                    <style jsx>{`
                        .custom-scrollbar-paper::-webkit-scrollbar {
                            width: 8px;
                        }
                        .custom-scrollbar-paper::-webkit-scrollbar-track {
                            background: transparent;
                        }
                        .custom-scrollbar-paper::-webkit-scrollbar-thumb {
                            background: #8d6e6344;
                            border-radius: 4px;
                        }
                        .custom-scrollbar-paper::-webkit-scrollbar-thumb:hover {
                            background: #8d6e6366;
                        }
                    `}</style>
                </div>
            )}
        </AnimatePresence>
    );
}
