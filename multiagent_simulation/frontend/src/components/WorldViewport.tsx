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

    // 1. Efecto para Terreno (Solo cuando cambia el mapa)
    useEffect(() => {
        if (!svgRef.current || !mapa || mapa.length === 0) return;

        const svg = d3.select(svgRef.current);
        let g = svg.select<SVGGElement>("g.main-group");
        if (g.empty()) g = svg.append("g").attr("class", "main-group");

        let terrainGroup = g.select<SVGGElement>(".terrain-layer");
        if (terrainGroup.empty()) terrainGroup = g.append("g").attr("class", "terrain-layer");

        const cellSize = 40;
        const terrainColors: Record<string, { start: string, end: string }> = {
            grass: { start: "#0f2e1d", end: "#143d26" },
            forest: { start: "#051f12", end: "#0a291a" },
            mountain: { start: "#1a1b20", end: "#2d2e36" },
            water: { start: "#08121f", end: "#0c1b2e" },
            desert: { start: "#2b210e", end: "#3d2f14" },
        };

        const buildingIcons: Record<string, string> = {
            "Hospital": "🏥", "Granja": "🌾", "Centro de Recarga": "⚡", 
            "Centro de Descanso": "🧘", "Centro Comunitario": "🤝", 
            "Comisaría": "👮", "Universidad": "🏛️", "Comedor": "🍽️", 
            "Centro de Ocio": "🎭", "Torre de Vigilancia": "🏹"
        };

        // Preparar defs
        let defs = svg.select<SVGDefsElement>("defs");
        if (defs.empty()) defs = svg.append("defs");
        
        Object.entries(terrainColors).forEach(([id, colors]) => {
            if (defs.select(`#grad-${id}`).empty()) {
                const grad = defs.append("linearGradient").attr("id", `grad-${id}`)
                    .attr("x1", "0%").attr("y1", "0%").attr("x2", "100%").attr("y2", "100%");
                grad.append("stop").attr("offset", "0%").attr("stop-color", colors.start);
                grad.append("stop").attr("offset", "100%").attr("stop-color", colors.end);
            }
        });

        // Renderizado del terreno del mapa - solo cuando el mapa cambia
        const flatMap = mapa.flatMap((row, x) => row.map((tile, y) => ({ ...tile, x, y })));
        const { civilizaciones, gruposDinamicos } = useGameStore.getState();

        terrainGroup.selectAll(".cell-group")
            .data(flatMap, (d: any) => `${d.x}-${d.y}`)
            .join(
                enter => {
                    const g = enter.append("g").attr("class", "cell-group")
                        .attr("transform", d => `translate(${d.x * cellSize}, ${d.y * cellSize})`);
                    g.append("rect").attr("class", "terrain-base")
                        .attr("width", cellSize).attr("height", cellSize)
                        .attr("stroke", "rgba(255,255,255,0.03)").attr("stroke-width", 0.5);
                    return g;
                }
            )
            .each(function(d: any) {
                const cell = d3.select(this);
                
                // Actualizar terreno base (gradiente)
                cell.select(".terrain-base").attr("fill", `url(#grad-${d.terrain})`);

                // Limpiar dinámicos anteriores
                cell.selectAll(".cell-overlay, .building-unit, .resource-icon, .terrain-icon").remove();
                
                // Icono de Terreno (Sutil)
                const terrainIcons: any = {
                    'forest': '🌲',
                    'mountain': '⛰️',
                    'water': '🌊',
                    'desert': '🏜️'
                };
                if (terrainIcons[d.terrain]) {
                    cell.append("text").attr("class", "terrain-icon")
                        .attr("x", cellSize / 2).attr("y", cellSize / 2 + 5).attr("text-anchor", "middle")
                        .attr("font-size", "10px").attr("opacity", 0.15).attr("pointer-events", "none")
                        .attr("fill", "#fff").text(terrainIcons[d.terrain]);
                }

                // Overlay de Territorio
                if (d.owner) {
                    const ownerInfo = civilizaciones[d.owner] || gruposDinamicos[d.owner];
                    const ownerColor = ownerInfo?.color || "#ffffff";
                    cell.append("rect").attr("class", "cell-overlay")
                        .attr("width", cellSize).attr("height", cellSize)
                        .attr("fill", "none").attr("stroke", ownerColor).attr("stroke-width", 1.5).attr("opacity", 0.3);
                    cell.append("path").attr("class", "cell-overlay")
                        .attr("d", `M 0 0 L 12 0 L 0 12 Z`).attr("fill", ownerColor).attr("opacity", 0.8);
                }

                // Edificios
                if (d.buildings && d.buildings.length > 0) {
                    d.buildings.forEach((b: any) => {
                        const ownerColor = civilizaciones[b.grupo_id]?.color || gruposDinamicos[b.grupo_id]?.color || "#7c4dff";
                        const bg = cell.append("g").attr("class", "building-unit");
                        bg.append("circle").attr("cx", cellSize / 2).attr("cy", cellSize / 2).attr("r", 12)
                            .attr("fill", "rgba(0,0,0,0.8)").attr("stroke", ownerColor).attr("stroke-width", 1.5);
                        bg.append("text").attr("x", cellSize / 2).attr("y", cellSize / 2 + 5).attr("text-anchor", "middle")
                            .attr("font-size", "14px").attr("fill", "#ffffff").text(buildingIcons[b.tipo] || "🏠");
                    });
                } else if (d.resource) {
                    const resourceIcon = d.resource.type === 'food' ? '🌾' : '💎';
                    const resourceColor = d.resource.type === 'food' ? '#fcd34d' : '#00e5ff';
                    cell.append("text").attr("class", "resource-icon")
                        .attr("x", cellSize / 2).attr("y", cellSize / 2 + 5).attr("text-anchor", "middle")
                        .attr("font-size", "12px").attr("fill", resourceColor).attr("opacity", 0.7).text(resourceIcon);
                }
            });

    }, [mapa]);

    // 2. Efecto para Zoom, Agentes, Vínculos y Burbujas (Cambios frecuentes)
    useEffect(() => {
        if (!svgRef.current || !containerRef.current || !mapa || mapa.length === 0) return;

        const width = containerRef.current.clientWidth;
        const height = containerRef.current.clientHeight;
        const svg = d3.select(svgRef.current);
        const cellSize = 40;

        // Grupo principal con Zoom
        let g = svg.select<SVGGElement>("g.main-group");
        if (g.empty()) g = svg.append("g").attr("class", "main-group");

        // Capas secundarias
        let linkGroup = g.select<SVGGElement>(".links-layer");
        if (linkGroup.empty()) linkGroup = g.append("g").attr("class", "links-layer");

        let agentGroup = g.select<SVGGElement>(".agents-layer");
        if (agentGroup.empty()) agentGroup = g.append("g").attr("class", "agents-layer");

        let bubbleGroup = g.select<SVGGElement>(".bubbles-layer");
        if (bubbleGroup.empty()) bubbleGroup = g.append("g").attr("class", "bubbles-layer");

        let weatherGroup = g.select<SVGGElement>(".weather-layer");
        if (weatherGroup.empty()) weatherGroup = g.append("g").attr("class", "weather-layer");

        const zoom = d3.zoom<SVGSVGElement, unknown>()
            .scaleExtent([0.5, 5])
            .on("zoom", (event) => g.attr("transform", event.transform));
        
        if (!initializedRef.current) {
            svg.call(zoom);
            const cols = mapa.length;
            const rows = mapa[0].length;
            const gridWidth = cols * cellSize;
            const gridHeight = rows * cellSize;
            const initialScale = Math.min(width / gridWidth, height / gridHeight) * 0.85;
            const initialX = (width - gridWidth * initialScale) / 2;
            const initialY = (height - gridHeight * initialScale) / 2;
            svg.call(zoom.transform, d3.zoomIdentity.translate(initialX, initialY).scale(initialScale));
            initializedRef.current = true;
        }

        // --- VÍNCULOS (Data binding) ---
        if (showLinks && relationships) {
            const agentCoords = new Map();
            agents.forEach(a => agentCoords.set(a.id, { x: a.x * cellSize + cellSize / 2, y: a.y * cellSize + cellSize / 2 }));
            
            const relationshipData = relationships.map(rel => ({
                ...rel,
                coords: { source: agentCoords.get(rel.source), target: agentCoords.get(rel.target) }
            })).filter(d => d.coords.source && d.coords.target);

            linkGroup.selectAll("line")
                .data(relationshipData, (d: any) => `${d.source}-${d.target}-${d.type}`)
                .join("line")
                .attr("x1", d => d.coords.source.x).attr("y1", d => d.coords.source.y)
                .attr("x2", d => d.coords.target.x).attr("y2", d => d.coords.target.y)
                .attr("stroke", d => d.type === 'amigo' ? "#00e676" : d.type === 'enemigo' ? "#ff1744" : d.type === 'alianza' ? "#ffd600" : "#ffffff")
                .attr("stroke-width", d => d.type === 'amigo' ? 1.2 : d.type === 'enemigo' ? 2 : d.type === 'alianza' ? 2.5 : 0.5)
                .attr("opacity", d => d.type === 'amigo' ? 0.5 : d.type === 'enemigo' ? 0.7 : d.type === 'alianza' ? 0.8 : 0.15)
                .attr("stroke-dasharray", d => d.type === 'alianza' ? "4,2" : "none");
        } else {
            linkGroup.selectAll("line").remove();
        }

        // --- AGENTES ---
        const prevPositions = new Map<string, { x: number, y: number }>();
        prevAgentsRef.current.forEach((a: any) => prevPositions.set(a.id, { x: a.x, y: a.y }));
        prevAgentsRef.current = agents;

        const agentSelection = agentGroup.selectAll<SVGGElement, any>(".agent")
            .data(agents, (d) => d.id);

        const enter = agentSelection.enter().append("g").attr("class", "agent").attr("cursor", "pointer")
            .on("click", (event, d) => { event.stopPropagation(); selectAgent(d.id); });

        enter.append("circle").attr("class", "selection-ring").attr("r", 18).attr("fill", "none").attr("stroke", "#7c4dff").attr("stroke-width", 1.5).attr("opacity", 0);
        enter.append("rect").attr("x", -7).attr("y", -7).attr("width", 14).attr("height", 14).attr("rx", 2).attr("fill", (d) => d.color || "#e0e0e0").attr("stroke", "#000").attr("stroke-width", 1.5);
        enter.append("rect").attr("x", -5).attr("y", -4).attr("width", 10).attr("height", 3).attr("fill", "#000").attr("opacity", 0.8);
        enter.append("rect").attr("x", -4).attr("y", -3).attr("width", 2).attr("height", 1).attr("fill", "#00e5ff");
        enter.append("rect").attr("x", 2).attr("y", -3).attr("width", 2).attr("height", 1).attr("fill", "#00e5ff");
        enter.append("text").attr("dy", -10).attr("text-anchor", "middle").attr("font-size", "8px").attr("fill", "#ffffff").attr("font-family", "monospace").attr("font-weight", "bold").attr("opacity", 0.8).text((d) => {
            const name = d.id || "???";
            // Si el nombre sigue el formato viejo A12_345, cortamos la A. Si no, mostramos los primeros caracteres cortos
            if (name.match(/^A\d+_\d+$/)) return name.replace('A', '');
            return name.substring(0, 5); // Mostrar máximo 5 letras para que entre en la UI sin desbordar
        });

        const merged = enter.merge(agentSelection);
        merged.each(function(d) {
            const currentPos = { x: d.x * cellSize + cellSize / 2, y: d.y * cellSize + cellSize / 2 };
            const prevPos = prevPositions.get(d.id);
            if (prevPos) {
                const prevX = prevPos.x * cellSize + cellSize / 2;
                const prevY = prevPos.y * cellSize + cellSize / 2;
                d3.select(this).attr("transform", `translate(${prevX}, ${prevY})`).transition().duration(400).attr("transform", `translate(${currentPos.x}, ${currentPos.y})`);
            } else {
                d3.select(this).attr("transform", `translate(${currentPos.x}, ${currentPos.y})`);
            }
        });

        merged.select(".selection-ring").transition().duration(200).attr("opacity", (d) => d.id === selectedAgentId ? 1 : 0).attr("stroke-dasharray", (d) => d.id === selectedAgentId ? "4,2" : "none");
        agentSelection.exit().remove();

        // --- BURBUJAS ---
        if (speechBubbles && !hideBubbles) {
            const bubbleData = Object.entries(speechBubbles).map(([id, b]) => ({ id, ...b })).filter(b => agents.some(a => a.id === b.id));
            
            bubbleGroup.selectAll(".bubble-g")
                .data(bubbleData, (d: any) => d.id + d.timestamp)
                .join(
                    enter => {
                        const bg = enter.append("g").attr("class", "bubble-g").attr("opacity", 0);
                        bg.append("rect").attr("class", "bubble-bg").attr("rx", 6).attr("fill", "rgba(10, 11, 16, 0.95)").attr("stroke", "#7c4dff").attr("stroke-width", 1.5);
                        bg.append("path").attr("d", "M -5 0 L 5 0 L 0 5 Z").attr("fill", "#7c4dff");
                        bg.append("text").attr("class", "bubble-text").attr("text-anchor", "middle").attr("font-size", "10px").attr("fill", "#fff").attr("font-family", "monospace");
                        return bg;
                    },
                    update => update,
                    exit => exit.transition().duration(200).attr("opacity", 0).remove()
                ).each(function(d: any) {
                    const agent = agents.find(a => a.id === d.id);
                    if (!agent) return;
                    const x = agent.x * cellSize + cellSize / 2;
                    const y = agent.y * cellSize + cellSize / 2 - 25;
                    const g = d3.select(this);
                    
                    const text = d.text;
                    const maxWidth = 140;
                    const charsPerLine = Math.floor(maxWidth / 7);
                    const words = text.split(/\s+/);
                    const lines: string[] = [];
                    let currentLine = "";
                    words.forEach((word: string) => {
                        if ((currentLine + word).length > charsPerLine) { lines.push(currentLine.trim()); currentLine = word + " "; }
                        else { currentLine += word + " "; }
                    });
                    lines.push(currentLine.trim());

                    const lineHeight = 12;
                    const bubblePadding = 10;
                    const bubbleWidth = Math.min(maxWidth, (Math.max(...lines.map(l => l.length)) * 7) + 20);
                    const bubbleHeight = (lines.length * lineHeight) + bubblePadding;

                    g.select("rect").attr("x", -bubbleWidth / 2).attr("y", -bubbleHeight).attr("width", bubbleWidth).attr("height", bubbleHeight);
                    const t = g.select("text").attr("y", -bubbleHeight + 14);
                    t.selectAll("tspan").data(lines).join("tspan").attr("x", 0).attr("dy", (l, i) => i === 0 ? 0 : lineHeight).text(d => d);

                    g.transition().duration(300).attr("opacity", 1).attr("transform", `translate(${x}, ${y - 8})`);
                });
        } else {
            bubbleGroup.selectAll(".bubble-g").remove();
        }

        // --- CLIMA ---
        weatherGroup.selectAll("rect")
            .data((weather === 'rainy' || weather === 'storm') ? [1] : [])
            .join("rect")
            .attr("width", mapa.length * cellSize).attr("height", mapa[0].length * cellSize)
            .attr("fill", "#2979ff").attr("opacity", 0.05).style("pointer-events", "none");

    }, [agents, selectedAgentId, weather, selectAgent, relationships, speechBubbles, showLinks, hideBubbles]);

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
