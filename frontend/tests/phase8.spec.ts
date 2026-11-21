import { expect, test, type Page } from "@playwright/test";
import { mkdir } from "node:fs/promises";

const predecessor = "int f(int a,int n,int d){\n  return a+n*d;\n}";
const correct = "int f(int n,int a){if(n<=0){return a;}return f(n-2,a+n);}";
const editor = ".source-editor .view-lines";
const captures = process.env.INTENTFORGE_PHASE8_CAPTURES;

async function insert(page: Page, source: string) {
  await page.goto("/");
  await page.locator(editor).click();
  await page.keyboard.press("Control+A");
  await page.keyboard.insertText(source);
}

async function setupBehavior(page: Page, source: string) {
  await insert(page, source);
  await page.getByText("Interactive behavioral verification", { exact: true }).click();
  const panel = page.getByLabel("Interactive behavioral verification", { exact: true });
  await panel.getByLabel("Entry point").fill("f");
  await panel.getByLabel("Compare repair candidates").check();
  await panel.getByLabel("Phase 5 repair and probes").check();
  await panel.getByLabel("Phase 8 specification-guided arithmetic").check();
  return panel;
}

async function capture(element: ReturnType<Page["locator"]>, name: string) {
  if (!captures) return;
  await mkdir(captures, { recursive: true });
  await element.screenshot({ path: `${captures}/${name}.png` });
}

test("Phase 8 shows typed requirements and invalidates an arithmetic hypothesis after a domain edit", async ({ page }) => {
  await insert(page, predecessor);
  await page.getByRole("tab", { name: "Intention", exact: true }).click();
  await page.getByLabel("Intention engine").selectOption("8");
  await page.getByLabel("Analysis mode").selectOption("examples");
  await page.getByLabel("Function").fill("f");
  await page.getByText("Expression locations and input/output examples", { exact: true }).click();
  await page.getByRole("textbox", { name: "Input/output examples", exact: true }).fill(
    '[{"args":[3,2,4],"expected_return":7},{"args":[2,4,5],"expected_return":17}]'
  );
  const domain = page.getByRole("textbox", { name: "Input domain (JSON)", exact: true }).first();
  await domain.fill('[null,{"minimum":1,"maximum":8},null]');
  await page.getByRole("button", { name: "Analyze Intention", exact: true }).click();
  const result = page.getByRole("region", { name: "Intention results" });
  const requirements = result.getByRole("region", { name: "Trusted requirements" });
  await expect(requirements).toContainText("n · [1, 8]");
  await expect(requirements).toContainText("2 supplied expectations");
  await result.getByRole("button", { name: /Review 1 · arithmetic predecessor/ }).click();
  await expect(result).toContainText("supplied examples · Phase 8");
  await expect(page.locator(editor)).toContainText("a+n*d");
  await capture(result, "trusted-arithmetic-constraints");
  await domain.fill('[null,{"minimum":1,"maximum":9},null]');
  await expect(result).toHaveCount(0);
});

test("Phase 8 keeps suggestions for matching originals collapsed and expandable", async ({ page }) => {
  test.skip(!process.env.INTENTFORGE_VM_SOCKET, "Requires the restricted Linux worker");
  const panel = await setupBehavior(page, correct);
  await panel.getByLabel("Test vectors (JSON)").fill('[{"arguments":[4,0],"expected":6},{"arguments":[7,0],"expected":16}]');
  await panel.getByRole("button", { name: "Run verification" }).click();
  await expect(panel.getByRole("region", { name: "Guided repair evidence" })).toContainText("Original matches supplied tests");
  const toggle = panel.getByRole("button", { name: /Show optional repairs/ });
  await expect(toggle).toHaveAttribute("aria-expanded", "false");
  await expect(panel.getByRole("button", { name: /Review candidate/ })).toHaveCount(0);
  await capture(panel, "optional-suggestions-collapsed");
  await toggle.click();
  await expect(panel.getByRole("button", { name: /Review candidate/ }).first()).toBeVisible();
  await expect(panel.getByText("Eligible for guided review", { exact: true })).toHaveCount(0);
});

test("Phase 8 verifies a predecessor repair and applies only a newly reviewed snapshot", async ({ page }) => {
  test.skip(!process.env.INTENTFORGE_VM_SOCKET, "Requires the restricted Linux worker");
  const panel = await setupBehavior(page, predecessor);
  await panel.getByLabel("Test vectors (JSON)").fill('[{"arguments":[3,2,4],"expected":7},{"arguments":[2,4,5],"expected":17}]');
  const domain = panel.getByRole("textbox", { name: "Input domain (JSON)", exact: true });
  await domain.fill('[null,{"minimum":1,"maximum":8},null]');
  const run = panel.getByRole("button", { name: "Run verification" });
  await run.click();
  await expect(panel.getByRole("alert")).toHaveText("Confirmed mismatch on supplied tests");
  const candidate = panel.locator("article").filter({ hasText: "Eligible for guided review" });
  const choice = candidate.getByRole("button", { name: /Review candidate/ });
  await choice.click();
  const review = panel.getByRole("region", { name: "Behavioral candidate review" });
  await expect(review.locator(".diff-after")).toContainText("a+(n - 1)*d");
  await capture(panel, "verified-predecessor-review");
  await domain.fill('[null,{"minimum":1,"maximum":9},null]');
  await expect(review).toHaveCount(0);
  await expect(page.locator(editor)).toContainText("a+n*d");
  await run.click();
  await choice.click();
  await review.getByRole("button", { name: "Apply reviewed behavioral repair" }).click();
  await expect(page.locator(editor)).toContainText(/a\+\(n\s*-\s*1\)\*d/);
});
