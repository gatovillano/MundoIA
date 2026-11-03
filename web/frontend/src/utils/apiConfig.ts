/**
 * Centralized API configuration for MundoIA.
 * Allows switching between local development, LAN, and production tunnel environments.
 */

const DEFAULT_API_URL = process.env.NEXT_PUBLIC_API_URL || '';
const DEFAULT_API_HOST = process.env.NEXT_PUBLIC_API_HOST || 'localhost:8005';

function isLocalhost(hostOrUrl: string): boolean {
    return hostOrUrl.includes('localhost') || hostOrUrl.includes('127.0.0.1');
}

function isPrivateLanIp(hostname: string): boolean {
    return (
        /^192\.168\.\d+\.\d+$/.test(hostname) ||
        /^10\.\d+\.\d+\.\d+$/.test(hostname) ||
        /^172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+$/.test(hostname)
    );
}

/**
 * Gets the current API host/URL from localStorage or defaults to the environment/window config.
 * Returns a full URL if available, or just the host.
 */
export const getApiBase = (): string => {
    if (typeof window !== 'undefined') {
        const host = window.location.host;
        const hostname = window.location.hostname;
        const onLocalBrowser = isLocalhost(hostname);

        const stored = localStorage.getItem('MUNDOIA_API_HOST');
        // Ignore stale localhost override when browsing from a remote domain or LAN IP
        if (stored && (onLocalBrowser || !isLocalhost(stored))) {
            return stored;
        }

        if (host && !onLocalBrowser) {
            if (host === 'mundoia.cuerpolibre.cl' || host.includes('mundoia.cuerpolibre.cl')) {
                return 'api-mundoia.cuerpolibre.cl';
            }
            // If accessed via LAN IP (e.g. 192.168.1.58:3005), point directly to backend port 8005 on that IP
            if (isPrivateLanIp(hostname)) {
                return `${hostname}:8005`;
            }
            // For tunnel/production domains (e.g. mundoia.kognitoai.cloud), use the current host (proxied by dev-proxy.mjs)
            return host;
        }
    }
    return DEFAULT_API_URL || DEFAULT_API_HOST;
};

/**
 * Resolves the appropriate HTTP protocol ('http' or 'https') for a given base host.
 */
function resolveHttpProtocol(base: string): 'http' | 'https' {
    const cleanHost = base.replace(/^https?:\/\//, '').split('/')[0].split(':')[0];
    if (isLocalhost(base) || isPrivateLanIp(cleanHost)) {
        return 'http';
    }
    if (typeof window !== 'undefined' && window.location.protocol === 'http:') {
        return 'http';
    }
    return 'https';
}

/**
 * Constructs a full HTTP/HTTPS URL for API requests.
 */
export const getHttpUrl = (path: string): string => {
    const base = getApiBase();
    let url = base;

    if (!base.startsWith('http://') && !base.startsWith('https://')) {
        const protocol = resolveHttpProtocol(base);
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

    if (base.startsWith('https://')) {
        url = base.replace('https://', 'wss://');
    } else if (base.startsWith('http://')) {
        url = base.replace('http://', 'ws://');
    } else {
        const httpProto = resolveHttpProtocol(base);
        const wsProto = httpProto === 'https' ? 'wss' : 'ws';
        url = `${wsProto}://${base}`;
    }

    if (!path) return url;
    const cleanPath = path.startsWith('/') ? path : `/${path}`;
    return `${url}${cleanPath}`;
};

// Compatibility export for old code
export const getApiHost = getApiBase;
