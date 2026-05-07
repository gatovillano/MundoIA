import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'export',
  images: {
    unoptimized: true,
  },
  allowedDevOrigins: [
    'mundoia.cuerpolibre.cl',
    'api-mundoia.cuerpolibre.cl',
    '192.168.1.58',
    'localhost',
    '127.0.0.1',
    'host.docker.internal',
  ],
};

export default nextConfig;
