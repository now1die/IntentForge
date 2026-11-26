import { expect, test } from "@playwright/test";

test("first-time demo link opens the example picker and loads ambiguity evidence inputs", async ({ page }) => {
  await page.goto("/classic");
  await page.getByRole("link", { name: "Explore demo examples" }).click();
  await page.getByLabel("Demo example").selectOption({ label: "Ambiguous interpolation repair" });
  await page.getByRole("button", { name: "Load demo source" }).click();
  await expect(page.locator(".source-editor .view-lines")).toContainText("int f(");
  await page.getByText("Demo expectations", { exact: true }).click();
  await expect(page.locator("#demo-examples pre").first()).toContainText("expected_return");
});
