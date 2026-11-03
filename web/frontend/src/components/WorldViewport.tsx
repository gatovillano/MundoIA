"use client";

import { useEffect, useRef, useState, useMemo } from "react";
import * as d3 from "d3";
import useGameStore from "@/store/useGameStore";
import { CloudRain, Sun, Link, Link2Off, Minimize2, Maximize2, ChevronDown, ChevronUp, Map as MapIcon } from "lucide-react";
import { replaceIdsWithNames } from "@/utils/nameUtils";

export default function WorldViewport({ hideBubbles = false }: { hideBubbles?: boolean }) {
    const svgRef = useRef<SVGSVGElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);
    const { agents, mapa, relationships, speechBubbles, selectAgent, selectedAgentId, weather } = useGameStore();
    const [showLinks, setShowLinks] = useState(true);
    const [showGrid, setShowGrid] = useState(true);
    const [isBoardMinimized, setIsBoardMinimized] = useState(false);
    const [isLegendCollapsed, setIsLegendCollapsed] = useState(false);
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
        
        // --- COLORES MODERNOS Y PALETA REFINADA ---
        const terrainColors: Record<string, { top: string, left: string, right: string }> = {
            grass: { top: "#689F38", left: "#33691E", right: "#558B2F" },
            forest: { top: "#2E7D32", left: "#1B5E20", right: "#2E7D32" },
            mountain: { top: "#8D6E63", left: "#4E342E", right: "#3E2723" }, // Tonos café más profundos
            montaña: { top: "#8D6E63", left: "#4E342E", right: "#3E2723" },
            water: { top: "#0288D1", left: "#01579B", right: "#0277BD" },
            desert: { top: "#FFD54F", left: "#F57F17", right: "#FFB300" },
            archaeological_site: { top: "#A1887F", left: "#5D4037", right: "#795548" },
            path: { top: "#BDBDBD", left: "#616161", right: "#9E9E9E" }
        };

        const buildingIcons: Record<string, string> = {
            "Hospital": "🏥", "Granja": "🌾", "Centro de Recarga": "🔋", 
            "Centro de Descanso": "🛌", "Centro Comunitario": "💠", 
            "Comisaría": "🚓", "Universidad": "🏫", "Comedor": "☕", 
            "Centro de Ocio": "🕹️", "Torre de Vigilancia": "🗼",
            "Mina": "⛏️", "Farmacia": "⚕️"
        };

        // --- DEFINICIONES SVG ---
        let defs = svg.select<SVGDefsElement>("defs");
        if (defs.empty()) defs = svg.append("defs");
        
        if (defs.select("#drop-shadow-soft").empty()) {
            const filter = defs.append("filter").attr("id", "drop-shadow-soft").attr("x", "-20%").attr("y", "-20%").attr("width", "140%").attr("height", "140%");
            filter.append("feDropShadow").attr("dx", "0").attr("dy", "3").attr("stdDeviation", "2.5").attr("flood-color", "#000").attr("flood-opacity", "0.4");
        }

        if (defs.select("#grass-texture").empty()) {
            const p = defs.append("pattern").attr("id", "grass-texture").attr("patternUnits", "userSpaceOnUse").attr("width", 40).attr("height", 40);
            p.append("rect").attr("width", 40).attr("height", 40).attr("fill", terrainColors.grass.top);
            // Textura de briznas más refinada y orgánica
            for (let i = 0; i < 12; i++) {
                const x = Math.random() * 40, y = Math.random() * 40;
                const h = 3 + Math.random() * 4;
                p.append("path")
                    .attr("d", `M ${x} ${y} Q ${x + 1} ${y - h} ${x + 2} ${y - h + 1}`)
                    .attr("stroke", i % 2 === 0 ? "#9CCC65" : "#7CB342")
                    .attr("stroke-width", 1)
                    .attr("fill", "none")
                    .attr("opacity", 0.6);
            }
        }

        if (defs.select("#sand-texture").empty()) {
            const p = defs.append("pattern").attr("id", "sand-texture").attr("patternUnits", "userSpaceOnUse").attr("width", 20).attr("height", 20);
            p.append("rect").attr("width", 20).attr("height", 20).attr("fill", terrainColors.desert.top);
            p.append("circle").attr("cx", 5).attr("cy", 5).attr("r", 0.5).attr("fill", "rgba(0,0,0,0.15)");
        }

        // Gradientes y texturas para edificios y ventanas
        if (defs.select("#roof-grad").empty()) {
            const rg = defs.append("linearGradient").attr("id", "roof-grad").attr("x1", "0").attr("y1", "0").attr("x2", "0").attr("y2", "1");
            rg.append("stop").attr("offset", "0%").attr("stop-color", "#6D4C41");
            rg.append("stop").attr("offset", "100%").attr("stop-color", "#4E342E");
        }

        if (defs.select("#window-grad").empty()) {
            const wg = defs.append("linearGradient").attr("id", "window-grad").attr("x1", "0").attr("y1", "0").attr("x2", "0").attr("y2", "1");
            wg.append("stop").attr("offset", "0%").attr("stop-color", "#eaf6ff").attr("stop-opacity", "0.95");
            wg.append("stop").attr("offset", "100%").attr("stop-color", "#b3e5fc").attr("stop-opacity", "0.6");
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
                // incluir decoraciones de edificio en la limpieza para evitar duplicados
                cell.selectAll(".terrain-decor, .cell-overlay, .building-unit, .resource-icon, .tree-unit, .building-decor, .farm-decor").remove();

            if (!isMountain) {
                let topFill = c.top;
                if (terrainStr === 'grass') topFill = "url(#grass-texture)";
                if (terrainStr === 'desert') topFill = "url(#sand-texture)";

                const gridStroke = showGrid ? "rgba(0,0,0,0.15)" : "none";
                const sideStroke = showGrid ? "rgba(0,0,0,0.2)" : "none";
                
                cell.select(".voxel-top").attr("fill", topFill).attr("stroke", gridStroke).attr("stroke-width", 0.8).style("filter", "url(#inner-glow-tile)");
                cell.select(".voxel-left").attr("fill", c.left).attr("stroke", sideStroke).attr("stroke-width", 0.5);
                cell.select(".voxel-right").attr("fill", c.right).attr("stroke", sideStroke).attr("stroke-width", 0.5);
            } else {
                cell.selectAll(".voxel-left, .voxel-right, .voxel-top").attr("opacity", 0);
                
                // === MONTAÑAS CON RELIEVE ROBUSTO Y TONOS CAFÉ ===
                const hf = 0.4 + (Math.abs(Math.sin(d.x * 0.5) * Math.cos(d.y * 0.5)) * 0.8);
                const mountainElevation = 0; 
                const peakGroup = cell.append("g").attr("class", "terrain-decor").attr("transform", `translate(0, -${mountainElevation})`);
                
                const drawRuggedMountain = (ox: number, oy: number, ph: number, pw: number, colorOffset: number) => {
                    const pg = peakGroup.append("g").attr("transform", `translate(${ox}, ${oy})`);
                    
                    // Colores variados dentro del rango café
                    const cTop = d3.color(terrainColors.mountain.top)?.darker(colorOffset).toString() || terrainColors.mountain.top;
                    const cLeft = d3.color(terrainColors.mountain.left)?.darker(colorOffset).toString() || terrainColors.mountain.left;
                    const cRight = d3.color(terrainColors.mountain.right)?.darker(colorOffset).toString() || terrainColors.mountain.right;

                    // Cara Izquierda con quiebres de roca
                    pg.append("path")
                        .attr("d", `M 0 ${-ph} L ${-pw*0.6} ${-ph*0.5} L ${-pw} 0 L 0 ${tileH/2} L 0 ${-ph*0.3} Z`)
                        .attr("fill", cLeft).attr("stroke", "rgba(0,0,0,0.3)").attr("stroke-width", 0.5);
                    
                    // Cara Derecha con quiebres
                    pg.append("path")
                        .attr("d", `M 0 ${-ph} L ${pw*0.7} ${-ph*0.4} L ${pw} 0 L 0 ${tileH/2} L 0 ${-ph*0.3} Z`)
                        .attr("fill", cRight).attr("stroke", "rgba(0,0,0,0.3)").attr("stroke-width", 0.5);
                    
                    // Detalle de cara superior/aristas
                    pg.append("path")
                        .attr("d", `M 0 ${-ph} L ${-pw*0.3} ${-ph*0.7} L 0 ${-ph*0.6} L ${pw*0.3} ${-ph*0.7} Z`)
                        .attr("fill", cTop).attr("opacity", 0.8);

                    // Nieve/Tierra clara en la cima
                    if (ph > 20) {
                        pg.append("path")
                            .attr("d", `M 0 ${-ph} L ${-pw*0.3} ${-ph+6} L 0 ${-ph+8} L ${pw*0.3} ${-ph+6} Z`)
                            .attr("fill", "#D7CCC8").attr("opacity", 0.6);
                    }
                };

                const peakHeight = 18 + (hf * 32);
                drawRuggedMountain(0, 0, peakHeight, 22, 0);
                
                if (hf > 0.6) {
                    drawRuggedMountain(-10, 4, peakHeight * 0.6, 14, 0.2);
                    drawRuggedMountain(12, -4, peakHeight * 0.4, 12, 0.1);
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
            }

            if (d.owner) {
                const ownerInfo = civilizaciones[d.owner] || gruposDinamicos[d.owner];
                const ownerColor = ownerInfo?.color || "#ffffff";
                cell.append("path").attr("class", "cell-overlay").attr("d", topFace).attr("fill", ownerColor).attr("opacity", 0.3).attr("stroke", ownerColor).attr("stroke-width", 2);
            }

            if (hasBuildings) {
                d.buildings.forEach((b: any) => {
                    const ownerColor = civilizaciones[b.grupo_id]?.color || gruposDinamicos[b.grupo_id]?.color || "#7c4dff";
                    // Posicionamiento centrado exacto
                    const bg = cell.append("g").attr("class", "building-unit").attr("transform", "translate(0, 0)");

                    // Diseño base robusto
                    let blkW = 16, blkH = 8, blkZ = 12;
                    const themeColors: any = {
                        Hospital: { t: "#FFFFFF", l: "#ECEFF1", r: "#CFD8DC", accents: "#EF5350", glass: true },
                        Universidad: { t: "#ECEFF1", l: "#B0BEC5", r: "#78909C", accents: "#3949AB", tiers: 2 },
                        Granja: { t: "#A1887F", l: "#6D4C41", r: "#4E342E", accents: "#FDD835", farm: true },
                        "Centro Comunitario": { t: "#80CBC4", l: "#00897B", r: "#00695C", accents: "#E0F2F1", octagonal: true },
                        "Torre de Vigilancia": { t: "#90A4AE", l: "#546E7A", r: "#37474F", accents: "#FFD54F", height: 35 },
                        Mina: { t: "#546E7A", l: "#263238", r: "#1C2329", accents: "#FFB300", rugged: true },
                        default: { t: "#FFCC80", l: "#FB8C00", r: "#E65100", accents: "#FFF" }
                    };
                    const tc = themeColors[b.tipo] || themeColors.default;

                    bg.style("filter", "url(#drop-shadow-soft)");

                    // Cimentación/Plataforma
                    bg.append("path").attr("d", `M ${-blkW-2} 0 L 0 ${blkH+1} L ${blkW+2} 0 L 0 ${-blkH-1} Z`).attr("fill", "rgba(0,0,0,0.2)");

                    const drawBox = (w: number, h: number, z: number, zOff: number, topC: string, leftC: string, rightC: string) => {
                        const g = bg.append("g").attr("transform", `translate(0, -${zOff})`);
                        const topD = `M ${-w} ${-z} L 0 ${-z + h} L ${w} ${-z} L 0 ${-z - h} Z`;
                        const leftD = `M ${-w} ${-z} L 0 ${-z + h} L 0 ${h} L ${-w} 0 Z`;
                        const rightD = `M 0 ${-z + h} L ${w} ${-z} L ${w} 0 L 0 ${h} Z`;
                        g.append("path").attr("d", leftD).attr("fill", leftC);
                        g.append("path").attr("d", rightD).attr("fill", rightC);
                        g.append("path").attr("d", topD).attr("fill", topC).attr("stroke", "rgba(255,255,255,0.1)").attr("stroke-width", 0.5);
                        return g;
                    };

                    if (tc.height) { // Torres
                        drawBox(8, 4, tc.height, 0, tc.t, tc.l, tc.r);
                        // Cúpula/Observatorio
                        drawBox(10, 5, 6, tc.height, tc.accents, tc.l, tc.r);
                    } else if (tc.tiers) { // Edificios complejos (Universidad)
                        drawBox(blkW, blkH, 10, 0, tc.t, tc.l, tc.r);
                        drawBox(blkW*0.6, blkH*0.6, 8, 10, tc.t, tc.l, tc.r);
                    } else if (tc.octagonal) { // Centro Comunitario
                        drawBox(12, 12, 14, 0, tc.t, tc.l, tc.r);
                    } else { // Edificios estándar
                        drawBox(blkW, blkH, blkZ, 0, tc.t, tc.l, tc.r);
                    }

                    // Detalles decorativos (ventanas realistas)
                    const winW = 3, winH = 4;
                    const rows = tc.height ? 4 : 2;
                    for(let i=0; i<rows; i++) {
                        const y = tc.height ? -(i*8 + 8) : -6;
                        bg.append("rect").attr("x", -6).attr("y", y).attr("width", winW).attr("height", winH).attr("fill", "#E3F2FD").attr("opacity", 0.8).attr("rx", 1);
                        bg.append("rect").attr("x", 3).attr("y", y).attr("width", winW).attr("height", winH).attr("fill", "#E3F2FD").attr("opacity", 0.8).attr("rx", 1);
                    }

                    // Puerta robusta
                    bg.append("path").attr("d", "M -3 0 L 3 0 L 3 -6 L -3 -6 Z").attr("fill", "#3E2723");

                    // Letrero Moderno
                    const sign = bg.append("g").attr("transform", `translate(0, -${(tc.height || blkZ) + 15})`);
                    sign.append("circle").attr("r", 10).attr("fill", "white").attr("stroke", ownerColor).attr("stroke-width", 2);
                    sign.append("text").attr("y", 4).attr("text-anchor", "middle").attr("font-size", "10px").text(buildingIcons[b.tipo] || "🏢");
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
                const resColors: Record<string, string> = { 
                    'food': '#FF5252', 'comida': '#FF5252', 'carne': '#FF5252', 'bayas': '#FF5252',
                    'wood': '#8D6E63', 'madera': '#8D6E63', 'leña': '#8D6E63',
                    'stone': '#90A4AE', 'piedra': '#90A4AE', 'roca': '#90A4AE',
                    'iron': '#B0BEC5', 'mineral': '#B0BEC5', 'hierro': '#B0BEC5', 'metal': '#B0BEC5',
                    'gold': '#FFD54F', 'oro': '#FFD54F', 'tesoro': '#FFD54F',
                    'medicine': '#81C784', 'medicina': '#81C784', 'hierbas': '#81C784',
                    'fish': '#4FC3F7', 'pescado': '#4FC3F7', 'pez': '#4FC3F7'
                };
                const resIcons: Record<string, string> = { 
                    'food': '🍎', 'comida': '🍎', 'carne': '🥩', 'bayas': '🍓',
                    'wood': '🪵', 'madera': '🪵', 'leña': '🪵',
                    'stone': '🗿', 'piedra': '🗿', 'roca': '🪨',
                    'iron': '⚙️', 'mineral': '⚙️', 'hierro': '⛓️', 'metal': '🔩',
                    'gold': '💰', 'oro': '💰', 'tesoro': '💎',
                    'medicine': '💊', 'medicina': '💊', 'hierbas': '🌿',
                    'fish': '🐟', 'pescado': '🐟', 'pez': '🐠'
                };
                const type = d.resource.type?.toLowerCase() || "unknown";
                const color = resColors[type] || '#7c4dff';
                // Iconos aún más pequeños y elegantes
                const bag = cell.append("g").attr("class", "resource-icon").attr("transform", `translate(0, 0) scale(0.65)`);
                
                // Sombra mínima
                bag.append("ellipse").attr("cx", 0).attr("cy", 2).attr("rx", 4).attr("ry", 1.5).attr("fill", "rgba(0,0,0,0.15)");
                
                bag.append("text").attr("y", -2).attr("text-anchor", "middle").attr("font-size", "14px").style("filter", "url(#drop-shadow-soft)").text(resIcons[type] || '🎁');
            }
            // Mostrar sitio arqueológico (oculto hasta ser descubierto)
            else if (d.is_archaeological_site || terrainStr === 'archaeological_site') {
                const siteGroup = cell.append("g").attr("class", "arch-site").attr("transform", "translate(0, -6)");
                if (d.discovered_by) {
                    siteGroup.append("ellipse").attr("cx", 0).attr("cy", 2).attr("rx", 7).attr("ry", 3).attr("fill", terrainColors.archaeological_site.top).attr("opacity", 0.95);
                    siteGroup.append("text").attr("y", 4).attr("text-anchor", "middle").attr("font-size", "14px").style("filter", "url(#drop-shadow-soft)").text("🏺");
                    if (d.artifact_type) {
                        siteGroup.append("text").attr("y", -10).attr("text-anchor", "middle").attr("font-size", "7px").attr("fill", "#ffffff").text(d.artifact_type);
                    }
                } else {
                    // Marcador sutil para sitio no descubierto (montículo)
                    const mound = cell.append("g").attr("class", "arch-site-hidden").attr("transform", "translate(0, -2)");
                    mound.append("ellipse").attr("cx", 0).attr("cy", 2).attr("rx", 6).attr("ry", 2).attr("fill", "rgba(0,0,0,0.12)");
                    mound.append("path").attr("d", "M -6 0 Q 0 -6 6 0 Z").attr("fill", terrainColors.archaeological_site.left).attr("opacity", 0.22);
                }
            }
        });
    }, [mapa, showGrid]);

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

        if (showLinks) {
            console.debug && console.debug(`[WorldViewport] relationships: ${ (relationships || []).length }, agents: ${agents.length}`);
            const agentCoords = new Map();
            agents.forEach(a => agentCoords.set(a.id, iso(a.x, a.y)));

            // --- LÍNEAS DE PERTENENCIA A GRUPO (líneas más finas, color del grupo) ---
            const groupsMap: Record<string, any[]> = {};
            agents.forEach(a => {
                const gid = (a as any).grupo_id || (a as any).group_id || null;
                if (gid) {
                    groupsMap[gid] = groupsMap[gid] || [];
                    groupsMap[gid].push(a);
                }
            });

            const groupLineData: any[] = Object.entries(groupsMap).flatMap(([gid, members]) => {
                // Conectar miembros adyacentes para evitar demasiadas líneas
                return members.slice(1).map((m: any, idx: number) => {
                    const src = members[idx];
                    const s = agentCoords.get(src.id);
                    const t = agentCoords.get(m.id);
                    if (!s || !t) return null;
                    return { source: src.id, target: m.id, coords: { source: s, target: t }, groupId: gid };
                }).filter(Boolean);
            });

            const groupLinks = linkGroup.selectAll("line.group-link").data(groupLineData, (d: any) => `${d.source}-${d.target}-group`)
                .join(
                    enter => enter.append("line").attr("class", "group-link"),
                    update => update,
                    exit => exit.remove()
                )
                .attr("x1", d => d.coords.source.x)
                .attr("y1", d => d.coords.source.y - 10)
                .attr("x2", d => d.coords.target.x)
                .attr("y2", d => d.coords.target.y - 10)
                .attr("stroke", d => {
                    const ownerInfo = (useGameStore.getState().civilizaciones || {})[d.groupId] || (useGameStore.getState().gruposDinamicos || {})[d.groupId];
                    return ownerInfo?.color || "#9c27b0";
                })
                .attr("stroke-width", 0.6)
                .attr("opacity", 0.45)
                .attr("stroke-linecap", "round")
                .attr("pointer-events", "none");
            // colocar líneas de grupo por debajo de los nodos
            groupLinks.each(function() { (this as any).parentNode && (this as any).parentNode.insertBefore(this, (this as any).parentNode.firstChild); });

            // --- RELACIONES ENTRE AGENTES ---
            const relationshipData = (relationships || []).map(rel => ({ ...rel, coords: { source: agentCoords.get(rel.source), target: agentCoords.get(rel.target) } })).filter(d => d.coords.source && d.coords.target);

            const relLinks = linkGroup.selectAll("line.rel-link").data(relationshipData, (d: any) => `${d.source}-${d.target}-${d.type}`).join(
                enter => enter.append("line").attr("class", "rel-link"),
                update => update,
                exit => exit.remove()
            );

            relLinks
                .attr("x1", d => d.coords.source.x)
                .attr("y1", d => d.coords.source.y - 10)
                .attr("x2", d => d.coords.target.x)
                .attr("y2", d => d.coords.target.y - 10)
                .attr("stroke", (d: any) => {
                    if (d.type === 'amigo') return "#00e676"; // verde amistad
                    if (d.type === 'enemigo') return "#ff1744"; // rojo enemistad
                    if (d.type === 'alianza' || d.type === 'alliance') return "#ffd600"; // diplomacia
                    if (d.type === 'conocido') return "#90A4AE"; // gris para conocidos
                    return "#ffffff";
                })
                .attr("stroke-width", (d: any) => {
                    const strength = Math.abs(Number(d.strength || 0));
                    const base = Math.max(0.5, Math.min(3, strength * 2));
                    if (d.type === 'amigo') return Math.max(1.0, base);
                    if (d.type === 'enemigo') return Math.max(1.6, base, 1.8);
                    if (d.type === 'alianza' || d.type === 'alliance') return Math.max(1.0, base);
                    if (d.type === 'conocido') return Math.max(0.6, base * 0.6);
                    return Math.max(0.5, base * 0.6);
                })
                .attr("stroke-dasharray", (d: any) => (d.type === 'alianza' || d.type === 'alliance') ? "6,3" : "none")
                .attr("opacity", (d: any) => {
                    if (d.type === 'amigo') return 0.75;
                    if (d.type === 'enemigo') return 0.95;
                    if (d.type === 'alianza' || d.type === 'alliance') return 0.9;
                    if (d.type === 'conocido') return 0.45;
                    return 0.35;
                })
                .attr("stroke-linecap", "round")
                .attr("pointer-events", "none");

            // Asegurar que las relaciones sociales se rendericen por encima de las líneas de grupo
            relLinks.each(function() { if ((this as any).parentNode) (this as any).parentNode.appendChild(this); });

            // --- SÍMBOLOS PARA ALIANZAS (emoji en el punto medio) ---
            const allianceData = relationshipData.filter((d: any) => d.type === 'alianza' || d.type === 'alliance');
            const allianceSymbols = linkGroup.selectAll("text.alliance-symbol").data(allianceData, (d: any) => `${d.source}-${d.target}`);
            allianceSymbols.join(
                enter => enter.append("text").attr("class", "alliance-symbol").attr("text-anchor", "middle").attr("alignment-baseline", "middle").text("🤝"),
                update => update,
                exit => exit.remove()
            )
            .attr("x", (d: any) => (d.coords.source.x + d.coords.target.x) / 2)
            .attr("y", (d: any) => ((d.coords.source.y + d.coords.target.y) / 2) - 8)
            .attr("font-size", 10)
            .attr("opacity", 0.95)
            .attr("pointer-events", "none");

        } else {
            linkGroup.selectAll("line").remove();
            linkGroup.selectAll("text.alliance-symbol").remove();
        }

        const sortedAgents = [...agents].sort((a, b) => (a.x + a.y) - (b.x + b.y));
        const agentSelection = agentGroup.selectAll<SVGGElement, any>(".agent").data(sortedAgents, (d) => d.id);
        const enter = agentSelection.enter().append("g").attr("class", "agent").attr("cursor", "pointer").on("click", (event, d) => { event.stopPropagation(); selectAgent(d.id); });
        enter.append("ellipse").attr("class", "agent-shadow").attr("cx", 0).attr("cy", 0).attr("rx", 10).attr("ry", 5).attr("fill", "rgba(0,0,0,0.25)");
        
        // Aura de Avatar de Jugador / Posesión
        enter.append("path").attr("class", "player-aura-ring")
            .attr("d", "M 0 -14 L 21 0 L 0 14 L -21 0 Z")
            .attr("fill", "rgba(16, 185, 129, 0.14)")
            .attr("stroke", "#ffd54f")
            .attr("stroke-width", 2)
            .attr("stroke-dasharray", "4,2")
            .attr("opacity", 0)
            .style("filter", "drop-shadow(0 0 6px #10b981)");

        // Indicador de Selección: Un rombo brillante debajo del agente
        enter.append("path").attr("class", "selection-ring")
            .attr("d", "M 0 -12 L 18 0 L 0 12 L -18 0 Z")
            .attr("fill", "none")
            .attr("stroke", "#4fc3f7")
            .attr("stroke-width", 3)
            .attr("opacity", 0)
            .style("filter", "drop-shadow(0 0 4px #4fc3f7)");
        
        const bodyGroup = enter.append("g").attr("class", "agent-body animate-organic-float").style("filter", "url(#drop-shadow-soft)");
        
        bodyGroup.each(function(d) {
            const g = d3.select(this);
            const seed = (d.id || "0").split('').reduce((a: number, b: string) => a + b.charCodeAt(0), 0);
            const isAvatar = Boolean(d.is_player_avatar || String(d.id || "").startsWith("av_"));
            
            // Aplicar variabilidad no uniforme mediante variables CSS
            const duration = 2.5 + (Math.sin(seed * 0.5) + 1) * 1.5; // Entre 2.5s y 5.5s
            const delay = -(Math.sin(seed * 0.8) + 1) * 2; // Offset negativo para que empiecen en puntos distintos
            
            g.style("--float-duration", `${duration}s`)
             .style("--float-delay", `${delay}s`);

            const skinTones = ["#FFDBAC", "#F1C27D", "#E0AC69", "#8D5524", "#C68642"];
            const hairColors = ["#000000", "#4B2C20", "#8D4E33", "#B1B1B1", "#D6C4C2", "#E4B877"];
            
            const skin = skinTones[seed % skinTones.length];
            const hair = hairColors[(seed * 7) % hairColors.length];
            const hairStyle = (seed * 3) % 4;

            // --- DISEÑO HUMANOIDE FLOTANTE SIN PIERNAS ---
            
            // Torso con base redondeada (estilo fantasma/flotante)
            const defaultBodyColor = isAvatar ? "#10b981" : "#EF5350";
            const torsoColor = (d.color && d.color !== "#ffffff") ? d.color : defaultBodyColor;
            g.append("path").attr("class", "agent-torso")
                .attr("d", "M -4.5 -16 L 4.5 -16 Q 5.5 -16 5.5 -13 L 5.5 -6 Q 5.5 -2 0 -2 Q -5.5 -2 -5.5 -6 L -5.5 -13 Q -5.5 -16 -4.5 -16")
                .attr("fill", torsoColor)
                .attr("stroke", isAvatar ? "#ffd54f" : "rgba(255,255,255,0.1)")
                .attr("stroke-width", isAvatar ? 1.5 : 1);
            
            // Cabeza redondeada
            g.append("rect").attr("x", -5.5).attr("y", -26).attr("width", 11).attr("height", 11).attr("rx", 5).attr("fill", skin);
            
            // CABELLO (Detrás de los ojos)
            const hG = g.append("g");
            if (hairStyle === 0) { hG.append("path").attr("d", "M -5.5 -26 Q 0 -32 5.5 -26 L 5.5 -24 L -5.5 -24 Z").attr("fill", hair); }
            else if (hairStyle === 1) { hG.append("path").attr("d", "M -5.5 -26 Q 2 -34 7 -26 L 5 -24 L -5.5 -24 Z").attr("fill", hair); }
            else if (hairStyle === 2) { hG.append("path").attr("d", "M -6 -26 Q 0 -30 6 -26 L 7 -18 L -7 -18 Z").attr("fill", hair); }
            else { hG.append("circle").attr("cx", 0).attr("cy", -26).attr("r", 5.5).attr("fill", hair); hG.append("circle").attr("cx", 0).attr("cy", -30).attr("r", 2.5).attr("fill", hair); }

            // ROSTRO
            g.append("circle").attr("cx", -2).attr("cy", -21).attr("r", 1.2).attr("fill", "#212121");
            g.append("circle").attr("cx", 2).attr("cy", -21).attr("r", 1.2).attr("fill", "#212121");
            g.append("circle").attr("cx", -2.4).attr("cy", -21.4).attr("r", 0.4).attr("fill", "#fff");
            g.append("circle").attr("cx", 1.6).attr("cy", -21.4).attr("r", 0.4).attr("fill", "#fff");

            // Brazos
            g.append("rect").attr("x", -6.5).attr("y", -15).attr("width", 2).attr("height", 6).attr("rx", 1).attr("fill", skin);
            g.append("rect").attr("x", 4.5).attr("y", -15).attr("width", 2).attr("height", 6).attr("rx", 1).attr("fill", skin);

            // Corona de Avatar de Jugador
            g.append("text")
                .attr("class", "player-crown-badge")
                .attr("x", 0)
                .attr("y", -33)
                .attr("text-anchor", "middle")
                .attr("font-size", "10px")
                .attr("opacity", isAvatar ? 1 : 0)
                .text("👑");
        });

        const nameGroup = enter.append("g").attr("class", "agent-name-group").attr("transform", "translate(0, 10)");
        nameGroup.append("rect").attr("class", "agent-name-bg").attr("x", -34).attr("y", 0).attr("width", 68).attr("height", 13).attr("rx", 3).attr("fill", "rgba(0,0,0,0.75)");
        nameGroup.append("text").attr("class", "agent-name-text").attr("y", 9.5).attr("text-anchor", "middle").attr("font-size", "8.5px").attr("fill", "#ffffff").attr("font-weight", "600").attr("font-family", "monospace");

        const merged = enter.merge(agentSelection);
        
        // Aplicar la clase y variables de animación a todos los agentes (nuevos y existentes)
        merged.select(".agent-body")
            .attr("class", "agent-body animate-organic-float")
            .each(function(d) {
                const seed = (d.id || "0").split('').reduce((a: number, b: string) => a + b.charCodeAt(0), 0);
                const duration = 2.5 + (Math.sin(seed * 0.5) + 1) * 1.5;
                const delay = -(Math.sin(seed * 0.8) + 1) * 2;
                const isAvatar = Boolean(d.is_player_avatar || String(d.id || "").startsWith("av_"));
                const defaultBodyColor = isAvatar ? "#10b981" : "#EF5350";
                const torsoColor = (d.color && d.color !== "#ffffff") ? d.color : defaultBodyColor;
                
                const g = d3.select(this)
                    .style("--float-duration", `${duration}s`)
                    .style("--float-delay", `${delay}s`);

                g.select(".agent-torso")
                    .attr("fill", torsoColor)
                    .attr("stroke", isAvatar ? "#ffd54f" : "rgba(255,255,255,0.1)")
                    .attr("stroke-width", isAvatar ? 1.5 : 1);

                g.select(".player-crown-badge")
                    .attr("opacity", (isAvatar || d.is_possessed) ? 1 : 0)
                    .text(isAvatar ? "👑" : "⚡");
            });

        merged.select(".agent-name-bg")
            .attr("fill", (d) => (d.is_player_avatar || String(d.id || "").startsWith("av_")) ? "rgba(6, 78, 59, 0.9)" : "rgba(0,0,0,0.75)")
            .attr("stroke", (d) => (d.is_player_avatar || String(d.id || "").startsWith("av_")) ? "#ffd54f" : "none")
            .attr("stroke-width", (d) => (d.is_player_avatar || String(d.id || "").startsWith("av_")) ? 1 : 0);

        merged.select(".agent-name-text")
            .attr("fill", (d) => (d.is_player_avatar || String(d.id || "").startsWith("av_")) ? "#ffd54f" : "#ffffff")
            .text((d) => {
                const isAvatar = Boolean(d.is_player_avatar || String(d.id || "").startsWith("av_"));
                const rawName = d.identidad?.nombre || d.alma?.nombre_propio || d.id || "???";
                const shortName = rawName.length > 9 ? rawName.substring(0, 8) + ".." : rawName;
                return isAvatar ? `👑${shortName}` : shortName;
            });

        merged.each(function(d) {
            const currentPos = iso(d.x, d.y);
            const node = d3.select(this);
            
            // Eliminar delay para evitar que actualizaciones frecuentes cancelen la transición
            node.transition()
                .duration(400)
                .ease(d3.easeCubicOut)
                .attr("transform", `translate(${currentPos.x}, ${currentPos.y})`);
        });
        merged.select(".player-aura-ring").transition().duration(200).attr("opacity", (d) => (d.is_player_avatar || String(d.id || "").startsWith("av_") || d.is_possessed) ? 1 : 0);
        merged.select(".selection-ring").transition().duration(200).attr("opacity", (d) => d.id === selectedAgentId ? 1 : 0);
        agentSelection.exit().remove();

        if (speechBubbles && !hideBubbles) {
            const bubbleData = Object.entries(speechBubbles).map(([id, b]) => ({ id, ...b })).filter(b => agents.some(a => a.id === b.id));
            bubbleGroup.selectAll(".bubble-g").data(bubbleData, (d: any) => d.id + d.timestamp).join(
                enter => {
                    const bg = enter.append("g").attr("class", "bubble-g").attr("opacity", 1);
                    bg.append("rect").attr("class", "bubble-bg").attr("rx", 4).attr("fill", "white").attr("stroke", "#424242").attr("stroke-width", 2);
                    bg.append("path").attr("d", "M -5 0 L 5 0 L 0 5 Z").attr("fill", "white").attr("stroke", "#424242").attr("stroke-width", 2);
                    bg.append("path").attr("d", "M -4 0 L 4 0 L 0 4 Z").attr("fill", "white");
                    bg.append("text").attr("class", "bubble-text").attr("text-anchor", "middle").attr("font-size", "6.5px").attr("fill", "#000").attr("font-family", "monospace").attr("font-weight", "bold");
                    return bg;
                }, update => update, exit => exit.remove()
            ).each(function(this: any, d: any) {
                const agent = agents.find(a => a.id === d.id); if (!agent) return;
                const pos = iso(agent.x, agent.y);
                const g = d3.select(this); 
                const rawText = d.text || "";
                const text = replaceIdsWithNames(rawText, agents).toUpperCase(); 
                const words = text.split(/\s+/); 
                const lines: string[] = []; 
                let cur = "";
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
                g.attr("opacity", 1).attr("transform", `translate(${pos.x}, ${pos.y + yOff})`);
            });
        } else bubbleGroup.selectAll(".bubble-g").remove();

        weatherGroup.selectAll("rect").data((weather === 'rainy' || weather === 'storm') ? [1] : []).join("rect").attr("x", -mapa.length*tileW).attr("y", -mapa[0].length*tileH).attr("width", mapa.length * tileW * 2).attr("height", mapa[0].length * tileH * 2).attr("fill", "#1E88E5").attr("opacity", 0.08);

    }, [agents, selectedAgentId, weather, selectAgent, relationships, speechBubbles, showLinks, hideBubbles]);

    return (
        <div ref={containerRef} className="w-full h-full relative bg-[#1c2128] overflow-hidden" style={{ imageRendering: "pixelated" }}>
            {/* Contenedor del Tablero Isométrico (replegable/minimizable) */}
            <div
                className={`transition-all duration-300 ${
                    isBoardMinimized
                        ? "absolute top-20 left-6 w-72 h-44 rounded-2xl border-2 border-emerald-500/40 shadow-2xl overflow-hidden z-40 bg-[#14181f]"
                        : "w-full h-full relative"
                }`}
            >
                <svg ref={svgRef} className="w-full h-full block" />
                {isBoardMinimized && (
                    <div className="absolute top-2 left-2 right-2 flex items-center justify-between px-2.5 py-1 rounded-lg bg-black/75 border border-white/10 backdrop-blur-md pointer-events-auto">
                        <span className="text-[10px] font-mono font-bold text-emerald-400 uppercase flex items-center gap-1.5">
                            <MapIcon className="w-3 h-3" /> Tablero ({mapWidth}×{mapHeight})
                        </span>
                        <button
                            onClick={() => setIsBoardMinimized(false)}
                            className="p-1 rounded bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 transition-all"
                            title="Expandir Tablero a pantalla completa"
                        >
                            <Maximize2 className="w-3 h-3" />
                        </button>
                    </div>
                )}
            </div>

            <div className="absolute top-20 right-6 flex flex-col gap-2 z-50">
                <button
                    onClick={() => setIsBoardMinimized(!isBoardMinimized)}
                    title={isBoardMinimized ? "Expandir Tablero" : "Minimizar / Replegar Tablero"}
                    className="glass-panel p-2.5 rounded-xl border border-white/10 hover:border-emerald-500/50 transition-all"
                >
                    {isBoardMinimized ? (
                        <Maximize2 className="w-4 h-4 text-emerald-400" />
                    ) : (
                        <Minimize2 className="w-4 h-4 text-gray-300" />
                    )}
                </button>
                <button onClick={() => setShowLinks(!showLinks)} title="Relaciones" className="glass-panel p-2.5 rounded-xl border border-white/10 hover:border-purple-500/50 transition-all">
                    {showLinks ? <Link className="w-4 h-4 text-emerald-400" /> : <Link2Off className="w-4 h-4 text-gray-400" />}
                </button>
                <button onClick={() => setShowGrid(!showGrid)} title="Cuadrícula" className="glass-panel p-2.5 rounded-xl border border-white/10 hover:border-blue-500/50 transition-all">
                    <svg className={`w-4 h-4 ${showGrid ? 'text-blue-400' : 'text-gray-400'}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="3" y1="15" x2="21" y2="15"/><line x1="9" y1="3" x2="9" y2="21"/><line x1="15" y1="3" x2="15" y2="21"/>
                    </svg>
                </button>
            </div>
            {!isBoardMinimized && (
                <div className="absolute top-20 left-6 flex flex-col gap-2 z-40">
                    {/* Leyenda de Biomas y Dimensiones (replegable) */}
                    <div className="p-2.5 rounded-xl border-2 border-[#424242] text-[9px] w-40 bg-[#212121]/90 shadow-[2px_2px_0px_#000]">
                        <button
                            onClick={() => setIsLegendCollapsed(!isLegendCollapsed)}
                            className="w-full flex items-center justify-between text-[#E0E0E0] font-bold uppercase font-monospace"
                        >
                            <span>Biomas ({mapWidth}×{mapHeight})</span>
                            {isLegendCollapsed ? <ChevronDown className="w-3 h-3" /> : <ChevronUp className="w-3 h-3" />}
                        </button>
                        {!isLegendCollapsed && (
                            <div className="mt-2 pt-2 border-t-2 border-[#424242] space-y-2">
                                <div className="grid grid-cols-1 gap-y-1.5 px-1 font-monospace text-[#BDBDBD]">
                                    <LegendBox top="#7CB342" left="#558B2F" right="#689F38" label="Hierba" />
                                    <LegendBox top="#B0BEC5" left="#546E7A" right="#37474F" label="Montaña" />
                                    <LegendBox top="#29B6F6" left="#0288D1" right="#039BE5" label="Lago" />
                                    <LegendBox top="#558B2F" left="#33691E" right="#417A27" label="Bosque" />
                                    <LegendBox top="#FFE082" left="#FFB300" right="#FFCA28" label="Desierto" />
                                </div>
                                {mapa && mapa.length > 0 && (
                                    <div className="pt-1.5 border-t border-[#424242] text-[8px] font-monospace text-gray-400">
                                        {mapWidth * mapHeight} casillas totales
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                </div>
            )}
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
