import { defineConfig } from "@playwright/test";

const backendPort = Number(process.env.INTENTFORGE_BACKEND_PORT ?? 8000);
const preview = process.env.INTENTFORGE_PRODUCT_PREVIEW === "1";
const frontendURL = `http://127.0.0.1:${preview ? 4173 : 5173}`;
const browserExecutable = process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE;

export default defineConfig({
  testDir: "./tests",
  fullyParallel: false,
  workers: 1,
  timeout: 45000,
  use: {
    baseURL: frontendURL,
    browserName: "chromium",
    launchOptions: browserExecutable ? { executablePath: browserExecutable } : undefined,
    headless: true,
    viewport: { width: 1440, height: 1000 },
  },
  webServer: [
    {
      command: preview ? "npm run preview" : "npm run dev",
      url: frontendURL,
      reuseExistingServer: true,
    },
    {
      command: `python -m uvicorn backend.app.main:app --host 127.0.0.1 --port ${backendPort}`,
      cwd: "..",
      url: `http://127.0.0.1:${backendPort}/health`,
      reuseExistingServer: true,
    },
  ],
});
