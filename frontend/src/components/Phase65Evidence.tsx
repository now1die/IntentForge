import type { Phase65Analysis } from "../types/compiler";

function lineNumber(span: { start: { line: number } }) {
  return span.start.line;
}

export function Phase65Evidence({ analysis, name }: { analysis: Phase65Analysis; name: string }) {
  const paths = analysis.paths[name];
  const summary = analysis.interprocedural[name];
  if (!paths && !summary) return null;

  return <section aria-label="Path and call evidence">
    {paths && <>
      <h5>Return paths</h5>
      {!paths.complete && <p>Some paths could not be classified within the work limit.</p>}
      {!!paths.unresolved_conditions.length && <p>Conditions with unknown outcomes: {paths.unresolved_conditions.length}.</p>}
      <ul>{paths.returns.map((row) => <li key={row.site}>
        Line {lineNumber(row.span)} · {row.feasibility === "excluded" ? "Excluded by modeled constraints" : row.feasibility}
        {row.paths.map((state, index) => <div key={index}>
          {state.facts.length ? state.facts.map((fact) => `${fact.name} ∈ [${fact.min}, ${fact.max}]${fact.excluded.length ? ` excluding ${fact.excluded.join(", ")}` : ""}`).join(" · ") : "No atomic branch facts"}
          {!state.dependencies_complete && <div>Upstream dependency evidence is incomplete.</div>}
          {!!state.possible_upstream_definitions.length && <div>Possible upstream definitions · {state.possible_upstream_definitions.map((item) => `${item.name} (line ${lineNumber(item.span)})`).join(", ")}</div>}
          {!!state.definitions.length && <div>Reaching definitions · {state.definitions.map((item) => `${item.name} (line ${lineNumber(item.span)})`).join(", ")}</div>}
        </div>)}
      </li>)}</ul>
      {!!paths.recursive_returns.length && <>
        <h5>Recurrence</h5>
        {paths.recursive_returns.map((row) => <p key={row.site}><code>{row.expression}</code> · {row.self_calls} self-call{row.self_calls === 1 ? "" : "s"}</p>)}
        {paths.base_guards.map((guard, index) => <p key={index}>Base return when <code>{guard.condition}</code> is {String(guard.outcome)} · line {lineNumber(guard.span)}</p>)}
        <p>Other modeled return sites: {paths.other_return_sites.length}. Supplied examples are required to compare recurrence operators.</p>
      </>}
    </>}
    {summary && <>
      <h5>Function dependencies</h5>
      {summary.scalar_helper && <p>Scalar helper · depth {summary.scalar_helper.depth} · Possible argument inputs {summary.scalar_helper.parameter_inputs.map((position) => position + 1).join(", ") || "none"}</p>}
      <p>Possible return argument positions · {summary.return_parameter_inputs.map((position) => position + 1).join(", ") || "none"}</p>
      {summary.effects_unknown && <p>Call effects remain unknown. Global accesses are conservatively included.</p>}
      {!!summary.call_sites.length && <ul>{summary.call_sites.map((call, index) => <li key={index}>
        {call.self_recursive ? "Self-call" : call.target || "Unknown callee"} · line {lineNumber(call.span)}
        {call.feeds_return && " · feeds return"}
        {!!call.arguments.length && <ul>{call.arguments.map((argument) => <li key={argument.position}>
          Argument {argument.position + 1}{argument.parameter && ` → ${argument.parameter}`}
          {argument.affine && <code> · {argument.affine.name}
            {argument.affine.offset > 0 && ` + ${argument.affine.offset}`}
            {argument.affine.offset < 0 && ` − ${-argument.affine.offset}`}</code>}
        </li>)}</ul>}
        {call.callee_result_inputs && <p>Callee result argument positions · {call.callee_result_inputs.map((position) => position + 1).join(", ") || "none"}</p>}
      </li>)}</ul>}
    </>}
  </section>;
}
