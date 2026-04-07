'use client';

import React, { useState, useEffect } from 'react';
import { Settings, X, Globe, Save, RefreshCw } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import useGameStore from '../store/useGameStore';

const MobileSettings: React.FC = () => {
    const { apiHost, setApiHost, isConnected, connect, disconnect } = useGameStore();
    const [isOpen, setIsOpen] = useState(false);
    const [localHost, setLocalHost] = useState(apiHost);
    const [isMounted, setIsMounted] = useState(false);

    useEffect(() => {
        setIsMounted(true);
        setLocalHost(apiHost);
    }, [apiHost]);

    if (!isMounted) return null;

    const handleSave = () => {
        setApiHost(localHost);
        setIsOpen(false);
    };

    const handleReconnect = () => {
        disconnect();
        setTimeout(() => connect(), 500);
    };

    return (
        <>
            {/* Botón flotante de configuración - Solo visible en móviles o pantallas pequeñas */}
            <motion.button
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.9 }}
                onClick={() => setIsOpen(true)}
                className="fixed bottom-4 right-4 z-[9999] p-3 bg-indigo-600/80 hover:bg-indigo-500 text-white rounded-full shadow-lg backdrop-blur-md border border-white/20 transition-all"
                title="Configuración de Conexión"
            >
                <Settings size={24} className={isConnected ? "text-white" : "text-red-300 animate-pulse"} />
            </motion.button>

            {/* Modal de Configuración */}
            <AnimatePresence>
                {isOpen && (
                    <div className="fixed inset-0 z-[10000] flex items-center justify-center p-4">
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            onClick={() => setIsOpen(false)}
                            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
                        />
                        
                        <motion.div
                            initial={{ scale: 0.9, opacity: 0, y: 20 }}
                            animate={{ scale: 1, opacity: 1, y: 0 }}
                            exit={{ scale: 0.9, opacity: 0, y: 20 }}
                            className="relative w-full max-w-md bg-slate-900 border border-indigo-500/30 rounded-2xl shadow-2xl overflow-hidden p-6 text-white"
                        >
                            <div className="flex justify-between items-center mb-6">
                                <h3 className="text-xl font-bold flex items-center gap-2 text-indigo-300">
                                    <Globe size={20} className="text-indigo-400" />
                                    Conexión al Servidor
                                </h3>
                                <button 
                                    onClick={() => setIsOpen(false)}
                                    className="p-1 hover:bg-white/10 rounded-full transition-colors"
                                >
                                    <X size={20} />
                                </button>
                            </div>

                            <div className="space-y-4">
                                <div>
                                    <label className="block text-sm font-medium text-slate-400 mb-1">
                                        Host del API (IP:Puerto)
                                    </label>
                                    <div className="flex gap-2">
                                        <input
                                            type="text"
                                            value={localHost}
                                            onChange={(e) => setLocalHost(e.target.value)}
                                            placeholder="ej: api-mundoia.cuerpolibre.cl"
                                            className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all font-mono text-sm"
                                        />
                                    </div>
                                    <p className="mt-2 text-xs text-slate-500 italic">
                                        En Android, usa la IP local de tu computador. No uses 'localhost'.
                                    </p>
                                </div>

                                <div className="flex items-center gap-3 p-3 bg-slate-800/50 rounded-lg">
                                    <div className={`w-3 h-3 rounded-full ${isConnected ? "bg-green-500 shadow-[0_0_10px_rgba(34,197,94,0.6)]" : "bg-red-500 shadow-[0_0_10px_rgba(239,68,68,0.6)]"}`} />
                                    <span className="text-sm">
                                        Estado: <span className={isConnected ? "text-green-400 font-medium" : "text-red-400 font-medium"}>
                                            {isConnected ? "Conectado" : "Desconectado"}
                                        </span>
                                    </span>
                                </div>

                                <div className="flex gap-3 pt-4">
                                    <button
                                        onClick={handleSave}
                                        className="flex-1 flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-500 py-2.5 rounded-xl font-semibold transition-all active:scale-95"
                                    >
                                        <Save size={18} />
                                        Guardar
                                    </button>
                                    <button
                                        onClick={handleReconnect}
                                        className="flex items-center justify-center gap-2 bg-slate-800 hover:bg-slate-700 px-4 py-2.5 rounded-xl font-semibold transition-all active:scale-95"
                                    >
                                        <RefreshCw size={18} className={isConnected ? "" : "animate-spin"} />
                                        Reconectar
                                    </button>
                                </div>
                            </div>

                            <div className="mt-6 pt-6 border-t border-slate-800 text-[10px] text-slate-500 uppercase tracking-widest text-center">
                                MundoIA Hybrid Engine • Capacitor Android
                            </div>
                        </motion.div>
                    </div>
                )}
            </AnimatePresence>
        </>
    );
};

export default MobileSettings;
