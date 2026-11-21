import { useEffect, useRef, useState } from "react";
import { getExecutionCapability, verifyBehavior } from "../services/api";
import { FiniteRepairEvidence, CoordinatedLocations } from "./FiniteRepairEvidence";
import { SearchRepairEvidence } from "./SearchRepairEvidence";
import { ControlFlowEvidence } from "./ControlFlowEvidence";
import { RobustRepairEvidence } from "./RobustRepairEvidence";
import { SpecificationEvidence } from "./SpecificationEvidence";
import type { IntentionCandidate, Phase8Analysis } from "../types/compiler";
import { Evidence, type BehaviorEvidence, type Span } from "./BehaviorDemo";

type Scalar = number | boolean;
type Vector = { arguments: Scalar[]; expected: Scalar };
export type ExecutionCapability = { status: string; detail: string };
export type VerificationResponse = {
  availability: ExecutionCapability;
  program: string;
  original: BehaviorEvidence | null;
  candidates: { id: string; static_rank: number; static_evidence: string; hypothesis: string; source: string;
    behavior: BehaviorEvidence }[];
  review_order: string[];
  comparison_status: string | null;
  guided_evidence?: {
    original: keyof typeof originalEvidence;
    review: "REVIEW_MATCHING_REPAIR" | "MULTIPLE_PLAUSIBLE_REPAIRS" | "POSSIBLE_REPAIR" | "ABSTAIN";
    confirmed_fault: boolean;
    recommended_candidate: string | null;
    matching_candidates: string[];
  };
  candidate_pairs?: { candidates: [string, string]; status: keyof typeof pairEvidence; compared_inputs: number }[];
  candidate_categories?: Record<string, string>;
  review_presentation?: "OPTIONAL_COLLAPSED" | "REVIEW_VISIBLE";
  specification?: Phase8Analysis | null;
  runtime_observation?: {
    program: string;
    input: Scalar[] | null;
    issue: { code: string; message: string; span: Span | null };
    alternatives: Record<string, { completed_trusted_suite: boolean; matched_trusted_suite: boolean }>;
  } | null;
  candidate_details?: Record<string, {
    evidence: { detail: string }[];
    counter_evidence: { detail: string }[];
    evidence_basis: string;
    edits: IntentionCandidate["edits"];
  }>;
  probes: { arguments: Scalar[]; relation: string;
    assessment?: string; separated_pairs?: number; new_pairs?: number; steps?: number; input_basis?: string;
    candidates: { candidate_id: string; status: string; actual: Scalar | null; issue: string | null }[] }[];
};
const originalEvidence = {
  CONFIRMED_TEST_MISMATCH: "Confirmed mismatch on supplied tests",
  ORIGINAL_MATCHES_SUPPLIED_TESTS: "Original matches supplied tests",
  INSUFFICIENT_SPECIFICATION: "More information required",
  RUNTIME_FAILURE: "Original execution encountered a runtime failure",
  EXECUTION_LIMITED: "Original execution reached a resource limit",
  EXECUTION_UNSUPPORTED: "Original execution is unsupported",
  VERIFICATION_UNAVAILABLE: "Verification unavailable",
};

const pairEvidence = {
  distinguished: "Different observed outcomes",
  agreed_on_probes: "Agreed on tested probes",
  inconclusive: "Inconclusive observations",
  untested: "No probe comparisons",
};

type Props = {
  code: string;
  functions: string[];
  onNavigate: (span: Span) => void;
  onApply: (original: string, proposed: string) => void;
};

function scalar(value: unknown): value is Scalar {
  return typeof value === "boolean" || (typeof value === "number" && Number.isInteger(value)
    && value >= -2147483648 && value <= 2147483647);
}

function readVectors(input: string, observational: boolean): Vector[] {
  const rows: unknown = JSON.parse(input);
  if (!Array.isArray(rows) || (!observational && !rows.length) || rows.length > 12 || rows.some((item) =>
    !item || !Array.isArray(item.arguments) || item.arguments.length > 16
    || !item.arguments.every(scalar) || !scalar(item.expected))) {
    throw new Error("Supply one to twelve tests with integer or Boolean arguments and an explicit expected value.");
  }
  return rows.map((item) => ({ arguments: item.arguments, expected: item.expected }));
}

export function InteractiveBehavior({ code, functions, onNavigate, onApply }: Props) {
  const [capability, setCapability] = useState<ExecutionCapability | null>(null);
  const [entry, setEntry] = useState("");
  const [vectors, setVectors] = useState("[]");
  const [steps, setSteps] = useState("10000");
  const [depth, setDepth] = useState("32");
  const [cells, setCells] = useState("4096");
  const [trace, setTrace] = useState(false);
  const [compare, setCompare] = useState(false);
  const [phase5, setPhase5] = useState(false);
  const [profile, setProfile] = useState<5 | 55 | 6 | 65 | 7 | 75 | 8 | 85 | 9 | 95 | 10>(5);
  const [inputDomain, setInputDomain] = useState("");
  const [showOptional, setShowOptional] = useState(false);
  const [expression, setExpression] = useState("");
  const [reply, setReply] = useState<{ snapshot: string; result: VerificationResponse } | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const request = useRef<AbortController | null>(null);
  const discovery = useRef<AbortController | null>(null);
  const snapshot = JSON.stringify([code, entry, vectors, trace, compare, phase5, profile, expression, inputDomain, steps, depth, cells]);

  function invalidate() {
    request.current?.abort();
    setReply(null);
    setSelected(null);
    setShowOptional(false);
    setBusy(false);
    setError(null);
  }

  function refresh() {
    discovery.current?.abort();
    const controller = new AbortController();
    discovery.current = controller;
    setCapability(null);
    async function discover() {
      let result = await getExecutionCapability(controller.signal);
      for (let attempt = 0; attempt < 4 && result.status === "capacity_reached" && !controller.signal.aborted; attempt++) {
        await new Promise((resolve) => setTimeout(resolve, 500));
        if (!controller.signal.aborted) result = await getExecutionCapability(controller.signal);
      }
      return result;
    }
    discover().then((result) => {
      if (!controller.signal.aborted) setCapability(result);
    }).catch(() => {
      if (!controller.signal.aborted) setCapability({ status: "worker_unavailable", detail: "The execution gateway is unavailable." });
    });
  }

  useEffect(() => {
    refresh();
    return () => discovery.current?.abort();
  }, []);

  useEffect(() => {
    invalidate();
    return () => request.current?.abort();
  }, [snapshot]);

  async function verify() {
    let input: Vector[];
    let domain: unknown;
    try {
      input = readVectors(vectors, compare && phase5);
      if (phase5 && (profile === 8 || profile === 85 || profile === 9 || profile === 95 || profile === 10) && inputDomain.trim()) domain = JSON.parse(inputDomain);
    } catch (failure) {
      const jsonMessage = phase5 && (profile === 8 || profile === 85 || profile === 9 || profile === 95 || profile === 10) ? "Test vectors and input domain must be valid JSON." : "Test vectors must be valid JSON.";
      setError(failure instanceof SyntaxError ? jsonMessage : (failure as Error).message);
      return;
    }
    invalidate();
    const controller = new AbortController();
    request.current = controller;
    setBusy(true);
    try {
      const payload = {
        source: code, entry_point: entry, vectors: input, trace, compare_candidates: compare,
        ...(phase5 ? { engine_version: profile } : {}),
        ...(domain !== undefined ? { input_domain: domain } : {}),
        limits: { steps: Number(steps), call_depth: Number(depth), memory_cells: Number(cells) },
        ...(compare && expression.trim() ? { return_expression: expression.trim() } : {}),
      };
      let result = await verifyBehavior(payload, controller.signal);
      if (result.availability.status === "capacity_reached" && !controller.signal.aborted) {
        await new Promise((resolve) => setTimeout(resolve, 650));
        if (!controller.signal.aborted) result = await verifyBehavior(payload, controller.signal);
      }
      if (!controller.signal.aborted) setReply({ snapshot, result });
    } catch (failure) {
      if (!controller.signal.aborted) setError(failure instanceof Error ? failure.message : "Could not verify behavior.");
    } finally {
      if (!controller.signal.aborted) setBusy(false);
    }
  }

  function addProbe(args: Scalar[]) {
    try {
      const rows = JSON.parse(vectors);
      if (!Array.isArray(rows) || rows.length >= 12) {
        setError("At most twelve tests can be verified in one run.");
        return;
      }
      setVectors(JSON.stringify([...rows, { arguments: args, expected: null }], null, 2));
    } catch {
      setError("Correct the test-vector JSON first.");
    }
  }

  const result = reply?.snapshot === snapshot ? reply.result : null;
  const optional = result?.review_presentation === "OPTIONAL_COLLAPSED";
  const showSuggestions = !optional || showOptional;
  const candidate = showSuggestions ? result?.candidates.find((item) => item.id === selected) : undefined;

  return <details className="inspector behavior-panel" aria-label="Interactive behavioral verification">
    <summary>Interactive behavioral verification</summary>
    <div className="live-behavior">
      <p>{capability?.detail ?? "Checking local execution availability…"}</p>
      {capability?.status !== "available" && <>
        <p>Recorded demonstrations are available below.</p>
        <button type="button" onClick={refresh}>Refresh execution availability</button>
      </>}
      {capability?.status === "available" && <form onSubmit={(event) => { event.preventDefault(); void verify(); }}>
        <div className="intention-fields">
          <label>Entry point<input required maxLength={80} pattern="[A-Za-z_][A-Za-z_0-9]*"
            list="behavior-functions" value={entry} onChange={(event) => setEntry(event.target.value)} /></label>
          <datalist id="behavior-functions">{functions.map((name) => <option key={name} value={name} />)}</datalist>
          <label>Step limit<input type="number" required min={1} max={20000} value={steps} onChange={(event) => setSteps(event.target.value)} /></label>
          <label>Call-depth limit<input type="number" required min={1} max={64} value={depth} onChange={(event) => setDepth(event.target.value)} /></label>
          <label>Cell limit<input type="number" required min={1} max={8192} value={cells} onChange={(event) => setCells(event.target.value)} /></label>
        </div>
        <label>Test vectors (JSON)<textarea rows={5} maxLength={3800} value={vectors} spellCheck={false}
          placeholder='[{"arguments":[4],"expected":8}]' onChange={(event) => setVectors(event.target.value)} /></label>
        <div className="behavior-controls">
          <label><input type="checkbox" checked={trace} onChange={(event) => setTrace(event.target.checked)} /> Record trace</label>
          <label><input type="checkbox" checked={compare} onChange={(event) => setCompare(event.target.checked)} /> Compare repair candidates</label>
          {compare && <label><input type="checkbox" checked={phase5} onChange={(event) => setPhase5(event.target.checked)} /> Phase 5 repair and probes</label>}
          {compare && phase5 && <label><input type="checkbox" checked={profile === 55} onChange={(event) => setProfile(event.target.checked ? 55 : 5)} /> Phase 5.5 precision gates</label>}
          {compare && phase5 && <label><input type="checkbox" checked={profile === 6} onChange={(event) => setProfile(event.target.checked ? 6 : 5)} /> Phase 6 program reasoning</label>}
          {compare && phase5 && <label><input type="checkbox" checked={profile === 65} onChange={(event) => setProfile(event.target.checked ? 65 : 5)} /> Phase 6.5 interprocedural reasoning</label>}
          {compare && phase5 && <label><input type="checkbox" checked={profile === 7} onChange={(event) => setProfile(event.target.checked ? 7 : 5)} /> Phase 7 guided repair precision</label>}
          {compare && phase5 && <label><input type="checkbox" checked={profile === 75} onChange={(event) => setProfile(event.target.checked ? 75 : 5)} /> Phase 7.5 generalized repair recovery</label>}
          {compare && phase5 && <label><input type="checkbox" checked={profile === 8} onChange={(event) => setProfile(event.target.checked ? 8 : 5)} /> Phase 8 specification-guided arithmetic</label>}
          {compare && phase5 && <label><input type="checkbox" checked={profile === 85} onChange={(event) => setProfile(event.target.checked ? 85 : 5)} /> Phase 8.5 branch-aware repair</label>}
          {compare && phase5 && <label><input type="checkbox" checked={profile === 9} onChange={(event) => setProfile(event.target.checked ? 9 : 5)} /> Phase 9 semantic robustness</label>}
          {compare && phase5 && <label><input type="checkbox" checked={profile === 95} onChange={(event) => setProfile(event.target.checked ? 95 : 5)} /> Phase 9.5 control-flow repair</label>}
          {compare && phase5 && <label><input type="checkbox" checked={profile === 10} onChange={(event) => setProfile(event.target.checked ? 10 : 5)} /> Phase 10 search repair</label>}
        </div>
        {phase5 && (profile === 8 || profile === 85 || profile === 9 || profile === 95 || profile === 10) && <label>Input domain (JSON)<textarea rows={2} value={inputDomain} maxLength={2000}
          placeholder='[{"minimum":0,"maximum":32},null]' onChange={(event) => setInputDomain(event.target.value)} /></label>}
        {compare && phase5 && <p>Use an empty test list to compare probe observations without expected values.</p>}
        {compare && <label>Expected return expression (optional)<input value={expression} maxLength={160}
          onChange={(event) => setExpression(event.target.value)} /></label>}
        <button className="primary" type="submit" disabled={busy}>{busy ? "Verifying…" : "Run verification"}</button>
      </form>}
      {error && <p role="alert">{error}</p>}
      {result && result.availability.status !== "available" && <p role="status">{result.availability.detail}</p>}
      {result?.specification && <SpecificationEvidence analysis={result.specification} />}
      {result?.specification?.phase10 && <SearchRepairEvidence analysis={result.specification.phase10} />}
      {result?.specification?.phase95 && <ControlFlowEvidence analysis={result.specification.phase95} />}
      {result?.specification?.phase9 && !result.specification.phase95?.loops?.length && <RobustRepairEvidence analysis={result.specification.phase9} />}
      {result?.specification?.phase85 && !result.specification.phase9?.branch && !result.specification.phase9?.loop_summary
        && <FiniteRepairEvidence analysis={result.specification.phase85} />}
      {result?.runtime_observation && <section aria-label="Observed runtime failure" className="guided-evidence">
        <h4>Observed runtime failure</h4>
        <p>{result.runtime_observation.issue.message}</p>
        {result.runtime_observation.input && <p>Triggering input <code>{JSON.stringify(result.runtime_observation.input)}</code></p>}
        {result.runtime_observation.issue.span && <button type="button"
          onClick={() => onNavigate(result.runtime_observation!.issue.span!)}>Go to failing expression</button>}
        <p>Source snapshot <code>{result.runtime_observation.program.slice(0,12)}</code></p>
      </section>}
      {result?.guided_evidence && <section className="guided-evidence" aria-label="Guided repair evidence">
        <h2>Original verification</h2>
        <p role={result.guided_evidence.confirmed_fault ? "alert" : "status"}>{originalEvidence[result.guided_evidence.original]}</p>
        {result.guided_evidence.review === "REVIEW_MATCHING_REPAIR" && <p>One candidate matches the supplied tests and is eligible for guided review.</p>}
        {result.guided_evidence.review === "MULTIPLE_PLAUSIBLE_REPAIRS" && <p>Multiple candidate behaviors remain plausible. Supply a distinguishing expectation.</p>}
        {result.guided_evidence.review === "POSSIBLE_REPAIR" && <p>Compiler-valid hypotheses are available for manual inspection.</p>}
      </section>}
      {result?.original && <>
        <h2>Live interpreter evidence</h2>
        {phase5 && result.original.status === "ORACLE_UNAVAILABLE" && <p>Observational comparison. Candidates retain static order until you supply expected outputs.</p>}
        {result.comparison_status === "MULTIPLE_MATCHES" && <p>Multiple candidates match. More test cases may distinguish them.</p>}
        {optional && <button type="button" aria-expanded={showOptional} onClick={() => {
          if (showOptional) setSelected(null);
          setShowOptional(!showOptional);
        }}>{showOptional ? "Hide" : "Show"} optional repairs ({result.candidates.length})</button>}
        {showSuggestions && result.guided_evidence && !!result.candidates.length && <h3>Repair suggestions</h3>}
        <div className="behavior-evidence">
          <Evidence label="Live original" result={result.original} onNavigate={onNavigate} observationOnly={phase5} />
          {showSuggestions && result.review_order.map((id, index) => {
            const item = result.candidates.find((row) => row.id === id);
            return item && <article key={id}>
              <p>Compiler valid · Static rank {item.static_rank} · {item.static_evidence.toLowerCase().replaceAll("_", " ")}</p>
              {phase5 && <p>Review position {index + 1} · {item.id}</p>}
              {result.candidate_categories?.[id] && <p>{result.candidate_categories[id].toLowerCase().replaceAll("_", " ")}</p>}
              {result.guided_evidence?.recommended_candidate === id && <p>Eligible for guided review</p>}
              <p>{item.hypothesis}</p>
              {result.runtime_observation?.alternatives[id]?.completed_trusted_suite &&
                <p>{result.runtime_observation.alternatives[id].matched_trusted_suite
                  ? "Completed and matched all supplied tests." : "Completed with a supplied-test mismatch."}</p>}
              {result.candidate_details?.[id] && <details>
                <summary>Supporting evidence and uncertainty</summary>
                <ul>{result.candidate_details[id].evidence.map((fact, number) => <li key={number}>{fact.detail}</li>)}</ul>
                <ul>{result.candidate_details[id].counter_evidence.map((fact, number) => <li key={number}>{fact.detail}</li>)}</ul>
              </details>}
              <Evidence label={`Live candidate ${item.static_rank}`} result={item.behavior} observationOnly={phase5} />
              <button type="button" onClick={() => setSelected(id)}>Review candidate {item.static_rank}</button>
            </article>;
          })}
        </div>
        {showSuggestions && !!result.candidate_pairs?.length && <section aria-label="Candidate pair outcomes">
          <h3>Candidate pair outcomes</h3>
          <ul>{result.candidate_pairs.map((pair) => <li key={pair.candidates.join("/")}>
            {pair.candidates.map((id) => result.candidates.find((item) => item.id === id)?.static_rank ?? id).join(" / ")}
            {" · "}{pairEvidence[pair.status]} · {pair.compared_inputs} compared inputs
          </li>)}</ul>
        </section>}
        {showSuggestions && !!result.probes.length && <section aria-label="Candidate disagreement">
          <h3>Candidate probe inputs</h3>
          <p>Inspect candidate outputs and provide an expected value before rerunning a probe as a test.</p>
          <ul>{result.probes.map((probe) => <li key={JSON.stringify(probe.arguments)}>
            <code>{JSON.stringify(probe.arguments)}</code> · {probe.relation} · {probe.candidates.map((row) =>
              `${row.candidate_id}: ${row.actual !== null ? String(row.actual) : row.issue ?? row.status}`).join(" · ")}
            {probe.assessment && <small> · {probe.assessment.replaceAll("_", " ")} · {probe.separated_pairs} {probe.separated_pairs === 1 ? "pair" : "pairs"}
              {" "}({probe.new_pairs} new) · {probe.steps} steps · {probe.input_basis?.replaceAll("_", " ")}</small>}
            <button type="button" onClick={() => addProbe(probe.arguments)}>Use probe input</button>
          </li>)}</ul>
        </section>}
        {candidate && <section aria-label="Behavioral candidate review">
          <h3>Candidate {candidate.static_rank} · {candidate.id}</h3>
          {(profile === 85 || profile === 9 || profile === 95 || profile === 10) && result.candidate_details?.[candidate.id] &&
            <CoordinatedLocations edits={result.candidate_details[candidate.id].edits} onNavigate={onNavigate} />}
          <div className="behavior-evidence">
            <div><strong>Original source</strong><pre className="diff-before">{code}</pre></div>
            <div><strong>Proposed source</strong><pre className="diff-after">{candidate.source}</pre></div>
          </div>
          <button type="button" className="primary" onClick={() => onApply(code, candidate.source)}>
            Apply reviewed behavioral repair
          </button>
        </section>}
      </>}
    </div>
  </details>;
}
