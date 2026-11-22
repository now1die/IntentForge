import type { Phase11Analysis } from "../types/compiler";

const states: Record<string,string> = {
  INCOMPLETE_SPECIFICATION: "Supply typed outputs for at least three different inputs.",
  CONSTRAINTS_ALREADY_AGREE: "The checked projection agrees with the supplied outputs.",
  MULTIPLE_COMPATIBLE_EDITS: "Several edits agree with the supplied outputs.",
  COMPATIBLE_EDIT: "One bounded edit agrees with the supplied outputs.",
  NO_COMPATIBLE_EDIT: "No supported edit agrees with every supplied output.",
  UNSUPPORTED_PROJECTION: "This source exceeds the relational projection.",
  ANALYSIS_LIMITED: "Analysis reached its bounded work limit.",
};

const relationLabels: Record<string,string> = {
  interpolation: "Interpolation denominator",
  helper: "Zero and magnitude helper contract",
  cyclic: "Cyclic ordering",
  range: "Coordinated range origin",
  cells: "Checked cell relationship",
};

export function RelationalRepairEvidence({ analysis }: { analysis: Phase11Analysis }) {
  return <section className="guided-evidence" aria-label="Phase 11 relational evidence">
    <h4>Phase 11 relational evidence</h4>
    <p>{states[analysis.status] ?? analysis.status}</p>
    {analysis.endpoint_contracts?.map((fact,i) => <p key={i}>
      Endpoint contract in <code>{fact.function}</code> · {fact.contracts.map((name) => name.replaceAll("_"," ")).join(" or ")}
      {" · "}{fact.duplicate_samples} duplicate-key samples
    </p>)}
    {analysis.facts.map((fact,i) => <details key={i} open={fact.kind==="interpolation"}>
      <summary>{relationLabels[fact.kind] ?? fact.kind} · line {fact.span.start.line}</summary>
      <p>Bindings · <code>{fact.bindings.join(", ")}</code></p>
      {!!fact.compiler.length && <p>Compiler facts · {fact.compiler.join(" · ")}</p>}
      {fact.assumptions.map((assumption,j) => <p key={j}>{assumption}</p>)}
      {fact.hypothesis && <p>Hypothesis · {fact.hypothesis}</p>}
      {!!fact.samples.length && <ul aria-label="Supplied input observations">
        {fact.samples.map((sample,j) => <li key={j}>Input {sample.input}
          {sample.denominator !== undefined && ` · [${sample.low}, ${sample.high}] · endpoints ${sample.lower_value}, ${sample.upper_value} · denominator ${sample.denominator}`}
          {sample.descents && ` · cyclic descents ${sample.descents.join(", ") || "none"} · ${sample.duplicates ? "duplicate cells" : "distinct cells"}`}
          {sample.arguments && ` · ${JSON.stringify(sample.arguments)} · original result ${String(sample.observed)}`}
          {sample.issue && ` · ${sample.issue.toLowerCase().replaceAll("_"," ")}`}
        </li>)}
      </ul>}
    </details>)}
  </section>;
}
