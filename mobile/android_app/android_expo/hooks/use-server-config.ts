
import { useState, useEffect } from 'react';
// import AsyncStorage from '@react-native-async-storage/async-storage'; 
// Usaremos un hook simple por ahora hasta que podamos instalar persistencia real

const DEFAULT_IP = 'api-mundoia.cuerpolibre.cl';
const DEFAULT_FRONTEND_PORT = '443';
const DEFAULT_API_PORT = '';

export function useServerConfig() {
  const [config, setConfig] = useState({
    ip: DEFAULT_IP,
    frontendPort: DEFAULT_FRONTEND_PORT,
    apiPort: DEFAULT_API_PORT,
  });

  const getFrontendUrl = () => config.ip.includes('cuerpolibre.cl') ? `https://${config.ip}` : `http://${config.ip}:${config.frontendPort}`;
  const getApiHost = () => config.apiPort ? `${config.ip}:${config.apiPort}` : config.ip;

  return {
    ...config,
    setConfig,
    frontendUrl: getFrontendUrl(),
    apiHost: getApiHost(),
  };
}
