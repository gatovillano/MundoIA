"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import { Send, Search, MessageCircle, User, Bot, Loader2, ArrowLeft, Sparkles } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import ReactMarkdown from "react-markdown";
import useGameStore from "@/store/useGameStore";

interface ChatMessage {
    role: "user" | "agent";
    content: string;
    timestamp: number;
}

interface AgentChatInfo {
    id: string;
    rol: string;
    profesion: string | null;
    grupo_id: string | null;
    reputacion: number;
    personalidad_resumen: string;
    pensamiento: string;
    color: string;
    esta_vivo: boolean;
}

interface ChatPanelProps {
    userId: string;
    onClose: () => void;
}

export default function ChatPanel({ userId, onClose }: ChatPanelProps) {
    const { agents, selectAgent } = useGameStore();
    const [chatAgents, setChatAgents] = useState<AgentChatInfo[]>([]);
    const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [inputText, setInputText] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [isLoadingAgents, setIsLoadingAgents] = useState(true);
    const [searchQuery, setSearchQuery] = useState("");
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLInputElement>(null);

    const getApiHost = useCallback(() => {
        const protocol = window.location.protocol;
        let host = window.location.host;
        if (window.location.hostname === "mundoia.cuerpolibre.cl") {
            host = "api-mundoia.cuerpolibre.cl";
        } else if (window.location.hostname === "localhost" || window.location.hostname.includes("capacitor")) {
            host = localStorage.getItem("MUNDOIA_API_HOST") || "api-mundoia.cuerpolibre.cl";
        }
        return `${protocol}//${host}`;
    }, []);

     // Cargar lista de agentes
     useEffect(() => {
         const fetchAgents = async () => {
             try {
                 const url = `${getApiHost()}/chat/${userId}/agents`;
                 console.log('🔍 [ChatPanel] Fetching agents from:', url);
                 const res = await fetch(url);
                 console.log('📥 [ChatPanel] Response status:', res.status, res.ok);
                 if (res.ok) {
                     const data = await res.json();
                     console.log('✅ [ChatPanel] Agents data:', data);
                     const aliveAgents = data.agents.filter((a: AgentChatInfo) => a.esta_vivo);
                     console.log('🧬 [ChatPanel] Alive agents count:', aliveAgents.length);
                     setChatAgents(aliveAgents);
                 } else {
                     const errText = await res.text();
                     console.error('❌ [ChatPanel] Error response:', res.status, errText);
                     setChatAgents([]);
                 }
             } catch (e) {
                 console.error("🔥 [ChatPanel] Fetch exception:", e);
                 setChatAgents([]);
             } finally {
                 setIsLoadingAgents(false);
             }
         };
         fetchAgents();
     }, [userId, getApiHost]);

    // Actualizar agentes periódicamente cuando agents cambia en el store
    useEffect(() => {
        if (agents.length > 0) {
            const fetchAgents = async () => {
                try {
                    const res = await fetch(`${getApiHost()}/chat/${userId}/agents`);
                    if (res.ok) {
                        const data = await res.json();
                        const aliveAgents = data.agents.filter((a: AgentChatInfo) => a.esta_vivo);
                        setChatAgents(aliveAgents);
                    }
                } catch (e) { /* silent */ }
            };
            fetchAgents();
        }
    }, [agents, userId, getApiHost, selectedAgentId]);

    // Cargar historial al seleccionar agente
    useEffect(() => {
        if (!selectedAgentId) return;
        const fetchHistory = async () => {
            try {
                const res = await fetch(`${getApiHost()}/chat/${userId}/${selectedAgentId}/history`);
                if (res.ok) {
                    const data = await res.json();
                    setMessages(data.messages || []);
                }
            } catch (e) {
                console.error("Error fetching history:", e);
            }
        };
        fetchHistory();
    }, [selectedAgentId, userId, getApiHost]);

    // Auto-scroll
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    // Focus input when agent selected
    useEffect(() => {
        if (selectedAgentId) {
            setTimeout(() => inputRef.current?.focus(), 100);
        }
    }, [selectedAgentId]);

    const sendMessage = async () => {
        console.log('🔍 [ChatPanel] sendMessage called', { inputText, selectedAgentId, isLoading, userId });
        if (!inputText.trim() || !selectedAgentId || isLoading) {
            console.warn('⚠️ [ChatPanel] sendMessage blocked', { hasText: !!inputText.trim(), hasAgent: !!selectedAgentId, isLoading });
            return;
        }

        const userMsg: ChatMessage = {
            role: "user",
            content: inputText.trim(),
            timestamp: Date.now() / 1000,
        };
        setMessages((prev) => [...prev, userMsg]);
        setInputText("");
        setIsLoading(true);

        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 60000);

        try {
            const url = `${getApiHost()}/chat/${userId}/${selectedAgentId}`;
            console.log('🚀 [ChatPanel] POST to:', url, { message: userMsg.content.slice(0, 50) });
            const res = await fetch(url, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: userMsg.content }),
                signal: controller.signal,
            });
            clearTimeout(timeout);
            console.log('📥 [ChatPanel] Response status:', res.status, res.ok);
            if (res.ok) {
                const data = await res.json();
                console.log('✅ [ChatPanel] Response data:', data);
                const agentMsg: ChatMessage = {
                    role: "agent",
                    content: data.response,
                    timestamp: Date.now() / 1000,
                };
                setMessages((prev) => [...prev, agentMsg]);
            } else {
                const errData = await res.json().catch(() => ({}));
                console.error('❌ [ChatPanel] Error response:', errData);
                setMessages((prev) => [
                    ...prev,
                    { role: "agent", content: `*Error: ${errData.detail || "No se pudo conectar con el agente"}*`, timestamp: Date.now() / 1000 },
                ]);
            }
        } catch (e: any) {
            console.error('🔥 [ChatPanel] Fetch exception:', e);
            const isTimeout = e?.name === "AbortError";
            setMessages((prev) => [
                ...prev,
                { role: "agent", content: isTimeout ? "*El agente tardó demasiado en responder. Inténtalo de nuevo.*" : "*El agente no responde. Verifica la conexión.*", timestamp: Date.now() / 1000 },
            ]);
        } finally {
            clearTimeout(timeout);
            setIsLoading(false);
        }
    };

    const filteredAgents = chatAgents.filter(
        (a) =>
            a.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
            (a.profesion && a.profesion.toLowerCase().includes(searchQuery.toLowerCase())) ||
            (a.rol && a.rol.toLowerCase().includes(searchQuery.toLowerCase()))
    );

    const selectedAgent = chatAgents.find((a) => a.id === selectedAgentId);

    console.log('🔍 [ChatPanel] Debug:', { userId, selectedAgentId, chatAgentsCount: chatAgents.length, filteredCount: filteredAgents.length });

    const getPersonalityEmoji = (resumen: string) => {
        if (resumen.includes("amabilidad")) return "";
        if (resumen.includes("hostilidad")) return "⚔️";
        if (resumen.includes("curiosidad")) return "";
        if (resumen.includes("competitividad")) return "";
        if (resumen.includes("extroversión")) return "";
        return "";
    };

    return (
        <div className="flex flex-col h-full">
            {/* Header interno */}
            <div className="flex items-center gap-3 px-1 pb-4 border-b border-white/5">
                {selectedAgentId ? (
                    <>
                        <button
                            onClick={() => {
                                setSelectedAgentId(null);
                                setMessages([]);
                            }}
                            className="p-2 hover:bg-white/10 rounded-xl transition-all text-white/50 hover:text-white"
                        >
                            <ArrowLeft className="w-4 h-4" />
                        </button>
                        <div
                            className="w-3 h-3 rounded-full shrink-0"
                            style={{ backgroundColor: selectedAgent?.color || "#fff" }}
                        />
                        <div className="min-w-0">
                            <h3 className="text-sm font-bold text-white truncate">{selectedAgentId}</h3>
                            <p className="text-[9px] text-white/40 truncate">
                                {selectedAgent?.profesion || selectedAgent?.rol || "Ciudadano"} — {selectedAgent?.personalidad_resumen}
                            </p>
                        </div>
                    </>
                ) : (
                    <>
                        <MessageCircle className="w-5 h-5 text-cyan-400" />
                        <div>
                            <h3 className="text-sm font-bold text-white">Chat con Agentes</h3>
                            <p className="text-[9px] text-white/40">{chatAgents.length} agentes disponibles</p>
                        </div>
                    </>
                )}
            </div>

            <AnimatePresence mode="wait">
                {!selectedAgentId ? (
                    /* ──── LISTA DE CONTACTOS ──── */
                    <motion.div
                        key="list"
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: -20 }}
                        className="flex-1 flex flex-col min-h-0"
                    >
                        {/* Buscador */}
                        <div className="relative mt-4 mb-3">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30" />
                            <input
                                type="text"
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                placeholder="Buscar agente..."
                                className="w-full pl-10 pr-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-xs text-white placeholder:text-white/20 focus:border-cyan-500/30 focus:outline-none transition-all"
                            />
                        </div>

                        {/* Lista */}
                        <div className="flex-1 overflow-y-auto custom-scrollbar space-y-1">
                            {isLoadingAgents ? (
                                <div className="flex items-center justify-center py-10">
                                    <Loader2 className="w-5 h-5 text-cyan-400 animate-spin" />
                                </div>
                            ) : filteredAgents.length === 0 ? (
                                <div className="text-center py-10 text-white/20 text-xs">
                                    No se encontraron agentes vivos
                                </div>
                            ) : (
                                filteredAgents.map((agent) => (
                                    <button
                                        key={agent.id}
                                        onClick={() => setSelectedAgentId(agent.id)}
                                        className="w-full flex items-center gap-3 p-3 rounded-xl hover:bg-white/5 transition-all group text-left"
                                    >
                                        <div className="relative">
                                            <div
                                                className="w-10 h-10 rounded-xl flex items-center justify-center text-white font-bold text-xs border border-white/10"
                                                style={{
                                                    backgroundColor: `${agent.color}20`,
                                                    borderColor: `${agent.color}40`,
                                                }}
                                            >
                                                {agent.id.replace(/[^a-zA-Z0-9]/g, "").slice(0, 3).toUpperCase()}
                                            </div>
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-2">
                                                <span className="text-xs font-bold text-white truncate">{agent.id}</span>
                                                <span className="text-[9px] text-white/30">
                                                    {getPersonalityEmoji(agent.personalidad_resumen)}
                                                </span>
                                            </div>
                                            <p className="text-[10px] text-white/40 truncate">
                                                {agent.profesion || agent.rol} — {agent.personalidad_resumen}
                                            </p>
                                            <p className="text-[9px] text-white/20 truncate mt-0.5 italic">
                                                {agent.pensamiento.slice(0, 60)}...
                                            </p>
                                        </div>
                                        <div
                                            className="w-2 h-2 rounded-full shrink-0"
                                            style={{ backgroundColor: agent.color }}
                                        />
                                    </button>
                                ))
                            )}
                        </div>
                    </motion.div>
                ) : (
                    /* ──── VISTA DE CONVERSACIÓN ──── */
                    <motion.div
                        key="chat"
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: 20 }}
                        className="flex-1 flex flex-col min-h-0 mt-3"
                    >
                        {/* Header con botón volver */}
                        <div className="flex items-center gap-2 mb-3">
                            <button
                                onClick={() => setSelectedAgentId(null)}
                                className="p-1.5 hover:bg-white/10 rounded-lg transition-colors text-white/50 hover:text-white"
                            >
                                ← Volver
                            </button>
                            <div className="flex items-center gap-2 px-2">
                                <div
                                    className="w-2 h-2 rounded-full"
                                    style={{ backgroundColor: selectedAgent?.color }}
                                />
                                <span className="text-xs font-bold text-white">{selectedAgentId}</span>
                            </div>
                        </div>

                        {/* Info del agente */}
                        <div className="mb-3 p-3 bg-white/[0.02] rounded-xl border border-white/5">
                            <div className="flex items-center gap-2 mb-1">
                                <Sparkles className="w-3 h-3 text-yellow-400/60" />
                                <span className="text-[9px] font-bold uppercase tracking-widest text-white/30">
                                    Pensamiento actual
                                </span>
                            </div>
                            <p className="text-[10px] text-white/50 italic leading-relaxed">
                                &ldquo;{selectedAgent?.pensamiento || "Procesando..."}&rdquo;
                            </p>
                        </div>

                        {/* Mensajes */}
                        <div className="flex-1 overflow-y-auto custom-scrollbar space-y-3 pr-1">
                            {messages.length === 0 && (
                                <div className="flex flex-col items-center justify-center h-full text-center">
                                    <div
                                        className="w-16 h-16 rounded-2xl flex items-center justify-center mb-3 border border-white/10"
                                        style={{ backgroundColor: `${selectedAgent?.color}15` }}
                                    >
                                        <MessageCircle className="w-6 h-6 text-white/30" />
                                    </div>
                                    <p className="text-xs text-white/30 font-medium">
                                        Escribe un mensaje para {selectedAgentId}
                                    </p>
                                    <p className="text-[10px] text-white/15 mt-1">
                                        El agente responderá según su personalidad
                                    </p>
                                </div>
                            )}

                            {messages.map((msg, i) => (
                                <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                                    <div
                                        className={`max-w-[85%] rounded-2xl px-4 py-2.5 ${
                                            msg.role === "user"
                                                ? "bg-cyan-500/15 border border-cyan-500/20 text-cyan-100"
                                                : "bg-white/5 border border-white/10 text-white/80"
                                        }`}
                                    >
                                        <div className="flex items-center gap-1.5 mb-1">
                                            {msg.role === "user" ? (
                                                <User className="w-3 h-3 text-cyan-400" />
                                            ) : (
                                                <Bot className="w-3 h-3" style={{ color: selectedAgent?.color }} />
                                            )}
                                            <span className="text-[8px] font-bold uppercase tracking-widest text-white/30">
                                                {msg.role === "user" ? "Tú" : selectedAgentId}
                                            </span>
                                        </div>
                                        <div className="text-xs leading-relaxed break-words">
                                            <ReactMarkdown>{msg.content}</ReactMarkdown>
                                        </div>
                                    </div>
                                </div>
                            ))}

                            {isLoading && (
                                <div className="flex justify-start">
                                    <div className="bg-white/5 border border-white/10 rounded-2xl px-4 py-3 flex items-center gap-2">
                                        <Loader2 className="w-3.5 h-3.5 text-white/40 animate-spin" />
                                        <span className="text-[10px] text-white/30 italic">
                                            {selectedAgentId} está pensando...
                                        </span>
                                    </div>
                                </div>
                            )}

                            <div ref={messagesEndRef} />
                        </div>

                        {/* Input */}
                        <div className="mt-3 relative">
                            <input
                                ref={inputRef}
                                type="text"
                                value={inputText}
                                onChange={(e) => setInputText(e.target.value)}
                                onKeyDown={(e) => e.key === "Enter" && sendMessage()}
                                placeholder={`Mensaje a ${selectedAgentId}...`}
                                disabled={isLoading}
                                className="w-full pr-12 pl-4 py-3 bg-white/5 border border-white/10 rounded-xl text-xs text-white placeholder:text-white/20 focus:border-cyan-500/30 focus:outline-none transition-all disabled:opacity-40"
                            />
                            <button
                                onClick={sendMessage}
                                disabled={!inputText.trim() || isLoading}
                                className="absolute right-2 top-1/2 -translate-y-1/2 p-2 bg-cyan-500/20 hover:bg-cyan-500 text-cyan-400 hover:text-black rounded-lg transition-all disabled:opacity-20"
                            >
                                <Send className="w-3.5 h-3.5" />
                            </button>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
