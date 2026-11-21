import type { Phase8Analysis } from "../types/compiler";

const constraintStatus: Record<string, string> = {
  INCOMPLETE_SPECIFICATION: "More trusted inputs needed for arithmetic synthesis",
  SPECIFICATION_ONLY: "Specification validated",
  CONSTRAINTS_ALREADY_AGREE: "Arithmetic constraints agree on supplied inputs",
  COMPATIBLE_EDIT: "One arithmetic edit fits the supplied examples",
  MULTIPLE_COMPATIBLE_EDITS: "Multiple arithmetic edits fit the supplied examples",
  NO_COMPATIBLE_EDIT: "The bounded arithmetic search found no compatible edit",
  UNSUPPORTED_EXPRESSION: "The expression is outside the bounded arithmetic model",
  UNSUPPORTED_CHECKED_ARITHMETIC: "The model encountered overflow or an invalid divisor",
  ANALYSIS_LIMITED: "Arithmetic analysis reached its work limit",
};

export function SpecificationEvidence({ analysis }: { analysis: Phase8Analysis }) {
  const spec = analysis.specification;
  return <section aria-label="Trusted requirements" className="guided-evidence">
    <h4>Trusted requirements</h4>
    {spec.function && <p><code>{spec.function}({spec.parameters.map((p) => `${p.type} ${p.name}`).join(", ")})</code>
      {spec.return_type && ` · returns ${spec.return_type}`}</p>}
    <p>{spec.trusted_examples} supplied expectations{spec.partial_inputs > 0 && ` · ${spec.partial_inputs} partial inputs`}</p>
    {spec.input_domain && <ul aria-label="Input domain">{spec.input_domain.map((axis, position) => <li key={position}>
      {spec.parameters[position]?.name ?? `Argument ${position + 1}`} · {axis ? `[${axis.minimum}, ${axis.maximum}]` : "Unrestricted within scalar type"}
    </li>)}</ul>}
    <p>{constraintStatus[analysis.constraints.status] ?? spec.status.toLowerCase().replaceAll("_", " ")}</p>
    {!!analysis.constraints.helper_functions.length && <p>Traced helpers · {analysis.constraints.helper_functions.join(", ")}</p>}
  </section>;
}
