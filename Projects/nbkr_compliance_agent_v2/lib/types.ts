// lib/types.ts

export type LangCode = "ru" | "en" | "ky";

export interface Citation {
  law_id: string;
  ref: string;           // e.g., "П.21(8)"
  title?: string;
  snippet?: string;
  full_text?: string;
  score?: number;        // 0..1-ish from RAG
}

export interface SuggestedFix {
  ru: string;
  en: string;
  ky: string;
}

export interface ContractLocator {
  page_guess?: number;   // 1-based
  char_index?: number;   // position in OCR text
}

export interface FlagItem {
  title: string;
  summary?: string;
  offending_text?: string;
  severity: "low" | "medium" | "high";
  law_ref?: string;              // e.g., "П.21(7)"
  violation_code?: string;       // stable code like "penalty_cap_10"
  citations: Citation[];
  contract_locator?: ContractLocator;
  suggested_fix?: SuggestedFix;
  confidence?: number;           // 0..1 (rounded)
}

export interface FlagsBlock {
  items: FlagItem[];
}

export interface EvidenceItem extends Citation {}

export interface AgentTraceStep {
  step: string;                  // "ocr" | "policy" | "rag" | ...
  tool: string;
  args?: Record<string, unknown>;
  observation?: Record<string, unknown>;
}

export interface RunSummary {
  used: Record<string, boolean>;
  elapsed_ms: number;
}

export interface AnalyzeResponse {
  goal: string;
  entities: { names: string[]; roles: string[] };
  flags: FlagsBlock;
  evidence: EvidenceItem[];
  translations?: { original_lang?: string; [k: string]: unknown };
  agent_trace?: AgentTraceStep[];
  run_summary?: RunSummary;
}
