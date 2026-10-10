
"use client";

import { useCallback, useEffect, useState } from "react";
import {
  AlertCircle,
  ArrowRight,
  Calendar,
  CheckCircle2,
  ExternalLink,
  GitCompareArrows,
  LoaderCircle,
  ShieldCheck,
  ShieldX,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";

interface CompareWorkspaceProps {
  initialOldId?: string;
  initialNewId?: string;
}

type JsonRecord = Record<string, unknown>;

interface CaptureOption {
  capture_id: string;
  query: string;
  captured_at?: string;
  country?: string;
  device?: string;
}

interface EvidenceOption {
  key: string;
  surface: string;
  identity_key: string;
  title: string;
  url?: string;
  snippet?: string;
}

function isRecord(value: unknown): value is JsonRecord {
  return (
    typeof value === "object" &&
    value !== null &&
    !Array.isArray(value)
  );
}

function getString(value: unknown): string | undefined {
  return typeof value === "string" && value.trim()
    ? value
    : undefined;
}

function getNumber(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value)
    ? value
    : 0;
}

function getArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function formatDate(value?: string): string {
  if (!value) return "Timestamp unavailable";

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;

  return new Intl.DateTimeFormat("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function mapCapture(value: unknown): CaptureOption | null {
  if (!isRecord(value)) return null;

  const context = isRecord(value.search_context)
    ? value.search_context
    : {};

  const captureId = getString(value.capture_id);
  if (!captureId) return null;

  return {
    capture_id: captureId,
    query:
      getString(context.query) ??
      getString(value.query) ??
      "Unknown query",
    captured_at:
      getString(value.captured_at) ??
      getString(value.timestamp),
    country:
      getString(context.country) ??
      getString(value.country),
    device:
      getString(context.device) ??
      getString(value.device),
  };
}

function getEvidenceOptions(value: unknown): EvidenceOption[] {
  if (!isRecord(value)) return [];

  const normalized = isRecord(value.normalized_evidence)
    ? value.normalized_evidence
    : {};

  const collections = [
    "organic_results",
    "news_results",
    "shopping_results",
    "local_results",
    "knowledge_graph",
    "perspectives",
    "related_questions",
    "inline_images",
    "inline_videos",
  ];

  const options: EvidenceOption[] = [];
  const seen = new Set<string>();

  function addItems(surface: string, value: unknown) {
    for (const item of getArray(value)) {
      if (!isRecord(item)) continue;

      const identityKey = getString(item.identity_key);
      if (!identityKey) continue;

      const key = `${surface}:${identityKey}`;
      if (seen.has(key)) continue;
      seen.add(key);

      options.push({
        key,
        surface,
        identity_key: identityKey,
        title:
          getString(item.title) ??
          getString(item.question) ??
          getString(item.name) ??
          identityKey,
        url: getString(item.url) ?? getString(item.link),
        snippet:
          getString(item.snippet) ??
          getString(item.description) ??
          getString(item.text),
      });
    }
  }

  for (const surface of collections) {
    addItems(surface, normalized[surface]);
  }

  const aiOverview = normalized.ai_overview;

  if (isRecord(aiOverview)) {
    addItems("ai_overview", aiOverview.references);
  } else {
    addItems("ai_overview", aiOverview);
  }

  const additional = normalized.additional_surfaces;

  if (isRecord(additional)) {
    for (const [surface, items] of Object.entries(additional)) {
      addItems(surface, items);
    }
  }

  return options;
}

function getDetail(value: unknown): string {
  if (!isRecord(value)) return "No details supplied.";

  return (
    getString(value.detail) ??
    getString(value.message) ??
    "The backend request failed."
  );
}

function surfaceLabel(value: string): string {
  const labels: Record<string, string> = {
    organic_results: "Organic",
    news_results: "News",
    shopping_results: "Shopping",
    local_results: "Local",
    knowledge_graph: "Knowledge graph",
    ai_overview: "AI Overview",
    related_questions: "Related questions",
    inline_images: "Images",
    inline_videos: "Videos",
  };

  return (
    labels[value] ??
    value.replace(/_/g, " ").replace(/\b\w/g, (letter) =>
      letter.toUpperCase()
    )
  );
}

export function CompareWorkspace({
  initialOldId,
  initialNewId,
}: CompareWorkspaceProps) {
  const [captures, setCaptures] = useState<CaptureOption[]>([]);
  const [oldId, setOldId] = useState(initialOldId ?? "");
  const [newId, setNewId] = useState(initialNewId ?? "");

  const [listLoading, setListLoading] = useState(true);
  const [listError, setListError] = useState<string | null>(null);

  const [evidenceOptions, setEvidenceOptions] = useState<EvidenceOption[]>([]);
  const [selectedEvidenceKey, setSelectedEvidenceKey] = useState("");
  const [evidenceLoading, setEvidenceLoading] = useState(false);
  const [evidenceError, setEvidenceError] = useState<string | null>(null);
  const [claimText, setClaimText] = useState("");

  const [evaluating, setEvaluating] = useState(false);
  const [evaluationError, setEvaluationError] = useState<string | null>(null);
  const [evaluationPayload, setEvaluationPayload] =
    useState<JsonRecord | null>(null);

  const [history, setHistory] = useState<JsonRecord | null>(null);
  const [historyError, setHistoryError] = useState<string | null>(null);

  const baseUrl = process.env.NEXT_PUBLIC_API_URL?.replace(/\/+$/, "");

  const loadCaptures = useCallback(async () => {
    if (!baseUrl) {
      setListError("NEXT_PUBLIC_API_URL is missing from frontend/.env.local.");
      setListLoading(false);
      return;
    }

    setListLoading(true);
    setListError(null);

    try {
      const response = await fetch(`${baseUrl}/v1/captures`, {
        cache: "no-store",
      });

      const payload: unknown = await response.json().catch(() => null);

      if (!response.ok) {
        throw new Error(getDetail(payload));
      }

      const rawItems = Array.isArray(payload)
        ? payload
        : isRecord(payload) && Array.isArray(payload.items)
          ? payload.items
          : null;

      if (!rawItems) {
        throw new Error("Unexpected response from GET /v1/captures.");
      }

      const items = rawItems
        .map(mapCapture)
        .filter((item): item is CaptureOption => item !== null);

      setCaptures(items);

      // The API returns newest captures first. Default to older baseline,
      // newer candidate, unless valid IDs were supplied in the URL.
      const baseline = items.some(
        (item) => item.capture_id === initialOldId
      )
        ? initialOldId!
        : items[items.length - 1]?.capture_id ?? "";

      const candidate = items.some(
        (item) =>
          item.capture_id === initialNewId &&
          item.capture_id !== baseline
      )
        ? initialNewId!
        : items.find((item) => item.capture_id !== baseline)?.capture_id ??
          baseline;

      setOldId(baseline);
      setNewId(candidate);
      setEvaluationPayload(null);
      setHistory(null);
    } catch (error) {
      setListError(
        error instanceof Error
          ? error.message
          : "Could not load captures."
      );
    } finally {
      setListLoading(false);
    }
  }, [baseUrl, initialNewId, initialOldId]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadCaptures();
    }, 0);

    return () => window.clearTimeout(timer);
  }, [loadCaptures]);

  const loadBaselineEvidence = useCallback(async () => {
    setEvidenceOptions([]);
    setSelectedEvidenceKey("");
    setEvidenceError(null);

    if (!baseUrl || !oldId) return;

    setEvidenceLoading(true);

    try {
      const response = await fetch(
        `${baseUrl}/v1/captures/${encodeURIComponent(oldId)}`,
        { cache: "no-store" }
      );

      const payload: unknown = await response.json().catch(() => null);

      if (!response.ok) {
        throw new Error(getDetail(payload));
      }

      const options = getEvidenceOptions(payload);
      setEvidenceOptions(options);
      setSelectedEvidenceKey(options[0]?.key ?? "");

      if (options.length === 0) {
        setEvidenceError(
          "No evidence with identity keys was found in the baseline capture. The evaluation needs a resolvable evidence reference."
        );
      }
    } catch (error) {
      setEvidenceError(
        error instanceof Error
          ? error.message
          : "Could not load baseline evidence."
      );
    } finally {
      setEvidenceLoading(false);
    }
  }, [baseUrl, oldId]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadBaselineEvidence();
    }, 0);

    return () => window.clearTimeout(timer);
  }, [loadBaselineEvidence]);

  const baseline = captures.find((item) => item.capture_id === oldId);
  const current = captures.find((item) => item.capture_id === newId);
  const selectedEvidence = evidenceOptions.find(
    (item) => item.key === selectedEvidenceKey
  );

  const sameQuery = Boolean(
    baseline &&
      current &&
      baseline.query.trim().toLowerCase() ===
        current.query.trim().toLowerCase()
  );

  const validation =
    evaluationPayload && isRecord(evaluationPayload.validation)
      ? evaluationPayload.validation
      : null;

  const result =
    evaluationPayload && isRecord(evaluationPayload.result)
      ? evaluationPayload.result
      : null;

  const gate = result && isRecord(result.gate) ? result.gate : null;
  const evidenceDiff =
    result && isRecord(result.evidence_diff)
      ? result.evidence_diff
      : null;

  const surfaceDiffs =
    evidenceDiff && isRecord(evidenceDiff.surface_diffs)
      ? Object.entries(evidenceDiff.surface_diffs).filter(
          (entry): entry is [string, JsonRecord] => isRecord(entry[1])
        )
      : [];

  const evidenceChanges = surfaceDiffs.flatMap(([surface, diff]) =>
    getArray(diff.changes).map((change, index) => ({
      key: `${surface}-${index}`,
      surface,
      change,
    }))
  );

  const claimImpacts = result ? getArray(result.claim_impacts) : [];

  async function runEvaluation() {
    if (!baseUrl) {
      setEvaluationError("NEXT_PUBLIC_API_URL is missing.");
      return;
    }

    if (!baseline || !current || oldId === newId) {
      setEvaluationError("Choose two different stored captures.");
      return;
    }

    if (!sameQuery) {
      setEvaluationError(
        "Select captures with the same search query. The backend will validate all remaining search-context fields."
      );
      return;
    }

    if (!claimText.trim()) {
      setEvaluationError(
        "Enter the exact agent claim you want to evaluate."
      );
      return;
    }

    if (!selectedEvidence) {
      setEvaluationError(
        "Select an evidence item from the baseline capture."
      );
      return;
    }

    setEvaluating(true);
    setEvaluationError(null);
    setEvaluationPayload(null);
    setHistory(null);
    setHistoryError(null);

    try {
      const requestBody = {
        baseline_capture_id: baseline.capture_id,
        current_capture_id: current.capture_id,
        agent_answer: {
          answer_id: `frontend-claim-${baseline.capture_id}-${current.capture_id}`,
          text: claimText.trim(),
          claims: [
            {
              claim_id: "claim-1",
              text: claimText.trim(),
              evidence_refs: [
                {
                  surface: selectedEvidence.surface,
                  identity_key: selectedEvidence.identity_key,
                  relation: "supports",
                },
              ],
              importance: "important",
              confidence: 0.9,
            },
          ],
        },
      };

      const response = await fetch(
        `${baseUrl}/v1/evaluations/persisted`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(requestBody),
        }
      );

      const payload: unknown = await response.json().catch(() => null);

      if (!response.ok) {
        throw new Error(
          `Evaluation request failed (${response.status}): ${getDetail(payload)}`
        );
      }

      if (!isRecord(payload)) {
        throw new Error("The backend returned an invalid evaluation response.");
      }

      setEvaluationPayload(payload);

      const evaluationId = getString(payload.evaluation_id);

      if (evaluationId) {
        try {
          const historyResponse = await fetch(
            `${baseUrl}/v1/evaluations/${encodeURIComponent(evaluationId)}`,
            { cache: "no-store" }
          );

          const historyPayload: unknown = await historyResponse
            .json()
            .catch(() => null);

          if (!historyResponse.ok) {
            throw new Error(getDetail(historyPayload));
          }

          if (isRecord(historyPayload)) {
            setHistory(historyPayload);
          } else {
            setHistoryError(
              "The saved evaluation endpoint returned an invalid response."
            );
          }
        } catch (error) {
          setHistoryError(
            error instanceof Error
              ? `Evaluation ran, but saved history could not be fetched: ${error.message}`
              : "Evaluation ran, but saved history could not be fetched."
          );
        }
      }
    } catch (error) {
      setEvaluationError(
        error instanceof Error
          ? error.message
          : "Could not run the persisted evaluation."
      );
    } finally {
      setEvaluating(false);
    }
  }

  const gateDecision = getString(gate?.decision)?.toLowerCase();
  const gateClass =
    gateDecision === "pass"
      ? "border-emerald-900/60 bg-emerald-950/20 text-emerald-300"
      : gateDecision === "warn"
        ? "border-amber-900/60 bg-amber-950/20 text-amber-300"
        : "border-red-900/60 bg-red-950/20 text-red-300";

  return (
    <div className="space-y-8">
      <section>
        <div className="flex items-center gap-2">
          <GitCompareArrows className="h-4 w-4 text-zinc-500" />
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-zinc-500">
            Evidence comparison
          </p>
        </div>

        <h1 className="mt-3 text-3xl font-semibold tracking-tight text-zinc-100">
          Compare
        </h1>

        <p className="mt-2 max-w-2xl text-sm leading-6 text-zinc-500">
          Evaluate a claim against stored search evidence. The gate and
          evidence changes displayed below come from the backend response.
        </p>
      </section>

      {listError && (
        <Card className="border-red-900/50 bg-[#111113] p-5">
          <div className="flex items-start gap-3">
            <AlertCircle className="mt-0.5 h-5 w-5 text-red-400" />
            <div className="flex-1">
              <p className="text-sm font-medium text-zinc-200">
                Could not load captures
              </p>
              <p className="mt-1 text-sm text-zinc-400">{listError}</p>
              <button
                type="button"
                onClick={() => void loadCaptures()}
                className="mt-3 text-xs text-zinc-300 underline"
              >
                Retry
              </button>
            </div>
          </div>
        </Card>
      )}

      <section className="grid gap-4 lg:grid-cols-[1fr_auto_1fr] lg:items-center">
        <Card className="border-zinc-800 bg-[#111113] p-5">
          <Badge variant="outline" className="border-zinc-800 text-zinc-400">
            BASELINE
          </Badge>

          <label
            htmlFor="baseline-capture"
            className="mb-2 mt-4 block text-xs text-zinc-500"
          >
            Older capture
          </label>

          <select
            id="baseline-capture"
            value={oldId}
            disabled={listLoading || captures.length === 0}
            onChange={(event) => {
              setOldId(event.target.value);
              setEvaluationPayload(null);
              setHistory(null);
            }}
            className="h-11 w-full rounded-md border border-zinc-800 bg-zinc-950 px-3 text-sm text-zinc-200 outline-none focus:border-zinc-600"
          >
            {captures.map((capture) => (
              <option key={capture.capture_id} value={capture.capture_id}>
                {capture.query} — {formatDate(capture.captured_at)}
              </option>
            ))}
          </select>

          {baseline && (
            <div className="mt-4 border-t border-zinc-800 pt-4">
              <p className="break-all font-mono text-[10px] text-zinc-600">
                {baseline.capture_id}
              </p>
              <p className="mt-2 text-sm text-zinc-300">
                {baseline.query}
              </p>
              <p className="mt-2 flex items-center gap-2 text-xs text-zinc-500">
                <Calendar className="h-3 w-3" />
                {formatDate(baseline.captured_at)}
              </p>
            </div>
          )}
        </Card>

        <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-full border border-zinc-800 bg-zinc-950">
          <ArrowRight className="h-4 w-4 text-zinc-500" />
        </div>

        <Card className="border-zinc-800 bg-[#111113] p-5">
          <Badge
            variant="outline"
            className="border-blue-900/60 bg-blue-950/20 text-blue-300"
          >
            CURRENT
          </Badge>

          <label
            htmlFor="current-capture"
            className="mb-2 mt-4 block text-xs text-zinc-500"
          >
            Newer capture
          </label>

          <select
            id="current-capture"
            value={newId}
            disabled={listLoading || captures.length === 0}
            onChange={(event) => {
              setNewId(event.target.value);
              setEvaluationPayload(null);
              setHistory(null);
            }}
            className="h-11 w-full rounded-md border border-zinc-800 bg-zinc-950 px-3 text-sm text-zinc-200 outline-none focus:border-zinc-600"
          >
            {captures.map((capture) => (
              <option key={capture.capture_id} value={capture.capture_id}>
                {capture.query} — {formatDate(capture.captured_at)}
              </option>
            ))}
          </select>

          {current && (
            <div className="mt-4 border-t border-zinc-800 pt-4">
              <p className="break-all font-mono text-[10px] text-zinc-600">
                {current.capture_id}
              </p>
              <p className="mt-2 text-sm text-zinc-300">
                {current.query}
              </p>
              <p className="mt-2 flex items-center gap-2 text-xs text-zinc-500">
                <Calendar className="h-3 w-3" />
                {formatDate(current.captured_at)}
              </p>
            </div>
          )}
        </Card>
      </section>

      {listLoading && (
        <p className="flex items-center gap-2 text-sm text-zinc-500">
          <LoaderCircle className="h-4 w-4 animate-spin" />
          Loading stored captures...
        </p>
      )}

      {!listLoading && captures.length === 0 && !listError && (
        <Card className="border-zinc-800 bg-[#111113] p-6 text-sm text-zinc-400">
          No captures are stored in the backend yet. Create at least two
          captures before running a comparison.
        </Card>
      )}

      {baseline && current && !sameQuery && (
        <div className="rounded-md border border-amber-900/50 bg-amber-950/10 px-4 py-3 text-xs text-amber-300">
          These captures have different queries. Choose captures with the
          same query; the backend will also validate the full search context.
        </div>
      )}

      <Card className="border-zinc-800 bg-[#111113] p-5">
        <div className="flex items-center gap-2">
          <ShieldCheck className="h-4 w-4 text-zinc-400" />
          <h2 className="text-sm font-semibold text-zinc-100">
            Claim and evidence dependency
          </h2>
        </div>

        <p className="mt-2 text-xs leading-5 text-zinc-500">
          Enter the exact claim you want to evaluate. Select an evidence item
          from the baseline capture that the claim depends on. The frontend
          sends this explicit dependency to the backend for validation.
        </p>

        <label
          htmlFor="claim-text"
          className="mb-2 mt-5 block text-xs text-zinc-400"
        >
          Agent claim
        </label>

        <textarea
          id="claim-text"
          value={claimText}
          onChange={(event) => setClaimText(event.target.value)}
          rows={3}
          maxLength={2000}
          placeholder="Paste the exact claim made by your agent..."
          className="w-full resize-y rounded-md border border-zinc-800 bg-zinc-950 p-3 text-sm text-zinc-200 outline-none placeholder:text-zinc-600 focus:border-zinc-600"
        />

        <label
          htmlFor="evidence-reference"
          className="mb-2 mt-4 block text-xs text-zinc-400"
        >
          Baseline evidence reference
        </label>

        <select
          id="evidence-reference"
          value={selectedEvidenceKey}
          disabled={evidenceLoading || evidenceOptions.length === 0}
          onChange={(event) => setSelectedEvidenceKey(event.target.value)}
          className="h-11 w-full rounded-md border border-zinc-800 bg-zinc-950 px-3 text-sm text-zinc-200 outline-none focus:border-zinc-600"
        >
          {evidenceOptions.length === 0 && (
            <option value="">No evidence references available</option>
          )}
          {evidenceOptions.map((item) => (
            <option key={item.key} value={item.key}>
              {surfaceLabel(item.surface)} — {item.title}
            </option>
          ))}
        </select>

        {evidenceLoading && (
          <p className="mt-2 flex items-center gap-2 text-xs text-zinc-500">
            <LoaderCircle className="h-3 w-3 animate-spin" />
            Loading baseline evidence...
          </p>
        )}

        {evidenceError && (
          <p className="mt-2 text-xs text-amber-400">{evidenceError}</p>
        )}

        {selectedEvidence && (
          <div className="mt-3 rounded-md border border-zinc-800 bg-zinc-950/60 p-3">
            <p className="text-xs font-medium text-zinc-200">
              {selectedEvidence.title}
            </p>
            {selectedEvidence.snippet && (
              <p className="mt-2 text-xs leading-5 text-zinc-500">
                {selectedEvidence.snippet}
              </p>
            )}
            <p className="mt-2 break-all font-mono text-[10px] text-zinc-600">
              {selectedEvidence.identity_key}
            </p>
            {selectedEvidence.url && (
              <a
                href={selectedEvidence.url}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-2 inline-flex items-center gap-1 text-xs text-zinc-400 hover:text-zinc-100"
              >
                Open source <ExternalLink className="h-3 w-3" />
              </a>
            )}
          </div>
        )}

        {evaluationError && (
          <div className="mt-4 flex items-start gap-2 rounded-md border border-red-900/50 bg-red-950/10 p-3 text-sm text-red-300">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            {evaluationError}
          </div>
        )}

        <button
          type="button"
          onClick={() => void runEvaluation()}
          disabled={
            evaluating ||
            listLoading ||
            evidenceLoading ||
            !baseline ||
            !current ||
            oldId === newId ||
            !sameQuery ||
            !claimText.trim() ||
            !selectedEvidence
          }
          className="mt-5 inline-flex items-center justify-center gap-2 rounded-md border border-zinc-600 bg-zinc-100 px-4 py-2.5 text-sm font-semibold text-zinc-900 transition hover:bg-white disabled:cursor-not-allowed disabled:opacity-40"
        >
          {evaluating ? (
            <LoaderCircle className="h-4 w-4 animate-spin" />
          ) : (
            <GitCompareArrows className="h-4 w-4" />
          )}
          {evaluating ? "Evaluating..." : "Run persisted evaluation"}
        </button>
      </Card>

      {evaluationPayload && (
        <section className="space-y-5">
          <Card className="overflow-hidden border-zinc-800 bg-zinc-950">
            <div className="border-b border-zinc-800 p-5">
              <p className="text-xs font-medium uppercase tracking-widest text-zinc-500">
                Backend evaluation
              </p>
              <h2 className="mt-2 text-lg font-semibold text-zinc-100">
                {validation?.valid === false
                  ? "Evaluation validation failed"
                  : result
                    ? "Evaluation completed"
                    : "Evaluation returned no result"}
              </h2>
              <p className="mt-2 break-all font-mono text-xs text-zinc-500">
                Evaluation ID: {getString(evaluationPayload.evaluation_id) ?? "Not supplied"}
              </p>
            </div>

            {validation?.valid === false ? (
              <div className="p-5">
                <div className="flex items-center gap-2 text-amber-300">
                  <ShieldX className="h-4 w-4" />
                  <p className="text-sm font-medium">
                    The backend rejected the claim/evidence validation.
                  </p>
                </div>

                <p className="mt-3 text-xs leading-5 text-zinc-400">
                  No drift gate decision is shown because the backend returned
                  no evaluation result.
                </p>

                {getArray(validation.unresolved_claim_links).length > 0 && (
                  <details className="mt-4">
                    <summary className="cursor-pointer text-xs text-zinc-300">
                      Unresolved claim links
                    </summary>
                    <pre className="mt-2 overflow-auto whitespace-pre-wrap break-words rounded-md bg-zinc-900 p-3 text-[11px] text-zinc-400">
                      {JSON.stringify(validation.unresolved_claim_links, null, 2)}
                    </pre>
                  </details>
                )}

                {getArray(validation.incompatible_search_context).length > 0 && (
                  <details className="mt-4">
                    <summary className="cursor-pointer text-xs text-zinc-300">
                      Incompatible search context
                    </summary>
                    <pre className="mt-2 overflow-auto whitespace-pre-wrap break-words rounded-md bg-zinc-900 p-3 text-[11px] text-zinc-400">
                      {JSON.stringify(validation.incompatible_search_context, null, 2)}
                    </pre>
                  </details>
                )}
              </div>
            ) : result && gate ? (
              <div className="p-5">
                <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex items-start gap-3">
                    {gateDecision === "pass" ? (
                      <CheckCircle2 className="mt-1 h-6 w-6 text-emerald-400" />
                    ) : (
                      <AlertCircle className="mt-1 h-6 w-6 text-amber-400" />
                    )}
                    <div>
                      <p className="text-lg font-semibold text-zinc-100">
                        Drift gate: {getString(gate.decision)?.toUpperCase() ?? "UNKNOWN"}
                      </p>
                      <p className="mt-1 text-sm text-zinc-400">
                        Severity: {getString(gate.severity) ?? "unknown"}
                      </p>
                    </div>
                  </div>

                  <Badge variant="outline" className={gateClass}>
                    {getString(gate.decision)?.toUpperCase() ?? "UNKNOWN"}
                  </Badge>
                </div>

                {getArray(gate.reasons).length > 0 && (
                  <div className="mt-4 space-y-2">
                    {getArray(gate.reasons).map((reason, index) => (
                      <p
                        key={index}
                        className="text-xs leading-5 text-zinc-400"
                      >
                        {typeof reason === "string"
                          ? reason
                          : JSON.stringify(reason)}
                      </p>
                    ))}
                  </div>
                )}

                <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
                  {[
                    ["Added", getNumber(evidenceDiff?.total_added)],
                    ["Removed", getNumber(evidenceDiff?.total_removed)],
                    ["Modified", getNumber(evidenceDiff?.total_modified)],
                    [
                      "Surface state changes",
                      getNumber(evidenceDiff?.total_surface_state_changes),
                    ],
                  ].map(([label, value]) => (
                    <div
                      key={String(label)}
                      className="rounded-md border border-zinc-800 bg-zinc-900/40 p-3"
                    >
                      <p className="text-[10px] uppercase tracking-wider text-zinc-500">
                        {label}
                      </p>
                      <p className="mt-2 text-xl font-semibold text-zinc-100">
                        {value}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="p-5 text-sm text-zinc-400">
                The API response did not contain a valid result. Check the
                validation response and backend logs.
              </div>
            )}
          </Card>

          {result && (
            <>
              <Card className="overflow-hidden border-zinc-800 bg-zinc-950">
                <div className="border-b border-zinc-800 p-5">
                  <h2 className="text-sm font-semibold uppercase tracking-wider text-zinc-100">
                    Surface changes
                  </h2>
                  <p className="mt-1 text-xs text-zinc-500">
                    Changes reported by the persisted evaluator.
                  </p>
                </div>

                {surfaceDiffs.length === 0 ? (
                  <p className="p-5 text-sm text-zinc-500">
                    No surface diff details were returned.
                  </p>
                ) : (
                  <div className="divide-y divide-zinc-800">
                    {surfaceDiffs.map(([surface, diff]) => {
                      const baselineState = isRecord(diff.baseline_state)
                        ? diff.baseline_state
                        : {};
                      const currentState = isRecord(diff.current_state)
                        ? diff.current_state
                        : {};

                      return (
                        <div key={surface} className="p-5">
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <p className="text-sm font-medium text-zinc-100">
                              {surfaceLabel(surface)}
                            </p>
                            <Badge variant="outline" className="border-zinc-800 text-zinc-400">
                              {getArray(diff.changes).length} changes
                            </Badge>
                          </div>

                          <div className="mt-3 grid gap-3 sm:grid-cols-2">
                            <div className="rounded-md bg-zinc-900/50 p-3">
                              <p className="text-[10px] uppercase tracking-wider text-zinc-500">
                                Baseline
                              </p>
                              <p className="mt-1 text-xs text-zinc-300">
                                {getString(baselineState.state) ?? "Unknown"}
                                {typeof baselineState.item_count === "number"
                                  ? ` · ${baselineState.item_count} items`
                                  : ""}
                              </p>
                            </div>
                            <div className="rounded-md bg-zinc-900/50 p-3">
                              <p className="text-[10px] uppercase tracking-wider text-zinc-500">
                                Current
                              </p>
                              <p className="mt-1 text-xs text-zinc-300">
                                {getString(currentState.state) ?? "Unknown"}
                                {typeof currentState.item_count === "number"
                                  ? ` · ${currentState.item_count} items`
                                  : ""}
                              </p>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </Card>

              <Card className="overflow-hidden border-zinc-800 bg-zinc-950">
                <div className="border-b border-zinc-800 p-5">
                  <h2 className="text-sm font-semibold uppercase tracking-wider text-zinc-100">
                    Evidence diff
                  </h2>
                  <p className="mt-1 text-xs text-zinc-500">
                    Item-level changes returned by the evaluator.
                  </p>
                </div>

                {evidenceChanges.length === 0 ? (
                  <p className="p-5 text-sm text-zinc-500">
                    No item-level changes were reported.
                  </p>
                ) : (
                  <div className="divide-y divide-zinc-800">
                    {evidenceChanges.map(({ key, surface, change }) => {
                      const item = isRecord(change) ? change : {};
                      const before = isRecord(item.baseline)
                        ? item.baseline
                        : isRecord(item.old_item)
                          ? item.old_item
                          : {};
                      const after = isRecord(item.current)
                        ? item.current
                        : isRecord(item.new_item)
                          ? item.new_item
                          : {};

                      const title =
                        getString(item.title) ??
                        getString(after.title) ??
                        getString(before.title) ??
                        getString(item.identity_key) ??
                        getString(after.identity_key) ??
                        getString(before.identity_key) ??
                        "Evidence item changed";

                      const url =
                        getString(item.url) ??
                        getString(after.url) ??
                        getString(before.url);

                      const kind =
                        getString(item.change_type) ??
                        getString(item.change) ??
                        getString(item.type) ??
                        "changed";

                      return (
                        <div key={key} className="p-5">
                          <div className="flex flex-wrap items-start justify-between gap-3">
                            <div>
                              <p className="text-[10px] uppercase tracking-wider text-zinc-500">
                                {surfaceLabel(surface)}
                              </p>
                              <h3 className="mt-2 text-sm font-medium text-zinc-200">
                                {title}
                              </h3>
                            </div>
                            <Badge variant="outline" className="border-zinc-800 text-zinc-400">
                              {kind}
                            </Badge>
                          </div>

                          {url && (
                            <a
                              href={url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="mt-3 inline-flex items-center gap-1.5 break-all text-xs text-zinc-400 hover:text-zinc-100"
                            >
                              {url}
                              <ExternalLink className="h-3 w-3 shrink-0" />
                            </a>
                          )}

                          {getString(item.snippet) && (
                            <p className="mt-2 text-xs leading-5 text-zinc-500">
                              {getString(item.snippet)}
                            </p>
                          )}

                          <details className="mt-3">
                            <summary className="cursor-pointer text-[11px] text-zinc-500">
                              Inspect raw change record
                            </summary>
                            <pre className="mt-2 overflow-auto whitespace-pre-wrap break-words rounded-md bg-black/30 p-3 text-[10px] text-zinc-500">
                              {JSON.stringify(change, null, 2)}
                            </pre>
                          </details>
                        </div>
                      );
                    })}
                  </div>
                )}
              </Card>

              <Card className="overflow-hidden border-zinc-800 bg-zinc-950">
                <div className="border-b border-zinc-800 p-5">
                  <h2 className="text-sm font-semibold uppercase tracking-wider text-zinc-100">
                    Claim impact
                  </h2>
                  <p className="mt-1 text-xs text-zinc-500">
                    The evaluator&apos;s assessment of your submitted claim and its
                    evidence dependency.
                  </p>
                </div>

                {claimImpacts.length === 0 ? (
                  <p className="p-5 text-sm text-zinc-500">
                    No claim impact records were returned.
                  </p>
                ) : (
                  <div className="divide-y divide-zinc-800">
                    {claimImpacts.map((impact, index) => {
                      const record = isRecord(impact) ? impact : {};
                      const reasons = getArray(record.reasons);
                      const dependencies = getArray(record.changed_dependencies);

                      return (
                        <div key={getString(record.claim_id) ?? index} className="p-5">
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <p className="text-sm font-medium text-zinc-200">
                              {getString(record.claim_id) ?? `Claim ${index + 1}`}
                            </p>
                            <Badge
                              variant="outline"
                              className={
                                record.material === true
                                  ? "border-red-900/60 bg-red-950/20 text-red-300"
                                  : record.affected === true
                                    ? "border-amber-900/60 bg-amber-950/20 text-amber-300"
                                    : "border-emerald-900/60 bg-emerald-950/20 text-emerald-300"
                              }
                            >
                              {record.material === true
                                ? "Material"
                                : record.affected === true
                                  ? "Affected"
                                  : "Not affected"}
                            </Badge>
                          </div>

                          <div className="mt-3 flex flex-wrap gap-2 text-xs text-zinc-400">
                            <span className="rounded border border-zinc-800 px-2 py-1">
                              Severity: {getString(record.severity) ?? "unknown"}
                            </span>
                            <span className="rounded border border-zinc-800 px-2 py-1">
                              Dependency: {getString(record.dependency_status) ?? "unknown"}
                            </span>
                            <span className="rounded border border-zinc-800 px-2 py-1">
                              Importance: {getString(record.importance) ?? "unknown"}
                            </span>
                          </div>

                          {reasons.length > 0 && (
                            <div className="mt-4 space-y-2">
                              {reasons.map((reason, reasonIndex) => (
                                <p key={reasonIndex} className="text-xs leading-5 text-zinc-400">
                                  {typeof reason === "string"
                                    ? reason
                                    : JSON.stringify(reason)}
                                </p>
                              ))}
                            </div>
                          )}

                          {dependencies.length > 0 && (
                            <details className="mt-4">
                              <summary className="cursor-pointer text-xs text-zinc-400">
                                Changed dependencies ({dependencies.length})
                              </summary>
                              <pre className="mt-2 overflow-auto whitespace-pre-wrap break-words rounded-md bg-black/30 p-3 text-[10px] text-zinc-500">
                                {JSON.stringify(dependencies, null, 2)}
                              </pre>
                            </details>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </Card>
            </>
          )}

          <Card className="border-zinc-800 bg-[#111113] p-5">
            <h2 className="text-sm font-semibold text-zinc-100">
              Persisted evaluation history
            </h2>

            {history ? (
              <div className="mt-3 space-y-2 text-xs text-zinc-400">
                <p>
                  Evaluation ID:{" "}
                  <span className="break-all font-mono text-zinc-300">
                    {getString(history.evaluation_id) ?? "Not supplied"}
                  </span>
                </p>
                <p>
                  Created: {formatDate(getString(history.created_at))}
                </p>
                <p>
                  Evaluator version:{" "}
                  {getString(history.evaluator_version) ?? "Not supplied"}
                </p>
                <p className="flex items-center gap-2 text-emerald-400">
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  Saved evaluation retrieved successfully.
                </p>
              </div>
            ) : historyError ? (
              <p className="mt-3 text-xs leading-5 text-amber-400">
                {historyError}
              </p>
            ) : evaluationPayload ? (
              <p className="mt-3 text-xs text-zinc-500">
                Checking the saved evaluation record...
              </p>
            ) : (
              <p className="mt-3 text-xs text-zinc-500">
                Run an evaluation to retrieve its saved history.
              </p>
            )}
          </Card>
        </section>
      )}
    </div>
  );
}
