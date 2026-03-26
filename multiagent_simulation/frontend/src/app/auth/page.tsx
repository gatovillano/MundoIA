"use client";

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import useGameStore from '@/store/useGameStore';
import { motion } from 'framer-motion';
import { Cpu, User, Lock, ArrowRight, Activity, ShieldCheck } from 'lucide-react';
import { synthesizer } from '@/utils/SoundSynthesizer';

export default function AuthPage() {
  const [isLogin, setIsLogin] = useState(true);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();
  const { login, isAuthenticated } = useGameStore();

  useEffect(() => {
    if (isAuthenticated) {
      router.push('/game');
    }
  }, [isAuthenticated, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);
    synthesizer.playSelect();

    // Determinar host dinámicamente
    const protocol = window.location.protocol;
    let host = window.location.host;
    
    // Si estamos en producción
    if (window.location.hostname === 'mundoia.cuerpolibre.cl') {
      host = 'api-mundoia.cuerpolibre.cl';
    } 
    // Si estamos en desarrollo local (PC o Capacitor/Expo)
    else if (window.location.hostname === 'localhost' || window.location.hostname.match(/^\d+\.\d+\.\d+\.\d+$/) || window.location.hostname.includes('capacitor')) {
      host = localStorage.getItem('MUNDOIA_API_HOST') || 'localhost:8005';
    }

    const url = isLogin ? '/auth/login' : '/auth/register';
    const body = JSON.stringify({ username, password });

    try {
      const response = await fetch(`${protocol}//${host}${url}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body,
      });

      const data = await response.json();

      if (response.ok) {
        login(data.user_id, data.username);
        router.push('/game');
      } else {
        setError(data.detail || 'Ocurrió un error');
        synthesizer.playAlert();
      }
    } catch (err) {
      setError('No se pudo conectar con el servidor');
      synthesizer.playAlert();
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-[#030305] text-[#e0e0e0] relative overflow-hidden">

      {/* Background Ambience (Igual a Home) */}
      <div className="absolute inset-0 z-0">
        <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] bg-[#7c4dff] rounded-full blur-[150px] opacity-20 animate-pulse" />
        <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] bg-[#00e676] rounded-full blur-[150px] opacity-10" />
        <div className="absolute inset-0 bg-[url('/grid.svg')] opacity-5" />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="relative z-10 w-full max-w-md p-1"
      >
        <div className="glass-panel rounded-2xl p-8 backdrop-blur-xl border border-white/10 shadow-2xl relative overflow-hidden group">

          {/* Decorative Border Glow */}
          <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-[#7c4dff] to-transparent opacity-50" />

          {/* Header */}
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center p-3 mb-4 rounded-xl bg-white/5 ring-1 ring-white/10">
              <Cpu className="w-8 h-8 text-[#7c4dff]" />
            </div>
            <h1 className="text-3xl font-bold tracking-tight mb-2 font-mono">
              {isLogin ? 'INICIAR SESIÓN' : 'REGISTRARSE'}
            </h1>
            <p className="text-[10px] text-gray-400 font-mono uppercase tracking-[0.3em]">
              Autenticación de Observador
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-2">
              <label className="text-[10px] font-bold text-gray-500 uppercase tracking-widest flex items-center gap-2">
                <User className="w-3 h-3 text-[#7c4dff]" /> Usuario
              </label>
              <input
                type="text"
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:border-[#7c4dff]/50 focus:bg-black/60 focus:outline-none transition-all font-mono"
                placeholder="Identificador único..."
              />
            </div>

            <div className="space-y-2">
              <label className="text-[10px] font-bold text-gray-500 uppercase tracking-widest flex items-center gap-2">
                <Lock className="w-3 h-3 text-[#7c4dff]" /> Contraseña
              </label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:border-[#7c4dff]/50 focus:bg-black/60 focus:outline-none transition-all font-mono"
                placeholder="********"
              />
            </div>

            {error && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                className="text-[10px] text-red-400 bg-red-500/10 border border-red-500/20 p-3 rounded-lg flex items-center gap-2 font-mono"
              >
                <div className="w-1 h-1 bg-red-500 rounded-full animate-pulse" />
                {error}
              </motion.div>
            )}

            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-4 rounded-xl bg-gradient-to-r from-[#7c4dff] to-[#651fff] hover:from-[#651fff] hover:to-[#7c4dff] text-white font-bold tracking-widest text-[11px] uppercase shadow-lg shadow-[#7c4dff]/25 hover:shadow-[#7c4dff]/40 transition-all flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {isLoading ? (
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <>
                  <span>{isLogin ? 'ACCEDER AL NODO' : 'CREAR IDENTIDAD'}</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          <div className="mt-8 text-center">
            <button
              onClick={() => {
                setIsLogin(!isLogin);
                setError('');
                synthesizer.playSelect();
              }}
              className="text-[10px] text-gray-500 hover:text-[#7c4dff] font-mono uppercase tracking-[0.2em] transition-colors"
            >
              {isLogin
                ? '¿No tienes cuenta? Registra tu ADN digital'
                : '¿Ya eres observador? Inicia sesión aquí'}
            </button>
          </div>

          {/* Footer Stats (Consistencia) */}
          <div className="mt-8 pt-6 border-t border-white/5 grid grid-cols-2 gap-4">
            <div className="flex items-center gap-3 p-3 rounded-lg bg-white/2 border border-white/5">
              <Activity className="w-3.5 h-3.5 text-[#00e676]" />
              <div className="flex flex-col">
                <span className="text-[8px] text-gray-600 uppercase">SERVER</span>
                <span className="text-[10px] font-mono text-white/50">ONLINE</span>
              </div>
            </div>
            <div className="flex items-center gap-3 p-3 rounded-lg bg-white/2 border border-white/5">
              <ShieldCheck className="w-3.5 h-3.5 text-[#7c4dff]" />
              <div className="flex flex-col">
                <span className="text-[8px] text-gray-600 uppercase">ENCRIP</span>
                <span className="text-[10px] font-mono text-white/50">SSL-AES</span>
              </div>
            </div>
          </div>
        </div>

        <p className="text-center mt-6 text-[10px] text-gray-700 font-mono">
          SISTEMA DE CONTROL DE ACCESO v2.4.0
        </p>
      </motion.div>
    </main>
  );
}
