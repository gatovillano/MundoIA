"use client";

import { useState, useEffect } from "react";
import { X, Settings, Key, Cpu, RefreshCw, Save, CheckCircle2, AlertCircle, ExternalLink, Search, Info } from "lucide-react";
import useGameStore from "@/store/useGameStore";
import { getHttpUrl, getApiBase } from "@/utils/apiConfig";

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

const STORAGE_KEY = "mundoia_ai_config";

const PROVIDER_DISPLAY_MAP: Record<string, string> = {
    openrouter: "OpenRouter",
    openai: "OpenAI",
    ollama: "Ollama",
    kilocode: "KiloCode",
};

const OPENAI_DEFAULT_MODELS: ModelInfo[] = [
    { id: "gpt-4o", name: "GPT-4o" },
    { id: "gpt-4o-mini", name: "GPT-4o Mini" },
    { id: "gpt-4-turbo", name: "GPT-4 Turbo" },
];

function stripProviderPrefix(modelId: string): string {
    if (!modelId) return "";
    return modelId.replace(/^(openrouter|ollama|kilocode)\//i, "");
}

function addProviderPrefix(modelId: string, prov: string): string {
    if (!modelId) return "";
    const clean = stripProviderPrefix(modelId);
    if (prov === "OpenRouter") return `openrouter/${clean}`;
    if (prov === "Ollama") return `ollama/${clean}`;
    if (prov === "KiloCode") return `kilocode/${clean}`;
    return clean;
}

function resolveProviderDisplay(rawProvider?: string, rawModel?: string): string {
    if (rawProvider) {
        const mapped = PROVIDER_DISPLAY_MAP[rawProvider.toLowerCase()];
        if (mapped) return mapped;
    }
    if (rawModel?.startsWith("openrouter/")) return "OpenRouter";
    if (rawModel?.startsWith("ollama/")) return "Ollama";
    if (rawModel?.startsWith("kilocode/")) return "KiloCode";
    if (rawModel?.startsWith("gpt-")) return "OpenAI";
    return "OpenRouter";
}

export default function ConfigPanelContent({ isOpen, onClose }: ConfigPanelProps) {
    const [provider, setProvider] = useState("OpenRouter");
    const [apiKey, setApiKey] = useState("");
    const [baseUrl, setBaseUrl] = useState("");
    const [tavilyApiKey, setTavilyApiKey] = useState("");
    const [selectedModel, setSelectedModel] = useState("");
    const [apiKeysByProvider, setApiKeysByProvider] = useState<Record<string, string>>({});
    const [baseUrlsByProvider, setBaseUrlsByProvider] = useState<Record<string, string>>({});
    const [modelsByProvider, setModelsByProvider] = useState<Record<string, string>>({});
    const [models, setModels] = useState<ModelInfo[]>([]);
    const [isLoadingModels, setIsLoadingModels] = useState(false);
    const [status, setStatus] = useState<{ type: 'idle' | 'loading' | 'success' | 'error', msg: string }>({ type: 'idle', msg: '' });
    const [searchTerm, setSearchTerm] = useState("");

    const { socialMode, setSocialMode } = useGameStore();

    // Cargar caché local de inmediato y sincronizar con el backend
    useEffect(() => {
        try {
            const cached = localStorage.getItem(STORAGE_KEY);
            if (cached) {
                const parsed = JSON.parse(cached);
                if (parsed.provider) setProvider(parsed.provider);
                if (parsed.apiKey) setApiKey(parsed.apiKey);
                if (parsed.baseUrl !== undefined) setBaseUrl(parsed.baseUrl);
                if (parsed.tavilyApiKey) setTavilyApiKey(parsed.tavilyApiKey);
                if (parsed.selectedModel) setSelectedModel(parsed.selectedModel);
                if (parsed.apiKeysByProvider) setApiKeysByProvider(parsed.apiKeysByProvider);
                if (parsed.baseUrlsByProvider) setBaseUrlsByProvider(parsed.baseUrlsByProvider);
                if (parsed.modelsByProvider) setModelsByProvider(parsed.modelsByProvider);
            }
        } catch (e) {
            console.warn("Error leyendo caché local de AI config:", e);
        }
        fetchCurrentConfig();
    }, []);

    useEffect(() => {
        if (isOpen) {
            fetchCurrentConfig();
        }
    }, [isOpen]);

    const persistLocalCache = (patch: Record<string, any>) => {
        try {
            const currentRaw = localStorage.getItem(STORAGE_KEY);
            const current = currentRaw ? JSON.parse(currentRaw) : {};
            localStorage.setItem(STORAGE_KEY, JSON.stringify({ ...current, ...patch }));
        } catch (e) {
            console.warn("Error guardando caché local de AI config:", e);
        }
    };

    const loadModels = async (prov: string, currentApiKey: string, currentBaseUrl: string) => {
        if (prov === "OpenAI") {
            setModels(OPENAI_DEFAULT_MODELS);
            return;
        }
        setIsLoadingModels(true);
        setStatus({ type: 'loading', msg: 'Cargando...' });
        try {
            const url = new URL(getHttpUrl(`/config/models/${prov}`));
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
            const res = await fetch(getHttpUrl("/config/ai"));
            if (res.ok) {
                const data = await res.json();
                const loadedProv = resolveProviderDisplay(data.provider, data.model);
                const provKey = loadedProv.toLowerCase();

                const keysMap: Record<string, string> = data.api_keys || {};
                const urlsMap: Record<string, string> = data.base_urls || {};
                const modelsMap: Record<string, string> = data.models_by_provider || {};

                const activeKey = data.api_key || keysMap[provKey] || "";
                const activeUrl = data.base_url !== undefined ? data.base_url : (urlsMap[provKey] || "");
                const activeModel = data.model || modelsMap[provKey] || "";
                const activeTavily = data.tavily_api_key || "";

                if (activeKey) keysMap[provKey] = activeKey;
                if (activeUrl) urlsMap[provKey] = activeUrl;
                if (activeModel) modelsMap[provKey] = activeModel;

                setProvider(loadedProv);
                setApiKey(activeKey);
                setBaseUrl(activeUrl);
                setTavilyApiKey(activeTavily);
                setSelectedModel(activeModel);
                setApiKeysByProvider(keysMap);
                setBaseUrlsByProvider(urlsMap);
                setModelsByProvider(modelsMap);

                persistLocalCache({
                    provider: loadedProv,
                    apiKey: activeKey,
                    baseUrl: activeUrl,
                    tavilyApiKey: activeTavily,
                    selectedModel: activeModel,
                    apiKeysByProvider: keysMap,
                    baseUrlsByProvider: urlsMap,
                    modelsByProvider: modelsMap,
                });

                loadModels(loadedProv, activeKey, activeUrl);
            }
        } catch (error) {
            console.error("Error fetching config:", error);
        }
    };

    const handleProviderChange = (newProv: string) => {
        // Guardar lo que el usuario estaba editando en el proveedor actual
        const oldProvKey = provider.toLowerCase();
        const updatedKeys = { ...apiKeysByProvider, [oldProvKey]: apiKey };
        const updatedUrls = { ...baseUrlsByProvider, [oldProvKey]: baseUrl };
        const updatedModels = selectedModel
            ? { ...modelsByProvider, [oldProvKey]: selectedModel }
            : modelsByProvider;

        setApiKeysByProvider(updatedKeys);
        setBaseUrlsByProvider(updatedUrls);
        setModelsByProvider(updatedModels);

        const newProvKey = newProv.toLowerCase();
        const nextKey = updatedKeys[newProvKey] || "";
        const nextUrl = updatedUrls[newProvKey] || (newProv === "KiloCode" ? "https://api.kilo.ai/api/gateway" : "");
        const nextModel = updatedModels[newProvKey] || "";

        setProvider(newProv);
        setApiKey(nextKey);
        setBaseUrl(nextUrl);
        if (nextModel) {
            setSelectedModel(nextModel);
        }
        loadModels(newProv, nextKey, nextUrl);
    };

    const handleManualReload = () => {
        loadModels(provider, apiKey, baseUrl);
    };

    const handleSave = async () => {
        setStatus({ type: 'loading', msg: 'Sincronizando...' });
        try {
            const rawModel = selectedModel || searchTerm; // Try searchTerm as custom input if selected is missing
            const finalModel = addProviderPrefix(rawModel, provider);
            const provKey = provider.toLowerCase();
            const finalBaseUrl = (provider === "Ollama" || provider === "KiloCode") ? baseUrl : "";

            const res = await fetch(getHttpUrl("/config/ai"), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    provider: provKey, // Enviar en minúscula al backend: "kilocode", "openrouter", "openai", "ollama"
                    api_key: apiKey,
                    model: finalModel,
                    base_url: finalBaseUrl,
                    tavily_api_key: tavilyApiKey
                })
            });

            if (res.ok) {
                const updatedKeys = { ...apiKeysByProvider, [provKey]: apiKey };
                const updatedUrls = { ...baseUrlsByProvider, [provKey]: finalBaseUrl };
                const updatedModels = { ...modelsByProvider, [provKey]: finalModel };

                setSelectedModel(finalModel);
                setApiKeysByProvider(updatedKeys);
                setBaseUrlsByProvider(updatedUrls);
                setModelsByProvider(updatedModels);

                persistLocalCache({
                    provider,
                    apiKey,
                    baseUrl: finalBaseUrl,
                    tavilyApiKey,
                    selectedModel: finalModel,
                    apiKeysByProvider: updatedKeys,
                    baseUrlsByProvider: updatedUrls,
                    modelsByProvider: updatedModels,
                });

                setStatus({ type: 'success', msg: 'Matriz Cognitiva Guardada' });
                setTimeout(() => setStatus({ type: 'idle', msg: '' }), 3000);
            } else {
                setStatus({ type: 'error', msg: 'Error de Red' });
            }
        } catch (error) {
            setStatus({ type: 'error', msg: 'Error Crítico' });
        }
    };

    const isModelSelected = (modelId: string) => {
        if (!selectedModel || !modelId) return false;
        return (
            selectedModel === modelId ||
            stripProviderPrefix(selectedModel) === stripProviderPrefix(modelId)
        );
    };

    // Asegurar que el modelo actualmente seleccionado siempre aparezca en la lista y al principio si coincide con el filtro
    const baseModels: ModelInfo[] = (() => {
        if (!selectedModel) return models;
        const exists = models.some(m => isModelSelected(m.id));
        if (exists) return models;
        const cleanId = stripProviderPrefix(selectedModel);
        return [{ id: selectedModel, name: `${cleanId} (Guardado)` }, ...models];
    })();

    const filteredModels = baseModels
        .filter(m =>
            m.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
            m.id.toLowerCase().includes(searchTerm.toLowerCase())
        )
        .sort((a, b) => {
            const aSel = isModelSelected(a.id) ? -1 : 0;
            const bSel = isModelSelected(b.id) ? -1 : 0;
            return aSel - bSel;
        });

    return (
        <div className="flex flex-col h-full space-y-8 pb-8">
            {/* Proveedor */}
            <Section title="Proveedor de Inteligencia">
                <div className="grid grid-cols-4 gap-2 p-1 bg-black/40 rounded-2xl border border-white/5 shadow-inner">
                    {["OpenRouter", "OpenAI", "Ollama", "KiloCode"].map((p) => (
                        <button
                            key={p}
                            onClick={() => handleProviderChange(p)}
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

                    {(provider === "Ollama" || provider === "KiloCode") && (
                        <div className="relative group">
                            <input
                                type="text"
                                value={baseUrl}
                                onChange={(e) => setBaseUrl(e.target.value)}
                                placeholder={provider === "Ollama" 
                                    ? "Endpoint (ej: http://localhost:11434)" 
                                    : "Endpoint Kilo (opcional, ej: https://api.kilo.ai/api/gateway)"}
                                className="w-full bg-black/60 border border-white/10 rounded-2xl p-4 text-xs text-white placeholder:text-gray-700 focus:border-indigo-500/40 focus:outline-none transition-all font-mono"
                            />
                        </div>
                    )}

                    {(provider !== "Ollama") && (
                        <div className="flex items-center justify-between px-1">
                            <a
                                href={
                                    provider === "OpenRouter" 
                                        ? "https://openrouter.ai/keys" 
                                        : provider === "KiloCode" 
                                            ? "https://kilo.ai/gateway" 
                                            : "https://platform.openai.com/api-keys"
                                }
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
                    {selectedModel && (
                        <div className="flex items-center justify-between px-3 py-2 rounded-xl bg-indigo-500/10 border border-indigo-500/20">
                            <div className="flex items-center gap-2 min-w-0">
                                <Cpu className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
                                <span className="text-[9px] text-indigo-300/70 uppercase tracking-wider font-bold shrink-0">Activo:</span>
                                <span className="text-[10px] text-indigo-200 font-mono truncate">{selectedModel}</span>
                            </div>
                            <CheckCircle2 className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
                        </div>
                    )}

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
                                filteredModels.map((m) => {
                                    const active = isModelSelected(m.id);
                                    return (
                                        <button
                                            key={m.id}
                                            onClick={() => setSelectedModel(addProviderPrefix(m.id, provider))}
                                            className={`w-full flex flex-col p-3 rounded-xl text-left transition-all mb-1 last:mb-0 group ${active ? 'bg-indigo-500/20 border border-indigo-500/20 shadow-lg' : 'hover:bg-white/[0.03]'}`}
                                        >
                                            <div className="flex items-center justify-between">
                                                <span className={`text-[11px] font-bold font-mono transition-colors ${active ? 'text-indigo-300' : 'text-gray-500 group-hover:text-gray-300'}`}>
                                                    {m.name}
                                                </span>
                                                {active && <CheckCircle2 className="w-3 h-3 text-indigo-400" />}
                                            </div>
                                            <span className="text-[8px] text-gray-600 font-mono mt-0.5 truncate uppercase tracking-tighter opacity-50">{m.id}</span>
                                        </button>
                                    );
                                })
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
