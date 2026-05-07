"use client";

import React, { useRef, useMemo, useState, Suspense, useEffect } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { OrbitControls, Text, Stars, Environment, Float, Html, QuadraticBezierLine } from "@react-three/drei";
import useGameStore from "@/store/useGameStore";
import * as THREE from "three";
import { replaceIdsWithNames } from "@/utils/nameUtils";
import { EffectComposer, Bloom, Vignette } from "@react-three/postprocessing";
import { synthesizer } from "@/utils/SoundSynthesizer";
import ErrorBoundary from "./ErrorBoundary";
import { Link, Link2Off } from "lucide-react";

const PLANET_RADIUS = 10;

function getSphericalPosition(x: number, y: number, size: number, radiusOffset: number = 0) {
    const lon = ((x / size) * 2 * Math.PI) - Math.PI;
    const lat = ((y / size) * Math.PI) - (Math.PI / 2);
    const radius = PLANET_RADIUS + radiusOffset;
    return new THREE.Vector3(
        radius * Math.cos(lat) * Math.cos(lon),
        radius * Math.sin(lat),
        radius * Math.cos(lat) * Math.sin(lon)
    );
}

// COLORES DE TERRENO MEJORADOS (PALETA MODERNA)
const terrainColors: Record<string, { base: string, variation: string, metal: number, rough: number }> = {
    grass: { base: "#558B2F", variation: "#689F38", metal: 0, rough: 0.9 },
    forest: { base: "#2E7D32", variation: "#388E3C", metal: 0, rough: 0.85 },
    mountain: { base: "#5D4037", variation: "#6D4C41", metal: 0.1, rough: 0.8 }, // Café montañoso
    water: { base: "#01579B", variation: "#0277BD", metal: 0.6, rough: 0.1 },  // Azul profundo y metálico
    desert: { base: "#FFA000", variation: "#FFC107", metal: 0.1, rough: 0.7 }, // Arena vibrante
    path: { base: "#795548", variation: "#8D6E63", metal: 0, rough: 0.9 }
};

// GEOMETRIAS COMPARTIDAS
const boxGeom = new THREE.BoxGeometry(1, 1, 1);
const coneGeom = new THREE.ConeGeometry(1, 1, 8);
const cylinderGeom = new THREE.CylinderGeometry(0.5, 0.5, 1, 8);
const sphereGeom = new THREE.SphereGeometry(0.5, 12, 12);

// MATERIALES COMPARTIDOS
const sharedMaterials: Record<string, THREE.Material> = {
    trunk: new THREE.MeshStandardMaterial({ color: "#5D4037", roughness: 0.95, metalness: 0 }),
    foliage1: new THREE.MeshStandardMaterial({ color: "#2E7D32", roughness: 0.85, metalness: 0, flatShading: true }),
    foliage2: new THREE.MeshStandardMaterial({ color: "#388E3C", roughness: 0.85, metalness: 0, flatShading: true }),
    foliage3: new THREE.MeshStandardMaterial({ color: "#1B5E20", roughness: 0.85, metalness: 0, flatShading: true }),
    mountainBase: new THREE.MeshStandardMaterial({ color: "#607D8B", roughness: 0.9, metalness: 0.05, flatShading: true }),
    mountainMid: new THREE.MeshStandardMaterial({ color: "#78909C", roughness: 0.85, metalness: 0.05, flatShading: true }),
    mountainPeak: new THREE.MeshStandardMaterial({ color: "#546E7A", roughness: 0.8, metalness: 0.1, flatShading: true }),
    snow: new THREE.MeshStandardMaterial({ color: "#FAFAFA", roughness: 0.4, metalness: 0.1, flatShading: true }),
    water: new THREE.MeshStandardMaterial({ color: "#0277BD", transparent: true, opacity: 0.75, roughness: 0.2, metalness: 0.1 }),
    houseWall: new THREE.MeshStandardMaterial({ color: "#A1887F", roughness: 0.85, metalness: 0 }),
    houseRoof: new THREE.MeshStandardMaterial({ color: "#6D4C41", roughness: 0.95, metalness: 0, flatShading: true }),
    houseDoor: new THREE.MeshStandardMaterial({ color: "#4E342E", roughness: 0.8, metalness: 0 }),
    houseWindow: new THREE.MeshStandardMaterial({ color: "#B3E5FC", roughness: 0.2, metalness: 0.4, transparent: true, opacity: 0.8 }),
    skin: new THREE.MeshStandardMaterial({ color: "#FFAB91", roughness: 0.5, metalness: 0 }),
    eye: new THREE.MeshStandardMaterial({ color: "#263238", roughness: 0.3, metalness: 0.1 }),
    hair: new THREE.MeshStandardMaterial({ color: "#3E2723", roughness: 0.95, metalness: 0 }),
};

// Generador de ruido Simplex simplificado para terreno realista
function noise3D(v: THREE.Vector3, scale: number = 1) {
    const s = v.clone().multiplyScalar(scale);
    return (Math.sin(s.x) * Math.sin(s.y) * Math.sin(s.z) + 
            Math.sin(s.x * 2.1) * Math.sin(s.y * 2.1) * Math.sin(s.z * 2.1) * 0.5) / 1.5;
}

// Generador de offsets determinísticos
function seededRandom(seed: number) {
    const x = Math.sin(seed * 127.1 + 311.7) * 43758.5453;
    return x - Math.floor(x);
}

// Geometría especial para blades de pasto (triángulo)
const grassBladeGeom = new THREE.BufferGeometry();
const bladeVerts = new Float32Array([
    -0.02, 0, 0,
    0.02, 0, 0,
    0, 0.15, 0
]);
const bladeNorms = new Float32Array([0, 0, 1, 0, 0, 1, 0, 0, 1]);
const bladeUVs = new Float32Array([0, 0, 1, 0, 0.5, 1]);
grassBladeGeom.setAttribute('position', new THREE.BufferAttribute(bladeVerts, 3));
grassBladeGeom.setAttribute('normal', new THREE.BufferAttribute(bladeNorms, 3));
grassBladeGeom.setAttribute('uv', new THREE.BufferAttribute(bladeUVs, 2));
grassBladeGeom.setIndex([0, 1, 2]);

// Componente para grass blade individual
const InstancedMeshGrassBlade = React.forwardRef<THREE.InstancedMesh, { geometry?: THREE.BufferGeometry; material?: THREE.Material; count: number }>(
    ({ geometry, material, count }, ref) => {
        return <instancedMesh ref={ref} args={[geometry || grassBladeGeom, material || new THREE.MeshStandardMaterial({ color: "#4CAF50", side: THREE.DoubleSide }), count]} />;
    }
);

// ---------------- Procedural texture helpers ----------------
function createNoiseTexture(baseColor: string, overlayColor: string, size = 256, dots = 800, repeatX = 4, repeatY = 4) {
    const canvas = document.createElement('canvas');
    canvas.width = canvas.height = size;
    const ctx = canvas.getContext('2d')!;
    ctx.fillStyle = baseColor;
    ctx.fillRect(0, 0, size, size);
    for (let i = 0; i < dots; i++) {
        const x = Math.random() * size;
        const y = Math.random() * size;
        const r = Math.random() * (size * 0.012);
        ctx.fillStyle = overlayColor;
        ctx.globalAlpha = 0.04 + Math.random() * 0.12;
        ctx.beginPath();
        ctx.arc(x, y, r, 0, Math.PI * 2);
        ctx.fill();
    }
    ctx.globalAlpha = 1;
    const tex = new THREE.CanvasTexture(canvas);
    tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
    tex.repeat.set(repeatX, repeatY);
    tex.anisotropy = 4;
    tex.needsUpdate = true;
    return tex;
}

function createStripedTexture(baseColor: string, stripeColor: string, size = 256, stripeWidth = 8, repeatX = 6, repeatY = 6) {
    const canvas = document.createElement('canvas');
    canvas.width = canvas.height = size;
    const ctx = canvas.getContext('2d')!;
    ctx.fillStyle = baseColor;
    ctx.fillRect(0, 0, size, size);
    ctx.fillStyle = stripeColor;
    for (let i = -size; i < size * 2; i += stripeWidth * 2) {
        ctx.beginPath();
        ctx.moveTo(i, 0);
        ctx.lineTo(i + stripeWidth, 0);
        ctx.lineTo(i + size + stripeWidth, size);
        ctx.lineTo(i + size, size);
        ctx.closePath();
        ctx.globalAlpha = 0.12;
        ctx.fill();
    }
    ctx.globalAlpha = 1;
    const tex = new THREE.CanvasTexture(canvas);
    tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
    tex.repeat.set(repeatX, repeatY);
    tex.anisotropy = 4;
    tex.needsUpdate = true;
    return tex;
}


// ARBOLES INSTANCIADOS - Más grandes y variados
function InstancedDecorations({ mapa, textures }: { mapa: any[][], textures?: any }) {
    const size = mapa.length;
    const treeRefs = [useRef<THREE.InstancedMesh>(null), useRef<THREE.InstancedMesh>(null), useRef<THREE.InstancedMesh>(null)];
    const mountainRefs = [useRef<THREE.InstancedMesh>(null), useRef<THREE.InstancedMesh>(null), useRef<THREE.InstancedMesh>(null), useRef<THREE.InstancedMesh>(null)];
    const grassRef = useRef<THREE.InstancedMesh>(null);
    
    const data = useMemo(() => {
        const trees: THREE.Matrix4[][] = [[], [], []];
        const mountains: THREE.Matrix4[][] = [[], [], [], []];
        const grassBlades: THREE.Matrix4[] = [];
        const tempObj = new THREE.Object3D();

        mapa.forEach((row, x) => {
            row.forEach((tile, y) => {
                const pos = getSphericalPosition(x, y, size, 0);
                const normal = pos.clone().normalize();
                
                const terrain = (tile.terrain || "grass").toLowerCase();
                
                if (terrain === "forest") {
                    // 2-3 arboles por tile, tamaños variados (0.8x a 2.0x)
                    const treeCount = 2 + Math.floor(seededRandom(x * 100 + y) * 2);
                    for (let i = 0; i < treeCount; i++) {
                        const seed = x * 1000 + y * 10 + i;
                        const ox = (seededRandom(seed) - 0.5) * 0.5;
                        const oy = (seededRandom(seed + 1) - 0.5) * 0.5;
                        const sizeMult = 0.8 + seededRandom(seed + 2) * 1.2;
                        
                        const tPos = getSphericalPosition(x + (ox/size)*20, y + (oy/size)*20, size, 0.05);
                        const tNormal = tPos.clone().normalize();
                        const tQuat = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), tNormal);
                        
                        tempObj.position.copy(tPos);
                        tempObj.quaternion.copy(tQuat);
                        
                        // Tronco grueso y alto
                        tempObj.scale.set(0.15 * sizeMult, 0.6 * sizeMult, 0.15 * sizeMult);
                        tempObj.position.add(tNormal.clone().multiplyScalar(0.3 * sizeMult));
                        tempObj.updateMatrix();
                        trees[0].push(tempObj.matrix.clone());
                        
                        // Follaje bajo - cono grande
                        tempObj.scale.set(0.8 * sizeMult, 0.7 * sizeMult, 0.8 * sizeMult);
                        tempObj.position.copy(tPos).add(tNormal.clone().multiplyScalar(0.6 * sizeMult));
                        tempObj.updateMatrix();
                        trees[1].push(tempObj.matrix.clone());
                        
                        // Follaje alto - cono medio
                        tempObj.scale.set(0.55 * sizeMult, 0.55 * sizeMult, 0.55 * sizeMult);
                        tempObj.position.copy(tPos).add(tNormal.clone().multiplyScalar(0.95 * sizeMult));
                        tempObj.updateMatrix();
                        trees[2].push(tempObj.matrix.clone());
                    }
                } else if (terrain.includes("moun") || terrain.includes("mont")) {
                    const seed = x * 100 + y;
                    const noiseVal = (Math.sin(x * 12.9898 + y * 78.233) * 43758.5453) % 1;
                    const scale = 1.5 + seededRandom(seed) * 1.2;
                    const hOffset = 0.5 + (noiseVal * 0.6);
                    
                    const mPos = getSphericalPosition(x, y, size, hOffset);
                    const mNormal = mPos.clone().normalize();
                    const mQuat = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), mNormal);

                    tempObj.position.copy(mPos);
                    tempObj.quaternion.copy(mQuat);
                    
                    // Base grande
                    tempObj.scale.set(1.3 * scale, 1.0 * scale, 1.3 * scale);
                    tempObj.position.copy(mPos).add(mNormal.clone().multiplyScalar(0.5 * scale));
                    tempObj.updateMatrix();
                    mountains[0].push(tempObj.matrix.clone());
                    
                    // Capa media
                    tempObj.scale.set(1.0 * scale, 0.9 * scale, 1.0 * scale);
                    tempObj.position.copy(mPos).add(mNormal.clone().multiplyScalar(1.1 * scale));
                    tempObj.updateMatrix();
                    mountains[1].push(tempObj.matrix.clone());
                    
                    // Peak
                    tempObj.scale.set(0.65 * scale, 1.0 * scale, 0.65 * scale);
                    tempObj.position.copy(mPos).add(mNormal.clone().multiplyScalar(1.7 * scale));
                    tempObj.updateMatrix();
                    mountains[2].push(tempObj.matrix.clone());
                    
                    // Snow
                    tempObj.scale.set(0.35 * scale, 0.4 * scale, 0.35 * scale);
                    tempObj.position.copy(mPos).add(mNormal.clone().multiplyScalar(2.2 * scale));
                    tempObj.updateMatrix();
                    mountains[3].push(tempObj.matrix.clone());
                } else if (terrain === "grass" || terrain === "forest") {
                    // Grass blades para textura de pasto
                    const bladeCount = terrain === "forest" ? 0 : 4 + Math.floor(seededRandom(x * 50 + y) * 4);
                    for (let b = 0; b < bladeCount; b++) {
                        const bSeed = x * 500 + y * 10 + b;
                        const ox = (seededRandom(bSeed) - 0.5) * 0.8;
                        const oy = (seededRandom(bSeed + 1) - 0.5) * 0.8;
                        const gPos = getSphericalPosition(x + ox / size * 20, y + oy / size * 20, size, 0.08);
                        const gNormal = gPos.clone().normalize();
                        const gQuat = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), gNormal);
                        
                        tempObj.position.copy(gPos);
                        tempObj.quaternion.copy(gQuat);
                        tempObj.scale.set(1, 0.5 + seededRandom(bSeed + 2) * 0.5, 1);
                        tempObj.updateMatrix();
                        grassBlades.push(tempObj.matrix.clone());
                    }
                }
            });
        });
        return { trees, mountains, grassBlades };
    }, [mapa]);

    // Crear materiales basados en texturas (si existen)
    const trunkMat = useMemo(() => new THREE.MeshStandardMaterial({ map: textures?.bark || undefined, color: textures?.bark ? undefined : "#5D4037", roughness: 0.95, metalness: 0 }), [textures?.bark]);
    const foliage1Mat = useMemo(() => new THREE.MeshStandardMaterial({ map: textures?.grass || undefined, color: textures?.grass ? undefined : "#2E7D32", roughness: 0.85, metalness: 0, flatShading: true }), [textures?.grass]);
    const foliage2Mat = useMemo(() => new THREE.MeshStandardMaterial({ map: textures?.grass || undefined, color: textures?.grass ? undefined : "#388E3C", roughness: 0.85, metalness: 0, flatShading: true }), [textures?.grass]);

    const mountainBaseMat = useMemo(() => new THREE.MeshStandardMaterial({ map: textures?.rock || undefined, color: textures?.rock ? undefined : "#607D8B", roughness: 0.9, metalness: 0.05, flatShading: true }), [textures?.rock]);
    const mountainMidMat = useMemo(() => new THREE.MeshStandardMaterial({ map: textures?.rock || undefined, color: textures?.rock ? undefined : "#78909C", roughness: 0.85, metalness: 0.05, flatShading: true }), [textures?.rock]);
    const mountainPeakMat = useMemo(() => new THREE.MeshStandardMaterial({ map: textures?.rock || undefined, color: textures?.rock ? undefined : "#546E7A", roughness: 0.8, metalness: 0.1, flatShading: true }), [textures?.rock]);
    const snowMat = useMemo(() => new THREE.MeshStandardMaterial({ map: textures?.snow || undefined, color: textures?.snow ? undefined : "#FAFAFA", roughness: 0.4, metalness: 0.1, flatShading: true }), [textures?.snow]);

    const grassMat = useMemo(() => new THREE.MeshStandardMaterial({ map: textures?.grass || undefined, color: textures?.grass ? undefined : "#4CAF50", side: THREE.DoubleSide }), [textures?.grass]);

    useEffect(() => {
        return () => {
            [trunkMat, foliage1Mat, foliage2Mat, mountainBaseMat, mountainMidMat, mountainPeakMat, snowMat, grassMat].forEach((m) => { try { m.dispose(); } catch (e) { /* ignore */ } });
        };
    }, [trunkMat, foliage1Mat, foliage2Mat, mountainBaseMat, mountainMidMat, mountainPeakMat, snowMat, grassMat]);

    useEffect(() => {
        treeRefs.forEach((ref, idx) => {
            const mesh = ref.current;
            if (mesh && data.trees[idx]) {
                data.trees[idx].forEach((m, i) => mesh.setMatrixAt(i, m));
                mesh.instanceMatrix.needsUpdate = true;
            }
        });
        mountainRefs.forEach((ref, idx) => {
            const mesh = ref.current;
            if (mesh && data.mountains[idx]) {
                data.mountains[idx].forEach((m, i) => mesh.setMatrixAt(i, m));
                mesh.instanceMatrix.needsUpdate = true;
            }
        });
        if (grassRef.current && data.grassBlades.length > 0) {
            data.grassBlades.forEach((m, i) => grassRef.current!.setMatrixAt(i, m));
            grassRef.current.instanceMatrix.needsUpdate = true;
        }
    }, [data]);

    return (
        <group>
            <instancedMesh ref={treeRefs[0]} args={[cylinderGeom, trunkMat, data.trees[0].length]} />
            <instancedMesh ref={treeRefs[1]} args={[coneGeom, foliage1Mat, data.trees[1].length]} />
            <instancedMesh ref={treeRefs[2]} args={[coneGeom, foliage2Mat, data.trees[2].length]} />
            <instancedMesh ref={mountainRefs[0]} args={[coneGeom, mountainBaseMat, data.mountains[0].length]} />
            <instancedMesh ref={mountainRefs[1]} args={[coneGeom, mountainMidMat, data.mountains[1].length]} />
            <instancedMesh ref={mountainRefs[2]} args={[coneGeom, mountainPeakMat, data.mountains[2].length]} />
            <instancedMesh ref={mountainRefs[3]} args={[coneGeom, snowMat, data.mountains[3].length]} />
            <InstancedMeshGrassBlade ref={grassRef} geometry={grassBladeGeom} material={grassMat} count={data.grassBlades.length} />
        </group>
    );
}

// GRANJA - Casa realista
function Farm({ position, rotation }: any) {
    return (
        <group position={position} quaternion={rotation}>
            {/* Base de tierra */}
            <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.02, 0]} receiveShadow>
                <planeGeometry args={[1.0, 1.0]} />
                <meshStandardMaterial color="#5D4037" roughness={1} />
            </mesh>
            {/* Cuerpo de la casa */}
            <mesh position={[0, 0.35, 0]} castShadow>
                <boxGeometry args={[0.7, 0.6, 0.6]} />
                <primitive object={sharedMaterials.houseWall} attach="material" />
            </mesh>
            {/* Techo */}
            <mesh position={[0, 0.75, 0]} rotation={[0, Math.PI / 4, 0]} castShadow>
                <coneGeometry args={[0.55, 0.35, 4]} />
                <primitive object={sharedMaterials.houseRoof} attach="material" />
            </mesh>
            {/* Puerta */}
            <mesh position={[0, 0.2, 0.31]} castShadow>
                <boxGeometry args={[0.18, 0.35, 0.02]} />
                <primitive object={sharedMaterials.houseDoor} attach="material" />
            </mesh>
            {/* Ventanas */}
            <mesh position={[-0.2, 0.4, 0.31]} castShadow>
                <boxGeometry args={[0.15, 0.15, 0.02]} />
                <primitive object={sharedMaterials.houseWindow} attach="material" />
            </mesh>
            <mesh position={[0.2, 0.4, 0.31]} castShadow>
                <boxGeometry args={[0.15, 0.15, 0.02]} />
                <primitive object={sharedMaterials.houseWindow} attach="material" />
            </mesh>
        </group>
    );
}

// Recursos 3D: eliminado — la visualización de recursos se gestiona desde la vista 2D.

// Edificio genérico para la vista 3D
function Building({ position, rotation, color }: any) {
    return (
        <group position={position} quaternion={rotation}>
            <mesh position={[0, 0.4, 0]} castShadow>
                <boxGeometry args={[0.5, 0.8, 0.5]} />
                <meshStandardMaterial color={color} roughness={0.7} metalness={0.2} />
            </mesh>
            <mesh position={[0, 0.85, 0]}>
                <boxGeometry args={[0.55, 0.1, 0.55]} />
                <meshStandardMaterial color="#37474F" />
            </mesh>
        </group>
    );
}

// Superficie del Planeta - REALISTA CON RUIDO FRACTAL Y ATMÓSFERA
function PlanetSurface({ mapa }: { mapa: any[][] }) {
    const planetRef = useRef<THREE.Mesh>(null);
    const size = mapa.length;

    const { geometry, waterGeometry, atmosphereGeom } = useMemo(() => {
        const g = new THREE.SphereGeometry(PLANET_RADIUS, 180, 90); // Alta resolución
        const wg = new THREE.SphereGeometry(PLANET_RADIUS - 0.08, 120, 60); 
        const ag = new THREE.SphereGeometry(PLANET_RADIUS * 1.08, 60, 30); // Atmósfera
        
        const pos = g.attributes.position;
        const colorArray = new Float32Array(pos.count * 3);

        const getTileData = (gx: number, gy: number) => {
            const x = ((Math.floor(gx) % size) + size) % size;
            const y = Math.max(0, Math.min(size - 1, Math.floor(gy)));
            const tile = mapa[x]?.[y] || { terrain: "water" };
            const type = (tile.terrain || "grass").toLowerCase();
            const colorKey = type.includes("moun") || type.includes("mont") ? "mountain" : type;
            const c = new THREE.Color(terrainColors[colorKey]?.base || terrainColors.grass.base);
            
            let h = type === "water" ? -0.25 : 0.08;
            if (colorKey === "mountain") h = 0.55;
            else if (type === "forest") h = 0.15;
            else if (type === "desert") h = 0.05;

            return { color: c, height: h, type };
        };

        for (let i = 0; i < pos.count; i++) {
            const v = new THREE.Vector3().fromBufferAttribute(pos, i);
            const n = v.clone().normalize();
            
            // Mapeo UV esférico corregido para evitar distorsión en polos
            const u = 0.5 + (Math.atan2(n.z, n.x) / (2 * Math.PI));
            const ve = 0.5 + (Math.asin(n.y) / Math.PI);

            const fx = u * size;
            const fy = ve * size;
            const x1 = Math.floor(fx);
            const y1 = Math.floor(fy);
            const tx = fx - x1;
            const ty = fy - y1;

            const d11 = getTileData(x1, y1);
            const d21 = getTileData(x1 + 1, y1);
            const d12 = getTileData(x1, y1 + 1);
            const d22 = getTileData(x1 + 1, y1 + 1);

            // Interpolación de altura base
            let baseH = (d11.height * (1 - tx) * (1 - ty)) + (d21.height * tx * (1 - ty)) + (d12.height * (1 - tx) * ty) + (d22.height * tx * ty);
            
            // Añadir RUIDO FRACTAL para realismo (accidentes geográficos)
            const detail = noise3D(n, 12) * 0.15 + noise3D(n, 35) * 0.04;
            const ruggedH = baseH + (baseH > 0 ? detail : detail * 0.2);

            // Interpolación de color
            const r = (d11.color.r * (1 - tx) * (1 - ty)) + (d21.color.r * tx * (1 - ty)) + (d12.color.r * (1 - tx) * ty) + (d22.color.r * tx * ty);
            const ge = (d11.color.g * (1 - tx) * (1 - ty)) + (d21.color.g * tx * (1 - ty)) + (d12.color.g * (1 - tx) * ty) + (d22.color.g * tx * ty);
            const b = (d11.color.b * (1 - tx) * (1 - ty)) + (d21.color.b * tx * (1 - ty)) + (d12.color.b * (1 - tx) * ty) + (d22.color.b * tx * ty);

            // Variación de color natural basada en el ruido
            const colorVariation = 1.0 + detail * 0.8;
            colorArray[i * 3]     = r * colorVariation;
            colorArray[i * 3 + 1] = ge * colorVariation;
            colorArray[i * 3 + 2] = b * colorVariation;

            v.copy(n).multiplyScalar(PLANET_RADIUS + ruggedH);
            pos.setXYZ(i, v.x, v.y, v.z);
        }

        g.setAttribute("color", new THREE.Float32BufferAttribute(colorArray, 3));
        g.computeVertexNormals();
        return { geometry: g, waterGeometry: wg, atmosphereGeom: ag };
    }, [mapa]);

    useEffect(() => {
        return () => { 
            [geometry, waterGeometry, atmosphereGeom].forEach(g => g?.dispose());
        };
    }, [geometry, waterGeometry, atmosphereGeom]);

    return (
        <group>
            {/* Atmósfera suave */}
            <mesh geometry={atmosphereGeom}>
                <meshStandardMaterial 
                    color="#81D4FA" 
                    transparent 
                    opacity={0.12} 
                    side={THREE.BackSide}
                    blending={THREE.AdditiveBlending}
                />
            </mesh>

            {/* Océano con brillo */}
            <mesh geometry={waterGeometry}>
                <meshStandardMaterial 
                    color="#01579B" 
                    roughness={0.05} 
                    metalness={0.9} 
                    transparent 
                    opacity={0.85}
                    emissive="#039BE5"
                    emissiveIntensity={0.3}
                />
            </mesh>
            
            {/* Corteza con relieve fractal */}
            <mesh ref={planetRef} geometry={geometry} receiveShadow castShadow>
                <meshStandardMaterial 
                    vertexColors 
                    flatShading={false} 
                    roughness={0.85} 
                    metalness={0.02} 
                />
            </mesh>
        </group>
    );
}

// Decoraciones 3D
const PlanetDecorations = React.memo(function PlanetDecorations({ x, y, tile, size }: any) {
    const basePos = useMemo(() => getSphericalPosition(x, y, size, 0.05), [x, y, size]);
    const rotation = useMemo(() => {
        const up = new THREE.Vector3(0, 1, 0);
        const normal = basePos.clone().normalize();
        const quaternion = new THREE.Quaternion();
        quaternion.setFromUnitVectors(up, normal);
        return quaternion;
    }, [basePos]);

    const buildings = useMemo(() => {
        if (!tile.buildings) return [];
        const typeToColor: Record<string, string> = {
            "Hospital": "#ef4444", "Centro de Recarga": "#fbbf24",
            "Centro de Descanso": "#8b5cf6", "Centro Comunitario": "#ec4899",
            "Comisaría": "#3b82f6", "Universidad": "#10b981"
        };
        return tile.buildings
            .filter((b: any) => b.tipo !== "Granja")
            .map((b: any) => ({
                color: typeToColor[b.tipo] || tile.ownerColor || "#3b82f6"
            }));
    }, [tile.buildings, tile.ownerColor]);

    return (
        <group>
            {tile.buildings?.some((b: any) => b.tipo === "Granja") && (
                <Farm position={basePos} rotation={rotation} />
            )}
            {buildings.map((b: any, idx: number) => (
                <Building key={`bld-${idx}`} position={basePos} rotation={rotation} color={b.color} />
            ))}
            {/* recursos: el mapa usa `resource` con {type, amount} */}
            {/* Recursos 3D deshabilitados (gestión de recursos en la vista 2D) */}
        </group>
    );
});

// AGENTE CON ROSTRO - Más grande y realista
function Agent3D({ agent, isSelected }: any) {
    const bubble = useGameStore((s) => s.speechBubbles?.[agent.id]);
    const mapa = useGameStore((s) => s.mapa);
    const groupRef = useRef<THREE.Group>(null);
    const bodyRef = useRef<THREE.Group>(null);

    const size = (mapa?.length) || 20;
    const agentColor = agent.color || "#EF5350";
    const targetPos = useMemo(() => getSphericalPosition(agent.x, agent.y, size, 0.5), [agent.x, agent.y, size]);

    // Parámetros de bobbing/animación determinísticos por agente
    const bobParams = useMemo(() => {
        const idHash = String(agent.id).split("").reduce((h, c) => ((h << 5) - h) + c.charCodeAt(0), 0) || Math.floor(Math.random() * 10000);
        const r = (n: number) => seededRandom(idHash + n);
        return {
            bobAmplitude: 0.02 + r(1) * 0.06,
            bobFrequency: 3 + r(2) * 5,
            bobPhase: r(3) * Math.PI * 2,
            rotAmplitude: 0.03 + r(4) * 0.12,
            rotSpeed: 0.5 + r(5) * 2.0,
            moveLerp: 3 + r(6) * 8,
            orientLerp: 4 + r(7) * 8,
        };
    }, [agent.id]);

    useFrame((state, delta) => {
        if (groupRef.current) {
            groupRef.current.position.lerp(targetPos, delta * bobParams.moveLerp);
            const normal = groupRef.current.position.clone().normalize();
            const quaternion = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), normal);
            groupRef.current.quaternion.slerp(quaternion, delta * bobParams.orientLerp);

            if (bodyRef.current) {
                const t = state.clock.elapsedTime;
                // Movimiento flotante compuesto (dos ondas para irregularidad)
                const mainBob = Math.sin(t * bobParams.bobFrequency + bobParams.bobPhase);
                const secondaryBob = Math.sin(t * (bobParams.bobFrequency * 1.5) + bobParams.bobPhase * 0.5) * 0.3;
                
                bodyRef.current.position.y = 0.25 + (mainBob + secondaryBob) * bobParams.bobAmplitude;
                
                // Balanceo lateral (sway) para mayor naturalidad
                const swayX = Math.sin(t * (bobParams.rotSpeed * 0.7) + bobParams.bobPhase) * 0.05;
                const swayZ = Math.cos(t * (bobParams.rotSpeed * 0.8) + bobParams.bobPhase * 1.2) * 0.05;
                bodyRef.current.position.x = swayX;
                bodyRef.current.position.z = swayZ;

                bodyRef.current.rotation.y = Math.sin(t * bobParams.rotSpeed + bobParams.bobPhase) * bobParams.rotAmplitude;
                // Inclinación leve según el movimiento
                bodyRef.current.rotation.z = swayX * 0.5;
                bodyRef.current.rotation.x = swayZ * 0.5;
            }
        }
    });

    const agentSeed = useMemo(() => String(agent.id).split("").reduce((h, c) => ((h << 5) - h) + c.charCodeAt(0), 0) || 0, [agent.id]);
    const getAgentValue = (offset: number) => (Math.sin(agentSeed + offset) * 10000) % 1;

    const skinTones = ["#FFDBAC", "#F1C27D", "#E0AC69", "#8D5524", "#C68642"];
    const hairColors = ["#000000", "#4B2C20", "#8D4E33", "#B1B1B1", "#D6C4C2", "#E4B877"];
    
    const skinColor = useMemo(() => skinTones[Math.abs(Math.floor(getAgentValue(10) * skinTones.length))], [agentSeed]);
    const hairColor = useMemo(() => hairColors[Math.abs(Math.floor(getAgentValue(20) * hairColors.length))], [agentSeed]);
    const hairStyle = useMemo(() => Math.abs(Math.floor(getAgentValue(30) * 4)), [agentSeed]);

    const showBubble = isSelected || (bubble && (Date.now() - bubble.timestamp < 15000));

    return (
        <group ref={groupRef}>
            <group ref={bodyRef}>
                {/* Torso Moderno Flotante */}
                <mesh position={[0, 0.45, 0]} castShadow>
                    <cylinderGeometry args={[0.2, 0.2, 0.4, 12]} />
                    <meshStandardMaterial color={agentColor} />
                </mesh>

                {/* Cabeza Redondeada */}
                <mesh position={[0, 0.8, 0]} castShadow>
                    <sphereGeometry args={[0.22, 16, 16]} />
                    <meshStandardMaterial color={skinColor} roughness={0.6} />
                </mesh>

                {/* Brazos Modernos */}
                <mesh position={[-0.26, 0.45, 0]} castShadow>
                    <boxGeometry args={[0.08, 0.3, 0.08]} />
                    <meshStandardMaterial color={skinColor} />
                </mesh>
                <mesh position={[0.26, 0.45, 0]} castShadow>
                    <boxGeometry args={[0.08, 0.3, 0.08]} />
                    <meshStandardMaterial color={skinColor} />
                </mesh>

                {/* PEINADOS 3D DIVERSIFICADOS */}
                <group position={[0, 0.8, 0]}>
                    {hairStyle === 0 && ( // Modern Short
                        <mesh position={[0, 0.18, 0]} castShadow>
                            <sphereGeometry args={[0.18, 12, 12, 0, Math.PI * 2, 0, Math.PI / 2]} />
                            <meshStandardMaterial color={hairColor} />
                        </mesh>
                    )}
                    {hairStyle === 1 && ( // Side Quiff / Wave
                        <mesh position={[0.05, 0.2, 0]} rotation={[0, 0, -0.4]} castShadow>
                            <sphereGeometry args={[0.2, 12, 12]} />
                            <meshStandardMaterial color={hairColor} />
                        </mesh>
                    )}
                    {hairStyle === 2 && ( // Long Hair (Back)
                        <group>
                            <mesh position={[0, 0.18, 0]} castShadow>
                                <sphereGeometry args={[0.18, 12, 12, 0, Math.PI * 2, 0, Math.PI / 2]} />
                                <meshStandardMaterial color={hairColor} />
                            </mesh>
                            <mesh position={[0, -0.1, -0.15]} castShadow>
                                <boxGeometry args={[0.3, 0.4, 0.1]} />
                                <meshStandardMaterial color={hairColor} />
                            </mesh>
                        </group>
                    )}
                    {hairStyle === 3 && ( // Top Bun / Knot
                        <group>
                            <mesh position={[0, 0.18, 0]} castShadow>
                                <sphereGeometry args={[0.18, 12, 12, 0, Math.PI * 2, 0, Math.PI / 2]} />
                                <meshStandardMaterial color={hairColor} />
                            </mesh>
                            <mesh position={[0, 0.25, 0]} castShadow>
                                <sphereGeometry args={[0.1, 8, 8]} />
                                <meshStandardMaterial color={hairColor} />
                            </mesh>
                        </group>
                    )}
                </group>
                
                {/* Ojos Modernos */}
                <mesh position={[-0.08, 0.82, 0.18]} castShadow>
                    <sphereGeometry args={[0.04, 8, 8]} />
                    <meshStandardMaterial color="#000000" />
                </mesh>
                <mesh position={[0.08, 0.82, 0.18]} castShadow>
                    <sphereGeometry args={[0.04, 8, 8]} />
                    <meshStandardMaterial color="#000000" />
                </mesh>
                
                {isSelected && (
                    <mesh position={[0, -0.05, 0]} rotation={[-Math.PI / 2, 0, 0]}>
                        <torusGeometry args={[0.5, 0.03, 8, 32]} />
                        <meshStandardMaterial color="#4fc3f7" emissive="#4fc3f7" emissiveIntensity={1} transparent opacity={0.8} />
                    </mesh>
                )}
            </group>

            {isSelected && (
                <Text position={[0, 1.5, 0]} fontSize={0.35} color="white" fontWeight="bold" outlineWidth={0.04} outlineColor="black">
                    {agent.identidad?.nombre?.substring(0, 10) || agent.id}
                </Text>
            )}

            {showBubble && bubble && (
                <Html position={[0, 2.0, 0]} center transform={false} occlude={false}>
                    <div style={{
                        background: "white",
                        border: "3px solid #424242",
                        padding: "12px 20px",
                        borderRadius: "10px",
                        boxShadow: "4px 4px 0px #000",
                        minWidth: "360px",
                        maxWidth: "840px",
                        pointerEvents: "none",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        textAlign: "center",
                    }}>
                        <p style={{
                            fontSize: "18px",
                            color: "black",
                            fontFamily: "monospace",
                            fontWeight: "700",
                            lineHeight: "1.3",
                            margin: 0,
                            wordBreak: "break-word",
                            whiteSpace: "normal"
                        }}>
                            {replaceIdsWithNames(bubble.text, useGameStore.getState().agents)}
                        </p>
                    </div>
                </Html>
            )}
        </group>
    );
}

// Enlaces curvos
function RelationshipLines({ showLinks }: { showLinks: boolean }) {
    const relationships = useGameStore((s) => s.relationships || []);
    const agents = useGameStore((s) => s.agents);
    const mapa = useGameStore((s) => s.mapa);

    const size = (mapa?.length) || 20;

    const agentPositions = useMemo(() => {
        const pos: Record<string, THREE.Vector3> = {};
        agents.forEach((a: any) => {
            pos[a.id] = getSphericalPosition(a.x, a.y, size, 0);
        });
        return pos;
    }, [agents, size]);

    const validLinks = useMemo(() => {
        return (relationships || []).filter((r: any) =>
            agentPositions[r.source] && agentPositions[r.target]
        );
    }, [relationships, agentPositions]);

    if (!showLinks) return null;

    return (
        <group>
            {validLinks.map((r: any, i: number) => {
                const start = agentPositions[r.source];
                const end = agentPositions[r.target];
                const mid = start.clone().add(end).multiplyScalar(0.5).normalize().multiplyScalar(PLANET_RADIUS + 10);

                let color = "#4ade80";
                let opacity = 0.3;
                let width = 1;

                // Estilizado por tipo y fuerza
                const strength = Math.abs(Number(r.strength || 0));
                const base = Math.max(0.6, Math.min(3, strength * 2));
                if (r.type === "enemigo") { color = "#ef4444"; opacity = 0.95; width = Math.max(1.8, base); }
                else if (r.type === "alianza") { color = "#fbbf24"; opacity = 0.9; width = Math.max(1.2, base); }
                else if (r.type === "amigo") { color = "#4ade80"; opacity = 0.75; width = Math.max(1.0, base); }
                else if (r.type === "conocido") { color = "#90A4AE"; opacity = 0.45; width = Math.max(0.6, base * 0.6); }

                return (
                    <QuadraticBezierLine
                        key={`link-${i}`}
                        start={start}
                        end={end}
                        mid={mid}
                        color={color}
                        lineWidth={width}
                        transparent
                        opacity={opacity}
                        dashed={false}
                    />
                );
            })}
        </group>
    );
}

function Planet({ showLinks }: { showLinks: boolean }) {
    const agents = useGameStore((s) => s.agents);
    const mapa = useGameStore((s) => s.mapa);
    const selectedAgentId = useGameStore((s) => s.selectedAgentId);
    const selectAgent = useGameStore((s) => s.selectAgent);
    const civilizaciones = useGameStore((s) => s.civilizaciones);
    const gruposDinamicos = useGameStore((s) => s.gruposDinamicos);
    const planetGroup = useRef<THREE.Group>(null);
    const [userInteracting, setUserInteracting] = useState(false);
    useFrame(() => { if (planetGroup.current && !userInteracting) planetGroup.current.rotation.y += 0.0003; });

    const decorations = useMemo(() => {
        if (!mapa) return null;
        const size = mapa.length;
        return mapa.flatMap((row: any, x: number) =>
            row.map((tile: any, y: number) => {
                const enrichedTile = {
                    ...tile,
                    ownerColor: tile.owner
                        ? (civilizaciones[tile.owner]?.color || gruposDinamicos[tile.owner]?.color || null)
                        : null
                };
                return <PlanetDecorations key={`${x}-${y}`} x={x} y={y} tile={enrichedTile} size={size} />;
            })
        );
    }, [mapa, civilizaciones, gruposDinamicos]);

    return (
        <group ref={planetGroup}>
            {mapa && <PlanetSurface mapa={mapa} />}
            {mapa && <InstancedDecorations mapa={mapa} />}
            {decorations}
            {agents.map((agent: any) => (
                <group key={agent.id} onClick={() => { selectAgent(agent.id); synthesizer.playSelect(); }}>
                    <Agent3D agent={agent} isSelected={agent.id === selectedAgentId} />
                </group>
            ))}
            <RelationshipLines showLinks={showLinks} />
            {/* OrbitControls moved here so we can pause auto-rotation while the user interacts.
                We allow unlimited azimuthal rotation by setting min/max azimuth to infinite. */}
            <OrbitControls
                enableDamping
                dampingFactor={0.05}
                rotateSpeed={0.8}
                minDistance={14}
                maxDistance={55}
                minPolarAngle={0}
                maxPolarAngle={Math.PI}
                minAzimuthAngle={-Infinity}
                maxAzimuthAngle={Infinity}
                enablePan={false}
                onStart={() => setUserInteracting(true)}
                onEnd={() => setUserInteracting(false)}
            />
        </group>
    );
}

const WebGLFallback = () => (
    <div className="w-full h-full flex items-center justify-center bg-black text-white">
        <div className="text-center">
            <h2 className="text-2xl font-bold mb-2">WebGL Not Supported</h2>
            <p>Your browser does not support WebGL, which is required for the 3D view.</p>
        </div>
    </div>
);

const PostProcessing = () => {
    const gl = useThree((state) => state.gl);
    const [ready, setReady] = useState(false);

    useEffect(() => {
        let frame: number;
        let mounted = true;

        const checkGl = () => {
            if (!mounted) return;
            try {
                if (gl && gl.getContext()) {
                    const attributes = gl.getContext().getContextAttributes();
                    if (attributes && attributes.alpha !== undefined) {
                        setReady(true);
                        return;
                    }
                }
            } catch (e) { }
            frame = requestAnimationFrame(checkGl);
        };

        frame = requestAnimationFrame(checkGl);
        return () => { mounted = false; cancelAnimationFrame(frame); };
    }, [gl]);

    // No renderizar post-procesamiento si WebGL no está listo
    if (!ready) return null;

    // Fallback: no usar postprocessing si falla
    try {
        return (
            <EffectComposer multisampling={0} enableNormalPass={false}>
                <Bloom intensity={1.2} luminanceThreshold={0.5} radius={0.8} />
                <Vignette darkness={0.6} />
            </EffectComposer>
        );
    } catch (e) {
        console.warn("PostProcessing no disponible:", e);
        return null;
    }
};

export default function WorldViewport3D() {
    const [showLinks, setShowLinks] = useState(true);
    const [hasWebGL, setHasWebGL] = useState<boolean | null>(null);

    useEffect(() => {
        let mounted = true;
        const checkWebGL = () => {
            try {
                const canvas = document.createElement('canvas');
                const options: any = { alpha: false, antialias: false, powerPreference: 'default' };
                // try to create context using the same options react-three-fiber will request
                const ctx = canvas.getContext('webgl2', options) || canvas.getContext('webgl', options) || canvas.getContext('experimental-webgl', options);
                if (!ctx) return false;
                // release the test context if possible to avoid leaking GPU resources
                try {
                    const loseExt = (ctx as any).getExtension && ((ctx as any).getExtension('WEBGL_lose_context') || (ctx as any).getExtension('WEBGL_lose_context'));
                    if (loseExt && typeof loseExt.loseContext === 'function') {
                        loseExt.loseContext();
                    }
                } catch (e) { /* ignore */ }
                return true;
            } catch (e) {
                return false;
            }
        };
        // run the check on mount (component is client-side because of `use client`)
        const available = checkWebGL();
        if (mounted) setHasWebGL(available);
        return () => { mounted = false; };
    }, []);

    // If WebGL explicitly unavailable, show fallback
    if (hasWebGL === false) {
        return <WebGLFallback />;
    }

    return (
        <div className="w-full h-full relative bg-[#000000]">
            <ErrorBoundary fallback={<WebGLFallback />}>
                <Suspense fallback={
                    <div className="w-full h-full flex items-center justify-center bg-black text-white">
                        Loading 3D View...
                    </div>
                }>
                    {hasWebGL === null ? (
                        <div className="w-full h-full flex items-center justify-center bg-black text-white">
                            Initializing 3D...
                        </div>
                    ) : (
                        <Canvas
                            camera={{ position: [28, 18, 28], fov: 35 }}
                            shadows={false}
                            gl={{ alpha: false, antialias: false, powerPreference: "default" }}
                            onCreated={({ gl }) => {
                                try { gl.setClearColor("#1c2128"); } catch (e) { console.warn('Failed to set clear color', e); }
                            }}
                        >
                            <color attach="background" args={["#1c2128"]} />
                            <ambientLight intensity={1.2} />
                            <directionalLight position={[50, 50, 20]} intensity={1.5} />
                            <pointLight position={[-30, 20, -30]} intensity={0.5} color="#FFFFFF" />
                            <Planet showLinks={showLinks} />
                            <OrbitControls enableDamping minDistance={14} maxDistance={55} />
                        </Canvas>
                    )}

                    <style jsx>{`
                        .glass-panel { background: rgba(0, 0, 0, 0.5); backdrop-filter: blur(50px); }
                    `}</style>
                </Suspense>
            </ErrorBoundary>

            <button
                onClick={() => setShowLinks(!showLinks)}
                className="absolute top-6 right-6 glass-panel p-3 rounded-xl border border-white/10 hover:border-purple-500/50 transition-all duration-300 group z-50"
                title={showLinks ? "Ocultar vínculos" : "Mostrar vínculos"}
            >
                {showLinks ? (
                    <Link className="w-5 h-5 text-purple-400 group-hover:text-purple-300 transition-colors" />
                ) : (
                    <Link2Off className="w-5 h-5 text-gray-500 group-hover:text-gray-400 transition-colors" />
                )}
            </button>
            
        </div>
    );
}
