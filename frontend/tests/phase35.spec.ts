import { expect, test } from "@playwright/test";
import { mkdir } from "node:fs/promises";

test("shared evidence follows the compiler and invalidates when the editor changes", async ({ page }) => {
  await page.goto("/classic");
  const evidence = page.getByRole("region", { name: "Shared compiler evidence" });
  await evidence.getByRole("button", { name: "Inspect compiler evidence" }).click();
  await expect(evidence.getByRole("heading", { name: "Mini-C evidence" })).toBeVisible();
  await expect(evidence.getByText(/main.mc · AST available/)).toBeVisible();
  await page.getByLabel("Language").selectOption("clang");
  await expect(evidence.getByRole("heading")).toHaveCount(0);
  await evidence.getByRole("button", { name: "Inspect compiler evidence" }).click();
  await expect(evidence.getByRole("heading", { name: "Clang evidence" })).toBeVisible();
  if (process.env.INTENTFORGE_LIBCLANG) {
    await expect(evidence.getByText(/main.c · AST available/)).toBeVisible();
    const captures = process.env.INTENTFORGE_PHASE35_CAPTURES;
    if (captures) {
      await mkdir(captures, { recursive: true });
      await page.screenshot({ path: `${captures}/shared-clang-evidence.png`, fullPage: true });
    }
  } else {
    await expect(evidence.getByText("Clang analysis is disabled on this deployment.")).toBeVisible();
  }
  await page.locator(".source-editor .view-lines").click();
  await page.keyboard.insertText(" ");
  await expect(evidence.getByRole("heading")).toHaveCount(0);
});

test("Phase 3.5 shows contextual evidence and keeps boundary repair in review", async ({ page }) => {
  await page.goto("/classic");
  const editor = page.locator(".source-editor .view-lines");
  await editor.click();
  await page.keyboard.press("Control+A");
  await page.keyboard.insertText("int a[6]; int f(){for(int i=5;i>=-1;i--){a[i]=i;}return a[0];}");
  await page.getByRole("tab", { name: "Intention", exact: true }).click();
  await page.getByLabel("Intention engine").selectOption("4");
  await page.getByLabel("Analysis mode").selectOption("code_only");
  await page.getByRole("button", { name: "Analyze Intention", exact: true }).click();
  await page.getByRole("button", { name: /Review 1/ }).click();
  const preview = page.getByRole("region", { name: "Selected intention repair" });
  await expect(preview.getByText("Strong contextual hypothesis")).toBeVisible();
  await expect(preview.locator(".diff-after")).toHaveText("+>");
  await expect(editor).toContainText("i>=-1");
  const captures = process.env.INTENTFORGE_PHASE35_CAPTURES;
  if (captures) {
    await mkdir(captures, { recursive: true });
    await page.screenshot({ path: `${captures}/contextual-review.png`, fullPage: true });
  }
});
