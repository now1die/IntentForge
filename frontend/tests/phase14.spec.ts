import { expect, test, type Page } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import { join } from "node:path";

async function capture(page: Page, name: string) {
  const directory = process.env.INTENTFORGE_PRODUCT_CAPTURES;
  if (!directory) return;
  await mkdir(directory, { recursive: true });
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({path:join(directory,`${name}.png`), fullPage:true, animations:"disabled"});
}

async function navigate(page: Page, label: string) {
  await page.getByRole("navigation", {name:"Workspace sidebar"}).getByRole("link",{name:label,exact:true}).click();
}

async function open(page: Page) {
  await page.goto("/");
  await expect(page.getByText("Backend connected",{exact:true})).toBeVisible({timeout:15000});
  await expect(page.locator(".source-editor .monaco-editor")).toBeVisible();
}

async function replaceSource(page: Page, source: string) {
  await page.getByRole("textbox",{name:"Mini-C source editor",exact:true}).focus();
  await page.keyboard.press("Control+A");
  await page.keyboard.insertText(source);
}

async function example(page: Page, label: string) {
  await navigate(page,"Examples & Learning");
  await page.getByRole("button",{name:`Try Example: ${label}`,exact:true}).click();
}

test("compiler evidence, four routes, and preserved Monaco source", async ({page}) => {
  await open(page);
  const primary = page.getByRole("navigation",{name:"Primary navigation"});
  const sidebar = page.getByRole("navigation",{name:"Workspace sidebar"});
  for (const route of ["Compiler","Intention","Research Lab","Examples & Learning","Compiler"]) {
    await navigate(page,route);
    await expect(primary.getByRole("link",{name:route,exact:true})).toHaveAttribute("aria-current","page");
    await expect(sidebar.getByRole("link",{name:route,exact:true})).toHaveAttribute("aria-current","page");
  }
  await replaceSource(page,"int square(int x) {\n    return x * x;\n}");
  await navigate(page,"Intention");
  await expect(page.locator(".source-editor .view-lines")).toContainText("square");
  await navigate(page,"Compiler");
  await page.getByRole("button",{name:"Analyze Code",exact:true}).click();
  await expect(page.getByRole("heading",{name:"Compilation Successful"})).toBeVisible();
  await expect(page.getByRole("group",{name:"Control-flow graph"})).toBeVisible();
  await capture(page,"compiler-success");
  await page.getByRole("tab",{name:"Tokens",exact:true}).click();
  await expect(page.getByRole("cell",{name:"IDENTIFIER",exact:true}).first()).toBeVisible();
  await page.getByRole("tab",{name:"AST",exact:true}).click();
  await expect(page.locator("summary").filter({hasText:"Program"})).toBeVisible();
  await capture(page,"compiler-ast");
  await page.getByRole("tab",{name:"Symbols",exact:true}).click();
  await expect(page.getByRole("cell",{name:"square",exact:true})).toBeVisible();
  await capture(page,"compiler-symbols");
});

test("real compiler diagnostics and fixes require approval", async ({page}) => {
  await open(page);
  await replaceSource(page,"int main() { int x = 10; if (x > 5 { return x; } return 0; }");
  await page.getByRole("button",{name:"Analyze Code",exact:true}).click();
  const issues = page.getByRole("complementary",{name:"Compilation result"});
  await expect(issues.getByRole("heading",{name:/compilation issue/i})).toBeVisible();
  await issues.getByRole("button",{name:"Find compiler fixes"}).click();
  await expect(page.getByRole("button",{name:"Apply Corrected Code"})).toBeEnabled();
  await capture(page,"compiler-correction");
  await page.getByRole("button",{name:"Apply Corrected Code"}).click();
  await expect(page.getByRole("heading",{name:"Compilation Successful"})).toBeVisible();
});

test("typed table, real suggestion and source-bound approval", async ({page}) => {
  await page.route("**/api/v1/behavioral-verification/capability",route => route.abort());
  await open(page);
  await example(page,"Addition or subtraction?");
  await expect(page.getByRole("heading",{name:"Test Cases (3)"})).toBeVisible();
  await expect(page.getByRole("columnheader",{name:"a",exact:true})).toBeVisible();
  await capture(page,"intention-test-cases");
  await page.getByRole("textbox",{name:"Case 1 expected output"}).fill("oops");
  await page.getByRole("button",{name:"Analyze Intention",exact:true}).click();
  await expect(page.getByRole("region",{name:"Intent and repair result"}).getByRole("alert")).toContainText("signed 32-bit integer");
  await page.getByRole("textbox",{name:"Case 1 expected output"}).fill("8");
  const request = page.waitForRequest(req => req.url().endsWith("/v1/intention-analysis") && req.postDataJSON().mode === "examples");
  await page.getByRole("button",{name:"Analyze Intention",exact:true}).click();
  expect((await request).postDataJSON()).toMatchObject({engine_version:13,requirement:{function:"add",
    examples:[{args:[5,3],expected_return:8},{args:[10,2],expected_return:12},{args:[4,7],expected_return:11}]}});
  await expect(page.getByRole("heading",{name:"Suggested Fixes"})).toBeVisible();
  await expect(page.getByText("Unverified",{exact:true})).toBeVisible();
  await expect(page.getByText("Restricted worker unavailable.",{exact:false})).toBeVisible();
  await capture(page,"intention-suggestion");
  await page.getByRole("button",{name:"Review Repair",exact:true}).click();
  await expect(page.getByRole("dialog",{name:"Review source change"})).toBeVisible();
  await page.getByRole("button",{name:"Cancel",exact:true}).click();
  await replaceSource(page,"int add(int a, int b) { return 0; }");
  await expect(page.getByText("Source changed since analysis.",{exact:false})).toBeVisible();
  await expect(page.getByRole("button",{name:"Apply Reviewed Repair"})).toHaveCount(0);
  await navigate(page,"Examples & Learning");
  await page.getByRole("button",{name:"Try Example: Addition or subtraction?",exact:true}).click();
  await expect(page.getByRole("dialog",{name:"Replace edited source"})).toBeVisible();
  await page.getByRole("button",{name:"Load Example",exact:true}).click();
  await page.getByRole("button",{name:"Analyze Intention",exact:true}).click();
  await page.getByRole("button",{name:"Review Repair",exact:true}).click();
  await page.getByRole("button",{name:"Apply Reviewed Repair",exact:true}).click();
  await expect(page.locator(".source-editor .view-lines")).toContainText("a + b");
});

test("worker verifies the documented UI flow", async ({page}) => {
  test.skip(!process.env.INTENTFORGE_VM_SOCKET,"Requires the restricted worker");
  await open(page);
  await example(page,"Addition or subtraction?");
  await expect(page.getByText("Restricted worker ready",{exact:true})).toBeVisible();
  await page.getByRole("button",{name:"Analyze Intention",exact:true}).click();
  await expect(page.getByText("Confirmed behavioral mismatch on supplied tests.")).toBeVisible();
  await expect(page.getByText("Verified on supplied tests",{exact:true})).toBeVisible();
  await page.getByText("Verification Results",{exact:true}).click();
  await expect(page.getByRole("region",{name:"Suggested repair"}).getByRole("cell",{name:"Pass",exact:true})).toHaveCount(3);
  await capture(page,"intention-verified");
});

test("ambiguity can be inspected without being applied", async ({page}) => {
  await open(page);
  await example(page,"Ambiguous interpolation repair");
  await page.getByRole("button",{name:"Analyze Intention",exact:true}).click();
  await expect(page.getByRole("heading",{name:"Multiple compatible repairs"})).toBeVisible();
  await capture(page,"intention-ambiguous");
  await page.getByRole("button",{name:"Review Repair",exact:true}).click();
  await expect(page.getByRole("button",{name:"Apply Reviewed Repair",exact:true})).toBeDisabled();
});

test("research graph keeps real loop edges, selected block and view state", async ({page}) => {
  await open(page);
  await example(page,"An exclusive loop bound");
  await navigate(page,"Research Lab");
  await page.getByRole("button",{name:"Run Research Analysis",exact:true}).click();
  const graph = page.getByRole("group",{name:"Control-flow graph"});
  await expect(graph).toBeVisible();
  const header = graph.locator('[data-kind="loop_header"]');
  const headerId = await header.getAttribute("data-block");
  await expect(graph.locator(`[data-edge="back"][data-to="${headerId}"]`)).toHaveCount(1);
  await expect(graph.locator(`[data-edge="true"][data-from="${headerId}"]`)).toHaveCount(1);
  await expect(graph.locator(`[data-edge="false"][data-from="${headerId}"]`)).toHaveCount(1);
  await header.focus();
  await page.keyboard.press("Enter");
  await expect(header).toHaveAttribute("aria-pressed","true");
  await expect(page.getByRole("heading",{name:`Block B${headerId}`})).toBeVisible();
  await capture(page,"research-cfg");
  await page.getByRole("button",{name:"Zoom in",exact:true}).click();
  await expect(graph).toHaveAttribute("data-zoom","1.25");
  const box = await graph.boundingBox();
  if (!box) throw new Error("Graph canvas is missing");
  await page.mouse.move(box.x + box.width - 12,box.y + box.height - 12);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width - 45,box.y + box.height - 40,{steps:6});
  await page.mouse.up();
  await page.getByRole("button",{name:"Fit graph",exact:true}).click();
  await expect(graph).toHaveAttribute("data-zoom","1");
  await page.getByRole("button",{name:"Program State",exact:true}).click();
  await expect(page.getByRole("heading",{name:"Program State",exact:true})).toBeVisible();
  await expect(page.getByRole("heading",{name:"Benchmark Results",exact:true})).toBeVisible();
  await capture(page,"research-state-benchmarks");
});

test("examples search, responsive navigation, and reduced motion", async ({page}) => {
  await open(page);
  await navigate(page,"Examples & Learning");
  await capture(page,"examples");
  const search = page.getByRole("searchbox",{name:"Search examples"});
  await search.fill("sentinel");
  await expect(search).toHaveValue("sentinel");
  await expect(page.getByRole("heading",{name:"A correct program",exact:true})).toHaveCount(0);
  await page.getByLabel("Difficulty",{exact:true}).selectOption("Beginner");
  await expect(page.getByText("No examples match these filters.")).toBeVisible();
  await page.getByLabel("Difficulty",{exact:true}).selectOption("Intermediate");
  await expect(page.getByRole("heading",{name:"Sentinel collision",exact:true})).toBeVisible();
  await page.setViewportSize({width:390,height:844});
  await page.emulateMedia({reducedMotion:"reduce"});
  await navigate(page,"Compiler");
  await expect(page.locator(".product-intro")).toHaveCSS("animation-name","none");
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
  const tab = page.getByRole("tab",{name:"Overview"});
  await tab.focus();
  await page.keyboard.press("ArrowRight");
  await expect(page.getByRole("tab",{name:"Tokens",exact:true})).toBeFocused();
  await capture(page,"responsive");
});

test("backend offline preserves editing and navigation", async ({page}) => {
  await page.route("**/api/**",route => route.abort());
  await page.goto("/");
  await expect(page.getByText("Backend offline",{exact:true})).toBeVisible();
  await expect(page.locator(".source-editor .monaco-editor")).toBeVisible();
  await capture(page,"backend-offline");
  await navigate(page,"Examples & Learning");
  await expect(page.getByRole("searchbox")).toBeVisible();
});
