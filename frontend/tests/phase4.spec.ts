import { expect, test } from "@playwright/test";
import { mkdir } from "node:fs/promises";

test("recorded Mini-C evidence compares outputs, preserves source, and invalidates after editing", async ({ page }) => {
  const requests: string[] = [];
  page.on("request", (request) => requests.push(new URL(request.url()).pathname));
  await page.goto("/");
  await page.getByText("Behavioral verification", { exact: true }).click();
  await page.getByRole("button", { name: "Load trusted example" }).click();
  const before = page.getByRole("region", { name: "Original program" });
  const after = page.getByRole("region", { name: "Candidate 1" });
  await expect(before.getByText("Mismatches supplied tests")).toBeVisible();
  await expect(before.getByRole("row", { name: /\[4\] 8 6 Fail/ })).toBeVisible();
  await expect(after.getByRole("row", { name: /\[4\] 8 8 Pass/ })).toBeVisible();
  const editor = page.locator(".source-editor .view-lines");
  await expect(editor).toContainText("x+2");
  const captures = process.env.INTENTFORGE_PHASE4_CAPTURES;
  if (captures) {
    await mkdir(captures, { recursive: true });
    await page.screenshot({ path: `${captures}/repair-comparison.png`, fullPage: true });
  }
  await editor.click();
  await page.keyboard.insertText(" ");
  await expect(before).toHaveCount(0);
  expect(requests.filter((path) => /execute|verify-repairs/.test(path))).toEqual([]);
});

test("recorded failures and ambiguity remain readable on narrow screens and C mode hides the VM", async ({ page }) => {
  await page.setViewportSize({ width: 420, height: 900 });
  await page.goto("/");
  await page.getByText("Behavioral verification", { exact: true }).click();
  const choices = page.getByLabel("Trusted example");
  const load = page.getByRole("button", { name: "Load trusted example" });
  await choices.selectOption("divide-by-zero");
  await load.click();
  await expect(page.getByText("DIVISION_BY_ZERO", { exact: true })).toBeVisible();
  await choices.selectOption("bounded-loop");
  await load.click();
  await expect(page.getByText("STEP_LIMIT", { exact: true })).toBeVisible();
  await page.getByText("Execution trace", { exact: true }).click();
  await expect(page.getByText(/execution limit · line/)).toBeVisible();
  const captures = process.env.INTENTFORGE_PHASE4_CAPTURES;
  if (captures) {
    await mkdir(captures, { recursive: true });
    await page.screenshot({ path: `${captures}/step-limit-mobile.png`, fullPage: true });
  }
  await choices.selectOption("coincident-arguments");
  await load.click();
  await expect(page.getByText("Multiple candidates match. Intent remains ambiguous.")).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(420);
  await page.getByLabel("Language").selectOption("clang");
  await expect(page.getByText("Behavioral verification", { exact: true })).toHaveCount(0);
});
