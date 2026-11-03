"use client";

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    Cpu, Activity, ShieldCheck, Play, 
    RefreshCw, Zap, Users, Database, 
    Clock, ChevronRight, Binary, Globe
} from 'lucide-react';
import useGameStore from '@/store/useGameStore';
import { getHttpUrl } from '@/utils/apiConfig';
import { synthesizer } from "@/utils/SoundSynthesizer";

export default function StartPage() {
  const router = useRouter();
  const { isAuthenticated, userId, username, connect, modoControlTotal, setGameId } = useGameStore();
  const [loading, setLoading] = useState(false);
  const [savedGames, setSavedGames] = useState<any[]>([]);
  const [quickAgents, setQuickAgents] = useState<number>(12);
  const [quickSave, setQuickSave] = useState<boolean>(true);

  useEffect(() => {
    if (!isAuthenticated) {
        router.push('/auth');
    } else {
        fetchSavedGames();
    }
  }, [isAuthenticated, router]);

  const fetchSavedGames = async () => {
    if (!userId) return;
    try {
      const res = await fetch(getHttpUrl(`/games/list/${userId}`));
      if (res.ok) {
        const data = await res.json();
        setSavedGames(data.games || []);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleLoad = async (gameIdToLoad?: string) => {
    if (!userId) return;
    const targetGameId = gameIdToLoad || (savedGames.length > 0 ? savedGames[0].id : null);
    if (!targetGameId) return;

    setLoading(true);
    synthesizer.playSelect();
    try {
      setGameId(targetGameId);
      const res = await fetch(getHttpUrl('/games/load'), {
        method: 'POST', 
        headers: {'Content-Type': 'application/json'}, 
        body: JSON.stringify({ user_id: targetGameId })
      });
      if (res.ok) router.push('/game');
    } catch (e) {
      alert('Error cargando la simulación');
    } finally { setLoading(false); }
  };

  const handleNew = async () => {
    if (!userId) return;
    const confirmed = window.confirm("¿Iniciar nueva realidad en un slot nuevo?");
    if (!confirmed) return;

    setLoading(true);
    synthesizer.playSelect();
    try {
        const newGameId = `${userId}_${Date.now().toString(36)}`;
        setGameId(newGameId);

        const res = await fetch(getHttpUrl(`/game/god-mode/${newGameId}`), {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                action: 'reset',
                modo_control_total: modoControlTotal
            })
        });
        if (res.ok) {
            useGameStore.setState({ startupOperationDone: true });
            router.push('/game');
        }
    } catch (e) {
      alert('Error creando nueva realidad');
    } finally { setLoading(false); }
  };

  const handleQuickPlay = async () => {
    if (!userId) return;
    setLoading(true);
    synthesizer.playSelect();
    try {
      const newGameId = `${userId}_${Date.now().toString(36)}`;
      setGameId(newGameId);

      const res = await fetch(getHttpUrl('/games/quickplay'), {
        method: 'POST', 
        headers: {'Content-Type': 'application/json'}, 
        body: JSON.stringify({ 
            user_id: newGameId, 
            num_agents: quickAgents, 
            save: quickSave 
        })
      });
            if (res.ok) {
                useGameStore.setState({ startupOperationDone: true });
                router.push('/game');
            }
    } catch (e) {
      alert('Error lanzando Protocolo Rápido');
    } finally { setLoading(false); }
  };

  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-[#030305] text-[#e0e0e0] relative overflow-hidden">
      
      {/* Background Decor */}
      <div className="absolute inset-0 z-0">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-indigo-500/10 rounded-full blur-[120px]" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-purple-500/10 rounded-full blur-[120px]" />
        <div className="absolute inset-0 bg-[url('/grid.svg')] opacity-[0.03]" />
      </div>

      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="relative z-10 w-full max-w-5xl px-6"
      >
        {/* Header */}
        <div className="flex flex-col md:flex-row items-center justify-between gap-6 mb-12 border-b border-white/5 pb-8">
            <div className="text-center md:text-left">
                <div className="flex items-center gap-3 mb-2 justify-center md:justify-start">
                    <div className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse" />
                    <span className="text-[#7c4dff] font-mono text-[10px] uppercase tracking-[0.5em] font-black">Módulo de Carga</span>
                </div>
                <h1 className="text-4xl font-black text-white tracking-tighter uppercase">Gestión de <span className="text-gradient">Simulaciones</span></h1>
            </div>
            
            <div className="flex items-center gap-4 bg-white/5 p-4 rounded-3xl border border-white/5 backdrop-blur-md">
                <div className="w-10 h-10 rounded-full bg-indigo-500/20 flex items-center justify-center text-indigo-400">
                    <Users className="w-5 h-5" />
                </div>
                <div>
                    <p className="text-[10px] text-gray-500 font-mono uppercase tracking-widest leading-none mb-1">Arquitecto</p>
                    <p className="text-sm font-bold text-white uppercase tracking-tight">{username}</p>
                </div>
            </div>
        </div>

        {loading ? (
            <div className="h-[400px] flex flex-col items-center justify-center gap-6">
                <div className="w-16 h-16 border-4 border-indigo-500/20 border-t-indigo-500 rounded-full animate-spin" />
                <p className="text-[10px] font-mono text-indigo-400 uppercase tracking-[0.5em] animate-pulse">Reconfigurando Realidad...</p>
            </div>
        ) : (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
                
                {/* Main Operations */}
                <div className="lg:col-span-7 space-y-4">
                    <OperationCard 
                        onClick={() => handleLoad()}
                        disabled={savedGames.length === 0}
                        icon={Play}
                        title="Continuar Simulación"
                        desc={savedGames.length > 0 ? `Reanudar flujo temporal desde paso ${savedGames[0].paso_actual}.` : 'No se detectan estados guardados en el núcleo.'}
                        badge={savedGames.length > 0 ? `PASO ${savedGames[0].paso_actual}` : undefined}
                    />
                    
                    <OperationCard 
                        onClick={handleNew}
                        icon={RefreshCw}
                        title="Nueva Partida"
                        desc="Crear un nuevo universo persistente en un nuevo slot de guardado."
                        variant="danger"
                    />

                    <div className="pt-8">
                        <div className="flex items-center gap-3 mb-6">
                            <div className="h-px flex-1 bg-white/5" />
                            <span className="text-[9px] font-mono text-gray-600 uppercase tracking-[0.3em]">Estado de la Base de Datos</span>
                            <div className="h-px flex-1 bg-white/5" />
                        </div>
                        
                        {savedGames.length === 0 ? (
                            <div className="p-8 border border-dashed border-white/5 rounded-[32px] text-center">
                                <Database className="w-8 h-8 text-gray-700 mx-auto mb-3" />
                                <p className="text-xs text-gray-600 font-medium">Núcleo de almacenamiento vacío.</p>
                            </div>
                        ) : (
                            <div className="space-y-3">
                                {savedGames.map((g, i) => (
                                    <button 
                                        key={i} 
                                        onClick={() => handleLoad(g.id)}
                                        className="w-full text-left p-5 bg-white/[0.02] border border-white/5 rounded-2xl flex items-center justify-between hover:bg-white/[0.05] hover:border-indigo-500/30 transition-all group"
                                    >
                                        <div className="flex items-center gap-4">
                                            <div className="p-2 bg-indigo-500/10 rounded-lg text-indigo-400 group-hover:bg-indigo-500/20">
                                                <Clock className="w-4 h-4" />
                                            </div>
                                            <div>
                                                <p className="text-[10px] text-gray-500 uppercase font-mono">
                                                    Turno Registrado - {g.id.split('_')[1] || g.id}
                                                </p>
                                                <p className="text-sm font-black text-white">{g.paso_actual}</p>
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-6">
                                            <div className="text-right">
                                                <p className="text-[10px] text-gray-500 uppercase font-mono">Misiones</p>
                                                <p className="text-sm font-black text-[#00e676]">{g.score} PTS</p>
                                            </div>
                                            <ChevronRight className="w-5 h-5 text-indigo-500 opacity-0 group-hover:opacity-100 transition-all translate-x-[-10px] group-hover:translate-x-0" />
                                        </div>
                                    </button>
                                ))}
                            </div>
                        )}
                    </div>
                </div>

                {/* Quick Play Sidebar */}
                <div className="lg:col-span-5">
                    <div className="p-8 bg-indigo-500/[0.03] border border-indigo-500/10 rounded-[35px] space-y-8 relative overflow-hidden group">
                        <div className="absolute top-0 right-0 p-8 opacity-5 group-hover:opacity-10 transition-opacity">
                            <Zap className="w-32 h-32 text-indigo-400 fill-current" />
                        </div>

                        <div className="relative z-10">
                            <div className="flex items-center gap-4 mb-6">
                                <div className="p-3 bg-indigo-500/20 rounded-2xl text-indigo-400">
                                    <Zap className="w-6 h-6" />
                                </div>
                                <h3 className="text-xl font-bold text-white uppercase tracking-tight">Partida Rápida</h3>
                            </div>
                            
                            <p className="text-sm text-gray-500 leading-relaxed mb-8">
                                Protocolo de despliegue inmediato. Inyecta agentes aleatorios y un entorno base para comenzar la experimentación.
                            </p>

                            <div className="space-y-6">
                                <div className="space-y-3">
                                    <div className="flex justify-between text-[10px] font-mono uppercase tracking-widest">
                                        <span className="text-gray-500">Volumen de Agentes</span>
                                        <span className="text-indigo-400">{quickAgents}</span>
                                    </div>
                                    <input 
                                        type="range" min={4} max={40} step={2} 
                                        value={quickAgents} 
                                        onChange={(e) => setQuickAgents(parseInt(e.target.value))}
                                        className="w-full h-1.5 bg-white/10 rounded-full appearance-none cursor-pointer accent-indigo-500"
                                    />
                                </div>

                                <label className="flex items-center gap-3 cursor-pointer group/check">
                                    <div className={`w-5 h-5 rounded-md border flex items-center justify-center transition-all ${quickSave ? 'bg-indigo-500 border-indigo-400' : 'border-white/10 bg-white/5'}`}>
                                        <input type="checkbox" className="hidden" checked={quickSave} onChange={(e) => setQuickSave(e.target.checked)} />
                                        {quickSave && <ChevronRight className="w-3 h-3 text-white" />}
                                    </div>
                                    <span className="text-[10px] text-gray-400 group-hover/check:text-gray-300 font-mono uppercase tracking-widest">Auto-guardar al iniciar</span>
                                </label>

                                <button 
                                    onClick={handleQuickPlay}
                                    className="w-full py-5 bg-indigo-500 hover:bg-indigo-400 text-white font-black text-sm uppercase tracking-[0.2em] rounded-2xl transition-all shadow-xl shadow-indigo-500/10 active:scale-[0.98] flex items-center justify-center gap-4"
                                >
                                    <Globe className="w-4 h-4" />
                                    Lanzar Realidad
                                </button>
                            </div>
                        </div>
                    </div>
                </div>

            </div>
        )}
      </motion.div>

      {/* Footer Metadatos */}
      <div className="fixed bottom-8 w-full flex justify-center opacity-20 pointer-events-none">
          <div className="flex items-center gap-4 text-[9px] font-mono tracking-[0.4em] uppercase text-white">
              <span>Status: Synchronized</span>
              <div className="w-1 h-1 rounded-full bg-indigo-500" />
              <span>Host: {getHttpUrl('').replace(/^https?:\/\//, '').replace(/\/$/, '')}</span>
          </div>
      </div>
    </main>
  );
}

function OperationCard({ icon: Icon, title, desc, onClick, disabled = false, badge, variant = 'primary' }: any) {
    return (
        <button 
            disabled={disabled}
            onClick={onClick}
            onMouseEnter={() => !disabled && synthesizer.playHover()}
            className={`w-full group p-8 rounded-[32px] transition-all text-left flex items-start gap-6 border relative overflow-hidden ${
                disabled 
                ? 'bg-white/[0.01] border-white/5 opacity-30 grayscale cursor-not-allowed' 
                : variant === 'danger'
                    ? 'bg-red-500/[0.02] border-red-500/10 hover:border-red-500/30 hover:bg-red-500/[0.04]'
                    : 'bg-white/[0.02] border-white/5 hover:border-indigo-500/30 hover:bg-white/[0.04]'
            }`}
        >
            <div className={`p-4 rounded-2xl transition-all ${
                disabled 
                ? 'bg-white/5 text-gray-600' 
                : variant === 'danger'
                    ? 'bg-red-500/10 text-red-400 group-hover:bg-red-500/20'
                    : 'bg-indigo-500/10 text-indigo-400 group-hover:bg-indigo-500/20'
            }`}>
                <Icon className="w-6 h-6" />
            </div>
            
            <div className="flex-1 pr-8">
                <div className="flex items-center gap-3 mb-1">
                    <h4 className="text-lg font-bold text-white uppercase tracking-tight">{title}</h4>
                    {badge && <span className="px-2 py-0.5 bg-indigo-500/20 text-indigo-400 text-[8px] font-black rounded-full border border-indigo-500/20">{badge}</span>}
                </div>
                <p className="text-xs text-gray-500 leading-relaxed max-w-sm">{desc}</p>
            </div>

            {!disabled && (
                <div className="mt-4 opacity-0 group-hover:opacity-100 transition-all translate-x-[-10px] group-hover:translate-x-0">
                    <ChevronRight className={`w-5 h-5 ${variant === 'danger' ? 'text-red-500' : 'text-indigo-500'}`} />
                </div>
            )}
        </button>
    );
}
