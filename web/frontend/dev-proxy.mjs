import http from "node:http";
import net from "node:net";
import { spawn } from "node:child_process";

const PROXY_PORT = Number(process.env.PORT || 3000);
const NEXT_PORT = Number(process.env.NEXT_INTERNAL_PORT || 3001);
const BACKEND_HOST = process.env.BACKEND_INTERNAL_HOST || "mundoia-backend";
const BACKEND_PORT = Number(process.env.BACKEND_INTERNAL_PORT || 8000);

/**
 * Determines whether an incoming HTTP or WebSocket request path belongs to the FastAPI backend.
 * Frontend Next.js pages are: /, /auth, /start, /game, /_next/*, static files.
 * Backend FastAPI endpoints are:
 *  - /auth/login, /auth/register (any /auth/... subpath)
 *  - /game/control, /game/speed, /game/god-mode/..., /game/spawn/... (any /game/... subpath)
 *  - /games/...
 *  - /config/...
 *  - /chat/...
 *  - /social/...
 *  - /agents/...
 *  - /ws/...
 */
function isBackendPath(url = "") {
  const pathname = url.split("?")[0];
  if (
    pathname.startsWith("/auth/") &&
    pathname.length > "/auth/".length
  ) {
    return true;
  }
  if (
    pathname.startsWith("/game/") &&
    pathname.length > "/game/".length
  ) {
    return true;
  }
  if (
    pathname.startsWith("/games/") ||
    pathname === "/games" ||
    pathname.startsWith("/config/") ||
    pathname === "/config" ||
    pathname.startsWith("/chat/") ||
    pathname.startsWith("/social/") ||
    pathname.startsWith("/agents/") ||
    pathname.startsWith("/ws/")
  ) {
    return true;
  }
  return false;
}

// 1. Start Next.js dev server on NEXT_PORT (3001)
const nextProc = spawn(
  "npx",
  ["next", "dev", "-H", "127.0.0.1", "-p", String(NEXT_PORT)],
  {
    stdio: "inherit",
    env: {
      ...process.env,
      PORT: String(NEXT_PORT),
    },
  }
);

nextProc.on("exit", (code) => {
  process.exit(code ?? 0);
});

// 2. HTTP Reverse Proxy on PROXY_PORT (3000 -> exposed as 3005 on host)
const server = http.createServer((clientReq, clientRes) => {
  const useBackend = isBackendPath(clientReq.url || "");
  const targetHost = useBackend ? BACKEND_HOST : "127.0.0.1";
  const targetPort = useBackend ? BACKEND_PORT : NEXT_PORT;

  const headers = { ...clientReq.headers };
  if (!useBackend) {
    // Prevent Next.js dev server from rejecting proxied requests due to cross-origin headers
    headers.host = `127.0.0.1:${NEXT_PORT}`;
    if (headers.origin) {
      headers.origin = `http://127.0.0.1:${NEXT_PORT}`;
    }
  } else {
    headers.host = `${BACKEND_HOST}:${BACKEND_PORT}`;
  }

  const proxyReq = http.request(
    {
      hostname: targetHost,
      port: targetPort,
      path: clientReq.url,
      method: clientReq.method,
      headers,
    },
    (proxyRes) => {
      clientRes.writeHead(proxyRes.statusCode || 502, proxyRes.headers);
      proxyRes.pipe(clientRes, { end: true });
    }
  );

  proxyReq.on("error", (err) => {
    if (!clientRes.headersSent) {
      clientRes.writeHead(502, { "Content-Type": "application/json" });
    }
    clientRes.end(
      JSON.stringify({
        detail: `Proxy error connecting to ${useBackend ? "backend" : "frontend"}: ${err.message}`,
      })
    );
  });

  clientReq.pipe(proxyReq, { end: true });
});

// 3. WebSocket Upgrade Tunnel (/ws/* -> FastAPI Backend, /_next/webpack-hmr -> Next.js)
server.on("upgrade", (req, clientSocket, head) => {
  const url = req.url || "";
  const useBackend = url.startsWith("/ws/") || isBackendPath(url);
  const targetHost = useBackend ? BACKEND_HOST : "127.0.0.1";
  const targetPort = useBackend ? BACKEND_PORT : NEXT_PORT;

  const upstreamSocket = net.connect(targetPort, targetHost, () => {
    // Reconstruct raw HTTP Upgrade request
    const lines = [`${req.method || "GET"} ${url} HTTP/${req.httpVersion}`];
    const rawHeaders = req.rawHeaders || [];
    for (let i = 0; i < rawHeaders.length; i += 2) {
      const key = rawHeaders[i];
      let val = rawHeaders[i + 1];
      const lower = key.toLowerCase();
      if (!useBackend) {
        if (lower === "host") val = `127.0.0.1:${NEXT_PORT}`;
        if (lower === "origin") val = `http://127.0.0.1:${NEXT_PORT}`;
      } else {
        if (lower === "host") val = `${BACKEND_HOST}:${BACKEND_PORT}`;
      }
      lines.push(`${key}: ${val}`);
    }
    lines.push("", "");
    upstreamSocket.write(lines.join("\r\n"));
    if (head && head.length > 0) {
      upstreamSocket.write(head);
    }

    upstreamSocket.pipe(clientSocket);
    clientSocket.pipe(upstreamSocket);
  });

  const closeBoth = () => {
    if (!clientSocket.destroyed) clientSocket.destroy();
    if (!upstreamSocket.destroyed) upstreamSocket.destroy();
  };

  upstreamSocket.on("error", closeBoth);
  clientSocket.on("error", closeBoth);
});

server.listen(PROXY_PORT, "0.0.0.0", () => {
  console.log(
    `🚀 [MundoIA Gateway] Listening on http://0.0.0.0:${PROXY_PORT} (Next.js -> 127.0.0.1:${NEXT_PORT}, Backend API/WS -> ${BACKEND_HOST}:${BACKEND_PORT})`
  );
});

process.on("SIGTERM", () => {
  nextProc.kill("SIGTERM");
  server.close(() => process.exit(0));
});
process.on("SIGINT", () => {
  nextProc.kill("SIGINT");
  server.close(() => process.exit(0));
});
