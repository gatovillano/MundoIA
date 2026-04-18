"use client";

import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Cpu, Activity, ShieldCheck } from "lucide-react";
import { synthesizer } from "@/utils/SoundSynthesizer";
import useGameStore from "@/store/useGameStore";
import RankingPanel from "@/components/RankingPanel";
import { useEffect } from "react";

export default function Home() {
  const router = useRouter();
  const { isAuthenticated, connect, socket } = useGameStore();

  useEffect(() => {
    // Intentar conectar para obtener ranking si no hay socket activo
    if (!socket) {
      connect();
    }
  }, [socket, connect]);

  const handleEnter = () => {
    synthesizer.playSelect();
    if (isAuthenticated) {
      router.push("/game");
    } else {
      router.push("/auth");
    }
  };

  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-[#030305] text-[#e0e0e0] relative overflow-hidden">

      {/* Background Ambience */}
      <div className="absolute inset-0 z-0">
        <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] bg-[#7c4dff] rounded-full blur-[150px] opacity-20 animate-pulse" />
        <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] bg-[#00e676] rounded-full blur-[150px] opacity-10" />
        <div className="absolute inset-0 bg-[url('/grid.svg')] opacity-5" />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 1 }}
        className="relative z-10 w-full max-w-6xl px-6 grid grid-cols-1 lg:grid-cols-12 gap-12 items-center"
      >
        {/* Lado Izquierdo: Branding y Acceso */}
        <div className="lg:col-span-5 space-y-8 flex flex-col items-center lg:items-start text-center lg:text-left">
          <div className="space-y-4">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ delay: 0.2 }}
              className="inline-flex items-center justify-center p-4 rounded-3xl bg-white/5 ring-1 ring-white/10"
            >
              <Cpu className="w-12 h-12 text-[#7c4dff]" />
            </motion.div>
            <h1 className="text-6xl font-bold tracking-tighter mb-2 font-mono">
              <span className="text-white">MUNDO</span>
              <span className="text-gradient">IA</span>
            </h1>
            <p className="text-lg text-gray-400 font-mono uppercase tracking-[0.4em]">
              Sistema de Simulación Multiagente
            </p>
            <p className="max-w-md text-gray-500 font-serif italic text-sm leading-relaxed">
              "Donde cada decisión de las máquinas esculpe la historia de una civilización emergente. Observa, construye y guía."
            </p>
          </div>

          <div className="w-full max-w-sm space-y-4">
            <button
              onClick={handleEnter}
              className="w-full py-5 px-8 rounded-2xl bg-gradient-to-r from-[#7c4dff] to-[#651fff] hover:from-[#651fff] hover:to-[#7c4dff] text-white font-black text-lg tracking-widest shadow-[0_0_30px_rgba(124,77,255,0.3)] hover:shadow-[0_0_40px_rgba(124,77,255,0.5)] hover:-translate-y-1 active:translate-y-0 transition-all flex items-center justify-center gap-4 overflow-hidden"
            >
              <span>{isAuthenticated ? "CONTINUAR SIMULACIÓN" : "ACCEDER AL SISTEMA"}</span>
            </button>

            <div className="flex justify-between items-center gap-4 px-2">
              <div className="flex items-center gap-2">
                <Activity className="w-4 h-4 text-[#00e676]" />
                <span className="text-[10px] font-mono text-gray-400">SERVER: OK</span>
              </div>
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-[#7c4dff]" />
                <span className="text-[10px] font-mono text-gray-400">ARCHITECT AUTH: ENFORCED</span>
              </div>
            </div>
          </div>
        </div>

        {/* Lado Derecho: Ranking */}
        <div className="lg:col-span-1" /> {/* Divisor / Espaciador */}

        <div className="lg:col-span-6 flex flex-col gap-6">
          <RankingPanel />
        </div>

      </motion.div>

      <p className="fixed bottom-6 w-full text-center text-[10px] text-gray-700 font-mono tracking-widest opacity-50">
        © 2026 KOGNITO AI LABS. PROTOCOLO DE CONSCIENCIA EMERGENTE.
      </p>
    </main>
  );
}
