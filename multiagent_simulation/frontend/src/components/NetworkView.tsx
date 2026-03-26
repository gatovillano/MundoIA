"use client";

import { useEffect, useRef } from "react";
import * as d3 from "d3";
import useGameStore from "@/store/useGameStore";

export default function NetworkView() {
    const svgRef = useRef<SVGSVGElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);
    const { agents, relationships, selectAgent, selectedAgentId, speechBubbles } = useGameStore();

    useEffect(() => {
        if (!svgRef.current || !containerRef.current || agents.length === 0) return;

        const width = containerRef.current.clientWidth;
        const height = containerRef.current.clientHeight;
        const svg = d3.select(svgRef.current);

        svg.selectAll("*").remove();

        // 1. Datos para simulación
        const nodes = agents.map(a => ({ ...a })); // Copia para no mutar store directamente

        const links = relationships.map(rel => {
            const sourceInfo = nodes.find(n => n.id === rel.source);
            const targetInfo = nodes.find(n => n.id === rel.target);
            return sourceInfo && targetInfo ? { ...rel, source: sourceInfo, target: targetInfo } : null;
        }).filter(l => l !== null);

        // 2. Simulación de fuerza
        const simulation = d3.forceSimulation(nodes as any)
            .force("link", d3.forceLink(links as any).id((d: any) => d.id).distance(150))
            .force("charge", d3.forceManyBody().strength(-400))
            .force("center", d3.forceCenter(width / 2, height / 2))
            .force("collide", d3.forceCollide().radius(40));

        // 3. Renderizado - Estilo Neon/Cyber
        const g = svg.append("g");

        // Zoom
        const zoom = d3.zoom<SVGSVGElement, unknown>()
            .scaleExtent([0.1, 4])
            .on("zoom", (event) => g.attr("transform", event.transform));
        svg.call(zoom);

        // Definir glow filters
        const defs = svg.append("defs");
        const glowFilter = defs.append("filter").attr("id", "neon-glow");
        glowFilter.append("feGaussianBlur").attr("stdDeviation", "2.5").attr("result", "coloredBlur");
        const feMerge = glowFilter.append("feMerge");
        feMerge.append("feMergeNode").attr("in", "coloredBlur");
        feMerge.append("feMergeNode").attr("in", "SourceGraphic");

        // Enlaces con gradientes o colores brillantes
        const link = g.append("g")
            .attr("stroke-opacity", 0.6)
            .selectAll("line")
            .data(links as any[])
            .join("line")
            .attr("stroke-width", (d) => Math.sqrt(Math.abs(d.strength || 1)) * 1.5)
            .attr("stroke", (d) => {
                if (d.type === 'amigo') return "#00e676";
                if (d.type === 'enemigo') return "#ff1744";
                if (d.type === 'alianza') return "#ffd600";
                return "rgba(255,255,255,0.1)";
            })
            .attr("stroke-dasharray", (d) => d.type === 'alianza' ? "4,2" : "none");

        // Nodos estilo Cyber
        const node = g.append("g")
            .selectAll("g")
            .data(nodes)
            .join("g")
            .attr("class", "agent-node")
            .attr("cursor", "pointer")
            .call(d3.drag<any, any>()
                .on("start", (event, d) => {
                    if (!event.active) simulation.alphaTarget(0.3).restart();
                    d.fx = d.x;
                    d.fy = d.y;
                })
                .on("drag", (event, d) => {
                    d.fx = event.x;
                    d.fy = event.y;
                })
                .on("end", (event, d) => {
                    if (!event.active) simulation.alphaTarget(0);
                    d.fx = null;
                    d.fy = null;
                }) as any)
            .on("click", (event, d) => {
                event.stopPropagation();
                selectAgent(d.id);
            });

        // Círculo exterior (Glow)
        node.append("circle")
            .attr("r", 15)
            .attr("fill", "none")
            .attr("stroke", (d) => d.color || "#7c4dff")
            .attr("stroke-width", 1)
            .attr("opacity", 0.5)
            .attr("filter", "url(#neon-glow)");

        // Círculo interior
        node.append("circle")
            .attr("r", 8)
            .attr("fill", "#0a0b10")
            .attr("stroke", (d) => d.id === selectedAgentId ? "#ffffff" : (d.color || "#7c4dff"))
            .attr("stroke-width", (d) => d.id === selectedAgentId ? 2 : 1.5);

        // Icono/Texto
        node.append("text")
            .attr("dy", 3)
            .attr("text-anchor", "middle")
            .attr("font-size", "8px")
            .attr("fill", "#fff")
            .attr("pointer-events", "none")
            .attr("font-family", "monospace")
            .text(d => d.id.replace("A", ""));

        // Etiqueta al hover o seleccionado
        const labels = node.append("text")
            .attr("dy", 25)
            .attr("text-anchor", "middle")
            .attr("font-size", "8px")
            .attr("fill", "#bbb")
            .attr("font-family", "monospace")
            .text(d => d.profesion || "Agente")
            .attr("opacity", d => d.id === selectedAgentId ? 1 : 0);


        // --- BURBUJAS DE DIÁLOGO ---
        const bubbleContainer = g.append("g").attr("class", "bubble-container");

        const renderBubbles = () => {
            bubbleContainer.selectAll("*").remove();

            if (!speechBubbles) return;

            Object.entries(speechBubbles).forEach(([agentId, bubble]) => {
                const n = nodes.find(node => node.id === agentId);
                if (n) {
                    const bx = (n as any).x;
                    const by = (n as any).y - 25;

                    const bubbleG = bubbleContainer.append("g")
                        .attr("transform", `translate(${bx}, ${by})`);

                    // Lógica de envuelto idéntica a WorldViewport
                    const maxWidth = 120;
                    const words = bubble.text.split(/\s+/);
                    const lines: string[] = [];
                    let currentLine = "";
                    const charsPerLine = Math.floor(maxWidth / 7);

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
                    const bubbleWidth = (Math.max(...lines.map(l => l.length)) * 7) + 20;
                    const bubbleHeight = (lines.length * lineHeight) + bubblePadding;

                    // Fondo
                    bubbleG.append("rect")
                        .attr("x", -bubbleWidth / 2)
                        .attr("y", -bubbleHeight)
                        .attr("width", bubbleWidth)
                        .attr("height", bubbleHeight)
                        .attr("rx", 6)
                        .attr("fill", "rgba(10, 11, 16, 0.95)")
                        .attr("stroke", "#7c4dff")
                        .attr("stroke-width", 1.5)
                        .attr("filter", "url(#neon-glow)");

                    // Flecha
                    bubbleG.append("path")
                        .attr("d", `M -5 0 L 5 0 L 0 5 Z`)
                        .attr("fill", "#7c4dff");

                    // Texto
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
                }
            });
        };

        // Actualización en cada tick
        simulation.on("tick", () => {
            link
                .attr("x1", (d: any) => d.source.x)
                .attr("y1", (d: any) => d.source.y)
                .attr("x2", (d: any) => d.target.x)
                .attr("y2", (d: any) => d.target.y);

            node
                .attr("transform", (d: any) => `translate(${d.x},${d.y})`);

            // Reposicionar burbujas en el contenedor existente (más eficiente que recrear todo en cada tick)
            bubbleContainer.selectAll("g")
                .data(Object.keys(speechBubbles || {}))
                .each(function (agentId) {
                    const n = nodes.find(node => node.id === agentId);
                    if (n) {
                        d3.select(this).attr("transform", `translate(${(n as any).x}, ${(n as any).y - 25})`);
                    }
                });
        });

        // Si cambian los mensajes, recreamos las burbujas
        renderBubbles();

        // Limpieza
        return () => {
            simulation.stop();
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

