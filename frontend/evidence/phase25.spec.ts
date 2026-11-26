import { execFileSync } from "node:child_process";
import { mkdir, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { expect, test } from "@playwright/test";

const output = resolve(process.env.INTENTFORGE_EVIDENCE_DIR ?? "../audit/phase2_5");

const scenarios = [
  { file: "01-code-only-review.png", mode: "code_only", source: "int cost(int price,int quantity){int bill=price*quantity;return price;}",
    input: "", heading: "Unverified intention hypothesis", preview: true },
  { file: "02-language-review.png", mode: "natural_language", source: "int choose(int left,int right){if(left<right){return left;}return right;}",
    input: "Return the maximum of left and right", heading: "Possible mismatch with the supplied requirement", preview: true },
  { file: "03-unsupported-requirement.png", mode: "natural_language", source: "bool ready(int count){return count==2;}",
    input: "Make this fit our process", heading: "No supported mismatch found", preview: false },
  { file: "04-explicit-mobile.png", mode: "explicit", source: "int increment(int input){return input-3;}",
    input: "input+3", heading: "Possible mismatch with the supplied requirement", preview: true },
] as const;

test("capture changed intention analysis features", async ({ page, browser }) => {
  await mkdir(output, { recursive: true });
  const captures = [];
  for (const scenario of scenarios) {
    const viewport = scenario.mode === "explicit" ? { width: 390, height: 844 } : { width: 1440, height: 1000 };
    await page.setViewportSize(viewport);
    await page.goto("/classic");
    await expect(page.getByText("Backend connected", { exact: true })).toBeVisible();
    await page.locator(".source-editor .view-lines").click();
    await page.keyboard.press("Control+A");
    await page.keyboard.insertText(scenario.source);
    await page.getByRole("tab", { name: "Intention", exact: true }).click();
    await page.getByLabel("Analysis mode").selectOption(scenario.mode);
    if (scenario.mode !== "code_only") {
      await page.getByLabel(scenario.mode === "explicit" ? "Return expression" : "Requirement description").fill(scenario.input);
    }
    await page.getByRole("button", { name: "Analyze Intention", exact: true }).click();
    await expect(page.getByRole("heading", { name: scenario.heading })).toBeVisible();
    if (scenario.preview) {
      await page.getByRole("button", { name: /Review 1/ }).click();
      await page.getByRole("region", { name: "Selected intention repair" }).scrollIntoViewIfNeeded();
    } else {
      await expect(page.getByText("Unsupported requirement wording.", { exact: false })).toBeVisible();
    }
    await page.evaluate(() => document.fonts.ready);
    await page.screenshot({ path: resolve(output, scenario.file), animations: "disabled" });
    captures.push({ ...scenario, viewport });
  }
  await writeFile(resolve(output, "capture-metadata.json"), JSON.stringify({
    revision: execFileSync("git", ["rev-parse", "HEAD"], { encoding: "utf8" }).trim(),
    browser: browser.version(), backend: "Local FastAPI with repository model artifacts",
    mocks: false, captures,
  }, null, 2) + "\n");
});
