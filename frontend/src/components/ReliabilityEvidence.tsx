import type { Phase115Analysis } from "../types/compiler";

export function ReliabilityEvidence({ analysis }: { analysis: Phase115Analysis }) {
  if (!analysis.facts.length) return null;
  return <section className="guided-evidence" aria-label="Phase 11.5 reliability evidence">
    <h4>Phase 11.5 reliability evidence</h4>
    {analysis.facts.map((fact, i) => <details open={fact.kind === "interpolation"} key={i}>
      <summary>{fact.contract}{fact.span ? ` · line ${fact.span.start.line}` : ""}</summary>
      {fact.bindings?.length ? <p>Bindings · <code>{fact.bindings.join(", ")}</code></p> : null}
      {fact.extent ? <p>Physical extent · {fact.extent} cells</p> : null}
      {fact.alternatives ? <p>{fact.alternatives} discovery-compatible candidates</p> : null}
      {fact.assumption ? <p>{fact.assumption}</p> : null}
      {fact.samples.length ? <ul aria-label="Supplied input observations">
        {fact.samples.map((row, j) => <li key={j}>Input {row.input}
          {row.start ? ` · entered interval [${row.start.join(", ")}]` : ""}
          {row.negative_empty_endpoint ? " · concrete negative endpoint reaches an empty interval" : ""}
          {row.minima?.length ? ` · minimum positions ${row.minima.join(", ")}` : ""}
          {row.issue ? ` · ${row.issue.toLowerCase().replaceAll("_", " ")}` : ""}
        </li>)}
      </ul> : null}
    </details>)}
  </section>;
}
