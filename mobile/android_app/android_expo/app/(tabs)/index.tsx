import React, { useState, useEffect } from 'react';
import { 
  StyleSheet, 
  View, 
  StatusBar, 
  Text, 
  TextInput, 
  TouchableOpacity, 
  ActivityIndicator,
  Alert
} from 'react-native';
import { SafeAreaView, SafeAreaProvider } from 'react-native-safe-area-context';
import Constants from 'expo-constants';
import useNativeStore from '../../hooks/useNativeStore';
import NativeWorldViewport from '../../components/NativeWorldViewport';
import Native2DViewport from '../../components/Native2DViewport';
import AgentNativeSheet from '../../components/AgentNativeSheet';
import LogTicker from '../../components/LogTicker';
import { Settings, LogIn, Globe, Play, Pause, Layers } from 'lucide-react-native';

export default function HomeScreen() {
  const { 
    isAuthenticated, 
    login, 
    isConnected, 
    connect, 
    apiHost, 
    setApiHost,
    step,
    sendAction
  } = useNativeStore();

  const [viewMode, setViewMode] = useState<'2d' | 'iso'>('2d');

  const [isLogin, setIsLogin] = useState(true);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [tempHost, setTempHost] = useState('');

  // Detectar IP automáticamente solo la primera vez si no hay una guardada o es localhost
  useEffect(() => {
    if (apiHost === 'localhost:8005' || apiHost === 'api-mundoia.cuerpolibre.cl' || !apiHost) {
        const hostUri = Constants.expoConfig?.hostUri;
        const hostIp = hostUri ? hostUri.split(':')[0] : 'localhost';
        
        // Priorizar el host de producción
        const initialHost = 'api-mundoia.cuerpolibre.cl';
        setTempHost(initialHost);
        if (apiHost === 'localhost:8005' || !apiHost) setApiHost(initialHost);
    } else {
        setTempHost(apiHost);
    }
  }, []);

  useEffect(() => {
    if (isAuthenticated && !isConnected) {
      connect();
    }
  }, [isAuthenticated, isConnected]);

  const handleSubmit = async () => {
    setIsLoading(true);
    const isProd = apiHost.includes('cuerpolibre.cl');
    const protocol = isProd ? 'https' : 'http';
    const cleanHost = apiHost.replace('http://', '').replace('https://', '');

    const endpoint = isLogin ? '/auth/login' : '/auth/register';

    try {
      const url = `${protocol}://${cleanHost}${endpoint}`;
      console.log(`🔑 Auth Attempt (${isLogin ? 'LOGIN' : 'REGISTER'}): ${url}`);
      
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });

      const data = await response.json();
      if (response.ok) {
        if (!isLogin) {
            Alert.alert('Éxito', 'Cuenta creada. Ahora puedes iniciar sesión.');
            setIsLogin(true);
        } else {
            login(data.user_id, data.username);
        }
      } else {
        Alert.alert('Error', data.detail || 'Fallo en la operación');
      }
    } catch (error) {
      Alert.alert('Error', 'No se pudo conectar al servidor. Verifica la IP.');
    } finally {
      setIsLoading(false);
    }
  };

  const saveSettings = () => {
    setApiHost(tempHost);
    setShowSettings(false);
    Alert.alert('Configuración', 'Host del API actualizado.');
  };

  if (!isAuthenticated) {
    return (
      <SafeAreaProvider>
        <SafeAreaView style={styles.container}>
          <StatusBar barStyle="light-content" backgroundColor="#030305" />
          <View style={styles.authContainer}>
            <Text style={styles.title}>Mundo<Text style={{color: '#7c4dff'}}>IA</Text></Text>
            <Text style={styles.subtitle}>{isLogin ? 'INICIAR SESIÓN' : 'CREAR IDENTIDAD'}</Text>

            <View style={styles.inputGroup}>
              <Text style={styles.label}>Usuario</Text>
              <TextInput
                style={styles.input}
                value={username}
                onChangeText={setUsername}
                placeholder="Identificador..."
                placeholderTextColor="#666"
                autoCapitalize="none"
              />
            </View>

            <View style={styles.inputGroup}>
              <Text style={styles.label}>Contraseña</Text>
              <TextInput
                style={styles.input}
                value={password}
                onChangeText={setPassword}
                placeholder="********"
                placeholderTextColor="#666"
                secureTextEntry
              />
            </View>

            <TouchableOpacity 
              style={styles.button} 
              onPress={handleSubmit}
              disabled={isLoading}
            >
              {isLoading ? (
                <ActivityIndicator color="white" />
              ) : (
                <Text style={styles.buttonText}>{isLogin ? 'ACCEDER AL NODO' : 'REGISTRARME'}</Text>
              )}
            </TouchableOpacity>

            <TouchableOpacity 
              style={styles.toggleButton} 
              onPress={() => setIsLogin(!isLogin)}
            >
              <Text style={styles.toggleText}>
                {isLogin ? '¿No tienes cuenta? Registrate aquí' : '¿Ya tienes cuenta? Inicia sesión'}
              </Text>
            </TouchableOpacity>

            <TouchableOpacity 
              style={styles.settingsButton} 
              onPress={() => setShowSettings(!showSettings)}
            >
              <Settings size={16} color="#666" />
              <Text style={styles.settingsText}>Configurar Host</Text>
            </TouchableOpacity>

            {showSettings && (
              <View style={styles.settingsPanel}>
                <Text style={styles.label}>Host del API (IP:Puerto)</Text>
                <TextInput
                  style={styles.inputSmall}
                  value={tempHost}
                  onChangeText={setTempHost}
                  placeholder="api-mundoia.cuerpolibre.cl"
                  placeholderTextColor="#444"
                  autoCapitalize="none"
                />
                <TouchableOpacity style={styles.saveButton} onPress={saveSettings}>
                  <Text style={styles.saveButtonText}>Guardar</Text>
                </TouchableOpacity>
              </View>
            )}
          </View>
        </SafeAreaView>
      </SafeAreaProvider>
    );
  }

  return (
    <SafeAreaProvider>
      <View style={{ flex: 1, backgroundColor: '#000' }}>
        <StatusBar hidden />
        
        {/* Renderizador de Mundo (2D por defecto, Iso opcional) */}
        {viewMode === '2d' ? <Native2DViewport /> : <NativeWorldViewport />}
        
        {/* Capa de Logs Inferior */}
        <LogTicker />

        {/* HUD de Control y Estado */}
        <View style={styles.hudOverlay}>
          <View style={styles.statusBadge}>
            <Globe size={10} color={isConnected ? "#00e676" : "#ff1744"} />
            <Text style={styles.statusText}>{isConnected ? 'SYNCED' : 'OFFLINE'}</Text>
            <View style={styles.badgeDivider} />
            <Text style={styles.statusText}>PASO {step}</Text>
          </View>

          {/* Botones de Arquitecto (Flotantes) */}
          <View style={styles.controlsRow}>
            <TouchableOpacity style={styles.controlFab} onPress={() => sendAction('start')}>
              <Play size={18} color="#fff" />
            </TouchableOpacity>
            <TouchableOpacity style={styles.controlFab} onPress={() => sendAction('pause')}>
              <Pause size={18} color="#fff" />
            </TouchableOpacity>
            <TouchableOpacity style={[styles.controlFab, { backgroundColor: '#333' }]} onPress={() => setViewMode(viewMode === '2d' ? 'iso' : '2d')}>
              <Layers size={18} color="#fff" />
            </TouchableOpacity>
          </View>
        </View>

        {/* Detalle del Agente (Bottom Sheet nativo) */}
        <AgentNativeSheet />
      </View>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#030305',
    justifyContent: 'center',
    padding: 30,
  },
  authContainer: {
    alignItems: 'center',
    width: '100%',
  },
  title: {
    fontSize: 42,
    fontWeight: 'bold',
    color: 'white',
    letterSpacing: -2,
    marginBottom: 5,
  },
  subtitle: {
    color: '#666',
    fontSize: 10,
    textTransform: 'uppercase',
    letterSpacing: 4,
    marginBottom: 40,
  },
  inputGroup: {
    width: '100%',
    marginBottom: 20,
  },
  label: {
    color: '#444',
    fontSize: 10,
    fontWeight: 'bold',
    textTransform: 'uppercase',
    marginBottom: 8,
  },
  input: {
    backgroundColor: 'rgba(255,255,255,0.05)',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.1)',
    borderRadius: 12,
    padding: 15,
    color: 'white',
    fontSize: 14,
  },
  button: {
    backgroundColor: '#7c4dff',
    width: '100%',
    padding: 18,
    borderRadius: 12,
    alignItems: 'center',
    marginTop: 10,
    shadowColor: '#7c4dff',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
  },
  buttonText: {
    color: 'white',
    fontWeight: '900',
    fontSize: 12,
    letterSpacing: 1,
  },
  settingsButton: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 40,
    gap: 8,
  },
  settingsText: {
    color: '#666',
    fontSize: 10,
    fontWeight: 'bold',
    textTransform: 'uppercase',
  },
  toggleButton: {
    marginTop: 25,
    padding: 10,
    width: '100%',
    alignItems: 'center',
  },
  toggleText: {
    color: '#7c4dff',
    fontSize: 12,
    fontWeight: 'bold',
  },
  settingsPanel: {
    width: '100%',
    marginTop: 20,
    padding: 20,
    backgroundColor: 'rgba(255,255,255,0.03)',
    borderRadius: 15,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.05)',
  },
  inputSmall: {
    backgroundColor: 'black',
    borderRadius: 8,
    padding: 10,
    color: '#aaa',
    fontSize: 12,
    marginBottom: 10,
  },
  saveButton: {
    backgroundColor: '#333',
    padding: 10,
    borderRadius: 8,
    alignItems: 'center',
  },
  saveButtonText: {
    color: 'white',
    fontSize: 10,
    fontWeight: 'bold',
  },
  hudOverlay: {
    position: 'absolute',
    top: 50,
    left: 20,
    right: 20,
    zIndex: 100,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
  },
  statusBadge: {
    flexDirection: 'row',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
    backgroundColor: 'rgba(10,11,16,0.9)',
    alignItems: 'center',
    gap: 8,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.1)',
  },
  badgeDivider: {
    width: 1,
    height: 10,
    backgroundColor: 'rgba(255,255,255,0.2)',
  },
  statusText: {
    color: 'white',
    fontSize: 9,
    fontWeight: '900',
    letterSpacing: 0.5,
  },
  controlsRow: {
    flexDirection: 'row',
    gap: 10,
  },
  controlFab: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: '#7c4dff',
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.5,
    shadowRadius: 5,
    elevation: 8,
  },
});
