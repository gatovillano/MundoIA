'use client';

import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';
import { useSimulationStore } from '../store/useSimulationStore';
import { motion } from 'framer-motion';

export default function SimulationView() {
    const svgRef = useRef<SVGSVGElement>(null);
    const { agents, relationships, setSelectedAgent } = useSimulationStore();

    useEffect(() => {
        if (!svgRef.current) return;

        const svg = d3.select(svgRef.current);
        const width = svgRef.current.clientWidth;
        const height = svgRef.current.clientHeight;

        svg.selectAll("*").remove();

        // Filters for glow effects
        const defs = svg.append("defs");

        const glowFilter = defs.append("filter")
            .attr("id", "glow")
            .attr("x", "-50%")
            .attr("y", "-50%")
            .attr("width", "200%")
            .attr("height", "200%");

        glowFilter.append("feGaussianBlur")
            .attr("stdDeviation", "3")
            .attr("result", "blur");
        glowFilter.append("feComposite")
            .attr("in", "SourceGraphic")
            .attr("in2", "blur")
            .attr("operator", "over");

        const g = svg.append("g");

        // Zoom behavior
        const zoom = d3.zoom().on("zoom", (event) => {
            g.attr("transform", event.transform);
        });
        svg.call(zoom as any);

        const nodes = Array.from(agents.values()).map(a => ({ ...a }));
        const links = relationships.map(r => ({
            source: r.source,
            target: r.target,
            strength: r.strength,
            type: r.type
        }));

        const simulation = d3.forceSimulation(nodes as any)
            .force("link", d3.forceLink(links).id((d: any) => d.id).distance(150))
            .force("charge", d3.forceManyBody().strength(-500))
            .force("center", d3.forceCenter(width / 2, height / 2))
            .force("collision", d3.forceCollide().radius(40));

        const link = g.append("g")
            .selectAll("line")
            .data(links)
            .join("line")
            .attr("stroke", (d: any) => d.type === 'amigo' ? '#00ff9d' : d.type === 'enemigo' ? '#ff3e3e' : '#00f2ff')
            .attr("stroke-opacity", 0.4)
            .attr("stroke-width", (d: any) => Math.abs(d.strength) + 2)
            .style("filter", "url(#glow)");

        const nodeGroup = g.append("g")
            .selectAll("g")
            .data(nodes)
            .join("g")
            .style("cursor", "pointer")
            .on("click", (event, d: any) => setSelectedAgent(d.id))
            .call(d3.drag<any, any>()
                .on("start", dragstarted)
                .on("drag", dragged)
                .on("end", dragended) as any);

        // Agent Outer Ring (Glow)
        nodeGroup.append("circle")
            .attr("r", 22)
            .attr("fill", "transparent")
            .attr("stroke", (d: any) => d.grupo_id ? `hsl(${parseInt(d.grupo_id.replace(/\D/g, '')) * 137.5 % 360}, 70%, 50%)` : '#00f2ff')
            .attr("stroke-width", 1)
            .attr("stroke-dasharray", "4,2")
            .style("filter", "url(#glow)");

        // Agent Body (Hexagon-ish)
        nodeGroup.append("circle")
            .attr("r", 18)
            .attr("fill", "#0a0c12")
            .attr("stroke", (d: any) => d.grupo_id ? `hsl(${parseInt(d.grupo_id.replace(/\D/g, '')) * 137.5 % 360}, 70%, 50%)` : '#00f2ff')
            .attr("stroke-width", 2);

        // Agent Icon (Simplified Robot Face)
        nodeGroup.append("path")
            .attr("d", "M-8 -4 L8 -4 L8 4 L-8 4 Z M-4 -2 L-2 -2 M2 -2 L4 -2")
            .attr("stroke", "#fff")
            .attr("stroke-width", 1.5)
            .attr("fill", "none");

        const label = g.append("g")
            .selectAll("text")
            .data(nodes)
            .join("text")
            .text((d: any) => d.id)
            .attr("font-family", "'Orbitron', sans-serif")
            .attr("font-size", "10px")
            .attr("fill", "#00f2ff")
            .attr("text-anchor", "middle")
            .attr("dy", 35)
            .style("text-shadow", "0 0 5px rgba(0, 242, 255, 0.5)");

        simulation.on("tick", () => {
            link
                .attr("x1", (d: any) => d.source.x)
                .attr("y1", (d: any) => d.source.y)
                .attr("x2", (d: any) => d.target.x)
                .attr("y2", (d: any) => d.target.y);

            nodeGroup
                .attr("transform", (d: any) => `translate(${d.x},${d.y})`);

            label
                .attr("x", (d: any) => d.x)
                .attr("y", (d: any) => d.y);
        });

        function dragstarted(event: any) {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            event.subject.fx = event.subject.x;
            event.subject.fy = event.subject.y;
        }

        function dragged(event: any) {
            event.subject.fx = event.x;
            event.subject.fy = event.y;
        }

        function dragended(event: any) {
            if (!event.active) simulation.alphaTarget(0);
            event.subject.fx = null;
            event.subject.fy = null;
        }

        return () => { simulation.stop(); };
    }, [agents, relationships]);

    return (
        <div className="w-full h-full relative bg-[#05060a]">
            {/* Grid Background */}
            <div className="absolute inset-0 opacity-10 pointer-events-none"
                style={{ backgroundImage: 'radial-gradient(var(--accent-primary) 1px, transparent 1px)', backgroundSize: '40px 40px' }} />

            <svg ref={svgRef} className="w-full h-full relative z-10" />

            {/* Legend HUD */}
            <div className="absolute bottom-8 left-8 p-4 glass border-cyan-500/30 flex flex-col gap-3 text-[10px] font-cyber">
                <div className="text-cyan-500/50 mb-1 border-b border-cyan-500/20 pb-1">RELATION_PROTOCOL</div>
                <div className="flex items-center gap-3">
                    <div className="w-2 h-2 rounded-full bg-[#00ff9d] shadow-[0_0_5px_#00ff9d]" />
                    <span className="text-emerald-400">AFFINITY_POSITIVE</span>
                </div>
                <div className="flex items-center gap-3">
                    <div className="w-2 h-2 rounded-full bg-[#ff3e3e] shadow-[0_0_5px_#ff3e3e]" />
                    <span className="text-rose-500">AFFINITY_NEGATIVE</span>
                </div>
                <div className="flex items-center gap-3">
                    <div className="w-2 h-2 rounded-full bg-[#00f2ff] shadow-[0_0_5px_#00f2ff]" />
                    <span className="text-cyan-400">NEUTRAL_CONTACT</span>
                </div>
            </div>
        </div>
    );
}
