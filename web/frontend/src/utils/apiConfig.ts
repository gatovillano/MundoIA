/**
 * Centralized API configuration for MundoIA.
 * Allows switching between local development and production environments.
 */

// Default API URL/Host from environment variable or fallback to localhost
const DEFAULT_API_URL = process.env.NEXT_PUBLIC_API_URL || '';
const DEFAULT_API_HOST = process.env.NEXT_PUBLIC_API_HOST || 'localhost:8005';

/**
 * Gets the current API host/URL from localStorage or defaults to the environment config.
 * Returns a full URL if available, or just the host.
 */
export const getApiBase = (): string => {
    if (typeof window !== 'undefined') {
        const stored = localStorage.getItem('MUNDOIA_API_HOST');
        if (stored) return stored;
        
        const host = window.location.host;
        if (host && !host.includes('localhost') && !host.includes('127.0.0.1')) {
            // Si estamos en mundoia.cuerpolibre.cl, la API está en api-mundoia.cuerpolibre.cl
            if (host === 'mundoia.cuerpolibre.cl' || host.includes('mundoia.cuerpolibre.cl')) {
                return 'api-mundoia.cuerpolibre.cl';
            }
            // Para otros dominios, usar el host actual
            return host;
        }
    }
    return DEFAULT_API_URL || DEFAULT_API_HOST;
};

/**
 * Constructs a full HTTP/HTTPS URL for API requests.
 */
export const getHttpUrl = (path: string): string => {
    const base = getApiBase();
    let url = base;

    // If base doesn't start with http, prepend protocol
    if (!base.startsWith('http://') && !base.startsWith('https://')) {
        const protocol = base.includes('localhost') || base.includes('127.0.0.1') ? 'http' : 'https';
        url = `${protocol}://${base}`;
    }

    if (!path) return url;
    const cleanPath = path.startsWith('/') ? path : `/${path}`;
    return `${url}${cleanPath}`;
};

/**
 * Constructs a full WS/WSS URL for WebSocket connections.
 */
export const getWsUrl = (path: string): string => {
    const base = getApiBase();
    let url = base;

    // Convert http to ws or handle host-only
    if (base.startsWith('https://')) {
        url = base.replace('https://', 'wss://');
    } else if (base.startsWith('http://')) {
        url = base.replace('http://', 'ws://');
    } else {
        const protocol = base.includes('localhost') || base.includes('127.0.0.1') ? 'ws' : 'wss';
        url = `${protocol}://${base}`;
    }

    if (!path) return url;
    const cleanPath = path.startsWith('/') ? path : `/${path}`;
    return `${url}${cleanPath}`;
};

// Compatibility export for old code
export const getApiHost = getApiBase;
