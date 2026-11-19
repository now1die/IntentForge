import { useEffect, useRef, useState } from "react";
import { inspectCompilerEvidence } from "../services/api";
import type { ClangSpan } from "../types/clang";
import type { SharedEvidenceReport } from "../types/evidence";

type Props = {
  code: string;
  language: "mini-c" | "c";
  standard: string;
  discovering: boolean;
  focus: (span: ClangSpan) => void;
};

export function SharedEvidence({ code, language, standard, discovering, focus }: Props) {
  const request = useRef<AbortController | null>(null);
  const [result, setResult] = useState<SharedEvidenceReport | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => () => request.current?.abort(), []);

  async function inspect() {
    request.current?.abort();
    const controller = new AbortController();
    request.current = controller;
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const response = await inspectCompilerEvidence(code, language, standard, controller.signal);
      if (!controller.signal.aborted) setResult(response);
    } catch (failure) {
      if (!controller.signal.aborted) setError(failure instanceof Error ? failure.message : "Evidence was unavailable.");
    } finally {
      if (!controller.signal.aborted) setBusy(false);
    }
  }

  return <section className="inspector" aria-label="Shared compiler evidence">
    <div className="inspector-body shared-evidence">
      <button type="button" className="primary" disabled={busy || discovering} onClick={() => void inspect()}>
        {busy ? "Inspecting source…" : "Inspect compiler evidence"}
      </button>
      {error && <p role="alert">{error}</p>}
      {result && <>
        <h3>{result.provider === "clang" ? "Clang" : "Mini-C"} evidence</h3>
        {result.detail && <p>{result.detail}</p>}
        {result.units.map((unit) => <div key={unit.entry}>
          <p>{unit.entry} · AST {unit.ast} · {unit.nodes.length} nodes · {unit.nodes.filter((node) => node.declaration).length} declarations · {unit.scopes.length} scopes · {unit.control_flow_nodes.length} control-flow nodes</p>
          <ul>{unit.diagnostics.map((diagnostic, index) => <li key={index}>
            {diagnostic.message}{" "}
            {diagnostic.span && diagnostic.span.file === (language === "c" ? "main.c" : "main.mc") &&
              <button type="button" onClick={() => diagnostic.span && focus(diagnostic.span)}>
                {diagnostic.span.start.line}:{diagnostic.span.start.column}
              </button>}
          </li>)}</ul>
        </div>)}
      </>}
    </div>
  </section>;
}
