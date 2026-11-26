import { expect, test, type Page } from "@playwright/test";
import { mkdir } from "node:fs/promises";

const editor = ".source-editor .view-lines";
const capture = process.env.INTENTFORGE_PHASE65_CAPTURES;
const source = "int f(int n,int total){\n  if(0>=n){return total;}\n  return f(n,total+3);\n}";

async function openSource(page: Page) {
  await page.goto("/classic");
  await page.locator(editor).click();
  await page.keyboard.press("Control+A");
  await page.keyboard.insertText(source);
}

test("Phase 6.5 shows branch facts, call arguments and a review only diff", async ({ page }) => {
  await openSource(page);
  await page.getByRole("tab", { name: "Intention", exact: true }).click();
  await page.getByLabel("Intention engine").selectOption("65");
  await page.getByLabel("Analysis mode").selectOption("code_only");
  await page.getByRole("button", { name: "Analyze Intention", exact: true }).click();
  const result = page.getByRole("region", { name: "Intention results" });
  await result.getByText("f(int n, int total) · int", { exact: true }).click();
  const evidence = result.getByRole("region", { name: "Path and call evidence" });
  await expect(evidence).toContainText("Return paths");
  await expect(evidence).toContainText("Argument 2 → total · total + 3");
  await expect(evidence).toContainText("n ∈ [-2147483648, 0]");
  await result.getByRole("button", { name: /Review 1 · recursive parameter progress/ }).click();
  const proposed = result.getByRole("region", { name: "Selected intention repair" });
  await expect(proposed).toContainText("Evidence basis · static · Phase 6.5");
  await expect(proposed.getByRole("button", { name: "Apply Reviewed Intention Repair" })).toBeVisible();
  await expect(page.locator(editor)).toContainText("f(n,total+3)");
  if (capture) {
    await mkdir(capture, { recursive: true });
    await result.screenshot({ path: `${capture}/interprocedural-review.png` });
  }
  await page.getByLabel("Intention engine").selectOption("6");
  await expect(result).toHaveCount(0);
});

test("Phase 6.5 isolates a multi-argument runtime failure and invalidates changed tests", async ({ page }) => {
  test.skip(!process.env.INTENTFORGE_VM_SOCKET, "Requires the restricted Linux worker");
  await openSource(page);
  await page.getByText("Interactive behavioral verification", { exact: true }).click();
  const panel = page.getByLabel("Interactive behavioral verification", { exact: true });
  await panel.getByLabel("Entry point").fill("f");
  await panel.getByLabel("Compare repair candidates").check();
  await panel.getByLabel("Phase 5 repair and probes").check();
  await panel.getByLabel("Phase 6.5 interprocedural reasoning").check();
  await panel.getByLabel("Record trace").check();
  const vectors = panel.getByLabel("Test vectors (JSON)");
  await vectors.fill('[{"arguments":[4,2],"expected":14}]');
  await panel.getByRole("button", { name: "Run verification" }).click();
  await expect(panel.getByRole("region", { name: "Live original" })).toContainText("CALL_DEPTH");
  await expect(panel.getByRole("region", { name: "Live candidate 1" })).toContainText("Matches supplied tests");
  await panel.getByRole("button", { name: "Review candidate 1" }).click();
  await expect(panel.getByRole("button", { name: "Apply reviewed behavioral repair" })).toBeVisible();
  await expect(page.locator(editor)).toContainText("f(n,total+3)");
  if (capture) {
    await mkdir(capture, { recursive: true });
    await panel.screenshot({ path: `${capture}/isolated-multi-argument.png` });
  }
  await vectors.fill('[{"arguments":[5,2],"expected":17}]');
  await expect(panel.getByText("Live interpreter evidence")).toHaveCount(0);
});
