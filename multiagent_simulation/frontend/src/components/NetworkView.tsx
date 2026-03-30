"use client";

import { useEffect, useRef } from "react";
import * as d3 from "d3";
import useGameStore from "@/store/useGameStore";

export default function NetworkView() {
    const svgRef = useRef<SVGSVGElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);
    const { agents, relationships, selectAgent, selectedAgentId, speechBubbles } = useGameStore();

    const simulationRef = useRef<any>(null);

    // Debug: Log cuando relationships cambia
    useEffect(() => {
        console.log("[NetworkView] relationships count:", relationships.length, "agents count:", agents.length);
    }, [relationships, agents.length]);

    // 1. Inicializar Simulación (Solo al montar o cambiar estructura de red)
    useEffect(() => {
        if (!svgRef.current || !containerRef.current) return;
        
        const width = containerRef.current.clientWidth;
        const height = containerRef.current.clientHeight;
        const svg = d3.select(svgRef.current);
        
        // Asegurar que el SVG tenga tamaño explícito
        svg.attr("width", width).attr("height", height);
        
        let g = svg.select<SVGGElement>("g.vis-group");
        if (g.empty()) g = svg.append("g").attr("class", "vis-group");

        // Zoom
        const zoom = d3.zoom<SVGSVGElement, unknown>()
            .scaleExtent([0.1, 4])
            .on("zoom", (event) => g.attr("transform", event.transform));
        svg.call(zoom);

        // Filtro Neon
        let defs = svg.select<SVGDefsElement>("defs");
        if (defs.empty()) {
            defs = svg.append("defs");
            const glowFilter = defs.append("filter").attr("id", "neon-glow");
            glowFilter.append("feGaussianBlur").attr("stdDeviation", "2.5").attr("result", "coloredBlur");
            const feMerge = glowFilter.append("feMerge");
            feMerge.append("feMergeNode").attr("in", "coloredBlur");
            feMerge.append("feMergeNode").attr("in", "SourceGraphic");
        }

        // Simulación persistente
        if (!simulationRef.current) {
            simulationRef.current = d3.forceSimulation()
                .force("link", d3.forceLink().id((d: any) => d.id).distance(150))
                .force("charge", d3.forceManyBody().strength(-400))
                .force("center", d3.forceCenter(width / 2, height / 2))
                .force("collide", d3.forceCollide().radius(40));
        }

        const simulation = simulationRef.current;

        // Actualizar datos de la simulación
        const nodes = agents.map(a => {
            const existingNode = simulation.nodes().find((n: any) => n.id === a.id);
            return existingNode ? { ...a, x: existingNode.x, y: existingNode.y, vx: existingNode.vx, vy: existingNode.vy } : { ...a };
        });

        const links = relationships.map(rel => {
            const source = nodes.find(n => n.id === rel.source);
            const target = nodes.find(n => n.id === rel.target);
            return source && target ? { ...rel, source, target } : null;
        }).filter(l => l !== null);

        simulation.nodes(nodes as any);
        simulation.force("link").links(links as any);
        simulation.alpha(0.3).restart();

        // 2. Renderizado de Enlaces
        let linkLayer = g.select<SVGGElement>(".links-layer");
        if (linkLayer.empty()) linkLayer = g.append("g").attr("class", "links-layer").attr("stroke-opacity", 1);

        const linkSelection = linkLayer.selectAll("line")
            .data(links as any[], (d: any) => `${d.source.id}-${d.target.id}-${d.type}`)
            .join(
                enter => enter.append("line"),
                update => update,
                exit => exit.remove()
            )
            .attr("stroke-width", (d) => {
                const base = Math.sqrt(Math.abs(d.strength || 1)) * 1.5;
                return Math.max(0.5, base); // mínimo 0.5px para siempre visible
            })
            .attr("stroke", (d) => {
                if (d.type === 'amigo') return "#00e676";
                if (d.type === 'enemigo') return "#ff1744";
                if (d.type === 'alianza') return "#ffd600";
                if (d.type === 'conflict') return "#ff6b6b";
                // Cualquier otro tipo también visible
                return "#7c4dff";
            })
            .attr("stroke-dasharray", (d) => d.type === 'alianza' ? "4,2" : "none")
            .attr("stroke-linecap", "round");

        // 3. Renderizado de Nodos
        let nodeLayer = g.select<SVGGElement>(".nodes-layer");
        if (nodeLayer.empty()) nodeLayer = g.append("g").attr("class", "nodes-layer");

        const nodeSelection = nodeLayer.selectAll<SVGGElement, any>("g.agent-node")
            .data(nodes, (d) => d.id)
            .join(
                enter => {
                    const eg = enter.append("g").attr("class", "agent-node").attr("cursor", "pointer")
                        .call(d3.drag<any, any>()
                            .on("start", (event, d) => {
                                if (!event.active) simulation.alphaTarget(0.3).restart();
                                d.fx = d.x; d.fy = d.y;
                            })
                            .on("drag", (event, d) => { d.fx = event.x; d.fy = event.y; })
                            .on("end", (event, d) => {
                                if (!event.active) simulation.alphaTarget(0);
                                d.fx = null; d.fy = null;
                            }) as any)
                        .on("click", (event, d) => { event.stopPropagation(); selectAgent(d.id); });
                    
                    eg.append("circle").attr("class", "ring").attr("r", 15).attr("fill", "none").attr("stroke-width", 1).attr("opacity", 0.5).attr("filter", "url(#neon-glow)");
                    eg.append("circle").attr("class", "core").attr("r", 8).attr("fill", "#0a0b10").attr("stroke-width", 1.5);
                    eg.append("text").attr("class", "id-text").attr("dy", 3).attr("text-anchor", "middle").attr("font-size", "8px").attr("fill", "#fff").attr("pointer-events", "none").attr("font-family", "monospace");
                    eg.append("text").attr("class", "label-text").attr("dy", 25).attr("text-anchor", "middle").attr("font-size", "8px").attr("fill", "#bbb").attr("font-family", "monospace");
                    return eg;
                }
            );

        nodeSelection.select(".ring").attr("stroke", (d) => d.color || "#7c4dff");
        nodeSelection.select(".core").attr("stroke", (d) => d.id === selectedAgentId ? "#ffffff" : (d.color || "#7c4dff"))
            .attr("stroke-width", (d) => d.id === selectedAgentId ? 2 : 1.5);
        nodeSelection.select(".id-text").text(d => d.id.replace("A", ""));
        nodeSelection.select(".label-text").text(d => d.profesion || "Agente").attr("opacity", d => d.id === selectedAgentId ? 1 : 0);

        // 4. Burbujas
        let bubbleLayer = g.select<SVGGElement>(".bubble-layer");
        if (bubbleLayer.empty()) bubbleLayer = g.append("g").attr("class", "bubble-layer");

        const updateBubbles = () => {
            const bubbleData = Object.entries(speechBubbles || {}).map(([id, b]) => ({ id, ...b }));
            
            bubbleLayer.selectAll<SVGGElement, any>("g.bubble-g")
                .data(bubbleData, (d: any) => d.id + d.timestamp)
                .join(
                    enter => {
                        const bg = enter.append("g").attr("class", "bubble-g");
                        bg.append("rect").attr("rx", 6).attr("fill", "rgba(10, 11, 16, 0.95)").attr("stroke", "#7c4dff").attr("stroke-width", 1.5).attr("filter", "url(#neon-glow)");
                        bg.append("path").attr("d", `M -5 0 L 5 0 L 0 5 Z`).attr("fill", "#7c4dff");
                        bg.append("text").attr("text-anchor", "middle").attr("font-size", "10px").attr("fill", "#fff").attr("font-family", "monospace");
                        return bg;
                    }
                ).each(function(d: any) {
                    const text = d.text;
                    const maxWidth = 120;
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
                    const bubbleWidth = (Math.max(...lines.map(l => l.length)) * 7) + 20;
                    const bubbleHeight = (lines.length * lineHeight) + bubblePadding;

                    const g = d3.select(this);
                    g.select("rect").attr("x", -bubbleWidth / 2).attr("y", -bubbleHeight).attr("width", bubbleWidth).attr("height", bubbleHeight);
                    const t = g.select("text").attr("y", -bubbleHeight + 14);
                    t.selectAll("tspan").data(lines).join("tspan").attr("x", 0).attr("dy", (l, i) => i === 0 ? 0 : lineHeight).text(d => d);
                });
        };

        updateBubbles();

        // Tick loop
        simulation.on("tick", () => {
            linkSelection
                .attr("x1", (d: any) => d.source.x)
                .attr("y1", (d: any) => d.source.y)
                .attr("x2", (d: any) => d.target.x)
                .attr("y2", (d: any) => d.target.y);

            nodeSelection.attr("transform", (d: any) => `translate(${d.x},${d.y})`);

            bubbleLayer.selectAll<SVGGElement, any>("g.bubble-g").each(function(d: any) {
                const n = nodes.find(node => node.id === d.id);
                if (n) d3.select(this).attr("transform", `translate(${(n as any).x}, ${(n as any).y - 25})`);
            });
        });

        return () => {
            if (simulationRef.current) simulationRef.current.stop();
        };

    }, [agents, relationships, selectedAgentId, selectAgent, speechBubbles]);

    return (
        <div ref={containerRef} className="w-full h-full relative bg-[#030305] overflow-hidden">
            <svg ref={svgRef} className="w-full h-full block" />
            <div className="absolute bottom-4 right-4 bg-black/50 p-2 rounded border border-white/5 text-[10px] text-gray-500 font-mono tracking-wider backdrop-blur-sm">
                RED NEURONAL SOCIAL
            </div>
        </div>
    );
}

