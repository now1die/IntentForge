import { mkdir } from "node:fs/promises";
import { expect, test, type Locator, type Page } from "@playwright/test";

const editor = ".source-editor .view-lines";
const recursive = `int lookup(int key,int p,int q,int a,int b,int c) {
  int cells[3]; cells[0]=a;cells[1]=b;cells[2]=c;
  if(p>q){return -1;} int middle=p+(q-p)/2; int current=cells[middle];
  if(current==key){return middle;}
  if(key<current){return lookup(key,p,middle-1,a,b,c);}
  return lookup(key,middle+1,q,a,b,c);
}
int f(int key,int a,int b,int c){return lookup(key,0,3,a,b,c);}`;
const expansion = `int f(int key,int a,int b,int c,int d,int e){
  int values[5];values[0]=a;values[1]=b;values[2]=c;values[3]=d;values[4]=e;
  if(a==key){return 0;}if(e==key){return 4;}
  int extent=1;while(extent<5 && values[extent]<key){extent*=2;}
  int lo=extent/2;int hi=extent;if(hi>5){hi=5;}hi--;
  while(lo<=hi){int mid=(lo+hi)/2;if(values[mid]==key){return mid;}
    if(values[mid]<key){lo=mid+1;}else{hi=mid-1;}}
  return -lo-1;
}`;
const bounds: [number[],number][] = [[[12,2,5,8],-1],[[8,2,5,8],2],[[2,2,5,8],0],[[4,2,5,8],-1],[[5,2,5,8],1]];
const expanding: [number[],number][] = [
  [[3,1,3,7,10,18],1],[[7,1,3,7,10,18],2],[[4,1,3,7,10,18],-1],
  [[10,1,3,7,10,18],3],[[18,1,3,7,10,18],4],[[-2,-9,-2,3,15,17],1],
];

async function insert(page: Page, code: string) {
  await page.goto("/");
  await page.locator(editor).click();
  await page.keyboard.press("Control+A");
  await page.keyboard.insertText(code);
}

async function analyze(page: Page, points: [number[],number][]) {
  await page.getByRole("tab",{name:"Intention",exact:true}).click();
  await page.getByLabel("Intention engine").selectOption("10");
  await page.getByLabel("Analysis mode").selectOption("examples");
  await page.getByLabel("Function").fill("f");
  await page.getByText("Expression locations and input/output examples",{exact:true}).click();
  await page.getByRole("textbox",{name:"Input/output examples",exact:true}).fill(
    JSON.stringify(points.map(([args,expected_return])=>({args,expected_return}))));
  await page.getByRole("button",{name:"Analyze Intention",exact:true}).click();
  return page.getByRole("region",{name:"Intention results"});
}

async function capture(element: Locator, name: string) {
  const folder = process.env.INTENTFORGE_PHASE10_CAPTURES;
  if (!folder) return;
  await mkdir(folder,{recursive:true});
  await element.screenshot({path:`${folder}/${name}.png`});
}

test("Phase 10 displays failed index observations and clears stale source evidence", async ({page}) => {
  await insert(page,recursive);
  const result = await analyze(page,bounds);
  const evidence = result.getByRole("region",{name:"Phase 10 search evidence"});
  await expect(evidence).toContainText("3 int cells");
  await expect(evidence).toContainText("Recursive interval [p, q]");
  await expect(evidence).toContainText("Outside declared extent");
  await capture(evidence,"checked-recursive-interval");
  await page.getByLabel("Intention engine").selectOption("95");
  await expect(evidence).toHaveCount(0);
});

test("Phase 10 previews the expanding repair as one atomic approval", async ({page}) => {
  await insert(page,expansion);
  const result = await analyze(page,expanding);
  const evidence = result.getByRole("region",{name:"Phase 10 search evidence"});
  await expect(evidence).toContainText("Increasing window bound");
  await result.getByRole("button",{name:/Review .*expanding handoff constraint/}).click();
  const preview = result.getByRole("region",{name:"Selected intention repair"});
  await expect(preview.locator(".diff-after")).toHaveCount(2);
  await expect(preview).toContainText("extent+1");
  await expect(preview).toContainText("-1");
  await expect(page.locator(editor)).toContainText("return -lo-1");
  await capture(preview,"atomic-expanding-handoff");
  await preview.getByRole("button",{name:"Apply Reviewed Intention Repair"}).click();
  await expect(page.locator(editor)).toContainText("hi=extent+1");
  await expect(page.locator(editor)).toContainText("return -1");
  await expect(preview).toHaveCount(0);
});

test("Phase 10 isolates the original runtime failure and invalidates its preview when tests change", async ({page}) => {
  test.skip(!process.env.INTENTFORGE_VM_SOCKET,"Requires the restricted Linux worker");
  await insert(page,recursive);
  await page.getByText("Interactive behavioral verification",{exact:true}).click();
  const panel=page.getByLabel("Interactive behavioral verification",{exact:true});
  await panel.getByLabel("Entry point").fill("f");
  await panel.getByLabel("Compare repair candidates").check();
  await panel.getByLabel("Phase 5 repair and probes").check();
  await panel.getByLabel("Phase 10 search repair").check();
  const inputs=panel.getByLabel("Test vectors (JSON)");
  await inputs.fill(JSON.stringify(bounds.map(([arguments_,expected])=>({arguments:arguments_,expected}))));
  await panel.getByRole("button",{name:"Run verification"}).click();
  const issue=panel.getByRole("region",{name:"Observed runtime failure"});
  await expect(issue).toContainText("Triggering input");
  await expect(panel.getByText("Eligible for guided review",{exact:true})).toHaveCount(0);
  await capture(issue,"isolated-runtime-failure");
  await panel.getByRole("button",{name:/Review candidate/}).first().click();
  const preview=panel.getByRole("region",{name:"Behavioral candidate review"});
  await expect(preview.locator(".diff-after")).toContainText("lookup(key,0,2");
  await inputs.fill('[{"arguments":[2,2,5,8],"expected":0}]');
  await expect(preview).toHaveCount(0);
  await expect(page.locator(editor)).toContainText("lookup(key,0,3");
});

test("Phase 10 shows a sampled traversal origin derived from local cells", async ({page}) => {
  const shifted = `int f(int a,int b,int c){
    int cell[3];cell[0]=a;cell[1]=b;cell[2]=c;
    int low=a;for(int v=1;v<3;v++){if(cell[v]<low){low=cell[v];}}
    int out=5;for(int i=low;i<low+3;i++){out+=2*cell[i-0]+i;}return out;
  }`;
  await insert(page,shifted);
  const result = await analyze(page,[[[0,4,5],26],[[5,-2,8],24],[[4,2,3],32],[[7,9,11],83]]);
  const evidence=result.getByRole("region",{name:"Phase 10 search evidence"});
  await evidence.getByText("Array traversal origins",{exact:true}).click();
  await expect(evidence).toContainText("start at low");
  await expect(evidence).toContainText("Input 2 · first -2");
});
