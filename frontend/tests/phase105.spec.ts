import { readFileSync } from "node:fs";
import { mkdir } from "node:fs/promises";
import { expect, test, type Locator, type Page } from "@playwright/test";

type Vector = { arguments: number[]; expected: number | boolean };
type Fixture = { id: string; source: string; vectors: Vector[]; holdout_vectors: Vector[] };
const corpora = ["phase105_data","phase10_data"].flatMap((directory): Fixture[] =>
  JSON.parse(readFileSync(new URL(`../../benchmarks/${directory}/cases-v1.json`,import.meta.url),"utf8")));

const editor = ".source-editor .view-lines";

function fixture(id: string) {
  const row = corpora.find((item) => item.id === id);
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
  await page.getByLabel("Intention engine").selectOption("105");
  await page.getByLabel("Analysis mode").selectOption("examples");
  await page.getByLabel("Function").fill("f");
  await page.getByText("Expression locations and input/output examples",{exact:true}).click();
  await page.getByRole("textbox",{name:"Input/output examples",exact:true}).fill(JSON.stringify(
    row.vectors.map((vector) => ({args:vector.arguments,expected_return:vector.expected}))));
  await page.getByRole("button",{name:"Analyze Intention",exact:true}).click();
  return page.getByRole("region",{name:"Intention results"});
}

async function capture(locator: Locator, filename: string) {
  const folder = process.env.INTENTFORGE_PHASE105_CAPTURES;
  if (!folder) return;
  await mkdir(folder,{recursive:true});
  await locator.screenshot({path:`${folder}/${filename}.png`});
}

test("Phase 10.5 explains the duplicate endpoint and approves its two source edits together", async ({page}) => {
  const result = await analyze(page,"duplicate-lower-bound-fault");
  const evidence = result.getByRole("region",{name:"Phase 10.5 endpoint evidence"});
  await expect(evidence).toContainText("saturated lower");
  await expect(evidence).toContainText("duplicate-key samples");
  await capture(evidence,"duplicate-endpoint");
  await result.getByRole("button",{name:/Review .*endpoint search constraint/}).click();
  const edit = result.getByRole("region",{name:"Selected intention repair"});
  await expect(edit.locator(".diff-pair")).toHaveCount(2);
  await expect(page.locator(editor)).toContainText("return m;");
  await capture(edit,"atomic-endpoint-diff");
  await edit.getByRole("button",{name:"Apply Reviewed Intention Repair"}).click();
  await expect(page.locator(editor)).not.toContainText("return m;");
  await expect(page.locator(editor)).toContainText("key<=cell[m]");
  await expect(edit).toHaveCount(0);
});

test("Phase 10.5 exposes checked rotation relations and clears evidence on profile change", async ({page}) => {
  const result=await analyze(page,"coordinated-three-cell-pivot-fault");
  const evidence=result.getByRole("region",{name:"Phase 10.5 endpoint evidence"});
  await evidence.getByText("Rotated interval",{exact:false}).click();
  await expect(evidence).toContainText("distinct cells in cyclic increasing order");
  await expect(evidence).toContainText("5 supporting samples");
  await capture(evidence,"checked-rotation");
  await page.getByLabel("Intention engine").selectOption("10");
  await expect(evidence).toHaveCount(0);
  await expect(page.locator(editor)).toContainText("left=middle;");
});

test("Phase 10.5 keeps original division failure separate and clears stale runtime review", async ({page}) => {
  test.skip(!process.env.INTENTFORGE_VM_SOCKET,"Requires the restricted Linux worker");
  const row=fixture("division-reserve-sentinel-fault");
  await setSource(page,row.source);
  await page.getByText("Interactive behavioral verification",{exact:true}).click();
  const panel=page.getByLabel("Interactive behavioral verification",{exact:true});
  await panel.getByLabel("Entry point").fill("f");
  await panel.getByLabel("Compare repair candidates").check();
  await panel.getByLabel("Phase 5 repair and probes").check();
  await panel.getByLabel("Phase 10.5 endpoint repair").check();
  const vectors=panel.getByLabel("Test vectors (JSON)");
  await vectors.fill(JSON.stringify(row.vectors));
  await panel.getByRole("button",{name:"Run verification"}).click();
  const failure=panel.getByRole("region",{name:"Observed runtime failure"});
  await expect(failure).toContainText("Triggering input");
  await expect(panel.getByText("Eligible for guided review",{exact:true})).toHaveCount(0);
  await capture(failure,"isolated-zero-divisor");
  await panel.getByRole("button",{name:/Review candidate/}).first().click();
  const preview=panel.getByRole("region",{name:"Behavioral candidate review"});
  await expect(preview.locator(".diff-after")).toContainText("if (unit == 0)");
  await vectors.fill(JSON.stringify(row.holdout_vectors));
  await expect(preview).toHaveCount(0);
  await expect(page.locator(editor)).toContainText(row.source);
});
