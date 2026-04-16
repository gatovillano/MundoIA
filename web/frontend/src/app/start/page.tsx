"use client";

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import useGameStore from '@/store/useGameStore';
import { getHttpUrl } from '@/utils/apiConfig';

export default function StartPage() {
  const router = useRouter();
  const { isAuthenticated, userId, username } = useGameStore();
  const [loading, setLoading] = useState(false);
  const [savedGames, setSavedGames] = useState<any[]>([]);
  const [quickAgents, setQuickAgents] = useState<number>(6);
  const [quickSave, setQuickSave] = useState<boolean>(false);

  useEffect(() => {
    if (!isAuthenticated) router.push('/auth');
  }, [isAuthenticated, router]);

  const loadSaved = async () => {
    if (!userId) return;
    setLoading(true);
    try {
      const res = await fetch(getHttpUrl(`/games/list/${userId}`));
      if (!res.ok) throw new Error('fetch failed');
      const data = await res.json();
      setSavedGames(data.games || []);
    } catch (e) {
      console.error(e);
      alert('Error obteniendo partidas guardadas');
    } finally { setLoading(false); }
  };

  const handleLoad = async () => {
    if (!userId) return;
    setLoading(true);
    try {
      const res = await fetch(getHttpUrl('/games/load'), {
        method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ user_id: userId })
      });
      if (!res.ok) throw new Error('load failed');
      router.push('/game');
    } catch (e) {
      console.error(e);
      alert('Error cargando la partida');
    } finally { setLoading(false); }
  };

  const handleNew = async () => {
    if (!userId) return;
    setLoading(true);
    try {
      const res = await fetch(getHttpUrl('/game/control'), {
        method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ user_id: userId, action: 'reset' })
      });
      if (!res.ok) throw new Error('new failed');
      router.push('/game');
    } catch (e) {
      console.error(e);
      alert('Error creando nueva partida');
    } finally { setLoading(false); }
  };

  const handleQuickPlay = async () => {
    if (!userId) return;
    setLoading(true);
    try {
      const res = await fetch(getHttpUrl('/games/quickplay'), {
        method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ user_id: userId, num_agents: quickAgents, save: quickSave })
      });
      if (!res.ok) throw new Error('quickplay failed');
      router.push('/game');
    } catch (e) {
      console.error(e);
      alert('Error lanzando Partida Rápida');
    } finally { setLoading(false); }
  };

  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-[#030305] text-[#e0e0e0] relative overflow-hidden">
      <div className="glass-panel rounded-2xl p-8 backdrop-blur-xl border border-white/10 shadow-2xl w-full max-w-2xl">
        <h2 className="text-2xl font-bold mb-4">Bienvenido, {username || 'Observador'}</h2>
        <div className="grid grid-cols-3 gap-4">
          <button onClick={loadSaved} className="p-4 bg-white/5 rounded-lg">Cargar partida</button>
          <button onClick={handleNew} className="p-4 bg-white/5 rounded-lg">Iniciar nueva partida</button>
          <button onClick={() => setQuickAgents(6) || setQuickSave(false)} className="p-4 bg-white/5 rounded-lg">Partida Rápida</button>
        </div>

        <div className="mt-6">
          <h3 className="font-bold">Partida Rápida (Opciones)</h3>
          <div className="flex items-center gap-2 mt-2">
            <label className="text-sm">Agentes:</label>
            <input type="number" min={1} max={40} value={quickAgents} onChange={(e)=>setQuickAgents(Number(e.target.value))} className="w-20 bg-black/40 rounded px-2 py-1" />
            <label className="ml-4"><input type="checkbox" checked={quickSave} onChange={(e)=>setQuickSave(e.target.checked)} /> Guardar al iniciar</label>
            <button onClick={handleQuickPlay} className="ml-auto p-2 bg-[#7c4dff] rounded text-white">Iniciar</button>
          </div>
        </div>

        <div className="mt-6">
          <h4 className="font-bold">Partidas guardadas</h4>
          <div className="mt-2">
            {loading && <div>Consultando...</div>}
            {!loading && savedGames.length === 0 && <div>No hay partidas guardadas.</div>}
            {!loading && savedGames.map((g, i) => (
              <div key={i} className="p-2 border rounded mb-2 flex items-center justify-between">
                <div>
                  <div>Turno: {g.paso_actual}</div>
                  <div>Puntos: {g.score}</div>
                </div>
                <div>
                  <button onClick={handleLoad} className="px-3 py-1 bg-white/5 rounded">Cargar</button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </main>
  );
}
