import { Phase12Demo } from "./components/Phase12Demo";
import { InteractiveBehavior } from "./components/InteractiveBehavior";
import { BehaviorDemo } from "./components/BehaviorDemo";
import { ClangEvidence } from "./components/ClangEvidence";
import type { ClangAnalysis, ClangCapability, ClangSpan } from "./types/clang";
import { SharedEvidence } from "./components/SharedEvidence";
import { IntentionPanel } from "./components/IntentionPanel";
import { useEffect, useRef, useState } from "react";
import { FileCode, X, ArrowRight } from "@phosphor-icons/react";
import { Toolbar } from "./components/Toolbar";
import { CodeEditor, type EditorHandle } from "./components/CodeEditor";
import { AnalysisPanel } from "./components/AnalysisPanel";
import { DiagnosticList } from "./components/DiagnosticList";
import { InspectorTabs, tabs, type Tab } from "./components/InspectorTabs";
import { ASTView } from "./components/ASTView";
import { SymbolTableView } from "./components/SymbolTableView";
import { TokenTable } from "./components/TokenTable";
import {
  CorrectionPanel,
} from "./components/CorrectionPanel";
import { DEFAULT_CODE } from "./constants/examples";
import {
  analyzeCode,
  analyzeC,
  clangCapability,
  checkHealth,
  correctCode,
  getCorrectionOptions,
  getTokens,
  validateCorrection,
} from "./services/api";
import type {
  AnalysisResponse,
  CorrectionOptionsResponse,
  CorrectionResponse,
  Diagnostic,
  Health,
  Token,
} from "./types/compiler";

export default function App() {
  const [language, setLanguage] = useState<"mini" | "clang">("mini");
  const [standard, setStandard] = useState("c17");
  const [clang, setClang] = useState<ClangCapability | null>(null);
  const [cResult, setCResult] = useState<ClangAnalysis | null>(null);
  const fullC = language === "clang";
  const [code, setCode] = useState(DEFAULT_CODE);
  const [health, setHealth] = useState<Health | null>(null);
  const [checking, setChecking] = useState(true);
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
  const [correction, setCorrection] = useState<CorrectionResponse | null>(null);
  const [correctionOptions, setCorrectionOptions] = useState<CorrectionOptionsResponse | null>(null);
  const [tokens, setTokens] = useState<Token[] | null>(null);
  const [active, setActive] = useState<Tab>("Diagnostics");
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState("Ready to analyze");
  const [selected, setSelected] = useState<Diagnostic | null>(null);
  const editor = useRef<EditorHandle | null>(null);
  const current = useRef(DEFAULT_CODE);
  const task = useRef<AbortController | null>(null);
  const tokenTask = useRef<AbortController | null>(null);
  const healthTask = useRef<AbortController | null>(null);
  const [tokenLoading, setTokenLoading] = useState(false);
  const diagnostics = analysis
    ? [
        ...analysis.lexical.errors,
        ...analysis.syntax.errors,
        ...analysis.semantic.errors,
      ]
    : [];
  async function refreshHealth() {
    healthTask.current?.abort();
    const controller = new AbortController();
    healthTask.current = controller;
    setChecking(true);
    try {
      const result = await checkHealth(controller.signal);
      if (!controller.signal.aborted) setHealth(result);
    } catch {
      if (!controller.signal.aborted) setHealth(null);
    } finally {
      if (!controller.signal.aborted) setChecking(false);
    }
  }
  useEffect(() => {
    void refreshHealth();
    return () => {
      task.current?.abort();
      tokenTask.current?.abort();
      healthTask.current?.abort();
    };
  }, []);
  useEffect(() => {
    if (!fullC) return;
    const controller = new AbortController();
    setClang(null);
    clangCapability(controller.signal).then((result) => {
      if (!controller.signal.aborted) setClang(result);
    }).catch(() => {
      if (!controller.signal.aborted) setClang({ status: "unavailable", version: null, standards: [],
        features: [], unsupported: [], detail: "Clang capability discovery could not reach the backend." });
    });
    return () => controller.abort();
  }, [fullC]);

  function changeSource(value: string) {
    task.current?.abort();
    tokenTask.current?.abort();
    setBusy(null);
    setTokenLoading(false);
    current.current = value;
    setCode(value);
    setAnalysis(null);
    setCResult(null);
    setCorrection(null);
    setCorrectionOptions(null);
    setTokens(null);
    setSelected(null);
    setError(null);
    setNotice("Source changed. Analyze to refresh results.");
  }
  async function loadTokens() {
    tokenTask.current?.abort();
    const controller = new AbortController();
    tokenTask.current = controller;
    setTokenLoading(true);
    try {
      const result = await getTokens(current.current, controller.signal);
      if (!controller.signal.aborted) setTokens(result.tokens);
    } catch (err) {
      if (!controller.signal.aborted)
        setError(err instanceof Error ? err.message : "Token request failed.");
    } finally {
      if (!controller.signal.aborted) setTokenLoading(false);
    }
  }
  function selectTab(tab: Tab) {
    setActive(tab);
    if (tab === "Tokens" && !tokens) void loadTokens();
  }
  async function run(mode: "analyze" | "correct", source = current.current) {
    task.current?.abort();
    const controller = new AbortController();
    task.current = controller;
    setBusy(mode);
    setError(null);
    setAnalysis(null);
    setSelected(null);
    setCorrection(null);
    setCResult(null);
    try {
      if (fullC) {
        if (mode !== "analyze") return;
        const result = await analyzeC(source, standard, controller.signal);
        if (controller.signal.aborted) return;
        setCResult(result);
        setNotice(result.status === "ok" ? "Clang analysis complete." : result.detail ?? "Clang reported diagnostics.");
      } else if (mode === "analyze") {
        const result = await analyzeCode(source, controller.signal);
        if (controller.signal.aborted) return;
        setAnalysis(result);
        setSelected(
          [
            ...result.lexical.errors,
            ...result.syntax.errors,
            ...result.semantic.errors,
          ][0] ?? null,
        );
        setNotice(
          result.success
            ? "Analysis complete. All checks passed."
            : "Analysis complete. Diagnostics available.",
        );
        setActive("Diagnostics");
      } else {
        // Analyze the original buffer for correctly positioned markers. Correction diagnostics
        // refer to a different source version and are shown only in the review editor.
        const [result, original, optionResult] = await Promise.all([
          correctCode(source, controller.signal),
          analyzeCode(source, controller.signal),
          getCorrectionOptions(source, controller.signal),
        ]);
        if (controller.signal.aborted) return;
        setCorrection(result);
        setCorrectionOptions(optionResult);
        setAnalysis(original);
        setSelected(result.history[0]?.original_error ?? null);
        setActive("Corrections");
        setNotice(
          result.corrected_code !== source || optionResult.options.length > 0 ||
          result.history.some((entry) => entry.status === "SUGGESTED" && entry.validation?.valid)
            ? "Correction ready for review. Source has not changed."
            : result.success
              ? "Source passes syntax checks. See analysis for semantic diagnostics."
              : "No correction applied. Review the unresolved result.",
        );
      }
    } catch (err) {
      if (!controller.signal.aborted) {
        setError(err instanceof Error ? err.message : "Request failed.");
        setNotice("Request did not complete.");
      }
    } finally {
      if (!controller.signal.aborted) setBusy(null);
    }
  }
  function focusClang(span: ClangSpan) {
    editor.current?.revealLineInCenter(span.start.line);
    editor.current?.setPosition({ lineNumber: span.start.line, column: span.start.column });
    editor.current?.focus();
  }

  function focusDiagnostic(d: Diagnostic) {
    setSelected(d);
    editor.current?.revealLineInCenter(d.line);
    editor.current?.setPosition({ lineNumber: d.line, column: d.column });
    editor.current?.focus();
  }
  function applyCode(value: string, label: string) {
    if (!value || current.current !== (correction?.original_code ?? current.current)) return;
    changeSource(value);
    setNotice(`${label} applied. Validating source…`);
    void run("analyze", value);
  }

  function applyIntention(original: string, proposed: string) {
    if (current.current !== original) return;
    changeSource(proposed);
    setNotice("Reviewed intention repair applied. Validating source…");
    void run("analyze", proposed);
  }

  async function validateCustomCode(value: string) {
    const response = await validateCorrection(current.current, value);
    return { valid: response.valid, message: response.message };
  }

  return (
    <main className="app-shell">
      <Toolbar
        health={health}
        analysis={analysis}
        checking={checking}
        busy={busy}
        fullC={fullC}
        analyzeUnavailable={fullC && clang?.status !== "available"}
        onAnalyze={() => void run("analyze")}
        onCorrect={() => void run("correct")}
        onReset={() => {
          changeSource(fullC ? "int main(void) { return 0; }\n" : DEFAULT_CODE);
          setAnalysis(null);
          setCorrection(null);
          setCorrectionOptions(null);
          setTokens(null);
          setSelected(null);
          setNotice("Default example restored.");
        }}
        onRetry={() => void refreshHealth()}
      />
      <div className="workspace-heading">
        <div>
          <span className="section-label">WORKSPACE</span>
          <label className="language-picker">Language <select value={language} onChange={(event) => {
            changeSource(current.current);
            setLanguage(event.target.value === "clang" ? "clang" : "mini");
            setActive("Diagnostics");
            setNotice("Language changed. Analyze to refresh results.");
          }}>
            <option value="mini">Mini-C</option><option value="clang">C / Clang</option>
          </select></label>
        </div>
      </div>
      {error && (
        <div role="alert" className="error-banner">
          <span>{error}</span>
          <button onClick={() => setError(null)} aria-label="Dismiss error">
            <X />
          </button>
        </div>
      )}
      <div className="workbench">
        <section className="editor-panel" aria-label="Source workspace">
          <div className="editor-heading">
            <span className="file-tab">
              <FileCode size={17} />
              {fullC ? "main.c" : "main.mc"}
            </span>
            <span>
              {fullC ? "C / Clang" : "Mini-C"} <ArrowRight size={12} /> backend analysis
            </span>
          </div>
          <div
            className="source-editor"
            onKeyDown={(event) => event.stopPropagation()}
          >
            <CodeEditor
              code={code}
              onChange={changeSource}
              diagnostics={diagnostics}
              fullC={fullC}
              clangDiagnostics={cResult?.units[0]?.diagnostics}
              onReady={(instance) => {
                editor.current = instance;
              }}
            />
          </div>
          <div className="editor-footer">
            <span>{code.split("\n").length} lines</span>
            <span>UTF-8</span>
            <span>Spaces: 4</span>
            <span className="editor-mode">Editing only</span>
          </div>
        </section>
        {fullC ? <section className="editor-panel clang-overview" aria-label="Clang capability">
          <h2>C / Clang</h2>
          <p>{clang?.detail ?? "Checking Clang availability…"}</p>
          {clang?.version && <p>Clang {clang.version} · Syntax and type analysis</p>}
          <label className="language-picker">C standard <select value={standard} onChange={(event) => {
            changeSource(current.current);
            setStandard(event.target.value);
          }}>
            {["c99", "c11", "c17", "c23"].map((name) => <option key={name}>{name}</option>)}
          </select></label>
          <p>Includes resolve only to files supplied to the API. This editor analyzes one file.</p>
          <p>Intelligent repair, linking and execution are unavailable in C mode.</p>
        </section> : <AnalysisPanel
          analysis={analysis}
          correction={correction}
          selected={selected}
        />}
      </div>
      {fullC ? <ClangEvidence analysis={cResult} focus={focusClang} /> : <section className="inspector">
        <InspectorTabs
          active={active}
          onChange={selectTab}
          count={diagnostics.length}
        />
        <div
          className="inspector-body"
          id="inspector-content"
          role="tabpanel"
          aria-labelledby={`tab-${tabs.indexOf(active)}`}
          tabIndex={0}
        >
          {busy ? (
            <div className="empty loading">
              <strong>
                {busy === "correct"
                  ? "Requesting validated corrections…"
                  : "Analyzing source…"}
              </strong>
              <span>Waiting for the compiler backend</span>
            </div>
          ) : active === "Tokens" ? (
            tokenLoading ? (
              <div className="empty">Loading backend tokens…</div>
            ) : (
              <TokenTable tokens={tokens} />
            )
          ) : active === "AST" ? (
            <ASTView ast={analysis?.ast ?? null} />
          ) : active === "Symbol Table" ? (
            <SymbolTableView symbols={analysis?.symbols ?? null} />
          ) : active === "Intention" ? (
            <IntentionPanel code={code} onApply={applyIntention} />
          ) : active === "Corrections" ? (
            <CorrectionPanel result={correction} options={correctionOptions} onApplyCode={applyCode} onValidateCustom={validateCustomCode} />
          ) : (
            <DiagnosticList
              diagnostics={diagnostics}
              onSelect={focusDiagnostic}
              analyzed={!!analysis}
            />
          )}
        </div>
      </section>}
      <SharedEvidence key={JSON.stringify([language, standard, code])} code={code}
        language={fullC ? "c" : "mini-c"} standard={standard} discovering={fullC && clang === null} focus={focusClang} />
      {!fullC && <>
        <Phase12Demo onLoad={changeSource} />
        <InteractiveBehavior code={code} functions={Array.isArray(analysis?.ast?.functions)
          ? analysis.ast.functions.filter((fn) => fn.return_type === "int" || fn.return_type === "bool").map((fn) => fn.name)
          : []} onNavigate={(span) => {
          editor.current?.revealLineInCenter(span.start.line);
          editor.current?.setPosition({ lineNumber: span.start.line, column: span.start.column });
          editor.current?.focus();
        }} onApply={applyIntention} />
        <BehaviorDemo code={code} onLoad={changeSource} />
      </>}
      <footer className="statusbar">
        <span role="status" aria-live="polite">
          {notice}
        </span>
        <span>{fullC ? "C / Clang" : "Mini-C language"} / Compiler Workbench</span>
      </footer>
    </main>
  );
}
