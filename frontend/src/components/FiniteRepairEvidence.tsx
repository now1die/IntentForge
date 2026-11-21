import type { BranchWitness, IntentionCandidate, LoopWitness, Phase85Analysis } from "../types/compiler";
import type { Span } from "./BehaviorDemo";

const statusLabels: Record<string, string> = {
  INCOMPLETE_SPECIFICATION: "Supply expected outcomes for at least two distinct inputs.",
  CONSTRAINTS_ALREADY_AGREE: "The original model agrees with the supplied expectations.",
  COMPATIBLE_EDIT: "One edit set fits the supplied expectations in the model.",
  MULTIPLE_COMPATIBLE_EDITS: "Multiple edit sets fit the supplied expectations in the model.",
  NO_COMPATIBLE_EDIT: "The bounded search found no compatible edit set.",
  UNSUPPORTED_PROJECTION: "The selected function exceeds the supported branch, coefficient, or counting patterns.",
  UNSUPPORTED_CHECKED_ARITHMETIC: "Checked arithmetic stopped the projection.",
  ANALYSIS_LIMITED: "The projection reached its work limit.",
};

export function BranchEvidence({ witness }: { witness: BranchWitness }) {
  return <>
    {!!witness.guards.length && <ul aria-label="Branch coverage">{witness.guards.map((guard) => <li key={guard.site}>
      Line {guard.span.start.line} · <code>{guard.predicate}</code> · {Object.entries(guard.supplied_coverage)
        .map(([outcome, count]) => `${outcome} on ${count} supplied inputs`).join(" · ")}
    </li>)}</ul>}
    <ul aria-label="Projected return paths">{witness.returns.map((exit, index) => <li key={index}>
      Return on line {exit.span.start.line} · {exit.examples} supplied inputs
      {exit.conditions.length > 0 && ` · ${exit.conditions.map((condition) => {
        const guard = witness.guards.find((row) => row.site === condition.site);
        return `line ${guard?.span.start.line} ${condition.outcome}`;
      }).join(", ")}`}
      {exit.definitions.length > 0 && <> · Reaching definitions {exit.definitions.map((definition) =>
        `${definition.name} (line ${definition.span.start.line})`).join(", ")}</>}
    </li>)}</ul>
  </>;
}

function LoopEvidence({ witness }: { witness: LoopWitness }) {
  return <>
    <p>Loop guard on line {witness.guard_span.start.line} · Step {witness.step} · At most {witness.point_limit} points per input</p>
    <p>Accumulator initialized on line {witness.seed_span.start.line}, updated on line {witness.accumulator_update_span.start.line},
      and returned on line {witness.return_span.start.line}.</p>
    <ul aria-label="Loop sample coverage">{witness.iterations.map((count, index) => <li key={index}>
      Supplied input {index + 1} · {count} iterations · {witness.matches[index]} accumulator updates
    </li>)}</ul>
  </>;
}

export function FiniteRepairEvidence({ analysis }: { analysis: Phase85Analysis }) {
  return <section aria-label="Phase 8.5 constraints" className="guided-evidence">
    <h4>Phase 8.5 constraints</h4>
    <p>{statusLabels[analysis.status] ?? analysis.status.toLowerCase().replaceAll("_", " ")}</p>
    {analysis.examples !== undefined && <p>{analysis.examples} supplied inputs · {analysis.original_mismatches} projected original mismatches</p>}
    {analysis.branch && <BranchEvidence witness={analysis.branch} />}
    {analysis.loop && <LoopEvidence witness={analysis.loop} />}
    {(analysis.branch || analysis.loop) && <p>Coverage describes the supplied inputs. Other paths and inputs may behave differently.</p>}
    {analysis.witnesses?.some((witness) => witness.branch || witness.loop) && <details>
      <summary>Projected coverage after edits</summary>
      {analysis.witnesses.map((witness, index) => <div key={index}>
        <h5>{witness.edits.map((edit) => `Line ${edit.span.start.line} → ${edit.replacement}`).join(", ")}</h5>
        {witness.branch && <BranchEvidence witness={witness.branch} />}
        {witness.loop && <LoopEvidence witness={witness.loop} />}
      </div>)}
    </details>}
  </section>;
}

export function CoordinatedLocations({ edits, onNavigate }: {
  edits: IntentionCandidate["edits"]; onNavigate?: (span: Span) => void;
}) {
  if (edits.length < 2) return null;
  return <section aria-label="Coordinated edit locations">
    <h5>{edits.length} coordinated edits</h5>
    <ul>{edits.map((edit) => {
      const location = `Line ${edit.span.start.line}, column ${edit.span.start.column}`;
      return <li key={edit.span.start.offset}>
        {onNavigate ? <button type="button" onClick={() => onNavigate(edit.span)}>{location}</button> : location}
        {" · "}<code>{edit.original}</code> → <code>{edit.proposed}</code>
      </li>;
    })}</ul>
    <p>Approval applies both edits together.</p>
  </section>;
}
