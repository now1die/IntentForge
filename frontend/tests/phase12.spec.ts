import { mkdir } from "node:fs/promises";
import { expect, test, type Locator, type Page } from "@playwright/test";

const editor = ".source-editor .view-lines";
const expectations = [
  { args: [true, -1], expected_return: -1 },
  { args: [false, 5], expected_return: 12 },
  { args: [true, 0], expected_return: 0 },
];

async function loadDemo(page: Page, label: string) {
  await page.goto("/");
  await page.getByText("Phase 12 demo examples", { exact: true }).click();
  await page.getByLabel("Demo example").selectOption({ label });
  await page.getByRole("button", { name: "Load demo source" }).click();
}

async function capture(locator: Locator, file: string) {
  const root = process.env.INTENTFORGE_PHASE12_CAPTURES;
  if (!root) return;
  await mkdir(root, { recursive: true });
  await locator.screenshot({ path: `${root}/${file}.png` });
}

async function intention(page: Page) {
  await page.getByRole("tab", { name: "Intention", exact: true }).click();
  await page.getByLabel("Intention engine").selectOption("12");
  await page.getByLabel("Analysis mode").selectOption("examples");
  await page.getByLabel("Function").fill("demo");
  await page.getByText("Expression locations and input/output examples", { exact: true }).click();
  await page.getByRole("textbox", { name: "Input/output examples", exact: true }).fill(JSON.stringify(expectations));
  await page.getByRole("button", { name: "Analyze Intention", exact: true }).click();
  return page.getByRole("region", { name: "Intention results" });
}

test("semantic evidence and a manual source-bound sentinel repair", async ({ page }) => {
  await loadDemo(page, "Sentinel collision and manual repair");
  const result = await intention(page);
  const evidence = result.getByRole("region", { name: "Phase 12 semantic state evidence" });
  await expect(evidence).toContainText("Sentinel -1");
  await expect(evidence).toContainText("flag guarded");
  await capture(evidence, "sentinel-evidence");
  const review = result.getByRole("button", { name: /Review .*sentinel presence constraint/ });
  await review.click();
  const preview = result.getByRole("region", { name: "Selected intention repair" });
  await expect(preview.locator(".diff-pair")).toHaveCount(1);
  await expect(page.locator(editor)).toContainText("if (value == -1)");
  await capture(preview, "manual-diff");
  await preview.getByRole("button", { name: "Apply Reviewed Intention Repair" }).click();
  await expect(page.locator(editor)).toContainText("if (!present)");
});

test("source edit invalidates an open Phase 12 repair", async ({ page }) => {
  await loadDemo(page, "Sentinel collision and manual repair");
  const result = await intention(page);
  await result.getByRole("button", { name: /Review .*sentinel presence constraint/ }).click();
  const preview = result.getByRole("region", { name: "Selected intention repair" });
  await expect(preview).toBeVisible();
  await page.locator(editor).click();
  await page.keyboard.press("Control+End");
  await page.keyboard.insertText("\n");
  await expect(preview).toHaveCount(0);
  await expect(page.locator(editor)).toContainText("if (value == -1)");
});

test("private verification confirms the mismatch and invalidates a reviewed diff when inputs change", async ({ page }) => {
  test.skip(!process.env.INTENTFORGE_VM_SOCKET, "Requires the restricted Linux worker");
  await loadDemo(page, "Sentinel collision and manual repair");
  await page.getByText("Interactive behavioral verification", { exact: true }).click();
  const panel = page.getByLabel("Interactive behavioral verification", { exact: true });
  await panel.getByLabel("Entry point").fill("demo");
  await panel.getByLabel("Compare repair candidates").check();
  await panel.getByLabel("Phase 5 repair and probes").check();
  await panel.getByLabel("Phase 12 semantic state").check();
  const vectors = panel.getByLabel("Test vectors (JSON)");
  await vectors.fill(JSON.stringify(expectations.map((row) => ({ arguments: row.args, expected: row.expected_return }))));
  await panel.getByRole("button", { name: "Run verification" }).click();
  await expect(panel.getByText("Mismatches supplied tests", { exact: true })).toBeVisible();
  await expect(panel.getByRole("region", { name: "Phase 12 semantic state evidence" })).toBeVisible();
  await capture(panel.getByRole("region", { name: "Guided repair evidence" }), "confirmed-mismatch");
  await panel.getByRole("button", { name: /Review candidate/ }).first().click();
  const preview = panel.getByRole("region", { name: "Behavioral candidate review" });
  await expect(preview).toBeVisible();
  await vectors.fill("[]");
  await expect(preview).toHaveCount(0);
});

test("authored demos load for compiler analysis and code-only abstention", async ({ page }) => {
  await loadDemo(page, "Correct program");
  await page.getByRole("button", { name: "Analyze", exact: true }).click();
  await expect(page.getByText("Analysis complete.", { exact: false }).first()).toBeVisible();
  await page.getByLabel("Demo example").selectOption({ label: "Compiler diagnostic" });
  await page.getByRole("button", { name: "Load demo source" }).click();
  await page.getByRole("button", { name: "Analyze", exact: true }).click();
  await expect(page.locator(".diagnostic-row").first()).toBeVisible();
  await page.getByLabel("Demo example").selectOption({ label: "Abstention without a contract" });
  await page.getByRole("button", { name: "Load demo source" }).click();
  await page.getByRole("tab", { name: "Intention", exact: true }).click();
  await page.getByLabel("Intention engine").selectOption("12");
  await page.getByRole("button", { name: "Analyze Intention", exact: true }).click();
  const result = page.getByRole("region", { name: "Intention results" });
  await expect(result.getByRole("region", { name: "Phase 12 semantic state evidence" })).toContainText("Physical extent");
  await expect(result.getByRole("button", { name: /Review candidate/ })).toHaveCount(0);
});
