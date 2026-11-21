import { mkdir } from "node:fs/promises";
import { expect, test, type Locator, type Page } from "@playwright/test";

const editor = ".source-editor .view-lines";
const joined = `int f(int n) {
  int out=n+7;
  if(n<=4) { int n=9; out=3*n; }
  return out;
}`;
const pairs = `int f(int x, int y) {
  int left=4*x;
  int right=8*y;
  return left+right;
}`;
const count = `int f(int n) {
  int visits=0;
  for(int i=0;i<=n;i++){if(i%3==0){visits++;}}
  return visits;
}`;

async function insert(page: Page, source: string) {
  await page.goto("/");
  await page.locator(editor).click();
  await page.keyboard.press("Control+A");
  await page.keyboard.insertText(source);
}

async function analyze(page: Page, samples: [number[], number][]) {
  await page.getByRole("tab", { name: "Intention", exact: true }).click();
  await page.getByLabel("Intention engine").selectOption("85");
  await page.getByLabel("Analysis mode").selectOption("examples");
  await page.getByLabel("Function").fill("f");
  await page.getByText("Expression locations and input/output examples", { exact: true }).click();
  await page.getByRole("textbox", { name: "Input/output examples", exact: true }).fill(
    JSON.stringify(samples.map(([args, expected_return]) => ({ args, expected_return })))
  );
  await page.getByRole("button", { name: "Analyze Intention", exact: true }).click();
  return page.getByRole("region", { name: "Intention results" });
}

async function capture(element: Locator, caption: string) {
  const directory = process.env.INTENTFORGE_PHASE85_CAPTURES;
  if (!directory) return;
  await mkdir(directory, { recursive: true });
  await element.screenshot({ path: `${directory}/${caption}.png` });
}

test("Phase 8.5 shows guarded definitions and invalidates evidence on profile changes", async ({ page }) => {
  await insert(page, joined);
  const result = await analyze(page, [[[2],27],[[3],27],[[4],11],[[5],12]]);
  const evidence = result.getByRole("region", { name: "Phase 8.5 constraints" });
  await expect(result.getByRole("region", { name: "Trusted requirements" })).toContainText("4 supplied expectations");
  await expect(evidence).toContainText("true on 3 supplied inputs");
  await expect(evidence).toContainText("out (line 2)");
  await expect(evidence).toContainText("out (line 3)");
  await capture(evidence, "joined-branch-evidence");
  await page.getByLabel("Intention engine").selectOption("8");
  await expect(result).toHaveCount(0);
});

test("Phase 8.5 records loop bounds and counts per supplied input", async ({ page }) => {
  await insert(page, count);
  const result = await analyze(page, [[[0],0],[[3],1],[[4],2],[[6],2]]);
  const evidence = result.getByRole("region", { name: "Phase 8.5 constraints" });
  await expect(evidence).toContainText("At most 64 points per input");
  await expect(evidence).toContainText("Supplied input 2 · 4 iterations · 2 accumulator updates");
  await capture(evidence, "bounded-loop-evidence");
});

test("Phase 8.5 applies a two-site static preview in one action", async ({ page }) => {
  await insert(page, pairs);
  const result = await analyze(page, [[[1,0],3],[[0,1],7],[[2,3],27],[[4,-1],5]]);
  await result.getByRole("button", { name: /Review 1 · coordinated coefficients/ }).click();
  const preview = result.getByRole("region", { name: "Selected intention repair" });
  const locations = preview.getByRole("region", { name: "Coordinated edit locations" });
  await expect(locations).toContainText("Line 2, column");
  await expect(locations).toContainText("Line 3, column");
  await expect(page.locator(editor)).toContainText("left=4*x");
  await expect(page.locator(editor)).toContainText("right=8*y");
  await capture(preview, "two-site-static-preview");
  await preview.getByRole("button", { name: "Apply Reviewed Intention Repair" }).click();
  await expect(page.locator(editor)).toContainText("left=3*x");
  await expect(page.locator(editor)).toContainText("right=7*y");
});

test("Phase 8.5 binds isolated verification and review to current vectors, limits and domain", async ({ page }) => {
  test.skip(!process.env.INTENTFORGE_VM_SOCKET, "Requires the restricted Linux worker");
  await insert(page, pairs);
  await page.getByText("Interactive behavioral verification", { exact: true }).click();
  const panel = page.getByLabel("Interactive behavioral verification", { exact: true });
  await panel.getByLabel("Entry point").fill("f");
  await panel.getByLabel("Compare repair candidates").check();
  await panel.getByLabel("Phase 5 repair and probes").check();
  await panel.getByLabel("Phase 8.5 branch-aware repair").check();
  await panel.getByLabel("Test vectors (JSON)").fill(
    '[{"arguments":[1,0],"expected":3},{"arguments":[0,1],"expected":7},{"arguments":[2,3],"expected":27}]'
  );
  const run = panel.getByRole("button", { name: "Run verification" });
  const choice = panel.locator("article").filter({ hasText: "Eligible for guided review" }).getByRole("button", { name: /Review candidate/ });
  const review = panel.getByRole("region", { name: "Behavioral candidate review" });
  const domain = panel.getByLabel("Input domain (JSON)");
  await domain.fill('[{"minimum":0,"maximum":9},null]');
  await run.click();
  await expect(panel.getByRole("alert")).toHaveText("Confirmed mismatch on supplied tests");
  await choice.click();
  await expect(review.getByRole("region", { name: "Coordinated edit locations" })).toContainText("2 coordinated edits");
  await expect(review.locator(".diff-after")).toContainText("right=7*y");
  await capture(review, "verified-coordinated-approval");
  await domain.fill('[{"minimum":0,"maximum":8},null]');
  await expect(review).toHaveCount(0);
  await run.click();
  await choice.click();
  await panel.getByLabel("Step limit").fill("9999");
  await expect(review).toHaveCount(0);
  await expect(page.locator(editor)).toContainText("left=4*x");
  await run.click();
  await choice.click();
  await panel.getByLabel("Test vectors (JSON)").fill(
    '[{"arguments":[1,0],"expected":3},{"arguments":[0,1],"expected":7},{"arguments":[2,3],"expected":27},{"arguments":[3,-1],"expected":2}]'
  );
  await expect(review).toHaveCount(0);
  await run.click();
  await choice.click();
  await review.getByRole("button", { name: "Apply reviewed behavioral repair" }).click();
  await expect(page.locator(editor)).toContainText("left=3*x");
  await expect(page.locator(editor)).toContainText("right=7*y");
});
