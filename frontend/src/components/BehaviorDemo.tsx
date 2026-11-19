import { useEffect, useState } from "react";
import recorded from "../data/phase4-demonstrations.json";

type Scalar = number | boolean;
type Vector = { arguments: Scalar[]; expected: Scalar };
export type Span = { start: { line: number; column: number } };
export type BehaviorEvidence = {
  status: string;
  entry_point: string;
  observations: { vector: Vector; actual: Scalar }[];
  diagnostics: string[];
  execution: {
    vectors: Vector[];
    issue: { code: string; message: string; vector: number | null; span: Span | null } | null;
    trace: { kind: string; vector: number; step: number; span: Span | null }[];
    trace_truncated: boolean;
    samples?: { steps: number; peak_cells: number; call_depth: number }[];
  } | null;
};

const statusLabels: Record<string, string> = {
  MATCHES_SUPPLIED_TESTS: "Matches supplied tests",
  MISMATCHES_SUPPLIED_TESTS: "Mismatches supplied tests",
  EXECUTION_LIMITED: "Execution limited",
  EXECUTION_UNSUPPORTED: "Execution unsupported",
  BEHAVIOR_UNKNOWN: "Behavior unknown",
  ORACLE_UNAVAILABLE: "Behavioral verification unavailable",
};

function location(span: Span | null) {
  return span ? `line ${span.start.line}, column ${span.start.column}` : "Location unavailable";
}

export function Evidence({ label, result, onNavigate, observationOnly = false }: {
  label: string; result: BehaviorEvidence; onNavigate?: (span: Span) => void; observationOnly?: boolean;
}) {
  if (observationOnly && result.status === "ORACLE_UNAVAILABLE") return <section className="behavior-run" aria-label={label}>
    <h3>{label}</h3>
    <p>No expected values supplied.</p>
  </section>;
  const issue = result.execution?.issue;
  return <section className="behavior-run" aria-label={label}>
    <h3>{label}</h3>
    <p>{statusLabels[result.status] ?? result.status}</p>
    {issue && <p><strong>{issue.code}</strong> · {issue.message} · {issue.span && onNavigate
      ? <button type="button" onClick={() => onNavigate(issue.span!)}>{location(issue.span)}</button>
      : location(issue.span)}</p>}
    {!issue && result.diagnostics.map((message) => <p key={message}>{message}</p>)}
    <div className="behavior-table">
      <table>
        <caption>{label} test results</caption>
        <thead><tr><th scope="col">Arguments</th><th scope="col">Expected</th>
          <th scope="col">Observed</th><th scope="col">Outcome</th></tr></thead>
        <tbody>{result.execution?.vectors.map((vector, index) => {
          const observation = result.observations[index];
          const outcome = observation
            ? observation.actual === vector.expected ? "Pass" : "Fail"
            : issue?.vector === index ? "Stopped" : "Unavailable";
          return <tr key={index}><td><code>{JSON.stringify(vector.arguments)}</code></td>
            <td>{String(vector.expected)}</td>
            <td>{observation ? String(observation.actual) : "—"}</td><td>{outcome}</td></tr>;
        })}</tbody>
      </table>
    </div>
    {onNavigate && !!result.execution?.samples?.length && <ol aria-label="Execution usage">
      {result.execution.samples.map((sample, i) => <li key={i}>
        Test {i + 1} · {sample.steps} steps · {sample.peak_cells} peak cells · depth {sample.call_depth}
      </li>)}
    </ol>}
    {!!result.execution?.trace.length && <details>
      <summary>Execution trace</summary>
      {result.execution.trace_truncated && <p>Trace truncated at the recording limit.</p>}
      <ol>{result.execution.trace.map((item, index) => <li key={index}>
        Test {item.vector + 1} · Step {item.step} · {item.kind.toLowerCase().replaceAll("_", " ")} · {location(item.span)}
      </li>)}</ol>
    </details>}
  </section>;
}

export function BehaviorDemo({ code, onLoad }: { code: string; onLoad: (source: string) => void }) {
  const [selection, setSelection] = useState(recorded[0].id);
  const [loaded, setLoaded] = useState(false);
  const chosen = recorded.find((item) => item.id === selection) ?? recorded[0];
  useEffect(() => {
    if (code !== chosen.source) setLoaded(false);
  }, [code, chosen.source]);

  return <details className="inspector behavior-panel" aria-label="Behavioral verification">
    <summary>Behavioral verification</summary>
    <div className="inspector-body">
      <p>Recorded observations from the Mini-C interpreter on trusted examples. Execution of editor submissions is unavailable.</p>
      <div className="behavior-controls">
        <label>Trusted example <select value={selection} onChange={(event) => {
          setLoaded(false);
          setSelection(event.target.value);
        }}>{recorded.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</select></label>
        <button type="button" className="primary" onClick={() => {
          onLoad(chosen.source);
          setLoaded(true);
        }}>Load trusted example</button>
      </div>
      {loaded && code === chosen.source && <>
        <p>Entry point <code>{chosen.original.entry_point}</code>. Test agreement applies to the supplied vectors.</p>
        {chosen.comparison_status === "MULTIPLE_MATCHES" && <p>Multiple candidates match. Intent remains ambiguous.</p>}
        <div className="behavior-evidence">
          <Evidence label="Original program" result={chosen.original} />
          {chosen.candidates.map((candidate) => <div key={candidate.id}>
            <Evidence label={`Candidate ${candidate.static_rank}`} result={candidate.behavior} />
            <details><summary>View proposed source</summary><pre>{candidate.proposed_code}</pre></details>
          </div>)}
        </div>
        {chosen.skipped_candidates > 0 && <p>{chosen.skipped_candidates} candidate(s) had no recorded run.</p>}
        {chosen.candidates.length > 0 && <p>Candidate changes require explicit approval in the correction workflow.</p>}
      </>}
    </div>
  </details>;
}
