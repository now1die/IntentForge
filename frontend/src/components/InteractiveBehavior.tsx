import { useEffect, useRef, useState } from "react";
import { getExecutionCapability, verifyBehavior } from "../services/api";
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
  probes: { arguments: Scalar[]; relation: string;
    candidates: { candidate_id: string; status: string; actual: Scalar | null; issue: string | null }[] }[];
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

function readVectors(input: string): Vector[] {
  const rows: unknown = JSON.parse(input);
  if (!Array.isArray(rows) || !rows.length || rows.length > 12 || rows.some((item) =>
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
  const [expression, setExpression] = useState("");
  const [reply, setReply] = useState<{ snapshot: string; result: VerificationResponse } | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const request = useRef<AbortController | null>(null);
  const discovery = useRef<AbortController | null>(null);
  const snapshot = JSON.stringify([code, entry, vectors, trace, compare, expression, steps, depth, cells]);

  function invalidate() {
    request.current?.abort();
    setReply(null);
    setSelected(null);
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
    try {
      input = readVectors(vectors);
    } catch (failure) {
      setError(failure instanceof SyntaxError ? "Test vectors must be valid JSON." : (failure as Error).message);
      return;
    }
    invalidate();
    const controller = new AbortController();
    request.current = controller;
    setBusy(true);
    try {
      const result = await verifyBehavior({
        source: code, entry_point: entry, vectors: input, trace, compare_candidates: compare,
        limits: { steps: Number(steps), call_depth: Number(depth), memory_cells: Number(cells) },
        ...(compare && expression.trim() ? { return_expression: expression.trim() } : {}),
      }, controller.signal);
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
  const candidate = result?.candidates.find((item) => item.id === selected);

  return <details className="inspector behavior-panel" aria-label="Interactive behavioral verification">
    <summary>Interactive behavioral verification</summary>
    <div className="inspector-body live-behavior">
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
        </div>
        {compare && <label>Expected return expression (optional)<input value={expression} maxLength={160}
          onChange={(event) => setExpression(event.target.value)} /></label>}
        <button className="primary" type="submit" disabled={busy}>{busy ? "Verifying…" : "Run verification"}</button>
      </form>}
      {error && <p role="alert">{error}</p>}
      {result && result.availability.status !== "available" && <p role="status">{result.availability.detail}</p>}
      {result?.original && <>
        <h2>Live interpreter evidence</h2>
        {result.comparison_status === "MULTIPLE_MATCHES" && <p>Multiple candidates match. More test cases may distinguish them.</p>}
        <div className="behavior-evidence">
          <Evidence label="Live original" result={result.original} onNavigate={onNavigate} />
          {result.review_order.map((id) => {
            const item = result.candidates.find((row) => row.id === id);
            return item && <article key={id}>
              <p>Compiler valid · Static rank {item.static_rank} · {item.static_evidence.toLowerCase().replaceAll("_", " ")}</p>
              <p>{item.hypothesis}</p>
              <Evidence label={`Live candidate ${item.static_rank}`} result={item.behavior} />
              <button type="button" onClick={() => setSelected(id)}>Review candidate {item.static_rank}</button>
            </article>;
          })}
        </div>
        {!!result.probes.length && <section aria-label="Candidate disagreement">
          <h3>Candidate probe inputs</h3>
          <p>Inspect candidate outputs and provide an expected value before rerunning a probe as a test.</p>
          <ul>{result.probes.map((probe) => <li key={JSON.stringify(probe.arguments)}>
            <code>{JSON.stringify(probe.arguments)}</code> · {probe.relation} · {probe.candidates.map((row) =>
              `${row.candidate_id}: ${row.actual !== null ? String(row.actual) : row.issue ?? row.status}`).join(" · ")}
            <button type="button" onClick={() => addProbe(probe.arguments)}>Use probe input</button>
          </li>)}</ul>
        </section>}
        {candidate && <section aria-label="Behavioral candidate review">
          <h3>Candidate {candidate.static_rank} · {candidate.id}</h3>
          <div className="diff-pair">
            <pre className="diff-before">{code}</pre><pre className="diff-after">{candidate.source}</pre>
          </div>
          <button type="button" className="primary" onClick={() => onApply(code, candidate.source)}>
            Apply reviewed behavioral repair
          </button>
        </section>}
      </>}
    </div>
  </details>;
}
