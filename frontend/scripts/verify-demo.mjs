// Run against a local development server or a built Vite preview.
import assert from "node:assert/strict";
import { mkdir } from "node:fs/promises";
import { chromium } from "playwright";

const port = Number(process.argv[2] || 4173);
assert(Number.isInteger(port) && port > 0 && port <= 65535);
const offline = process.argv.includes("--offline");
const browser = await chromium.launch({ executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE });
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const loaded = new Set();
  page.on("response", r => {
    if (r.ok() && r.request().resourceType() === "script") loaded.add(new URL(r.url()).pathname);
  });
  await page.goto(`http://127.0.0.1:${port}`);
  const cdp = await page.context().newCDPSession(page);
  await cdp.send("Network.enable");
  await cdp.send("Network.setCacheDisabled", { cacheDisabled: true });
  await page.reload();
  await page.locator(".source-editor .view-lines").waitFor();
  await page.getByText(offline ? "Backend offline" : "Backend connected", { exact: true }).waitFor();
  await page.getByRole("link", { name: "Explore demo examples" }).click();
  await page.getByLabel("Demo example").selectOption({ label: "Sentinel collision and manual repair" });
  await page.getByRole("button", { name: "Load demo source" }).click();
  if (!offline) {
    await page.getByRole("button", { name: "Analyze", exact: true }).click();
    await page.getByText("Analysis complete. All checks passed.", { exact: true }).waitFor();
    await page.getByRole("tab", { name: "Intention", exact: true }).click();
    await page.getByLabel("Intention engine").selectOption("13");
    await page.getByLabel("Analysis mode").selectOption("examples");
    await page.getByLabel("Function", { exact: true }).fill("demo");
    await page.getByText("Expression locations and input/output examples", {exact:true}).click();
    await page.getByRole("textbox", {name:"Input/output examples",exact:true}).fill(JSON.stringify([
      {args:[true,-1],expected_return:-1},{args:[false,5],expected_return:12},{args:[true,0],expected_return:0}
    ]));
    await page.getByRole("button",{name:"Analyze Intention",exact:true}).click();
    await page.getByRole("button",{name:/Review .*sentinel presence constraint/}).click();
    const preview = page.getByRole("region",{name:"Selected intention repair"});
    await preview.waitFor();
    if (process.env.INTENTFORGE_DEMO_CAPTURES) {
      await mkdir(process.env.INTENTFORGE_DEMO_CAPTURES, {recursive:true});
      await preview.screenshot({path:`${process.env.INTENTFORGE_DEMO_CAPTURES}/diff-${port}.png`});
    }
    await preview.getByRole("button",{name:"Apply Reviewed Intention Repair"}).click();
    await page.waitForFunction(() => document.querySelector(".source-editor .view-lines")?.textContent.includes("!present"));
  }
  // Basic Mini-C editing can finish without requesting language services. Exercise
  // the configured Monaco factory explicitly to check the worker asset on refresh.
  const started = page.waitForEvent("worker");
  await page.evaluate(() => { window.MonacoEnvironment.getWorker("", "editorWorkerService"); });
  const worker = await started;
  assert.match(await worker.evaluate(() => self.location.href), /worker/i);
  assert(loaded.size > 1);
  console.log(JSON.stringify({port,offline,loadedScripts:loaded.size,workerAsset:new URL(worker.url()).pathname}));
} finally { await browser.close(); }
