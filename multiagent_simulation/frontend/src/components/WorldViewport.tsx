"use client";

import { useEffect, useRef, useState, useMemo } from "react";
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

    // TILE DIMENSIONS PARA ISOMETRIA
    const tileW = 48;
    const tileH = 24;

    const iso = (col: number, row: number) => ({
        x: (col - row) * (tileW / 2),
        y: (col + row) * (tileH / 2)
    });

    const baseDepth = 8;

    // Dimensiones del mapa (puede ser rectangular)
    const mapWidth = mapa?.length || 0;
    const mapHeight = mapa?.[0]?.length || 0;

    // Partículas
    const particleData = useMemo(() => {
        if (!mapa || mapa.length === 0) return [];
        return Array.from({ length: 30 }).map((_, i) => ({
            id: i,
            x: (Math.random() - 0.5) * mapWidth * tileW * 2,
            y: (Math.random() - 0.2) * mapHeight * tileH * 2,
            r: 1 + Math.random() * 2,
            delay: Math.random() * 15
        }));
    }, [mapa?.length, mapa?.[0]?.length]);

    // 1. TERRENO E ISOMETRÍA
    useEffect(() => {
        if (!svgRef.current || !mapa || mapa.length === 0) return;

        const svg = d3.select(svgRef.current);
        let g = svg.select<SVGGElement>("g.main-group");
        if (g.empty()) g = svg.append("g").attr("class", "main-group");

        let terrainGroup = g.select<SVGGElement>(".terrain-layer");
        if (terrainGroup.empty()) terrainGroup = g.append("g").attr("class", "terrain-layer");
        
        // --- COLORES HABBO STYLE ---
        const terrainColors: Record<string, { top: string, left: string, right: string }> = {
            grass: { top: "#7CB342", left: "#558B2F", right: "#689F38" },
            forest: { top: "#558B2F", left: "#33691E", right: "#417A27" },
            mountain: { top: "#B0BEC5", left: "#546E7A", right: "#37474F" },
            montaña: { top: "#B0BEC5", left: "#546E7A", right: "#37474F" },
            water: { top: "#29B6F6", left: "#0288D1", right: "#039BE5" },
            desert: { top: "#FFE082", left: "#FFB300", right: "#FFCA28" },
            archaeological_site: { top: "#BCAAA4", left: "#795548", right: "#8D6E63" },
            path: { top: "#E0E0E0", left: "#9E9E9E", right: "#BDBDBD" }
        };

        const buildingIcons: Record<string, string> = {
            "Hospital": "🏥", "Granja": "🌾", "Centro de Recarga": "🔋", 
            "Centro de Descanso": "🛌", "Centro Comunitario": "💠", 
            "Comisaría": "🚓", "Universidad": "🏫", "Comedor": "☕", 
            "Centro de Ocio": "🕹️", "Torre de Vigilancia": "🗼"
        };

        // --- DEFINICIONES SVG ---
        let defs = svg.select<SVGDefsElement>("defs");
        if (defs.empty()) defs = svg.append("defs");
        
        if (defs.select("#drop-shadow-soft").empty()) {
            const filter = defs.append("filter").attr("id", "drop-shadow-soft").attr("x", "-20%").attr("y", "-20%").attr("width", "140%").attr("height", "140%");
            filter.append("feDropShadow").attr("dx", "0").attr("dy", "3").attr("stdDeviation", "2").attr("flood-color", "#000").attr("flood-opacity", "0.3");
        }

        if (defs.select("#pattern-grass-real").empty()) {
            const p = defs.append("pattern").attr("id", "pattern-grass-real").attr("patternUnits", "userSpaceOnUse").attr("width", 32).attr("height", 32);
            p.append("rect").attr("width", 32).attr("height", 32).attr("fill", terrainColors.grass.top);
            Array.from({ length: 15 }).forEach(() => {
                p.append("path")
                    .attr("d", `M ${Math.random()*32} ${Math.random()*32} l ${(Math.random()-0.5)*4} -${2 + Math.random()*4}`)
                    .attr("stroke", Math.random() > 0.5 ? terrainColors.grass.left : "#8BC34A")
                    .attr("stroke-width", 1.5)
                    .attr("stroke-linecap", "round")
                    .attr("fill", "none")
                    .attr("opacity", 0.7 + Math.random() * 0.3);
            });
        }

        if (defs.select("#pattern-desert-real").empty()) {
            const p = defs.append("pattern").attr("id", "pattern-desert-real").attr("patternUnits", "userSpaceOnUse").attr("width", 40).attr("height", 40);
            p.append("rect").attr("width", 40).attr("height", 40).attr("fill", terrainColors.desert.top);
            Array.from({ length: 8 }).forEach(() => {
                p.append("path")
                    .attr("d", `M ${Math.random()*40} ${Math.random()*40} q 4 -2 8 0 t 8 0`)
                    .attr("stroke", "#FFD54F").attr("stroke-width", 1.5).attr("fill", "none").attr("opacity", 0.6);
            });
            Array.from({ length: 20 }).forEach(() => {
                p.append("circle").attr("cx", Math.random() * 40).attr("cy", Math.random() * 40).attr("r", 0.6).attr("fill", terrainColors.desert.left).attr("opacity", 0.5);
            });
        }

        const flatMap = mapa.flatMap((row, x) => row.map((tile, y) => ({ ...tile, x, y })));
        flatMap.sort((a, b) => (a.x + a.y) - (b.x + b.y));

        const { civilizaciones, gruposDinamicos } = useGameStore.getState();

        const topFace = `M 0 ${-tileH/2} L ${tileW/2} 0 L 0 ${tileH/2} L ${-tileW/2} 0 Z`;
        const getLeftFace = (depth: number) => `M ${-tileW/2} 0 L 0 ${tileH/2} L 0 ${tileH/2 + depth} L ${-tileW/2} ${depth} Z`;
        const getRightFace = (depth: number) => `M 0 ${tileH/2} L ${tileW/2} 0 L ${tileW/2} ${depth} L 0 ${tileH/2 + depth} Z`;

        terrainGroup.selectAll(".cell-group")
            .data(flatMap, (d: any) => `${d.x}-${d.y}`)
            .join(
                enter => {
                    const g = enter.append("g").attr("class", "cell-group");
                    g.append("path").attr("class", "voxel-left").attr("d", getLeftFace(baseDepth));
                    g.append("path").attr("class", "voxel-right").attr("d", getRightFace(baseDepth));
                    g.append("path").attr("class", "voxel-top").attr("d", topFace);
                    g.append("path").attr("class", "mountain-left").attr("d", getLeftFace(baseDepth + 8)).attr("opacity", 0);
                    g.append("path").attr("class", "mountain-right").attr("d", getRightFace(baseDepth + 8)).attr("opacity", 0);
                    g.append("path").attr("class", "mountain-top").attr("d", topFace).attr("opacity", 0);
                    return g;
                }
            )
            .each(function(this: any, d: any) {
                const cell = d3.select(this);
                const pos = iso(d.x, d.y);
                const terrainStr = (d.terrain || "grass").toLowerCase();
                const isMountain = terrainStr.includes("moun") || terrainStr.includes("mont");
                const hasBuildings = d.buildings && d.buildings.length > 0;
                let c = terrainColors[isMountain ? 'mountain' : terrainStr] || terrainColors.grass;

                cell.attr("transform", `translate(${pos.x}, ${pos.y})`);

                // Reset de visibilidad para re-renderizado
                cell.selectAll(".mountain-left, .mountain-right, .mountain-top").attr("transform", null).attr("opacity", 0);
                cell.selectAll(".voxel-left, .voxel-right, .voxel-top").attr("opacity", 1);
                cell.selectAll(".terrain-decor, .cell-overlay, .building-unit, .resource-icon, .tree-unit").remove();

            if (!isMountain) {
                let topFill = c.top;
                if (!hasBuildings) {
                    if (terrainStr === 'grass') topFill = "url(#pattern-grass-real)";
                    if (terrainStr === 'desert') topFill = "url(#pattern-desert-real)";
                }
                cell.select(".voxel-top").attr("fill", topFill).attr("stroke", "rgba(0,0,0,0.1)").attr("stroke-width", 0.5);
                cell.select(".voxel-left").attr("fill", c.left).attr("stroke", "rgba(0,0,0,0.1)").attr("stroke-width", 0.5);
                cell.select(".voxel-right").attr("fill", c.right).attr("stroke", "rgba(0,0,0,0.1)").attr("stroke-width", 0.5);
            } else {
                cell.selectAll(".voxel-left, .voxel-right, .voxel-top").attr("opacity", 0);
                
                // === MONTAÑAS CON RELIEVE REALISTA Y ESTILIZADO ===
                const noise = (d.x * 127 + d.y * 131) % 100;
                const hf = 0.3 + (Math.abs(Math.sin(d.x * 0.7) * Math.cos(d.y * 0.7)) * 0.7);
                
                // Elevamos los picos desde la base del terreno (0 para que no floten)
                const mountainElevation = 0; 
                
                const peakGroup = cell.append("g").attr("class", "terrain-decor").attr("transform", `translate(0, -${mountainElevation})`);
                
                // Función para dibujar picos más realistas y menos "agujas"
                const drawRuggedMountain = (ox: number, oy: number, ph: number, pw: number) => {
                    const pg = peakGroup.append("g").attr("transform", `translate(${ox}, ${oy})`);
                    
                    // Cuerpo principal (polígono más complejo para realismo)
                    // Cara Izquierda (con un quiebre para rugosidad)
                    pg.append("path")
                        .attr("d", `M 0 ${-ph} L ${-pw*0.7} ${-ph*0.4} L ${-pw} 0 L 0 ${tileH/2} L 0 ${-ph*0.3} Z`)
                        .attr("fill", "#546E7A").attr("stroke", "rgba(0,0,0,0.2)");
                    // Cara Derecha (con un quiebre para rugosidad)
                    pg.append("path")
                        .attr("d", `M 0 ${-ph} L ${pw*0.8} ${-ph*0.3} L ${pw} 0 L 0 ${tileH/2} L 0 ${-ph*0.3} Z`)
                        .attr("fill", "#37474F").attr("stroke", "rgba(0,0,0,0.2)");
                    
                    // Nieve en la cumbre (más orgánica)
                    if (ph > 18) {
                        const snowH = ph * 0.35;
                        const snowW = pw * 0.5;
                        pg.append("path")
                            .attr("d", `M 0 ${-ph} L ${-snowW*0.6} ${-ph+snowH/2} L 0 ${-ph+snowH*0.8} L ${snowW*0.6} ${-ph+snowH/2} Z`)
                            .attr("fill", "#CFD8DC").attr("opacity", 0.9);
                    }
                };

                // Altura de pico más controlada (no tan alta)
                const peakHeight = 15 + (hf * 35);
                drawRuggedMountain(0, 0, peakHeight, 22);
                
                // Pequeños picos secundarios para naturalidad
                if (hf > 0.5) {
                    drawRuggedMountain(-12, 4, peakHeight * 0.5, 12);
                    drawRuggedMountain(14, -6, peakHeight * 0.3, 10);
                }
            }

            // === DECORACIONES POR BIOMA ADICIONALES ===
            if (terrainStr === 'water') {
                const w = cell.append("g").attr("class", "terrain-decor");
                w.append("path").attr("d", `M ${-tileW/4} ${-tileH/8} L ${tileW/4} ${tileH/8}`).attr("stroke", "rgba(255,255,255,0.4)").attr("stroke-width", 1.5);
            } else if (terrainStr === 'desert') {
                const noise = (d.x * 23 + d.y * 19) % 100;
                if (noise < 10) {
                   const c = cell.append("g").attr("class", "terrain-decor").attr("transform", "translate(0, -4)");
                   c.append("path").attr("d", "M -2 0 L -2 -8 M 2 -2 L 2 -10 M -5 -5 L 5 -5").attr("stroke", "#2E7D32").attr("stroke-width", 2);
                }
            } else if (terrainStr === 'grass' && !hasBuildings) {
                const noise = (d.x * 17 + d.y * 31) % 100;
                if (noise < 8) {
                    const b = cell.append("g").attr("class", "terrain-decor").attr("transform", `translate(0, -5)`);
                    b.append("ellipse").attr("cx", 0).attr("cy", 0).attr("rx", 10).attr("ry", 5).attr("fill", "rgba(0,0,0,0.3)");
                    const bx = 6, by = 6, bz = 8;
                    b.append("path").attr("d", `M ${-bx} ${-bz} L 0 ${-bz+by} L ${bx} ${-bz} L 0 ${-bz-by} Z`).attr("fill", "#81C784");
                    b.append("path").attr("d", `M ${-bx} ${-bz} L 0 ${-bz+by} L 0 ${by} L ${-bx} 0 Z`).attr("fill", "#4CAF50");
                    b.append("path").attr("d", `M 0 ${-bz+by} L ${bx} ${-bz} L ${bx} 0 L 0 ${by} Z`).attr("fill", "#388E3C");
                }
            }

            if (d.owner) {
                const ownerInfo = civilizaciones[d.owner] || gruposDinamicos[d.owner];
                const ownerColor = ownerInfo?.color || "#ffffff";
                cell.append("path").attr("class", "cell-overlay").attr("d", topFace).attr("fill", ownerColor).attr("opacity", 0.3).attr("stroke", ownerColor).attr("stroke-width", 2);
            }

            if (hasBuildings) {
                d.buildings.forEach((b: any) => {
                    const ownerColor = civilizaciones[b.grupo_id]?.color || gruposDinamicos[b.grupo_id]?.color || "#7c4dff";
                    const bg = cell.append("g").attr("class", "building-unit").attr("transform", "translate(0, -4)");
                    let blkW = 14, blkH = 7, blkZ = 16; 
                    const themeColors: any = { "Hospital": { t: "#EF9A9A", l: "#E53935", r: "#C62828" }, "Universidad": { t: "#9FA8DA", l: "#3949AB", r: "#283593" }, "Granja": { t: "#FFE082", l: "#FFB300", r: "#FF8F00" }, "Centro Comunitario": { t: "#80DEEA", l: "#00ACC1", r: "#00838F" }, "Torre de Vigilancia": { t: "#B0BEC5", l: "#546E7A", r: "#37474F", tall: true }, "default": { t: "#FFCC80", l: "#F57C00", r: "#E65100" } };
                    const tc = themeColors[b.tipo] || themeColors["default"];
                    if (tc.tall) { blkW = 8; blkH = 4; blkZ = 28; }
                    bg.style("filter", "url(#drop-shadow-soft)");
                    bg.append("path").attr("d", `M ${-blkW} ${-blkZ} L 0 ${-blkZ+blkH} L ${blkW} ${-blkZ} L 0 ${-blkZ-blkH} Z`).attr("fill", tc.t).attr("stroke", "rgba(0,0,0,0.2)");
                    bg.append("path").attr("d", `M ${-blkW} ${-blkZ} L 0 ${-blkZ+blkH} L 0 ${blkH} L ${-blkW} 0 Z`).attr("fill", tc.l);
                    bg.append("path").attr("d", `M 0 ${-blkZ+blkH} L ${blkW} ${-blkZ} L ${blkW} 0 L 0 ${blkH} Z`).attr("fill", tc.r);
                    const sign = bg.append("g").attr("transform", `translate(0, ${-blkZ - 12})`);
                    sign.append("circle").attr("r", 8).attr("fill", "#FFF").attr("stroke", ownerColor).attr("stroke-width", 2);
                    sign.append("text").attr("y", 3).attr("text-anchor", "middle").attr("font-size", "10px").text(buildingIcons[b.tipo] || "🏢");
                });
            } else if (!hasBuildings && terrainStr === 'forest') {
                const treeGroup = cell.append("g").attr("class", "tree-unit").style("filter", "url(#drop-shadow-soft)").attr("transform", `translate(0, -6)`);
                const drwTr = (ox: number, oy: number, scale: number) => {
                    const tg = treeGroup.append("g").attr("transform", `translate(${ox}, ${oy}) scale(${scale})`);
                    const tw=3, th=1.5, tz=8;
                    tg.append("path").attr("d", `M ${-tw} ${-tz} L 0 ${-tz+th} L ${tw} ${-tz} L 0 ${-tz-th} Z`).attr("fill", "#A1887F");
                    tg.append("path").attr("d", `M ${-tw} ${-tz} L 0 ${-tz+th} L 0 ${th} L ${-tw} 0 Z`).attr("fill", "#795548");
                    tg.append("path").attr("d", `M 0 ${-tz+th} L ${tw} ${-tz} L ${tw} 0 L 0 ${th} Z`).attr("fill", "#5D4037");
                    const lw=10, lh=5, lz=12; const lzShift = -tz - 2;
                    tg.append("path").attr("d", `M ${-lw} ${lzShift-lz} L 0 ${lzShift-lz+lh} L ${lw} ${lzShift-lz} L 0 ${lzShift-lz-lh} Z`).attr("fill", "#81C784");
                    tg.append("path").attr("d", `M ${-lw} ${lzShift-lz} L 0 ${lzShift-lz+lh} L 0 ${lzShift+lh} L ${-lw} ${lzShift} Z`).attr("fill", "#4CAF50");
                    tg.append("path").attr("d", `M 0 ${lzShift-lz+lh} L ${lw} ${lzShift-lz} L ${lw} ${lzShift} L 0 ${lzShift+lh} Z`).attr("fill", "#388E3C");
                };
                const hash = (d.x * 23 + d.y * 37) % 3;
                if (hash === 0) drwTr(0, 0, 1.2);
                else if (hash === 1) { drwTr(-8, -4, 0.9); drwTr(8, 4, 1.0); }
                else { drwTr(4, -8, 0.8); drwTr(-4, 8, 0.9); }
            } else if (d.resource) {
                const resInfo: Record<string, string> = { 'food': '🍎', 'wood': '🪵', 'stone': '🗿', 'iron': '⚙️', 'medicine': '💊' };
                const type = d.resource.type; const r = resInfo[type] || '🎁';
                const bag = cell.append("g").attr("class", "resource-icon").attr("transform", `translate(0, -10)`);
                bag.append("text").attr("y", 0).attr("text-anchor", "middle").attr("font-size", "12px").style("filter", "url(#drop-shadow-soft)").text(r);
            }
        });
    }, [mapa]);

    // 2. AGENTES Y OVERLAYS
    useEffect(() => {
        if (!svgRef.current || !containerRef.current || !mapa || mapa.length === 0) return;
        const width = containerRef.current.clientWidth;
        const height = containerRef.current.clientHeight;
        const svg = d3.select(svgRef.current);
        let g = svg.select<SVGGElement>("g.main-group");
        if (g.empty()) g = svg.append("g").attr("class", "main-group");
        let linkGroup = g.select<SVGGElement>(".links-layer");
        if (linkGroup.empty()) linkGroup = g.append("g").attr("class", "links-layer");
        let agentGroup = g.select<SVGGElement>(".agents-layer");
        if (agentGroup.empty()) agentGroup = g.append("g").attr("class", "agents-layer");
        let bubbleGroup = g.select<SVGGElement>(".bubbles-layer");
        if (bubbleGroup.empty()) bubbleGroup = g.append("g").attr("class", "bubbles-layer");
        let weatherGroup = g.select<SVGGElement>(".weather-layer");
        if (weatherGroup.empty()) weatherGroup = g.append("g").attr("class", "weather-layer");
        let particlesGroup = g.select<SVGGElement>(".particles-layer");
        if (particlesGroup.empty()) particlesGroup = g.append("g").attr("class", "particles-layer");

        particlesGroup.selectAll("circle").data(particleData).join("circle").attr("cx", d => d.x).attr("cy", d => d.y).attr("r", d => d.r).attr("fill", "#7c4dff").attr("opacity", 0).attr("class", "animate-particle").style("animation-delay", d => `${d.delay}s`);

        const zoom = d3.zoom<SVGSVGElement, unknown>().scaleExtent([0.1, 4]).on("zoom", (event) => g.attr("transform", event.transform));
        
        // RECALCULAR ZOOM SI LAS DIMENSIONES CAMBIAN O NO SE HA INICIALIZADO
        const mapKey = `${mapWidth}x${mapHeight}`;
        const lastMapKey = (svg.node() as any)?.__lastMapKey;

        if (!initializedRef.current || lastMapKey !== mapKey) {
            svg.call(zoom);
            // Calcular centro del mapa para zoom inicial - soporta mapas rectangulares
            const mapPixelWidth = (mapWidth + mapHeight) * (tileW / 2);
            const mapPixelHeight = (mapWidth + mapHeight) * (tileH / 2);
            
            const centerX = width / 2;
            const centerY = height / 4; // Un poco más arriba para perspectiva isométrica
            
            // Escala dinámica según el tamaño del mapa para que quepa siempre
            const scale = Math.min(1.0, (width * 0.8) / mapPixelWidth, (height * 0.8) / mapPixelHeight);
            
            svg.transition().duration(800).call(
                zoom.transform, 
                d3.zoomIdentity.translate(centerX, centerY).scale(scale)
            );
            
            initializedRef.current = true;
            (svg.node() as any).__lastMapKey = mapKey;
        }

        if (showLinks && relationships) {
            const agentCoords = new Map();
            agents.forEach(a => agentCoords.set(a.id, iso(a.x, a.y)));
            const relationshipData = relationships.map(rel => ({ ...rel, coords: { source: agentCoords.get(rel.source), target: agentCoords.get(rel.target) } })).filter(d => d.coords.source && d.coords.target);
            linkGroup.selectAll("line").data(relationshipData, (d: any) => `${d.source}-${d.target}-${d.type}`).join("line").attr("x1", d => d.coords.source.x).attr("y1", d => d.coords.source.y - 10).attr("x2", d => d.coords.target.x).attr("y2", d => d.coords.target.y - 10).attr("stroke", d => d.type === 'amigo' ? "#00e676" : d.type === 'enemigo' ? "#ff1744" : d.type === 'alianza' ? "#ffd600" : "#ffffff").attr("stroke-width", d => d.type === 'amigo' ? 1.5 : d.type === 'enemigo' ? 2 : d.type === 'alianza' ? 2.5 : 0.5).attr("opacity", d => d.type === 'amigo' ? 0.6 : d.type === 'enemigo' ? 0.8 : d.type === 'alianza' ? 0.8 : 0.2);
        } else linkGroup.selectAll("line").remove();

        const sortedAgents = [...agents].sort((a, b) => (a.x + a.y) - (b.x + b.y));
        const agentSelection = agentGroup.selectAll<SVGGElement, any>(".agent").data(sortedAgents, (d) => d.id);
        const enter = agentSelection.enter().append("g").attr("class", "agent").attr("cursor", "pointer").on("click", (event, d) => { event.stopPropagation(); selectAgent(d.id); });
        enter.append("ellipse").attr("class", "agent-shadow").attr("cx", 0).attr("cy", 0).attr("rx", 10).attr("ry", 5).attr("fill", "rgba(0,0,0,0.3)");
        enter.append("path").attr("class", "selection-ring").attr("d", "M 0 -10 L 15 0 L 0 10 L -15 0 Z").attr("fill", "none").attr("stroke", "#fff").attr("stroke-width", 2).attr("opacity", 0);
        const bodyGroup = enter.append("g").attr("class", "agent-body animate-pixel-idle").style("filter", "url(#drop-shadow-soft)");
        bodyGroup.append("rect").attr("x", -4).attr("y", -8).attr("width", 3).attr("height", 8).attr("fill", "#1E88E5");
        bodyGroup.append("rect").attr("x", 1).attr("y", -8).attr("width", 3).attr("height", 8).attr("fill", "#1E88E5");
        bodyGroup.append("rect").attr("x", -5).attr("y", -18).attr("width", 10).attr("height", 10).attr("fill", (d) => d.color || "#EF5350");
        bodyGroup.append("rect").attr("x", -7).attr("y", -18).attr("width", 2).attr("height", 8).attr("fill", "#FFCCBC");
        bodyGroup.append("rect").attr("x", 5).attr("y", -18).attr("width", 2).attr("height", 8).attr("fill", "#FFCCBC");
        bodyGroup.append("rect").attr("x", -6).attr("y", -28).attr("width", 12).attr("height", 10).attr("fill", "#FFCCBC");
        bodyGroup.append("rect").attr("x", -3).attr("y", -24).attr("width", 2).attr("height", 2).attr("fill", "#000");
        bodyGroup.append("rect").attr("x", 1).attr("y", -24).attr("width", 2).attr("height", 2).attr("fill", "#000");
        bodyGroup.append("path").attr("d", "M -7 -28 L 7 -28 L 7 -32 L -7 -32 Z").attr("fill", "#4E342E");
        const nameGroup = enter.append("g").attr("transform", "translate(0, 10)");
        nameGroup.append("rect").attr("x", -20).attr("y", 0).attr("width", 40).attr("height", 12).attr("rx", 2).attr("fill", "rgba(0,0,0,0.7)");
        nameGroup.append("text").attr("y", 9).attr("text-anchor", "middle").attr("font-size", "9px").attr("fill", "#ffffff").attr("font-weight", "500").attr("font-family", "monospace").text((d) => { const name = d.alma?.nombre_propio || d.id || "???"; return name.split(' ')[0].substring(0, 6); });

        const merged = enter.merge(agentSelection);
        merged.each(function(d) {
            const currentPos = iso(d.x, d.y);
            
            // --- PERSONALIDAD DETERMINISTA SEGÚN AGENTE ID ---
            const agentSeed = d.id.split('').reduce((acc: number, char: string) => acc + char.charCodeAt(0), 0);
            const getSeededValue = (offset: number) => (Math.sin(agentSeed * (123.45 + offset)) * 10000) % 1;
            
            // Variación de velocidad y ritmo (algunos son lentos, otros rápidos)
            const duration = 650 + getSeededValue(10) * 550;
            const startDelay = getSeededValue(20) * 450; 
            
            // Easing variable (snappy vs suave)
            const easings = [d3.easeCubicInOut, d3.easeQuadInOut, d3.easeSinInOut, d3.easeExpInOut];
            const easingIndex = Math.abs(Math.floor(getSeededValue(30) * easings.length)) % easings.length;
            const chosenEasing = easings[easingIndex] ?? d3.easeCubicInOut;
            
            // Micro-desajuste (jitter) para que no estén todos centrados perfectamente
            const jitterX = (getSeededValue(40) - 0.5) * 12;
            const jitterY = (getSeededValue(50) - 0.5) * 6;
            
            // Altura de salto al caminar (bobbing)
            const jumpHeight = -4 - (getSeededValue(60) * 8);

            // Variar la animación IDLE (breathing) para que no sea síncrona
            const idleDuration = 0.6 + getSeededValue(70) * 0.4;
            const idleDelay = getSeededValue(80) * 2;
            d3.select(this).select(".agent-body")
                .style("animation-duration", `${idleDuration}s`)
                .style("animation-delay", `${idleDelay}s`);

            // Movimiento principal con ligero "swerve" (curva sutil)
            const node = d3.select(this);
            const midX = currentPos.x + jitterX + (getSeededValue(90) - 0.5) * 8;
            const midY = currentPos.y + jitterY + (getSeededValue(100) - 0.5) * 4;

            node.transition()
                .delay(startDelay)
                .duration(duration * 0.4)
                .ease(d3.easeQuadOut)
                .attr("transform", `translate(${midX}, ${midY})`)
                .transition()
                .duration(duration * 0.6)
                .ease(chosenEasing)
                .attr("transform", `translate(${currentPos.x + jitterX}, ${currentPos.y + jitterY})`);
                
            // Movimiento vertical asíncrono y orgánico (salto al caminar)
            d3.select(this).select(".agent-body")
                .transition()
                .delay(startDelay)
                .duration(duration / 2.2)
                .ease(d3.easeQuadOut)
                .attr("transform", `translate(0, ${jumpHeight})`)
                .transition()
                .duration(duration / 2.2)
                .ease(d3.easeBounceOut)
                .attr("transform", "translate(0, 0)");
        });
        merged.select(".selection-ring").transition().duration(200).attr("opacity", (d) => d.id === selectedAgentId ? 1 : 0);
        agentSelection.exit().remove();

        if (speechBubbles && !hideBubbles) {
            const bubbleData = Object.entries(speechBubbles).map(([id, b]) => ({ id, ...b })).filter(b => agents.some(a => a.id === b.id));
            bubbleGroup.selectAll(".bubble-g").data(bubbleData, (d: any) => d.id + d.timestamp).join(
                enter => {
                    const bg = enter.append("g").attr("class", "bubble-g").attr("opacity", 0);
                    bg.append("rect").attr("class", "bubble-bg").attr("rx", 4).attr("fill", "white").attr("stroke", "#424242").attr("stroke-width", 2);
                    bg.append("path").attr("d", "M -5 0 L 5 0 L 0 5 Z").attr("fill", "white").attr("stroke", "#424242").attr("stroke-width", 2);
                    bg.append("path").attr("d", "M -4 0 L 4 0 L 0 4 Z").attr("fill", "white");
                    bg.append("text").attr("class", "bubble-text").attr("text-anchor", "middle").attr("font-size", "6.5px").attr("fill", "#000").attr("font-family", "monospace").attr("font-weight", "bold");
                    return bg;
                }, update => update, exit => exit.transition().duration(200).attr("opacity", 0).remove()
            ).each(function(d: any) {
                const agent = agents.find(a => a.id === d.id); if (!agent) return;
                const pos = iso(agent.x, agent.y);
                const g = d3.select(this); const text = d.text.toUpperCase(); const words = text.split(/\s+/); const lines: string[] = []; let cur = "";
                words.forEach((w: string) => { if ((cur + w).length > 25) { lines.push(cur.trim()); cur = w + " "; } else cur += w + " "; }); lines.push(cur.trim());
                const lh = 8; const bp = 8; const bw = Math.min(180, (Math.max(...lines.map(l => l.length)) * 4) + 16); const bh = (lines.length * lh) + bp;
                let yOff = -45;
                const tile = mapa[agent.x]?.[agent.y];
                if (tile?.terrain?.toLowerCase() === 'mountain' || tile?.terrain?.toLowerCase() === 'montaña') {
                    yOff -= 0;
                }
                g.select("rect").attr("x", -bw / 2).attr("y", -bh).attr("width", bw).attr("height", bh);
                const t = g.select("text").attr("y", -bh + 12);
                t.selectAll("tspan").data(lines).join("tspan").attr("x", 0).attr("dy", (l, i) => i === 0 ? 0 : lh).text(d => d);
                g.transition().duration(200).attr("opacity", 1).attr("transform", `translate(${pos.x}, ${pos.y + yOff})`);
            });
        } else bubbleGroup.selectAll(".bubble-g").remove();

        weatherGroup.selectAll("rect").data((weather === 'rainy' || weather === 'storm') ? [1] : []).join("rect").attr("x", -mapa.length*tileW).attr("y", -mapa[0].length*tileH).attr("width", mapa.length * tileW * 2).attr("height", mapa[0].length * tileH * 2).attr("fill", "#1E88E5").attr("opacity", 0.08);

    }, [agents, selectedAgentId, weather, selectAgent, relationships, speechBubbles, showLinks, hideBubbles]);

    return (
        <div ref={containerRef} className="w-full h-full relative bg-[#1c2128] overflow-hidden" style={{ imageRendering: "pixelated" }}>
            <svg ref={svgRef} className="w-full h-full block" />
            <button onClick={() => setShowLinks(!showLinks)} className="absolute top-20 right-6 glass-panel p-2.5 rounded-xl border border-white/10 hover:border-purple-500/50 transition-all z-50">
                {showLinks ? <Link className="w-4 h-4 text-emerald-400" /> : <Link2Off className="w-4 h-4 text-gray-400" />}
            </button>
            <div className="absolute top-20 left-6 flex flex-col gap-3">
                {/* Leyenda de Biomas */}
                <div className="p-3 rounded-xl border-2 border-[#424242] text-[9px] space-y-2 pointer-events-none w-36 bg-[#212121]/90 shadow-[2px_2px_0px_#000]">
                    <div className="text-[#E0E0E0] font-bold uppercase mb-1 border-b-2 border-[#424242] pb-1.5 font-monospace">Biomas</div>
                    <div className="grid grid-cols-1 gap-y-1.5 px-1 font-monospace text-[#BDBDBD]">
                        <LegendBox top="#7CB342" left="#558B2F" right="#689F38" label="Hierba" />
                        <LegendBox top="#B0BEC5" left="#546E7A" right="#37474F" label="Montaña" />
                        <LegendBox top="#29B6F6" left="#0288D1" right="#039BE5" label="Lago" />
                        <LegendBox top="#558B2F" left="#33691E" right="#417A27" label="Bosque" />
                        <LegendBox top="#FFE082" left="#FFB300" right="#FFCA28" label="Desierto" />
                    </div>
                </div>
                {/* Dimensiones del Mundo */}
                {mapa && mapa.length > 0 && (
                    <div className="p-3 rounded-xl border-2 border-[#424242] text-[9px] pointer-events-none bg-[#212121]/90 shadow-[2px_2px_0px_#000]">
                        <div className="text-[#E0E0E0] font-bold uppercase mb-2 border-b-2 border-[#424242] pb-1 font-monospace">Dimensiones</div>
                        <div className="font-monospace text-[#BDBDBD] flex items-center gap-2">
                            <span className="text-yellow-500 font-bold">{mapWidth}</span>
                            <span className="text-gray-600">×</span>
                            <span className="text-emerald-400 font-bold">{mapHeight}</span>
                        </div>
                        <div className="text-[7px] text-gray-500 mt-1 font-monospace">
                            {mapWidth * mapHeight} casillas totales
                        </div>
                    </div>
                )}
            </div>
            {weather === 'rainy' && <div className="absolute inset-0 pointer-events-none bg-[url('/rain.png')] opacity-15 animate-rain"></div>}
        </div>
    );
}

function LegendBox({ top, left, right, label }: { top: string, left: string, right: string, label: string }) {
    return (
        <div className="flex items-center gap-2">
            <svg width="12" height="12" viewBox="0 -6 12 12">
                <path d="M 0 -3 L 6 -6 L 12 -3 L 6 0 Z" fill={top} />
                <path d="M 0 -3 L 6 0 L 6 6 L 0 3 Z" fill={left} />
                <path d="M 6 0 L 12 -3 L 12 3 L 6 6 Z" fill={right} />
            </svg>
            <span>{label}</span>
        </div>
    );
}
