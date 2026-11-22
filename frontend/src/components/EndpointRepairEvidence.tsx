import type { Phase105Analysis } from "../types/compiler";

const descriptions: Record<string,string> = {
  INCOMPLETE_SPECIFICATION: "Supply typed expected outputs for at least three different inputs.",
  CONSTRAINTS_ALREADY_AGREE: "The checked projection agrees with the supplied examples.",
  COMPATIBLE_EDIT: "One bounded repair agrees with the supplied examples.",
  MULTIPLE_COMPATIBLE_EDITS: "Several bounded repairs agree with the supplied examples.",
  NO_COMPATIBLE_EDIT: "No supported edit agrees with all supplied examples.",
  UNSUPPORTED_PROJECTION: "This source exceeds the endpoint and relational model.",
  ANALYSIS_LIMITED: "Projection reached its work limit.",
};

export function EndpointRepairEvidence({ analysis }: { analysis: Phase105Analysis }) {
  return <section className="guided-evidence" aria-label="Phase 10.5 endpoint evidence">
    <h4>Phase 10.5 endpoint evidence</h4>
    <p>{descriptions[analysis.status] ?? analysis.status}</p>
    {!!analysis.arrays?.length && <ul aria-label="Checked array extents">
      {analysis.arrays.map((array,i) => <li key={i}><code>{array.name}</code> · {array.length} {array.element_type} cells</li>)}
    </ul>}
    {analysis.facts.map((fact,i) => <div key={i}>
      {fact.kind === "endpoint" && <p>
        Search contract · <strong>{fact.contracts.map((name) => name.replaceAll("_"," ")).join(" or ")}</strong>
        {" · "}{fact.termination} · {fact.duplicate_samples} duplicate-key samples of {fact.samples} · line {fact.span.start.line}
      </p>}
      {(fact.kind === "neighbor" || fact.kind === "rotation") && <details>
        <summary>{fact.kind === "rotation" ? "Rotated interval" : "Adjacent cells"} · line {fact.span.start.line}</summary>
        {fact.assumption && <p>{fact.assumption} · {fact.supported_samples} supporting samples</p>}
        <ul>{fact.observations.map((row,index) => <li key={index}>
          Index {row.left_index} held {row.left_value} · index {row.right_index} held {row.right_value}
        </li>)}</ul>
      </details>}
      {fact.kind === "zero" && <p>Zero-input guard · <code>{fact.guard}</code> returns {String(fact.expected)}
        {" · "}division or remainder at line {fact.span.start.line}</p>}
      {fact.kind === "helper" && <p>Checked helper <code>{fact.function}</code> · {fact.assumption}</p>}
      {fact.kind === "origin" && <p>Range origin <code>{fact.origin}</code> · checked array scan at line {fact.scan.start.line}</p>}
    </div>)}
    {!!analysis.access_issues?.length && <ul aria-label="Unavailable cell facts">
      {analysis.access_issues.map((issue,i) => <li key={i}>
        Input {issue.sample} · line {issue.span.start.line} · {issue.status === "INVALID_INDEX" ? "Invalid index" : "Missing cell fact"}
      </li>)}
    </ul>}
  </section>;
}
