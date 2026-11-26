import { useEffect, useRef, useState } from "react";
import { ChartBar, GitBranch, Stack, TreeStructure } from "@phosphor-icons/react";
import { Evidence } from "../components/BehaviorDemo";
import type { VerificationResponse } from "../components/InteractiveBehavior";
import { ASTView } from "../components/ASTView";
import { SymbolTableView } from "../components/SymbolTableView";
import { SemanticStateEvidence } from "../components/SemanticStateEvidence";
import { analyzeIntention } from "../services/api";
import type { AnalysisResponse, IntentionResponse, SourceSpan } from "../types/compiler";
import { FlowDiagram } from "./Graph";
import { INTENTFORGE_ENGINE, type ExampleCase } from "./Intention";
import frozen from "../../../benchmarks/reports/phase13-static-v1.json";
import ablations from "../../../benchmarks/reports/phase12-static-v1.json";

const engines = [2,3,4,5,55,6,65,7,75,8,85,9,95,10,105,11,115,12,13] as const;
const engineName = (value: number) => value === 2 ? "Phase 2.5" : value === 3 ? "ML v3" : value === 4 ? "Phase 3.5"
  : value === 105 || value === 115 || (value >= 55 && value < 100) ? `Phase ${value / 10}` : `Phase ${value}`;
const sections = ["Control-flow graph","AST","Program State","Dataflow","Program Relationships","Candidate Evidence","Verification Results","Benchmarks","Ablation Studies"] as const;
const versions = ["13","12","115","11","105"] as const;
const ratio = (m: {hits:number;total:number}) => `${m.hits} / ${m.total}`;
const current = frozen.profiles["13"].metrics;

export function Benchmarks({ detailed = false }: { detailed?: boolean }) {
  const real = current["adapted-real-defect"];
  const authored = current["authored-injected"];
  return <>
    <section className="paper-card recorded-results"><h2><ChartBar /> Benchmark Results</h2><p>Frozen documented adaptations · guided unless labeled</p>
      <div className="bench-metrics">{[
        ["Behavioral recovery",ratio(real.behavioral)], ["Exact recovery",ratio(real.exact)],
        ["Code-only recovery",`${real.code_only_behavioral.hits + authored.code_only_behavioral.hits} / ${real.code_only_behavioral.total + authored.code_only_behavioral.total}`],
      ].map(([label,value]) => <div key={label}><span>{label}</span><strong>{value}</strong></div>)}</div>
      {detailed && <><p>Code-only includes documented and authored faults. Authored guided recovery {ratio(authored.behavioral)}.</p>
        <p>Archived diagnostic recovery {frozen.archive.filter(row => row.candidates.some(c => c.holdout === "MATCHES_SUPPLIED_TESTS")).length} / {frozen.archive.length} behaviorally.</p></>}
    </section>
    <section className="paper-card engine-comparison"><h2><Stack /> Engine Comparison</h2><p>Same documented cohort and supplied examples</p>
      <div className="table-scroll"><table><thead><tr><th>Engine</th><th>Behavioral</th><th>Exact</th></tr></thead><tbody>
        {versions.map((version) => {
          const cases = frozen.profiles[version].metrics["adapted-real-defect"];
          return <tr key={version}><th>{engineName(Number(version))}</th><td>{ratio(cases.behavioral)}</td><td>{ratio(cases.exact)}</td></tr>;
        })}
      </tbody></table></div>
    </section>
  </>;
}

export function ResearchWorkspace({ code, fullC, compiler, program, expected, entry, locate, onCompiler, execution, verification }: {
  code: string; fullC: boolean; compiler: AnalysisResponse | null; program: IntentionResponse | null;
  expected: ExampleCase[]; entry: string; locate: (span: SourceSpan) => void;
  onCompiler: () => void; execution: string; verification: VerificationResponse | null;
}) {
  const [section,setSection] = useState<typeof sections[number]>("Control-flow graph");
  const [engine,setEngine] = useState<typeof engines[number]>(INTENTFORGE_ENGINE);
  const [last,setLast] = useState<{code:string; engine:number; entry:string; expected:ExampleCase[]; result:IntentionResponse} | null>(null);
  const [fn,setFn] = useState("");
  const [busy,setBusy] = useState(false);
  const [error,setError] = useState("");
  const request = useRef<AbortController | null>(null);
  useEffect(() => { request.current?.abort(); setBusy(false); setError(""); setFn(""); }, [code,fullC,engine,entry,expected]);
  useEffect(() => () => request.current?.abort(), []);
  const result = last?.code === code && last.engine === engine && last.entry === entry && last.expected === expected ? last.result :
    engine === INTENTFORGE_ENGINE ? program : null;
  const functions = result?.program_analysis?.functions ?? [];
  const active = functions.find(row => row.name === (fn || entry)) ?? functions[0];
  const graph = active?.cfg;

  async function inspect() {
    onCompiler();
    if (fullC) return;
    request.current?.abort();
    const controller = new AbortController();
    request.current = controller;
    setBusy(true);setError("");
    try {
      const guided = [7,75,8,85,9,95,10,105,11,115,12,13].some(v => v === engine) && entry && expected.length > 0;
      const result = await analyzeIntention(code,guided ? {function:entry,examples:expected} : null,
        guided ? "examples" : "code_only",controller.signal,engine,undefined,true);
      if (!controller.signal.aborted) setLast({code,engine,entry,expected,result});
    } catch (failure) {
      if (!controller.signal.aborted) setError((failure as Error).message);
    } finally {
      if (!controller.signal.aborted) setBusy(false);
    }
  }
  return <>
    <div className="paper-card research-controls">
      <div className="research-sections" role="group" aria-label="Research sections">
        {sections.map(item => <button key={item} type="button" aria-pressed={section===item}
          onClick={() => setSection(item)}>{item}</button>)}
      </div>
      <label>Engine <select value={engine} onChange={event => setEngine(Number(event.target.value) as typeof engine)}>
        {engines.map(value => <option key={value} value={value}>{engineName(value)}{value === 13 ? " · current" : ""}</option>)}</select></label>
      <button type="button" className="primary" disabled={busy} onClick={() => void inspect()}>{busy ? "Analyzing…" : "Run Research Analysis"}</button>
    </div>
    <div className="research-center paper-card"><h2><GitBranch /> {section === "Control-flow graph" ? "Control-Flow Graph (CFG)" : section}</h2>
      {error && <p role="alert" className="p14-error">{error}</p>}
      {busy && <p role="status">Collecting evidence…</p>}
      {result?.program_analysis?.status === "ANALYSIS_LIMITED" && <p>Analysis reached a work or source limit. Completed evidence appears below.</p>}
      {section === "Control-flow graph" && <>
        {functions.length > 1 && <label>Graph function<select value={active?.name} onChange={e => setFn(e.target.value)}>
          {functions.map(row => <option key={row.name}>{row.name}</option>)}</select></label>}
        {graph ? <FlowDiagram key={JSON.stringify([code,engine,active.name])} graph={graph} code={code} onLocate={locate} />
          : <p>{fullC ? "Control-flow graphs are available for Mini-C." : result && !result.compiler_valid ? "Compiler errors prevent graph construction."
            : result ? "This profile or source did not return a graph." : "Run research analysis to build a graph for the current source."}</p>}
      </>}
      {section === "AST" && <ASTView ast={compiler?.ast ?? null} />}
      {section === "Program State" && <>{result?.program_analysis?.phase12 ?
        <SemanticStateEvidence analysis={result.program_analysis.phase12} /> : <p>No bounded state evidence is available for the selected profile and source.</p>}
        <SymbolTableView symbols={compiler?.symbols ?? null} /></>}
      {section === "Dataflow" && (active ? <>
        <h3>{active.name} · Reaching definitions for returns</h3>
        {active.returns.length ? <ul>{active.returns.map((row,i) => <li key={i}>Return on line {row.span.start.line}
          <ul>{row.definitions.map((definition,j) => <li key={j}><button type="button" onClick={() => locate(definition.span)}>
            {definition.name} · Block {definition.site} · Line {definition.span.start.line}</button></li>)}</ul>
          {!row.definitions.length && <p>No reaching definition recorded.</p>}</li>)}</ul> : <p>No reachable return evidence recorded.</p>}
        {!!active.effects.length && <p>Analysis limits · {active.effects.join(" · ").replaceAll("_"," ")}</p>}
      </> : <p>Run research analysis to collect return dependencies.</p>)}
      {section === "Program Relationships" && (active ? <>
        <p>Calls from {active.name} · {active.calls.join(", ") || "None recorded"}</p><p>Recursion · {active.recursion.toLowerCase()}</p>
        {result?.program_analysis?.phase11 && <details><summary>Relational constraints</summary><pre>{JSON.stringify(result.program_analysis.phase11,null,2)}</pre></details>}
      </> : <p>Run analysis with a program-reasoning profile to inspect relationships.</p>)}
      {section === "Candidate Evidence" && <>
        {result?.candidates.length ? <><p>Candidate Ranking · {result.ranking}</p>{result.candidates.map(candidate => <details key={candidate.id}>
          <summary>{candidate.category.replaceAll("_"," ").toLowerCase()} · {candidate.id}</summary>
          <p>{candidate.hypothesis}</p><ul>{[...candidate.evidence,...(candidate.counter_evidence ?? [])].map((fact,i) => <li key={i}>{fact.detail}</li>)}</ul>
        </details>)}</> : <p>No candidate evidence on this source and profile.</p>}
        {!!result && <details><summary>Raw engine report</summary><pre>{JSON.stringify(result,null,2)}</pre></details>}
      </>}
      {section === "Verification Results" && <><p>{execution}</p>
        {verification?.original ? <>
          <Evidence label="Original" result={verification.original} onNavigate={span => locate({start:{...span.start,offset:0},end:{...span.start,offset:0}})} />
          {verification.candidates.map(candidate => <Evidence key={candidate.id} label={`Candidate ${candidate.static_rank}`} result={candidate.behavior} />)}
        </> : <p>Run Intention with supplied expectations to collect observations for the current source.</p>}
        <a href="#intention">Open Test Behavior</a></>}
      {section === "Benchmarks" && <Benchmarks detailed />}
      {section === "Ablation Studies" && <><p>Phase 12 documented adaptations by enabled component, measured at freeze.</p>
        <table><thead><tr><th>Component</th><th>Behavioral</th><th>Exact</th></tr></thead><tbody>
        {(["state","logical","initialization","coordinate","12"] as const).map(version => {
          const cases = ablations.profiles[version].metrics["adapted-real-defect"];
          return <tr key={version}><th>{version === "12" ? "Combined" : version}</th><td>{ratio(cases.behavioral)}</td><td>{ratio(cases.exact)}</td></tr>;
        })}</tbody></table></>}
    </div>
    <div className="research-right"><Benchmarks />
      <section className="paper-card"><h2><TreeStructure /> Technical Data</h2>
        {graph && active ? <dl className="flow-facts"><dt>Function</dt><dd>{active.name}</dd><dt>Basic blocks</dt><dd>{graph.blocks.length}</dd>
          <dt>Edges</dt><dd>{graph.edges.length}</dd><dt>Loop conditions</dt><dd>{graph.blocks.filter(row => row.kind === "loop_header").length}</dd>
          <dt>Return type</dt><dd>{active.return_type}</dd></dl> : <p>Analyze a Mini-C function to see live graph metrics.</p>}
      </section>
      <section className="paper-card"><h2>Historical workbench</h2><p>Reproduce older engine outputs, recorded demonstrations and advanced verification settings.</p>
        <a href="/classic" target="_blank" rel="opener" onClick={() => {
          try { sessionStorage.setItem("intentforge-classic-source",JSON.stringify({code,fullC})); } catch { /* Storage can be disabled. */ }
        }}>Open historical workbench ↗</a></section>
    </div>
  </>;
}
