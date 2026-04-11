"use client";

import { useState, useEffect } from "react";
import { X, Settings, Key, Cpu, RefreshCw, Save, CheckCircle2, AlertCircle, ExternalLink, Search, Info } from "lucide-react";
import useGameStore from "@/store/useGameStore";

interface ConfigPanelProps {
    isOpen: boolean;
    onClose: () => void;
}

interface ModelInfo {
    id: string;
    name: string;
    context_length?: number;
    pricing?: any;
}

export default function ConfigPanelContent({ isOpen, onClose }: ConfigPanelProps) {
    const [provider, setProvider] = useState("OpenRouter");
    const [apiKey, setApiKey] = useState("");
    const [baseUrl, setBaseUrl] = useState("");
    const [tavilyApiKey, setTavilyApiKey] = useState("");
    const [selectedModel, setSelectedModel] = useState("");
    const [models, setModels] = useState<ModelInfo[]>([]);
    const [isLoadingModels, setIsLoadingModels] = useState(false);
    const [status, setStatus] = useState<{ type: 'idle' | 'loading' | 'success' | 'error', msg: string }>({ type: 'idle', msg: '' });
    const [searchTerm, setSearchTerm] = useState("");

    const { socialMode, setSocialMode } = useGameStore();

    // Cargar config inicial
    useEffect(() => {
        if (isOpen) {
            fetchCurrentConfig();
        }
    }, [isOpen]);

    // loadModels has been moved or modified to accept arguments so it doesn't rely on stale state
    const loadModels = async (prov: string, currentApiKey: string, currentBaseUrl: string) => {
        setIsLoadingModels(true);
        setStatus({ type: 'loading', msg: 'Cargando...' });
        try {
            const host = window.location.hostname === 'localhost' ? 'api-mundoia.cuerpolibre.cl' : 'api-mundoia.cuerpolibre.cl';
            const protocol = window.location.protocol;
            const url = new URL(`${protocol}//${host}/config/models/${prov}`);
            if (currentApiKey) url.searchParams.append('api_key', currentApiKey);
            if (currentBaseUrl) url.searchParams.append('base_url', currentBaseUrl);

            const res = await fetch(url.toString());
            const data = await res.json();
            if (data.models) {
                setModels(data.models);
                setStatus({ type: 'idle', msg: '' });
            } else {
                setModels([]);
                setStatus({ type: 'error', msg: 'Error cargando modelos.' });
            }
        } catch (error) {
            console.error("Error fetching models:", error);
            setModels([]);
            setStatus({ type: 'error', msg: 'Excepción al cargar modelos.' });
        } finally {
            setIsLoadingModels(false);
        }
    };

    const fetchCurrentConfig = async () => {
        try {
            const host = window.location.hostname === 'localhost' ? 'api-mundoia.cuerpolibre.cl' : 'api-mundoia.cuerpolibre.cl';
            const protocol = window.location.protocol;
            const res = await fetch(`${protocol}//${host}/config/ai`);
            if (res.ok) {
                const data = await res.json();
                setApiKey(data.api_key || "");
                setBaseUrl(data.base_url || "");
                setTavilyApiKey(data.tavily_api_key || "");
                setSelectedModel(data.model || "");
                let loadedProv = "OpenRouter";
                if (data.model?.includes("openrouter/")) {
                    loadedProv = "OpenRouter";
                } else if (data.model?.includes("ollama/")) {
                    loadedProv = "Ollama";
                } else if (data.model?.includes("gpt-")) {
                    loadedProv = "OpenAI";
                }
                setProvider(loadedProv);
                
                if (loadedProv === "OpenRouter" || loadedProv === "Ollama") {
                    loadModels(loadedProv, data.api_key || "", data.base_url || "");
                } else {
                    setModels([
                        { id: "gpt-4o", name: "GPT-4o" },
                        { id: "gpt-4o-mini", name: "GPT-4o Mini" },
                        { id: "gpt-4-turbo", name: "GPT-4 Turbo" }
                    ]);
                }
            }
        } catch (error) {
            console.error("Error fetching config:", error);
        }
    };

    const handleManualReload = () => {
        if (provider === "OpenRouter" || provider === "Ollama") {
            loadModels(provider, apiKey, baseUrl);
        }
    };

    const handleSave = async () => {
        setStatus({ type: 'loading', msg: 'Sincronizando...' });
        try {
            const host = window.location.hostname === 'localhost' ? 'api-mundoia.cuerpolibre.cl' : 'api-mundoia.cuerpolibre.cl';
            const protocol = window.location.protocol;

            let finalModel = selectedModel || searchTerm; // Try searchTerm as custom input if selected is missing
            if (provider === "OpenRouter" && !finalModel.startsWith("openrouter/")) {
                finalModel = `openrouter/${finalModel}`;
            } else if (provider === "Ollama" && !finalModel.startsWith("ollama/")) {
                finalModel = `ollama/${finalModel}`;
            }

            const res = await fetch(`${protocol}//${host}/config/ai`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    provider,
                    api_key: apiKey,
                    model: finalModel,
                    base_url: baseUrl,
                    tavily_api_key: tavilyApiKey
                })
            });

            if (res.ok) {
                setSelectedModel(finalModel); // Actualizar el modelo seleccionado en la UI si era custom
                setStatus({ type: 'success', msg: 'Matriz Cognitiva Guardada' });
                setTimeout(() => setStatus({ type: 'idle', msg: '' }), 3000);
            } else {
                setStatus({ type: 'error', msg: 'Error de Red' });
            }
        } catch (error) {
            setStatus({ type: 'error', msg: 'Error Crítico' });
        }
    };

    const filteredModels = models.filter(m =>
        m.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        m.id.toLowerCase().includes(searchTerm.toLowerCase())
    );

    return (
        <div className="flex flex-col h-full space-y-8 pb-8">
            {/* Proveedor */}
            <Section title="Proveedor de Inteligencia">
                <div className="grid grid-cols-3 gap-2 p-1 bg-black/40 rounded-2xl border border-white/5 shadow-inner">
                    {["OpenRouter", "OpenAI", "Ollama"].map((p) => (
                        <button
                            key={p}
                            onClick={() => setProvider(p)}
                            className={`py-2.5 text-[10px] font-bold uppercase rounded-xl transition-all ${provider === p ? 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 shadow-[0_0_15px_rgba(99,102,241,0.1)]' : 'text-gray-500 hover:text-gray-300'}`}
                        >
                            {p}
                        </button>
                    ))}
                </div>
            </Section>

            {/* Credenciales / Endpoint */}
            <Section title={provider === "Ollama" ? "Credenciales y Endpoint" : "Credenciales de Acceso"}>
                <div className="space-y-4">
                    <div className="relative group">
                        <input
                            type="password" // Consider switching to text if users need to see Ollama keys, but password is safe
                            value={apiKey}
                            onChange={(e) => setApiKey(e.target.value)}
                            placeholder={`Pega tu API Key de ${provider}...`}
                            autoComplete="off"
                            className="w-full bg-black/60 border border-white/10 rounded-2xl p-4 pr-12 text-xs text-white placeholder:text-gray-700 focus:border-indigo-500/40 focus:outline-none transition-all font-mono"
                        />
                        <div className="absolute right-4 top-1/2 -translate-y-1/2 text-indigo-500/30">
                            <Key className="w-4 h-4" />
                        </div>
                    </div>

                    {provider === "Ollama" && (
                        <div className="relative group">
                            <input
                                type="text"
                                value={baseUrl}
                                onChange={(e) => setBaseUrl(e.target.value)}
                                placeholder="Endpoint (ej: https://api.ollama.cloud/v1 o http://localhost:11434)"
                                className="w-full bg-black/60 border border-white/10 rounded-2xl p-4 text-xs text-white placeholder:text-gray-700 focus:border-indigo-500/40 focus:outline-none transition-all font-mono"
                            />
                        </div>
                    )}

                    {provider !== "Ollama" && (
                        <div className="flex items-center justify-between px-1">
                            <a
                                href={provider === "OpenRouter" ? "https://openrouter.ai/keys" : "https://platform.openai.com/api-keys"}
                                target="_blank"
                                rel="noreferrer"
                                className="text-[9px] text-indigo-400/60 hover:text-indigo-400 flex items-center gap-1.5 transition-colors uppercase font-bold tracking-widest"
                            >
                                Obtener Llave <ExternalLink className="w-2.5 h-2.5" />
                            </a>
                            <span className="text-[8px] text-gray-600 font-mono italic">Seguro: AES-256 Encrypted</span>
                        </div>
                    )}
                </div>
            </Section>

            {/* Herramientas Externas */}
            <Section title="Herramientas Externas">
                <div className="space-y-4">
                    <div className="relative group">
                        <input
                            type="password"
                            value={tavilyApiKey}
                            onChange={(e) => setTavilyApiKey(e.target.value)}
                            placeholder="Tavily API Key (para navegación web)..."
                            autoComplete="off"
                            className="w-full bg-black/60 border border-white/10 rounded-2xl p-4 pr-12 text-xs text-white placeholder:text-gray-700 focus:border-indigo-500/40 focus:outline-none transition-all font-mono"
                        />
                        <div className="absolute right-4 top-1/2 -translate-y-1/2 text-indigo-500/30">
                            <Search className="w-4 h-4" />
                        </div>
                    </div>
                    <div className="px-1">
                        <a
                            href="https://tavily.com/"
                            target="_blank"
                            rel="noreferrer"
                            className="text-[9px] text-indigo-400/60 hover:text-indigo-400 flex items-center gap-1.5 transition-colors uppercase font-bold tracking-widest"
                        >
                            Obtener Tavily Key <ExternalLink className="w-2.5 h-2.5" />
                        </a>
                    </div>
                </div>
            </Section>

            {/* Model Selector */}
            <Section title="Modelos Disponibles">
                <div className="space-y-4">
                    <div className="relative">
                        <input
                            type="text"
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                            placeholder="Buscar en lista o escribir modelo personalizado..."
                            className="w-full bg-black/40 border border-white/5 rounded-xl py-3 px-10 text-[10px] text-gray-400 placeholder:text-gray-700 focus:outline-none focus:border-indigo-500/20 transition-all font-mono"
                        />
                        <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-700" />
                        <button
                             onClick={handleManualReload}
                             disabled={isLoadingModels}
                             className={`absolute right-3 top-1/2 -translate-y-1/2 text-indigo-500/40 hover:text-indigo-400 transition-all ${isLoadingModels ? 'animate-spin' : ''}`}
                        >
                            <RefreshCw className="w-3.5 h-3.5" />
                        </button>
                    </div>

                    <div className="bg-black/60 rounded-2xl border border-white/5 overflow-hidden shadow-2xl">
                        <div className="max-h-[180px] overflow-y-auto custom-scrollbar p-1.5">
                            {isLoadingModels ? (
                                <div className="py-12 flex flex-col items-center justify-center gap-3">
                                    <div className="w-6 h-6 border-2 border-indigo-500/20 border-t-indigo-500 rounded-full animate-spin" />
                                    <span className="text-[9px] font-mono text-indigo-500/40 uppercase tracking-widest animate-pulse">Sincronizando...</span>
                                </div>
                            ) : filteredModels.length > 0 ? (
                                filteredModels.map((m) => (
                                    <button
                                        key={m.id}
                                        onClick={() => setSelectedModel(m.id)}
                                        className={`w-full flex flex-col p-3 rounded-xl text-left transition-all mb-1 last:mb-0 group ${selectedModel === m.id ? 'bg-indigo-500/20 border border-indigo-500/20 shadow-lg' : 'hover:bg-white/[0.03]'}`}
                                    >
                                        <div className="flex items-center justify-between">
                                            <span className={`text-[11px] font-bold font-mono transition-colors ${selectedModel === m.id ? 'text-indigo-300' : 'text-gray-500 group-hover:text-gray-300'}`}>
                                                {m.name}
                                            </span>
                                            {selectedModel === m.id && <CheckCircle2 className="w-3 h-3 text-indigo-400" />}
                                        </div>
                                        <span className="text-[8px] text-gray-600 font-mono mt-0.5 truncate uppercase tracking-tighter opacity-50">{m.id}</span>
                                    </button>
                                ))
                            ) : (
                                <div className="py-10 text-center text-[10px] text-gray-600 italic">No se encontraron modelos.</div>
                            )}
                        </div>
                    </div>
                </div>
            </Section>

            {/* Interfaz de Red Social */}
            <Section title="Interfaz de Red Social">
                <div className="grid grid-cols-2 gap-2 p-1 bg-black/40 rounded-2xl border border-white/5 shadow-inner">
                    <button
                        onClick={() => setSocialMode('twitter')}
                        className={`py-3 text-[10px] font-bold uppercase rounded-xl transition-all flex items-center justify-center gap-2 ${socialMode === 'twitter' ? 'bg-[#1d9bf0]/20 text-[#1d9bf0] border border-[#1d9bf0]/30' : 'text-gray-500 hover:text-gray-300'}`}
                    >
                        <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
                        </svg>
                        X / Twitter
                    </button>
                    <button
                        onClick={() => setSocialMode('reddit')}
                        className={`py-3 text-[10px] font-bold uppercase rounded-xl transition-all flex items-center justify-center gap-2 ${socialMode === 'reddit' ? 'bg-[#ff4500]/20 text-[#ff4500] border border-[#ff4500]/30' : 'text-gray-500 hover:text-gray-300'}`}
                    >
                        <svg className="w-4 h-4" viewBox="0 0 20 20" fill="currentColor">
                            <path d="M16.5 9a1.5 1.5 0 1 0 1.5 1.5A1.5 1.5 0 0 0 16.5 9zM10.25 13a.75.75 0 0 0 0 1.5h.5a.75.75 0 0 0 0-1.5zM14.5 9a1.5 1.5 0 1 0 1.5 1.5A1.5 1.5 0 0 0 14.5 9zM10 0a10 10 0 1 0 10 10A10 10 0 0 0 10 0zm0 18a8 8 0 1 1 8-8 8 8 0 0 1-8 8zm4.5-12.5a.5.5 0 1 0-.5-.5.5.5 0 0 0 .5.5zM6.5 10a1.5 1.5 0 1 0 1.5-1.5 1.5 1.5 0 0 0-1.5 1.5zm1 4.5A4.49 4.49 0 0 1 10 16a4.49 4.49 0 0 1 2.5-1.5.5.5 0 1 1 .14.98A3.49 3.49 0 0 0 10 17a3.49 3.49 0 0 0-2.64-1.52.5.5 0 1 1 .14-.98zM5 9a1.5 1.5 0 1 0 1.5 1.5A1.5 1.5 0 0 0 5 9z" />
                        </svg>
                        Reddit
                    </button>
                </div>
            </Section>

            {/* Actions */}
            <div className="pt-4 mt-auto">
                <button
                    onClick={handleSave}
                    disabled={status.type === 'loading' || (!selectedModel && !searchTerm) || (provider !== "Ollama" && !apiKey)}
                    className={`w-full py-4 rounded-2xl text-[10px] font-black uppercase tracking-[0.2em] transition-all flex items-center justify-center gap-3 shadow-xl disabled:opacity-20 ${status.type === 'success' ? 'bg-green-500/20 text-green-400 border border-green-500/30' :
                        status.type === 'error' ? 'bg-red-500/20 text-red-400 border border-red-500/30' :
                            'bg-indigo-600 hover:bg-indigo-500 text-white border border-indigo-400/50 shadow-indigo-600/30'
                        }`}
                >
                    {status.type === 'loading' ? <RefreshCw className="w-4 h-4 animate-spin" /> : 
                     status.type === 'success' ? <CheckCircle2 className="w-4 h-4" /> : <Save className="w-4 h-4" />}
                    {status.type === 'success' ? status.msg :
                        status.type === 'error' ? status.msg :
                            "Actualizar Matriz Cognitiva"}
                </button>
            </div>
        </div>
    );
}

function Section({ title, children }: { title: string, children: React.ReactNode }) {
    return (
        <div className="space-y-4">
            <div className="flex items-center gap-4">
                <h3 className="text-[9px] font-black text-white/20 uppercase tracking-[0.3em] whitespace-nowrap">{title}</h3>
                <div className="h-px bg-white/5 w-full"></div>
            </div>
            {children}
        </div>
    );
}
