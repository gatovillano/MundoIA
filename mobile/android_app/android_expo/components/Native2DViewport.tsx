import React, { useState, useMemo } from 'react';
import { StyleSheet, View, Dimensions, PanResponder, Animated } from 'react-native';
import Svg, { Rect, Circle, G, Text as SvgText } from 'react-native-svg';
import useNativeStore from '../hooks/useNativeStore';

const { width, height } = Dimensions.get('window');

const TILE_SIZE = 40;

const BIOME_COLORS: { [key: string]: string } = {
  ocean: '#0d47a1',
  water: '#1976d2',
  beach: '#fff59d',
  desert: '#ffe082',
  grass: '#4caf50',
  forest: '#2e7d32',
  mountain: '#616161',
  snow: '#fafafa',
  void: '#000000',
};

export default function Native2DViewport() {
  const { mapa, agents, selectedAgentId, selectAgent } = useNativeStore();
  
  // Pan and Zoom state
  const pan = React.useRef(new Animated.ValueXY({ x: 0, y: 0 })).current;
  const [scale, setScale] = useState(1);
  
  const panResponder = React.useRef(
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
    return mapa.map((row, x) => 
      row.map((tile, y) => {
        if (!tile) return null;
        return (
          <Rect
            key={`tile-${x}-${y}`}
            x={x * TILE_SIZE}
            y={y * TILE_SIZE}
            width={TILE_SIZE}
            height={TILE_SIZE}
            fill={BIOME_COLORS[tile.terrain] || '#333'}
            stroke="#ffffff05"
          />
        );
      })
    );
  }, [mapa]);

  const renderAgents = useMemo(() => {
    return agents.map((agent) => {
      const isSelected = agent.id === selectedAgentId;
      return (
        <G 
          key={`agent-${agent.id}`} 
          onPress={() => selectAgent(agent.id)}
        >
          <Circle
            cx={agent.x * TILE_SIZE + TILE_SIZE / 2}
            cy={agent.y * TILE_SIZE + TILE_SIZE / 2}
            r={TILE_SIZE / 2.5}
            fill={agent.color || '#fff'}
            stroke={isSelected ? '#fff' : 'none'}
            strokeWidth={2}
          />
          <SvgText
            x={agent.x * TILE_SIZE + TILE_SIZE / 2}
            y={agent.y * TILE_SIZE + TILE_SIZE / 2 + 3}
            fill="black"
            fontSize="8"
            fontWeight="bold"
            textAnchor="middle"
          >
            {agent.id?.substring(0, 2)}
          </SvgText>
        </G>
      );
    });
  }, [agents, selectedAgentId, selectAgent]);

  return (
    <View style={styles.container} {...panResponder.panHandlers}>
      <Animated.View style={[
        styles.zoomContainer,
        {
          transform: [
            { translateX: pan.x },
            { translateY: pan.y },
            { scale: scale }
          ]
        }
      ]}>
        <Svg width={mapa.length * TILE_SIZE} height={(mapa[0]?.length || 0) * TILE_SIZE}>
          {renderMap}
          {renderAgents}
        </Svg>
      </Animated.View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000',
    overflow: 'hidden',
  },
  zoomContainer: {
    padding: 100, // Margin to avoid edges
  }
});
