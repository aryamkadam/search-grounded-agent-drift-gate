import type {
  Capture,
  DriftComparison,
  SearchSurface,
} from "./types";

export const surfaceLabels: Record<SearchSurface, string> = {
  organic: "Organic",
  news: "News",
  ai_overview: "AI Overview",
  shopping: "Shopping",
  local: "Local",
  knowledge: "Knowledge",
};

export const captures: Capture[] = [
  {
    id: "cap_001",
    query: "best AI coding tools for developers in 2026",
    timestamp: "2026-10-05T18:42:00+05:30",
    location: "Pune, India",
    language: "en-IN",
    device: "desktop",
    surfaces: ["organic", "ai_overview", "news"],
    evidenceCount: 14,
    agentRunId: "run_001",
  },

  {
    id: "cap_002",
    query: "OpenAI latest model",
    timestamp: "2026-10-05T18:26:00+05:30",
    location: "Pune, India",
    language: "en-IN",
    device: "desktop",
    surfaces: ["organic", "ai_overview"],
    evidenceCount: 9,
    agentRunId: "run_002",
  },

  {
    id: "cap_003",
    query: "best laptops for developers",
    timestamp: "2026-10-05T17:18:00+05:30",
    location: "Mumbai, India",
    language: "en-IN",
    device: "desktop",
    surfaces: ["organic", "shopping", "news"],
    evidenceCount: 18,
    agentRunId: "run_003",
  },

  {
    id: "cap_004",
    query: "latest cybersecurity vulnerabilities",
    timestamp: "2026-10-05T16:45:00+05:30",
    location: "Pune, India",
    language: "en-IN",
    device: "desktop",
    surfaces: ["organic", "news"],
    evidenceCount: 12,
    agentRunId: "run_004",
  },

  {
    id: "cap_005",
    query: "best Java frameworks for backend development",
    timestamp: "2026-10-05T15:32:00+05:30",
    location: "Pune, India",
    language: "en-IN",
    device: "desktop",
    surfaces: ["organic", "ai_overview"],
    evidenceCount: 11,
    agentRunId: "run_005",
  },

  {
    id: "cap_006",
    query: "Google Gemini latest features",
    timestamp: "2026-10-05T14:21:00+05:30",
    location: "Mumbai, India",
    language: "en-IN",
    device: "mobile",
    surfaces: ["organic", "ai_overview", "news"],
    evidenceCount: 16,
    agentRunId: "run_006",
  },

  {
    id: "cap_007",
    query: "AI agent frameworks 2026",
    timestamp: "2026-10-05T13:08:00+05:30",
    location: "Pune, India",
    language: "en-IN",
    device: "desktop",
    surfaces: ["organic", "ai_overview", "news"],
    evidenceCount: 15,
    agentRunId: "run_007",
  },

  {
    id: "cap_008",
    query: "best developer productivity tools",
    timestamp: "2026-10-05T11:52:00+05:30",
    location: "Pune, India",
    language: "en-IN",
    device: "desktop",
    surfaces: ["organic", "shopping"],
    evidenceCount: 10,
    agentRunId: "run_008",
  },
];

/*
 * Demo comparison used later by the Compare page.
 * This is intentionally static for now.
 * The backend will eventually provide real comparison data.
 */
export const demoComparison: DriftComparison = {
  id: "cmp_001",

  oldCaptureId: "cap_001",

  newCaptureId: "cap_002",

  query: "best AI coding tools for developers in 2026",

  severity: "high",

  gate: "FAIL",

  surfaceChanges: [
    {
      surface: "ai_overview",
      added: 1,
      removed: 1,
      modified: 1,
    },

    {
      surface: "organic",
      added: 2,
      removed: 1,
      modified: 2,
    },

    {
      surface: "news",
      added: 1,
      removed: 2,
      modified: 0,
    },
  ],

  evidenceChanges: [
    {
      id: "ev_001",
      surface: "ai_overview",
      title: "Example AI Overview source",
      url: "https://example.com/source-a",
      snippet: "Example evidence from the previous search run.",
      rank: 1,
      source: "example.com",
      changed: true,
      changeType: "removed",
    },

    {
      id: "ev_002",
      surface: "ai_overview",
      title: "New AI Overview source",
      url: "https://example.com/source-b",
      snippet: "Example evidence appearing in the new search run.",
      rank: 1,
      source: "example.com",
      changed: true,
      changeType: "added",
    },
  ],

  claimImpacts: [
    {
      id: "claim_001",

      claim:
        "Tool X is currently among the top recommended coding assistants.",

      status: "weakened",

      oldEvidence: ["ev_001"],

      newEvidence: [],
    },

    {
      id: "claim_002",

      claim:
        "Tool Y supports repository-level code generation.",

      status: "supported",

      oldEvidence: ["ev_004"],

      newEvidence: ["ev_007"],
    },
  ],

  summary:
    "Search evidence changed enough to affect 1 of 2 agent claims.",
};