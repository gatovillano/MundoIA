"use client";

import { useEffect, useRef } from "react";
import * as d3 from "d3";
import useGameStore from "@/store/useGameStore";
import { CloudRain, Sun } from "lucide-react";

export default function WorldViewport() {
    const svgRef = useRef<SVGSVGElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);
    const { agents, mapa, relationships, speechBubbles, selectAgent, selectedAgentId, weather } = useGameStore();

    // Configuración D3
    useEffect(() => {
        if (!svgRef.current || !containerRef.current || mapa.length === 0) return;

        const width = containerRef.current.clientWidth;
        const height = containerRef.current.clientHeight;
        const svg = d3.select(svgRef.current);

        svg.selectAll("*").remove(); // Limpiar

        // Grupo principal con Zoom
        const g = svg.append("g");

        const zoom = d3.zoom<SVGSVGElement, unknown>()
            .scaleExtent([0.5, 5])
            .on("zoom", (event) => {
                g.attr("transform", event.transform);
            });

        svg.call(zoom);

        // Configuración de la cuadrícula
        const cols = 20;
        const rows = 20;
        const cellSize = 40;
        const gridWidth = cols * cellSize;
        const gridHeight = rows * cellSize;

        // Centrar el mapa inicialmente
        const initialScale = Math.min(width / gridWidth, height / gridHeight) * 0.85;
        const initialX = (width - gridWidth * initialScale) / 2;
        const initialY = (height - gridHeight * initialScale) / 2;

        svg.call(zoom.transform, d3.zoomIdentity.translate(initialX, initialY).scale(initialScale));

        // --- CAPA 0: TERRENO y TERRITORIOS ---
        // Colores más sofisticados y oscuros
        const factionColors: Record<string, string> = {
            "Tecnócratas": "#7c4dff",
            "Ecologistas": "#00e676"
        };

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

        // Definir gradientes en el SVG
        const defs = svg.append("defs");
        Object.entries(terrainColors).forEach(([id, colors]) => {
            const grad = defs.append("linearGradient")
                .attr("id", `grad-${id}`)
                .attr("x1", "0%").attr("y1", "0%")
                .attr("x2", "100%").attr("y2", "100%");
            grad.append("stop").attr("offset", "0%").attr("stop-color", colors.start);
            grad.append("stop").attr("offset", "100%").attr("stop-color", colors.end);
        });

        // Filtro de resplandor para agentes seleccionados
        const filter = defs.append("filter")
            .attr("id", "glow");
        filter.append("feGaussianBlur")
            .attr("stdDeviation", "2.5")
            .attr("result", "coloredBlur");
        const feMerge = filter.append("feMerge");
        feMerge.append("feMergeNode").attr("in", "coloredBlur");
        feMerge.append("feMergeNode").attr("in", "SourceGraphic");

        mapa.forEach((row, x) => {
            row.forEach((tile, y) => {
                const cellGroup = g.append("g")
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
                    const ownerColor = factionColors[tile.owner] || "#ffffff";

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
                        cellGroup.append("circle")
                            .attr("cx", cellSize / 2)
                            .attr("cy", cellSize / 2)
                            .attr("r", 10)
                            .attr("fill", "rgba(0,0,0,0.5)");

                        cellGroup.append("text")
                            .attr("x", cellSize / 2)
                            .attr("y", cellSize / 2 + 5)
                            .attr("text-anchor", "middle")
                            .attr("font-size", "16px")
                            .text(buildingIcons[b.tipo] || "🏠");
                    });
                } else if (tile.resource) {
                    // Recursos
                    const resourceIcon = tile.resource.type === 'food' ? '●' : '■';
                    const resourceColor = tile.resource.type === 'food' ? '#00e676' : '#ffd600';

                    cellGroup.append("text")
                        .attr("x", cellSize / 2)
                        .attr("y", cellSize / 2 + 4)
                        .attr("text-anchor", "middle")
                        .attr("font-size", "8px")
                        .attr("fill", resourceColor)
                        .attr("opacity", 0.6)
                        .text(resourceIcon);
                }
            });
        });

        // --- CAPA 1: GRAFO SOCIAL (Enlaces) ---
        const linkGroup = g.append("g").attr("class", "links");

        if (relationships && relationships.length > 0) {
            const agentCoords = new Map();
            agents.forEach(a => agentCoords.set(a.id, { x: a.x * cellSize + cellSize / 2, y: a.y * cellSize + cellSize / 2 }));

            relationships.forEach(rel => {
                const source = agentCoords.get(rel.source);
                const target = agentCoords.get(rel.target);

                if (source && target) {
                    let strokeColor = "#ffffff";
                    let strokeWidth = 0.5;
                    let opacity = 0.15;

                    if (rel.type === 'amigo') { strokeColor = "#00e676"; opacity = 0.3; strokeWidth = 1; }
                    if (rel.type === 'enemigo') { strokeColor = "#ff1744"; opacity = 0.3; strokeWidth = 1; }
                    if (rel.type === 'alianza') { strokeColor = "#ffd600"; opacity = 0.5; strokeWidth = 1.5; }

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
        const agentGroup = g.append("g").attr("class", "agents");

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

            // Cuerpo del agente (Brillante)
            enter.append("circle")
                .attr("r", 6)
                .attr("fill", (d) => d.grupo_id ? "#00e676" : "#e0e0e0")
                .attr("stroke", "#000")
                .attr("stroke-width", 2)
                .attr("filter", "url(#glow)"); // Glow effect

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

            merged.transition().duration(500)
                .attr("transform", (d) => `translate(${d.x * cellSize + cellSize / 2}, ${d.y * cellSize + cellSize / 2})`);

            // Actualizar estado de selección
            merged.select(".selection-ring")
                .transition().duration(200)
                .attr("opacity", (d) => d.id === selectedAgentId ? 1 : 0)
                .attr("stroke-dasharray", (d) => d.id === selectedAgentId ? "4,2" : "none");

            agentSelection.exit().remove();
        };

        updateAgents();

        // --- CAPA 3: BURBUJAS DE DIÁLOGO (GAME STYLE) ---
        const bubbleGroup = g.append("g").attr("class", "bubbles");

        if (speechBubbles) {
            Object.entries(speechBubbles).forEach(([agentId, bubble]) => {
                const agent = agents.find(a => a.id === agentId);
                if (agent) {
                    const x = agent.x * cellSize + cellSize / 2;
                    const y = agent.y * cellSize + cellSize / 2 - 25;

                    const bubbleG = bubbleGroup.append("g")
                        .attr("transform", `translate(${x}, ${y})`);

                    // Texto temporal
                    const tempText = bubbleG.append("text")
                        .attr("font-size", "10px")
                        .attr("font-family", "monospace")
                        .attr("visibility", "hidden")
                        .text(bubble.text);

                    const bbox = tempText.node()?.getBBox();
                    const width = (bbox?.width || 0) + 20;
                    const height = (bbox?.height || 0) + 12;
                    tempText.remove();

                    // Fondo estilo RPG
                    bubbleG.append("rect")
                        .attr("x", -width / 2)
                        .attr("y", -height)
                        .attr("width", width)
                        .attr("height", height)
                        .attr("rx", 4)
                        .attr("fill", "rgba(10, 11, 16, 0.9)")
                        .attr("stroke", "#7c4dff")
                        .attr("stroke-width", 1);

                    // Texto real
                    bubbleG.append("text")
                        .attr("text-anchor", "middle")
                        .attr("y", -height / 2 + 4)
                        .attr("font-size", "10px")
                        .attr("fill", "#fff")
                        .attr("font-family", "monospace")
                        .text(bubble.text);

                    // Animación
                    bubbleG.attr("opacity", 0)
                        .transition().duration(200)
                        .attr("opacity", 1)
                        .attr("transform", `translate(${x}, ${y - 5})`);
                }
            });
        }


        // --- CAPA 4: CLIMA (Overlay Sutil) ---
        if (weather === 'rainy' || weather === 'storm') {
            g.append("rect")
                .attr("width", gridWidth)
                .attr("height", gridHeight)
                .attr("fill", "#2979ff")
                .attr("opacity", 0.05)
                .style("pointer-events", "none");
        }

    }, [mapa, agents, selectedAgentId, weather, selectAgent, relationships, speechBubbles]);

    return (
        <div ref={containerRef} className="w-full h-full relative bg-[#030305] overflow-hidden">
            <svg ref={svgRef} className="w-full h-full block" />

            {/* Weather Widget */}
            <div className="absolute top-4 left-4 glass-panel px-4 py-2 rounded-full flex items-center gap-3">
                {weather === 'sunny' ? (
                    <Sun className="w-4 h-4 text-[#ffd600] animate-spin-slow" />
                ) : (
                    <CloudRain className="w-4 h-4 text-[#2979ff] animate-bounce" />
                )}
                <span className="text-xs font-mono text-gray-300 uppercase">{weather === 'sunny' ? 'Despejado' : 'Lluvioso'}</span>
            </div>

            {/* Leyenda Sofisticada */}
            <div className="absolute bottom-6 left-6 glass-panel p-4 rounded-xl border border-white/5 text-[10px] space-y-3 pointer-events-none max-w-[200px]">
                <div className="flex items-center gap-2 text-white/50 font-bold uppercase tracking-widest mb-1 border-b border-white/5 pb-2">
                    Topografía
                </div>
                <div className="grid grid-cols-2 gap-x-4 gap-y-2">
                    <div className="flex items-center gap-2 text-gray-400">
                        <span className="w-2 h-2 rounded-full bg-[#0f2e1d] border border-white/10"></span> Hierba
                    </div>
                    <div className="flex items-center gap-2 text-gray-400">
                        <span className="w-2 h-2 rounded-full bg-[#1a1b20] border border-white/10"></span> Montaña
                    </div>
                    <div className="flex items-center gap-2 text-gray-400">
                        <span className="w-2 h-2 rounded-full bg-[#08121f] border border-white/10"></span> Agua
                    </div>
                    <div className="flex items-center gap-2 text-gray-400">
                        <span className="w-2 h-2 rounded-full bg-[#051f12] border border-white/10"></span> Bosque
                    </div>
                </div>
            </div>

            {weather === 'rainy' && <div className="absolute inset-0 pointer-events-none bg-[url('/rain.png')] opacity-10 animate-rain"></div>}
        </div>
    );
}

