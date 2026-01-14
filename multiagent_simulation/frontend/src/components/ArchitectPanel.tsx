'use client';

import React, { useState } from 'react';
import { useSimulationStore } from '../store/useSimulationStore';
import { Globe, Zap, UserPlus, Send, AlertCircle } from 'lucide-react';

export default function ArchitectPanel() {
    const [lore, setLore] = useState('');
    const [seed, setSeed] = useState('');
    const [event, setEvent] = useState({ tipo: 'Lluvia de Recursos', descripcion: '', duracion: 5 });
    const [archetype, setArchetype] = useState('Merchant');

    const handleSetSeed = async () => {
        await fetch('http://localhost:8001/architect/seed', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ lore, seed })
        });
        alert('Lore y Seed actualizados');
    };

    const handleTriggerEvent = async () => {
        await fetch('http://localhost:8001/architect/event', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(event)
        });
        alert('Evento disparado');
    };

    const handleSpawn = async () => {
        await fetch('http://localhost:8001/architect/spawn', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ arquetipo: archetype })
        });
        alert('Agente spawneado');
    };

    return (
        <div className="p-8 h-full overflow-y-auto custom-scrollbar">
            <div className="max-w-4xl mx-auto space-y-8">
                <header>
                    <h2 className="text-2xl font-bold mb-2">Herramientas del Arquitecto</h2>
                    <p className="text-slate-400">Control global y manipulación de la realidad.</p>
                </header>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                    {/* World Seed & Lore */}
                    <section className="glass p-6 space-y-6">
                        <div className="flex items-center gap-3 mb-2">
                            <Globe className="text-indigo-400" size={20} />
                            <h3 className="font-semibold">Semilla del Mundo</h3>
                        </div>
                        <div className="space-y-4">
                            <div>
                                <label className="block text-xs text-slate-500 mb-2 uppercase tracking-wider">Contexto Narrativo (Lore)</label>
                                <textarea
                                    value={lore}
                                    onChange={(e) => setLore(e.target.value)}
                                    className="w-full bg-white/5 border border-white/10 rounded-lg p-3 text-sm focus:border-indigo-500 outline-none h-24 resize-none"
                                    placeholder="Ej: Un mundo post-escasez donde la energía es la única moneda..."
                                />
                            </div>
                            <div>
                                <label className="block text-xs text-slate-500 mb-2 uppercase tracking-wider">Semilla (Seed)</label>
                                <input
                                    type="text"
                                    value={seed}
                                    onChange={(e) => setSeed(e.target.value)}
                                    className="w-full bg-white/5 border border-white/10 rounded-lg p-3 text-sm focus:border-indigo-500 outline-none"
                                    placeholder="Ej: alpha-99-omega"
                                />
                            </div>
                            <button
                                onClick={handleSetSeed}
                                className="w-full py-3 bg-indigo-600 hover:bg-indigo-500 rounded-lg font-semibold text-sm flex items-center justify-center gap-2"
                            >
                                <Send size={16} />
                                Aplicar Cambios Globales
                            </button>
                        </div>
                    </section>

                    {/* Global Events */}
                    <section className="glass p-6 space-y-6">
                        <div className="flex items-center gap-3 mb-2">
                            <Zap className="text-amber-400" size={20} />
                            <h3 className="font-semibold">Eventos Catastróficos</h3>
                        </div>
                        <div className="space-y-4">
                            <div>
                                <label className="block text-xs text-slate-500 mb-2 uppercase tracking-wider">Tipo de Evento</label>
                                <select
                                    value={event.tipo}
                                    onChange={(e) => setEvent({ ...event, tipo: e.target.value })}
                                    className="w-full bg-white/5 border border-white/10 rounded-lg p-3 text-sm focus:border-indigo-500 outline-none"
                                >
                                    <option>Lluvia de Recursos</option>
                                    <option>Hambruna</option>
                                    <option>Crisis Económica</option>
                                    <option>Peste</option>
                                    <option>Edad de Oro</option>
                                </select>
                            </div>
                            <div>
                                <label className="block text-xs text-slate-500 mb-2 uppercase tracking-wider">Descripción</label>
                                <input
                                    type="text"
                                    value={event.descripcion}
                                    onChange={(e) => setEvent({ ...event, descripcion: e.target.value })}
                                    className="w-full bg-white/5 border border-white/10 rounded-lg p-3 text-sm focus:border-indigo-500 outline-none"
                                    placeholder="Ej: Un meteorito de oro ha caído en el centro..."
                                />
                            </div>
                            <button
                                onClick={handleTriggerEvent}
                                className="w-full py-3 bg-amber-600 hover:bg-amber-500 rounded-lg font-semibold text-sm flex items-center justify-center gap-2"
                            >
                                <AlertCircle size={16} />
                                Desatar Evento
                            </button>
                        </div>
                    </section>

                    {/* Archetype Spawner */}
                    <section className="glass p-6 space-y-6 md:col-span-2">
                        <div className="flex items-center gap-3 mb-2">
                            <UserPlus className="text-emerald-400" size={20} />
                            <h3 className="font-semibold">Generador de Arquetipos</h3>
                        </div>
                        <div className="flex flex-wrap gap-4">
                            {['Merchant', 'Warrior', 'Scientist', 'Citizen'].map((type) => (
                                <button
                                    key={type}
                                    onClick={() => setArchetype(type)}
                                    className={`px-6 py-3 rounded-xl border transition-all ${archetype === type
                                        ? 'bg-emerald-600/20 border-emerald-500 text-emerald-400'
                                        : 'bg-white/5 border-white/10 text-slate-400 hover:border-white/20'
                                        }`}
                                >
                                    {type}
                                </button>
                            ))}
                            <button
                                onClick={handleSpawn}
                                className="ml-auto px-8 py-3 bg-emerald-600 hover:bg-emerald-500 rounded-xl font-semibold text-sm"
                            >
                                Spawnear Agente
                            </button>
                        </div>
                    </section>
                </div>
            </div>
        </div>
    );
}
