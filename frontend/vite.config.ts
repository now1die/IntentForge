import { defineConfig, type ProxyOptions } from "vite";
import react from "@vitejs/plugin-react";

const backendPort = Number(process.env.INTENTFORGE_BACKEND_PORT ?? 8000);
if (!Number.isInteger(backendPort) || backendPort < 1 || backendPort > 65535) {
  throw new Error("INTENTFORGE_BACKEND_PORT must be a valid TCP port");
}

// Match only public workbench routes. The backend still owns execution access.
const proxy: Record<string, ProxyOptions> = {
  "^/api/(?:health|analyze|correct|correction-options|validate-correction|tokens|ast|symbols|v1/(?:intention-analysis|compiler-evidence|c-analysis(?:/capability)?|behavioral-verification(?:/capability)?))/?(?:\\?.*)?$": {
    target: `http://127.0.0.1:${backendPort}`,
    rewrite: (path) => path.slice(4),
  },
};

function forwardedHost(port: number): string[] {
  const name = process.env.CODESPACE_NAME;
  const domain = process.env.GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN ?? "app.github.dev";
  return name && /^[a-z0-9-]+$/.test(name) && /^[a-z0-9.-]+$/.test(domain)
    ? [`${name}-${port}.${domain}`]
    : [];
}

export default defineConfig({
  plugins: [react()],
  server: { port: 5173, strictPort: true, allowedHosts: forwardedHost(5173), proxy },
  preview: { port: 4173, strictPort: true, allowedHosts: forwardedHost(4173), proxy },
});
