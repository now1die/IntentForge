import { useEffect, useRef, useState, type FormEvent } from "react";
import { analyzeIntention } from "../services/api";
import type { IntentionMode, IntentionRequirement, IntentionResponse } from "../types/compiler";

const findings: Record<string, string> = {
  COMPILER_ERROR: "Compiler-detected error",
  SPECIFICATION_SUPPORTED_SUSPICION: "Possible mismatch with the supplied requirement",
  HEURISTIC_SUSPICION: "Unverified intention hypothesis",
  NO_SUPPORTED_MISMATCH: "No supported mismatch found",
  UNSUPPORTED_LANGUAGE: "Unsupported Mini-C construct",
};

const decisions: Record<string, string> = {
  STRONG_SPECIFICATION_EVIDENCE: "The proposed expression matches the supplied requirement. Review before applying.",
  AMBIGUOUS: "Several repairs are plausible. Choose a candidate to inspect.",
  REVIEW_UNCERTAIN: "One candidate is available, with insufficient evidence to establish intent.",
  INSUFFICIENT_CONTEXT: "More context is needed to infer an intended repair.",
  REQUIREMENT_SHAPE_MATCHES: "The selected expression matches the supplied requirement structurally.",
  NO_SUPPORTED_CORRECTION: "No supported repair is available.",
  BUDGET_EXHAUSTED: "The analysis budget expired. Only completed checks are shown.",
};

function readRequirement(form: HTMLFormElement): { mode: IntentionMode; requirement: IntentionRequirement | null } {
  const data = new FormData(form);
  const value = (key: string) => String(data.get(key) ?? "").trim() || undefined;
  const selected = value("mode");
  const mode = selected === "auto"
    ? (value("return_expression") || value("condition") ? "explicit" : value("description") ? "natural_language" : "code_only")
    : selected as IntentionMode;
  if (mode === "code_only") return { mode, requirement: null };
  const vectors = value("examples");
  const examples = vectors ? JSON.parse(vectors) : undefined;
  if (examples !== undefined && !Array.isArray(examples)) throw new Error("Examples must be a JSON array.");
  const requirement = {
    function: value("function"),
    description: mode === "natural_language" ? value("description") : undefined,
    return_expression: mode === "explicit" ? value("return_expression") : undefined,
    condition: mode === "explicit" ? value("condition") : undefined,
    return_ordinal: value("return_ordinal") ? Number(value("return_ordinal")) : undefined,
    condition_ordinal: value("condition_ordinal") ? Number(value("condition_ordinal")) : undefined,
    examples,
  };
  return { mode, requirement };
}

export function IntentionPanel({ code, onApply }: {
  code: string;
  onApply: (original: string, proposed: string) => void;
}) {
  const pending = useRef<AbortController | null>(null);
  const [busy, setBusy] = useState(false);
  const [engineVersion, setEngineVersion] = useState<2 | 3 | 4>(2);
  const [mode, setMode] = useState<IntentionMode | "auto">("auto");
  const [error, setError] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<{ code: string; result: IntentionResponse } | null>(null);
  const [selected, setSelected] = useState<string | null>(null);

  useEffect(() => {
    setBusy(false);
    setError(null);
    setAnalysis(null);
    setSelected(null);
    return () => pending.current?.abort();
  }, [code]);

  function invalidate() {
    pending.current?.abort();
    setBusy(false);
    setAnalysis(null);
    setSelected(null);
    setError(null);
  }

  async function inspect(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    invalidate();
    const controller = new AbortController();
    pending.current = controller;
    setBusy(true);
    try {
      let input: ReturnType<typeof readRequirement>;
      try {
        input = readRequirement(form);
      } catch (failure) {
        setError(failure instanceof SyntaxError ? "Examples must be valid JSON." : String(failure));
        return;
      }
      const result = await analyzeIntention(code, input.requirement, input.mode, controller.signal, engineVersion);
      if (!controller.signal.aborted) setAnalysis({ code, result });
    } catch (failure) {
      if (!controller.signal.aborted) setError(failure instanceof Error ? failure.message : "Intention analysis failed.");
    } finally {
      if (!controller.signal.aborted) setBusy(false);
    }
  }

  const result = analysis?.code === code ? analysis.result : null;
  const choice = result?.candidates.find((candidate) => candidate.id === selected);

  return (
    <section className="intention-panel" aria-label="Intention analysis">
      <form onSubmit={(event) => void inspect(event)} onChange={invalidate}>
        <div className="intention-fields">
          <label>Intention engine
            <select value={engineVersion} onChange={(event) => setEngineVersion(event.target.value === "4" ? 4 : event.target.value === "3" ? 3 : 2)}>
              <option value="2">Phase 2.5</option>
              <option value="3">Generalization v3</option>
              <option value="4">Phase 3.5 evidence</option>
            </select>
          </label>
          <label>Analysis mode
            <select name="mode" value={mode} onChange={(event) => setMode(event.target.value as IntentionMode | "auto")}>
              <option value="auto">Use entered fields</option>
              <option value="code_only">Code only</option>
              <option value="natural_language">Natural-language requirement</option>
              <option value="explicit">Explicit specification</option>
            </select>
          </label>
          {mode !== "code_only" && <label>Function<input name="function" placeholder="Optional for a single function" maxLength={80} /></label>}
          {(mode === "auto" || mode === "explicit") && <>
            <label>Return expression<input name="return_expression" placeholder="x * x" maxLength={160} /></label>
            <label>Condition<input name="condition" placeholder="age >= 18" maxLength={160} /></label>
          </>}
          {(mode === "auto" || mode === "natural_language") &&
            <label>Requirement description<input name="description" placeholder="Return the maximum of left and right" maxLength={400} /></label>}
        </div>
        {mode !== "code_only" && <details>
          <summary>Expression locations and input/output examples</summary>
          <div className="intention-fields">
            <label>Return location<input name="return_ordinal" type="number" min={1} max={3000} /></label>
            <label>Condition location<input name="condition_ordinal" type="number" min={1} max={3000} /></label>
            <label>Input/output examples<textarea name="examples" maxLength={4000} placeholder='[{"args":[3],"expected_return":9}]' /></label>
          </div>
          <p>Locations start at 1 in source order. Examples are recorded for review.</p>
        </details>}
        <button type="submit" className="primary" disabled={busy}>{busy ? "Analyzing intention…" : "Analyze Intention"}</button>
      </form>
      {error && <p role="alert">{error}</p>}
      {result && (
        <section aria-label="Intention results">
          <h3>{findings[result.finding] ?? result.finding}</h3>
          {result.requirement_status === "UNSUPPORTED_DESCRIPTION" &&
            <p><strong>Unsupported requirement wording.</strong> Use a named operation, a comparison, or an explicit expression.</p>}
          <p>{decisions[result.decision] ?? result.decision}</p>
          {result.recommendation === "ABSTAIN" && <p>No repair recommendation. Review the available evidence.</p>}
          {result.recommendation === "REVIEW_WITH_EVIDENCE" && <p>Evidence supports reviewing the first alternative.</p>}
          <p>{result.behavioral_status === "EXECUTION_UNSUPPORTED"
            ? "Behavioral checks are unsupported for this source." : "Behavioral verification unavailable."}</p>
          {result.candidates.length > 0 && <p>{result.ranking === "LEARNED"
            || result.ranking === "EXPANDED_LEARNED" || result.ranking === "V3_LEARNED" || result.ranking === "V4_LEARNED"
            ? "The model ranked comparable alternatives. Relative scores indicate order."
            : "Compiler evidence and contextual rules ordered these alternatives."}</p>}
          {result.diagnostics.map((diagnostic, index) => (
            <p key={index}>{diagnostic.message}</p>
          ))}
          {result.evidence.map((fact, index) => <p key={index}>{fact.detail}</p>)}
          {result.notes.map((note) => <p key={note}>{note}</p>)}
          {result.candidates.length > 0 && (
            <ul className="intention-candidates">
              {result.candidates.map((candidate, index) => (
                <li key={candidate.id}>
                  <button type="button" aria-pressed={selected === candidate.id} onClick={() => setSelected(candidate.id)}>
                    Review {index + 1} · {candidate.category.toLowerCase().replaceAll("_", " ")}
                  </button>
                  {" "}{candidate.compiler_valid ? "Compiler valid" : "Diagnostics remain"}
                  {engineVersion !== 4 && candidate.relative_score !== null && <small> · Relative rank score {candidate.relative_score.toFixed(2)}</small>}
                </li>
              ))}
            </ul>
          )}
          {choice && analysis && (
            <section className="intention-preview" aria-label="Selected intention repair">
              <h4>Proposed edit</h4>
              <p><strong>Assumption</strong> {choice.hypothesis}</p>
              <p><strong>Evidence strength</strong> {
                choice.tier === "STRONG_CONTEXT" ? "Strong contextual hypothesis"
                  : choice.tier === "WEAK_CONTEXT" ? "Weak contextual hypothesis"
                  : choice.evidence.some((fact) => fact.kind === "USER_REQUIREMENT")
                  ? "Supported by the supplied requirement"
                  : result.finding === "COMPILER_ERROR" ? "Compiler-supported repair hypothesis" : "Code-only hypothesis"
              }</p>
              <ul>{choice.evidence.map((fact, index) => <li key={index}>
                {fact.detail}{fact.span && <small> · Line {fact.span.start.line}</small>}
              </li>)}</ul>
              {choice.edits.map((edit, index) => (
                <div className="inline-diff" key={index}>
                  <div className="diff-pair">
                    <code className="diff-before"><span aria-hidden="true">−</span>{edit.original || "(empty)"}</code>
                    <code className="diff-after"><span aria-hidden="true">+</span>{edit.proposed || "(removed)"}</code>
                  </div>
                </div>
              ))}
              <p>{choice.safety.reason}</p>
              <button type="button" className="primary" disabled={!choice.compiler_valid}
                onClick={() => onApply(analysis.code, choice.proposed_code)}>Apply Reviewed Intention Repair</button>
            </section>
          )}
        </section>
      )}
    </section>
  );
}
