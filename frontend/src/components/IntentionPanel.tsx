import { useEffect, useRef, useState, type FormEvent } from "react";
import { analyzeIntention } from "../services/api";
import type { IntentionRequirement, IntentionResponse } from "../types/compiler";

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

function readRequirement(form: HTMLFormElement): IntentionRequirement | null {
  const data = new FormData(form);
  const value = (key: string) => String(data.get(key) ?? "").trim() || undefined;
  const vectors = value("examples");
  const examples = vectors ? JSON.parse(vectors) : undefined;
  if (examples !== undefined && !Array.isArray(examples)) throw new Error("Examples must be a JSON array.");
  const requirement = {
    function: value("function"),
    description: value("description"),
    return_expression: value("return_expression"),
    condition: value("condition"),
    return_ordinal: value("return_ordinal") ? Number(value("return_ordinal")) : undefined,
    condition_ordinal: value("condition_ordinal") ? Number(value("condition_ordinal")) : undefined,
    examples,
  };
  return Object.values(requirement).some((item) => item !== undefined) ? requirement : null;
}

export function IntentionPanel({ code, onApply }: {
  code: string;
  onApply: (original: string, proposed: string) => void;
}) {
  const pending = useRef<AbortController | null>(null);
  const [busy, setBusy] = useState(false);
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
      let requirement: IntentionRequirement | null;
      try {
        requirement = readRequirement(form);
      } catch (failure) {
        setError(failure instanceof SyntaxError ? "Examples must be valid JSON." : String(failure));
        return;
      }
      const result = await analyzeIntention(code, requirement, controller.signal);
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
        <p>Analyze the source with an optional requirement. Changes need your approval.</p>
        <div className="intention-fields">
          <label>Function<input name="function" placeholder="Optional for a single function" maxLength={80} /></label>
          <label>Return expression<input name="return_expression" placeholder="x * x" maxLength={160} /></label>
          <label>Condition<input name="condition" placeholder="age >= 18" maxLength={160} /></label>
          <label>Requirement description<input name="description" placeholder="Return the square of x" maxLength={400} /></label>
        </div>
        <details>
          <summary>Expression locations and input/output examples</summary>
          <div className="intention-fields">
            <label>Return location<input name="return_ordinal" type="number" min={1} max={3000} /></label>
            <label>Condition location<input name="condition_ordinal" type="number" min={1} max={3000} /></label>
            <label>Input/output examples<textarea name="examples" maxLength={4000} placeholder='[{"args":[3],"expected_return":9}]' /></label>
          </div>
          <p>Locations start at 1 in source order. Examples are recorded for review.</p>
        </details>
        <button type="submit" className="primary" disabled={busy}>{busy ? "Analyzing intention…" : "Analyze Intention"}</button>
      </form>
      {error && <p role="alert">{error}</p>}
      {result && (
        <section aria-label="Intention results">
          <h3>{findings[result.finding] ?? result.finding}</h3>
          <p>{decisions[result.decision] ?? result.decision}</p>
          <p>{result.behavioral_status === "EXECUTION_UNSUPPORTED"
            ? "Behavioral checks are unsupported for this source." : "Behavioral verification unavailable."}</p>
          {result.candidates.length > 0 && <p>{result.ranking === "LEARNED"
            ? "The model ranked comparable alternatives. Relative scores are not probabilities."
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
                  {candidate.relative_score !== null && <small> · Relative rank score {candidate.relative_score.toFixed(2)}</small>}
                </li>
              ))}
            </ul>
          )}
          {choice && analysis && (
            <section className="intention-preview" aria-label="Selected intention repair">
              <h4>Proposed edit</h4>
              <p>{choice.hypothesis}</p>
              <ul>{choice.evidence.map((fact, index) => <li key={index}>{fact.detail}</li>)}</ul>
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
