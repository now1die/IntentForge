import { test, expect, type Page } from "@playwright/test";
import { examples } from "../src/constants/examples";

async function enterExample(page: Page, name: keyof typeof examples) {
  await page.locator(".source-editor .view-lines").click();
  await page.keyboard.press("Control+A");
  await page.keyboard.insertText(examples[name]);
  await expect(page.getByRole("status")).toContainText("Source changed");
}

test("lowercase a remains normal Monaco input and never runs Analyze", async ({
  page,
}) => {
  let analyzeRequests = 0;
  page.on("request", (request) => {
    if (new URL(request.url()).pathname === "/analyze") analyzeRequests += 1;
  });

  await page.goto("/");
  await page.screenshot({
    path: "../audit/ui-ux-polish/desktop-initial.png",
    fullPage: true,
  });
  await page.locator(".source-editor .view-lines").click();
  await page.keyboard.press("Control+A");
  await page.keyboard.press("a");

  await expect(page.locator(".source-editor .view-lines")).toHaveText("a");
  await expect(page.getByRole("status")).toContainText("Source changed");
  expect(analyzeRequests).toBe(0);
});

test("real backend analysis, Monaco markers, and all data inspectors", async ({
  page,
}) => {
  await page.goto("/");
  await expect(
    page.getByText("Backend connected", { exact: true }),
  ).toBeVisible();
  await expect(page.locator(".source-editor .monaco-editor")).toBeVisible();
  await page.getByRole("button", { name: "Analyze", exact: true }).click();
  await expect(page.getByRole("status")).toContainText("All checks passed");
  await page.getByRole("tab", { name: "Tokens" }).click();
  await expect(
    page.getByRole("cell", { name: "INTEGER_LITERAL", exact: true }).first(),
  ).toBeVisible();
  await page.getByRole("tab", { name: "AST", exact: true }).click();
  await expect(
    page.locator("summary").filter({ hasText: "Program" }),
  ).toBeVisible();
  await page.getByRole("tab", { name: "Symbol Table" }).click();
  await expect(
    page.getByRole("cell", { name: "main", exact: true }),
  ).toBeVisible();
  await enterExample(page, "Broken If");
  // Invalid source has no squiggles before a backend response.
  await expect(page.locator(".source-editor .squiggly-error")).toHaveCount(0);
  await page.getByRole("button", { name: "Analyze", exact: true }).click();
  await expect(page.getByRole("status")).toContainText("Diagnostics available");
  await expect(
    page.locator(".source-editor .squiggly-error").first(),
  ).toBeVisible();
  // Monaco paints marker decorations beneath its text layer, so a real pointer
  // event must bypass Playwright's interception guard at the same coordinates.
  await page
    .locator(".source-editor .squiggly-error")
    .first()
    .hover({ force: true });
  await expect(page.locator(".monaco-hover:not(.hidden)")).toContainText(
    "Mini-C backend",
  );
  await expect(page.locator(".diagnostic-row").first()).toContainText(
    "UNEXPECTED_TOKEN",
  );
  await page.locator(".diagnostic-row").first().click();
  await page.screenshot({
    path: "../audit/ui-ux-polish/diagnostics.png",
    fullPage: true,
  });
});

test("real ML correction is reviewed before explicitly applying", async ({
  page,
}) => {
  await page.goto("/");
  await enterExample(page, "Broken If");
  await page.getByRole("button", { name: "Correct", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Apply Corrected Code" }),
  ).toBeEnabled();
  await expect(page.getByRole("status")).toContainText(
    "Source has not changed",
  );
  await expect(page.locator(".history")).toContainText('Insert ")"');
  await expect(page.locator(".history")).toContainText("Validated");
  await expect(
    page.getByText(
      /Compiler validation is authorit[a]tive\. ML and AI only rank or select supported rep[a]irs\./,
    ),
  ).toHaveCount(0);
  await expect(
    page.locator(".source-editor .squiggly-error").first(),
  ).toBeVisible();
  await page.screenshot({
    path: "../audit/ui-ux-polish/deterministic-correction.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Apply Corrected Code" }).click();
  await expect(page.getByRole("status")).toContainText("All checks passed");
  await expect(page.locator(".source-editor .squiggly-error")).toHaveCount(0);
});

test("Groq ambiguity-selection metadata is visible in correction review", async ({
  page,
}) => {
  const original = examples.Valid;
  const corrected = `${original}\n`;
  const location = { line: 1, column: 1, offset: 0 };
  const span = { start: location, end: location };
  const candidate = {
    id: "SYN-0001-C02",
    action: "DELETE",
    token_type: "LBRACE",
    token_lexeme: "{",
    offset: 0,
    span,
    text: "",
    reason: "Delete the trailing opener",
    grammar_context: "expression",
    diagnostic_id: "SYN-0001",
    origin: "traditional_recovery",
    parser_validated: true,
    score: 0.01,
    edits: [],
  };
  const validation = {
    candidate,
    corrected_source: corrected,
    valid: true,
    relevant_valid: true,
    target_resolved: true,
    remaining_syntax_errors: 0,
    remaining_lexical_errors: 0,
  };
  await page.route("**/correct", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        success: true,
        original_code: original,
        corrected_code: corrected,
        fully_syntactically_valid: true,
        corrections_applied: 1,
        history: [
          {
            sequence: 1,
            status: "APPLIED",
            applied: true,
            diagnostic_id: "SYN-0001",
            original_error: {
              phase: "syntax",
              code: "UNEXPECTED_EOF",
              message: "Unexpected end of input",
              line: 1,
              column: 1,
              offset: 0,
              span,
            },
            prediction: {
              label: "REPLACE_BRACKET",
              confidence: 0.99,
              probabilities: { REPLACE_BRACKET: 0.99 },
            },
            selected_candidate: candidate,
            candidate_rank: 2,
            candidate_probability: 0.01,
            before_snippet: original,
            after_snippet: corrected,
            source_offset: 0,
            validation,
            reason: "ambiguity_selection_groq_parser_validated",
            llm_fallback: null,
            ambiguity_selection: {
              attempted: true,
              available: true,
              model: "mock-groq",
              selected_candidate_id: candidate.id,
              confidence: 0.91,
              reason: "Deleting the trailing opener preserves the function structure.",
              selected_candidate: candidate,
              validation,
              accepted: true,
              error: null,
            },
          },
        ],
        predictions: [],
        confidence_values: [],
        groq_fallback_used: false,
        ambiguity_selection_used: true,
        needs_llm_fallback: false,
        unresolved_syntax_diagnostics: [],
        semantic_diagnostics: [],
        stop_reason: "source_is_syntactically_valid",
      }),
    }),
  );

  await page.goto("/");
  await page.getByRole("button", { name: "Correct", exact: true }).click();

  await expect(page.locator(".analysis-panel")).toContainText(
    "AI intent selection",
  );
  await expect(page.locator(".analysis-panel")).toContainText("Selected");
  await expect(page.locator(".analysis-panel")).toContainText("91.0%");
  await expect(page.locator(".analysis-panel")).toContainText(
    "Deleting the trailing opener preserves the function structure.",
  );
  await page.screenshot({
    path: "../audit/ui-ux-polish/ambiguity-selection.png",
    fullPage: true,
  });
});

test("selected compound correction is visible and can be applied", async ({ page }) => {
  const original = `int main() {
int x = 10;
if ((x > 5] {
    return x;
}

return 0;
}`;
  const corrected = original.replace("if ((x > 5] {", "if ((x > 5)) {");
  const bracketOffset = original.indexOf("]");
  const insertOffset = original.indexOf(" {", original.indexOf("if"));
  const start = { line: 3, column: 5, offset: original.indexOf("((") };
  const end = { line: 3, column: 12, offset: bracketOffset + 1 };
  const edits = [
    {
      action: "REPLACE",
      token_type: "RPAREN",
      token_lexeme: "]",
      offset: bracketOffset,
      span: {
        start: { line: 3, column: 11, offset: bracketOffset },
        end: { line: 3, column: 12, offset: bracketOffset + 1 },
      },
      text: ")",
    },
    {
      action: "INSERT",
      token_type: "RPAREN",
      token_lexeme: ")",
      offset: insertOffset,
      span: {
        start: { line: 3, column: 13, offset: insertOffset },
        end: { line: 3, column: 13, offset: insertOffset },
      },
      text: ")",
    },
  ];
  const candidate = {
    id: "SYN-0001-M01",
    action: "COMPOUND",
    token_type: "COMPOUND",
    token_lexeme: null,
    offset: start.offset,
    span: { start, end },
    text: "",
    reason: "Replace the mismatched closer and close the remaining local opener",
    grammar_context: "if_condition",
    diagnostic_id: "SYN-0001",
    origin: "compound_recovery",
    parser_validated: true,
    score: 0.99,
    edits,
  };
  const diagnostic = {
    phase: "syntax",
    code: "UNEXPECTED_TOKEN",
    message: "Unexpected token RBRACKET; expected RPAREN",
    line: 3,
    column: 11,
    offset: bracketOffset,
    span: edits[0].span,
    unexpected_token: "RBRACKET",
    unexpected_lexeme: "]",
    expected_tokens: ["RPAREN"],
    grammar_context: "if_condition",
  };
  const validation = {
    candidate,
    corrected_source: corrected,
    valid: true,
    relevant_valid: true,
    target_resolved: true,
    remaining_syntax_errors: 0,
    remaining_lexical_errors: 0,
  };
  await page.route("**/correct", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        success: true,
        original_code: original,
        corrected_code: corrected,
        fully_syntactically_valid: true,
        corrections_applied: 1,
        history: [{
          sequence: 1,
          status: "APPLIED",
          applied: true,
          diagnostic_id: "SYN-0001",
          original_error: diagnostic,
          prediction: { label: "INSERT_RPAREN", confidence: 0.99, probabilities: { INSERT_RPAREN: 0.99 } },
          selected_candidate: candidate,
          candidate_rank: 1,
          candidate_probability: 0.99,
          before_snippet: original,
          after_snippet: corrected,
          source_offset: start.offset,
          validation,
          attempts: [],
          reason: "high_confidence_and_parser_validated",
          llm_fallback: null,
          ambiguity_selection: null,
        }],
        predictions: [],
        confidence_values: [],
        groq_fallback_used: false,
        ambiguity_selection_used: false,
        needs_llm_fallback: false,
        unresolved_syntax_diagnostics: [],
        semantic_diagnostics: [],
        stop_reason: "source_is_syntactically_valid",
      }),
    }),
  );

  await page.goto("/");
  await page.locator(".source-editor .view-lines").click();
  await page.keyboard.press("Control+A");
  await page.keyboard.insertText(original);
  await page.getByRole("button", { name: "Correct", exact: true }).click();

  await expect(page.locator(".review-header")).toContainText("1 validated correction ready");
  await expect(page.locator(".history")).toContainText("Compound correction");
  await expect(page.locator(".history")).toContainText('Replace "]" with ")"');
  await expect(page.locator(".analysis-panel")).toContainText("2 coordinated edits");
  await expect(page.locator(".inline-diff")).toContainText("if ((x > 5] {");
  await expect(page.locator(".inline-diff")).toContainText("if ((x > 5)) {");
  await expect(page.getByRole("button", { name: "Apply Corrected Code" })).toBeEnabled();
  await page.screenshot({
    path: "../audit/ui-ux-polish/compound-correction.png",
    fullPage: true,
  });
});

test("invented missing expression remains unresolved and cannot be applied", async ({ page }) => {
  const source = "int main(){ int x = ; return 0; }";
  const offset = source.indexOf(";");
  const location = { line: 1, column: offset + 1, offset };
  const diagnostic = {
    phase: "syntax",
    code: "UNEXPECTED_TOKEN",
    message: "Unexpected semicolon; expected an expression",
    line: 1,
    column: offset + 1,
    offset,
    span: { start: location, end: { ...location, column: location.column + 1, offset: offset + 1 } },
    unexpected_token: "SEMICOLON",
    unexpected_lexeme: ";",
    expected_tokens: ["IDENTIFIER", "INTEGER_LITERAL"],
    grammar_context: "declaration",
  };
  await page.route("**/correct", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        success: false,
        original_code: source,
        corrected_code: source,
        fully_syntactically_valid: false,
        corrections_applied: 0,
        history: [{
          sequence: 1,
          status: "UNRESOLVED",
          applied: false,
          diagnostic_id: "SYN-0001",
          original_error: diagnostic,
          prediction: { label: "INSERT_RPAREN", confidence: 0.4, probabilities: { INSERT_RPAREN: 0.4 } },
          selected_candidate: null,
          candidate_rank: null,
          candidate_probability: null,
          before_snippet: source,
          after_snippet: null,
          source_offset: offset,
          validation: null,
          attempts: [],
          reason: "no_safe_candidate",
          llm_fallback: {
            attempted: true,
            available: true,
            model: "mock-groq",
            accepted: false,
            error: "Unsafe LLM suggestion: semantic_content_invention_is_forbidden",
            suggestion: { action: "INSERT", replacement_text: "0", target_start: offset, target_end: offset, reason: "Invent zero" },
            validation: null,
          },
          ambiguity_selection: null,
        }],
        predictions: [],
        confidence_values: [],
        groq_fallback_used: true,
        ambiguity_selection_used: false,
        needs_llm_fallback: true,
        unresolved_syntax_diagnostics: [diagnostic],
        semantic_diagnostics: [],
        stop_reason: "no_safe_candidate",
      }),
    }),
  );

  await page.goto("/");
  await page.locator(".source-editor .view-lines").click();
  await page.keyboard.press("Control+A");
  await page.keyboard.insertText(source);
  await page.getByRole("button", { name: "Correct", exact: true }).click();

  await expect(page.locator(".review-header")).toContainText("No validated correction is ready");
  await expect(page.locator(".review-header")).toContainText(
    "AI suggestion was rejected because compiler evidence did not support it",
  );
  await expect(page.locator(".analysis-panel")).toContainText(
    "Suggestion rejected by safety policy",
  );
  await expect(page.locator(".analysis-panel")).not.toContainText("Invent zero");
  await expect(page.locator(".history")).toContainText("Unresolved");
  await expect(page.getByRole("button", { name: "Apply Corrected Code" })).toBeDisabled();
  await page.screenshot({
    path: "../audit/ui-ux-polish/unsafe-unresolved.png",
    fullPage: true,
  });
});

test("offline and missing-model errors are safe and recoverable", async ({
  page,
}) => {
  await page.route("**/health", (route) => route.abort());
  await page.goto("/");
  await expect(
    page.getByText("Backend offline", { exact: true }),
  ).toBeVisible();
  await page.route("**/correct", (route) =>
    route.fulfill({
      status: 503,
      contentType: "application/json",
      body: '{"detail":"private detail"}',
    }),
  );
  await page.getByRole("button", { name: "Correct", exact: true }).click();
  await expect(page.locator(".error-banner")).toContainText(
    "correction model is unavailable",
  );
  await expect(page.locator(".error-banner")).not.toContainText(
    "private detail",
  );
});

test("reset cancels stale analysis and clears markers", async ({ page }) => {
  await page.route("**/analyze", async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 1200));
    await route.continue().catch(() => {});
  });
  await page.goto("/");
  await enterExample(page, "Broken If");
  await page.getByRole("button", { name: "Analyze", exact: true }).click();
  await page.getByRole("button", { name: "Reset", exact: true }).click();
  await page.waitForTimeout(1500);
  await expect(page.getByRole("status")).toContainText(
    "Default example restored",
  );
  await expect(page.locator(".source-editor .squiggly-error")).toHaveCount(0);
});

test("narrow workspace stacks without horizontal page overflow", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(page.locator(".source-editor .monaco-editor")).toBeVisible();
  await expect(page.getByText("Backend connected", { exact: true })).toBeVisible();
  await expect(page.locator(".connections")).not.toContainText("ML");
  await expect(page.locator(".connections")).not.toContainText("Groq");
  await expect(page.getByRole("tab", { name: "Corrections" })).toBeVisible();
  await expect(page.getByRole("tab", { name: /Diagnostics/ })).toBeVisible();
  const editor = await page.locator(".editor-panel").boundingBox();
  const panel = await page.locator(".analysis-panel").boundingBox();
  expect(panel!.y).toBeGreaterThan(editor!.y);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "../audit/ui-ux-polish/mobile.png",
    fullPage: true,
  });
});

test("semantic-only analysis keeps compiler correction unavailable", async ({
  page,
}) => {
  await page.goto("/");
  await page.locator(".source-editor .view-lines").click();
  await page.keyboard.press("Control+A");
  await page.keyboard.insertText(
    "int main(){ int x = 1; return missing; }",
  );
  await page.getByRole("button", { name: "Analyze", exact: true }).click();

  const correct = page.getByRole("button", { name: "Correct", exact: true });
  await expect(page.getByRole("status")).toContainText("Diagnostics available");
  await expect(page.locator(".analysis-panel")).toContainText("semantic");
  await expect(correct).toBeDisabled();
  await expect(correct).toHaveAttribute(
    "title",
    "Semantic errors require manual code changes",
  );
  await page.screenshot({
    path: "../audit/ui-ux-polish/semantic-error.png",
    fullPage: true,
  });
});

test("tablet stacks while desktop preserves the split workbench", async ({
  page,
}) => {
  await page.setViewportSize({ width: 900, height: 1000 });
  await page.goto("/");
  let editor = await page.locator(".editor-panel").boundingBox();
  let panel = await page.locator(".analysis-panel").boundingBox();
  expect(panel!.y).toBeGreaterThan(editor!.y);
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(
    900,
  );
  await page.screenshot({
    path: "../audit/ui-ux-polish/tablet.png",
    fullPage: true,
  });

  await page.setViewportSize({ width: 1440, height: 900 });
  editor = await page.locator(".editor-panel").boundingBox();
  panel = await page.locator(".analysis-panel").boundingBox();
  expect(Math.abs(panel!.y - editor!.y)).toBeLessThan(2);
  expect(panel!.x).toBeGreaterThan(editor!.x);
  await page.screenshot({
    path: "../audit/ui-ux-polish/desktop-1440x900.png",
    fullPage: true,
  });
});

test("multiple deterministic fixes form a numbered correction history", async ({
  page,
}) => {
  await page.goto("/");
  await page.locator(".source-editor .view-lines").click();
  await page.keyboard.press("Control+A");
  await page.keyboard.insertText("int main(){ int x = 1 return x }");
  await page.getByRole("button", { name: "Correct", exact: true }).click();

  await expect(page.locator(".history article")).toHaveCount(2);
  await expect(page.locator(".history")).toContainText("Correction 1");
  await expect(page.locator(".history")).toContainText("Correction 2");
  await expect(page.locator(".history")).toContainText("Validated");
  await page.screenshot({
    path: "../audit/ui-ux-polish/correction-history.png",
    fullPage: true,
  });
});

test("backend tables expose accessible captions", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Analyze", exact: true }).click();
  await expect(page.getByRole("status")).toContainText("All checks passed");
  await page.getByRole("tab", { name: "Tokens" }).click();
  await expect(
    page.getByRole("cell", { name: "INTEGER_LITERAL", exact: true }).first(),
  ).toBeVisible();
  await expect(
    page.locator("caption").filter({ hasText: "Compiler token stream" }),
  ).toBeAttached();
  await page.getByRole("tab", { name: "Symbol Table" }).click();
  await expect(
    page.locator("caption").filter({ hasText: "Symbols in the global scope" }),
  ).toBeAttached();
});

test("a behavior-changing operator stays in review until the user selects and applies it", async ({ page }) => {
  await page.goto("/");
  await page.locator(".source-editor .view-lines").click();
  await page.keyboard.press("Control+A");
  await page.keyboard.insertText("int main(){ int a,b; if(a.b){return 0;} }");
  await page.getByRole("button", { name: "Correct", exact: true }).click();

  await expect(page.getByRole("status")).toContainText("Source has not changed");
  await expect(page.locator(".source-editor .view-lines")).toContainText("a.b");
  await expect(page.getByRole("button", { name: "Apply Corrected Code" })).toBeDisabled();
  await expect(page.locator(".history")).toContainText("Review required");
  await page.getByRole("button", { name: /Option.*a>b/ }).first().click();
  await page.getByRole("button", { name: "Apply Selected", exact: true }).click();
  await expect(page.locator(".source-editor .view-lines")).toContainText("a>b");
  await expect(page.getByRole("status")).toContainText("All checks passed");
});

test("specification-supported intention repair is previewed and applied only on approval", async ({ page }) => {
  await page.goto("/");
  await page.locator(".source-editor .view-lines").click();
  await page.keyboard.press("Control+A");
  await page.keyboard.insertText("int square(int n){return n+n;}");
  await page.getByRole("tab", { name: "Intention", exact: true }).click();
  await page.getByLabel("Requirement description").fill("Return the square of n");
  await page.getByRole("button", { name: "Analyze Intention", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Possible mismatch with the supplied requirement" })).toBeVisible();
  await expect(page.getByText("Behavioral verification unavailable.", { exact: true })).toBeVisible();
  await expect(page.locator(".source-editor .view-lines")).toContainText("n+n");
  await expect(page.getByRole("button", { name: "Apply Reviewed Intention Repair" })).toHaveCount(0);
  await page.getByRole("button", { name: /Review 1/ }).click();
  await expect(page.getByRole("region", { name: "Selected intention repair" })).toContainText("n * n");
  await expect(page.locator(".source-editor .view-lines")).toContainText("n+n");
  await page.getByRole("button", { name: "Apply Reviewed Intention Repair" }).click();
  await expect(page.locator(".source-editor .view-lines")).toContainText("n * n");
  await expect(page.getByRole("status")).toContainText("All checks passed");
});

test("a changed requirement invalidates an intention preview", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("tab", { name: "Intention", exact: true }).click();
  await page.getByLabel("Return expression").fill("2");
  await page.getByText("Expression locations and input/output examples", { exact: true }).click();
  await page.getByLabel("Return location").fill("1");
  await page.getByRole("button", { name: "Analyze Intention", exact: true }).click();
  await page.getByRole("button", { name: /Review 1/ }).click();
  await expect(page.getByRole("button", { name: "Apply Reviewed Intention Repair" })).toBeEnabled();
  await page.getByLabel("Return expression").fill("3");
  await expect(page.getByRole("button", { name: "Apply Reviewed Intention Repair" })).toHaveCount(0);
});

test("code-only suspicion stays review-only and a source edit invalidates the preview", async ({ page }) => {
  await page.goto("/");
  const editor = page.locator(".source-editor .view-lines");
  await editor.click();
  await page.keyboard.press("Control+A");
  await page.keyboard.insertText("int cost(int a,int b){int bill=a*b;return a;}");
  await page.getByRole("tab", { name: "Intention", exact: true }).click();
  await page.getByLabel("Analysis mode").selectOption("code_only");
  await expect(page.getByLabel("Requirement description")).toHaveCount(0);
  await page.getByRole("button", { name: "Analyze Intention", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Unverified intention hypothesis" })).toBeVisible();
  await page.getByRole("button", { name: /Review 1/ }).click();
  await expect(page.getByText("Code-only hypothesis", { exact: false })).toBeVisible();
  await expect(editor).toContainText("return a;");
  await editor.click();
  await page.keyboard.press("Control+A");
  await page.keyboard.insertText("int cost(int a,int b){return 17;}");
  await expect(page.getByRole("button", { name: "Apply Reviewed Intention Repair" })).toHaveCount(0);
  await expect(editor).toContainText("return 17;");
});

test("natural-language mode exposes unrecognized wording and accepts a supported comparison", async ({ page }) => {
  await page.goto("/");
  const editor = page.locator(".source-editor .view-lines");
  await editor.click();
  await page.keyboard.press("Control+A");
  await page.keyboard.insertText("bool ready(int amount){return amount<5;}");
  await page.getByRole("tab", { name: "Intention", exact: true }).click();
  await page.getByLabel("Analysis mode").selectOption("natural_language");
  await expect(page.getByLabel("Return expression")).toHaveCount(0);
  await page.getByLabel("Requirement description").fill("Check this carefully");
  await page.getByRole("button", { name: "Analyze Intention", exact: true }).click();
  await expect(page.getByText("Unsupported requirement wording.", { exact: false })).toBeVisible();
  await page.getByLabel("Requirement description").fill("Return whether amount is at least 5");
  await page.getByRole("button", { name: "Analyze Intention", exact: true }).click();
  await page.getByRole("button", { name: /Review 1/ }).click();
  await expect(page.getByRole("region", { name: "Selected intention repair" })).toContainText("amount >= 5");
  await expect(editor).toContainText("amount<5");
});
