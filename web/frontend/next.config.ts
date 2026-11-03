import type { NextConfig } from "next";

const isExport = process.env.NEXT_OUTPUT_EXPORT === "true";
const backendInternalUrl = process.env.BACKEND_INTERNAL_URL || "http://mundoia-backend:8000";

const nextConfig: NextConfig = {
  ...(isExport ? { output: "export" } : {}),
  images: {
    unoptimized: true,
  },
  allowedDevOrigins: [
    "mundoia.kognitoai.cloud",
    "*.kognitoai.cloud",
    "mundoia.cuerpolibre.cl",
    "api-mundoia.cuerpolibre.cl",
    "*.cuerpolibre.cl",
    "192.168.1.58",
    "localhost",
    "127.0.0.1",
    "host.docker.internal",
  ],
  ...(!isExport
    ? {
        async rewrites() {
          return [
            {
              source: "/auth/:path+",
              destination: `${backendInternalUrl}/auth/:path+`,
            },
            {
              source: "/game/:path+",
              destination: `${backendInternalUrl}/game/:path+`,
            },
            {
              source: "/games/:path*",
              destination: `${backendInternalUrl}/games/:path*`,
            },
            {
              source: "/multiplayer/:path*",
              destination: `${backendInternalUrl}/multiplayer/:path*`,
            },
            {
              source: "/config/:path*",
              destination: `${backendInternalUrl}/config/:path*`,
            },
            {
              source: "/chat/:path*",
              destination: `${backendInternalUrl}/chat/:path*`,
            },
            {
              source: "/social/:path*",
              destination: `${backendInternalUrl}/social/:path*`,
            },
            {
              source: "/agents/:path*",
              destination: `${backendInternalUrl}/agents/:path*`,
            },
          ];
        },
      }
    : {}),
};

export default nextConfig;
