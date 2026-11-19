import { expect, test, type Page } from "@playwright/test";
import { mkdir } from "node:fs/promises";

const editor = ".source-editor .view-lines";
const capture = process.env.INTENTFORGE_PHASE5_CAPTURES;

async function source(page: Page, text: string) {
  await page.goto("/");
  await page.locator(editor).click();
  await page.keyboard.press("Control+A");
  await page.keyboard.insertText(text);
}

test("Phase 5 structural evidence explains a two-edit repair before approval", async ({ page }) => {
  await source(page, "int delta(int a,int b){return b-a;} int f(int x,int y){return delta(x,y)+delta(y,x)+delta(x,y);}");
  await page.getByRole("tab", { name: "Intention", exact: true }).click();
  await page.getByLabel("Intention engine").selectOption("5");
  await page.getByLabel("Analysis mode").selectOption("code_only");
  await page.getByRole("button", { name: "Analyze Intention", exact: true }).click();
  const result = page.getByRole("region", { name: "Intention results" });
  await expect(result.getByRole("region", { name: "Structural scan" })).toContainText("reverses two");
  await result.getByRole("button", { name: /Review 1 · argument role permutation/ }).click();
  const preview = result.getByRole("region", { name: "Selected intention repair" });
  await expect(preview.locator(".inline-diff")).toHaveCount(2);
  await expect(page.locator(editor)).toContainText("delta(y,x)");
  if (capture) {
    await mkdir(capture, { recursive: true });
    await result.screenshot({ path: `${capture}/structural-review.png` });
  }
  await preview.getByRole("button", { name: "Apply Reviewed Intention Repair" }).click();
  await expect(page.locator(editor)).not.toContainText("delta(y,x)");
  await expect(result).toHaveCount(0);
});

test("Phase 5 isolated probes require an explicit expectation before resolving ambiguity", async ({ page }) => {
  test.skip(!process.env.INTENTFORGE_VM_SOCKET, "Requires the verified Mini-C worker");
  await source(page, "int f(int left,int right){return missing;}");
  await page.getByText("Interactive behavioral verification", { exact: true }).click();
  const panel = page.getByLabel("Interactive behavioral verification", { exact: true });
  await panel.getByLabel("Entry point").fill("f");
  await panel.getByLabel("Compare repair candidates").check();
  await panel.getByLabel("Phase 5 repair and probes").check();
  const run = panel.getByRole("button", { name: "Run verification" });
  await run.click();
  await expect(panel.getByText(/Observational comparison/)).toBeVisible();
  const probes = panel.getByRole("region", { name: "Candidate disagreement" });
  const distinct = probes.getByRole("listitem").filter({ hasText: "different values" }).first();
  await expect(distinct).toContainText("1 pair (1 new)");
  if (capture) {
    await mkdir(capture, { recursive: true });
    await panel.screenshot({ path: `${capture}/isolated-probes.png` });
  }
  await distinct.getByRole("button", { name: "Use probe input" }).click();
  const vectors = panel.getByLabel("Test vectors (JSON)");
  await expect(vectors).toHaveValue(/"expected": null/);
  await run.click();
  await expect(panel.getByRole("alert")).toContainText("explicit expected value");
  const rows = JSON.parse(await vectors.inputValue());
  rows[0].expected = rows[0].arguments[0];
  await vectors.fill(JSON.stringify(rows));
  await run.click();
  await expect(panel.getByText("Matches supplied tests", { exact: true })).toHaveCount(1);
  await expect(panel.getByText("Mismatches supplied tests", { exact: true })).toHaveCount(1);
  await expect(page.locator(editor)).toContainText("return missing");
});
