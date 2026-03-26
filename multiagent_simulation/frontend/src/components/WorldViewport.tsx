"use client";

import { useEffect, useRef, useState } from "react";
import * as d3 from "d3";
import useGameStore from "@/store/useGameStore";
import { CloudRain, Sun, Link, Link2Off } from "lucide-react";

export default function WorldViewport({ hideBubbles = false }: { hideBubbles?: boolean }) {
    const svgRef = useRef<SVGSVGElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);
    const { agents, mapa, relationships, speechBubbles, selectAgent, selectedAgentId, weather } = useGameStore();
    const [showLinks, setShowLinks] = useState(true);
    const initializedRef = useRef(false);
    const prevAgentsRef = useRef<any[]>([]);

    // Configuración D3
    useEffect(() => {
        if (!svgRef.current || !containerRef.current || mapa.length === 0) return;

        // Detectar agentes que ya existían vs nuevos
        const currentAgentIds = new Set(agents.map((a: any) => a.id));
        const prevAgentIds = new Set(prevAgentsRef.current.map((a: any) => a.id));
        
        // Guardar posiciones anteriores para movimiento suave
        const prevPositions = new Map<string, { x: number, y: number }>();
        prevAgentsRef.current.forEach((a: any) => {
            prevPositions.set(a.id, { x: a.x, y: a.y });
        });
        prevAgentsRef.current = agents;

        const width = containerRef.current.clientWidth;
        const height = containerRef.current.clientHeight;
        const svg = d3.select(svgRef.current);

        // Grupo principal con Zoom
        let g = svg.select<SVGGElement>("g.main-group");
        if (g.empty()) {
            g = svg.append("g").attr("class", "main-group");
        }

        // Crear o obtener grupos para cada capa (solo si es la primera vez)
        let terrainGroup = g.select<SVGGElement>(".terrain-layer");
        if (terrainGroup.empty()) {
            terrainGroup = g.append("g").attr("class", "terrain-layer");
        }

        let linkGroup = g.select<SVGGElement>(".links-layer");
        if (linkGroup.empty()) {
            linkGroup = g.append("g").attr("class", "links-layer");
        }

        let agentGroup = g.select<SVGGElement>(".agents-layer");
        if (agentGroup.empty()) {
            agentGroup = g.append("g").attr("class", "agents-layer");
        }

        let bubbleGroup = g.select<SVGGElement>(".bubbles-layer");
        // Las burbujas NO persisten - se recrean cada render
        if (!bubbleGroup.empty()) {
            bubbleGroup.remove();
        }
        bubbleGroup = g.append("g").attr("class", "bubbles-layer");

        // Capa de clima (persistente)
        let weatherGroup = g.select<SVGGElement>(".weather-layer");
        if (weatherGroup.empty()) {
            weatherGroup = g.append("g").attr("class", "weather-layer");
        }
        weatherGroup.selectAll("*").remove(); // Limpiar solo el contenido

        // Zoom (solo inicializar una vez)
        const zoom = d3.zoom<SVGSVGElement, unknown>()
            .scaleExtent([0.5, 5])
            .on("zoom", (event) => {
                g.attr("transform", event.transform);
            });
        
        if (!initializedRef.current) {
            svg.call(zoom);
            initializedRef.current = true;
        }

        // Configuración de la cuadrícula dinámica
        const cols = mapa.length;
        const rows = mapa[0].length;
        const cellSize = 40;
        const gridWidth = cols * cellSize;
        const gridHeight = rows * cellSize;

        // Centrar el mapa inicialmente
        const initialScale = Math.min(width / gridWidth, height / gridHeight) * 0.85;
        const initialX = (width - gridWidth * initialScale) / 2;
        const initialY = (height - gridHeight * initialScale) / 2;

        svg.call(zoom.transform, d3.zoomIdentity.translate(initialX, initialY).scale(initialScale));

        // --- CAPA 0: TERRENO y TERRITORIOS ---
        const { civilizaciones, gruposDinamicos } = useGameStore.getState();

        const terrainColors: Record<string, { start: string, end: string }> = {
            grass: { start: "#0f2e1d", end: "#143d26" }, // Verde oscuro
            forest: { start: "#051f12", end: "#0a291a" }, // Más oscuro
            mountain: { start: "#1a1b20", end: "#2d2e36" }, // Gris azulado oscuro
            water: { start: "#08121f", end: "#0c1b2e" }, // Azul muy oscuro
            desert: { start: "#2b210e", end: "#3d2f14" }, // Marrón oscuro
        };

        const buildingIcons: Record<string, string> = {
            "Hospital": "🏥",
            "Granja": "🌾",
            "Centro de Recarga": "⚡",
            "Centro de Descanso": "🧘",
            "Centro Comunitario": "🤝",
            "Comisaría": "👮",
            "Universidad": "🏛️",
            "Comedor": "🍽️",
            "Centro de Ocio": "🎭",
            "Torre de Vigilancia": "🏹"
        };

        // Limpiar contenido de la capa de clima
        if (!weatherGroup.empty()) {
            weatherGroup.selectAll("*").remove();
        }

        // Crear o obtener defs (solo una vez)
        let defs = svg.select<SVGDefsElement>("defs");
        if (defs.empty()) {
            defs = svg.append("defs");
        }

        // Definir gradientes en el SVG (solo si no existen)
        Object.entries(terrainColors).forEach(([id, colors]) => {
            if (defs.select(`#grad-${id}`).empty()) {
                const grad = defs.append("linearGradient")
                    .attr("id", `grad-${id}`)
                    .attr("x1", "0%").attr("y1", "0%")
                    .attr("x2", "100%").attr("y2", "100%");
                grad.append("stop").attr("offset", "0%").attr("stop-color", colors.start);
                grad.append("stop").attr("offset", "100%").attr("stop-color", colors.end);
            }
        });

        // Filtro de resplandor (solo si no existe)
        if (defs.select("#glow").empty()) {
            const filter = defs.append("filter")
                .attr("id", "glow");
            filter.append("feGaussianBlur")
                .attr("stdDeviation", "2.5")
                .attr("result", "coloredBlur");
            const feMerge = filter.append("feMerge");
            feMerge.append("feMergeNode").attr("in", "coloredBlur");
            feMerge.append("feMergeNode").attr("in", "SourceGraphic");
        }

        mapa.forEach((row, x) => {
            row.forEach((tile, y) => {
                const cellGroup = terrainGroup.append("g")
                    .attr("transform", `translate(${x * cellSize}, ${y * cellSize})`);

                // Base del terreno con gradiente
                cellGroup.append("rect")
                    .attr("width", cellSize)
                    .attr("height", cellSize)
                    .attr("fill", `url(#grad-${tile.terrain})`)
                    .attr("stroke", "rgba(255,255,255,0.03)")
                    .attr("stroke-width", 0.5);

                // Overlay de Territorio (Si tiene dueño)
                if (tile.owner) {
                    const ownerInfo = civilizaciones[tile.owner] || gruposDinamicos[tile.owner];
                    const ownerColor = ownerInfo?.color || "#ffffff";

                    // Indicador sutil de borde
                    cellGroup.append("rect")
                        .attr("width", cellSize)
                        .attr("height", cellSize)
                        .attr("fill", "none")
                        .attr("stroke", ownerColor)
                        .attr("stroke-width", 1.5)
                        .attr("opacity", 0.3);

                    // Indicador de esquina para facción
                    cellGroup.append("path")
                        .attr("d", `M 0 0 L 12 0 L 0 12 Z`)
                        .attr("fill", ownerColor)
                        .attr("opacity", 0.8);
                }

                // Construcciones (Iconografía)
                if (tile.buildings && tile.buildings.length > 0) {
                    tile.buildings.forEach((b: any) => {
                        // Fondo para el icono para mejor legibilidad
                        const ownerColor = civilizaciones[b.grupo_id]?.color || gruposDinamicos[b.grupo_id]?.color || "#7c4dff";

                        cellGroup.append("circle")
                            .attr("cx", cellSize / 2)
                            .attr("cy", cellSize / 2)
                            .attr("r", 12)
                            .attr("fill", "rgba(0,0,0,0.8)")
                            .attr("stroke", ownerColor)
                            .attr("stroke-width", 1.5)
                            .style("filter", "drop-shadow(0 0 5px " + ownerColor + ")");

                        cellGroup.append("text")
                            .attr("x", cellSize / 2)
                            .attr("y", cellSize / 2 + 5)
                            .attr("text-anchor", "middle")
                            .attr("font-size", "14px")
                            .attr("fill", "#ffffff")
                            .text(buildingIcons[b.tipo] || "🏠");
                    });
                } else if (tile.resource) {
                    // Recursos temáticos (Civilization style)
                    const resourceIcon = tile.resource.type === 'food' ? '🌾' : '💎';
                    const resourceColor = tile.resource.type === 'food' ? '#fcd34d' : '#00e5ff';

                    cellGroup.append("text")
                        .attr("x", cellSize / 2)
                        .attr("y", cellSize / 2 + 5)
                        .attr("text-anchor", "middle")
                        .attr("font-size", "12px")
                        .attr("fill", resourceColor)
                        .attr("opacity", 0.7)
                        .text(resourceIcon);
                }
            });
        });

        // --- CAPA 1: GRAFO SOCIAL (Enlaces) ---

        if (showLinks && relationships && relationships.length > 0) {
            const agentCoords = new Map();
            agents.forEach(a => agentCoords.set(a.id, { x: a.x * cellSize + cellSize / 2, y: a.y * cellSize + cellSize / 2 }));

            relationships.forEach(rel => {
                const source = agentCoords.get(rel.source);
                const target = agentCoords.get(rel.target);

                if (source && target) {
                    let strokeColor = "#ffffff";
                    let strokeWidth = 0.5;
                    let opacity = 0.15;

                    if (rel.type === 'amigo') { strokeColor = "#00e676"; opacity = 0.5; strokeWidth = 1.2; }
                    if (rel.type === 'enemigo') { strokeColor = "#ff1744"; opacity = 0.7; strokeWidth = 2; }
                    if (rel.type === 'alianza') { strokeColor = "#ffd600"; opacity = 0.8; strokeWidth = 2.5; }

                    const line = linkGroup.append("line")
                        .attr("x1", source.x)
                        .attr("y1", source.y)
                        .attr("x2", target.x)
                        .attr("y2", target.y)
                        .attr("stroke", strokeColor)
                        .attr("stroke-width", strokeWidth)
                        .attr("opacity", opacity);

                    if (rel.type === 'alianza') {
                        line.attr("stroke-dasharray", "4,2");
                    }
                }
            });
        }


        // --- CAPA 2: AGENTES ---
        const updateAgents = () => {
            const agentSelection = agentGroup.selectAll<SVGGElement, any>(".agent")
                .data(agents, (d) => d.id);

            const enter = agentSelection.enter()
                .append("g")
                .attr("class", "agent")
                .attr("cursor", "pointer")
                .on("click", (event, d) => {
                    event.stopPropagation();
                    selectAgent(d.id);
                });

            // Aura de selección con animación
            const aura = enter.append("circle")
                .attr("class", "selection-ring")
                .attr("r", 18)
                .attr("fill", "none")
                .attr("stroke", "#7c4dff")
                .attr("stroke-width", 1.5)
                .attr("opacity", 0);

            // Cuerpo del Robot (Estilo Tech)
            enter.append("rect")
                .attr("x", -7)
                .attr("y", -7)
                .attr("width", 14)
                .attr("height", 14)
                .attr("rx", 2)
                .attr("fill", (d) => d.color || "#e0e0e0")
                .attr("stroke", "#000")
                .attr("stroke-width", 1.5)
                .attr("filter", "url(#glow)");

            // Visor / Ojos brillantes
            enter.append("rect")
                .attr("x", -5)
                .attr("y", -4)
                .attr("width", 10)
                .attr("height", 3)
                .attr("fill", "#000")
                .attr("opacity", 0.8);

            enter.append("rect")
                .attr("x", -4)
                .attr("y", -3)
                .attr("width", 2)
                .attr("height", 1)
                .attr("fill", "#00e5ff"); // Ojo izquierdo brillante

            enter.append("rect")
                .attr("x", 2)
                .attr("y", -3)
                .attr("width", 2)
                .attr("height", 1)
                .attr("fill", "#00e5ff"); // Ojo derecho brillante

            // ID
            enter.append("text")
                .attr("dy", -10)
                .attr("text-anchor", "middle")
                .attr("font-size", "8px")
                .attr("fill", "#ffffff")
                .attr("font-family", "monospace")
                .attr("font-weight", "bold")
                .attr("opacity", 0.8)
                .text((d) => d.id.replace('A', ''));

            // Actualización de posición
            const merged = enter.merge(agentSelection);

            // Aplicar posición con transición solo para agentes existentes
            // Para agentes nuevos (first render), posicionar directamente
            merged.each(function(d) {
                const prevPos = prevPositions.get(d.id);
                const currentPos = { x: d.x * cellSize + cellSize / 2, y: d.y * cellSize + cellSize / 2 };
                
                if (prevPos) {
                    // Agente existente - animación desde posición anterior
                    const prevX = prevPos.x * cellSize + cellSize / 2;
                    const prevY = prevPos.y * cellSize + cellSize / 2;
                    d3.select(this)
                        .attr("transform", `translate(${prevX}, ${prevY})`)
                        .transition()
                        .duration(400)
                        .attr("transform", `translate(${currentPos.x}, ${currentPos.y})`);
                } else {
                    // Agente nuevo - posicionar directamente
                    d3.select(this)
                        .attr("transform", `translate(${currentPos.x}, ${currentPos.y})`);
                }
            });

            // Actualizar estado de selección
            merged.select(".selection-ring")
                .transition().duration(200)
                .attr("opacity", (d) => d.id === selectedAgentId ? 1 : 0)
                .attr("stroke-dasharray", (d) => d.id === selectedAgentId ? "4,2" : "none");

            agentSelection.exit().remove();
        };

        updateAgents();

        // --- CAPA 3: BURBUJAS DE DIÁLOGO (GAME STYLE) ---
        // Ocultar burbujas cuando hay un panel activo
        if (speechBubbles && !hideBubbles) {
            Object.entries(speechBubbles).forEach(([agentId, bubble]) => {
                const agent = agents.find(a => a.id === agentId);
                if (agent) {
                    const x = agent.x * cellSize + cellSize / 2;
                    const y = agent.y * cellSize + cellSize / 2 - 25;

                    const bubbleG = bubbleGroup.append("g")
                        .attr("transform", `translate(${x}, ${y})`);

                    // Configuración de envuelto (wrap)
                    const maxWidth = 140;
                    const words = bubble.text.split(/\s+/);
                    const lines: string[] = [];
                    let currentLine = "";

                    // Una forma simple de calcular el wrap sin medir cada vez (estimación por fuente mono)
                    const charsPerLine = Math.floor(maxWidth / 7); // Aprox 7px por char en 10px mono

                    words.forEach(word => {
                        if ((currentLine + word).length > charsPerLine) {
                            lines.push(currentLine.trim());
                            currentLine = word + " ";
                        } else {
                            currentLine += word + " ";
                        }
                    });
                    lines.push(currentLine.trim());

                    const lineHeight = 12;
                    const bubblePadding = 10;
                    const bubbleWidth = Math.min(maxWidth, (Math.max(...lines.map(l => l.length)) * 7) + 20);
                    const bubbleHeight = (lines.length * lineHeight) + bubblePadding;

                    // Fondo estilo RPG (Cuadro de texto)
                    bubbleG.append("rect")
                        .attr("x", -bubbleWidth / 2)
                        .attr("y", -bubbleHeight)
                        .attr("width", bubbleWidth)
                        .attr("height", bubbleHeight)
                        .attr("rx", 6)
                        .attr("fill", "rgba(10, 11, 16, 0.95)")
                        .attr("stroke", "#7c4dff")
                        .attr("stroke-width", 1.5)
                        .attr("filter", "url(#glow)");

                    // Pequeña flecha hacia abajo
                    bubbleG.append("path")
                        .attr("d", `M -5 0 L 5 0 L 0 5 Z`)
                        .attr("fill", "#7c4dff")
                        .attr("transform", `translate(0, 0)`);

                    // Texto multilínea
                    const textElement = bubbleG.append("text")
                        .attr("text-anchor", "middle")
                        .attr("font-size", "10px")
                        .attr("fill", "#fff")
                        .attr("font-family", "monospace")
                        .attr("y", -bubbleHeight + 14);

                    lines.forEach((line, i) => {
                        textElement.append("tspan")
                            .attr("x", 0)
                            .attr("dy", i === 0 ? 0 : lineHeight)
                            .text(line);
                    });

                    // Animación de entrada suave
                    bubbleG.attr("opacity", 0)
                        .transition().duration(300)
                        .attr("opacity", 1)
                        .attr("transform", `translate(${x}, ${y - 8})`);
                }
            });
        }


        // --- CAPA 4: CLIMA (Overlay Sutil) ---
        if (weather === 'rainy' || weather === 'storm') {
            weatherGroup.append("rect")
                .attr("width", gridWidth)
                .attr("height", gridHeight)
                .attr("fill", "#2979ff")
                .attr("opacity", 0.05)
                .style("pointer-events", "none");
        }

    }, [mapa, agents, selectedAgentId, weather, selectAgent, relationships, speechBubbles, showLinks, hideBubbles]);

    return (
        <div ref={containerRef} className="w-full h-full relative bg-[#030305] overflow-hidden">
            <svg ref={svgRef} className="w-full h-full block" />

            {/* Botón para toggle de vínculos - Moved down to avoid header overlap */}
            <button
                onClick={() => setShowLinks(!showLinks)}
                className="absolute top-20 right-6 glass-panel p-2.5 rounded-xl border border-white/10 hover:border-purple-500/50 hover:bg-white/5 transition-all duration-300 group pointer-events-auto"
                title={showLinks ? "Ocultar vínculos" : "Mostrar vínculos"}
            >
                {showLinks ? (
                    <Link className="w-4 h-4 text-purple-400 group-hover:text-purple-300 transition-colors" />
                ) : (
                    <Link2Off className="w-4 h-4 text-gray-400 group-hover:text-gray-300 transition-colors" />
                )}
            </button>

            {/* Leyenda Sofisticada - Moved to avoid terminal overlap */}
            <div className="absolute top-20 left-6 glass-panel p-3 rounded-xl border border-white/5 text-[9px] space-y-2 pointer-events-none max-w-[150px] bg-black/20 backdrop-blur-sm">
                <div className="flex items-center gap-2 text-white/30 font-bold uppercase tracking-[0.2em] mb-1 border-b border-white/5 pb-1.5">
                    Terreno
                </div>
                <div className="grid grid-cols-1 gap-y-1.5 px-1">
                    <LegendItem color="#0f2e1d" label="Hierba" />
                    <LegendItem color="#1a1b20" label="Montaña" />
                    <LegendItem color="#08121f" label="Agua" />
                    <LegendItem color="#051f12" label="Bosque" />
                    <LegendItem color="#2b210e" label="Desierto" />
                </div>
            </div>

            {weather === 'rainy' && <div className="absolute inset-0 pointer-events-none bg-[url('/rain.png')] opacity-10 animate-rain"></div>}
        </div>
    );
}


function LegendItem({ color, label }: { color: string, label: string }) {
    return (
        <div className="flex items-center gap-2 text-gray-500 font-mono">
            <span className="w-1.5 h-1.5 rounded-full border border-white/10 shadow-sm" style={{ backgroundColor: color }}></span>
            {label}
        </div>
    );
}
