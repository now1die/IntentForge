import { readFileSync } from "node:fs";
import { mkdir } from "node:fs/promises";
import { expect, test, type Locator, type Page } from "@playwright/test";

type Vector = { arguments: number[]; expected: number | boolean };
type Fixture = { id: string; source: string; vectors: Vector[]; holdout_vectors: Vector[] };
const fixtures = ["phase115_data","phase11_data"].flatMap((directory): Fixture[] =>
  JSON.parse(readFileSync(new URL(`../../benchmarks/${directory}/cases-v1.json`,import.meta.url),"utf8")));
const editor = ".source-editor .view-lines";

function fixture(id: string) {
  const row = fixtures.find((item) => item.id === id);
  if (!row) throw new Error(`Unknown case ${id}`);
  return row;
}

async function setSource(page: Page, code: string) {
  await page.goto("/classic");
  await page.locator(editor).click();
  await page.keyboard.press("Control+A");
  await page.keyboard.insertText(code);
}

async function capture(locator: Locator, name: string) {
  const folder=process.env.INTENTFORGE_PHASE115_CAPTURES;
  if (!folder) return;
  await mkdir(folder,{recursive:true});
  await locator.screenshot({path:`${folder}/${name}.png`});
}

test("workbench routes the API on the frontend origin and shows compiler readiness", async ({page,request}) => {
  const health=await request.get("/api/health");
  expect(health.ok()).toBe(true);
  expect((await health.json()).status).toBe("ok");
  const privateRoute=await request.get("/api/internal/capability");
  expect(privateRoute.headers()["content-type"]).not.toContain("application/json");
  const seen=page.waitForRequest((req) => new URL(req.url()).pathname==="/api/health");
  await page.goto("/classic");
  expect(new URL((await seen).url()).origin).toBe(new URL(page.url()).origin);
  await expect(page.getByText("Backend connected",{exact:true})).toBeVisible();
  await capture(page.locator(".connections"),"compiler-readiness");
});

test("lazy workbench failure shows a reload action without displaying internal errors", async ({page}) => {
  await page.route("**/src/App.tsx*", (route) => route.abort());
  await page.goto("/classic");
  const fallback=page.getByRole("alert").filter({hasText:"Workbench could not load"});
  await expect(fallback.getByRole("button",{name:"Reload workbench"})).toBeVisible();
  await expect(fallback).not.toContainText("TypeError");
  await capture(fallback,"startup-error-boundary");
});

test("failed entry module leaves a static troubleshooting message", async ({page}) => {
  await page.route("**/src/main.tsx*", (route) => route.abort());
  await page.goto("/classic");
  await expect(page.getByRole("heading",{name:"Loading Compiler Workbench…"})).toBeVisible();
  await expect(page.getByText("If this message stays visible",{exact:false})).toBeVisible();
});

test("Phase 11.5 applies the range origin and seed as a single approved repair", async ({page}) => {
  const row=fixture("reaching-maximum-seed-fault");
  await setSource(page,row.source);
  await page.getByRole("tab",{name:"Intention",exact:true}).click();
  await page.getByLabel("Intention engine").selectOption("115");
  await page.getByLabel("Analysis mode").selectOption("examples");
  await page.getByLabel("Function").fill("f");
  await page.getByText("Expression locations and input/output examples",{exact:true}).click();
  await page.getByRole("textbox",{name:"Input/output examples",exact:true}).fill(JSON.stringify(
    row.vectors.map((vector) => ({args:vector.arguments,expected_return:vector.expected}))));
  await page.getByRole("button",{name:"Analyze Intention",exact:true}).click();
  const result=page.getByRole("region",{name:"Intention results"});
  await expect(result.getByRole("region",{name:"Phase 11.5 reliability evidence"})).toContainText("Shared extrema");
  await result.getByRole("button",{name:/Review .*coordinated extrema seed constraint/}).click();
  const preview=result.getByRole("region",{name:"Selected intention repair"});
  await expect(preview.locator(".diff-pair")).toHaveCount(2);
  await capture(preview,"atomic-range-seed");
  await expect(page.locator(editor)).toContainText("int checksum=2");
  await preview.getByRole("button",{name:"Apply Reviewed Intention Repair"}).click();
  await expect(page.locator(editor)).toContainText("int checksum=ceiling");
  await expect(page.locator(editor)).toContainText("int k=base");
});

test("Phase 11.5 retains both interpolation alternatives after a disagreement probe", async ({page}) => {
  test.skip(!process.env.INTENTFORGE_VM_SOCKET,"Requires the restricted Linux worker");
  const row=fixture("equal-endpoint-probe-fault");
  await setSource(page,row.source);
  await page.getByText("Interactive behavioral verification",{exact:true}).click();
  const panel=page.getByLabel("Interactive behavioral verification",{exact:true});
  await panel.getByLabel("Entry point").fill("f");
  await panel.getByLabel("Compare repair candidates").check();
  await panel.getByLabel("Phase 5 repair and probes").check();
  await panel.getByLabel("Phase 11.5 repair reliability").check();
  const values=panel.getByLabel("Test vectors (JSON)");
  await values.fill(JSON.stringify(row.vectors));
  await panel.getByRole("button",{name:"Run verification"}).click();
  await expect(panel.getByRole("region",{name:"Phase 11.5 reliability evidence"})).toContainText("2 discovery-compatible");
  await expect(panel.getByRole("button",{name:/Review candidate/})).toHaveCount(2);
  await expect(panel.getByText("Eligible for guided review",{exact:true})).toHaveCount(0);
  await capture(panel.getByRole("region",{name:"Candidate pair outcomes"}),"interpolation-pair");
  await panel.getByRole("button",{name:/Review candidate/}).first().click();
  const preview=panel.getByRole("region",{name:"Behavioral candidate review"});
  await expect(preview).toBeVisible();
  await values.fill(JSON.stringify(row.holdout_vectors));
  await expect(preview).toHaveCount(0);
});
