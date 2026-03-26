"use client";

import { useRef, useMemo, useState, Suspense } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, Text, Stars, Environment, Float, Html, QuadraticBezierLine } from "@react-three/drei";
import useGameStore from "@/store/useGameStore";
import * as THREE from "three";
import { motion } from "framer-motion";
import { EffectComposer, Bloom, Vignette } from "@react-three/postprocessing";
import { synthesizer } from "@/utils/SoundSynthesizer";
import ErrorBoundary from "./ErrorBoundary";
import { Link, Link2Off } from "lucide-react";

const PLANET_RADIUS = 10;
// El tamaño base inicial es 20, pero se ajustará dinámicamente según el mapa recibido.

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

// MONTAÑA DETALLADA (con rocas y glaciar)
function Mountain({ position, rotation, scale = 1 }: any) {
    return (
        <group position={position} quaternion={rotation} scale={[scale, scale, scale]}>
            {/* Base rocosa */}
            <mesh position={[0, 0.15, 0]} castShadow>
                <coneGeometry args={[0.6, 0.5, 6]} />
                <meshStandardMaterial color="#3f3f46" flatShading roughness={1} />
            </mesh>
            {/* Cuerpo principal */}
            <mesh position={[0, 0.45, 0]} castShadow>
                <coneGeometry args={[0.45, 0.7, 5]} />
                <meshStandardMaterial color="#52525b" flatShading roughness={0.9} />
            </mesh>
            {/* Cumbre nevada */}
            <mesh position={[0, 0.75, 0]}>
                <coneGeometry args={[0.25, 0.4, 5]} />
                <meshStandardMaterial color="#fafafa" flatShading emissive="#ffffff" emissiveIntensity={0.3} />
            </mesh>
            {/* Rocas adicionales */}
            <mesh position={[0.3, 0.05, 0]} castShadow>
                <dodecahedronGeometry args={[0.15]} />
                <meshStandardMaterial color="#27272a" roughness={1} />
            </mesh>
            <mesh position={[-0.25, 0.05, 0.2]} castShadow>
                <dodecahedronGeometry args={[0.12]} />
                <meshStandardMaterial color="#27272a" roughness={1} />
            </mesh>
        </group>
    );
}

// ÁRBOL DETALLADO (Pino con capas)
function PineTree({ position, rotation }: any) {
    return (
        <group position={position} quaternion={rotation}>
            {/* Tronco */}
            <mesh position={[0, 0.15, 0]} castShadow>
                <cylinderGeometry args={[0.04, 0.06, 0.3, 8]} />
                <meshStandardMaterial color="#44403c" roughness={1} />
            </mesh>
            {/* Capas de follaje */}
            <mesh position={[0, 0.35, 0]} castShadow>
                <coneGeometry args={[0.25, 0.35, 8]} />
                <meshStandardMaterial color="#14532d" />
            </mesh>
            <mesh position={[0, 0.55, 0]} castShadow>
                <coneGeometry args={[0.2, 0.3, 8]} />
                <meshStandardMaterial color="#166534" />
            </mesh>
            <mesh position={[0, 0.72, 0]} castShadow>
                <coneGeometry args={[0.15, 0.25, 8]} />
                <meshStandardMaterial color="#15803d" />
            </mesh>
        </group>
    );
}

// GRANJA COMPLETA (con granero, cultivos y cerca)
function Farm({ position, rotation }: any) {
    return (
        <group position={position} quaternion={rotation}>
            {/* Suelo arado */}
            <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.01, 0]}>
                <planeGeometry args={[0.7, 0.7]} />
                <meshStandardMaterial color="#78350f" roughness={1} />
            </mesh>
            {/* Surcos de cultivo */}
            {[...Array(5)].map((_, i) => (
                <mesh key={`surco-${i}`} position={[-0.25 + i * 0.12, 0.02, 0]}>
                    <boxGeometry args={[0.08, 0.01, 0.6]} />
                    <meshStandardMaterial color="#451a03" />
                </mesh>
            ))}
            {/* Plantas */}
            {[...Array(12)].map((_, i) => (
                <mesh key={`plant-${i}`} position={[(i % 4 - 1.5) * 0.15, 0.06, (Math.floor(i / 4) - 1) * 0.15]}>
                    <boxGeometry args={[0.04, 0.12, 0.04]} />
                    <meshStandardMaterial color="#65a30d" />
                </mesh>
            ))}
            {/* Granero */}
            <group position={[0.35, 0.15, 0.35]}>
                <mesh castShadow>
                    <boxGeometry args={[0.25, 0.3, 0.2]} />
                    <meshStandardMaterial color="#7c2d12" />
                </mesh>
                <mesh position={[0, 0.2, 0]}>
                    <coneGeometry args={[0.18, 0.15, 4]} />
                    <meshStandardMaterial color="#991b1b" />
                </mesh>
            </group>
            {/* Cerca */}
            {[...Array(8)].map((_, i) => {
                const angle = (i / 8) * Math.PI * 2;
                return (
                    <mesh key={`fence-${i}`} position={[Math.cos(angle) * 0.4, 0.08, Math.sin(angle) * 0.4]}>
                        <boxGeometry args={[0.02, 0.16, 0.02]} />
                        <meshStandardMaterial color="#57534e" />
                    </mesh>
                );
            })}
        </group>
    );
}

// RECURSOS DIFERENCIADOS
function Resource({ position, type }: any) {
    const configs: any = {
        gold: { color: "#fbbf24", emissive: "#fbbf24", intensity: 3, size: 0.14 },
        crystal: { color: "#a855f7", emissive: "#a855f7", intensity: 2.5, size: 0.12 },
        food: { color: "#84cc16", emissive: "#84cc16", intensity: 2, size: 0.1 }
    };
    const config = configs[type] || configs.crystal;

    return (
        <Float speed={4} rotationIntensity={1} floatIntensity={0.5} position={position}>
            <mesh castShadow>
                <octahedronGeometry args={[config.size]} />
                <meshStandardMaterial
                    color={config.color}
                    emissive={config.emissive}
                    emissiveIntensity={config.intensity}
                    metalness={0.8}
                    roughness={0.2}
                />
            </mesh>
            <pointLight distance={2} intensity={1} color={config.color} />
        </Float>
    );
}

// EDIFICIO GENÉRICO
function Building({ position, rotation, color }: any) {
    return (
        <group position={position} quaternion={rotation}>
            <mesh castShadow>
                <boxGeometry args={[0.3, 0.4, 0.3]} />
                <meshStandardMaterial color={color} metalness={0.3} roughness={0.7} />
            </mesh>
            <mesh position={[0, 0.3, 0]}>
                <coneGeometry args={[0.2, 0.2, 4]} />
                <meshStandardMaterial color={color} />
            </mesh>
            <pointLight position={[0, 0.5, 0]} distance={3} intensity={1} color={color} />
        </group>
    );
}

// Superficie del Planeta con Textura Continua y Realista
function PlanetSurface({ mapa }: { mapa: any[][] }) {
    const { geometry } = useMemo(() => {
        const g = new THREE.SphereGeometry(PLANET_RADIUS, 160, 160);
        const pos = g.attributes.position;
        const cols = new Float32Array(pos.count * 3);

        const size = mapa.length;

        // Función de ruido multicapa mejorada
        const noise = (x: number, y: number) => {
            return Math.sin(x * 10.5) * Math.cos(y * 8.3) * 0.5 +
                Math.sin(x * 23.1) * Math.cos(y * 19.7) * 0.25 +
                Math.sin(x * 50.2) * Math.cos(y * 43.8) * 0.125 +
                Math.sin(x * 103.7) * Math.cos(y * 87.2) * 0.0625;
        };

        const biomeCols: any = {
            mountain: { base: new THREE.Color("#374151"), variation: 0.15 },
            forest: { base: new THREE.Color("#052e16"), variation: 0.2 },
            desert: { base: new THREE.Color("#b45309"), variation: 0.12 },
            water: { base: new THREE.Color("#0c4a6e"), variation: 0.08 },
            grass: { base: new THREE.Color("#14532d"), variation: 0.18 }
        };

        // Función para obtener tile con wrapping
        const getTile = (gx: number, gy: number) => {
            const x = ((gx % size) + size) % size;
            const y = Math.max(0, Math.min(size - 1, gy));
            return mapa[x]?.[y] || { terrain: "water" };
        };

        // Interpolación bilinear de colores entre tiles
        const getInterpolatedColor = (u: number, v: number) => {
            const gx = u * size;
            const gy = v * size;

            const x0 = Math.floor(gx);
            const y0 = Math.floor(gy);
            const x1 = x0 + 1;
            const y1 = y0 + 1;

            const fx = gx - x0;
            const fy = gy - y0;

            // Obtener los 4 tiles vecinos
            const t00 = getTile(x0, y0);
            const t10 = getTile(x1, y0);
            const t01 = getTile(x0, y1);
            const t11 = getTile(x1, y1);

            // Obtener colores base
            const c00 = biomeCols[t00.terrain]?.base || biomeCols.grass.base;
            const c10 = biomeCols[t10.terrain]?.base || biomeCols.grass.base;
            const c01 = biomeCols[t01.terrain]?.base || biomeCols.grass.base;
            const c11 = biomeCols[t11.terrain]?.base || biomeCols.grass.base;

            // Interpolación bilinear
            const c0 = c00.clone().lerp(c10, fx);
            const c1 = c01.clone().lerp(c11, fx);
            const finalColor = c0.lerp(c1, fy);

            // Variación promedio
            const avgVariation = (
                (biomeCols[t00.terrain]?.variation || 0.15) * (1 - fx) * (1 - fy) +
                (biomeCols[t10.terrain]?.variation || 0.15) * fx * (1 - fy) +
                (biomeCols[t01.terrain]?.variation || 0.15) * (1 - fx) * fy +
                (biomeCols[t11.terrain]?.variation || 0.15) * fx * fy
            );

            return { color: finalColor, variation: avgVariation };
        };

        const v = new THREE.Vector3();
        for (let i = 0; i < pos.count; i++) {
            v.fromBufferAttribute(pos, i);
            const u = 0.5 + (Math.atan2(v.z, v.x) / (2 * Math.PI));
            const ve = 0.5 + (Math.asin(v.y / PLANET_RADIUS) / Math.PI);

            // Obtener color interpolado
            const { color, variation } = getInterpolatedColor(u, ve);

            // Aplicar variación con ruido
            const noiseVal = noise(u * 50, ve * 50);
            const colorVariation = 1 + noiseVal * variation;
            const finalColor = color.clone().multiplyScalar(colorVariation);

            cols[i * 3] = Math.min(1, Math.max(0, finalColor.r));
            cols[i * 3 + 1] = Math.min(1, Math.max(0, finalColor.g));
            cols[i * 3 + 2] = Math.min(1, Math.max(0, finalColor.b));

            // Altura suave basada en el tile central
            const gx = Math.floor(u * size) % size;
            const gy = Math.floor(ve * size);
            const tile = getTile(gx, gy);

            let h = tile.terrain === "water" ? -0.2 : 0.05;
            h += noiseVal * 0.1; // Micro-relieve aumentado

            v.normalize().multiplyScalar(PLANET_RADIUS + h);
            pos.setXYZ(i, v.x, v.y, v.z);
        }

        g.setAttribute("color", new THREE.BufferAttribute(cols, 3));
        g.computeVertexNormals();
        return { geometry: g };
    }, [mapa]);

    return (
        <group>
            {/* Superficie principal con textura continua */}
            <mesh geometry={geometry} receiveShadow castShadow>
                <meshStandardMaterial
                    vertexColors
                    roughness={0.82}
                    metalness={0.04}
                    envMapIntensity={0.7}
                />
            </mesh>
            {/* Capa de agua con reflejos */}
            <mesh>
                <sphereGeometry args={[PLANET_RADIUS - 0.05, 96, 96]} />
                <meshStandardMaterial
                    color="#0284c7"
                    transparent
                    opacity={0.65}
                    metalness={0.96}
                    roughness={0.04}
                    envMapIntensity={1.6}
                />
            </mesh>
            {/* Atmósfera sutil */}
            <mesh scale={[1.02, 1.02, 1.02]}>
                <sphereGeometry args={[PLANET_RADIUS, 64, 64]} />
                <meshStandardMaterial
                    color="#7c4dff"
                    transparent
                    opacity={0.06}
                    side={THREE.BackSide}
                    emissive="#7c4dff"
                    emissiveIntensity={0.6}
                />
            </mesh>
        </group>
    );
}

// Decoraciones 3D con Orientación Corregida
function PlanetDecorations({ x, y, tile }: any) {
    const { civilizaciones, gruposDinamicos, mapa } = useGameStore();

    const size = useMemo(() => mapa.length, [mapa]);

    // Posición base en la superficie
    const basePos = useMemo(() => getSphericalPosition(x, y, size, 0.05), [x, y, size]);

    // Rotación correcta: el elemento debe mirar "hacia arriba" desde la superficie
    const rotation = useMemo(() => {
        const up = new THREE.Vector3(0, 1, 0);
        const normal = basePos.clone().normalize();
        const quaternion = new THREE.Quaternion();
        quaternion.setFromUnitVectors(up, normal);
        return quaternion;
    }, [basePos]);

    const items = [];

    // MONTAÑAS
    if (tile.terrain === "mountain") {
        items.push(
            <Mountain
                key="mtn"
                position={basePos}
                rotation={rotation}
                scale={0.65 + Math.random() * 0.35}
            />
        );
    }

    // ÁRBOLES
    if (tile.terrain === "forest") {
        for (let i = 0; i < 4; i++) {
            // Offset en coordenadas locales del tile
            const localOffsetX = (Math.random() - 0.5) * 0.4;
            const localOffsetY = (Math.random() - 0.5) * 0.4;

            // Convertir offset local a posición esférica
            const offsetPos = getSphericalPosition(
                x + localOffsetX / size * 20,
                y + localOffsetY / size * 20,
                size,
                0.05
            );

            const offsetRot = useMemo(() => {
                const normal = offsetPos.clone().normalize();
                const quat = new THREE.Quaternion();
                quat.setFromUnitVectors(new THREE.Vector3(0, 1, 0), normal);
                return quat;
            }, [offsetPos]);

            items.push(
                <PineTree
                    key={`t-${i}`}
                    position={offsetPos}
                    rotation={offsetRot}
                />
            );
        }
    }

    // GRANJAS
    if (tile.buildings && tile.buildings.some((b: any) => b.tipo === "Granja")) {
        items.push(
            <Farm
                key="f"
                position={basePos}
                rotation={rotation}
            />
        );
    }

    // EDIFICIOS
    if (tile.buildings) {
        const typeToColor: Record<string, string> = {
            "Hospital": "#ef4444",
            "Centro de Recarga": "#fbbf24",
            "Centro de Descanso": "#8b5cf6",
            "Centro Comunitario": "#ec4899",
            "Comisaría": "#3b82f6",
            "Universidad": "#10b981"
        };

        tile.buildings.forEach((building: any, idx: number) => {
            if (building.tipo !== "Granja") {
                const ownerColor = typeToColor[building.tipo] || civilizaciones[tile.owner]?.color ||
                    gruposDinamicos[tile.owner]?.color || "#3b82f6";
                items.push(
                    <Building
                        key={`bld-${idx}`}
                        position={basePos}
                        rotation={rotation}
                        color={ownerColor}
                    />
                );
            }
        });
    }

    // RECURSOS
    if (tile.resources > 0) {
        const resourceType = tile.terrain === "desert" ? "gold" :
            tile.terrain === "mountain" ? "crystal" : "food";
        const resourcePos = basePos.clone().multiplyScalar(1.06);

        items.push(
            <Resource
                key="res"
                position={[resourcePos.x, resourcePos.y, resourcePos.z]}
                type={resourceType}
            />
        );
    }

    return <group>{items}</group>;
}

// Agente Dron Cibernético Avanzado
function Agent3D({ agent, isSelected }: any) {
    const { civilizaciones, gruposDinamicos, speechBubbles, mapa } = useGameStore();
    const groupRef = useRef<THREE.Group>(null);
    const meshRef = useRef<THREE.Mesh>(null);
    const ring1Ref = useRef<THREE.Mesh>(null);
    const ring2Ref = useRef<THREE.Mesh>(null);

    const bubble = speechBubbles[agent.id];
    const size = useMemo(() => (mapa.length || 20), [mapa]);
    const groupColor = agent.color || "#ffffff";
    const targetPos = useMemo(() => getSphericalPosition(agent.x, agent.y, size, 1.6), [agent.x, agent.y, size]);

    useFrame((state, delta) => {
        if (groupRef.current) {
            // Movimiento suave hacia posición objetivo
            groupRef.current.position.lerp(targetPos, delta * 4);
            const matrix = new THREE.Matrix4();
            matrix.lookAt(groupRef.current.position, new THREE.Vector3(0, 0, 0), new THREE.Vector3(0, 1, 0));
            groupRef.current.quaternion.slerp(new THREE.Quaternion().setFromRotationMatrix(matrix), delta * 5);

            // Animación del Núcleo
            if (meshRef.current) {
                meshRef.current.rotation.y += delta * 0.5;
                meshRef.current.rotation.x += delta * 0.2;
                const pulse = 1 + Math.sin(state.clock.elapsedTime * 4) * 0.05;
                const scale = (isSelected ? 1.5 : 1.0) * pulse;
                meshRef.current.scale.lerp(new THREE.Vector3(scale, scale, scale), delta * 5);
            }

            // Animación de Anillos Orbitales
            if (ring1Ref.current) {
                ring1Ref.current.rotation.z += delta * 1.5;
                ring1Ref.current.rotation.x += delta * 0.5;
            }
            if (ring2Ref.current) {
                ring2Ref.current.rotation.y -= delta * 1.2;
                ring2Ref.current.rotation.z -= delta * 0.8;
            }
        }
    });

    return (
        <group ref={groupRef}>
            <pointLight distance={5} intensity={isSelected ? 3 : 0.8} color={groupColor} />

            {/* Núcleo Central */}
            <mesh ref={meshRef}>
                <dodecahedronGeometry args={[0.35, 0]} />
                <meshStandardMaterial
                    color={groupColor}
                    emissive={groupColor}
                    emissiveIntensity={isSelected ? 1.5 : 0.4}
                    metalness={0.9} // Más metálico
                    roughness={0.3}
                    flatShading
                />
            </mesh>

            {/* Anillo Orbital 1 */}
            <mesh ref={ring1Ref}>
                <torusGeometry args={[0.55, 0.02, 8, 32]} />
                <meshStandardMaterial color="#ffffff" emissive="#ffffff" emissiveIntensity={0.2} metalness={1} roughness={0} />
            </mesh>

            {/* Anillo Orbital 2 */}
            <mesh ref={ring2Ref} rotation={[Math.PI / 2, 0, 0]}>
                <torusGeometry args={[0.48, 0.03, 8, 32]} />
                <meshStandardMaterial color={groupColor} emissive={groupColor} emissiveIntensity={0.5} transparent opacity={0.6} />
            </mesh>

            <Text position={[0, 1.3, 0]} fontSize={0.35} color="white" fontWeight="black" outlineWidth={0.06} outlineColor="black">
                {agent.id.replace('A', '')}
            </Text>

            {/* Burbuja de chat (código original) */}
            {bubble && (
                <Html position={[0, 3.2, 0]} center>
                    <motion.div
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0 }}
                        transition={{ duration: 0.3 }}
                        className="relative"
                    >
                        {/* Contenedor Principal - Sincronizado con 2D */}
                        <div className="bg-[#0a0b10]/95 backdrop-blur-md p-[12px] rounded-[8px] border-[1.5px] border-[#7c4dff] shadow-[0_0_15px_rgba(124,77,255,0.4)] text-white font-mono min-w-[160px] max-w-[280px] relative">
                            {/* Texto del mensaje - Sin comillas, 12px mono */}
                            <div className="text-[12px] leading-tight text-gray-100 whitespace-pre-wrap text-center">
                                {bubble.text}
                            </div>
                        </div>

                        {/* Flecha indicadora abajo - Sincronizada con estilo 2D (10x5px) */}
                        <div
                            className="absolute -bottom-[5px] left-1/2 -translate-x-1/2 w-0 h-0 border-l-[5px] border-l-transparent border-r-[5px] border-r-transparent border-t-[5px] border-t-[#7c4dff]"
                        />
                    </motion.div>
                </Html>
            )}
        </group>
    );
}

// Enlaces curvos sobre la superficie
function RelationshipLines({ showLinks }: { showLinks: boolean }) {
    const { relationships, agents, mapa } = useGameStore();

    const size = useMemo(() => (mapa.length || 20), [mapa]);

    // Mapa rápido de posiciones
    const agentPositions = useMemo(() => {
        const pos: Record<string, THREE.Vector3> = {};
        agents.forEach((a: any) => {
            pos[a.id] = getSphericalPosition(a.x, a.y, size, 0); // En la superficie real
        });
        return pos;
    }, [agents, size]);

    // Filtrar relaciones válidas
    const validLinks = useMemo(() => {
        return relationships.filter((r: any) =>
            agentPositions[r.source] && agentPositions[r.target]
        );
    }, [relationships, agentPositions]);

    if (!showLinks) return null;

    return (
        <group>
            {validLinks.map((r: any, i: number) => {
                const start = agentPositions[r.source];
                const end = agentPositions[r.target];

                // Calcular punto medio elevado para la curva
                const mid = start.clone().add(end).multiplyScalar(0.5).normalize().multiplyScalar(PLANET_RADIUS + 9.5);

                let color = "#4ade80"; // Default Verde
                let opacity = 0.3;
                let width = 1;

                if (r.type === "enemigo") { color = "#ef4444"; opacity = 0.8; width = 2; }
                else if (r.type === "alianza") { color = "#fbbf24"; opacity = 0.9; width = 2.5; }
                else if (r.type === "amigo") { color = "#4ade80"; opacity = 0.5; width = 1.5; }

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
    const { agents, mapa, selectedAgentId, selectAgent } = useGameStore();
    const planetGroup = useRef<THREE.Group>(null);
    useFrame(() => { if (planetGroup.current) planetGroup.current.rotation.y += 0.0003; });

    return (
        <group ref={planetGroup}>
            {mapa && <PlanetSurface mapa={mapa} />}
            {mapa?.flatMap((row: any, x: number) =>
                row.map((tile: any, y: number) => (
                    <PlanetDecorations key={`${x}-${y}`} x={x} y={y} tile={tile} />
                ))
            )}
            {agents.map((agent: any) => (
                <group key={agent.id} onClick={() => { selectAgent(agent.id); synthesizer.playSelect(); }}>
                    <Agent3D agent={agent} isSelected={agent.id === selectedAgentId} />
                </group>
            ))}
            <RelationshipLines showLinks={showLinks} />
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

export default function WorldViewport3D() {
    const [showLinks, setShowLinks] = useState(true);

    return (
        <div className="w-full h-full relative bg-[#000000]">
            <ErrorBoundary fallback={<WebGLFallback />}>
                <Suspense fallback={
                    <div className="w-full h-full flex items-center justify-center bg-black text-white">
                        Loading 3D View...
                    </div>
                }>
                    <Canvas camera={{ position: [30, 20, 30], fov: 38 }} shadows>
                        <Stars radius={160} count={10000} factor={5} fade />
                        <ambientLight intensity={0.7} />
                        <directionalLight position={[60, 50, 40]} intensity={2.5} castShadow shadow-mapSize={[2048, 2048]} />
                        <pointLight position={[-40, -30, -40]} intensity={1.5} color="#7c4dff" />
                        <Planet showLinks={showLinks} />
                        <OrbitControls enableDamping minDistance={15} maxDistance={60} />
                        <Environment preset="city" />
                        <EffectComposer>
                            <Bloom intensity={1.8} luminanceThreshold={0.35} radius={0.85} />
                            <Vignette darkness={0.75} />
                        </EffectComposer>
                    </Canvas>

                    {/* Botón para toggle de vínculos */}
                    <button
                        onClick={() => setShowLinks(!showLinks)}
                        className="absolute top-6 right-6 glass-panel p-3 rounded-xl border border-white/10 hover:border-purple-500/50 transition-all duration-300 group z-10"
                        title={showLinks ? "Ocultar vínculos" : "Mostrar vínculos"}
                    >
                        {showLinks ? (
                            <Link className="w-5 h-5 text-purple-400 group-hover:text-purple-300 transition-colors" />
                        ) : (
                            <Link2Off className="w-5 h-5 text-gray-500 group-hover:text-gray-400 transition-colors" />
                        )}
                    </button>


                    <style jsx>{`
                        .glass-panel { background: rgba(0, 0, 0, 0.5); backdrop-filter: blur(50px); }
                    `}</style>
                </Suspense>
            </ErrorBoundary>
        </div>
    );
}
