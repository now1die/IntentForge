import { execFileSync } from "node:child_process";
import { mkdir, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { expect, test, type Page } from "@playwright/test";
import { DEFAULT_CODE, examples } from "../src/constants/examples";

const output = resolve(process.env.INTENTFORGE_EVIDENCE_DIR ?? "../audit/phase1-final");

async function enter(page: Page, source: string) {
  await page.locator(".source-editor .view-lines").click();
  await page.keyboard.press("Control+A");
  await page.keyboard.insertText(source);
  await expect(page.getByRole("status")).toContainText("Source changed");
}

async function analyze(page: Page, expected: string) {
  await page.getByRole("button", { name: "Analyze", exact: true }).click();
  await expect(page.getByRole("status")).toContainText(expected);
}

async function correct(page: Page) {
  const response = page.waitForResponse((reply) => new URL(reply.url()).pathname === "/correct"
    && reply.request().method() === "POST");
  await page.getByRole("button", { name: "Correct", exact: true }).click();
  return (await response).json();
}

test("capture Phase 1 evidence from the running workbench", async ({ page, browser }) => {
  await mkdir(output, { recursive: true });
  const records = [];
  const capture = async (name: string, source: string) => {
    await page.evaluate(() => document.fonts.ready);
    await page.screenshot({ path: resolve(output, name), animations: "disabled" });
    records.push({ file: name, viewport: page.viewportSize(), source,
      status: await page.getByRole("status").textContent() });
  };

  await page.goto("/");
  await expect(page.getByText("Backend connected", { exact: true })).toBeVisible();
  await expect(page.locator(".source-editor .monaco-editor")).toBeVisible();
  const healthResponse = await page.request.get("http://127.0.0.1:8000/health");
  expect(healthResponse.ok()).toBeTruthy();
  const health = await healthResponse.json();
  expect(health.ml_model_loaded).toBe(true);
  await capture("01-main-workbench.png", DEFAULT_CODE);

  await enter(page, examples["Broken If"]);
  const structural = await correct(page);
  expect(structural.history[0].safety.category).toBe("LOW_RISK_STRUCTURAL");
  await expect(page.getByRole("button", { name: "Apply Corrected Code" })).toBeEnabled();
  await capture("02-safe-structural.png", examples["Broken If"]);

  const operator = "int main(){ int a,b; if(a.b){return 0;} }";
  await enter(page, operator);
  const review = await correct(page);
  expect(review.corrections_applied).toBe(0);
  expect(review.history[0].safety.requires_review).toBe(true);
  await expect(page.locator(".history")).toContainText("Review required");
  await expect(page.getByRole("button", { name: "Apply Corrected Code" })).toBeDisabled();
  await page.locator(".history article").first().scrollIntoViewIfNeeded();
  await capture("03-review-required.png", operator);

  const ambiguous = "int main(){ int wet=2,dry=3; return wet dry; }";
  await enter(page, ambiguous);
  const uncertain = await correct(page);
  expect(uncertain.stop_reason).toBe("ambiguous_valid_candidates");
  expect(uncertain.corrected_code).toBe(ambiguous);
  await expect(page.locator(".suggestion-card")).toHaveCount(2);
  await page.locator(".suggestion-list").scrollIntoViewIfNeeded();
  await capture("04-ambiguous-intent.png", ambiguous);

  await enter(page, operator);
  await correct(page);
  await page.getByRole("button", { name: /Option.*a>b/ }).first().click();
  await expect(page.locator(".selected-preview")).toContainText("Selected preview");
  await page.locator(".selected-preview").scrollIntoViewIfNeeded();
  await capture("05-before-after.png", operator);

  await enter(page, examples["Broken If"]);
  await analyze(page, "Diagnostics available");
  await expect(page.locator(".diagnostic-row").first()).toBeVisible();
  await capture("06a-syntax-diagnostics.png", examples["Broken If"]);

  const semantic = "int main(){ int count = 4; return missing + count; }";
  await enter(page, semantic);
  await analyze(page, "Diagnostics available");
  await expect(page.locator(".analysis-panel")).toContainText(/semantic/i);
  await capture("06b-semantic-diagnostics.png", semantic);

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await analyze(page, "All checks passed");
  await capture("07-mobile.png", DEFAULT_CODE);

  await page.setViewportSize({ width: 1440, height: 900 });
  await page.getByRole("tab", { name: "Symbol Table" }).click();
  await expect(page.getByRole("cell", { name: "main", exact: true })).toBeVisible();
  await capture("08-desktop.png", DEFAULT_CODE);

  const revision = execFileSync("git", ["rev-parse", "HEAD"], { encoding: "utf8" }).trim();
  await writeFile(resolve(output, "capture-metadata.json"), JSON.stringify({
    revision, browser: browser.version(), backend: "Local FastAPI, real responses",
    frontend: "Local Vite and Monaco", fixtures: "Repository-owned source inputs. No request mocking.",
    ollamaConfigured: health.ollama_configured, records,
  }, null, 2) + "\n");
});
