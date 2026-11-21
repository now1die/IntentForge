import { mkdir } from "node:fs/promises";
import { expect, test, type Locator, type Page } from "@playwright/test";

const editor = ".source-editor .view-lines";
const guard = "int f(int n){return 3*n+19;}";
const window = `int f(int n,int a,int b,int c,int d){
  int digits[4]; digits[0]=a; digits[1]=b; digits[2]=c; digits[3]=d;
  int peak=0;
  for(int i=0;i<n-2;i++){
    int total=0;
    for(int j=0;j<2;j++){total+=digits[i+j];}
    if(total>peak){peak=total;}
  }
  return peak;
}`;

async function insert(page: Page, code: string) {
  await page.goto("/");
  await page.locator(editor).click();
  await page.keyboard.press("Control+A");
  await page.keyboard.insertText(code);
}

async function chooser(page: Page, points: [number[],number][]) {
  await page.getByRole("tab", { name:"Intention", exact:true }).click();
  await page.getByLabel("Intention engine").selectOption("95");
  await page.getByLabel("Analysis mode").selectOption("examples");
  await page.getByLabel("Function").fill("f");
  await page.getByText("Expression locations and input/output examples", {exact:true}).click();
  await page.getByRole("textbox",{name:"Input/output examples",exact:true}).fill(
    JSON.stringify(points.map(([args,expected_return]) => ({args,expected_return}))));
  await page.getByRole("button",{name:"Analyze Intention",exact:true}).click();
  return page.getByRole("region",{name:"Intention results"});
}

async function capture(element: Locator, name: string) {
  const folder = process.env.INTENTFORGE_PHASE95_CAPTURES;
  if (!folder) return;
  await mkdir(folder,{recursive:true});
  await element.screenshot({path:`${folder}/${name}.png`});
}

test("Phase 9.5 shows trusted guard evidence and applies only the selected snapshot", async ({page}) => {
  await insert(page,guard);
  const result = await chooser(page,[[[-2],7],[[-1],7],[[0],19],[[4],31]]);
  const evidence = result.getByRole("region",{name:"Phase 9.5 control-flow evidence"});
  await expect(evidence).toContainText("Entry guard n < 0");
  await expect(evidence).toContainText("Return 7 on supplied inputs 1, 2");
  await capture(evidence,"domain-guard-evidence");
  await result.getByRole("button",{name:/Review 1 · domain base case constraint/}).click();
  const preview = result.getByRole("region",{name:"Selected intention repair"});
  await expect(preview).toContainText("if (n < 0)");
  await expect(page.locator(editor)).not.toContainText("if (n < 0)");
  await preview.getByRole("button",{name:"Apply Reviewed Intention Repair"}).click();
  await expect(page.locator(editor)).toContainText("if (n < 0)");
  await expect(preview).toHaveCount(0);
});

test("Phase 9.5 displays checked original and proposed window endpoints", async ({page}) => {
  await insert(page,window);
  const result = await chooser(page,[[[2,2,3,7,5],5],[[3,2,1,7,0],8],[[4,5,3,6,5],11]]);
  const evidence = result.getByRole("region",{name:"Phase 9.5 control-flow evidence"});
  await expect(evidence).toContainText("Fixed-cell facts · digits");
  await expect(evidence).toContainText("Multiple control-flow edits");
  await expect(evidence).toContainText("Input 1 · 0 iterations");
  const candidate = evidence.getByText("Line 4 · <=", {exact:true});
  await candidate.click();
  await expect(evidence).toContainText("Input 1 · 1 iterations · first 0 · last 0");
  await capture(evidence,"window-boundary-evidence");
  await page.getByLabel("Intention engine").selectOption("9");
  await expect(result).toHaveCount(0);
});

test("Phase 9.5 isolated review clears when trusted vectors change", async ({page}) => {
  test.skip(!process.env.INTENTFORGE_VM_SOCKET,"Requires the restricted Linux worker");
  await insert(page,guard);
  await page.getByText("Interactive behavioral verification",{exact:true}).click();
  const panel = page.getByLabel("Interactive behavioral verification",{exact:true});
  await panel.getByLabel("Entry point").fill("f");
  await panel.getByLabel("Compare repair candidates").check();
  await panel.getByLabel("Phase 5 repair and probes").check();
  await panel.getByLabel("Phase 9.5 control-flow repair").check();
  const vectors = panel.getByLabel("Test vectors (JSON)");
  await vectors.fill('[{"arguments":[-2],"expected":7},{"arguments":[-1],"expected":7},{"arguments":[0],"expected":19},{"arguments":[4],"expected":31}]');
  await panel.getByRole("button",{name:"Run verification"}).click();
  await expect(panel.getByText("Eligible for guided review",{exact:true})).toBeVisible();
  await panel.getByRole("button",{name:/Review candidate/}).first().click();
  const preview=panel.getByRole("region",{name:"Behavioral candidate review"});
  await expect(preview.locator(".diff-after")).toContainText("if (n < 0)");
  await capture(preview,"isolated-guard-review");
  await vectors.fill('[{"arguments":[-2],"expected":7}]');
  await expect(preview).toHaveCount(0);
  await expect(page.locator(editor)).toContainText(guard);
});
