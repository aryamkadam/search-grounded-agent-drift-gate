export type SearchSurface =
  | "organic"
  | "news"
  | "ai_overview"
  | "shopping"
  | "local"
  | "knowledge";

export type DriftSeverity = "none" | "low" | "medium" | "high";

export type GateStatus = "PASS" | "FAIL" | "WARN";

export interface EvidenceItem {
  id: string;
  surface: SearchSurface;
  title: string;
  url: string;
  snippet?: string;
  rank?: number;
  source?: string;
  changed?: boolean;
  changeType?: "added" | "removed" | "modified" | "moved";
}

export interface Capture {
  id: string;
  query: string;
  timestamp: string;
  location?: string;
  language?: string;
  device?: string;
  surfaces: SearchSurface[];
  evidenceCount?: number;
  agentRunId?: string;
}

export interface ClaimImpact {
  id: string;
  claim: string;
  status: "supported" | "weakened" | "unsupported" | "unchanged";
  oldEvidence: string[];
  newEvidence: string[];
}

export interface DriftComparison {
  id: string;
  oldCaptureId: string;
  newCaptureId: string;
  query: string;
  severity: DriftSeverity;
  gate: GateStatus;

  surfaceChanges: {
    surface: SearchSurface;
    added: number;
    removed: number;
    modified: number;
  }[];

  evidenceChanges: EvidenceItem[];
  claimImpacts: ClaimImpact[];

  summary: string;
}