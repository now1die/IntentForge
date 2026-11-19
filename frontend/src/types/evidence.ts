import type { ClangDiagnostic } from "./clang";

export interface SharedEvidenceReport {
  schema_version: 1;
  language: "mini-c" | "c";
  provider: "ply-mini-c" | "clang";
  detail: string | null;
  status: string;
  units: {
    entry: string;
    ast: string;
    diagnostics: ClangDiagnostic[];
    nodes: { declaration: boolean }[];
    scopes: { id: number }[];
    control_flow_nodes: number[];
  }[];
}
