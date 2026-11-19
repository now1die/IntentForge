export interface ClangPosition {
  line: number;
  column: number;
  byte_offset: number;
}

export interface ClangSpan {
  file: string;
  start: ClangPosition;
  end: ClangPosition;
  origin: "physical" | "expansion" | "spelling";
}

export interface ClangDiagnostic {
  severity: "note" | "warning" | "error" | "fatal";
  message: string;
  category: string | null;
  code: string | null;
  phase: string;
  span: ClangSpan | null;
  related: ClangSpan[];
  notes: ClangDiagnostic[];
}

export interface ClangNode {
  id: number;
  parent: number | null;
  name: string | null;
  kind: string;
  span: ClangSpan | null;
  spelling_span: ClangSpan | null;
  scope: number | null;
  type: string | null;
  canonical_type: string | null;
  declaration: boolean;
  reference: number | null;
  parameter_types: string[] | null;
  result_type: string | null;
  variadic: boolean | null;
}

export interface ClangCapability {
  status: "available" | "unavailable";
  detail: string;
  version: string | null;
  standards: string[];
  features: string[];
  unsupported: string[];
}

export interface ClangAnalysis {
  status: "ok" | "syntax_errors" | "semantic_errors" | "compiler_errors" | "unavailable" |
    "unsupported_configuration" | "request_limit" | "timeout";
  detail: string | null;
  standard: string;
  units: { entry: string; ast: "available" | "partial" | "unavailable"; diagnostics: ClangDiagnostic[]; nodes: ClangNode[] }[];
}
