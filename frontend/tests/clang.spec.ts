import { expect, test } from "@playwright/test";
import { mkdir } from "node:fs/promises";

test("C capability and language switching keep Mini-C routes available", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Language").selectOption("clang");
  await expect(page.getByText("Intelligent repair, linking and execution are unavailable in C mode.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Correct", exact: true })).toHaveCount(0);
  if (!process.env.INTENTFORGE_LIBCLANG) {
    await expect(page.getByText("Clang analysis is disabled on this deployment.")).toBeVisible();
    await expect(page.getByRole("button", { name: "Analyze", exact: true })).toBeDisabled();
  }
  await page.getByLabel("Language").selectOption("mini");
  await expect(page.getByRole("button", { name: "Correct", exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Analyze", exact: true })).toBeEnabled();
});

test("real Clang diagnostics, AST and declarations are tied to the editor snapshot", async ({ page }) => {
  test.skip(!process.env.INTENTFORGE_LIBCLANG, "Clang integration requires the optional Linux worker");
  await page.goto("/");
  await page.getByLabel("Language").selectOption("clang");
  await expect(page.getByText(/Clang 19\./)).toBeVisible();
  const source = "struct Point { int x; };\nint locate(struct Point *p) { return p->missing; }";
  const sourceLines = page.locator(".source-editor .view-lines");
  await sourceLines.click();
  await page.keyboard.press("Control+A");
  await page.keyboard.insertText(source);
  await expect(page.getByRole("status")).toContainText("Source changed");
  await page.getByRole("button", { name: "Analyze", exact: true }).click();
  await expect(page.getByText(/no member named 'missing'/)).toBeVisible();
  await expect(page.getByRole("button", { name: /^main.c:2:/ }).first()).toBeVisible();
  const captures = process.env.INTENTFORGE_CLANG_CAPTURES;
  if (captures) {
    await mkdir(captures, { recursive: true });
    await page.screenshot({ path: `${captures}/diagnostics.png`, fullPage: true });
  }
  await page.getByRole("button", { name: "C AST" }).click();
  await page.getByRole("button", { name: "Toggle TRANSLATION_UNIT" }).click();
  await expect(page.getByText("STRUCT_DECL", { exact: true })).toBeVisible();
  if (captures) await page.screenshot({ path: `${captures}/ast.png`, fullPage: true });
  await page.getByRole("button", { name: "C declarations" }).click();
  await expect(page.getByText(/#\d+ locate/)).toBeVisible();
  if (captures) {
    await page.setViewportSize({ width: 420, height: 900 });
    await page.screenshot({ path: `${captures}/declarations-mobile.png`, fullPage: true });
  }
  await sourceLines.click();
  await page.keyboard.insertText(" ");
  await expect(page.getByText("Analyze the editor source to see Clang evidence.")).toBeVisible();
});
