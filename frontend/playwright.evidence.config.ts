import { defineConfig } from "@playwright/test";
import base from "./playwright.config";

export default defineConfig({
  ...base,
  testDir: "./evidence",
  use: { ...base.use, viewport: { width: 1440, height: 900 } },
});
