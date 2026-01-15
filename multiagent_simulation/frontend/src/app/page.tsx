"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { ArrowRight, Cpu, Activity, ShieldCheck } from "lucide-react";

export default function Home() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username) return;
    setLoading(true);

    try {
      // Intentar login primero
      const res = await fetch("http://localhost:8000/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password: "password" }),
      });
      const data = await res.json();

      if (data.status === "success") {
        localStorage.setItem("user_id", data.user_id);
        localStorage.setItem("username", data.username);
        router.push("/game");
      } else {
        // Si falla, intentar registro
        const regRes = await fetch("http://localhost:8000/auth/register", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username, password: "password" }),
        });
        const regData = await regRes.json();
        if (regData.status === "success") {
          localStorage.setItem("user_id", regData.user_id);
          localStorage.setItem("username", username);
          router.push("/game");
        }
      }
    } catch (error) {
      console.error("Login error:", error);
    } finally {
      setLoading(false);
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
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.8, ease: "easeOut" }}
        className="relative z-10 w-full max-w-md p-1"
      >
        <div className="glass-panel rounded-2xl p-8 backdrop-blur-xl border border-white/10 shadow-2xl relative overflow-hidden group">

          {/* Decorative Border Glow */}
          <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-[#7c4dff] to-transparent opacity-50" />

          {/* Header */}
          <div className="text-center mb-10">
            <motion.div
              initial={{ y: -20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.2 }}
              className="inline-flex items-center justify-center p-3 mb-4 rounded-xl bg-white/5 ring-1 ring-white/10"
            >
              <Cpu className="w-8 h-8 text-[#7c4dff]" />
            </motion.div>
            <h1 className="text-4xl font-bold tracking-tight mb-2 font-mono">
              <span className="text-white">MUNDO</span>
              <span className="text-gradient">IA</span>
            </h1>
            <p className="text-sm text-gray-400 font-mono uppercase tracking-[0.3em]">
              Sistema de Simulación Multiagente
            </p>
          </div>

          {/* Form */}
          <form onSubmit={handleLogin} className="space-y-6">
            <div className="space-y-2">
              <label htmlFor="username" className="text-[10px] font-bold text-[#7c4dff] uppercase tracking-widest ml-1 flex items-center gap-2">
                <Activity className="w-3 h-3" /> Identificación de Usuario
              </label>
              <div className="relative group/input">
                <input
                  id="username"
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="w-full bg-[#0a0b10]/50 border border-white/10 rounded-xl px-5 py-4 text-white placeholder:text-gray-600 focus:outline-none focus:border-[#7c4dff] focus:ring-1 focus:ring-[#7c4dff]/50 transition-all font-mono text-sm"
                  placeholder="Ingrese nombre de agente..."
                  autoComplete="off"
                  autoFocus
                />
                <div className="absolute right-4 top-1/2 -translate-y-1/2 opacity-0 group-focus-within/input:opacity-100 transition-opacity">
                  <div className="w-2 h-2 bg-[#00e676] rounded-full animate-pulse" />
                </div>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading || !username}
              className="w-full py-4 px-6 rounded-xl bg-gradient-to-r from-[#7c4dff] to-[#651fff] hover:from-[#651fff] hover:to-[#7c4dff] text-white font-bold tracking-wide shadow-lg shadow-[#7c4dff]/25 hover:shadow-[#7c4dff]/40 hover:-translate-y-0.5 active:translate-y-0 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-3 overflow-hidden relative"
            >
              {loading ? (
                <>
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  <span className="font-mono text-sm">INICIALIZANDO...</span>
                </>
              ) : (
                <>
                  <span>ACCEDER AL SISTEMA</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          {/* Footer Stats */}
          <div className="mt-10 pt-6 border-t border-white/5 grid grid-cols-2 gap-4">
            <div className="flex items-center gap-3 p-3 rounded-lg bg-white/5 border border-white/5">
              <div className="p-1.5 rounded bg-[#00e676]/10 text-[#00e676]">
                <Activity className="w-3.5 h-3.5" />
              </div>
              <div className="flex flex-col">
                <span className="text-[9px] text-gray-500 uppercase tracking-wider">Estado</span>
                <span className="text-xs font-mono text-white/90">OPERATIVO</span>
              </div>
            </div>
            <div className="flex items-center gap-3 p-3 rounded-lg bg-white/5 border border-white/5">
              <div className="p-1.5 rounded bg-[#7c4dff]/10 text-[#7c4dff]">
                <ShieldCheck className="w-3.5 h-3.5" />
              </div>
              <div className="flex flex-col">
                <span className="text-[9px] text-gray-500 uppercase tracking-wider">Seguridad</span>
                <span className="text-xs font-mono text-white/90">NIVEL 5</span>
              </div>
            </div>
          </div>

        </div>

        <p className="text-center mt-6 text-[10px] text-gray-600 font-mono">
          © 2026 CORPORACIÓN MUNDO IA. TODOS LOS DERECHOS RESERVADOS.
        </p>
      </motion.div>
    </main>
  );
}

