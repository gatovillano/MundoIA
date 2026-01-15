"use client";

import { useRef, useMemo, useState, useEffect } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { OrbitControls, Text, Sphere, Box, Stars, Environment, MeshReflectorMaterial, Float, Sparkles, Line } from "@react-three/drei";
import useGameStore from "@/store/useGameStore";
import * as THREE from "three";
import { EffectComposer, Bloom, DepthOfField, Vignette, Scanline, Noise } from "@react-three/postprocessing";
import { Share2 } from "lucide-react";

// Partículas flotantes ambientales
function FloatingParticles() {
    const particlesRef = useRef<THREE.Points>(null);

    const particles = useMemo(() => {
        const positions = new Float32Array(200 * 3);
        for (let i = 0; i < 200; i++) {
            positions[i * 3] = (Math.random() - 0.5) * 30;
            positions[i * 3 + 1] = Math.random() * 15;
            positions[i * 3 + 2] = (Math.random() - 0.5) * 30;
        }
        return positions;
    }, []);

    useFrame((state) => {
        if (particlesRef.current) {
            particlesRef.current.rotation.y = state.clock.elapsedTime * 0.05;
        }
    });

    return (
        <points ref={particlesRef}>
            <bufferGeometry>
                <bufferAttribute
                    attach="attributes-position"
                    args={[particles, 3]}
                />
            </bufferGeometry>
            <pointsMaterial
                size={0.05}
                color="#7c4dff"
                transparent
                opacity={0.6}
                sizeAttenuation
                blending={THREE.AdditiveBlending}
            />
        </points>
    );
}

// Geometría de Montaña
function MountainGeometry({ height, color }: { height: number, color: string }) {
    return (
        <group position={[0, 0, 0]}>
            <mesh position={[0, height / 2, 0]} castShadow>
                <coneGeometry args={[0.5, height, 4]} />
                <meshStandardMaterial color={color} roughness={0.9} />
            </mesh>
            <mesh position={[0.2, height / 3, 0.2]} castShadow>
                <coneGeometry args={[0.3, height / 1.5, 4]} />
                <meshStandardMaterial color={color} roughness={0.9} />
            </mesh>
        </group>
    );
}

// Geometría de Bosque
function ForestGeometry({ height }: { height: number }) {
    return (
        <group position={[0, height, 0]}>
            {[...Array(3)].map((_, i) => (
                <group key={i} position={[Math.sin(i * 2.1) * 0.2, 0, Math.cos(i * 2.1) * 0.2]}>
                    <mesh position={[0, 0.1, 0]} castShadow>
                        <cylinderGeometry args={[0.05, 0.05, 0.2, 8]} />
                        <meshStandardMaterial color="#3e2723" />
                    </mesh>
                    <mesh position={[0, 0.35, 0]} castShadow>
                        <coneGeometry args={[0.2, 0.4, 8]} />
                        <meshStandardMaterial color="#065f46" />
                    </mesh>
                </group>
            ))}
        </group>
    );
}

// Geometría de Edificio Futurista
function BuildingGeometry({ type, color }: { type?: string, color: string }) {
    const isHospital = type === "hospital" || type === "clinica";
    const isEnergy = type === "Centro de Recarga" || type === "Planta Eléctrica";

    return (
        <group>
            {/* Base */}
            <mesh position={[0, 0.2, 0]} castShadow>
                <boxGeometry args={[0.6, 0.4, 0.6]} />
                <meshStandardMaterial color={isHospital ? "#f8fafc" : (isEnergy ? "#1e293b" : color)} metalness={0.8} roughness={0.2} />
            </mesh>
            {/* Torre Central */}
            <mesh position={[0, 0.7, 0]} castShadow>
                <boxGeometry args={[0.3, 1.2, 0.3]} />
                <meshStandardMaterial color={isHospital ? "#f1f5f9" : (isEnergy ? "#334155" : color)} metalness={0.9} roughness={0.1} />
            </mesh>

            {isHospital ? (
                /* Cruz Médica Animada */
                <Float speed={5} rotationIntensity={0.5} floatIntensity={0.5}>
                    <group position={[0, 1.4, 0]}>
                        <mesh castShadow>
                            <boxGeometry args={[0.5, 0.15, 0.15]} />
                            <meshStandardMaterial color="#ef4444" emissive="#ef4444" emissiveIntensity={1} />
                        </mesh>
                        <mesh castShadow rotation={[0, 0, Math.PI / 2]}>
                            <boxGeometry args={[0.5, 0.15, 0.15]} />
                            <meshStandardMaterial color="#ef4444" emissive="#ef4444" emissiveIntensity={1} />
                        </mesh>
                    </group>
                </Float>
            ) : isEnergy ? (
                /* Núcleo de Energía */
                <Float speed={8} rotationIntensity={2} floatIntensity={1}>
                    <mesh position={[0, 1.2, 0]}>
                        <octahedronGeometry args={[0.25]} />
                        <meshStandardMaterial color="#00e5ff" emissive="#00e5ff" emissiveIntensity={3} />
                    </mesh>
                    <pointLight position={[0, 1.2, 0]} intensity={2} distance={4} color="#00e5ff" />
                    <Sparkles count={20} scale={1} size={2} speed={2} color="#00e5ff" />
                </Float>
            ) : (
                /* Anillo de energía para otros edificios */
                <mesh position={[0, 1.1, 0]} rotation={[Math.PI / 2, 0, 0]}>
                    <torusGeometry args={[0.25, 0.03, 16, 32]} />
                    <meshStandardMaterial color="#7c4dff" emissive="#7c4dff" emissiveIntensity={2} />
                </mesh>
            )}
        </group>
    );
}

// Componente para una celda del terreno mejorada
function TerrainTile({ x, y, tile }: any) {
    const meshRef = useRef<THREE.Mesh>(null);
    const [hovered, setHovered] = useState(false);

    const getTerrainProperties = () => {
        switch (tile.terrain) {
            case "mountain":
                return { height: 1.8, color: "#64748b", type: "mountain" };
            case "water":
                return { height: 0.1, color: "#0ea5e9", type: "water" };
            case "forest":
                return { height: 0.4, color: "#059669", type: "forest" };
            case "desert":
                return { height: 0.3, color: "#d97706", type: "desert" };
            default: // grass
                return { height: 0.4, color: "#10b981", type: "grass" };
        }
    };

    const { height, color, type } = getTerrainProperties();

    useFrame((state) => {
        if (meshRef.current && type === "water") {
            meshRef.current.position.y = 0.05 + Math.sin(state.clock.elapsedTime * 1.5 + x + y) * 0.04;
        }
    });

    return (
        <group position={[x - 10, 0, y - 10]}>
            {/* Suelo base */}
            <mesh
                ref={meshRef}
                position={[0, type === "water" ? 0.05 : height / 2, 0]}
                receiveShadow
                onPointerOver={() => setHovered(true)}
                onPointerOut={() => setHovered(false)}
            >
                <boxGeometry args={[0.95, height, 0.95]} />
                <meshStandardMaterial
                    color={color}
                    metalness={type === "water" ? 0.9 : 0.1}
                    roughness={type === "water" ? 0.1 : 0.8}
                    transparent={type === "water"}
                    opacity={type === "water" ? 0.8 : 1}
                />
            </mesh>

            {/* Elementos Representativos según tipo */}
            {type === "mountain" && <MountainGeometry height={height + 0.5} color={color} />}
            {type === "forest" && <ForestGeometry height={height / 2} />}

            {/* Borde de territorio */}
            {tile.owner && (
                <group position={[0, height + 0.05, 0]}>
                    <mesh rotation={[-Math.PI / 2, 0, 0]}>
                        <ringGeometry args={[0.4, 0.48, 4, 1]} />
                        <meshBasicMaterial
                            color={tile.owner === "Tecnócratas" ? "#7c4dff" : "#00e676"}
                            transparent
                            opacity={0.8}
                        />
                    </mesh>
                </group>
            )}

            {/* Edificios Representativos */}
            {tile.buildings && tile.buildings.length > 0 && (
                <group position={[0, height, 0]}>
                    <BuildingGeometry
                        type={tile.buildings[0].type}
                        color={tile.buildings[0].color || "#ffd600"}
                    />
                </group>
            )}

            {/* Recursos Representativos */}
            {tile.resource && tile.resource.type === "food" && (
                <Float speed={4} rotationIntensity={1} floatIntensity={0.5}>
                    <group position={[0, height + 0.4, 0]}>
                        <group>
                            {/* Arbusto de comida */}
                            <Sphere args={[0.15, 8, 8]}>
                                <meshStandardMaterial color="#ef4444" emissive="#ef4444" emissiveIntensity={0.5} />
                            </Sphere>
                            <mesh position={[0, -0.1, 0]}>
                                <sphereGeometry args={[0.2, 8, 8]} />
                                <meshStandardMaterial color="#22c55e" />
                            </mesh>
                        </group>
                    </group>
                </Float>
            )}
        </group>
    );
}

// Componente para un agente en 3D mejorado
function Agent3D({ agent, isSelected }: any) {
    const { civilizaciones, gruposDinamicos, speechBubbles } = useGameStore();
    const groupRef = useRef<THREE.Group>(null);
    const meshRef = useRef<THREE.Mesh>(null);
    const ringRef = useRef<THREE.Mesh>(null);
    const [hovered, setHovered] = useState(false);

    // Verificar si el agente está hablando
    const bubble = speechBubbles[agent.id];
    const isSpeaking = !!bubble;

    // Obtener color del grupo
    const groupInfo = agent.grupo_id ? (civilizaciones[agent.grupo_id] || gruposDinamicos[agent.grupo_id]) : null;
    const groupColor = groupInfo?.color || "#e0e0e0";

    // Identificar si es líder
    const isLeader = agent.rol?.toLowerCase().includes("líder") ||
        agent.rol?.toLowerCase().includes("gobernante") ||
        agent.rol?.toLowerCase().includes("fundador");

    const agentColor = agent.grupo_id ? groupColor : "#e0e0e0";
    const agentEmissive = agent.grupo_id ? groupColor : "#7c4dff";

    // Salud del agente (0 a 10)
    const health = agent.necesidades?.salud ?? 10;
    const healthPercent = health / 10;
    const healthColor = healthPercent > 0.7 ? "#00e676" : (healthPercent > 0.3 ? "#ffd600" : "#ff1744");
    const isCritical = healthPercent <= 0.3;

    // Posición objetivo para suavizado
    const targetPos = useMemo(() => new THREE.Vector3(agent.x - 10, 0, agent.y - 10), [agent.x, agent.y]);

    // Animaciones y Movimiento Suave
    useFrame((state, delta) => {
        if (groupRef.current) {
            const currentPos = groupRef.current.position;
            const distance = currentPos.distanceTo(targetPos);

            // Mover hacia el objetivo
            currentPos.lerp(targetPos, delta * 4);

            // Rotar hacia la dirección de movimiento
            if (distance > 0.1) {
                const direction = new THREE.Vector3().subVectors(targetPos, currentPos).normalize();
                const targetRotation = Math.atan2(direction.x, direction.z);

                // Suavizar la rotación (lerp de ángulo)
                let diff = targetRotation - groupRef.current.rotation.y;
                while (diff < -Math.PI) diff += Math.PI * 2;
                while (diff > Math.PI) diff -= Math.PI * 2;
                groupRef.current.rotation.y += diff * delta * 6;
            }

            if (meshRef.current) {
                // Efecto de "caminar" (bobbing) que se intensifica con el movimiento
                const walkSpeed = 8;
                const bobAmount = distance > 0.05 ? 0.2 : 0.05;
                const baseY = 1.3 + Math.sin(state.clock.elapsedTime * walkSpeed) * bobAmount;
                meshRef.current.position.y = baseY;

                // Balanceo lateral al caminar
                if (distance > 0.05) {
                    meshRef.current.rotation.z = Math.sin(state.clock.elapsedTime * walkSpeed) * 0.1;
                } else {
                    meshRef.current.rotation.z = 0;
                    meshRef.current.rotation.y = state.clock.elapsedTime * 0.5; // Rotación ociosa
                }

                // Efecto de pulso si es líder o salud crítica
                if (isLeader || isCritical) {
                    const pulseSpeed = isCritical ? 8 : 4;
                    const scale = (isLeader ? 1.3 : 1.0) + Math.sin(state.clock.elapsedTime * pulseSpeed) * (isCritical ? 0.1 : 0.05);
                    meshRef.current.scale.setScalar(scale);
                } else {
                    meshRef.current.scale.setScalar(1);
                }
            }
        }

        if (ringRef.current && isSelected) {
            ringRef.current.rotation.z = state.clock.elapsedTime * 2;
            ringRef.current.scale.setScalar(1 + Math.sin(state.clock.elapsedTime * 3) * 0.1);
        }
    });

    return (
        <group
            ref={groupRef}
            onPointerOver={() => setHovered(true)}
            onPointerOut={() => setHovered(false)}
        >
            {/* Salud / Energía Bar */}
            <group position={[0, isLeader ? 3.4 : 3.1, 0]}>
                <mesh position={[0, 0, 0]}>
                    <planeGeometry args={[0.8, 0.08]} />
                    <meshBasicMaterial color="#000000" transparent opacity={0.5} />
                </mesh>
                <mesh position={[(healthPercent - 1) * 0.4, 0, 0.01]}>
                    <planeGeometry args={[0.8 * healthPercent, 0.08]} />
                    <meshBasicMaterial color={healthColor} />
                </mesh>
                {isCritical && (
                    <pointLight intensity={1 + Math.sin(Date.now() * 0.01) * 0.5} distance={1} color="#ff1744" />
                )}
            </group>

            {/* Halo de luz */}
            <pointLight
                position={[0, 1.5, 0]}
                intensity={isLeader ? 2 : (isSelected ? 1.5 : hovered ? 1 : 0.5)}
                distance={5}
                color={isCritical ? "#ff1744" : (isLeader ? "#ffd600" : agentEmissive)}
            />

            {/* Cuerpo del agente con efecto de cristal */}
            <Sphere
                ref={meshRef}
                args={[0.35, 32, 32]}
                position={[0, 1.5, 0]}
            >
                <meshStandardMaterial
                    color={agentColor}
                    emissive={isLeader ? "#ffd600" : agentEmissive}
                    emissiveIntensity={isLeader ? 1.5 : (isSelected ? 1.5 : hovered ? 1.2 : 0.8)}
                    metalness={0.9}
                    roughness={0.1}
                    envMapIntensity={2}
                />
            </Sphere>

            {/* Corona de Líder */}
            {isLeader && (
                <Float speed={4} rotationIntensity={1} floatIntensity={0.5}>
                    <mesh position={[0, 2.1, 0]}>
                        <torusGeometry args={[0.2, 0.05, 16, 32]} />
                        <meshStandardMaterial color="#ffd600" emissive="#ffd600" emissiveIntensity={2} />
                    </mesh>
                    <mesh position={[0, 2.22, 0]}>
                        <tetrahedronGeometry args={[0.08]} />
                        <meshStandardMaterial color="#ffd600" emissive="#ffd600" emissiveIntensity={3} />
                    </mesh>
                </Float>
            )}

            {/* Anillo orbital */}
            {(isSelected || hovered || isLeader) && (
                <mesh ref={ringRef} rotation={[Math.PI / 2, 0, 0]} position={[0, 0.1, 0]}>
                    <ringGeometry args={[0.6, 0.7, 64]} />
                    <meshBasicMaterial
                        color={isLeader ? "#ffd600" : agentEmissive}
                        transparent
                        opacity={isSelected || isLeader ? 0.9 : 0.6}
                        side={THREE.DoubleSide}
                    />
                </mesh>
            )}

            {/* Anillo secundario para seleccionados */}
            {isSelected && (
                <mesh rotation={[Math.PI / 2, 0, 0]} position={[0, 0.1, 0]}>
                    <ringGeometry args={[0.75, 0.8, 64]} />
                    <meshBasicMaterial
                        color="#7c4dff"
                        transparent
                        opacity={0.4}
                        side={THREE.DoubleSide}
                    />
                </mesh>
            )}

            {/* Partículas alrededor del agente */}
            {(isSelected || isLeader) && (
                <Sparkles
                    count={isLeader ? 30 : 15}
                    scale={2}
                    size={2}
                    speed={0.4}
                    color={isLeader ? "#ffd600" : agentEmissive}
                />
            )}

            {/* ID del agente con mejor tipografía */}
            <Text
                position={[0, isLeader ? 2.8 : 2.5, 0]}
                fontSize={0.25}
                color={isLeader ? "#ffd600" : "#ffffff"}
                anchorX="center"
                anchorY="middle"
                outlineWidth={0.02}
                outlineColor="#000000"
                fontWeight="bold"
            >
                {isLeader ? `👑 ${agent.id.replace('A', '')}` : agent.id.replace('A', '')}
            </Text>

            {/* Símbolo de Hablando */}
            {isSpeaking && (
                <Float speed={10} rotationIntensity={0.5} floatIntensity={1}>
                    <group position={[0, isLeader ? 3.6 : 3.3, 0]}>
                        <Text
                            fontSize={0.4}
                            color="#ffffff"
                            anchorX="center"
                            anchorY="middle"
                        >
                            💬
                        </Text>
                        {/* Brillo de comunicación */}
                        <pointLight intensity={1} distance={2} color="#7c4dff" />
                        <Sparkles count={5} scale={0.5} size={2} speed={1} color="#7c4dff" />
                    </group>
                </Float>
            )}

            {/* Indicador de grupo y rol */}
            {agent.grupo_id && (
                <Text
                    position={[0, isLeader ? 3.1 : 2.8, 0]}
                    fontSize={0.15}
                    color={agentColor}
                    anchorX="center"
                    anchorY="middle"
                    outlineWidth={0.01}
                    outlineColor="#000000"
                >
                    {`${agent.grupo_id}${agent.rol ? ` | ${agent.rol}` : ''}`}
                </Text>
            )}
        </group>
    );
}

// Componente para visualizar los vínculos entre agentes
function RelationshipLinks({ show }: { show: boolean }) {
    const { agents, relationships } = useGameStore();

    if (!show || !relationships || relationships.length === 0) return null;

    return (
        <group>
            {relationships.map((rel: any, i: number) => {
                const source = agents.find(a => a.id === rel.source);
                const target = agents.find(a => a.id === rel.target);

                if (!source || !target) return null;

                const isAlliance = rel.type === "alianza" || rel.type === "alliance";
                const isFriend = rel.type === "amigo" || rel.type === "friend";
                const isEnemy = rel.type === "enemigo" || rel.type === "enemy";

                let color = "#7c4dff";
                if (isFriend) color = "#00e676";
                if (isEnemy) color = "#ff1744";
                if (isAlliance) color = "#ffd600";

                return (
                    <group key={`${rel.source}-${rel.target}-${i}`}>
                        <Line
                            points={[
                                [source.x - 10, 1.5, source.y - 10],
                                [target.x - 10, 1.5, target.y - 10]
                            ]}
                            color={color}
                            lineWidth={1.5}
                            dashed={isAlliance}
                            dashSize={0.5}
                            gapSize={0.2}
                            transparent
                            opacity={0.3}
                        />
                        {/* Efecto de flujo de energía (punto que recorre la línea) */}
                        <MovingEnergyPoint
                            start={[source.x - 10, 1.5, source.y - 10]}
                            end={[target.x - 10, 1.5, target.y - 10]}
                            color={color}
                        />
                    </group>
                );
            })}
        </group>
    );
}

// Punto de energía animado que recorre el vínculo
function MovingEnergyPoint({ start, end, color }: { start: [number, number, number], end: [number, number, number], color: string }) {
    const meshRef = useRef<THREE.Mesh>(null);
    const startVec = useMemo(() => new THREE.Vector3(...start), [start]);
    const endVec = useMemo(() => new THREE.Vector3(...end), [end]);

    useFrame((state) => {
        if (meshRef.current) {
            const t = (state.clock.elapsedTime * 0.5) % 1;
            meshRef.current.position.lerpVectors(startVec, endVec, t);
        }
    });

    return (
        <Sphere ref={meshRef} args={[0.08, 8, 8]}>
            <meshBasicMaterial color={color} />
        </Sphere>
    );
}

// Componente de la escena 3D mejorada
function Scene3D({ showLinks }: { showLinks: boolean }) {
    const { agents, mapa, selectedAgentId, selectAgent } = useGameStore();

    // Renderizar el mapa
    const terrainTiles = useMemo(() => {
        if (!mapa || mapa.length === 0) return null;

        return mapa.map((row: any, x: number) =>
            row.map((tile: any, y: number) => (
                <TerrainTile key={`${x}-${y}`} x={x} y={y} tile={tile} />
            ))
        );
    }, [mapa]);

    return (
        <>
            {/* Iluminación atmosférica mejorada */}
            <ambientLight intensity={0.3} color="#4c1d95" />

            {/* Luz direccional principal con sombras */}
            <directionalLight
                position={[15, 25, 15]}
                intensity={1.2}
                castShadow
                shadow-mapSize-width={4096}
                shadow-mapSize-height={4096}
                shadow-camera-far={50}
                shadow-camera-left={-20}
                shadow-camera-right={20}
                shadow-camera-top={20}
                shadow-camera-bottom={-20}
                color="#ffffff"
            />

            {/* Luces de acento */}
            <pointLight position={[-15, 15, -15]} intensity={0.8} color="#7c4dff" distance={30} />
            <pointLight position={[15, 15, -15]} intensity={0.6} color="#00e676" distance={30} />
            <pointLight position={[0, 20, 0]} intensity={0.4} color="#ffd600" distance={25} />

            {/* Luz de relleno */}
            <hemisphereLight intensity={0.5} color="#7c4dff" groundColor="#1e1b4b" />

            {/* Estrellas de fondo */}
            <Stars
                radius={100}
                depth={50}
                count={5000}
                factor={4}
                saturation={0}
                fade
                speed={0.5}
            />

            {/* Partículas flotantes */}
            <FloatingParticles />

            {/* Niebla volumétrica */}
            <fog attach="fog" args={["#0a0b10", 15, 45]} />

            {/* Terreno */}
            {terrainTiles}

            {/* Vínculos entre agentes */}
            <RelationshipLinks show={showLinks} />

            {/* Plano reflectante base */}
            <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.01, 0]} receiveShadow>
                <planeGeometry args={[50, 50]} />
                <MeshReflectorMaterial
                    blur={[400, 100]}
                    resolution={1024}
                    mixBlur={1}
                    mixStrength={0.3}
                    depthScale={1}
                    minDepthThreshold={0.85}
                    color="#0a0b10"
                    metalness={0.6}
                    roughness={0.8}
                    mirror={0.3}
                />
            </mesh>

            {/* Grid mejorado */}
            <gridHelper
                args={[22, 22, "#7c4dff", "#1e1b4b"]}
                position={[0, 0.02, 0]}
            />

            {/* Agentes */}
            {agents.map((agent: any) => (
                <group
                    key={agent.id}
                    onClick={(e) => {
                        e.stopPropagation();
                        selectAgent(agent.id);
                    }}
                    onPointerOver={() => (document.body.style.cursor = "pointer")}
                    onPointerOut={() => (document.body.style.cursor = "default")}
                >
                    <Agent3D agent={agent} isSelected={agent.id === selectedAgentId} />
                </group>
            ))}

            {/* Entorno HDR */}
            <Environment preset="night" />

            {/* Controles de cámara mejorados */}
            <OrbitControls
                enablePan={true}
                enableZoom={true}
                enableRotate={true}
                minDistance={8}
                maxDistance={45}
                maxPolarAngle={Math.PI / 2.1}
                enableDamping
                dampingFactor={0.05}
                rotateSpeed={0.5}
                zoomSpeed={0.8}
            />

            {/* Post-procesamiento */}
            <EffectComposer>
                <Bloom
                    intensity={1.5}
                    luminanceThreshold={0.1}
                    luminanceSmoothing={0.9}
                    height={300}
                />
                <Scanline opacity={0.1} />
                <Noise opacity={0.05} />
                <DepthOfField
                    focusDistance={0.02}
                    focalLength={0.05}
                    bokehScale={3}
                />
                <Vignette
                    offset={0.3}
                    darkness={0.5}
                />
            </EffectComposer>
        </>
    );
}

// Componente principal
export default function WorldViewport3D() {
    const [showLinks, setShowLinks] = useState(true);

    return (
        <div className="w-full h-full relative bg-gradient-to-b from-[#0a0b10] via-[#1e1b4b] to-[#0a0b10]">
            <Canvas
                camera={{
                    position: [18, 18, 18],
                    fov: 65,
                }}
                shadows
                gl={{
                    antialias: true,
                    alpha: false,
                    powerPreference: "high-performance"
                }}
            >
                <Scene3D showLinks={showLinks} />
            </Canvas>

            {/* Panel de controles estilizado */}
            <div className="absolute bottom-6 left-6 glass-panel rounded-2xl overflow-hidden border border-white/10 shadow-[0_0_50px_rgba(124,77,255,0.2)]">
                <div className="bg-gradient-to-r from-[#7c4dff]/20 to-transparent px-5 py-3 border-b border-white/10 flex items-center justify-between gap-8">
                    <div className="flex items-center gap-3">
                        <div className="w-2 h-2 rounded-full bg-[#7c4dff] animate-pulse shadow-[0_0_10px_#7c4dff]" />
                        <span className="text-xs font-bold text-[#7c4dff] uppercase tracking-[0.2em]">Controles 3D</span>
                    </div>
                    {/* Toggle de Vínculos */}
                    <button
                        onClick={() => setShowLinks(!showLinks)}
                        className={`flex items-center gap-2 px-2 py-1 rounded border transition-all ${showLinks ? 'bg-[#00e676]/20 border-[#00e676] text-[#00e676]' : 'bg-white/5 border-white/10 text-gray-500'}`}
                        title={showLinks ? "Ocultar Red Social" : "Mostrar Red Social"}
                    >
                        <Share2 className="w-3 h-3" />
                        <span className="text-[10px] font-bold uppercase tracking-tighter">{showLinks ? 'Vínculos ON' : 'Vínculos OFF'}</span>
                    </button>
                </div>
                <div className="p-5 space-y-2.5 text-xs text-gray-300">
                    <div className="flex items-center gap-3 group hover:text-white transition-colors">
                        <span className="text-lg">🖱️</span>
                        <span><span className="text-[#7c4dff] font-bold">Click izq + arrastrar:</span> Rotar cámara</span>
                    </div>
                    <div className="flex items-center gap-3 group hover:text-white transition-colors">
                        <span className="text-lg">🎯</span>
                        <span><span className="text-[#00e676] font-bold">Rueda del mouse:</span> Zoom in/out</span>
                    </div>
                    <div className="flex items-center gap-3 group hover:text-white transition-colors">
                        <span className="text-lg">✋</span>
                        <span><span className="text-[#ffd600] font-bold">Click der + arrastrar:</span> Mover vista</span>
                    </div>
                    <div className="flex items-center gap-3 group hover:text-white transition-colors">
                        <span className="text-lg">👆</span>
                        <span><span className="text-[#ff1744] font-bold">Click en agente:</span> Seleccionar</span>
                    </div>
                </div>
            </div>

            {/* Indicador de calidad visual */}
            <div className="absolute top-6 left-6 glass-panel px-4 py-2 rounded-full border border-[#00e676]/30">
                <div className="flex items-center gap-2">
                    <div className="w-1.5 h-1.5 rounded-full bg-[#00e676] shadow-[0_0_8px_#00e676]" />
                    <span className="text-[10px] font-bold text-[#00e676] uppercase tracking-wider">Premium Render</span>
                </div>
            </div>
        </div>
    );
}
