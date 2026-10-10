
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  ArrowUpRight,
  CheckCircle2,
  GitCompareArrows,
  LoaderCircle,
  Search,
  ShieldAlert,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";

type JsonRecord = Record<string, unknown>;

interface CaptureSummary {
  id: string;
  query: string;
  capturedAt: string;
  country: string;
  device: string;
}

interface EvaluationSummary {
  id: string;
  createdAt: string;
  baselineCaptureId: string;
  currentCaptureId: string;
  decision: "pass" | "warn" | "block" | null;
  severity: string | null;
  affectedClaimCount: number | null;
  materialClaimCount: number | null;
}

function asRecord(value: unknown): JsonRecord | null {
  if (
    typeof value === "object" &&
    value !== null &&
    !Array.isArray(value)
  ) {
    return value as JsonRecord;
  }

  return null;
}

function getString(value: unknown): string | undefined {
  return typeof value === "string" && value.trim()
    ? value.trim()
    : undefined;
}

function getCount(value: unknown): number | null {
  return typeof value === "number" &&
    Number.isFinite(value) &&
    value >= 0
    ? value
    : null;
}

function formatDate(value: string): string {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "Time unavailable";
  }

  return new Intl.DateTimeFormat("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function mapCapture(value: unknown): CaptureSummary | null {
  const record = asRecord(value);
  if (!record) return null;

  const id = getString(record.capture_id);
  if (!id) return null;

  return {
    id,
    query: getString(record.query) ?? "Unknown query",
    capturedAt:
      getString(record.captured_at) ??
      getString(record.timestamp) ??
      "",
    country: getString(record.country)?.toUpperCase() ?? "—",
    device: getString(record.device) ?? "—",
  };
}

function mapEvaluation(value: unknown): EvaluationSummary | null {
  const record = asRecord(value);
  if (!record) return null;

  const id = getString(record.evaluation_id);
  if (!id) return null;

  const rawDecision = getString(record.decision)?.toLowerCase();

  const decision: EvaluationSummary["decision"] =
    rawDecision === "pass" ||
    rawDecision === "warn" ||
    rawDecision === "block"
      ? rawDecision
      : null;

  return {
    id,
    createdAt: getString(record.created_at) ?? "",
    baselineCaptureId:
      getString(record.baseline_capture_id) ?? "Unknown",
    currentCaptureId:
      getString(record.current_capture_id) ?? "Unknown",
    decision,
    severity: getString(record.severity)?.toLowerCase() ?? null,
    affectedClaimCount: getCount(record.affected_claim_count),
    materialClaimCount: getCount(record.material_claim_count),
  };
}

function decisionLabel(decision: EvaluationSummary["decision"]) {
  if (decision === "pass") return "PASS";
  if (decision === "warn") return "WARN";
  if (decision === "block") return "BLOCK";
  return "UNRESOLVED";
}

function decisionClass(decision: EvaluationSummary["decision"]) {
  if (decision === "pass") {
    return "border-green-900/60 bg-green-950/20 text-green-400";
  }

  if (decision === "warn") {
    return "border-amber-900/60 bg-amber-950/20 text-amber-400";
  }

  if (decision === "block") {
    return "border-red-900/60 bg-red-950/20 text-red-400";
  }

  return "border-zinc-700 bg-zinc-900 text-zinc-400";
}

export default function Home() {
  const [captures, setCaptures] = useState<CaptureSummary[]>([]);
  const [totalCaptures, setTotalCaptures] = useState<number | null>(null);
  const [evaluations, setEvaluations] = useState<EvaluationSummary[]>([]);
  const [totalEvaluations, setTotalEvaluations] = useState<number | null>(null);

  const [capturesLoading, setCapturesLoading] = useState(true);
  const [evaluationsLoading, setEvaluationsLoading] = useState(true);
  const [captureError, setCaptureError] = useState<string | null>(null);
  const [evaluationError, setEvaluationError] = useState<string | null>(null);
  const [retryKey, setRetryKey] = useState(0);

  useEffect(() => {
    let cancelled = false;

    const timer = window.setTimeout(() => {
      async function loadDashboard() {
        const baseUrl =
          process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");

        if (!baseUrl) {
          if (!cancelled) {
            const message =
              "NEXT_PUBLIC_API_URL is missing from frontend/.env.local.";
            setCaptureError(message);
            setEvaluationError(message);
            setCapturesLoading(false);
            setEvaluationsLoading(false);
          }
          return;
        }

        const loadCaptures = async () => {
          try {
            const response = await fetch(`${baseUrl}/v1/captures`, {
              cache: "no-store",
            });

            if (!response.ok) {
              throw new Error(`Captures API returned HTTP ${response.status}.`);
            }

            const payload: unknown = await response.json();
            const body = asRecord(payload);

            if (!body || !Array.isArray(body.items)) {
              throw new Error("Unexpected captures API response.");
            }

            const items = body.items
              .map(mapCapture)
              .filter((item): item is CaptureSummary => item !== null);

            const total =
              getCount(body.total) ?? items.length;

            if (!cancelled) {
              setCaptures(items);
              setTotalCaptures(total);
              setCaptureError(null);
            }
          } catch (err) {
            if (!cancelled) {
              setCaptureError(
                err instanceof Error
                  ? err.message
                  : "Unable to load captures.",
              );
              setCaptures([]);
              setTotalCaptures(null);
            }
          } finally {
            if (!cancelled) setCapturesLoading(false);
          }
        };

        const loadEvaluations = async () => {
          try {
            const response = await fetch(`${baseUrl}/v1/evaluations`, {
              cache: "no-store",
            });

            if (!response.ok) {
              throw new Error(
                `Evaluation history API returned HTTP ${response.status}.`,
              );
            }

            const payload: unknown = await response.json();
            const body = asRecord(payload);

            if (!body || !Array.isArray(body.items)) {
              throw new Error("Unexpected evaluation history API response.");
            }

            const items = body.items
              .map(mapEvaluation)
              .filter((item): item is EvaluationSummary => item !== null);

            const total = getCount(body.total);

            if (total === null) {
              throw new Error(
                "Evaluation history response is missing a valid total count.",
              );
            }

            if (!cancelled) {
              setEvaluations(items);
              setTotalEvaluations(total);
              setEvaluationError(null);
            }
          } catch (err) {
            if (!cancelled) {
              setEvaluationError(
                err instanceof Error
                  ? err.message
                  : "Unable to load evaluation history.",
              );
              setEvaluations([]);
              setTotalEvaluations(null);
            }
          } finally {
            if (!cancelled) setEvaluationsLoading(false);
          }
        };

        await Promise.all([loadCaptures(), loadEvaluations()]);
      }

      void loadDashboard();
    }, 0);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [retryKey]);

  const decidedEvaluations = evaluations.filter(
    (item) => item.decision !== null,
  );

  const unresolvedCount = evaluations.filter(
    (item) => item.decision === null,
  ).length;

  // A drift event is a recorded WARN or BLOCK decision.
  const driftEvents = decidedEvaluations.filter(
    (item) => item.decision === "warn" || item.decision === "block",
  ).length;

  // Gate failures count recorded BLOCK decisions only.
  const gateFailures = decidedEvaluations.filter(
    (item) => item.decision === "block",
  ).length;

  const stats = [
    {
      label: "Total Captures",
      value: capturesLoading
        ? "…"
        : totalCaptures?.toString() ?? "—",
      description: captureError
        ? "Live count unavailable"
        : "Stored search observations",
      icon: Search,
    },
    {
      label: "Comparisons",
      value: evaluationsLoading
        ? "…"
        : totalEvaluations?.toString() ?? "—",
      description: evaluationError
        ? "History unavailable"
        : "Persisted evaluation records",
      icon: GitCompareArrows,
    },
    {
      label: "Drift Events",
      value: evaluationsLoading || evaluationError
        ? "—"
        : driftEvents.toString(),
      description: evaluationError
        ? "History unavailable"
        : "Recorded WARN or BLOCK decisions",
      icon: AlertTriangle,
    },
    {
      label: "Gate Failures",
      value: evaluationsLoading || evaluationError
        ? "—"
        : gateFailures.toString(),
      description: evaluationError
        ? "History unavailable"
        : "Recorded BLOCK decisions",
      icon: ShieldAlert,
    },
  ];

  const loading = capturesLoading || evaluationsLoading;
  const anyError = Boolean(captureError || evaluationError);

  return (
    <div className="space-y-8">
      <section>
        <div className="flex flex-col justify-between gap-4 md:flex-row md:items-end">
          <div>
            <p className="mb-2 text-xs font-medium uppercase tracking-[0.18em] text-zinc-500">
              Search evidence control
            </p>

            <h1 className="text-3xl font-semibold tracking-tight text-zinc-100">
              Overview
            </h1>

            <p className="mt-2 max-w-2xl text-sm leading-6 text-zinc-500">
              Detect when changes in live search evidence can change what an
              AI agent is able to claim.
            </p>
          </div>

          <Badge
            variant="outline"
            className={`w-fit px-3 py-1.5 ${
              anyError
                ? "border-amber-900/60 bg-amber-950/20 text-amber-400"
                : loading
                  ? "border-zinc-800 bg-zinc-950 text-zinc-400"
                  : "border-green-900/60 bg-green-950/20 text-green-400"
            }`}
          >
            {anyError
              ? "Partial API availability"
              : loading
                ? "Connecting to APIs…"
                : "Live API data"}
          </Badge>
        </div>
      </section>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {stats.map((stat) => {
          const Icon = stat.icon;

          return (
            <Card key={stat.label} className="border-zinc-800 bg-[#111113]">
              <CardContent className="p-5">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-xs text-zinc-500">{stat.label}</p>
                    <p className="mt-3 text-3xl font-semibold tracking-tight">
                      {stat.value}
                    </p>
                    <p className="mt-1 text-xs text-zinc-600">
                      {stat.description}
                    </p>
                  </div>

                  <div className="rounded-md border border-zinc-800 bg-zinc-950 p-2">
                    <Icon className="h-4 w-4 text-zinc-500" />
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </section>

      {anyError && (
        <Card className="border-amber-900/40 bg-[#111113]">
          <CardContent className="flex flex-col gap-3 p-5 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-sm font-medium text-amber-400">
                Some dashboard data is unavailable
              </p>
              {captureError && (
                <p className="mt-1 break-words text-xs text-zinc-500">
                  Captures: {captureError}
                </p>
              )}
              {evaluationError && (
                <p className="mt-1 break-words text-xs text-zinc-500">
                  Evaluations: {evaluationError}
                </p>
              )}
            </div>

            <button
              type="button"
              onClick={() => {
                setCapturesLoading(true);
                setEvaluationsLoading(true);
                setRetryKey((key) => key + 1);
              }}
              className="flex w-fit items-center gap-2 rounded-md border border-zinc-700 px-3 py-2 text-xs text-zinc-200 hover:bg-zinc-900"
            >
              Retry
            </button>
          </CardContent>
        </Card>
      )}

      <section className="grid gap-6 xl:grid-cols-[1.6fr_1fr]">
        <Card className="border-zinc-800 bg-[#111113]">
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-zinc-200">
                Recent captures
              </h2>
              <p className="mt-1 text-xs text-zinc-500">
                Latest stored search observations from the backend
              </p>
            </div>

            <Link
              href="/captures"
              className="flex items-center gap-1 text-xs text-zinc-500 transition hover:text-zinc-200"
            >
              View all
              <ArrowUpRight className="h-3 w-3" />
            </Link>
          </CardHeader>

          <CardContent className="p-0">
            {capturesLoading ? (
              <div className="flex items-center gap-2 px-6 py-8 text-sm text-zinc-500">
                <LoaderCircle className="h-4 w-4 animate-spin" />
                Loading captures…
              </div>
            ) : captureError ? (
              <p className="px-6 py-8 text-sm text-zinc-500">
                Recent captures cannot be shown until the capture API is
                available.
              </p>
            ) : captures.length === 0 ? (
              <p className="px-6 py-8 text-sm text-zinc-500">
                No stored captures are available yet.
              </p>
            ) : (
              <div className="divide-y divide-zinc-800">
                {captures.slice(0, 5).map((capture) => (
                  <Link
                    key={capture.id}
                    href={`/captures/${encodeURIComponent(capture.id)}`}
                    className="flex flex-col gap-3 px-6 py-4 transition hover:bg-zinc-950/60 sm:flex-row sm:items-center sm:justify-between"
                  >
                    <div className="min-w-0">
                      <p className="truncate text-sm text-zinc-200">
                        {capture.query}
                      </p>
                      <p className="mt-1 text-xs text-zinc-600">
                        {formatDate(capture.capturedAt)} · {capture.country} ·{" "}
                        {capture.device}
                      </p>
                      <p className="mt-1 break-all font-mono text-[10px] text-zinc-700">
                        {capture.id}
                      </p>
                    </div>

                    <ArrowUpRight className="h-4 w-4 shrink-0 text-zinc-600" />
                  </Link>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="border-zinc-800 bg-[#111113]">
          <CardHeader>
            <div className="flex items-center gap-2">
              <GitCompareArrows className="h-4 w-4 text-zinc-400" />
              <h2 className="text-sm font-semibold text-zinc-200">
                Recent evaluations
              </h2>
            </div>
          </CardHeader>

          <CardContent className="space-y-4">
            {evaluationsLoading ? (
              <div className="flex items-center gap-2 py-6 text-sm text-zinc-500">
                <LoaderCircle className="h-4 w-4 animate-spin" />
                Loading evaluation history…
              </div>
            ) : evaluationError ? (
              <p className="text-sm text-zinc-500">
                Evaluation history is currently unavailable.
              </p>
            ) : evaluations.length === 0 ? (
              <p className="text-sm text-zinc-500">
                No persisted evaluations were returned by the backend.
              </p>
            ) : (
              <div className="space-y-3">
                {evaluations.slice(0, 5).map((evaluation) => (
                  <div
                    key={evaluation.id}
                    className="rounded-lg border border-zinc-800 bg-zinc-950/60 p-3"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <Badge
                        variant="outline"
                        className={decisionClass(evaluation.decision)}
                      >
                        {decisionLabel(evaluation.decision)}
                      </Badge>
                      <span className="text-[10px] text-zinc-600">
                        {evaluation.createdAt
                          ? formatDate(evaluation.createdAt)
                          : "Time unavailable"}
                      </span>
                    </div>

                    <p className="mt-3 break-all font-mono text-[10px] leading-5 text-zinc-500">
                      {evaluation.id}
                    </p>

                    <p className="mt-2 text-xs text-zinc-500">
                      Affected claims:{" "}
                      {evaluation.affectedClaimCount ?? "Unavailable"}
                      {" · "}
                      Material claims:{" "}
                      {evaluation.materialClaimCount ?? "Unavailable"}
                    </p>

                    <p className="mt-1 break-all text-[10px] text-zinc-600">
                      Baseline: {evaluation.baselineCaptureId}
                    </p>
                    <p className="mt-1 break-all text-[10px] text-zinc-600">
                      Current: {evaluation.currentCaptureId}
                    </p>
                  </div>
                ))}
              </div>
            )}

            {!evaluationError && !evaluationsLoading && unresolvedCount > 0 && (
              <p className="text-xs leading-5 text-amber-400">
                {unresolvedCount} evaluation
                {unresolvedCount === 1 ? "" : "s"} have no recorded gate
                decision and are excluded from drift and failure counts.
              </p>
            )}

            <Link
              href="/compare"
              className="flex w-full items-center justify-center gap-2 rounded-md border border-zinc-700 bg-zinc-900 px-3 py-2 text-xs font-medium text-zinc-200 transition hover:bg-zinc-800"
            >
              <GitCompareArrows className="h-3.5 w-3.5" />
              Run a comparison
            </Link>

            <div className="flex items-center gap-2 text-xs text-zinc-600">
              <CheckCircle2 className="h-3.5 w-3.5 text-green-500" />
              {captureError
                ? "Capture API needs attention"
                : "Capture list loaded from backend"}
            </div>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
