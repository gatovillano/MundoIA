/**
 * Centralized API configuration for MundoIA.
 * Allows switching between local development and production environments.
 */

// Default API host from environment variable or fallback to localhost
const DEFAULT_API_HOST = process.env.NEXT_PUBLIC_API_HOST || 'localhost:8005';

/**
 * Gets the current API host from localStorage or defaults to the environment config.
 */
export const getApiHost = (): string => {
    if (typeof window !== 'undefined') {
        return localStorage.getItem('MUNDOIA_API_HOST') || DEFAULT_API_HOST;
    }
    return DEFAULT_API_HOST;
};

/**
 * Constructs a full HTTP/HTTPS URL for API requests.
 */
export const getHttpUrl = (path: string): string => {
    const host = getApiHost();
    const protocol = host.includes('localhost') || host.includes('127.0.0.1') ? 'http' : 'https';
    if (!path) return `${protocol}://${host}`;
    const cleanPath = path.startsWith('/') ? path : `/${path}`;
    return `${protocol}://${host}${cleanPath}`;
};

/**
 * Constructs a full WS/WSS URL for WebSocket connections.
 */
export const getWsUrl = (path: string): string => {
    const host = getApiHost();
    const protocol = host.includes('localhost') || host.includes('127.0.0.1') ? 'ws' : 'wss';
    if (!path) return `${protocol}://${host}`;
    const cleanPath = path.startsWith('/') ? path : `/${path}`;
    return `${protocol}://${host}${cleanPath}`;
};
