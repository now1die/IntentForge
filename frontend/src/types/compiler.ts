export interface SourceLocation {
  line: number;
  column: number;
  offset: number;
}
export interface SourceSpan {
  start: SourceLocation;
  end: SourceLocation;
}
export type Phase = "lexical" | "syntax" | "semantic";
export type JsonValue =
  | string
  | number
  | boolean
  | null
  | JsonValue[]
  | { [key: string]: JsonValue };
export interface CandidateEdit {
  action: "INSERT" | "DELETE" | "REPLACE";
  token_type: string | null;
  token_lexeme: string | null;
  offset: number;
  span: SourceSpan;
  text: string;
}
export interface Candidate {
  id: string;
  action: "INSERT" | "DELETE" | "REPLACE" | "COMPOUND";
  token_type: string | null;
  token_lexeme: string | null;
  offset: number;
  span: SourceSpan;
  text: string;
  reason: string;
  grammar_context: string;
  diagnostic_id: string;
  origin: string;
  parser_validated: boolean | null;
  score: number | null;
  edits: CandidateEdit[];
}
export interface Diagnostic {
  phase: Phase;
  code: string;
  message: string;
  line: number;
  column: number;
  offset: number;
  span: SourceSpan;
  severity?: string;
  diagnostic_id?: string;
  unexpected_token?: string | null;
  unexpected_lexeme?: string | null;
  expected_tokens?: string[];
  grammar_context?: string | null;
  correction_candidates?: Candidate[];
}
export interface Token {
  type: string;
  lexeme: string;
  value: JsonValue;
  line: number;
  column: number;
  offset: number;
  span: SourceSpan;
}
export interface AstNode {
  node: string;
  span: SourceSpan;
  [key: string]: unknown;
}
export interface SymbolType {
  kind: string;
  base: string;
  display: string;
  parameter_types: SymbolType[];
}
export interface Symbol {
  id: string;
  name: string;
  kind: string;
  type: SymbolType;
  scope_id: string;
  line: number;
  column: number;
  offset: number;
  span: SourceSpan;
  array_size: number | null;
}
export interface Scope {
  id: string;
  name: string;
  kind: string;
  parent_id: string | null;
  symbols: Symbol[];
  children: Scope[];
}
export interface SymbolTable {
  root: Scope;
}
export interface Prediction {
  label: string;
  confidence: number;
  probabilities: Record<string, number>;
}
export interface Validation {
  candidate: Candidate;
  corrected_source: string;
  valid: boolean;
  relevant_valid: boolean;
  target_resolved: boolean;
  remaining_syntax_errors: number;
  remaining_lexical_errors: number;
}
export interface GroqFallback {
  attempted: boolean;
  available: boolean;
  model: string;
  accepted: boolean;
  error: string | null;
  suggestion: {
    action: CandidateEdit["action"];
    replacement_text: string;
    target_start: number;
    target_end: number;
    reason: string;
  } | null;
  candidate?: Candidate | null;
  validation: Validation | null;
}
export interface GroqAmbiguitySelection {
  attempted: boolean;
  available: boolean;
  model: string;
  selected_candidate_id: string | null;
  confidence: number | null;
  reason: string | null;
  selected_candidate: Candidate | null;
  validation: Validation | null;
  accepted: boolean;
  error: string | null;
}
export interface RankedCandidate {
  candidate: Candidate;
  compatibility_score: number;
  matched_class: string | null;
  matched_classes: string[];
  predicted_class_match: boolean;
  grammar_context_match: boolean;
  parser_validated: boolean | null;
  original_index: number;
}
export interface CandidateAttempt {
  rank: number;
  ranked_candidate: RankedCandidate;
  validation: Validation | null;
  accepted: boolean;
  rejection_reason: string | null;
}
export interface RepairSafety {
  category: "LOW_RISK_STRUCTURAL" | "AMBIGUOUS" | "POTENTIALLY_BEHAVIOR_CHANGING" | "UNVERIFIED";
  reason: string;
  requires_review: boolean;
}

export interface CorrectionHistory {
  sequence: number;
  status: "APPLIED" | "SUGGESTED" | "UNRESOLVED";
  applied: boolean;
  diagnostic_id: string;
  original_error: Diagnostic;
  prediction: Prediction;
  selected_candidate: Candidate | null;
  candidate_rank: number | null;
  candidate_probability: number | null;
  before_snippet: string;
  after_snippet: string | null;
  source_offset: number;
  validation: Validation | null;
  attempts?: CandidateAttempt[];
  safety?: RepairSafety;
  reason: string | null;
  llm_fallback: GroqFallback | null;
  ambiguity_selection: GroqAmbiguitySelection | null;
}
export interface AnalysisResponse {
  success: boolean;
  token_count: number;
  lexical: { success: boolean; errors: Diagnostic[] };
  syntax: { success: boolean; errors: Diagnostic[] };
  semantic: { ran: boolean; success: boolean | null; errors: Diagnostic[] };
  ast: AstNode | null;
  symbols: SymbolTable | null;
}

export interface CorrectionOption {
  id: string;
  label: string;
  corrected_code: string;
  score: number;
  confidence: number;
  predicted_class: string;
  matched_class: string | null;
  reason: string;
  grammar_context: string;
  candidate: Candidate | null;
  validation: Validation | null;
  semantic_errors: number | null;
  fully_valid: boolean;
  safety?: RepairSafety;
  origin: string;
}
export interface CorrectionOptionsResponse {
  success: boolean;
  original_code: string;
  diagnostic: Diagnostic | null;
  prediction: Prediction | null;
  options: CorrectionOption[];
  message: string;
  ollama?: {
    available?: boolean;
    attempted?: boolean;
    model?: string;
    mode?: string;
    approved_ids?: string[];
    reason?: string;
    error?: string | null;
  };
}
export interface ValidateCorrectionResponse {
  valid: boolean;
  syntax_valid: boolean;
  lexical_errors: number;
  syntax_errors: number;
  semantic_errors: number;
  corrected_code: string;
  message: string;
}

export interface CorrectionResponse {
  success: boolean;
  original_code: string;
  corrected_code: string;
  fully_syntactically_valid: boolean;
  corrections_applied: number;
  history: CorrectionHistory[];
  predictions: Prediction[];
  confidence_values: number[];
  groq_fallback_used: boolean;
  ollama_fallback_used: boolean;
  ambiguity_selection_used: boolean;
  needs_llm_fallback: boolean;
  unresolved_syntax_diagnostics: Diagnostic[];
  semantic_diagnostics: Diagnostic[];
  stop_reason: string;
}
export interface TokensResponse {
  success: boolean;
  token_count: number;
  tokens: Token[];
  lexical_errors: Diagnostic[];
}
export interface AstResponse {
  success: boolean;
  ast: AstNode | null;
  lexical_errors: Diagnostic[];
  syntax_errors: Diagnostic[];
}
export interface SymbolsResponse {
  success: boolean;
  ran: boolean;
  symbols: SymbolTable | null;
  lexical_errors: Diagnostic[];
  syntax_errors: Diagnostic[];
  semantic_errors: Diagnostic[];
}
export interface Health {
  status: string;
  ml_model_loaded: boolean;
  groq_configured: boolean;
  ollama_configured: boolean;
}

export interface IntentionRequirement {
  function?: string;
  description?: string;
  return_expression?: string;
  condition?: string;
  return_ordinal?: number;
  condition_ordinal?: number;
  examples?: { args: (number | boolean)[]; expected_return: number | boolean }[];
}

export interface IntentionEvidence {
  kind: string;
  detail: string;
  span: Diagnostic["span"] | null;
}

export interface IntentionCandidate {
  tier?: "SPECIFICATION_SUPPORTED" | "COMPILER_CONFIRMED_ISSUE" | "STRONG_CONTEXT" | "WEAK_CONTEXT";
  id: string;
  category: string;
  proposed_code: string;
  compiler_valid: boolean;
  remaining_diagnostics: number;
  behavioral_status: string;
  relative_score: number | null;
  safety: { category: string; reason: string; requires_review: boolean };
  hypothesis: string;
  evidence: IntentionEvidence[];
  edits: { span: Diagnostic["span"]; original: string; proposed: string }[];
}

export type IntentionMode = "code_only" | "natural_language" | "explicit";

export interface IntentionResponse {
  recommendation?: "ABSTAIN" | "REVIEW_WITH_EVIDENCE" | null;
  requirement_status?: string | null;
  finding: string;
  decision: string;
  ranking: string;
  compiler_valid: boolean;
  behavioral_status: string;
  diagnostics: Diagnostic[];
  evidence: IntentionEvidence[];
  notes: string[];
  attempts: number;
  candidates: IntentionCandidate[];
}
