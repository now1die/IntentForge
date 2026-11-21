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
  evidence_basis?: "static" | "supplied_examples" | "supplied_specification";
  hypothesis_origin?: "phase65" | "phase75" | "phase8" | "phase85" | "phase9" | "earlier_engine";
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
  counter_evidence?: IntentionEvidence[];
  edits: { span: Diagnostic["span"]; original: string; proposed: string }[];
}

export type InputDomain = ({ minimum: number; maximum: number } | null)[];
export interface Phase8Inputs {
  input_domain?: InputDomain;
  partial_inputs?: (number | boolean)[][];
}

type AnalysisSpan = Diagnostic["span"];

export type BranchWitness = {
  guards: { site: number; span: AnalysisSpan; predicate: string; supplied_coverage: Record<string, number> }[];
  returns: {
    site: number; span: AnalysisSpan; expression_span: AnalysisSpan; examples: number;
    conditions: { site: number; outcome: string }[];
    definitions: { name: string; site: number; span: AnalysisSpan }[];
  }[];
};

export type LoopWitness = {
  guard_span: AnalysisSpan;
  update_span: AnalysisSpan;
  seed_span: AnalysisSpan;
  accumulator_update_span: AnalysisSpan;
  predicate_span: AnalysisSpan | null;
  return_span: AnalysisSpan;
  step: number;
  point_limit: number;
  iterations: number[];
  matches: number[];
};

export type Phase85Analysis = {
  status: string;
  mode?: "branches" | "coordinated" | "loops";
  examples?: number;
  original_mismatches?: number;
  compatible_candidates: number;
  branch?: BranchWitness;
  loop?: LoopWitness;
  witnesses?: {
    edits: { span: AnalysisSpan; replacement: string }[];
    branch?: BranchWitness;
    loop?: LoopWitness;
  }[];
};

export type Phase9Analysis = Pick<Phase85Analysis, "status" | "branch" | "examples" | "compatible_candidates"> & {
  loop_summary?: {
    normalized_relation: string;
    direction: string;
    variable_step: boolean;
    step_expression: string;
    guard_span: AnalysisSpan;
    update_span: AnalysisSpan;
    point_limit: number;
    carriers: { name: string; span: AnalysisSpan }[];
    steps?: (number | null)[];
    iterations?: number[];
    exit_states?: number[][];
  };
  modeled_faults?: { example: number; code: string; operator: string; operands: number[]; span: AnalysisSpan }[];
};

export interface Phase8Analysis {
  phase9?: Phase9Analysis | null;
  phase85?: Phase85Analysis | null;
  specification: {
    function: string | null;
    parameters: { name: string; type: string }[];
    return_type: string | null;
    status: string;
    source_snapshot: string;
    provenance: string;
    trusted_examples: number;
    partial_inputs: number;
    input_domain: InputDomain | null;
    assumptions: string[];
  };
  constraints: {
    status: string;
    trials: number;
    compatible_edits: number;
    helper_functions: string[];
    minimum_changed_tokens?: number | null;
  };
}

export type IntentionMode = "code_only" | "natural_language" | "explicit" | "examples";

type ProgressArgument = { offset: number } | { step_name: string; sign: number } | Record<string, never>;

export interface Phase65Analysis {
  progress?: Record<string, { complete: false; reason: string } | {
    complete: true;
    parameter: string;
    position: number;
    comparison: string;
    threshold: number;
    direction: number;
    calls: { span: Diagnostic["span"]; argument: ProgressArgument; feeds_return: boolean }[];
  }>;
  paths: Record<string, {
    complete: boolean;
    unresolved_conditions: number[];
    returns: {
      site: number;
      span: Diagnostic["span"];
      feasibility: "modeled" | "excluded" | "unknown";
      paths: {
        facts: { binding: string; name: string; min: number; max: number; excluded: number[] }[];
        definitions: { binding: string; name: string; span: Diagnostic["span"] }[];
        possible_upstream_definitions: { binding: string; name: string; span: Diagnostic["span"] }[];
        dependencies_complete: boolean;
      }[];
    }[];
    recursive_returns: { site: number; self_calls: number; expression: string }[];
    other_return_sites: number[];
    base_guards: { condition: string; outcome: boolean; span: Diagnostic["span"] }[];
  }>;
  interprocedural: Record<string, {
    complete: boolean;
    effects_unknown: boolean;
    scalar_helper?: { parameter_inputs: number[]; depth: number; identity_parameter: number | null };
    return_parameter_inputs: number[];
    call_sites: {
      target: string | null;
      span: Diagnostic["span"];
      feeds_return: boolean;
      self_recursive: boolean;
      arguments: {
        position: number;
        parameter: string | null;
        affine: { binding: string; name: string; offset: number } | null;
      }[];
      callee_result_inputs: number[] | null;
    }[];
  }>;
  withheld: { category: string; reason: string; span: Diagnostic["span"] }[];
}

export interface IntentionResponse {
  guided_evidence?: "POSSIBLE_REPAIR" | "INSUFFICIENT_SPECIFICATION";
  recommendation?: "ABSTAIN" | "REVIEW_WITH_EVIDENCE" | null;
  requirement_status?: string | null;
  program_analysis?: {
    phase65?: Phase65Analysis;
    phase8?: Phase8Analysis;
    phase85?: Phase85Analysis;
    phase9?: Phase9Analysis;
    status: "AVAILABLE" | "ANALYSIS_LIMITED" | "INCOMPLETE_COMPILER_EVIDENCE";
    functions: {
      name: string;
      parameters: { name: string; type: string }[];
      return_type: string;
      calls: string[];
      recursion: "DIRECT" | "MUTUAL" | "DIRECT_AND_MUTUAL" | "NONE";
      blocks: number;
      reachable_blocks: number;
      possible_missing_return: boolean;
      complete: boolean;
      conditions: { span: Diagnostic["span"]; normalized: string[] | null; kind: string }[];
      returns: { span: Diagnostic["span"]; definitions: { name: string; site: number; span: Diagnostic["span"] }[] }[];
      effects: string[];
    }[];
  };
  structural_scan?: {
    withheld?: { category: string; evidence: IntentionEvidence[]; counter_evidence: IntentionEvidence }[];
    status: "HEURISTIC_SCAN" | "SCAN_LIMITED" | "INCOMPLETE_COMPILER_EVIDENCE";
    findings: { category: string; assumption: string; evidence: IntentionEvidence[] }[];
  };
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
