import { SpecificationEvidence } from "./SpecificationEvidence";
import { Phase65Evidence } from "./Phase65Evidence";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { analyzeIntention } from "../services/api";
import type { IntentionMode, IntentionRequirement, IntentionResponse, Phase8Inputs } from "../types/compiler";

const findings: Record<string, string> = {
  POSSIBLE_REPAIR: "Possible repairs",
  INSUFFICIENT_SPECIFICATION: "More information required",
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
    return_ordinal: mode !== "examples" && value("return_ordinal") ? Number(value("return_ordinal")) : undefined,
    condition_ordinal: mode !== "examples" && value("condition_ordinal") ? Number(value("condition_ordinal")) : undefined,
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
  const [engineVersion, setEngineVersion] = useState<2 | 3 | 4 | 5 | 55 | 6 | 65 | 7 | 75 | 8>(2);
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
      const options: Phase8Inputs = {};
      if (engineVersion === 8 && input.mode !== "code_only") {
        const fields = new FormData(form);
        const domain = String(fields.get("input_domain") ?? "").trim();
        const partial = String(fields.get("partial_inputs") ?? "").trim();
        try {
          if (domain) options.input_domain = JSON.parse(domain);
          if (partial) options.partial_inputs = JSON.parse(partial);
        } catch {
          setError("Domain and partial inputs must be valid JSON.");
          return;
        }
      }
      const result = await analyzeIntention(code, input.requirement, input.mode, controller.signal, engineVersion, options);
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
    <section className="intention-panel" aria-label="Intention analysis" data-engine={engineVersion}>
      <form onSubmit={(event) => void inspect(event)} onChange={invalidate}>
        <div className="intention-fields">
          <label>Intention engine
            <select value={engineVersion} onChange={(event) => {
              const version = Number(event.target.value) as 2 | 3 | 4 | 5 | 55 | 6 | 65 | 7 | 75 | 8;
              setEngineVersion(version);
              if (version !== 7 && version !== 75 && version !== 8 && mode === "examples") setMode("code_only");
            }}>
              <option value="2">Phase 2.5</option>
              <option value="3">Generalization v3</option>
              <option value="4">Phase 3.5 evidence</option>
              <option value="5">Phase 5 structural evidence</option>
              <option value="55">Phase 5.5 precision gates</option>
              <option value="6">Phase 6 program reasoning</option>
              <option value="65">Phase 6.5 interprocedural reasoning</option>
              <option value="7">Phase 7 guided repair precision</option>
              <option value="75">Phase 7.5 generalized repair recovery</option>
              <option value="8">Phase 8 specification-guided arithmetic</option>
            </select>
          </label>
          <label>Analysis mode
            <select name="mode" value={mode} onChange={(event) => setMode(event.target.value as IntentionMode | "auto")}>
              <option value="auto">Use entered fields</option>
              {(engineVersion === 7 || engineVersion === 75 || engineVersion === 8) && <option value="examples">Supplied input/output examples</option>}
              <option value="code_only">Code only</option>
              <option value="natural_language">Natural-language requirement</option>
              <option value="explicit">Explicit specification</option>
            </select>
          </label>
          {mode !== "code_only" && <label>Function<input name="function" required={mode === "examples"}
            placeholder={mode === "examples" ? "Entry point" : "Optional for a single function"} maxLength={80} /></label>}
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
            {mode !== "examples" && <>
              <label>Return location<input name="return_ordinal" type="number" min={1} max={3000} /></label>
              <label>Condition location<input name="condition_ordinal" type="number" min={1} max={3000} /></label>
            </>}
            <label>Input/output examples<textarea name="examples" maxLength={4000} placeholder='[{"args":[3],"expected_return":9}]' /></label>
            {engineVersion === 8 && <>
              <label>Input domain (JSON)<textarea name="input_domain" maxLength={2000}
                placeholder='[{"minimum":0,"maximum":32},null]' /></label>
              <label>Partial inputs (JSON)<textarea name="partial_inputs" maxLength={2000} placeholder='[[2,3]]' /></label>
            </>}
          </div>
          <p>{mode !== "examples" && "Locations start at 1 in source order. "}Supplied examples inform static hypotheses. Use local verification to observe behavior.</p>
        </details>}
        <button type="submit" className="primary" disabled={busy}>{busy ? "Analyzing intention…" : "Analyze Intention"}</button>
      </form>
      {error && <p role="alert">{error}</p>}
      {result && (
        <section aria-label="Intention results">
          <h3>{findings[result.finding] ?? result.finding}</h3>
          {result.requirement_status === "UNSUPPORTED_DESCRIPTION" &&
            <p><strong>Unsupported requirement wording.</strong> Use a named operation, a comparison, or an explicit expression.</p>}
          {result.guided_evidence && <p>Original behavior awaits isolated verification. Compiler-valid alternatives are available for review when generated.</p>}
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
          {result.program_analysis?.phase8 && <SpecificationEvidence analysis={result.program_analysis.phase8} />}
          {result.program_analysis && <section aria-label="Program-level evidence">
            <h4>Program-level evidence</h4>
            {result.program_analysis.status === "ANALYSIS_LIMITED" && <p>Analysis reached its work limit. Completed evidence is shown.</p>}
            {result.program_analysis.status === "INCOMPLETE_COMPILER_EVIDENCE" && <p>Program reasoning requires a compiler-valid source snapshot.</p>}
            {result.program_analysis.functions.map((fn) => <details key={fn.name}>
              <summary>{fn.name}({fn.parameters.map((parameter) => `${parameter.type} ${parameter.name}`).join(", ")}) · {fn.return_type}</summary>
              <p>{fn.reachable_blocks}/{fn.blocks} reachable control-flow blocks
                {fn.recursion !== "NONE" && ` · ${fn.recursion.toLowerCase().replaceAll("_", " ")} recursion`}</p>
              {!!fn.calls.length && <p>Calls {fn.calls.join(", ")}</p>}
              {fn.possible_missing_return && <p>One modeled path can reach the function exit without returning a value.</p>}
              {!fn.complete && <p>Dependency evidence is incomplete.</p>}
              {!!fn.conditions.length && <ul>{fn.conditions.map((row, index) => <li key={index}>
                {row.kind.replaceAll("_", " ")} · line {row.span.start.line}
                {row.normalized && <code> · {row.normalized.join(" ")}</code>}
              </li>)}</ul>}
              {!!fn.returns.length && <ul aria-label="Return dependencies">{fn.returns.map((row, index) => <li key={index}>
                Return on line {row.span.start.line}{!!row.definitions.length && " depends on "}
                {row.definitions.map((definition) => `${definition.name} (line ${definition.span.start.line})`).join(", ")}
              </li>)}</ul>}
              {result.program_analysis?.phase65 && <Phase65Evidence analysis={result.program_analysis.phase65} name={fn.name} />}
              {!!fn.effects.length && <p>Analysis limits · {fn.effects.map((effect) => effect.replaceAll("_", " ")).join(" · ")}</p>}
            </details>)}
            {!!result.program_analysis.phase65?.withheld.length && <section aria-label="Withheld return hypotheses">
              <h5>Withheld return hypotheses</h5>
              {result.program_analysis.phase65.withheld.map((item, index) => <p key={index}>
                {item.reason} · Line {item.span.start.line}
              </p>)}
            </section>}
          </section>}
          {result.structural_scan && <section aria-label="Structural scan">
            <h4>Structural scan</h4>
            {result.structural_scan.status === "SCAN_LIMITED" && <p>Structural scan reached its work limit.</p>}
            {result.structural_scan.status === "INCOMPLETE_COMPILER_EVIDENCE" && <p>Structural scan needs a compiler-valid program.</p>}
            {result.structural_scan.status === "HEURISTIC_SCAN" && !result.structural_scan.findings.length &&
              !result.structural_scan.withheld?.length &&
              <p>No supported structural suspicion found.</p>}
            {result.structural_scan.findings.map((finding, index) => <article key={index}>
              <strong>{finding.category.toLowerCase().replaceAll("_", " ")}</strong>
              <p>{finding.assumption}</p>
              <ul>{finding.evidence.map((fact, number) => <li key={number}>
                {fact.detail}{fact.span && <small> · Line {fact.span.start.line}</small>}
              </li>)}</ul>
            </article>)}
            {!!result.structural_scan.withheld?.length && <section aria-label="Withheld structural hypotheses">
              <h4>Withheld structural hypotheses</h4>
              {result.structural_scan.withheld.map((item, index) => <article key={index}>
                <strong>{item.category.toLowerCase().replaceAll("_", " ")}</strong>
                <ul>{item.evidence.map((fact, number) => <li key={number}>{fact.detail}</li>)}</ul>
                <p><strong>Counter-evidence or missing evidence</strong> {item.counter_evidence.detail}
                  {item.counter_evidence.span && <small> · Line {item.counter_evidence.span.start.line}</small>}</p>
              </article>)}
            </section>}
          </section>}
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
              {choice.evidence_basis && <p>Evidence basis · {choice.evidence_basis.replaceAll("_", " ")}
                {choice.hypothesis_origin && ` · ${choice.hypothesis_origin === "phase8" ? "Phase 8" : choice.hypothesis_origin === "phase75" ? "Phase 7.5" : choice.hypothesis_origin === "phase65" ? "Phase 6.5" : "Earlier engine"}`}</p>}
              <ul>{choice.evidence.map((fact, index) => <li key={index}>
                {fact.detail}{fact.span && <small> · Line {fact.span.start.line}</small>}
              </li>)}</ul>
              {!!choice.counter_evidence?.length && <ul aria-label="Counter-evidence and missing assumptions">
                {choice.counter_evidence.map((fact, index) => <li key={index}>{fact.detail}</li>)}
              </ul>}
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
