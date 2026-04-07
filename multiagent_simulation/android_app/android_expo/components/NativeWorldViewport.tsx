import React, { useMemo, useRef, useState } from 'react';
import { View, StyleSheet, Dimensions, PanResponder, Animated } from 'react-native';
import Svg, { G, Path, Circle, Text as SvgText } from 'react-native-svg';
import useNativeStore from '../hooks/useNativeStore';

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');

const TILE_W = 60;
const TILE_H = 30;

const iso = (col: number, row: number) => ({
    x: (col - row) * (TILE_W / 2),
    y: (col + row) * (TILE_H / 2)
});

const TERRAIN_COLORS: Record<string, string> = {
    grass: "#4caf50",
    forest: "#2e7d32",
    mountain: "#616161",
    montaña: "#616161",
    water: "#1976d2",
    desert: "#ffe082",
    path: "#bdbdbd",
    default: "#333"
};

const NativeWorldViewport = () => {
    const { mapa, agents, selectedAgentId, selectAgent } = useNativeStore();

    // Pan state
    const pan = useRef(new Animated.ValueXY({ x: 0, y: 0 })).current;
    const [scale, setScale] = useState(1);
    
    const panResponder = useRef(
      PanResponder.create({
        onMoveShouldSetPanResponder: () => true,
        onPanResponderMove: Animated.event([null, { dx: pan.x, dy: pan.y }], { useNativeDriver: false }),
        onPanResponderRelease: () => {
          pan.extractOffset();
        },
      })
    ).current;

    const renderMap = useMemo(() => {
        if (!mapa || mapa.length === 0) return null;

        const flatMap = mapa.flatMap((row, x) => row.map((tile, y) => ({ ...tile, x, y })));
        flatMap.sort((a, b) => (a.x + a.y) - (b.x + b.y));

        const d = `M 0 -${TILE_H / 2} L ${TILE_W / 2} 0 L 0 ${TILE_H / 2} L -${TILE_W / 2} 0 Z`;

        return flatMap.map((tile) => {
            const pos = iso(tile.x, tile.y);
            const color = TERRAIN_COLORS[tile.terrain?.toLowerCase()] || TERRAIN_COLORS.default;
            
            return (
                <G key={`tile-${tile.x}-${tile.y}`} transform={`translate(${pos.x}, ${pos.y})`}>
                    <Path 
                        d={d} 
                        fill={color} 
                        stroke="rgba(255,255,255,0.05)" 
                        strokeWidth={0.5} 
                    />
                </G>
            );
        });
    }, [mapa]);

    const renderAgents = useMemo(() => {
        return agents.map((agent) => {
            const pos = iso(agent.x, agent.y);
            const isSelected = agent.id === selectedAgentId;

            return (
                <G 
                    key={`agent-${agent.id}`} 
                    transform={`translate(${pos.x}, ${pos.y})`}
                    onPress={() => selectAgent(agent.id)}
                >
                    <Circle cx={0} cy={2} r={6} fill="rgba(0,0,0,0.2)" />
                    {isSelected && (
                        <Circle cx={0} cy={0} r={12} stroke="#7c4dff" strokeWidth={2} fill="none" />
                    )}
                    <Circle cx={0} cy={-12} r={8} fill={agent.color || "#EF5350"} />
                    <SvgText
                      x={0}
                      y={8}
                      fill="white"
                      fontSize="7"
                      fontWeight="bold"
                      textAnchor="middle"
                    >
                      {agent.id?.substring(0, 4)}
                    </SvgText>
                </G>
            );
        });
    }, [agents, selectedAgentId, selectAgent]);

    if (!mapa || mapa.length === 0) return null;

    return (
        <View style={styles.container} {...panResponder.panHandlers}>
            <Animated.View style={{
                transform: [
                    { translateX: pan.x },
                    { translateY: pan.y },
                    { scale: scale }
                ]
            }}>
                <Svg 
                    width={SCREEN_WIDTH * 2} 
                    height={SCREEN_HEIGHT * 2} 
                    viewBox={`${-SCREEN_WIDTH} ${-SCREEN_HEIGHT / 2} ${SCREEN_WIDTH * 2} ${SCREEN_HEIGHT * 2}`}
                >
                    <G>
                        {renderMap}
                        {renderAgents}
                    </G>
                </Svg>
            </Animated.View>
        </View>
    );
};

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: '#1c2128',
    },
    emptyContainer: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
        backgroundColor: '#1c2128',
    },
    emptyText: {
        color: '#7c4dff',
        fontSize: 18,
        fontWeight: 'bold',
    },
    agentName: {
        color: 'white',
        fontSize: 8,
        textAlign: 'center',
        backgroundColor: 'rgba(0,0,0,0.5)',
        paddingHorizontal: 2,
    }
});

export default NativeWorldViewport;
