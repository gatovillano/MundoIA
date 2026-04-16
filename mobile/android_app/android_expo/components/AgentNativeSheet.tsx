import React, { useMemo } from 'react';
import { 
  StyleSheet, 
  View, 
  Text, 
  ScrollView, 
  TouchableOpacity, 
  Dimensions, 
  Animated 
} from 'react-native';
import { 
  X, 
  Heart, 
  Zap, 
  Brain, 
  Wallet, 
  Shield, 
  Users, 
  MessageSquare, 
  ChevronRight, 
  Compass, 
  Target, 
  Eye 
} from 'lucide-react-native';
import useNativeStore from '../hooks/useNativeStore';

const { height: SCREEN_HEIGHT } = Dimensions.get('window');

export default function AgentNativeSheet() {
  const { agents, selectedAgentId, selectAgent } = useNativeStore();
  const agent = useMemo(() => agents.find(a => a.id === selectedAgentId), [agents, selectedAgentId]);

  if (!selectedAgentId || !agent) return null;

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <View style={styles.handle} />
        <TouchableOpacity style={styles.closeButton} onPress={() => selectAgent(null)}>
          <X size={20} color="#666" />
        </TouchableOpacity>
      </View>

      <ScrollView style={styles.scrollContent} showsVerticalScrollIndicator={false}>
        {/* Profile Header */}
        <View style={styles.profileHeader}>
          <View style={[styles.avatar, { borderColor: agent.color || '#7c4dff' }]}>
            <Text style={styles.avatarText}>{agent.id?.substring(0, 2)}</Text>
          </View>
          <View>
            <Text style={styles.agentId}>AGENTE {agent.id?.substring(0, 8)}</Text>
            <View style={styles.badgeRow}>
              <View style={styles.badge}>
                <Text style={styles.badgeText}>{agent.profesion || "CIUDADANO"}</Text>
              </View>
              {agent.is_possessed && (
                <View style={[styles.badge, styles.possessedBadge]}>
                  <Text style={styles.badgeText}>POSEÍDO</Text>
                </View>
              )}
            </View>
          </View>
        </View>

        {/* Thought / Neural cortex */}
        <View style={styles.cortex}>
          <View style={styles.sectionHeader}>
            <Brain size={14} color="#7c4dff" />
            <Text style={styles.sectionTitle}>PENSAMIENTO ACTIVO</Text>
          </View>
          <Text style={styles.thoughtText}>&ldquo;{agent.pensamiento || "Procesando estímulos..."}&rdquo;</Text>
        </View>

        {/* Main Stats */}
        <View style={styles.statGrid}>
          <StatCard icon={Heart} label="Salud" value={agent.necesidades?.salud} color="#ff1744" />
          <StatCard icon={Zap} label="Recursos" value={agent.resources} color="#ffd600" />
          <StatCard icon={Brain} label="Córtex" value={(agent.skill_factor || 0) * 10} unit="/10" color="#7c4dff" />
          <StatCard icon={Wallet} label="MC" value={agent.money} unit="MC" color="#00e676" />
        </View>

        {/* BDI Section */}
        <View style={styles.section}>
          <SectionTitle icon={Target} title="Deseos e Intenciones" color="#ff4081" />
          {agent.deseos?.deseos && Object.values(agent.deseos.deseos).map((d: any, i) => (
            <ProgressBar 
              key={i}
              label={d.tipo} 
              value={d.intensidad} 
              color="#ff4081" 
            />
          ))}
          {!agent.deseos?.deseos && (
            <Text style={styles.emptyText}>Sin deseos detectados...</Text>
          )}
        </View>

        <View style={styles.section}>
          <SectionTitle icon={Eye} title="Sistema de Creencias" color="#00e5ff" />
          {agent.creencias && Object.values(agent.creencias).map((c: any, i) => (
            <View key={i} style={styles.beliefItem}>
              <Text style={styles.beliefText}>{c.proposicion?.replace(/_/g, ' ')}</Text>
              <Text style={styles.beliefProb}>{(c.probabilidad * 100).toFixed(0)}%</Text>
            </View>
          ))}
           {!agent.creencias && (
            <Text style={styles.emptyText}>Sin creencias formadas...</Text>
          )}
        </View>

        <TouchableOpacity style={styles.chatAction}>
          <MessageSquare size={16} color="#fff" />
          <Text style={styles.chatActionText}>CONECTAR CON LLM</Text>
          <ChevronRight size={16} color="#fff" opacity={0.5} />
        </TouchableOpacity>

        <View style={{ height: 40 }} />
      </ScrollView>
    </View>
  );
}

function StatCard({ icon: Icon, label, value, unit, color }: any) {
  return (
    <View style={styles.statCard}>
      <View style={styles.statCardHeader}>
        <Icon size={12} color={color} />
        <Text style={[styles.statLabel, { color }]}>{label}</Text>
      </View>
      <Text style={styles.statValue}>
        {typeof value === 'number' ? value.toFixed(1) : '0.0'}
        {unit && <Text style={styles.statUnit}> {unit}</Text>}
      </Text>
    </View>
  );
}

function SectionTitle({ icon: Icon, title, color }: any) {
  return (
    <View style={styles.sectionHeader}>
      <Icon size={14} color={color} />
      <Text style={[styles.sectionTitle, { color }]}>{title}</Text>
    </View>
  );
}

function ProgressBar({ label, value, color }: any) {
  const width = Math.max(0, Math.min(100, (value || 0) * 100));
  return (
    <View style={styles.progressContainer}>
      <View style={styles.progressHeader}>
        <Text style={styles.progressLabel}>{label?.replace(/_/g, ' ')}</Text>
        <Text style={styles.progressValue}>{(value || 0).toFixed(1)}</Text>
      </View>
      <View style={styles.progressBar}>
        <View style={[styles.progressFill, { width: `${width}%`, backgroundColor: color }]} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    height: SCREEN_HEIGHT * 0.7,
    backgroundColor: '#0a0b10',
    borderTopLeftRadius: 30,
    borderTopRightRadius: 30,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.1)',
    zIndex: 200,
  },
  header: {
    alignItems: 'center',
    paddingVertical: 10,
  },
  handle: {
    width: 40,
    height: 4,
    backgroundColor: 'rgba(255,255,255,0.1)',
    borderRadius: 2,
  },
  closeButton: {
    position: 'absolute',
    right: 20,
    top: 15,
  },
  scrollContent: {
    padding: 20,
  },
  profileHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 15,
    marginBottom: 20,
  },
  avatar: {
    width: 60,
    height: 60,
    borderRadius: 15,
    borderWidth: 2,
    backgroundColor: '#111218',
    justifyContent: 'center',
    alignItems: 'center',
  },
  avatarText: {
    color: '#fff',
    fontSize: 24,
    fontWeight: 'bold',
  },
  agentId: {
    color: '#fff',
    fontSize: 18,
    fontWeight: 'bold',
    letterSpacing: -0.5,
  },
  badgeRow: {
    flexDirection: 'row',
    gap: 5,
    marginTop: 5,
  },
  badge: {
    backgroundColor: 'rgba(255,255,255,0.05)',
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 5,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.1)',
  },
  possessedBadge: {
    borderColor: '#ffd60033',
    backgroundColor: '#ffd60011',
  },
  badgeText: {
    color: '#aaa',
    fontSize: 9,
    fontWeight: 'bold',
  },
  section: {
    marginTop: 25,
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 10,
  },
  sectionTitle: {
    fontSize: 10,
    fontWeight: 'bold',
    letterSpacing: 2,
    color: '#666',
  },
  cortex: {
    backgroundColor: 'rgba(124, 77, 255, 0.05)',
    padding: 15,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: 'rgba(124, 77, 255, 0.1)',
    marginBottom: 20,
  },
  thoughtText: {
    color: '#eee',
    fontSize: 13,
    fontStyle: 'italic',
    lineHeight: 20,
    marginTop: 5,
  },
  statGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
  },
  statCard: {
    flex: 1,
    minWidth: '45%',
    backgroundColor: 'rgba(255,255,255,0.03)',
    padding: 15,
    borderRadius: 15,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.05)',
  },
  statCardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginBottom: 5,
  },
  statLabel: {
    fontSize: 9,
    fontWeight: 'bold',
  },
  statValue: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
  },
  statUnit: {
    fontSize: 10,
    color: '#666',
  },
  progressContainer: {
    marginBottom: 12,
  },
  progressHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 5,
  },
  progressLabel: {
    color: '#aaa',
    fontSize: 10,
    textTransform: 'uppercase',
  },
  progressValue: {
    color: '#fff',
    fontSize: 10,
    fontWeight: 'bold',
  },
  progressBar: {
    height: 4,
    backgroundColor: 'rgba(255,255,255,0.05)',
    borderRadius: 2,
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    borderRadius: 2,
  },
  beliefItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    backgroundColor: 'rgba(255,255,255,0.02)',
    padding: 10,
    borderRadius: 10,
    marginBottom: 8,
  },
  beliefText: {
    color: '#ccc',
    fontSize: 12,
    textTransform: 'capitalize',
  },
  beliefProb: {
    color: '#00e5ff',
    fontWeight: 'bold',
    fontSize: 12,
  },
  emptyText: {
    color: '#444',
    fontSize: 11,
    fontStyle: 'italic',
    textAlign: 'center',
    marginTop: 10,
  },
  chatAction: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#7c4dff',
    padding: 15,
    borderRadius: 15,
    marginTop: 30,
    gap: 10,
  },
  chatActionText: {
    flex: 1,
    color: '#fff',
    fontWeight: 'bold',
    fontSize: 12,
  }
});
