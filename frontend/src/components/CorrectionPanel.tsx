import { useState } from "react";
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
        {option.safety?.requires_review && <small>{option.safety.reason}</small>}
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
  const [selected, setSelected] = useState<CorrectionOption | null>(null);
  const [customOpen, setCustomOpen] = useState(false);
  const [customCode, setCustomCode] = useState("");
  const [customMessage, setCustomMessage] = useState<string | null>(null);
  const selectedOption = selected && options?.options.includes(selected) ? selected : null;

  if (!result && !options) {
    return <div className="empty"><strong>Choose how to correct your code</strong><span>Run Correct to generate ranked alternatives you can review before applying.</span></div>;
  }

  const firstHistory = result?.history[0];
  const disabledReason = result ? unresolvedReason(result.stop_reason, firstHistory) : null;
  const validatedSource = result && canApplyCorrection(result) ? result.corrected_code : null;
  const reviewedProposal = result?.history.at(-1);
  const reviewSource = reviewedProposal?.status === "SUGGESTED" && reviewedProposal.validation?.valid
    ? reviewedProposal.validation.corrected_source
    : null;
  const availableCount = result?.corrections_applied || options?.options.length || (reviewSource ? 1 : 0);
  const reviewLabel = availableCount
    ? `${availableCount} validated correction${availableCount === 1 ? "" : "s"} ready`
    : "No validated correction is ready";

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
          <strong>{reviewLabel}</strong>
          <span>{availableCount ? options?.message : disabledReason ?? options?.message}</span>
        </div>
        {selectedOption ? (
          <button className="primary" onClick={() => onApplyCode(selectedOption.corrected_code, selectedOption.label)}>
            <CheckCircle /> Apply Selected
          </button>
        ) : result && (
          <button className="primary" type="button" disabled={!validatedSource}
            onClick={() => validatedSource && onApplyCode(validatedSource, "Correction")}>
            <CheckCircle /> Apply Corrected Code
          </button>
        )}
      </div>

      {options && (options.diagnostic || options.options.length > 0) && (
        <section className="suggestion-section" aria-label="AI correction suggestions">
          <div className="suggestion-heading">
            <div><span className="section-label">AI SUGGESTIONS</span><strong>{options.diagnostic?.message ?? "Review the proposed changes"}</strong></div>
            {options.prediction && <code>{options.prediction.label} · {(options.prediction.confidence * 100).toFixed(1)}%</code>}
          </div>
          {options.ollama && (
            <div className="ollama-review-status">
              <span>{options.ollama.error ? options.ollama.error : options.ollama.approved_ids?.length ? "Local Ollama reviewed the candidates" : options.ollama.attempted ? "Local Ollama ran" : "Compiler validation used"}</span>
              {options.ollama.model && <small>{options.ollama.model}</small>}
            </div>
          )}
          <div className="suggestion-list">
            {options.options.map((option) => <OptionCard key={option.id} option={option} selected={selectedOption === option} onSelect={() => setSelected(option)} />)}
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

      {reviewSource && !options?.options.length && (
        <section className="selected-preview">
          <div className="suggestion-heading">
            <strong>Proposed correction</strong>
            <span>{reviewedProposal?.safety?.reason}</span>
          </div>
          <div className="review-code compact-review"><CodeEditor code={reviewSource} readOnly /></div>
          <button className="primary" type="button" onClick={() => onApplyCode(reviewSource, "Reviewed proposal")}>
            <CheckCircle /> Apply Reviewed Proposal
          </button>
        </section>
      )}

      {result && result.history.length > 0 && (
        <section className="history" aria-label="Correction history">
          <div className="history-heading">Correction history</div>
          {result.history.map((history) => {
            const validated = history.validation?.relevant_valid === true;
            const reviewRequired = history.safety?.requires_review ?? false;
            return <article key={history.sequence}>
              <div className="history-step">Correction {history.sequence}</div>
              <div className="history-title"><strong>{describeCandidate(history.selected_candidate)}</strong><span className={validated ? "accent" : "warning"}>{validated && !reviewRequired ? <><CheckCircle /> Validated</> : <><WarningCircle /> {reviewRequired ? "Review required" : "Unresolved"}</>}</span></div>
              <EditList history={history} />
              {history.after_snippet && history.before_snippet !== history.after_snippet && (
                <div className="inline-diff" aria-label="Proposed edit">
                  <div className="diff-pair">
                    <code className="diff-before"><span aria-hidden="true">−</span>{history.before_snippet}</code>
                    <code className="diff-after"><span aria-hidden="true">+</span>{history.after_snippet}</code>
                  </div>
                </div>
              )}
              {reviewRequired && <small>{history.safety?.reason}</small>}
            </article>;
          })}
        </section>
      )}
    </div>
  );
}
