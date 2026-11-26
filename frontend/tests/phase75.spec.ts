import { expect, test, type Page } from "@playwright/test";
import { mkdir } from "node:fs/promises";

const source = "int f(int n,int total){\n  if(n<=0){return total;}\n  return f(n-1,total+n);\n}";
const editor = ".source-editor .view-lines";
const captures = process.env.INTENTFORGE_PHASE75_CAPTURES;

async function openSource(page: Page) {
  await page.goto("/classic");
  await page.locator(editor).click();
  await page.keyboard.press("Control+A");
  await page.keyboard.insertText(source);
}

test("Phase 7.5 exposes recursive progress and test-guided hypotheses", async ({ page }) => {
  await openSource(page);
  await page.getByRole("tab", { name: "Intention", exact: true }).click();
  await page.getByLabel("Intention engine").selectOption("75");
  await page.getByLabel("Analysis mode").selectOption("examples");
  await page.getByLabel("Function").fill("f");
  await page.getByText("Expression locations and input/output examples", { exact: true }).click();
  await page.getByRole("textbox", { name: "Input/output examples", exact: true }).fill(
    '[{"args":[4,0],"expected_return":6},{"args":[7,0],"expected_return":16}]'
  );
  await page.getByRole("button", { name: "Analyze Intention", exact: true }).click();
  const result = page.getByRole("region", { name: "Intention results" });
  await expect(result.getByRole("heading", { name: "Possible repairs" })).toBeVisible();
  await result.getByText("f(int n, int total) · int", { exact: true }).click();
  const progress = result.getByRole("region", { name: "Recursive progress evidence" });
  await expect(progress).toContainText("Guarded argument offset -1");
  await expect(progress).toContainText("feeds return");
  await result.getByRole("button", { name: /Review 1 · nonunit recursive progress/ }).click();
  await expect(result).toContainText("supplied examples · Phase 7.5");
  await expect(page.locator(editor)).toContainText("f(n-1,total+n)");
  if (captures) {
    await mkdir(captures, { recursive: true });
    await result.screenshot({ path: `${captures}/nonunit-evidence.png` });
  }
  await page.getByLabel("Intention engine").selectOption("7");
  await expect(result).toHaveCount(0);
});

test("Phase 7.5 verifies a nonunit candidate with current snapshot approval", async ({ page }) => {
  test.skip(!process.env.INTENTFORGE_VM_SOCKET, "Requires the restricted Linux worker");
  await openSource(page);
  await page.getByText("Interactive behavioral verification", { exact: true }).click();
  const panel = page.getByLabel("Interactive behavioral verification", { exact: true });
  await panel.getByLabel("Entry point").fill("f");
  await panel.getByLabel("Compare repair candidates").check();
  await panel.getByLabel("Phase 5 repair and probes").check();
  await panel.getByLabel("Phase 7.5 generalized repair recovery").check();
  const vectors = panel.getByLabel("Test vectors (JSON)");
  await vectors.fill('[{"arguments":[4,0],"expected":6},{"arguments":[7,0],"expected":16}]');
  const run = panel.getByRole("button", { name: "Run verification" });
  await run.click();
  await expect(panel.getByRole("alert")).toHaveText("Confirmed mismatch on supplied tests");
  const choice = panel.locator("article").filter({ hasText: "Eligible for guided review" });
  await choice.getByRole("button", { name: /Review candidate/ }).click();
  const review = panel.getByRole("region", { name: "Behavioral candidate review" });
  await expect(review.locator(".diff-after")).toContainText("f(n - 2,total+n)");
  const approve = review.getByRole("button", { name: "Apply reviewed behavioral repair" });
  await expect(approve).toBeVisible();
  await expect(page.locator(editor)).toContainText("f(n-1,total+n)");
  if (captures) {
    await mkdir(captures, { recursive: true });
    await panel.screenshot({ path: `${captures}/nonunit-confirmed-mismatch.png` });
  }
  await vectors.fill('[{"arguments":[8,2],"expected":22},{"arguments":[9,0],"expected":25}]');
  await expect(approve).toHaveCount(0);
  await run.click();
  await panel.locator("article").filter({ hasText: "Eligible for guided review" }).getByRole("button", { name: /Review candidate/ }).click();
  await approve.click();
  await expect(page.locator(editor)).toContainText("f(n - 2,total+n)");
  await expect(review).toHaveCount(0);
});
