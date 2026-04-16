import React, { useMemo, useRef, useEffect } from 'react';
import { StyleSheet, View, Text, FlatList, Dimensions } from 'react-native';
import { Terminal } from 'lucide-react-native';
import useNativeStore from '../hooks/useNativeStore';

const { width } = Dimensions.get('window');

const CATEGORY_COLORS: { [key: string]: string } = {
  social: '#7c4dff',
  conflict: '#ff1744',
  economia: '#00e676',
  construccion: '#ff9100',
  movimiento: '#00e5ff',
  consenso: '#2979ff',
  general: '#aaa',
};

export default function LogTicker() {
  const { logs } = useNativeStore();
  const flatListRef = useRef<FlatList>(null);

  // Auto-scroll to top when new logs arrive (since we prepend them)
  useEffect(() => {
    if (logs.length > 0) {
      flatListRef.current?.scrollToOffset({ offset: 0, animated: true });
    }
  }, [logs]);

  const renderLog = ({ item }: { item: any }) => {
    const color = CATEGORY_COLORS[item.category] || '#666';
    
    // Clean message
    let msg = item.message || "";
    const colonIdx = msg.indexOf(']: "');
    if (colonIdx !== -1) {
      msg = msg.substring(colonIdx + 4).replace(/"$/, '');
    }

    return (
      <View style={styles.logItem}>
        <View style={[styles.indicator, { backgroundColor: color }]} />
        <View style={styles.logContent}>
            <View style={styles.logMeta}>
                <Text style={[styles.logCategory, { color }]}>{item.category || "SYSTEM"}</Text>
                <Text style={styles.logStep}>PASO {item.step || 0}</Text>
            </View>
            <Text style={styles.logText} numberOfLines={2}>{msg}</Text>
        </View>
      </View>
    );
  };

  return (
    <View style={styles.container}>
      <View style={styles.tickerHeader}>
        <Terminal size={10} color="#666" />
        <Text style={styles.headerText}>LIVE DATA STREAM</Text>
      </View>
      <FlatList
        ref={flatListRef}
        data={logs}
        renderItem={renderLog}
        keyExtractor={(item, index) => `log-${index}`}
        showsVerticalScrollIndicator={false}
        inverted={false} // Since we want top to be latest
        style={styles.list}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    padding: 10,
    backgroundColor: 'rgba(0,0,0,0.8)',
    borderRadius: 15,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.05)',
    margin: 15,
    height: 120,
    position: 'absolute',
    bottom: 20,
    left: 0,
    right: 0,
    zIndex: 150,
  },
  tickerHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginBottom: 8,
    opacity: 0.5,
  },
  headerText: {
    color: '#fff',
    fontSize: 8,
    fontWeight: 'bold',
    letterSpacing: 2,
  },
  list: {
    flex: 1,
  },
  logItem: {
    flexDirection: 'row',
    marginBottom: 8,
    gap: 10,
  },
  indicator: {
    width: 2,
    height: '100%',
    borderRadius: 1,
  },
  logContent: {
    flex: 1,
  },
  logMeta: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 2,
  },
  logCategory: {
    fontSize: 8,
    fontWeight: 'bold',
    textTransform: 'uppercase',
  },
  logStep: {
    color: '#444',
    fontSize: 8,
    fontFamily: 'monospace',
  },
  logText: {
    color: '#eee',
    fontSize: 10,
    lineHeight: 14,
  }
});
