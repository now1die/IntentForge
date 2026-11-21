import { expect, test, type Page } from "@playwright/test";
import { mkdir } from "node:fs/promises";

const original = "int f(int n){\n  if(n<=1){return n;}\n  return f(n-1)-f(n-2);\n}";
const editor = ".source-editor .view-lines";
const captures = process.env.INTENTFORGE_PHASE7_CAPTURES;

async function openSource(page: Page) {
  await page.goto("/");
  await page.locator(editor).click();
  await page.keyboard.press("Control+A");
  await page.keyboard.insertText(original);
}

async function saveCapture(region: ReturnType<Page["locator"]>, name: string) {
  if (captures) {
    await mkdir(captures, { recursive: true });
    await region.screenshot({ path: `${captures}/${name}.png` });
  }
}

test("Phase 7 static examples show possible repairs and await verified behavior", async ({ page }) => {
  await openSource(page);
  await page.getByRole("tab", { name: "Intention", exact: true }).click();
  await page.getByLabel("Intention engine").selectOption("7");
  await page.getByLabel("Analysis mode").selectOption("examples");
  await page.getByLabel("Function").fill("f");
  await page.getByText("Expression locations and input/output examples", { exact: true }).click();
  await page.getByRole("textbox", { name: "Input/output examples", exact: true }).fill('[{"args":[4],"expected_return":3}]');
  await page.getByRole("button", { name: "Analyze Intention", exact: true }).click();
  const result = page.getByRole("region", { name: "Intention results" });
  await expect(result.getByRole("heading", { name: "Possible repairs" })).toBeVisible();
  await expect(result).toContainText("Original behavior awaits isolated verification");
  await expect(result.getByRole("button", { name: /Review .* recurrence operator mismatch/ })).toHaveCount(2);
  await page.getByRole("textbox", { name: "Input/output examples", exact: true }).fill('[{"args":[4],"expected_return":-1}]');
  await expect(result).toHaveCount(0);
});

test("Phase 7 separates original agreement from confirmed mismatch and keeps approval explicit", async ({ page }) => {
  test.skip(!process.env.INTENTFORGE_VM_SOCKET, "Requires the restricted Linux worker");
  await openSource(page);
  await page.getByText("Interactive behavioral verification", { exact: true }).click();
  const panel = page.getByLabel("Interactive behavioral verification", { exact: true });
  await panel.getByLabel("Entry point").fill("f");
  await panel.getByLabel("Compare repair candidates").check();
  await panel.getByLabel("Phase 5 repair and probes").check();
  await panel.getByLabel("Phase 7 guided repair precision").check();
  const testInput = panel.getByLabel("Test vectors (JSON)");
  const run = panel.getByRole("button", { name: "Run verification" });
  const evidence = panel.getByRole("region", { name: "Guided repair evidence" });
  await testInput.fill('[{"arguments":[4],"expected":-1}]');
  await run.click();
  await expect(evidence.getByRole("status")).toHaveText("Original matches supplied tests");
  await expect(panel.getByRole("button", { name: /Review candidate/ })).toHaveCount(2);
  await expect(panel.getByText("Eligible for guided review", { exact: true })).toHaveCount(0);
  await saveCapture(panel, "original-matches");
  await testInput.fill('[{"arguments":[4],"expected":3}]');
  await expect(evidence).toHaveCount(0);
  await run.click();
  await expect(evidence.getByRole("alert")).toHaveText("Confirmed mismatch on supplied tests");
  await expect(panel.getByText("Eligible for guided review", { exact: true })).toBeVisible();
  const recommended = panel.locator("article").filter({ hasText: "Eligible for guided review" });
  await recommended.getByRole("button", { name: /Review candidate/ }).click();
  await expect(panel.getByRole("region", { name: "Behavioral candidate review" }).locator(".diff-after")).toContainText("f(n-1)+f(n-2)");
  await expect(panel.getByRole("button", { name: "Apply reviewed behavioral repair" })).toBeVisible();
  await expect(page.locator(editor)).toContainText("f(n-1)-f(n-2)");
  await saveCapture(panel, "confirmed-mismatch");
  await panel.getByLabel("Step limit").fill("3000");
  await expect(panel.getByRole("button", { name: "Apply reviewed behavioral repair" })).toHaveCount(0);
});
