
"use client";

import { useEffect, useState } from "react";
import {
  AlertCircle,
  ExternalLink,
  History,
  Search,
  Database,
  LoaderCircle,
  RefreshCw,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";

type JsonRecord = Record<string, unknown>;

interface CaptureOption {
  capture_id: string;
  query: string;
  captured_at: string;
  country?: string;
  device?: string;
}

interface ReplayResponse {
  replay_id: string;
  capture_id: string;
  status: string;
  mode: string;
  captured_at: string;
  search_context: unknown;
  normalized_evidence: unknown;
}

interface EvidenceItem {
  id: string;
  surface: string;
  title: string;
  url?: string;
  snippet?: string;
  source?: string;
  rank?: number;
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

function humanize(value: string): string {
  return value
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function mapCapture(value: unknown): CaptureOption | null {
  const record = asRecord(value);

  if (!record) return null;

  const captureId = getString(record.capture_id);
  if (!captureId) return null;

  const context = asRecord(record.search_context);

  return {
    capture_id: captureId,
    query:
      getString(context?.query) ??
      getString(record.query) ??
      "Unknown query",
    captured_at:
      getString(record.captured_at) ??
      getString(record.timestamp) ??
      "",
    country:
      getString(context?.country) ??
      getString(record.country),
    device:
      getString(context?.device) ??
      getString(record.device),
  };
}

function extractEvidence(value: unknown): EvidenceItem[] {
  const results: EvidenceItem[] = [];
  const seen = new Set<string>();

  function visit(node: unknown, path: string, depth: number) {
    if (depth > 8) return;

    if (Array.isArray(node)) {
      node.forEach((item, index) =>
        visit(item, path, depth + 1),
      );
      return;
    }

    const record = asRecord(node);
    if (!record) return;

    const title =
      getString(record.title) ??
      getString(record.name) ??
      getString(record.question) ??
      getString(record.text);

    const url =
      getString(record.link) ??
      getString(record.url) ??
      getString(record.source_url);

    const snippet =
      getString(record.snippet) ??
      getString(record.description) ??
      getString(record.answer);

    const identity =
      getString(record.identity_key) ??
      getString(record.id) ??
      url ??
      title;

    if (title && (url || snippet || identity)) {
      const key = `${path}:${identity}:${title}`;

      if (!seen.has(key)) {
        seen.add(key);

        const rankValue =
          typeof record.position === "number"
            ? record.position
            : typeof record.rank === "number"
              ? record.rank
              : undefined;

        results.push({
          id: key,
          surface: path || "evidence",
          title,
          url,
          snippet,
          source:
            getString(record.source) ??
            getString(record.source_name) ??
            getString(record.displayed_link),
          rank: rankValue,
        });
      }
    }

    for (const [key, child] of Object.entries(record)) {
      if (key === "raw_response" || key === "metadata") continue;

      if (Array.isArray(child) || asRecord(child)) {
        visit(
          child,
          path ? `${path}.${key}` : key,
          depth + 1,
        );
      }
    }
  }

  visit(value, "", 0);
  return results;
}

export function ReplayWorkspace() {
  const [captures, setCaptures] = useState<CaptureOption[]>([]);
  const [captureId, setCaptureId] = useState("");
  const [replay, setReplay] = useState<ReplayResponse | null>(null);
  const [loadingCaptures, setLoadingCaptures] = useState(true);
  const [replaying, setReplaying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [retryKey, setRetryKey] = useState(0);

  useEffect(() => {
    let cancelled = false;

    const timer = window.setTimeout(() => {
      async function loadCaptures() {
        const baseUrl =
          process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");

        if (!baseUrl) {
          if (!cancelled) {
            setError(
              "NEXT_PUBLIC_API_URL is missing from frontend/.env.local.",
            );
            setLoadingCaptures(false);
          }
          return;
        }

        try {
          const response = await fetch(`${baseUrl}/v1/captures`, {
            cache: "no-store",
          });

          if (!response.ok) {
            throw new Error(
              `Could not load captures (HTTP ${response.status}).`,
            );
          }

          const payload: unknown = await response.json();
          const body = asRecord(payload);

          if (!body || !Array.isArray(body.items)) {
            throw new Error("The captures API returned an unexpected response.");
          }

          const items = body.items
            .map(mapCapture)
            .filter((item): item is CaptureOption => item !== null);

          if (!cancelled) {
            setCaptures(items);
            setCaptureId((current) => {
              if (current && items.some((item) => item.capture_id === current)) {
                return current;
              }
              return items[0]?.capture_id ?? "";
            });
            setError(null);
          }
        } catch (err) {
          if (!cancelled) {
            setError(
              err instanceof Error
                ? err.message
                : "Unable to load captures.",
            );
          }
        } finally {
          if (!cancelled) setLoadingCaptures(false);
        }
      }

      void loadCaptures();
    }, 0);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [retryKey]);

  const selectedCapture = captures.find(
    (item) => item.capture_id === captureId,
  );

  const evidence = replay
    ? extractEvidence(replay.normalized_evidence)
    : [];

  async function runReplay() {
    const baseUrl =
      process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");

    if (!baseUrl || !captureId) {
      setError(
        !baseUrl
          ? "NEXT_PUBLIC_API_URL is not configured."
          : "Select a saved capture first.",
      );
      return;
    }

    setReplaying(true);
    setError(null);
    setReplay(null);

    try {
      const response = await fetch(
        `${baseUrl}/v1/captures/${encodeURIComponent(captureId)}/replay`,
        {
          method: "POST",
          cache: "no-store",
        },
      );

      if (response.status === 404) {
        throw new Error(
          "The backend could not find this stored capture (HTTP 404). Refresh the capture list and try again.",
        );
      }

      if (response.status === 500) {
        throw new Error(
          "The backend reported a capture integrity failure (HTTP 500). The stored snapshot could not be replayed.",
        );
      }

      if (!response.ok) {
        const details = await response.text();
        throw new Error(
          `Replay failed (HTTP ${response.status}). ${details.slice(0, 300)}`,
        );
      }

      const payload: unknown = await response.json();
      const body = asRecord(payload);

      if (
        !body ||
        !getString(body.replay_id) ||
        !getString(body.capture_id) ||
        !getString(body.status) ||
        !getString(body.mode)
      ) {
        throw new Error("The replay endpoint returned an unexpected response.");
      }

      if (!asRecord(body.search_context) || !asRecord(body.normalized_evidence)) {
        throw new Error(
          "Replay response is missing search_context or normalized_evidence.",
        );
      }

      setReplay({
        replay_id: getString(body.replay_id)!,
        capture_id: getString(body.capture_id)!,
        status: getString(body.status)!,
        mode: getString(body.mode)!,
        captured_at: getString(body.captured_at) ?? "",
        search_context: body.search_context,
        normalized_evidence: body.normalized_evidence,
      });
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "An unexpected replay error occurred.",
      );
    } finally {
      setReplaying(false);
    }
  }

  const searchContext = asRecord(replay?.search_context);

  return (
    <div className="space-y-8">
      <section>
        <div className="flex items-center gap-2">
          <History className="h-4 w-4 text-zinc-500" />
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-zinc-500">
            Stored observations
          </p>
        </div>

        <h1 className="mt-3 text-3xl font-semibold tracking-tight text-zinc-100">
          Replay
        </h1>

        <p className="mt-2 max-w-2xl text-sm leading-6 text-zinc-500">
          Replay a saved search snapshot offline without issuing a new search
          request. The original stored evidence is returned by the backend.
        </p>
      </section>

      <Card className="border-zinc-800 bg-[#111113]">
        <div className="space-y-4 p-5">
          <label
            htmlFor="replay-capture"
            className="block text-xs text-zinc-500"
          >
            Select saved capture
          </label>

          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-600" />

            <select
              id="replay-capture"
              value={captureId}
              disabled={loadingCaptures || captures.length === 0 || replaying}
              onChange={(event) => {
                setCaptureId(event.target.value);
                setReplay(null);
                setError(null);
              }}
              className="h-11 w-full rounded-md border border-zinc-800 bg-zinc-950 pl-10 pr-3 text-sm text-zinc-200 outline-none focus:border-zinc-600 disabled:opacity-50"
            >
              {captures.length === 0 && (
                <option value="">
                  {loadingCaptures ? "Loading captures…" : "No captures available"}
                </option>
              )}

              {captures.map((item) => (
                <option key={item.capture_id} value={item.capture_id}>
                  {item.query} — {formatDate(item.captured_at)}
                </option>
              ))}
            </select>
          </div>

          {selectedCapture && (
            <div className="grid gap-4 border-t border-zinc-800 pt-4 sm:grid-cols-2">
              <div>
                <p className="text-[10px] uppercase tracking-wider text-zinc-500">
                  Search query
                </p>
                <p className="mt-2 text-sm text-zinc-200">
                  {selectedCapture.query}
                </p>
              </div>

              <div>
                <p className="text-[10px] uppercase tracking-wider text-zinc-500">
                  Capture ID
                </p>
                <p className="mt-2 break-all font-mono text-xs text-zinc-300">
                  {selectedCapture.capture_id}
                </p>
              </div>

              <div>
                <p className="text-[10px] uppercase tracking-wider text-zinc-500">
                  Captured at
                </p>
                <p className="mt-2 text-sm text-zinc-200">
                  {formatDate(selectedCapture.captured_at)}
                </p>
              </div>

              <div>
                <p className="text-[10px] uppercase tracking-wider text-zinc-500">
                  Country / Device
                </p>
                <p className="mt-2 text-sm text-zinc-200">
                  {selectedCapture.country ?? "—"} / {selectedCapture.device ?? "—"}
                </p>
              </div>
            </div>
          )}

          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={() => void runReplay()}
              disabled={!captureId || loadingCaptures || replaying}
              className="inline-flex h-10 items-center justify-center gap-2 rounded-md border border-zinc-700 bg-zinc-100 px-4 text-sm font-medium text-zinc-950 transition hover:bg-white disabled:cursor-not-allowed disabled:opacity-50"
            >
              {replaying ? (
                <LoaderCircle className="h-4 w-4 animate-spin" />
              ) : (
                <RefreshCw className="h-4 w-4" />
              )}
              {replaying ? "Replaying stored snapshot…" : "Replay stored snapshot"}
            </button>

            <button
              type="button"
              onClick={() => {
                setLoadingCaptures(true);
                setReplay(null);
                setError(null);
                setRetryKey((key) => key + 1);
              }}
              disabled={loadingCaptures || replaying}
              className="inline-flex h-10 items-center justify-center gap-2 rounded-md border border-zinc-800 px-4 text-sm text-zinc-300 hover:bg-zinc-900 disabled:opacity-50"
            >
              Refresh captures
            </button>
          </div>

          {error && (
            <div
              role="alert"
              className="flex items-start gap-2 rounded-md border border-red-900/50 bg-red-950/20 p-3 text-sm text-red-300"
            >
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}
        </div>
      </Card>

      {replay && (
        <>
          <Card className="border-zinc-800 bg-[#111113]">
            <div className="space-y-4 p-5">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-xs uppercase tracking-wider text-zinc-500">
                    Backend replay result
                  </p>
                  <h2 className="mt-2 text-lg font-semibold text-zinc-100">
                    Replay completed
                  </h2>
                </div>

                <Badge
                  variant="outline"
                  className="border-green-900/60 bg-green-950/20 text-green-400"
                >
                  {replay.status.toUpperCase()} · {replay.mode.toUpperCase()}
                </Badge>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <p className="text-[10px] uppercase tracking-wider text-zinc-500">
                    Replay ID
                  </p>
                  <p className="mt-2 break-all font-mono text-xs text-zinc-300">
                    {replay.replay_id}
                  </p>
                </div>

                <div>
                  <p className="text-[10px] uppercase tracking-wider text-zinc-500">
                    Capture ID
                  </p>
                  <p className="mt-2 break-all font-mono text-xs text-zinc-300">
                    {replay.capture_id}
                  </p>
                </div>

                <div>
                  <p className="text-[10px] uppercase tracking-wider text-zinc-500">
                    Original capture time
                  </p>
                  <p className="mt-2 text-sm text-zinc-200">
                    {replay.captured_at
                      ? formatDate(replay.captured_at)
                      : "Unavailable"}
                  </p>
                </div>

                <div>
                  <p className="text-[10px] uppercase tracking-wider text-zinc-500">
                    Evidence items displayed
                  </p>
                  <p className="mt-2 text-sm text-zinc-200">
                    {evidence.length}
                  </p>
                </div>
              </div>
            </div>
          </Card>

          <Card className="border-zinc-800 bg-zinc-950">
            <div className="border-b border-zinc-800 px-6 py-5">
              <div className="flex items-center gap-3">
                <Database className="h-5 w-5 text-zinc-400" />
                <div>
                  <h2 className="text-sm font-semibold uppercase tracking-wider text-zinc-100">
                    Original search context
                  </h2>
                  <p className="mt-1 text-xs text-zinc-500">
                    Returned by the offline replay endpoint
                  </p>
                </div>
              </div>
            </div>

            <div className="grid gap-4 p-6 sm:grid-cols-2">
              {searchContext &&
                Object.entries(searchContext).map(([key, value]) => (
                  <div key={key}>
                    <p className="text-[10px] uppercase tracking-wider text-zinc-500">
                      {humanize(key)}
                    </p>
                    <p className="mt-2 break-words text-sm text-zinc-200">
                      {value === null || value === undefined
                        ? "—"
                        : typeof value === "object"
                          ? JSON.stringify(value)
                          : String(value)}
                    </p>
                  </div>
                ))}
            </div>
          </Card>

          <Card className="overflow-hidden border-zinc-800 bg-zinc-950">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-zinc-800 px-6 py-5">
              <div className="flex items-center gap-3">
                <Database className="h-5 w-5 text-zinc-400" />
                <div>
                  <h2 className="text-sm font-semibold uppercase tracking-wider text-zinc-100">
                    Stored evidence snapshot
                  </h2>
                  <p className="mt-1 text-xs text-zinc-500">
                    Evidence extracted from the returned normalized snapshot
                  </p>
                </div>
              </div>

              <Badge
                variant="outline"
                className="border-green-900/60 bg-green-950/20 text-green-400"
              >
                BACKEND DATA
              </Badge>
            </div>

            {evidence.length > 0 ? (
              <div className="divide-y divide-zinc-800">
                {evidence.map((item) => (
                  <article key={item.id} className="space-y-3 p-6">
                    <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                      <h3 className="text-sm font-medium leading-5 text-zinc-100">
                        {item.title}
                      </h3>

                      <Badge
                        variant="outline"
                        className="w-fit border-zinc-700 text-zinc-400"
                      >
                        {humanize(item.surface)}
                      </Badge>
                    </div>

                    {item.snippet && (
                      <p className="text-xs leading-5 text-zinc-400">
                        {item.snippet}
                      </p>
                    )}

                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <span className="text-xs text-zinc-500">
                        {item.source ?? "Source unavailable"}
                        {item.rank !== undefined ? ` · Rank #${item.rank}` : ""}
                      </span>

                      {item.url && /^https?:\/\//i.test(item.url) && (
                        <a
                          href={item.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-xs text-zinc-400 hover:text-zinc-100"
                        >
                          View source
                          <ExternalLink className="h-3 w-3" />
                        </a>
                      )}
                    </div>
                  </article>
                ))}
              </div>
            ) : (
              <div className="flex flex-col items-center gap-3 px-6 py-12 text-center">
                <AlertCircle className="h-6 w-6 text-zinc-600" />
                <p className="text-sm font-medium text-zinc-300">
                  No displayable evidence items found
                </p>
                <p className="max-w-md text-xs leading-5 text-zinc-500">
                  The replay request succeeded, but this view could not extract
                  individual evidence records from the returned normalized
                  snapshot. The original response is still available in the
                  browser Network panel.
                </p>
              </div>
            )}
          </Card>
        </>
      )}
    </div>
  );
}
