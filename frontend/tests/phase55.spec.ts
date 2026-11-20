import { expect, test, type Page } from "@playwright/test";
import { mkdir } from "node:fs/promises";

const lines = ".source-editor .view-lines";
const capture = process.env.INTENTFORGE_PHASE55_CAPTURES;

async function openSource(page: Page, source: string) {
  await page.goto("/");
  await page.locator(lines).click();
  await page.keyboard.press("Control+A");
  await page.keyboard.insertText(source);
}

test("precision mode explains a withheld hypothesis and drops stale evidence", async ({ page }) => {
  await openSource(page, "int f(int x,int y,int z,int rebate){int total=0;total+=x;total+=y;total+=z;total-=rebate;return total;}");
  await page.getByRole("tab", { name: "Intention", exact: true }).click();
  await page.getByLabel("Intention engine").selectOption("55");
  await page.getByLabel("Analysis mode").selectOption("code_only");
  await page.getByRole("button", { name: "Analyze Intention", exact: true }).click();
  const result = page.getByRole("region", { name: "Intention results" });
  const withheld = result.getByRole("region", { name: "Withheld structural hypotheses" });
  await expect(withheld).toContainText("Distinct inputs may legitimately have different signs.");
  await expect(withheld).toContainText("adjacent updates");
  await expect(result.getByRole("button", { name: "Apply Reviewed Intention Repair" })).toHaveCount(0);
  if (capture) {
    await mkdir(capture, { recursive: true });
    await result.screenshot({ path: `${capture}/withheld-evidence.png` });
  }
  await page.locator(lines).click();
  await page.keyboard.insertText(" ");
  await expect(result).toHaveCount(0);
});

test("precision behavior stays isolated and explicit approval is still required", async ({ page }) => {
  test.skip(!process.env.INTENTFORGE_VM_SOCKET, "Requires the verified Linux worker");
  await openSource(page, "int f(int left,int right){return missing;}");
  await page.getByText("Interactive behavioral verification", { exact: true }).click();
  const panel = page.getByLabel("Interactive behavioral verification", { exact: true });
  await panel.getByLabel("Entry point").fill("f");
  await panel.getByLabel("Compare repair candidates").check();
  await panel.getByLabel("Phase 5 repair and probes").check();
  await panel.getByLabel("Phase 5.5 precision gates").check();
  const vectors = panel.getByLabel("Test vectors (JSON)");
  await vectors.fill('[{"arguments":[2,2],"expected":2}]');
  await panel.getByRole("button", { name: "Run verification" }).click();
  await expect(panel.getByText("Multiple candidates match. More test cases may distinguish them.")).toBeVisible();
  await panel.getByRole("button", { name: "Review candidate 1" }).click();
  const approval = panel.getByRole("button", { name: "Apply reviewed behavioral repair" });
  await expect(approval).toBeVisible();
  await expect(page.locator(lines)).toContainText("return missing");
  if (capture) {
    await mkdir(capture, { recursive: true });
    await panel.screenshot({ path: `${capture}/isolated-ambiguity.png` });
  }
  await panel.getByLabel("Phase 5.5 precision gates").uncheck();
  await expect(approval).toHaveCount(0);
  await expect(panel.getByText("Live interpreter evidence")).toHaveCount(0);
  await expect(page.locator(lines)).toContainText("return missing");
});
