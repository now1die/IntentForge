import { expect, test } from "@playwright/test";

test("v3 offers an array boundary repair for review without editing the source", async ({ page }) => {
  await page.goto("/classic");
  const editor = page.locator(".source-editor .view-lines");
  await editor.click();
  await page.keyboard.press("Control+A");
  await page.keyboard.insertText("int a[4]; int f(){int n=0;for(int i=0;i<=4;i++){n=a[i];}return n;}");
  await page.getByRole("tab", { name: "Intention", exact: true }).click();
  await page.getByLabel("Intention engine").selectOption("3");
  await page.getByLabel("Analysis mode").selectOption("code_only");
  await page.getByRole("button", { name: "Analyze Intention", exact: true }).click();
  await page.getByRole("button", { name: /Review 1/ }).click();
  const preview = page.getByRole("region", { name: "Selected intention repair" });
  await expect(preview.locator("code.diff-after")).toHaveText("+<");
  await expect(editor).toContainText("i<=4");
  await page.getByLabel("Intention engine").selectOption("2");
  await expect(page.getByRole("button", { name: "Apply Reviewed Intention Repair" })).toHaveCount(0);
});
