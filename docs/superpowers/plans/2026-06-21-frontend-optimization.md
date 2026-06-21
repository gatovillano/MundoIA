# Plan de Implementación de Optimización del Frontend

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Optimizar la velocidad de carga inicial y la fluidez de renderizado (FPS) de la simulación del frontend en MundoIA.

**Architecture:** Implementación de carga diferida (code splitting) mediante Next.js `dynamic` para aislar Three.js y D3 en chunks asíncronos; migración de animaciones de DOM a aceleración de hardware (GPU Composer) mediante `translate3d`; y optimización del bucle D3 en el mapa isométrico para evitar recreación de nodos del DOM mediante reconciliación incremental.

**Tech Stack:** Next.js 16.1, React 19.2, D3.js 7.9, Three.js 0.182, TailwindCSS.

---

### Task 1: Carga Diferida (Lazy Loading) de Componentes Pesados

**Files:**
- Modify: `web/frontend/src/app/game/page.tsx:1-31`
- Modify: `web/frontend/src/app/game/page.tsx:80-90` (donde se declaran los componentes si aplica)

- [ ] **Step 1: Modificar las importaciones de las vistas pesadas**
  Eliminar las importaciones estáticas de `WorldViewport`, `WorldViewport3D` y `NetworkView` en [web/frontend/src/app/game/page.tsx](file:///home/gato/Proyectos/MundoIA/web/frontend/src/app/game/page.tsx) y reemplazarlas por importaciones dinámicas utilizando `next/dynamic` con la opción `ssr: false`.

  **Código a reemplazar (líneas 11-13):**
  ```typescript
  import WorldViewport from "@/components/WorldViewport";
  import WorldViewport3D from "@/components/WorldViewport3D";
  import NetworkView from "@/components/NetworkView";
  ```

  **Código de reemplazo:**
  ```typescript
  import dynamic from "next/dynamic";

  const WorldViewport = dynamic(() => import("@/components/WorldViewport"), {
      ssr: false,
      loading: () => (
          <div className="w-full h-full flex items-center justify-center bg-[#1c2128]">
              <span className="text-gray-400 font-mono text-sm animate-pulse">CARGANDO MAPA ISOMÉTRICO (D3)...</span>
          </div>
      )
  });

  const WorldViewport3D = dynamic(() => import("@/components/WorldViewport3D"), {
      ssr: false,
      loading: () => (
          <div className="w-full h-full flex items-center justify-center bg-[#1c2128]">
              <span className="text-gray-400 font-mono text-sm animate-pulse">INICIALIZANDO MOTOR 3D (THREE.JS)...</span>
          </div>
      )
  });

  const NetworkView = dynamic(() => import("@/components/NetworkView"), {
      ssr: false,
      loading: () => (
          <div className="w-full h-full flex items-center justify-center bg-[#1c2128]">
              <span className="text-gray-400 font-mono text-sm animate-pulse">GENERANDO RED SOCIAL GRAFO...</span>
          </div>
      )
  });
  ```

- [ ] **Step 2: Verificar la ausencia de errores de compilación sintáctica**
  Ejecutar el linter de Next.js/Eslint sobre el frontend para verificar que no haya problemas de sintaxis o importación.
  Run: `npm run lint` en `web/frontend`
  Expected: PASS con advertencias normales o salida limpia.

- [ ] **Step 3: Commit**
  ```bash
  git add web/frontend/src/app/game/page.tsx
  git commit -m "perf: lazy load heavy viewports to split Three.js and D3 bundles"
  ```

---

### Task 2: Aceleración por Hardware (GPU) en BackgroundEffects

**Files:**
- Modify: `web/frontend/src/components/BackgroundEffects.tsx:8-43`

- [ ] **Step 1: Modificar la animación del cursor en BackgroundEffects**
  Reemplazar el uso de propiedades CSS `left` y `top` por `transform: translate3d(...)` para evitar recalcular el layout de la página en cada movimiento del cursor.

  **Código original a modificar:**
  ```typescript
      useEffect(() => {
          const handleMouseMove = (e: MouseEvent) => {
              if (blobRef.current) {
                  const x = e.clientX;
                  const y = e.clientY;
                  blobRef.current.animate({
                      left: `${x}px`,
                      top: `${y}px`
                  }, { duration: 3000, fill: "forwards" });
              }
          };

          window.addEventListener("pointermove", handleMouseMove);
          return () => window.removeEventListener("pointermove", handleMouseMove);
      }, []);

      return (
          <div className="fixed inset-0 z-[-1] overflow-hidden pointer-events-none">
              {/* Grid Pattern */}
              <div className="absolute inset-0 bg-[url('/grid.svg')] opacity-[0.03]" />

              {/* Ambient Gradient Blob */}
              <div
                  ref={blobRef}
                  className="absolute w-[800px] h-[800px] bg-indigo-500/10 rounded-full blur-[120px] -translate-x-1/2 -translate-y-1/2 transition-transform duration-75 will-change-transform"
              />
  ```

  **Código optimizado:**
  ```typescript
      useEffect(() => {
          const handleMouseMove = (e: MouseEvent) => {
              if (blobRef.current) {
                  const x = e.clientX;
                  const y = e.clientY;
                  blobRef.current.animate({
                      transform: `translate3d(calc(${x}px - 50%), calc(${y}px - 50%), 0)`
                  }, { duration: 3000, fill: "forwards" });
              }
          };

          window.addEventListener("pointermove", handleMouseMove);
          return () => window.removeEventListener("pointermove", handleMouseMove);
      }, []);

      return (
          <div className="fixed inset-0 z-[-1] overflow-hidden pointer-events-none">
              {/* Grid Pattern */}
              <div className="absolute inset-0 bg-[url('/grid.svg')] opacity-[0.03]" />

              {/* Ambient Gradient Blob */}
              <div
                  ref={blobRef}
                  className="absolute left-0 top-0 w-[800px] h-[800px] bg-indigo-500/10 rounded-full blur-[120px] will-change-transform"
                  style={{ transform: "translate3d(-50%, -50%, 0)" }}
              />
  ```

- [ ] **Step 2: Verificar la compilación**
  Verificar que no haya errores tipográficos ejecutando el chequeo de tipos de TypeScript.
  Run: `npx tsc --noEmit` en `web/frontend`
  Expected: Sin errores de compilación.

- [ ] **Step 3: Commit**
  ```bash
  git add web/frontend/src/components/BackgroundEffects.tsx
  git commit -m "perf: use GPU-accelerated translate3d for background mouse effect"
  ```

---

### Task 3: Optimización del Bucle de Renderizado de Celdas y Burbujas en D3

**Files:**
- Modify: `web/frontend/src/components/WorldViewport.tsx:150-365`
- Modify: `web/frontend/src/components/WorldViewport.tsx:620-655`

- [ ] **Step 1: Eliminar limpieza destructiva en el bucle de celdas**
  Remover la línea que vacía los elementos secundarios en cada renderizado y reemplazarla por comparaciones e inserciones condicionales.

  **Código original a eliminar (líneas 156-157 aprox.):**
  ```typescript
                  // incluir decoraciones de edificio en la limpieza para evitar duplicados
                  cell.selectAll(".terrain-decor, .cell-overlay, .building-unit, .resource-icon, .tree-unit, .building-decor, .farm-decor").remove();
  ```

- [ ] **Step 2: Implementar renderizado condicional de terrenos y decoraciones estáticas**
  Modificar el código para pintar bosques, agua, desiertos, overlays de civilización, edificios y recursos solo si no están ya presentes en la celda o si sus datos han cambiado (usando el tag `data-type`).

  **Código optimizado para terrenos y elementos estáticos:**
  ```typescript
              // Reset de visibilidad para re-renderizado
              cell.selectAll(".mountain-left, .mountain-right, .mountain-top").attr("transform", null).attr("opacity", 0);
              cell.selectAll(".voxel-left, .voxel-right, .voxel-top").attr("opacity", 1);

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
                  
                  // Dibujar montañas solo si no existe la decoración de montaña
                  if (cell.select(".terrain-decor").empty()) {
                      const hf = 0.4 + (Math.abs(Math.sin(d.x * 0.5) * Math.cos(d.y * 0.5)) * 0.8);
                      const mountainElevation = 0; 
                      const peakGroup = cell.append("g").attr("class", "terrain-decor").attr("transform", `translate(0, -${mountainElevation})`);
                      
                      const drawRuggedMountain = (ox: number, oy: number, ph: number, pw: number, colorOffset: number) => {
                          const pg = peakGroup.append("g").attr("transform", `translate(${ox}, ${oy})`);
                          const cTop = d3.color(terrainColors.mountain.top)?.darker(colorOffset).toString() || terrainColors.mountain.top;
                          const cLeft = d3.color(terrainColors.mountain.left)?.darker(colorOffset).toString() || terrainColors.mountain.left;
                          const cRight = d3.color(terrainColors.mountain.right)?.darker(colorOffset).toString() || terrainColors.mountain.right;

                          pg.append("path")
                              .attr("d", `M 0 ${-ph} L ${-pw*0.6} ${-ph*0.5} L ${-pw} 0 L 0 ${tileH/2} L 0 ${-ph*0.3} Z`)
                              .attr("fill", cLeft).attr("stroke", "rgba(0,0,0,0.3)").attr("stroke-width", 0.5);
                          
                          pg.append("path")
                              .attr("d", `M 0 ${-ph} L ${pw*0.7} ${-ph*0.4} L ${pw} 0 L 0 ${tileH/2} L 0 ${-ph*0.3} Z`)
                              .attr("fill", cRight).attr("stroke", "rgba(0,0,0,0.3)").attr("stroke-width", 0.5);
                          
                          pg.append("path")
                              .attr("d", `M 0 ${-ph} L ${-pw*0.3} ${-ph*0.7} L 0 ${-ph*0.6} L ${pw*0.3} ${-ph*0.7} Z`)
                              .attr("fill", cTop).attr("opacity", 0.8);

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
              }

              // Decoraciones adicionales por bioma condicionales
              if (terrainStr === 'water') {
                  if (cell.select(".terrain-decor").empty()) {
                      const w = cell.append("g").attr("class", "terrain-decor");
                      w.append("path").attr("d", `M ${-tileW/4} ${-tileH/8} L ${tileW/4} ${tileH/8}`).attr("stroke", "rgba(255,255,255,0.4)").attr("stroke-width", 1.5);
                  }
              } else if (terrainStr === 'desert') {
                  const noise = (d.x * 23 + d.y * 19) % 100;
                  if (noise < 10 && cell.select(".terrain-decor").empty()) {
                     const c = cell.append("g").attr("class", "terrain-decor").attr("transform", "translate(0, -4)");
                     c.append("path").attr("d", "M -2 0 L -2 -8 M 2 -2 L 2 -10 M -5 -5 L 5 -5").attr("stroke", "#2E7D32").attr("stroke-width", 2);
                  }
              }

              // Overlay de propiedad de civilizaciones
              const cellOverlay = cell.select(".cell-overlay");
              if (d.owner) {
                  const ownerInfo = civilizaciones[d.owner] || gruposDinamicos[d.owner];
                  const ownerColor = ownerInfo?.color || "#ffffff";
                  if (cellOverlay.empty()) {
                      cell.append("path").attr("class", "cell-overlay").attr("d", topFace).attr("fill", ownerColor).attr("opacity", 0.3).attr("stroke", ownerColor).attr("stroke-width", 2);
                  } else {
                      cellOverlay.attr("fill", ownerColor).attr("stroke", ownerColor);
                  }
              } else {
                  cellOverlay.remove();
              }

              // Edificios
              const buildingUnit = cell.select(".building-unit");
              if (hasBuildings) {
                  if (buildingUnit.empty()) {
                      d.buildings.forEach((b: any) => {
                          const ownerColor = civilizaciones[b.grupo_id]?.color || gruposDinamicos[b.grupo_id]?.color || "#7c4dff";
                          const bg = cell.append("g").attr("class", "building-unit").attr("transform", "translate(0, 0)");
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
                          bg.append("path").attr("d", `M ${-blkW-2} 0 L 0 ${blkH+1} L ${blkW+2} 0 L 0 ${-blkH-1} Z`).attr("fill", "rgba(0,0,0,0.2)");

                          const drawBox = (w: number, h: number, z: number, zOff: number, topC: string, leftC: string, rightC: string) => {
                              const g = bg.append("g").attr("transform", `translate(0, -${zOff})`);
                              const topD = `M ${-w} ${-z} L 0 ${-z + h} L ${w} ${-z} L 0 ${-z - h} Z`;
                              const leftD = `M ${-w} ${-z} L 0 ${-z + h} L 0 ${h} L ${-w} 0 Z`;
                              const rightD = `M 0 ${-z + h} L ${w} ${-z} L ${w} 0 L 0 ${h} Z`;
                              g.append("path").attr("d", leftD).attr("fill", leftC);
                              g.append("path").attr("d", rightD).attr("fill", rightC);
                              g.append("path").attr("d", topD).attr("fill", topC).attr("stroke", "rgba(255,255,255,0.1)").attr("stroke-width", 0.5);
                          };

                          if (tc.height) {
                              drawBox(8, 4, tc.height, 0, tc.t, tc.l, tc.r);
                              drawBox(10, 5, 6, tc.height, tc.accents, tc.l, tc.r);
                          } else if (tc.tiers) {
                              drawBox(blkW, blkH, 10, 0, tc.t, tc.l, tc.r);
                              drawBox(blkW*0.6, blkH*0.6, 8, 10, tc.t, tc.l, tc.r);
                          } else if (tc.octagonal) {
                              drawBox(12, 12, 14, 0, tc.t, tc.l, tc.r);
                          } else {
                              drawBox(blkW, blkH, blkZ, 0, tc.t, tc.l, tc.r);
                          }

                          const winW = 3, winH = 4;
                          const rows = tc.height ? 4 : 2;
                          for(let i=0; i<rows; i++) {
                              const y = tc.height ? -(i*8 + 8) : -6;
                              bg.append("rect").attr("x", -6).attr("y", y).attr("width", winW).attr("height", winH).attr("fill", "#E3F2FD").attr("opacity", 0.8).attr("rx", 1);
                              bg.append("rect").attr("x", 3).attr("y", y).attr("width", winW).attr("height", winH).attr("fill", "#E3F2FD").attr("opacity", 0.8).attr("rx", 1);
                          }
                          bg.append("path").attr("d", "M -3 0 L 3 0 L 3 -6 L -3 -6 Z").attr("fill", "#3E2723");
                          const sign = bg.append("g").attr("transform", `translate(0, -${(tc.height || blkZ) + 15})`);
                          sign.append("circle").attr("r", 10).attr("fill", "white").attr("stroke", ownerColor).attr("stroke-width", 2);
                          sign.append("text").attr("y", 4).attr("text-anchor", "middle").attr("font-size", "10px").text(buildingIcons[b.tipo] || "🏢");
                      });
                  }
              } else {
                  buildingUnit.remove();
              }

              // Bosques (Árboles)
              const treeUnit = cell.select(".tree-unit");
              if (!hasBuildings && terrainStr === 'forest') {
                  if (treeUnit.empty()) {
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
                  }
              } else {
                  treeUnit.remove();
              }

              // Recursos
              const resourceIcon = cell.select(".resource-icon");
              if (d.resource) {
                  const type = d.resource.type?.toLowerCase() || "unknown";
                  const currentType = resourceIcon.attr("data-type");
                  if (resourceIcon.empty() || currentType !== type) {
                      resourceIcon.remove();
                      const bag = cell.append("g").attr("class", "resource-icon").attr("data-type", type).attr("transform", "translate(0, 0) scale(0.65)");
                      bag.append("ellipse").attr("cx", 0).attr("cy", 2).attr("rx", 4).attr("ry", 1.5).attr("fill", "rgba(0,0,0,0.15)");
                      bag.append("text").attr("y", -2).attr("text-anchor", "middle").attr("font-size", "14px").style("filter", "url(#drop-shadow-soft)").text(resIcons[type] || '🎁');
                  }
              } else {
                  resourceIcon.remove();
              }

              // Sitios Arqueológicos
              const siteGroup = cell.select(".arch-site");
              const mound = cell.select(".arch-site-hidden");
              if (d.is_archaeological_site || terrainStr === 'archaeological_site') {
                  if (d.discovered_by) {
                      mound.remove();
                      if (siteGroup.empty()) {
                          const siteGroupNew = cell.append("g").attr("class", "arch-site").attr("transform", "translate(0, -6)");
                          siteGroupNew.append("ellipse").attr("cx", 0).attr("cy", 2).attr("rx", 7).attr("ry", 3).attr("fill", terrainColors.archaeological_site.top).attr("opacity", 0.95);
                          siteGroupNew.append("text").attr("y", 4).attr("text-anchor", "middle").attr("font-size", "14px").style("filter", "url(#drop-shadow-soft)").text("🏺");
                          if (d.artifact_type) {
                              siteGroupNew.append("text").attr("y", -10).attr("text-anchor", "middle").attr("font-size", "7px").attr("fill", "#ffffff").text(d.artifact_type);
                          }
                      }
                  } else {
                      siteGroup.remove();
                      if (mound.empty()) {
                          const moundNew = cell.append("g").attr("class", "arch-site-hidden").attr("transform", "translate(0, -2)");
                          moundNew.append("ellipse").attr("cx", 0).attr("cy", 2).attr("rx", 6).attr("ry", 2).attr("fill", "rgba(0,0,0,0.12)");
                          moundNew.append("path").attr("d", "M -6 0 Q 0 -6 6 0 Z").attr("fill", terrainColors.archaeological_site.left).attr("opacity", 0.22);
                      }
                  }
              } else {
                  siteGroup.remove();
                  mound.remove();
              }
  ```

- [ ] **Step 3: Optimizar burbujas de diálogo**
  Actualizar la lógica de Speech Bubbles para procesar el empaquetado de texto en el `enter` y únicamente recalcular el `transform` posicional en el `update`.

  **Código original de burbujas (líneas 622-654 aprox.):**
  ```typescript
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
  ```

  **Código de reemplazo optimizado:**
  ```typescript
          if (speechBubbles && !hideBubbles) {
              const bubbleData = Object.entries(speechBubbles).map(([id, b]) => ({ id, ...b })).filter(b => agents.some(a => a.id === b.id));
              const bubbles = bubbleGroup.selectAll<SVGGElement, any>(".bubble-g").data(bubbleData, (d: any) => d.id + d.timestamp);
              
              bubbles.join(
                  enter => {
                      const bg = enter.append("g").attr("class", "bubble-g").attr("opacity", 1);
                      const rawText = (enter.data() as any)[0]?.text || "";
                      
                      // Procesar el ajuste de texto y dimensiones una única vez en enter
                      bg.each(function(this: any, d: any) {
                          const g = d3.select(this);
                          const text = replaceIdsWithNames(d.text || "", agents).toUpperCase();
                          const words = text.split(/\s+/);
                          const lines: string[] = [];
                          let cur = "";
                          words.forEach((w: string) => { 
                              if ((cur + w).length > 25) { 
                                  lines.push(cur.trim()); 
                                  cur = w + " "; 
                              } else {
                                  cur += w + " "; 
                              }
                          }); 
                          lines.push(cur.trim());
                          
                          const lh = 8; 
                          const bp = 8; 
                          const bw = Math.min(180, (Math.max(...lines.map(l => l.length)) * 4) + 16); 
                          const bh = (lines.length * lh) + bp;
                          
                          g.append("rect").attr("class", "bubble-bg").attr("rx", 4).attr("fill", "white").attr("stroke", "#424242").attr("stroke-width", 2)
                           .attr("x", -bw / 2).attr("y", -bh).attr("width", bw).attr("height", bh);
                          
                          g.append("path").attr("d", "M -5 0 L 5 0 L 0 5 Z").attr("fill", "white").attr("stroke", "#424242").attr("stroke-width", 2);
                          g.append("path").attr("d", "M -4 0 L 4 0 L 0 4 Z").attr("fill", "white");
                          
                          const t = g.append("text").attr("class", "bubble-text").attr("text-anchor", "middle").attr("font-size", "6.5px").attr("fill", "#000").attr("font-family", "monospace").attr("font-weight", "bold").attr("y", -bh + 12);
                          t.selectAll("tspan").data(lines).join("tspan").attr("x", 0).attr("dy", (l, i) => i === 0 ? 0 : lh).text(d => d);
                          
                          // Almacenar altura calculada en el nodo del DOM
                          (this as any).__bh = bh;
                      });
                      
                      return bg;
                  },
                  update => update,
                  exit => exit.remove()
              ).each(function(this: any, d: any) {
                  // Mover la burbuja acompañando la posición del agente de manera eficiente
                  const agent = agents.find(a => a.id === d.id); 
                  if (!agent) return;
                  const pos = iso(agent.x, agent.y);
                  let yOff = -45;
                  d3.select(this).attr("opacity", 1).attr("transform", `translate(${pos.x}, ${pos.y + yOff})`);
              });
          } else bubbleGroup.selectAll(".bubble-g").remove();
  ```

- [ ] **Step 4: Compilar y validar el proyecto frontend**
  Ejecutar el pipeline de compilación para comprobar la viabilidad y tipos del archivo modificado.
  Run: `npm run lint` en `web/frontend`
  Expected: PASS

- [ ] **Step 5: Commit**
  ```bash
  git add web/frontend/src/components/WorldViewport.tsx
  git commit -m "perf: prevent full D3 DOM node reconstruction and optimize speech bubble rendering"
  ```
