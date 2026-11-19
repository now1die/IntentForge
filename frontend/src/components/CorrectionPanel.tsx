import { useMemo, useState } from "react";
import { CheckCircle, WarningCircle, PencilSimple, MagicWand } from "@phosphor-icons/react";
import { CodeEditor } from "./CodeEditor";
import type { CorrectionHistory, CorrectionOption, CorrectionOptionsResponse, CorrectionResponse } from "../types/compiler";
import { candidateEdits, describeCandidate, describeEdit, unresolvedReason } from "../utils/correctionPresentation";

export function canApplyCorrection(result: CorrectionResponse) {
  return result.original_code !== result.corrected_code && result.corrections_applied > 0 && result.fully_syntactically_valid;
}

function EditList({ history }: { history: CorrectionHistory }) {
  const candidate = history.selected_candidate;
  if (!candidate) return null;
  return (
    <ol className="atomic-edits">
      {candidateEdits(candidate).map((edit, index) => (
        <li key={`${edit.offset}-${index}`}>
          <span>{describeEdit(edit)}</span>
          <small>Ln {edit.span.start.line}:{edit.span.start.column}</small>
        </li>
      ))}
    </ol>
  );
}

function OptionCard({ option, selected, onSelect }: { option: CorrectionOption; selected: boolean; onSelect: () => void }) {
  return (
    <button className={`suggestion-card ${selected ? "selected" : ""}`} onClick={onSelect} type="button">
      <span className="suggestion-radio" aria-hidden="true">{selected ? "●" : "○"}</span>
      <span className="suggestion-main">
        <strong>{option.label}{option.fully_valid ? " · compiler valid" : " · syntax valid"}</strong>
        <code>{option.corrected_code}</code>
        <small>{option.reason}</small>
      </span>
      <span className="suggestion-confidence">{(option.confidence * 100).toFixed(0)}%</span>
    </button>
  );
}

export function CorrectionPanel({
  result,
  options,
  onApplyCode,
  onValidateCustom,
}: {
  result: CorrectionResponse | null;
  options: CorrectionOptionsResponse | null;
  onApplyCode: (code: string, label: string) => void;
  onValidateCustom: (code: string) => Promise<{ valid: boolean; message: string }>;
}) {
  const [selected, setSelected] = useState<string | null>(null);
  const [customOpen, setCustomOpen] = useState(false);
  const [customCode, setCustomCode] = useState("");
  const [customMessage, setCustomMessage] = useState<string | null>(null);
  const selectedOption = useMemo(() => options?.options.find((item) => item.id === selected) ?? null, [options, selected]);

  if (!result && !options) {
    return <div className="empty"><strong>Choose how to correct your code</strong><span>Run Correct to generate ranked alternatives you can review before applying.</span></div>;
  }

  const firstHistory = result?.history[0];
  const disabledReason = result ? unresolvedReason(result.stop_reason, firstHistory) : null;
  const legacyCanApply = result ? canApplyCorrection(result) : false;

  async function validateCustom() {
    if (!customCode.trim()) return;
    const validation = await onValidateCustom(customCode);
    setCustomMessage(validation.message);
    if (validation.valid) onApplyCode(customCode, "Custom correction");
  }

  return (
    <div className="correction-panel">
      <div className="review-header">
        <div>
          <strong>Choose your correction</strong>
          <span>{options?.message ?? (legacyCanApply ? "A validated correction is available." : disabledReason ?? "Review the available result.")}</span>
        </div>
        {selectedOption && (
          <button className="primary" onClick={() => onApplyCode(selectedOption.corrected_code, selectedOption.label)}>
            <CheckCircle /> Apply Selected
          </button>
        )}
      </div>

      {options?.diagnostic && (
        <section className="suggestion-section" aria-label="AI correction suggestions">
          <div className="suggestion-heading">
            <div><span className="section-label">AI SUGGESTIONS</span><strong>{options.diagnostic.message}</strong></div>
            {options.prediction && <code>{options.prediction.label} · {(options.prediction.confidence * 100).toFixed(1)}%</code>}
          </div>
          {options.ollama && (
            <div className="ollama-review-status">
              <span>{options.ollama.available ? "✓ Local Ollama verified the candidates" : "Local Ollama unavailable — compiler validation used"}</span>
              {options.ollama.model && <small>{options.ollama.model}</small>}
            </div>
          )}
          <div className="suggestion-list">
            {options.options.map((option) => <OptionCard key={option.id} option={option} selected={selected === option.id} onSelect={() => setSelected(option.id)} />)}
          </div>
          {options.options.length === 0 && <div className="empty compact"><strong>No compiler-validated alternatives</strong><span>Try Edit Original or write a custom correction below.</span></div>}
        </section>
      )}

      <section className="custom-section">
        <div className="custom-heading">
          <div><strong><PencilSimple /> Custom correction</strong><span>Write the version you want. The compiler validates it before applying.</span></div>
          <button onClick={() => { setCustomOpen(!customOpen); if (!customCode) setCustomCode(result?.original_code ?? options?.original_code ?? ""); }} type="button">{customOpen ? "Close" : "Edit manually"}</button>
        </div>
        {customOpen && (
          <div className="custom-editor-wrap">
            <textarea value={customCode} onChange={(event) => { setCustomCode(event.target.value); setCustomMessage(null); }} spellCheck={false} aria-label="Custom correction editor" />
            <div className="custom-actions">
              <span className={customMessage?.startsWith("Correction is") ? "accent" : "muted"}>{customMessage ?? ""}</span>
              <button className="primary" onClick={() => void validateCustom()}><MagicWand /> Validate & Apply</button>
            </div>
          </div>
        )}
      </section>

      <section className="original-edit-section">
        <button onClick={() => { setCustomOpen(true); setCustomCode(result?.original_code ?? options?.original_code ?? ""); setCustomMessage(null); }} type="button"><PencilSimple /> Edit Original Code</button>
        <span>Nothing changes in the main editor until you choose an option or apply your own correction.</span>
      </section>

      {selectedOption && (
        <section className="selected-preview">
          <div className="suggestion-heading"><strong>Selected preview</strong><span>{selectedOption.reason}</span></div>
          <div className="review-code compact-review"><CodeEditor code={selectedOption.corrected_code} readOnly /></div>
        </section>
      )}

      {result && result.history.length > 0 && (
        <section className="history" aria-label="Correction history">
          <div className="history-heading">Correction history</div>
          {result.history.map((history) => {
            const validated = history.status === "APPLIED" && history.validation?.relevant_valid === true;
            return <article key={history.sequence}>
              <div className="history-step">Correction {history.sequence}</div>
              <div className="history-title"><strong>{describeCandidate(history.selected_candidate)}</strong><span className={validated ? "accent" : "warning"}>{validated ? <><CheckCircle /> Validated</> : <><WarningCircle /> Unresolved</>}</span></div>
              <EditList history={history} />
            </article>;
          })}
        </section>
      )}
    </div>
  );
}
