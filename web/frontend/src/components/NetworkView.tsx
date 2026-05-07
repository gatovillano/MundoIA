"use client";

import { useEffect, useRef, useState } from "react";
import * as d3 from "d3";
import useGameStore from "@/store/useGameStore";
import { getAgentName, replaceIdsWithNames } from "@/utils/nameUtils";

export default function NetworkView() {
    const svgRef = useRef<SVGSVGElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);
    const { agents, relationships, selectAgent, selectedAgentId, speechBubbles, civilizaciones, gruposDinamicos, showBubbles, toggleBubbles } = useGameStore();
    const [isolatedAgentId, setIsolatedAgentId] = useState<string | null>(null);
    const lastClickRef = useRef<{id: string | null, time: number}>({ id: null, time: 0 });

    const simulationRef = useRef<any>(null);

    // Debug: Log cuando relationships cambia
    useEffect(() => {
        console.debug && console.debug("[NetworkView] relationships count:", (relationships || []).length, "agents count:", agents.length);
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
                .force("link", d3.forceLink().id((d: any) => d.id).distance(120).strength(0.7))
                .force("charge", d3.forceManyBody().strength(-150))
                .force("x", d3.forceX(width / 2).strength(0.15))
                .force("y", d3.forceY(height / 2).strength(0.15))
                .force("collide", d3.forceCollide().radius(35))
                .velocityDecay(0.5);
        } else {
            // Actualizar fuerzas de posicionamiento central en caso de resize
            simulationRef.current.force("x", d3.forceX(width / 2).strength(0.15));
            simulationRef.current.force("y", d3.forceY(height / 2).strength(0.15));
        }

        const simulation = simulationRef.current;

        // Actualizar datos de la simulación
        const nodes = agents.map(a => {
            const existingNode = simulation.nodes().find((n: any) => n.id === a.id);
            return existingNode ? { ...a, x: existingNode.x, y: existingNode.y, vx: existingNode.vx, vy: existingNode.vy } : { ...a };
        });

        const links = (relationships || []).map(rel => {
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

        // Construir líneas de pertenencia a grupo (conectar miembros adyacentes)
        const groupsMap: Record<string, any[]> = {};
        nodes.forEach((n: any) => {
            const gid = n.grupo_id || n.group_id || null;
            if (gid) {
                groupsMap[gid] = groupsMap[gid] || [];
                groupsMap[gid].push(n);
            }
        });

        const groupLinks = Object.entries(groupsMap).flatMap(([gid, members]) => members.slice(1).map((m: any, idx: number) => ({ source: members[idx], target: m, groupId: gid })));

        const groupSelection = linkLayer.selectAll("line.group-link")
            .data(groupLinks as any[], (d: any) => `${d.source.id}-${d.target.id}-${d.groupId}`)
            .join(
                enter => enter.append("line").attr("class", "group-link"),
                update => update,
                exit => exit.remove()
            )
            .attr("stroke", (d: any) => {
                const ownerInfo = (civilizaciones || {})[d.groupId] || (gruposDinamicos || {})[d.groupId];
                return ownerInfo?.color || '#9c27b0';
            })
            .attr("stroke-width", 0.8)
            .attr("opacity", 0.6)
            .attr("stroke-linecap", "round")
            .lower();

        // Enlaces de relaciones (relaciones sociales)
        // Si hay un agente aislado, filtrar links y nodes para mostrar solo sus relaciones
        const filteredLinks = isolatedAgentId ? (links as any[]).filter(l => l.source.id === isolatedAgentId || l.target.id === isolatedAgentId) : links as any[];

        const relSelection = linkLayer.selectAll("line.rel-link")
            .data(filteredLinks as any[], (d: any) => `${d.source.id}-${d.target.id}-${d.type}`)
            .join(
                enter => enter.append("line").attr("class", "rel-link"),
                update => update,
                exit => exit.remove()
            );

        relSelection
            .attr("stroke-width", (d: any) => {
                const base = Math.sqrt(Math.abs(d.strength || 0)) * 1.6 || 0.8;
                // Ajuste por tipo para garantizar visibilidad y jerarquía
                if (d.type === 'amigo') return Math.max(1.0, base);
                if (d.type === 'enemigo') return Math.max(1.8, base, 1.8);
                if (d.type === 'alianza') return Math.max(1.2, base, 1.0);
                if (d.type === 'conocido') return Math.max(0.6, base * 0.6);
                return Math.max(0.6, base);
            })
            .attr("stroke", (d: any) => {
                if (d.type === 'amigo') return "#00e676";
                if (d.type === 'enemigo') return "#ff1744";
                if (d.type === 'alianza' || d.type === 'alliance') return "#ffd600";
                if (d.type === 'conflict') return "#ff6b6b";
                if (d.type === 'conocido') return "#90A4AE";
                return "#7c4dff";
            })
            .attr("stroke-dasharray", (d: any) => (d.type === 'alianza' || d.type === 'alliance') ? "6,3" : "none")
            .attr("stroke-linecap", "round");

        // Símbolos para alianzas
        const allianceLinks = (filteredLinks as any[]).filter(l => l.type === 'alianza' || l.type === 'alliance');
        const allianceSymbols = linkLayer.selectAll("text.alliance-symbol").data(allianceLinks, (d: any) => `${d.source.id}-${d.target.id}`);
        allianceSymbols.join(
            enter => enter.append("text").attr("class", "alliance-symbol").attr("text-anchor", "middle").attr("alignment-baseline", "middle").text("🤝"),
            update => update,
            exit => exit.remove()
        ).attr("font-size", 10).attr("opacity", 0.95).attr("pointer-events", "none");

        // 3. Renderizado de Nodos
        let nodeLayer = g.select<SVGGElement>(".nodes-layer");
        if (nodeLayer.empty()) nodeLayer = g.append("g").attr("class", "nodes-layer");

        // Si hay un agente aislado, solo mostrar el nodo y sus vecinos directos
        const visibleNodeIds = isolatedAgentId ? new Set<string>([isolatedAgentId, ...(links as any[]).filter(l => l.source.id === isolatedAgentId || l.target.id === isolatedAgentId).flatMap(l => [l.source.id, l.target.id])]) : null;

        const nodeSelection = nodeLayer.selectAll<SVGGElement, any>("g.agent-node")
            .data(nodes.filter((n: any) => !visibleNodeIds || visibleNodeIds.has(n.id)), (d) => d.id)
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
                        .on("dblclick", (event, d) => {
                            event.stopPropagation();
                            if (isolatedAgentId === d.id) {
                                // Desaislar: volver a vista completa
                                setIsolatedAgentId(null);
                                svg.transition().duration(400).call(zoom.transform as any, d3.zoomIdentity);
                                // Restaurar alpha para que sim vuelva a acomodar
                                simulation.alpha(0.3).restart();
                            } else {
                                // Aislar agente: centrar y filtrar nodos/enlaces
                                setIsolatedAgentId(d.id);
                                const transform = d3.zoomIdentity.translate(width / 2 - d.x, height / 2 - d.y).scale(1.2);
                                svg.transition().duration(600).call(zoom.transform as any, transform);
                                // Bajar alpha para reposicionar
                                simulation.alpha(0.3).restart();
                            }
                        })
                        .on("click", (event, d) => { event.stopPropagation(); selectAgent(d.id); });
                    
                    // Sombras y anillos de estado
                    eg.append("circle").attr("class", "selection-glow").attr("r", 20).attr("fill", "none").attr("stroke", "#fff").attr("stroke-width", 2).attr("opacity", 0).attr("filter", "url(#neon-glow)");
                    eg.append("ellipse").attr("class", "shadow").attr("cx", 0).attr("cy", 2).attr("rx", 8).attr("ry", 3).attr("fill", "rgba(0,0,0,0.3)");
                    
                    const body = eg.append("g").attr("class", "body-group").attr("transform", "translate(0, 10)"); // Centrar verticalmente un poco
                    
                    // Capas del cuerpo (se llenarán en el update/each)
                    body.append("path").attr("class", "torso");
                    body.append("rect").attr("class", "head");
                    body.append("g").attr("class", "hair-group");
                    body.append("g").attr("class", "face-group");
                    body.append("rect").attr("class", "arm-l");
                    body.append("rect").attr("class", "arm-r");

                    eg.append("text").attr("class", "label-text").attr("dy", 25).attr("text-anchor", "middle").attr("font-size", "8px").attr("fill", "#bbb").attr("font-family", "monospace");
                    return eg;
                },
                update => update,
                exit => exit.remove()
            );

        // 3.1 Actualizar apariencia detallada de cada nodo
        const skinTones = ["#FFDBAC", "#F1C27D", "#E0AC69", "#8D5524", "#C68642"];
        const hairColors = ["#000000", "#4B2C20", "#8D4E33", "#B1B1B1", "#D6C4C2", "#E4B877"];

        nodeSelection.each(function(d: any) {
            const node = d3.select(this);
            const seed = (d.id || "0").split('').reduce((a: number, b: string) => a + b.charCodeAt(0), 0);
            const skin = skinTones[seed % skinTones.length];
            const hair = hairColors[(seed * 7) % hairColors.length];
            const hairStyle = (seed * 3) % 4;
            const color = d.color || "#7c4dff";
            const isSelected = d.id === selectedAgentId;

            // Escalar según capital social
            const capital = d.social_metrics?.capital_social || 10;
            const scale = 0.8 + (capital / 100) * 0.4;
            node.select(".body-group").attr("transform", `translate(0, 8) scale(${scale})`);

            const g = node.select(".body-group");
            
            // Torso
            g.select(".torso")
                .attr("d", "M -4.5 -16 L 4.5 -16 Q 5.5 -16 5.5 -13 L 5.5 -6 Q 5.5 -2 0 -2 Q -5.5 -2 -5.5 -6 L -5.5 -13 Q -5.5 -16 -4.5 -16")
                .attr("fill", color)
                .attr("stroke", isSelected ? "#fff" : "rgba(255,255,255,0.1)")
                .attr("stroke-width", isSelected ? 1.5 : 1);
            
            // Cabeza
            g.select(".head").attr("x", -5.5).attr("y", -26).attr("width", 11).attr("height", 11).attr("rx", 5).attr("fill", skin);
            
            // Cabello
            const hG = g.select(".hair-group");
            hG.selectAll("*").remove();
            if (hairStyle === 0) hG.append("path").attr("d", "M -5.5 -26 Q 0 -32 5.5 -26 L 5.5 -24 L -5.5 -24 Z").attr("fill", hair);
            else if (hairStyle === 1) hG.append("path").attr("d", "M -5.5 -26 Q 2 -34 7 -26 L 5 -24 L -5.5 -24 Z").attr("fill", hair);
            else if (hairStyle === 2) hG.append("path").attr("d", "M -6 -26 Q 0 -30 6 -26 L 7 -18 L -7 -18 Z").attr("fill", hair);
            else { hG.append("circle").attr("cx", 0).attr("cy", -26).attr("r", 5.5).attr("fill", hair); hG.append("circle").attr("cx", 0).attr("cy", -30).attr("r", 2.5).attr("fill", hair); }

            // Rostro
            const fG = g.select(".face-group");
            fG.selectAll("*").remove();
            fG.append("circle").attr("cx", -2).attr("cy", -21).attr("r", 1.2).attr("fill", "#212121");
            fG.append("circle").attr("cx", 2).attr("cy", -21).attr("r", 1.2).attr("fill", "#212121");
            fG.append("circle").attr("cx", -2.4).attr("cy", -21.4).attr("r", 0.4).attr("fill", "#fff");
            fG.append("circle").attr("cx", 1.6).attr("cy", -21.4).attr("r", 0.4).attr("fill", "#fff");

            // Brazos
            g.select(".arm-l").attr("x", -6.5).attr("y", -15).attr("width", 2).attr("height", 6).attr("rx", 1).attr("fill", skin);
            g.select(".arm-r").attr("x", 4.5).attr("y", -15).attr("width", 2).attr("height", 6).attr("rx", 1).attr("fill", skin);

            // Resplandor de selección
            node.select(".selection-glow").attr("opacity", isSelected ? 0.6 : 0).attr("stroke", color);
        });

        // Label muestra nivel de influencia si está seleccionado
        nodeSelection.select(".label-text")
            .text(d => {
                if (d.id === selectedAgentId) {
                    return d.identidad?.nombre || d.id;
                }
                return d.profesion || "";
            })
            .attr("opacity", d => d.id === selectedAgentId ? 1 : 0);

        // Añadir indicador de seguidores como anillo exterior
        nodeSelection.each(function(d: any) {
            const g = d3.select(this);
            const followers = d.social_metrics?.seguidores || 0;
            const capital = d.social_metrics?.capital_social || 10;
            
            // Eliminar indicador previo de seguidores
            g.select(".followers-ring").remove();
            
            // Añadir anillo de seguidores si tiene
            if (followers > 0) {
                const ringRadius = 18 + (capital / 100) * 8;
                g.insert("circle", ":first-child")
                    .attr("class", "followers-ring")
                    .attr("r", ringRadius)
                    .attr("fill", "none")
                    .attr("stroke", "#00e5ff")
                    .attr("stroke-width", Math.min(2, 0.5 + followers / 10))
                    .attr("stroke-dasharray", "3,2")
                    .attr("opacity", 0.6);
            }
        });

        // 4. Burbujas
        let bubbleLayer = g.select<SVGGElement>(".bubble-layer");
        if (bubbleLayer.empty()) bubbleLayer = g.append("g").attr("class", "bubble-layer");

        const updateBubbles = () => {
            if (!showBubbles) {
                bubbleLayer.selectAll("g.bubble-g").remove();
                return;
            }
            const bubbleData = Object.entries(speechBubbles || {}).map(([id, b]) => ({ id, ...b }));
            
            bubbleLayer.selectAll<SVGGElement, any>("g.bubble-g")
                .data(bubbleData, (d: any) => d.id + d.timestamp)
                .join(
                    enter => {
                        const bg = enter.append("g").attr("class", "bubble-g");
                        bg.append("rect").attr("rx", 6).attr("fill", "rgba(10, 11, 16, 0.95)").attr("stroke", "#7c4dff").attr("stroke-width", 1.5).attr("filter", "url(#neon-glow)");
                        bg.append("path").attr("d", `M -5 0 L 5 0 L 0 5 Z`).attr("fill", "#7c4dff");
                        bg.append("text").attr("text-anchor", "middle").attr("font-size", "8px").attr("fill", "#fff").attr("font-family", "monospace");
                        return bg;
                    }
                ).each(function(d: any) {
                    const text = replaceIdsWithNames(d.text || "", agents);
                    const maxWidth = 120;
                    const charsPerLine = Math.floor(maxWidth / 5.5);
                    const words = text.split(/\s+/);
                    const lines: string[] = [];
                    let currentLine = "";
                    words.forEach((word: string) => {
                        if ((currentLine + word).length > charsPerLine) { lines.push(currentLine.trim()); currentLine = word + " "; }
                        else { currentLine += word + " "; }
                    });
                    lines.push(currentLine.trim());

                    const lineHeight = 10;
                    const bubblePadding = 10;
                    const bubbleWidth = (Math.max(...lines.map(l => l.length)) * 5.5) + 20;
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
            // Relaciones sociales
            relSelection
                .attr("x1", (d: any) => d.source.x)
                .attr("y1", (d: any) => d.source.y)
                .attr("x2", (d: any) => d.target.x)
                .attr("y2", (d: any) => d.target.y);

            // Líneas de grupo (debajo)
            groupSelection
                .attr("x1", (d: any) => d.source.x)
                .attr("y1", (d: any) => d.source.y)
                .attr("x2", (d: any) => d.target.x)
                .attr("y2", (d: any) => d.target.y);

            // Símbolos de alianza (posición en el punto medio)
            linkLayer.selectAll("text.alliance-symbol")
                .attr("x", (d: any) => (d.source.x + d.target.x) / 2)
                .attr("y", (d: any) => (d.source.y + d.target.y) / 2);

            nodeSelection.attr("transform", (d: any) => `translate(${d.x},${d.y})`);

            // Si está aislado, aplicar pequeñas animaciones a los nodos visibles
            if (isolatedAgentId) {
                nodeSelection.selectAll(".selection-glow").attr("opacity", (d: any) => d.id === isolatedAgentId ? 0.8 : 0.15);
            }

            if (showBubbles) {
                bubbleLayer.selectAll<SVGGElement, any>("g.bubble-g").each(function(d: any) {
                    const n = nodes.find(node => node.id === d.id);
                    if (n) d3.select(this).attr("transform", `translate(${(n as any).x}, ${(n as any).y - 25})`);
                });
            } else {
                bubbleLayer.selectAll("g.bubble-g").remove();
            }
        });

        return () => {
            if (simulationRef.current) simulationRef.current.stop();
        };

    }, [agents, relationships, selectedAgentId, selectAgent, speechBubbles, showBubbles]);

    return (
        <div ref={containerRef} className="w-full h-full relative bg-[#030305] overflow-hidden">
            <svg ref={svgRef} className="w-full h-full block" />
            
            <div className="absolute bottom-4 right-4 flex items-center gap-3">
                <button 
                    onClick={toggleBubbles}
                    className={`px-3 py-1.5 rounded border text-[10px] font-mono tracking-wider backdrop-blur-sm transition-all ${
                        showBubbles 
                        ? "bg-[#7c4dff]/20 border-[#7c4dff] text-[#7c4dff] hover:bg-[#7c4dff]/30" 
                        : "bg-black/40 border-white/10 text-gray-400 hover:bg-white/5"
                    }`}
                >
                    {showBubbles ? "🗨️ BURBUJAS: ON" : "🗨️ BURBUJAS: OFF"}
                </button>
                <div className="bg-black/50 p-2 rounded border border-white/5 text-[10px] text-gray-500 font-mono tracking-wider backdrop-blur-sm">
                    RED NEURONAL SOCIAL
                </div>
            </div>
        </div>
    );
}
