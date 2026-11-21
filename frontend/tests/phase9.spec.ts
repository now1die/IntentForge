import { mkdir } from "node:fs/promises";
import { expect, test, type Locator, type Page } from "@playwright/test";

const editor = ".source-editor .view-lines";

async function source(page: Page, code: string) {
  await page.goto("/");
  await page.locator(editor).click();
  await page.keyboard.press("Control+A");
  await page.keyboard.insertText(code);
}

async function capture(element: Locator, title: string) {
  const target = process.env.INTENTFORGE_PHASE9_CAPTURES;
  if (!target) return;
  await mkdir(target, { recursive: true });
  await element.screenshot({ path: `${target}/${title}.png` });
}

async function staticCase(page: Page, examples: [number[], number][]) {
  await page.getByRole("tab", { name: "Intention", exact: true }).click();
  await page.getByLabel("Intention engine").selectOption("9");
  await page.getByLabel("Analysis mode").selectOption("examples");
  await page.getByLabel("Function").fill("f");
  await page.getByText("Expression locations and input/output examples", { exact: true }).click();
  await page.getByRole("textbox", { name: "Input/output examples", exact: true }).fill(
    JSON.stringify(examples.map(([args, expected_return]) => ({ args, expected_return })))
  );
  await page.getByRole("button", { name: "Analyze Intention", exact: true }).click();
  return page.getByRole("region", { name: "Intention results" });
}

test("Phase 9 displays a variable stride and checked loop exit values", async ({ page }) => {
  await source(page, `int f(int a,int n,int stride){
    int tally=0;
    for(int i=a;n>=i;i+=stride){tally++;}
    return tally;
  }`);
  const result = await staticCase(page, [[[0,4,2],2],[[2,9,3],3],[[3,3,2],0],[[8,5,0],0]]);
  const evidence = result.getByRole("region", { name: "Phase 9 evidence" });
  await expect(evidence).toContainText("ascending induction");
  await expect(evidence).toContainText("3 iterations · step 3 · exit values [3]");
  await expect(evidence).toContainText("0 iterations · latch skipped");
  await capture(evidence, "variable-stride-loop");
  await page.getByLabel("Intention engine").selectOption("85");
  await expect(result).toHaveCount(0);
});

test("Phase 9 approves both cross-branch sites together", async ({ page }) => {
  await source(page, `int f(int x){
    if(x<0){return 4*x+1;}
    return 8*x-2;
  }`);
  const result = await staticCase(page, [[[-4],-11],[[-3],-8],[[2],12],[[3],19]]);
  await expect(result.getByRole("region", { name: "Phase 9 evidence" })).toContainText("true on 2 supplied inputs");
  await result.getByRole("button", { name: /Review 1 · cross branch coefficients/ }).click();
  const preview = result.getByRole("region", { name: "Selected intention repair" });
  await expect(preview.getByRole("region", { name: "Coordinated edit locations" })).toContainText("2 coordinated edits");
  await expect(page.locator(editor)).toContainText("return 4*x+1");
  await expect(page.locator(editor)).toContainText("return 8*x-2");
  await capture(preview, "cross-branch-approval");
  await preview.getByRole("button", { name: "Apply Reviewed Intention Repair" }).click();
  await expect(page.locator(editor)).toContainText("return 3*x+1");
  await expect(page.locator(editor)).toContainText("return 7*x-2");
});

test("Phase 9 distinguishes verified runtime failure from a matching candidate and drops stale review", async ({ page }) => {
  test.skip(!process.env.INTENTFORGE_VM_SOCKET, "Requires the restricted Linux worker");
  await source(page, "int f(int a,int b){return 15/(a-b);}");
  await page.getByText("Interactive behavioral verification", { exact: true }).click();
  const panel = page.getByLabel("Interactive behavioral verification", { exact: true });
  await panel.getByLabel("Entry point").fill("f");
  await panel.getByLabel("Compare repair candidates").check();
  await panel.getByLabel("Phase 5 repair and probes").check();
  await panel.getByLabel("Phase 9 semantic robustness").check();
  await panel.getByLabel("Test vectors (JSON)").fill('[{"arguments":[5,5],"expected":1},{"arguments":[4,2],"expected":2},{"arguments":[2,3],"expected":3}]');
  await panel.getByRole("button", { name: "Run verification" }).click();
  const observed = panel.getByRole("region", { name: "Observed runtime failure" });
  await expect(observed).toContainText("Triggering input [5,5]");
  await expect(observed).toContainText("Source snapshot");
  await expect(panel.getByText("Completed and matched all supplied tests.", { exact: true })).toBeVisible();
  await expect(panel.getByText("Eligible for guided review", { exact: true })).toHaveCount(0);
  await capture(observed, "verified-runtime-failure");
  await panel.getByRole("button", { name: /Review candidate/ }).first().click();
  const preview = panel.getByRole("region", { name: "Behavioral candidate review" });
  await expect(preview.locator(".diff-after")).toContainText("15/(a+b)");
  await panel.getByLabel("Step limit").fill("9999");
  await expect(observed).toHaveCount(0);
  await expect(preview).toHaveCount(0);
  await expect(page.locator(editor)).toContainText("15/(a-b)");
});
