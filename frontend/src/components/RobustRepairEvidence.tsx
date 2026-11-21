import { BranchEvidence } from "./FiniteRepairEvidence";
import type { Phase9Analysis } from "../types/compiler";

const status: Record<string, string> = {
  INCOMPLETE_SPECIFICATION: "Supply expectations for at least two distinct inputs.",
  COMPATIBLE_EDIT: "One bounded edit fits the supplied expectations.",
  MULTIPLE_COMPATIBLE_EDITS: "Multiple edits fit the supplied expectations.",
  CONSTRAINTS_ALREADY_AGREE: "The model agrees with the supplied expectations.",
  UNSUPPORTED_PROJECTION: "The selected program falls outside the bounded model.",
  UNSUPPORTED_CHECKED_ARITHMETIC: "Checked arithmetic stopped the projection.",
  INSUFFICIENT_RUNTIME_CONSTRAINTS: "The modeled failure has too little independent output evidence.",
  NO_COMPATIBLE_EDIT: "The bounded search found no compatible edit.",
  NO_MODELED_RUNTIME_FAILURE: "The arithmetic model found no failure on the supplied inputs.",
  ANALYSIS_LIMITED: "The projection reached its work limit.",
};

export function RobustRepairEvidence({ analysis }: { analysis: Phase9Analysis }) {
  const loop = analysis.loop_summary;
  return <section aria-label="Phase 9 evidence" className="guided-evidence">
    <h4>Phase 9 evidence</h4>
    <p>{status[analysis.status] ?? analysis.status.toLowerCase().replaceAll("_", " ")}</p>
    {analysis.branch && <BranchEvidence witness={analysis.branch} />}
    {loop && <>
      <p>{loop.direction} induction · guard <code>{loop.normalized_relation}</code> on line {loop.guard_span.start.line} ·
        step <code>{loop.step_expression}</code> · at most {loop.point_limit} points per input</p>
      <p>Loop-carried values {loop.carriers.map((item) => item.name).join(", ")}</p>
      {loop.iterations && <ul aria-label="Loop projections">{loop.iterations.map((count, index) => <li key={index}>
        Input {index+1} · {count} iterations · {loop.steps?.[index] == null ? "latch skipped" : `step ${loop.steps[index]}`}
        {" · "}exit values <code>{JSON.stringify(loop.exit_states?.[index])}</code>
      </li>)}</ul>}
    </>}
    {analysis.modeled_faults && <section aria-label="Projected arithmetic failures">
      <h5>Static failure projection</h5>
      <ul>{analysis.modeled_faults.map((fault) => <li key={fault.example}>
        Input {fault.example} · line {fault.span.start.line} · {fault.code.toLowerCase().replaceAll("_", " ")}
        {" · "}<code>{fault.operands.join(` ${fault.operator} `)}</code>
      </li>)}</ul>
    </section>}
  </section>;
}
