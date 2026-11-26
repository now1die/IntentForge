import { readFileSync } from "node:fs";
import { mkdir } from "node:fs/promises";
import { expect, test, type Locator, type Page } from "@playwright/test";

type Vector = { arguments: number[]; expected: number | boolean };
type Fixture = { id: string; source: string; vectors: Vector[]; holdout_vectors: Vector[] };
const fixtures: Fixture[] = JSON.parse(readFileSync(new URL("../../benchmarks/phase11_data/cases-v1.json",import.meta.url),"utf8"));
const editor = ".source-editor .view-lines";

function fixture(id: string) {
  const row = fixtures.find((item) => item.id === id);
  if (!row) throw new Error(`Unknown benchmark case ${id}`);
  return row;
}

async function setSource(page: Page, code: string) {
  await page.goto("/classic");
  await page.locator(editor).click();
  await page.keyboard.press("Control+A");
  await page.keyboard.insertText(code);
}

async function analyze(page: Page, id: string) {
  const row = fixture(id);
  await setSource(page,row.source);
  await page.getByRole("tab",{name:"Intention",exact:true}).click();
  await page.getByLabel("Intention engine").selectOption("11");
  await page.getByLabel("Analysis mode").selectOption("examples");
  await page.getByLabel("Function").fill("f");
  await page.getByText("Expression locations and input/output examples",{exact:true}).click();
  await page.getByRole("textbox",{name:"Input/output examples",exact:true}).fill(JSON.stringify(
    row.vectors.map((vector) => ({args:vector.arguments,expected_return:vector.expected}))));
  await page.getByRole("button",{name:"Analyze Intention",exact:true}).click();
  return page.getByRole("region",{name:"Intention results"});
}

async function capture(locator: Locator, filename: string) {
  const folder = process.env.INTENTFORGE_PHASE11_CAPTURES;
  if (!folder) return;
  await mkdir(folder,{recursive:true});
  await locator.screenshot({path:`${folder}/${filename}.png`});
}

test("Phase 11 displays equal endpoints and applies the coordinated probe only on approval", async ({page}) => {
  const result=await analyze(page,"equal-endpoint-probe-fault");
  const evidence=result.getByRole("region",{name:"Phase 11 relational evidence"});
  await expect(evidence).toContainText("Interpolation denominator");
  await expect(evidence).toContainText("denominator 0");
  await capture(evidence,"interpolation-denominator");
  await result.getByRole("button",{name:/Review .*interpolation relational constraint/}).first().click();
  const choice=result.getByRole("region",{name:"Selected intention repair"});
  await expect(choice.locator(".diff-pair")).toHaveCount(2);
  await expect(page.locator(editor)).not.toContainText("shelf[right] == shelf[left]");
  await capture(choice,"atomic-interpolation-diff");
  await choice.getByRole("button",{name:"Apply Reviewed Intention Repair"}).click();
  await expect(page.locator(editor)).toContainText("shelf[right] == shelf[left]");
  await expect(choice).toHaveCount(0);
});

test("Phase 11 exposes duplicate cyclic relations and removes stale evidence", async ({page}) => {
  const result=await analyze(page,"duplicate-cyclic-pivot-fault");
  const evidence=result.getByRole("region",{name:"Phase 11 relational evidence"});
  await evidence.getByText("Cyclic ordering",{exact:false}).click();
  await expect(evidence).toContainText("cyclic descents");
  await expect(evidence).toContainText("duplicate cells");
  await capture(evidence,"cyclic-ordering");
  await page.getByLabel("Intention engine").selectOption("105");
  await expect(evidence).toHaveCount(0);
});

test("Phase 11 keeps runtime failure separate and drops review when vectors change", async ({page}) => {
  test.skip(!process.env.INTENTFORGE_VM_SOCKET,"Requires the restricted Linux worker");
  const row=fixture("equal-endpoint-probe-fault");
  await setSource(page,row.source);
  await page.getByText("Interactive behavioral verification",{exact:true}).click();
  const panel=page.getByLabel("Interactive behavioral verification",{exact:true});
  await panel.getByLabel("Entry point").fill("f");
  await panel.getByLabel("Compare repair candidates").check();
  await panel.getByLabel("Phase 5 repair and probes").check();
  await panel.getByLabel("Phase 11 relational repair").check();
  const vectors=panel.getByLabel("Test vectors (JSON)");
  await vectors.fill(JSON.stringify(row.vectors));
  await panel.getByRole("button",{name:"Run verification"}).click();
  const issue=panel.getByRole("region",{name:"Observed runtime failure"});
  await expect(issue).toContainText("Triggering input");
  await expect(panel.getByText("Eligible for guided review",{exact:true})).toHaveCount(0);
  await capture(issue,"isolated-interpolation-failure");
  await panel.getByRole("button",{name:/Review candidate/}).first().click();
  const preview=panel.getByRole("region",{name:"Behavioral candidate review"});
  await expect(preview.locator(".diff-after")).toContainText("shelf[right] == shelf[left]");
  await vectors.fill(JSON.stringify(row.holdout_vectors));
  await expect(preview).toHaveCount(0);
});
