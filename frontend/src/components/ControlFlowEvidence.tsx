import type { Phase95Analysis } from "../types/compiler";

const labels: Record<string, string> = {
  INCOMPLETE_SPECIFICATION: "Supply expected values for distinct inputs.",
  CONSTRAINTS_ALREADY_AGREE: "The projected original agrees with the supplied expectations.",
  COMPATIBLE_EDIT: "One bounded edit agrees with all supplied expectations.",
  MULTIPLE_COMPATIBLE_EDITS: "Multiple control-flow edits agree on the supplied inputs.",
  NO_COMPATIBLE_EDIT: "The bounded search found no compatible control-flow edit.",
  UNSUPPORTED_PROJECTION: "This function exceeds the supported control-flow model.",
  INSUFFICIENT_SUCCESSFUL_SAMPLES: "More successful original samples are needed to constrain the repair.",
  ANALYSIS_LIMITED: "The control-flow projection reached its work limit.",
};

function Loops({ loops }: { loops: NonNullable<Phase95Analysis["loops"]> }) {
  return <ul aria-label="Projected loop boundaries">{loops.map((loop, i) => <li key={i}>
    <p><code>{loop.function}</code> · Line {loop.span.start.line} · Origin <code>{loop.origin}</code> ·
      Guard <code>{loop.relation} {loop.bound}</code> · Latch <code>{loop.latch}</code></p>
    {!!loop.indexed_bindings.length && <p>Fixed-cell facts · {loop.indexed_bindings.join(", ")}</p>}
    <ul>{loop.samples.map((sample, j) => <li key={j}>Input {j+1} ·
      {" "}{sample.iterations} iterations{sample.last !== null && ` · first ${sample.first} · last ${sample.last}`}
    </li>)}</ul>
  </li>)}</ul>;
}

export function ControlFlowEvidence({ analysis }: { analysis: Phase95Analysis }) {
  return <section className="guided-evidence" aria-label="Phase 9.5 control-flow evidence">
    <h4>Phase 9.5 control-flow evidence</h4>
    <p>{labels[analysis.status] ?? analysis.status.toLowerCase().replaceAll("_", " ")}</p>
    {!!analysis.loops?.length && <details open>
      <summary>Original loop projections</summary>
      <Loops loops={analysis.loops} />
    </details>}
    {!!analysis.helper_calls && !!Object.keys(analysis.helper_calls).length && <p>Projected helpers · {
      Object.entries(analysis.helper_calls).map(([name, calls]) => `${name} (${calls})`).join(", ")}</p>}
    {!!analysis.exits && Object.keys(analysis.exits).length > 0 && <details>
      <summary>Sampled control transfers</summary>
      <ul>{Object.entries(analysis.exits).map(([site, count]) => <li key={site}>{site.replaceAll("_", " ")} · {count}</li>)}</ul>
    </details>}
    {!!analysis.witnesses?.length && <ul aria-label="Control-flow repair constraints">
      {analysis.witnesses.map((candidate, i) => <li key={i}>
        {candidate.guard ? <p>Entry guard <code>{candidate.guard.parameter} {candidate.guard.comparison} {candidate.guard.threshold}</code>
          {" · "}Return <code>{String(candidate.guard.expected_return)}</code> on supplied inputs {candidate.guard.covered_examples.join(", ")}</p>
          : <details>
            <summary>Line {candidate.edit.span.start.line} · <code>{candidate.edit.replacement}</code></summary>
            {candidate.loops && <Loops loops={candidate.loops} />}
          </details>}
      </li>)}
    </ul>}
  </section>;
}
