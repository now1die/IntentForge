import { expect, test, type Page } from "@playwright/test";
import { mkdir } from "node:fs/promises";

const live = !!process.env.INTENTFORGE_VM_SOCKET;
const sourceLines = ".source-editor .view-lines";

async function openPanel(page: Page, source: string) {
  await page.goto("/");
  await page.locator(sourceLines).click();
  await page.keyboard.press("Control+A");
  await page.keyboard.insertText(source);
  await page.getByText("Interactive behavioral verification", { exact: true }).click();
  return page.getByLabel("Interactive behavioral verification", { exact: true });
}

test("hosted/default workbench explains disabled execution and keeps recorded evidence", async ({ page }) => {
  test.skip(live, "This test checks the default-disabled profile");
  await page.goto("/");
  await page.getByText("Interactive behavioral verification", { exact: true }).click();
  await expect(page.getByText("Interactive execution is disabled on this deployment.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Run verification" })).toHaveCount(0);
  await page.getByText("Behavioral verification", { exact: true }).click();
  await expect(page.getByRole("button", { name: "Load trusted example" })).toBeVisible();
});

test("isolated editor run shows before and after and requires manual approval", async ({ page }) => {
  test.skip(!live, "An actual isolated VM service is required");
  const panel = await openPanel(page, "int f(int x){return x+2;}");
  await panel.getByLabel("Entry point").fill("f");
  await panel.getByLabel("Test vectors (JSON)").fill('[{"arguments":[4],"expected":8}]');
  await panel.getByLabel("Compare repair candidates").check();
  await panel.getByLabel("Expected return expression (optional)").fill("x*2");
  await panel.getByLabel("Record trace").check();
  await panel.getByRole("button", { name: "Run verification" }).click();
  await expect(panel.getByRole("region", { name: "Live original" }).getByRole("row", { name: /\[4\] 8 6 Fail/ })).toBeVisible();
  await expect(panel.getByRole("region", { name: "Live candidate 1" }).getByRole("row", { name: /\[4\] 8 8 Pass/ })).toBeVisible();
  await panel.getByRole("button", { name: "Review candidate 1" }).click();
  await expect(page.locator(sourceLines)).toContainText("x+2");
  const capture = process.env.INTENTFORGE_PHASE45_CAPTURES;
  if (capture) {
    await mkdir(capture, { recursive: true });
    await panel.screenshot({ path: `${capture}/live-review.png` });
  }
  await panel.getByRole("button", { name: "Apply reviewed behavioral repair" }).click();
  await expect(page.locator(sourceLines)).toContainText("x*2");
  await expect(panel.getByText("Live interpreter evidence")).toHaveCount(0);
});

test("isolated disagreement yields editable inputs without expectations and hides in C mode", async ({ page }) => {
  test.skip(!live, "An actual isolated VM service is required");
  await page.setViewportSize({ width: 430, height: 940 });
  const panel = await openPanel(page, "int choose(int a,int b){return lost;}");
  await panel.getByLabel("Entry point").fill("choose");
  await panel.getByLabel("Test vectors (JSON)").fill('[{"arguments":[2,2],"expected":2}]');
  await panel.getByLabel("Compare repair candidates").check();
  await panel.getByRole("button", { name: "Run verification" }).click();
  await expect(panel.getByText("Multiple candidates match. More test cases may distinguish them.")).toBeVisible();
  const section = panel.getByRole("region", { name: "Candidate disagreement" });
  await expect(section.getByText(/· disagree ·/).first()).toBeVisible();
  const capture = process.env.INTENTFORGE_PHASE45_CAPTURES;
  if (capture) {
    await mkdir(capture, { recursive: true });
    await section.screenshot({ path: `${capture}/live-probes-mobile.png` });
  }
  await section.getByRole("button", { name: "Use probe input" }).first().click();
  await expect(panel.getByLabel("Test vectors (JSON)")).toHaveValue(/"expected": null/);
  await expect(panel.getByText("Live interpreter evidence")).toHaveCount(0);
  await panel.getByRole("button", { name: "Run verification" }).click();
  await expect(panel.getByRole("alert")).toContainText("explicit expected value");
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(430);
  await page.getByLabel("Language").selectOption("clang");
  await expect(page.getByText("Interactive behavioral verification", { exact: true })).toHaveCount(0);
});

test("isolated runtime diagnostics navigate and settings invalidate the snapshot", async ({ page }) => {
  test.skip(!live, "An actual isolated VM service is required");
  const panel = await openPanel(page, "int f(){\n return 4/0;\n}");
  await panel.getByLabel("Entry point").fill("f");
  await panel.getByLabel("Test vectors (JSON)").fill('[{"arguments":[],"expected":0}]');
  await panel.getByRole("button", { name: "Run verification" }).click();
  await expect(panel.getByText("DIVISION_BY_ZERO", { exact: true })).toBeVisible();
  await panel.getByRole("button", { name: /line 2, column/ }).click();
  await panel.getByLabel("Step limit").fill("100");
  await expect(panel.getByText("Live interpreter evidence")).toHaveCount(0);
});
