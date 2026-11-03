"use client";

import React, { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import {
    Play,
    RefreshCw,
    Zap,
    Users,
    Database,
    Clock,
    ChevronRight,
    Globe,
    KeyRound,
    PlusCircle,
    Radio,
    Shield,
    Lock,
    Unlock
} from 'lucide-react';
import useGameStore from '@/store/useGameStore';
import { getHttpUrl } from '@/utils/apiConfig';
import { synthesizer } from "@/utils/SoundSynthesizer";

export default function StartPage() {
  const router = useRouter();
  const { isAuthenticated, userId, username, modoControlTotal, setGameId, setRoomInfo } = useGameStore();
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'single' | 'multiplayer'>('single');
  const [savedGames, setSavedGames] = useState<any[]>([]);
  const [quickAgents, setQuickAgents] = useState<number>(12);
  const [quickSave, setQuickSave] = useState<boolean>(true);

  // Multiplayer state
  const [rooms, setRooms] = useState<any[]>([]);
  const [loadingRooms, setLoadingRooms] = useState(false);
  const [roomName, setRoomName] = useState('');
  const [roomPublic, setRoomPublic] = useState(true);
  const [roomMode, setRoomMode] = useState<'cooperativo' | 'observador_poseedor'>('cooperativo');
  const [roomMaxPlayers, setRoomMaxPlayers] = useState<number>(8);
  const [roomAgents, setRoomAgents] = useState<number>(12);
  const [joinCode, setJoinCode] = useState('');
  const [mpError, setMpError] = useState('');

  const fetchSavedGames = useCallback(async () => {
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
  }, [userId]);

  const fetchMultiplayerRooms = useCallback(async () => {
    if (!userId) return;
    setLoadingRooms(true);
    try {
      const res = await fetch(getHttpUrl(`/multiplayer/rooms?user_id=${encodeURIComponent(userId)}`));
      if (res.ok) {
        const data = await res.json();
        setRooms(data.rooms || []);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingRooms(false);
    }
  }, [userId]);

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/auth');
    } else {
      fetchSavedGames();
      fetchMultiplayerRooms();
    }
  }, [isAuthenticated, router, fetchSavedGames, fetchMultiplayerRooms]);

  const handleLoad = async (gameIdToLoad?: string) => {
    if (!userId) return;
    const targetGameId = gameIdToLoad || (savedGames.length > 0 ? savedGames[0].id : null);
    if (!targetGameId) return;

    setLoading(true);
    synthesizer.playSelect();
    try {
      setRoomInfo(null);
      setGameId(targetGameId);
      const res = await fetch(getHttpUrl('/games/load'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: targetGameId })
      });
      if (res.ok) {
        useGameStore.setState({ startupOperationDone: true });
        router.push('/game');
      }
    } catch (e) {
      alert('Error cargando la simulación');
    } finally {
      setLoading(false);
    }
  };

  const handleNew = async () => {
    if (!userId) return;
    const confirmed = window.confirm("¿Iniciar nueva realidad en un slot nuevo?");
    if (!confirmed) return;

    setLoading(true);
    synthesizer.playSelect();
    try {
      const newGameId = `${userId}_${Date.now().toString(36)}`;
      setRoomInfo(null);
      setGameId(newGameId);

      const res = await fetch(getHttpUrl(`/game/god-mode/${newGameId}`), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
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
    } finally {
      setLoading(false);
    }
  };

  const handleQuickPlay = async () => {
    if (!userId) return;
    setLoading(true);
    synthesizer.playSelect();
    try {
      const newGameId = `${userId}_${Date.now().toString(36)}`;
      setRoomInfo(null);
      setGameId(newGameId);

      const res = await fetch(getHttpUrl('/games/quickplay'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
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
    } finally {
      setLoading(false);
    }
  };

  const handleCreateRoom = async () => {
    if (!userId) return;
    setMpError('');
    setLoading(true);
    synthesizer.playSelect();
    try {
      const res = await fetch(getHttpUrl('/multiplayer/rooms/create'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          nombre: roomName.trim() || `Nexo de ${username || 'Arquitecto'}`,
          host_user_id: userId,
          host_username: username || 'Arquitecto',
          es_publica: roomPublic,
          modo_juego: roomMode,
          max_jugadores: roomMaxPlayers,
          num_agents: roomAgents,
        })
      });
      const data = await res.json();
      if (!res.ok || !data.room) {
        setMpError(data.detail || 'Error al crear la sala multijugador');
        return;
      }
      setRoomInfo(data.room);
      setGameId(data.room.game_id);
      useGameStore.setState({ startupOperationDone: true });
      router.push('/game');
    } catch (e) {
      setMpError('Error de red al crear la sala multijugador');
    } finally {
      setLoading(false);
    }
  };

  const handleJoinRoom = async (opts: { codigo_acceso?: string; game_id?: string }) => {
    if (!userId) return;
    setMpError('');
    setLoading(true);
    synthesizer.playSelect();
    try {
      const res = await fetch(getHttpUrl('/multiplayer/rooms/join'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          username: username || 'Observador',
          codigo_acceso: opts.codigo_acceso,
          game_id: opts.game_id,
        })
      });
      const data = await res.json();
      if (!res.ok || !data.room) {
        setMpError(data.detail || 'No se pudo entrar a la sala');
        return;
      }
      setRoomInfo(data.room);
      setGameId(data.room.game_id);
      useGameStore.setState({ startupOperationDone: true });
      router.push('/game');
    } catch (e) {
      setMpError('Error conectando con la sala multijugador');
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-[#030305] text-[#e0e0e0] relative overflow-y-auto py-12">

      {/* Background Decor */}
      <div className="fixed inset-0 z-0 pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-indigo-500/10 rounded-full blur-[120px]" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-purple-500/10 rounded-full blur-[120px]" />
        <div className="absolute inset-0 bg-[url('/grid.svg')] opacity-[0.03]" />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="relative z-10 w-full max-w-6xl px-6"
      >
        {/* Header */}
        <div className="flex flex-col md:flex-row items-center justify-between gap-6 mb-8 border-b border-white/5 pb-8">
          <div className="text-center md:text-left">
            <div className="flex items-center gap-3 mb-2 justify-center md:justify-start">
              <div className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse" />
              <span className="text-[#7c4dff] font-mono text-[10px] uppercase tracking-[0.5em] font-black">Módulo de Carga</span>
            </div>
            <h1 className="text-4xl font-black text-white tracking-tighter uppercase">
              Gestión de <span className="text-gradient">Simulaciones</span>
            </h1>
          </div>

          {/* Selector de Modo: Individual vs Multijugador */}
          <div className="flex items-center gap-2 p-1.5 bg-white/[0.03] border border-white/10 rounded-2xl">
            <button
              onClick={() => {
                setActiveTab('single');
                synthesizer.playSelect();
              }}
              className={`px-5 py-2.5 rounded-xl text-xs font-mono uppercase tracking-widest font-bold transition-all flex items-center gap-2 ${
                activeTab === 'single'
                  ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-500/25'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              <Zap className="w-3.5 h-3.5" />
              Individual
            </button>
            <button
              onClick={() => {
                setActiveTab('multiplayer');
                fetchMultiplayerRooms();
                synthesizer.playSelect();
              }}
              className={`px-5 py-2.5 rounded-xl text-xs font-mono uppercase tracking-widest font-bold transition-all flex items-center gap-2 ${
                activeTab === 'multiplayer'
                  ? 'bg-[#00e676]/20 text-[#00e676] border border-[#00e676]/40 shadow-lg shadow-[#00e676]/10'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              <Users className="w-3.5 h-3.5" />
              Multijugador
              {rooms.length > 0 && (
                <span className="px-1.5 py-0.5 text-[9px] rounded-full bg-[#00e676]/20 text-[#00e676]">
                  {rooms.length}
                </span>
              )}
            </button>
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
        ) : activeTab === 'single' ? (
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
                  <div className="space-y-3 max-h-[300px] overflow-y-auto pr-1">
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
        ) : (
          /* === PESTAÑA MULTIJUGADOR === */
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
            {/* Columna Izquierda: Unirse por Código + Salas Activas */}
            <div className="lg:col-span-7 space-y-6">
              {mpError && (
                <div className="p-4 rounded-2xl bg-red-500/10 border border-red-500/30 text-red-300 text-xs font-mono">
                  ⚠️ {mpError}
                </div>
              )}

              {/* Unirse por Código */}
              <div className="p-6 bg-white/[0.02] border border-white/10 rounded-[28px] space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="p-2.5 bg-[#00e676]/15 text-[#00e676] rounded-xl">
                      <KeyRound className="w-5 h-5" />
                    </div>
                    <div>
                      <h3 className="text-base font-bold text-white uppercase tracking-tight">Unirse con Código de Nexo</h3>
                      <p className="text-[11px] text-gray-500">Ingresa el código de 6 caracteres compartido por otro Arquitecto.</p>
                    </div>
                  </div>
                </div>

                <div className="flex gap-3">
                  <input
                    type="text"
                    value={joinCode}
                    onChange={(e) => setJoinCode(e.target.value.toUpperCase())}
                    placeholder="EJ: NEO-42X"
                    maxLength={12}
                    className="flex-1 bg-black/50 border border-white/10 rounded-xl px-4 py-3 text-sm font-mono uppercase tracking-widest text-white focus:outline-none focus:border-[#00e676]/60"
                  />
                  <button
                    onClick={() => handleJoinRoom({ codigo_acceso: joinCode })}
                    disabled={!joinCode.trim()}
                    className="px-6 py-3 bg-[#00e676] hover:bg-[#00c853] disabled:opacity-40 text-black font-black text-xs uppercase tracking-widest rounded-xl transition-all flex items-center gap-2"
                  >
                    <span>Conectar</span>
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Lista de Salas Públicas / Propias */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Radio className="w-4 h-4 text-[#00e676] animate-pulse" />
                    <span className="text-xs font-mono text-gray-300 uppercase tracking-widest font-bold">
                      Realidades Compartidas Activas
                    </span>
                  </div>
                  <button
                    onClick={fetchMultiplayerRooms}
                    className="px-3 py-1.5 bg-white/5 hover:bg-white/10 rounded-xl text-[10px] font-mono uppercase tracking-widest text-gray-400 hover:text-white flex items-center gap-1.5 transition-all"
                  >
                    <RefreshCw className={`w-3 h-3 ${loadingRooms ? 'animate-spin' : ''}`} />
                    Actualizar
                  </button>
                </div>

                {rooms.length === 0 ? (
                  <div className="p-10 border border-dashed border-white/10 rounded-[28px] text-center space-y-2">
                    <Users className="w-8 h-8 text-gray-600 mx-auto" />
                    <p className="text-xs text-gray-400 font-medium">No hay salas públicas registradas todavía.</p>
                    <p className="text-[11px] text-gray-600">Crea una sala en el panel derecho para compartir tu realidad con otros jugadores.</p>
                  </div>
                ) : (
                  <div className="space-y-3 max-h-[380px] overflow-y-auto pr-1">
                    {rooms.map((room) => (
                      <div
                        key={room.game_id}
                        className="p-5 bg-white/[0.02] hover:bg-white/[0.04] border border-white/10 hover:border-[#00e676]/40 rounded-2xl flex flex-col sm:flex-row sm:items-center justify-between gap-4 transition-all"
                      >
                        <div className="space-y-1.5">
                          <div className="flex items-center gap-2.5 flex-wrap">
                            <span className="text-base font-black text-white tracking-tight">{room.nombre}</span>
                            <span className="px-2 py-0.5 rounded-md bg-indigo-500/20 border border-indigo-500/30 text-indigo-300 font-mono text-[10px] font-bold">
                              {room.codigo_acceso}
                            </span>
                            <span className="px-2 py-0.5 rounded-md bg-white/5 text-gray-400 font-mono text-[9px] uppercase">
                              {room.modo_juego === 'cooperativo' ? 'Co-Arquitectos' : 'Host + Poseedores'}
                            </span>
                            {!room.es_publica && (
                              <span className="px-2 py-0.5 rounded-md bg-amber-500/20 text-amber-300 font-mono text-[9px] uppercase flex items-center gap-1">
                                <Lock className="w-2.5 h-2.5" /> Privada
                              </span>
                            )}
                          </div>
                          <div className="flex items-center gap-4 text-[11px] text-gray-400 font-mono">
                            <span>Anfitrión: <strong className="text-gray-200">{room.host_username}</strong></span>
                            <span>•</span>
                            <span>Paso <strong className="text-white">{room.paso_actual || 0}</strong></span>
                            <span>•</span>
                            <span>Agentes: <strong className="text-indigo-400">{room.num_agentes || 0}</strong></span>
                          </div>
                        </div>

                        <div className="flex items-center gap-4">
                          <div className="text-right">
                            <div className="flex items-center gap-1.5 justify-end">
                              <span className={`w-2 h-2 rounded-full ${(room.online_count || 0) > 0 ? 'bg-[#00e676] animate-pulse' : 'bg-gray-600'}`} />
                              <span className="text-xs font-mono font-bold text-white">
                                {room.online_count || 0}/{room.max_jugadores || 8}
                              </span>
                            </div>
                            <span className="text-[9px] font-mono uppercase text-gray-500">En línea</span>
                          </div>

                          <button
                            onClick={() => handleJoinRoom({ game_id: room.game_id })}
                            className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs font-mono uppercase tracking-wider rounded-xl transition-all flex items-center gap-2"
                          >
                            <span>Entrar</span>
                            <ChevronRight className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Columna Derecha: Crear Nueva Sala Multijugador */}
            <div className="lg:col-span-5">
              <div className="p-8 bg-[#00e676]/[0.03] border border-[#00e676]/20 rounded-[35px] space-y-6 relative overflow-hidden">
                <div className="flex items-center gap-3">
                  <div className="p-3 bg-[#00e676]/20 rounded-2xl text-[#00e676]">
                    <PlusCircle className="w-6 h-6" />
                  </div>
                  <div>
                    <h3 className="text-xl font-bold text-white uppercase tracking-tight">Crear Sala Multijugador</h3>
                    <p className="text-[11px] text-gray-400">Inicia un mundo compartido en tiempo real</p>
                  </div>
                </div>

                <div className="space-y-4">
                  <div>
                    <label className="block text-[10px] font-mono uppercase tracking-widest text-gray-400 mb-1.5">
                      Nombre de la Realidad
                    </label>
                    <input
                      type="text"
                      value={roomName}
                      onChange={(e) => setRoomName(e.target.value)}
                      placeholder={`Nexo de ${username || 'Arquitecto'}`}
                      className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-[#00e676]/50 font-mono"
                    />
                  </div>

                  <div>
                    <label className="block text-[10px] font-mono uppercase tracking-widest text-gray-400 mb-1.5">
                      Modo de Intervención
                    </label>
                    <div className="grid grid-cols-2 gap-2">
                      <button
                        type="button"
                        onClick={() => setRoomMode('cooperativo')}
                        className={`p-3 rounded-xl border text-left transition-all ${
                          roomMode === 'cooperativo'
                            ? 'bg-indigo-500/20 border-indigo-500 text-white'
                            : 'bg-black/30 border-white/10 text-gray-400'
                        }`}
                      >
                        <div className="flex items-center gap-1.5 text-xs font-bold mb-0.5">
                          <Shield className="w-3.5 h-3.5 text-indigo-400" />
                          Co-Arquitectos
                        </div>
                        <p className="text-[10px] text-gray-400 leading-tight">
                          Todos pueden intervenir, invocar y poseer agentes.
                        </p>
                      </button>

                      <button
                        type="button"
                        onClick={() => setRoomMode('observador_poseedor')}
                        className={`p-3 rounded-xl border text-left transition-all ${
                          roomMode === 'observador_poseedor'
                            ? 'bg-indigo-500/20 border-indigo-500 text-white'
                            : 'bg-black/30 border-white/10 text-gray-400'
                        }`}
                      >
                        <div className="flex items-center gap-1.5 text-xs font-bold mb-0.5">
                          <Users className="w-3.5 h-3.5 text-[#00e676]" />
                          Host + Poseedores
                        </div>
                        <p className="text-[10px] text-gray-400 leading-tight">
                          El host controla el mundo; invitados poseen agentes.
                        </p>
                      </button>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <div className="flex justify-between text-[10px] font-mono uppercase tracking-widest mb-1.5">
                        <span className="text-gray-400">Agentes</span>
                        <span className="text-[#00e676] font-bold">{roomAgents}</span>
                      </div>
                      <input
                        type="range"
                        min={4}
                        max={36}
                        step={2}
                        value={roomAgents}
                        onChange={(e) => setRoomAgents(parseInt(e.target.value))}
                        className="w-full h-1.5 bg-white/10 rounded-full appearance-none cursor-pointer accent-[#00e676]"
                      />
                    </div>

                    <div>
                      <div className="flex justify-between text-[10px] font-mono uppercase tracking-widest mb-1.5">
                        <span className="text-gray-400">Máx. Jugadores</span>
                        <span className="text-indigo-400 font-bold">{roomMaxPlayers}</span>
                      </div>
                      <input
                        type="range"
                        min={2}
                        max={16}
                        step={1}
                        value={roomMaxPlayers}
                        onChange={(e) => setRoomMaxPlayers(parseInt(e.target.value))}
                        className="w-full h-1.5 bg-white/10 rounded-full appearance-none cursor-pointer accent-indigo-500"
                      />
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={() => setRoomPublic(!roomPublic)}
                    className="w-full flex items-center justify-between p-3 rounded-xl bg-black/30 border border-white/10 text-xs font-mono"
                  >
                    <span className="flex items-center gap-2 text-gray-300">
                      {roomPublic ? <Unlock className="w-4 h-4 text-[#00e676]" /> : <Lock className="w-4 h-4 text-amber-400" />}
                      {roomPublic ? 'Sala Pública (visible en el lobby)' : 'Sala Privada (solo con código)'}
                    </span>
                    <span className={`text-[10px] uppercase font-bold ${roomPublic ? 'text-[#00e676]' : 'text-amber-400'}`}>
                      {roomPublic ? 'PÚBLICA' : 'PRIVADA'}
                    </span>
                  </button>

                  <button
                    onClick={handleCreateRoom}
                    className="w-full py-4 bg-[#00e676] hover:bg-[#00c853] text-black font-black text-xs uppercase tracking-[0.2em] rounded-2xl transition-all shadow-xl shadow-[#00e676]/15 active:scale-[0.98] flex items-center justify-center gap-3"
                  >
                    <Globe className="w-4 h-4" />
                    Crear e Iniciar Sala
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </motion.div>

      {/* Footer Metadatos */}
      <div className="fixed bottom-4 w-full flex justify-center opacity-20 pointer-events-none">
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
      <div
        className={`p-4 rounded-2xl transition-all ${
          disabled
            ? 'bg-white/5 text-gray-600'
            : variant === 'danger'
            ? 'bg-red-500/10 text-red-400 group-hover:bg-red-500/20'
            : 'bg-indigo-500/10 text-indigo-400 group-hover:bg-indigo-500/20'
        }`}
      >
        <Icon className="w-6 h-6" />
      </div>

      <div className="flex-1 pr-8">
        <div className="flex items-center gap-3 mb-1">
          <h4 className="text-lg font-bold text-white uppercase tracking-tight">{title}</h4>
          {badge && (
            <span className="px-2 py-0.5 bg-indigo-500/20 text-indigo-400 text-[8px] font-black rounded-full border border-indigo-500/20">
              {badge}
            </span>
          )}
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
