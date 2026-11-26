import { CheckCircle, Code, GitBranch, Stack, WarningCircle } from "@phosphor-icons/react";
import type { AnalysisResponse, Diagnostic, IntentionResponse, Scope, SourceSpan } from "../types/compiler";
import { FlowDiagram } from "./Graph";

export function getFunctions(analysis: AnalysisResponse | null) {
  const nodes = analysis?.ast?.functions;
  if (!Array.isArray(nodes)) return [];
  return (nodes as { name: string; return_type: string; parameters: { name: string; type_name: string }[] }[])
    .map((item) => ({ name: item.name, result: item.return_type,
      parameters: item.parameters.map(({name, type_name}) => ({name, type: type_name})) }));
}

function variableCount(scope: Scope): number {
  return scope.symbols.filter((symbol) => ["variable", "array", "parameter"].includes(symbol.kind.toLowerCase())).length
    + scope.children.reduce((total, child) => total + variableCount(child), 0);
}

export function CompileResult({ analysis, diagnostics, busy, focus, onFix, correction, technical }: {
  analysis: AnalysisResponse | null;
  diagnostics: Diagnostic[];
  busy: string | null;
  focus: (d: Diagnostic) => void;
  onFix: () => void;
  correction: boolean;
  technical: React.ReactNode;
}) {
  const phases = [["lexical", "Lexical analysis", Code], ["syntax", "Syntax analysis", Stack],
    ["semantic", "Semantic analysis", GitBranch]] as const;
  return <aside className="paper-card compile-status" aria-label="Compilation result">
    <header><span className="heading-icon">{analysis?.success ? <CheckCircle size={26} /> : <Code size={26} />}</span>
      <div><h2>{busy ? "Checking source…" : !analysis ? "Compilation Result" : analysis.success ? "Compilation Successful"
        : `${diagnostics.length} compilation ${diagnostics.length === 1 ? "issue" : "issues"}`}</h2>
      <p>{analysis?.success ? "The source passed compiler checks. Use Intention to check expected behavior."
        : analysis ? "Open a diagnostic to inspect its source location." : "Analyze your source to see results here."}</p></div>
    </header>
    <div className="pipeline-summary">{phases.map(([phase,title,Icon]) => {
      const success = analysis?.[phase].success;
      return <div key={phase}><Icon size={18} /><span>{title}</span>
        <span className={`p14-badge ${success ? "success" : success === false ? "error" : ""}`}>
          {success ? "Passed" : success === false ? "Issues" : analysis ? "Not run" : "Pending"}</span></div>;
    })}</div>
    {!!diagnostics.length && <><ul className="compile-issues">{diagnostics.map(d => <li key={d.diagnostic_id}>
      <button type="button" onClick={() => focus(d)}><WarningCircle size={16} /><span>{d.message}</span><small>Line {d.line}</small></button>
    </li>)}</ul>
    {analysis && !analysis.syntax.success && <button type="button" disabled={!!busy} onClick={onFix}>Find compiler fixes</button>}</>}
    {correction && <details><summary>Repair Summary</summary>{technical}</details>}
  </aside>;
}

export function Overview({ analysis, program, code, locate }: {
  analysis: AnalysisResponse | null; program: IntentionResponse["program_analysis"] | null; code: string;
  locate: (span: SourceSpan) => void;
}) {
  const functions = getFunctions(analysis);
  const main = functions.find(f => f.name === "main") ?? functions[0];
  const graph = (program?.functions.find(fn => fn.name === main?.name) ?? program?.functions[0])?.cfg;
  return <div className="program-overview">
    <div><h2>Program Overview</h2>
      <p>{!analysis ? "Run Analyze Code to populate the overview." : !analysis.success ? "The compiler could only analyze part of this source."
        : main ? `${main.name} returns ${main.result}${main.parameters.length ? ` and takes ${main.parameters.length} input${main.parameters.length === 1 ? "" : "s"}` : " and takes no inputs"}.`
        : "The compiler found no function definitions."}</p>
      {analysis && <dl className="overview-metrics">
        <div><dt>Functions</dt><dd>{analysis.ast ? functions.length : "—"}</dd></div>
        <div><dt>Variables</dt><dd>{analysis.symbols ? variableCount(analysis.symbols.root) : "—"}</dd></div>
        <div><dt>Return type{main ? ` (${main.name})` : ""}</dt><dd>{main?.result ?? "—"}</dd></div>
      </dl>}
      {graph && <a href="#research">Explore Analysis <span aria-hidden="true">→</span></a>}
    </div>
    {graph && <FlowDiagram key={code} graph={graph} code={code} onLocate={locate} compact />}
  </div>;
}
