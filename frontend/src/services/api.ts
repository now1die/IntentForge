import type {
  AnalysisResponse,
  AstResponse,
  CorrectionOptionsResponse,
  CorrectionResponse,
  Health,
  IntentionMode,
  IntentionRequirement,
  IntentionResponse,
  Phase8Inputs,
  SymbolsResponse,
  TokensResponse,
  ValidateCorrectionResponse,
} from "../types/compiler";

export const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ||
  "/api"
).replace(/\/$/, "");

export class ApiError extends Error {
  constructor(message: string, public status = 0) {
    super(message);
  }
}

async function request<T>(path: string, payload?: unknown, signal?: AbortSignal): Promise<T> {
  const hasBody = payload !== undefined;
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      method: hasBody ? "POST" : "GET",
      headers: hasBody ? { "Content-Type": "application/json" } : undefined,
      body: hasBody ? JSON.stringify(payload) : undefined,
      signal: signal
        ? AbortSignal.any([signal, AbortSignal.timeout(90000)])
        : AbortSignal.timeout(90000),
    });
    if (!response.ok) {
      const message =
        (path === "/v1/intention-analysis" || path === "/v1/behavioral-verification") && [413, 422].includes(response.status)
          ? await intentionInputError(response)
          : response.status === 503
          ? "The correction model is unavailable. Train the backend model, then try again."
          : response.status === 422
            ? "The backend could not accept this source. Use at most 100,000 characters."
            : "The backend could not complete this request. Please try again.";
      throw new ApiError(message, response.status);
    }
    return (await response.json()) as T;
  } catch (error) {
    if (error instanceof ApiError || signal?.aborted) throw error;
    throw new ApiError("Could not reach the compiler. Check that the backend is running, then retry.");
  }
}

async function intentionInputError(response: Response): Promise<string> {
  const payload: { detail?: string | { msg: string }[] } = await response.json();
  if (typeof payload.detail === "string") return payload.detail;
  return payload.detail?.[0]?.msg ?? "Check the requirement fields and source length.";
}

export const analyzeIntention = (code: string, requirement: IntentionRequirement | null, mode: IntentionMode, signal: AbortSignal, engineVersion: 2 | 3 | 4 | 5 | 55 | 6 | 65 | 7 | 75 | 8 | 85 | 9 | 95 | 10 | 105 | 11 | 115 = 2, inputs?: Phase8Inputs) =>
  request<IntentionResponse>("/v1/intention-analysis", { code, requirement, mode, engine_version: engineVersion, ...inputs }, signal);

export const checkHealth = (signal?: AbortSignal) => request<Health>("/health", undefined, signal);
export const analyzeCode = (code: string, signal?: AbortSignal) => request<AnalysisResponse>("/analyze", { code }, signal);
export const correctCode = (code: string, signal?: AbortSignal) => request<CorrectionResponse>("/correct", { code }, signal);
export const getCorrectionOptions = (code: string, signal?: AbortSignal) => request<CorrectionOptionsResponse>("/correction-options", { code }, signal);
export const validateCorrection = (originalCode: string, correctedCode: string, signal?: AbortSignal) =>
  request<ValidateCorrectionResponse>("/validate-correction", { original_code: originalCode, corrected_code: correctedCode }, signal);
export const getTokens = (code: string, signal?: AbortSignal) => request<TokensResponse>("/tokens", { code }, signal);
export const getAst = (code: string, signal?: AbortSignal) => request<AstResponse>("/ast", { code }, signal);
export const getSymbols = (code: string, signal?: AbortSignal) => request<SymbolsResponse>("/symbols", { code }, signal);

export const clangCapability = (signal: AbortSignal) =>
  request<import("../types/clang").ClangCapability>("/v1/c-analysis/capability", undefined, signal);
export const analyzeC = (code: string, standard: string, signal: AbortSignal) =>
  request<import("../types/clang").ClangAnalysis>("/v1/c-analysis", { code, standard }, signal);

export const inspectCompilerEvidence = (code: string, language: "mini-c" | "c", standard: string, signal: AbortSignal) =>
  request<import("../types/evidence").SharedEvidenceReport>("/v1/compiler-evidence",
    language === "c" ? { code, language, standard } : { code, language }, signal);

export const getExecutionCapability = (signal: AbortSignal) =>
  request<import("../components/InteractiveBehavior").ExecutionCapability>("/v1/behavioral-verification/capability", undefined, signal);
export const verifyBehavior = (payload: unknown, signal: AbortSignal) =>
  request<import("../components/InteractiveBehavior").VerificationResponse>("/v1/behavioral-verification", payload, signal);
