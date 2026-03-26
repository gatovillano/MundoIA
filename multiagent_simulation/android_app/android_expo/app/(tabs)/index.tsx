import React from 'react';
import { StyleSheet, View, StatusBar, SafeAreaView } from 'react-native';
import { WebView } from 'react-native-webview';

export default function HomeScreen() {
  // --- CONFIGURACIÓN DE URL ---
  // MODO LOCAL (Para pruebas en casa)
  const localIp = '192.168.1.58'; 
  const frontendUrl = `http://${localIp}:3005`;
  const apiHost = `${localIp}:8005`;

  // MODO PRODUCCIÓN (Para entrar desde cualquier lugar)
  // Descomenta estas líneas y comenta las de arriba cuando subas el servidor
  /*
  const frontendUrl = 'https://mundoia.cuerpolibre.cl';
  const apiHost = 'api-mundoia.cuerpolibre.cl';
  */

  // Script para inyectar la URL del backend automáticamente
  const injectedJs = `
    localStorage.setItem('MUNDOIA_API_HOST', '${apiHost}');
    true;
  `;

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor="#000" />
      <View style={styles.webviewContainer}>
        <WebView 
          source={{ uri: frontendUrl }} 
          style={styles.webview} 
          javaScriptEnabled={true}
          domStorageEnabled={true}
          injectedJavaScript={injectedJs}
          startInLoadingState={true}
          scalesPageToFit={true}
        />
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000',
  },
  webviewContainer: {
    flex: 1,
  },
  webview: {
    flex: 1,
    backgroundColor: '#000',
  },
});
