import { useEffect, useRef, useState, type FormEvent } from "react";
import { Flask, Check, Plus, Target, Trash, WarningCircle } from "@phosphor-icons/react";
import { analyzeIntention, verifyBehavior } from "../services/api";
import type { IntentionCandidate, IntentionMode, IntentionRequirement, IntentionResponse, Phase8Inputs } from "../types/compiler";
import type { ExecutionCapability, VerificationResponse } from "../components/InteractiveBehavior";
import { Evidence } from "../components/BehaviorDemo";
import type { getFunctions } from "./compiler";

export const INTENTFORGE_ENGINE = 13;
export type ExampleCase = NonNullable<IntentionRequirement["examples"]>[number];
type Scalar = ExampleCase["expected_return"];
type Draft = { args: string[]; expected: string };
export type Expected = { key: number; entry: string; examples: ExampleCase[] };

const draft = (examples: ExampleCase[]): Draft[] =>
  examples.map((row) => ({args: row.args.map(String), expected: String(row.expected_return)}));

function readScalar(text: string, type?: string): Scalar {
  const value = text.trim();
  if ((type === undefined || type === "bool") && (value === "true" || value === "false")) return value === "true";
  const number = Number(value);
  if ((type === undefined || type === "int") && /^-?\d+$/.test(value) && Number.isInteger(number)
    && number >= -2147483648 && number <= 2147483647) return number;
  throw new Error(type === "bool" ? "Enter true or false for Boolean values." : type === "int" ?
    "Enter a signed 32-bit integer." : "Enter a Mini-C scalar value (integer or Boolean).");
}

const parseCases = (rows: Draft[], signature?: ReturnType<typeof getFunctions>[number]): ExampleCase[] =>
  rows.map((row, index) => {
    try {
      if (signature && row.args.length !== signature.parameters.length) throw new Error("Argument count does not match the function.");
      return { args: row.args.map((v,i) => readScalar(v, signature?.parameters[i]?.type)), expected_return: readScalar(row.expected, signature?.result) };
    } catch (error) {
      throw new Error(`Test case ${index + 1}: ${(error as Error).message}`);
    }
  });

const candidateName = (text: string) => text.toLowerCase().replaceAll("_", " ");
const statusText: Record<string,string> = {
  COMPILER_ERROR: "Compiler errors prevent analysis",
  INSUFFICIENT_CONTEXT: "Insufficient evidence",
  INSUFFICIENT_SPECIFICATION: "Insufficient evidence",
  NO_SUPPORTED_MISMATCH: "No supported repair found",
  UNSUPPORTED_LANGUAGE: "Unsupported Mini-C source",
  UNSUPPORTED_DESCRIPTION: "This requirement wording is unsupported",
  BUDGET_EXHAUSTED: "Analysis reached its work limit",
};

function RepairDiff({ candidate, source }: { candidate: IntentionCandidate; source: string }) {
  const lines = source.split("\n");
  return <div className="repair-diff" aria-label="Source changes">
    {candidate.edits.map((edit,index) => {
      const {start,end} = edit.span;
      const prefix = (lines[start.line-1] ?? "").slice(0,start.column-1);
      const suffix = (lines[end.line-1] ?? "").slice(end.column-1);
      return <div key={index} className="repair-location">
        <p>Line {start.line}, column {start.column}{end.line !== start.line && ` to line ${end.line}`}</p>
        <div className="repair-pair">
          {([["Before",edit.original],["After",edit.proposed]] as const).map(([label,text]) => <div key={label}
            className={label === "Before" ? "removed" : "added"}>
            <strong>{label}</strong><pre tabIndex={0}><code>{(prefix + text + suffix).split("\n").map((line,i) =>
              `${start.line+i}  ${line}`).join("\n")}</code></pre>
          </div>)}
        </div>
      </div>;
    })}
  </div>;
}

export function IntentionWorkspace({ code, fullC, functions, expected, execution, onApply, onEvidence, onVerification, onTests }: {
  code: string; fullC: boolean; functions: ReturnType<typeof getFunctions>; expected: Expected;
  execution: ExecutionCapability | null; onApply: (code: string, replacement: string) => void;
  onEvidence: (analysis: IntentionResponse | null) => void; onVerification: (result: VerificationResponse | null) => void; onTests: (rows: ExampleCase[], entry: string) => void;
}) {
  const [entry, setEntry] = useState(expected.entry);
  const [rows, setRows] = useState(() => draft(expected.examples));
  const [mode, setMode] = useState<IntentionMode>("examples");
  const [result, setResult] = useState<{ source:string; staticResult: IntentionResponse; live: VerificationResponse | null } | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [approval, setApproval] = useState(false);
  const [kept, setKept] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [stale, setStale] = useState(false);
  const [raw, setRaw] = useState("[]");
  const form = useRef<HTMLFormElement>(null);
  const request = useRef<AbortController | null>(null);
  const signature = functions.find(fn => fn.name === entry) ?? (!entry ? functions[0] : undefined);
  const selectedEntry = entry || signature?.name || "";
  const argumentCount = signature?.parameters.length ?? (rows[0]?.args.length ?? 2);
  const current = result?.source === code ? result : null;
  const choice = current?.staticResult.candidates.find(candidate => candidate.id === selected);
  const liveChoice = current?.live?.candidates.find(candidate => candidate.source === choice?.proposed_code);
  const behavior = liveChoice?.behavior.status;
  const verified = behavior === "MATCHES_SUPPLIED_TESTS";
  const contradicts = behavior === "MISMATCHES_SUPPLIED_TESTS";
  const live = current?.live;
  const ambiguous = live?.guided_evidence?.review === "MULTIPLE_PLAUSIBLE_REPAIRS" ||
    current?.staticResult.decision === "AMBIGUOUS" || (!live && (current?.staticResult.candidates.length ?? 0) > 1);

  function invalidate(showStale = false) {
    request.current?.abort();
    setStale(showStale && !!result);
    onEvidence(null); onVerification(null);
    setResult(null); setSelected(null); setApproval(false); setKept(false); setBusy(false); setError(null);
  }

  useEffect(() => {
    invalidate(true);
    return () => request.current?.abort();
  }, [code, fullC]);

  useEffect(() => {
    setRows(draft(expected.examples)); setEntry(expected.entry); setMode(expected.examples.length ? "examples" : "code_only");
    form.current?.reset();
    setRaw("[]");
  }, [expected]);

  function changeRow(index: number, column: number | "expected", text: string) {
    setRows((old) => old.map((row,i) => {
      if (i !== index) return row;
      if (column === "expected") return {...row, expected:text};
      return {...row, args: Array.from({length:argumentCount}, (_,j) => j === column ? text : row.args[j] ?? "")};
    }));
  }

  function importCases() {
    try {
      const input: unknown = JSON.parse(raw);
      if (!Array.isArray(input) || input.length > 12 || input.some((row) =>
        !row || !Array.isArray(row.args) || row.args.length > 16 ||
        [row.expected_return, ...row.args].some((value) => typeof value !== "boolean" && typeof value !== "number"))) {
        throw new Error("Import up to 12 cases with scalar args and expected_return.");
      }
      parseCases(draft(input), signature);
      invalidate();
      setRows(draft(input));
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "JSON import failed.");
    }
  }

  async function inspect(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    invalidate();
    const field = (name: string) => String(data.get(name) ?? "").trim() || undefined;
    const controller = new AbortController();
    request.current = controller;
    setBusy(true);
    try {
      const cases = mode === "code_only" ? [] : parseCases(rows, signature);
      const advanced: Phase8Inputs = {};
      if (mode !== "code_only") {
        if (field("domain")) advanced.input_domain = JSON.parse(field("domain")!);
        if (field("partial")) advanced.partial_inputs = JSON.parse(field("partial")!);
      }
      const requirement: IntentionRequirement | null = mode === "code_only" ? null :
        { function:selectedEntry || undefined, ...(cases.length ? {examples:cases} : {}) };
      if (mode === "examples" && (!selectedEntry || (!cases.length && !advanced.partial_inputs?.length))) {
        throw new Error("Select a function and add an expected result, or supply partial inputs in Advanced Settings.");
      }
      if (requirement && mode === "explicit") {
        requirement.return_expression = field("returnExpression");
        requirement.condition = field("condition");
        if (field("returnLocation")) requirement.return_ordinal = Number(field("returnLocation"));
        if (field("conditionLocation")) requirement.condition_ordinal = Number(field("conditionLocation"));
      }
      if (requirement && mode === "natural_language") requirement.description = field("description");
      const staticResult = await analyzeIntention(code, requirement, mode, controller.signal, INTENTFORGE_ENGINE, advanced, true);
      if (controller.signal.aborted) return;
      setResult({ source:code, staticResult, live:null });
      setSelected(staticResult.candidates[0]?.id ?? null);
      onEvidence(staticResult);
      onTests(cases, selectedEntry);
      if (staticResult.compiler_valid && cases.length && selectedEntry && execution?.status === "available") {
        const verification = await verifyBehavior({
          source:code, entry_point:selectedEntry, engine_version:INTENTFORGE_ENGINE, compare_candidates:true, trace:false,
          vectors:cases.map(row => ({arguments:row.args,expected:row.expected_return})),
          ...(advanced.input_domain ? {input_domain:advanced.input_domain} : {}),
          ...(requirement?.return_expression ? {return_expression:requirement.return_expression} : {}),
          ...(requirement?.condition ? {condition:requirement.condition} : {}),
        }, controller.signal);
        if (controller.signal.aborted) return;
        setResult({source:code, staticResult, live:verification});
        onVerification(verification);
        const recommended = verification.candidates.find(row => row.id === verification.guided_evidence?.recommended_candidate);
        if (recommended) setSelected(staticResult.candidates.find(row => row.proposed_code === recommended.source)?.id ?? staticResult.candidates[0]?.id ?? null);
      }
    } catch (failure) {
      if (!controller.signal.aborted) setError(failure instanceof Error ? failure.message : "Could not complete intention analysis.");
    } finally {
      if (!controller.signal.aborted) setBusy(false);
    }
  }

  const canApply = !!choice?.compiler_valid && !contradicts && !ambiguous &&
    (!live?.original || (live.guided_evidence?.review === "REVIEW_MATCHING_REPAIR" &&
      live.guided_evidence.recommended_candidate === liveChoice?.id && verified));
  return <>
    <form className="p14-form" ref={form} aria-label="Expected behavior" onSubmit={(event) => void inspect(event)} onChange={() => invalidate()}>
      <section className="paper-card expectation-card">
        <h2><Target /> Expected Behavior</h2>
        {fullC ? <p>Full C supports compiler analysis. Intention analysis is available for Mini-C.</p> : <>
          <label>Function {functions.length > 0 ?
            <select value={selectedEntry} onChange={e => {
              const name = e.target.value;
              const count = functions.find(fn => fn.name === name)?.parameters.length ?? 0;
              setEntry(name); setRows(old => old.map(row => ({...row,args:Array.from({length:count},(_,i) => row.args[i] ?? "")})));
            }}>{entry && !signature && <option disabled value={entry}>{entry} (choose a current function)</option>}
              {functions.map(fn => <option key={fn.name}>{fn.name}</option>)}</select>
            : <input maxLength={80} value={entry} onChange={e => setEntry(e.target.value)} placeholder="Analyze Code to discover functions" />}</label>
          <label>Use for analysis<select value={mode} onChange={e => setMode(e.target.value as IntentionMode)}>
            <option value="examples">Input and output examples</option><option value="code_only">Source code only</option>
            <option value="explicit">Explicit expression</option><option value="natural_language">Supported requirement wording</option></select></label>
          {mode === "natural_language" && <label>Requirement description<input name="description" maxLength={400} required placeholder="Return the maximum of left and right" />
            <small>Use a named operation or comparison. Free-form descriptions may be unsupported.</small></label>}
          {mode === "explicit" && <div className="field-pair">
            <label>Return expression<input name="returnExpression" maxLength={160} /></label>
            <label>Condition<input name="condition" maxLength={160} /></label>
          </div>}
        </>}
      </section>
      {!fullC && <>
        {mode !== "code_only" && <section className="paper-card">
          <div className="card-heading"><h2><Flask /> Test Cases ({rows.length})</h2>
            <button type="button" disabled={rows.length >= 12} onClick={() => {invalidate(); setRows([...rows,{args:Array(argumentCount).fill(""),expected:""}]);}}><Plus /> Add case</button></div>
          {rows.length ? <div className="table-scroll"><table className="case-table">
            <thead><tr><th scope="col">#</th>{Array.from({length:argumentCount},(_,i) =>
              <th key={i} scope="col">{signature?.parameters[i]?.name ?? `Input ${i+1}`}</th>)}
              <th scope="col">Expected output</th><th scope="col"><span className="sr-only">Remove</span></th></tr></thead>
            <tbody>{rows.map((row,index) => <tr key={index}><th scope="row">{index+1}</th>
              {Array.from({length:argumentCount},(_,i) => <td key={i}><input
                aria-label={`Case ${index+1} ${signature?.parameters[i]?.name ?? `input ${i+1}`}`}
                value={row.args[i] ?? ""} onChange={e => changeRow(index,i,e.target.value)} /></td>)}
              <td><input aria-label={`Case ${index+1} expected output`} value={row.expected} onChange={e => changeRow(index,"expected",e.target.value)} /></td>
              <td><button type="button" title={`Remove case ${index+1}`} aria-label={`Remove case ${index+1}`}
                onClick={() => {invalidate(); setRows(rows.filter((_,i) => i !== index));}}><Trash size={16} /></button></td>
            </tr>)}</tbody>
          </table></div> : <p>Add the inputs and expected return value for each case.</p>}
          <details className="p14-advanced"><summary>Advanced Settings</summary>
            {!signature && <label>Number of inputs<input type="number" min="0" max="16" value={argumentCount}
              onChange={e => {
                const count = Math.min(16, Math.max(0, Number(e.target.value)));
                if (!rows.length) setRows([{args:Array(count).fill(""),expected:""}]);
                else setRows(rows.map(row => ({...row,args:Array.from({length:count},(_,i) => row.args[i] ?? "")})));
              }} /></label>}
            <small>Verification accepts integer and Boolean arguments. Use scalar parameters to fill local arrays.</small>
            <label>Input domain (JSON)<textarea name="domain" maxLength={2000} placeholder='[{"minimum":0,"maximum":20},null]' /></label>
            <label>Partial inputs (JSON)<textarea name="partial" maxLength={2000} placeholder="[[2,3]]" /></label>
            {mode === "explicit" && <div className="field-pair"><label>Return location<input name="returnLocation" type="number" min={1} max={3000} /></label>
              <label>Condition location<input name="conditionLocation" type="number" min={1} max={3000} /></label></div>}
            <label>Test cases (JSON)<textarea maxLength={4000} value={raw} onChange={e => setRaw(e.target.value)} spellCheck={false} /></label>
            <div className="action-row"><button type="button" onClick={importCases}>Import JSON</button>
              <button type="button" onClick={() => {try { setRaw(JSON.stringify(parseCases(rows,signature),null,2)); setError(null); }
                catch (failure) {setError((failure as Error).message);}}}>Export JSON</button></div>
          </details>
        </section>}
        <div className="action-row"><button type="submit" className="primary" disabled={busy}>{busy ? "Analyzing…" : "Analyze Intention"}</button>
          <span className="engine-label">IntentForge Engine</span></div>
      </>}
    </form>
    <section className="paper-card intent-result" aria-label="Intent and repair result">
      <div className="card-heading"><h2><span className="heading-icon"><Target size={23} /></span> Intent &amp; Repair Result</h2>
        {choice && <span className={`p14-badge ${verified ? "success" : contradicts ? "error" : "unverified"}`}>
          {verified ? "Verified on supplied tests" : contradicts ? "Contradicted" : "Unverified"}</span>}</div>
      {error && <p className="p14-error" role="alert">{error}</p>}
      {busy && <p role="status">{current ? "Testing behavior in the private worker…" : "Analyzing intention…"}</p>}
      {!current && !busy && <p>{stale ? "Source changed since analysis. Analyze again to review a repair." :
        "Analyze your source and expectations to see whether a repair is supported."}</p>}
      {current && <>
        <h3>{!current.staticResult.compiler_valid ? "Compiler errors prevent analysis" : ambiguous ? "Multiple compatible repairs" :
          choice ? "Suggested Fixes" : statusText[current.staticResult.requirement_status ?? ""] ??
          statusText[current.staticResult.finding] ?? statusText[current.staticResult.decision] ?? "No supported repair found"}</h3>
        {!current.staticResult.compiler_valid && <ul>{current.staticResult.diagnostics.map((row,i) => <li key={i}>{row.message}</li>)}</ul>}
        {live?.guided_evidence?.confirmed_fault && <p className="p14-error">Confirmed behavioral mismatch on supplied tests.</p>}
        {live?.guided_evidence?.original === "ORIGINAL_MATCHES_SUPPLIED_TESTS" && <p>Original matches supplied tests.</p>}
        {ambiguous && <p>More evidence may be needed to distinguish the alternatives.</p>}
        {current.staticResult.candidates.length > 1 && <label>Candidate<select value={selected ?? ""} onChange={e => {
          setSelected(e.target.value);setApproval(false);setKept(false);
        }}>{current.staticResult.candidates.map((candidate,i) => <option key={candidate.id} value={candidate.id}>
          {i+1}. {candidateName(candidate.category)}</option>)}</select></label>}
        {choice && !kept && <>
          <RepairDiff candidate={choice} source={current.source} />
          <h3>Why this repair?</h3>
          <p>{choice.compiler_valid ? "Compiler-valid candidate." : "Compiler diagnostics remain."} {choice.evidence_basis === "supplied_examples" && "Static analysis used your supplied examples."}</p>
          <ul className="repair-evidence">{choice.evidence.slice(0,3).map((point,i) => <li key={i}>{point.detail}</li>)}</ul>
          <div className="action-row"><button type="button" className="primary" disabled={busy} onClick={() => setApproval(true)}>
            <Check /> Review Repair</button>
            <button type="button" onClick={() => {setApproval(false);setKept(true);}}>Keep Original</button></div>
          <details className="p14-advanced"><summary>View Technical Evidence</summary>
            <p>{choice.hypothesis}</p><p>{choice.safety.reason}</p>
            <ul>{[...choice.evidence,...(choice.counter_evidence ?? [])].map((point,i) => <li key={i}>{point.detail}</li>)}</ul>
            <a href="#research">Explore Analysis</a>
          </details>
          {approval && <dialog className="product-dialog repair-dialog" ref={(node) => {if (node && !node.open) node.showModal();}}
            onClose={() => setApproval(false)} aria-label="Review source change">
            <h2>Review source change</h2><p>{verified ? "The edited source matches the supplied runtime tests." :
              "This candidate has no passing runtime verification. Review every changed location before applying."}</p>
            <RepairDiff candidate={choice} source={current.source} />
            {!canApply && <p>Application is unavailable for this outcome. Add an expectation that distinguishes the candidate or edit the source manually.</p>}
            <details><summary>Complete proposed source</summary><pre>{choice.proposed_code}</pre></details>
            <form className="action-row" method="dialog"><button type="submit">Cancel</button>
              <button type="button" className="primary" disabled={!canApply || current.source !== code}
                onClick={() => {setApproval(false);onApply(current.source,choice.proposed_code);}}>Apply Reviewed Repair</button></form>
          </dialog>}
        </>}
        {kept && <p role="status">Original source retained. <button type="button" onClick={() => setKept(false)}>Show suggestion</button></p>}
        <section className="verification-summary"><h3>Test Behavior</h3>
          {execution?.status !== "available" ? <p><WarningCircle size={17} /> Restricted worker unavailable. Runtime tests were unverified.</p>
            : !live ? <p>{busy ? "Waiting for runtime observations." : "Add supplied test cases to run behavioral verification."}</p>
              : <><p>{live.availability.detail}</p>{live.guided_evidence?.recommended_candidate === liveChoice?.id && liveChoice &&
                <p>Runtime evidence supports reviewing this repair.</p>}
                {live.original && <details><summary>Verification Results</summary><Evidence label="Original" result={live.original} />
                  {liveChoice && <Evidence label="Suggested repair" result={liveChoice.behavior} />}</details>}</>}
        </section>
      </>}
    </section>
  </>;
}
