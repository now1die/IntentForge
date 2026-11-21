import { expect, test, type Page } from "@playwright/test";
import { mkdir } from "node:fs/promises";

const editor = ".source-editor .view-lines";
const capture = process.env.INTENTFORGE_PHASE6_CAPTURES;

async function writeSource(page: Page, source: string) {
  await page.goto("/");
  await page.locator(editor).click();
  await page.keyboard.press("Control+A");
  await page.keyboard.insertText(source);
}

test("Phase 6 shows return dependencies and both edit spans before approval", async ({ page }) => {
  await writeSource(page, "int f(int n,bool high){int raw=n+2;int scaled=raw*3;int adjusted=scaled+5;if(high){return raw;}return raw;}");
  await page.getByRole("tab", { name: "Intention", exact: true }).click();
  await page.getByLabel("Intention engine").selectOption("6");
  await page.getByLabel("Analysis mode").selectOption("code_only");
  await page.getByRole("button", { name: "Analyze Intention", exact: true }).click();
  const result = page.getByRole("region", { name: "Intention results" });
  const evidence = result.getByRole("region", { name: "Program-level evidence" });
  await evidence.getByText("f(int n, bool high) · int", { exact: true }).click();
  await expect(evidence.getByRole("list", { name: "Return dependencies" })).toContainText("raw (line 1)");
  await result.getByRole("button", { name: /Review 1 · return dependency mismatch/ }).click();
  const repair = result.getByRole("region", { name: "Selected intention repair" });
  await expect(repair.locator(".inline-diff")).toHaveCount(2);
  await expect(repair.getByRole("list", { name: "Counter-evidence and missing assumptions" })).toBeVisible();
  await expect(page.locator(editor)).toContainText("return raw");
  if (capture) {
    await mkdir(capture, { recursive: true });
    await result.screenshot({ path: `${capture}/return-dependencies.png` });
  }
  await repair.getByRole("button", { name: "Apply Reviewed Intention Repair" }).click();
  await expect(page.locator(editor)).toContainText("return adjusted");
  await expect(result).toHaveCount(0);
});

test("Phase 6 live recursion distinguishes call-depth failure from test agreement", async ({ page }) => {
  test.skip(!process.env.INTENTFORGE_VM_SOCKET, "Requires the restricted Linux worker");
  await writeSource(page, "int f(int n){if(n<=0){return 0;}return 2+f(n);}");
  await page.getByText("Interactive behavioral verification", { exact: true }).click();
  const panel = page.getByLabel("Interactive behavioral verification", { exact: true });
  await panel.getByLabel("Entry point").fill("f");
  await panel.getByLabel("Compare repair candidates").check();
  await panel.getByLabel("Phase 5 repair and probes").check();
  await panel.getByLabel("Phase 6 program reasoning").check();
  await panel.getByLabel("Record trace").check();
  const vectors = panel.getByLabel("Test vectors (JSON)");
  await vectors.fill('[{"arguments":[4],"expected":8}]');
  await panel.getByRole("button", { name: "Run verification" }).click();
  await expect(panel.getByRole("region", { name: "Live original" })).toContainText("CALL_DEPTH");
  await expect(panel.getByRole("region", { name: "Live candidate 1" })).toContainText("Matches supplied tests");
  await panel.getByRole("button", { name: "Review candidate 1" }).click();
  await expect(panel.getByRole("button", { name: "Apply reviewed behavioral repair" })).toBeVisible();
  await expect(page.locator(editor)).toContainText("2+f(n)");
  if (capture) {
    await mkdir(capture, { recursive: true });
    await panel.screenshot({ path: `${capture}/isolated-recursion.png` });
  }
  await vectors.fill('[{"arguments":[5],"expected":10}]');
  await expect(panel.getByText("Live interpreter evidence")).toHaveCount(0);
});
