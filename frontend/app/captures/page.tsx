
"use client";

import { useCallback, useEffect, useState } from "react";
import { Archive, AlertCircle, LoaderCircle, RefreshCw } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { CaptureBrowser } from "@/components/captures/capture-browser";
import type { Capture, SearchSurface } from "@/lib/types";

type ApiRecord = Record<string, unknown>;

function isRecord(value: unknown): value is ApiRecord {
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

const surfaceMap: Record<string, SearchSurface> = {
  organic: "organic",
  organic_results: "organic",
  news: "news",
  news_results: "news",
  ai_overview: "ai_overview",
  shopping: "shopping",
  shopping_results: "shopping",
  local: "local",
  local_results: "local",
  knowledge: "knowledge",
  knowledge_graph: "knowledge",
};


function mapCapture(value: unknown): Capture | null {
  if (!isRecord(value)) return null;

  const context = isRecord(value.search_context)
    ? value.search_context
    : {};

  const evidence = isRecord(value.normalized_evidence)
    ? value.normalized_evidence
    : {};

  const surfaceMetadata = isRecord(evidence.surfaces)
    ? evidence.surfaces
    : {};

  const id = getString(value.capture_id) ?? getString(value.id);

  if (!id) return null;

  const surfaces: SearchSurface[] = [];

  for (const [key, metadata] of Object.entries(surfaceMetadata)) {
    const surface = surfaceMap[key];

    if (!surface || !isRecord(metadata)) continue;

    if (
      metadata.state === "present" ||
      (typeof metadata.item_count === "number" &&
        metadata.item_count > 0)
    ) {
      if (!surfaces.includes(surface)) {
        surfaces.push(surface);
      }
    }
  }

  if (surfaces.length === 0) {
    for (const [key, surface] of Object.entries(surfaceMap)) {
      const items = evidence[key];

      if (
        (Array.isArray(items) && items.length > 0) ||
        (key === "ai_overview" &&
          items !== null &&
          items !== undefined)
      ) {
        if (!surfaces.includes(surface)) {
          surfaces.push(surface);
        }
      }
    }
  }

  const explicitCount = value.evidence_count ?? value.evidenceCount;
  let evidenceCount: number | undefined;

  if (
    typeof explicitCount === "number" &&
    Number.isFinite(explicitCount)
  ) {
    evidenceCount = explicitCount;
  } else if (isRecord(value.normalized_evidence)) {
    if (isRecord(value.normalized_evidence.surfaces)) {
      const entries = Object.values(
        value.normalized_evidence.surfaces
      ).filter(isRecord);

      const hasItemCounts = entries.some(
        (item) => typeof item.item_count === "number"
      );

      if (hasItemCounts) {
        evidenceCount = entries.reduce(
          (total, item) =>
            total +
            (typeof item.item_count === "number"
              ? item.item_count
              : 0),
          0
        );
      }
    }
  }

  const country =
    getString(value.country) ?? getString(context.country);

  return {
    id,
    query:
      getString(context.query) ??
      getString(value.query) ??
      "Unknown query",
    timestamp:
      getString(value.captured_at) ??
      getString(value.timestamp) ??
      "",
    location:
      getString(value.location) ??
      getString(context.location) ??
      country?.toUpperCase(),
    language:
      getString(context.language) ??
      getString(context.language_code),
    device:
      getString(context.device) ??
      getString(value.device),
    surfaces,
    evidenceCount,
    agentRunId:
      getString(value.agent_run_id) ??
      getString(value.agentRunId),
  };
}


export default function CapturesPage() {
  const [captures, setCaptures] = useState<Capture[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadCaptures = useCallback(async () => {
    const baseUrl = process.env.NEXT_PUBLIC_API_URL?.replace(/\/+$/, "");

    if (!baseUrl) {
      setError("API URL is missing. Check frontend/.env.local.");
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${baseUrl}/v1/captures`, {
        method: "GET",
        cache: "no-store",
      });

      const payload: unknown = await response.json();

      if (!response.ok) {
        const detail =
          isRecord(payload) && typeof payload.detail === "string"
            ? payload.detail
            : `Backend request failed (${response.status}).`;

        throw new Error(detail);
      }

      const rawItems = Array.isArray(payload)
        ? payload
        : isRecord(payload) && Array.isArray(payload.items)
          ? payload.items
          : null;

      if (!rawItems) {
        throw new Error(
          "Unexpected capture-list response. Expected an items array."
        );
      }

      const mappedCaptures = rawItems
        .map(mapCapture)
        .filter((capture): capture is Capture => capture !== null);

      if (rawItems.length > 0 && mappedCaptures.length === 0) {
        throw new Error(
          "Captures were returned, but their IDs could not be read. Please verify the backend response schema."
        );
      }

      setCaptures(mappedCaptures);

      setTotal(
        isRecord(payload) && typeof payload.total === "number"
          ? payload.total
          : mappedCaptures.length
      );
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not load captures from the backend."
      );
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadCaptures();
    }, 0);

    return () => window.clearTimeout(timer);
  }, [loadCaptures]);


  return (
    <div className="space-y-8">
      <section>
        <div className="flex flex-col justify-between gap-4 md:flex-row md:items-end">
          <div>
            <div className="mb-2 flex items-center gap-2">
              <Archive className="h-4 w-4 text-zinc-500" />
              <p className="text-xs font-medium uppercase tracking-[0.18em] text-zinc-500">
                Evidence archive
              </p>
            </div>

            <h1 className="text-3xl font-semibold tracking-tight text-zinc-100">
              Captures
            </h1>

            <p className="mt-2 max-w-2xl text-sm leading-6 text-zinc-500">
              Browse the search evidence recorded during agent runs.
              Every capture preserves the search context needed for
              deterministic comparison and replay.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <Badge
              variant="outline"
              className="w-fit border-zinc-800 bg-zinc-950 px-3 py-1.5 text-zinc-400"
            >
              {loading ? "Loading..." : `${total} captures`}
            </Badge>

            <button
              type="button"
              onClick={() => void loadCaptures()}
              disabled={loading}
              aria-label="Refresh captures"
              className="rounded-md border border-zinc-800 bg-zinc-950 p-2 text-zinc-400 hover:text-zinc-100 disabled:opacity-50"
            >
              <RefreshCw
                className={`h-4 w-4 ${loading ? "animate-spin" : ""}`}
              />
            </button>
          </div>
        </div>
      </section>

      {loading ? (
        <Card className="border-zinc-800 bg-[#111113]">
          <div className="flex items-center justify-center gap-3 p-12 text-sm text-zinc-400">
            <LoaderCircle className="h-5 w-5 animate-spin" />
            Loading captures from the backend...
          </div>
        </Card>
      ) : error ? (
        <Card className="border-red-900/50 bg-[#111113]">
          <div className="flex flex-col items-center gap-3 p-10 text-center">
            <AlertCircle className="h-6 w-6 text-red-400" />
            <h2 className="text-sm font-medium text-zinc-200">
              Could not load captures
            </h2>
            <p className="max-w-xl text-sm text-zinc-400">{error}</p>
            <p className="text-xs text-zinc-600">
              Check that the backend is running, the API URL is correct,
              and CORS allows this frontend origin.
            </p>
            <button
              type="button"
              onClick={() => void loadCaptures()}
              className="mt-2 rounded-md border border-zinc-700 px-4 py-2 text-sm text-zinc-200 hover:bg-zinc-900"
            >
              Try again
            </button>
          </div>
        </Card>
      ) : total === 0 ? (
        <Card className="border-zinc-800 bg-[#111113]">
          <div className="flex flex-col items-center justify-center px-6 py-20 text-center">
            <Archive className="h-6 w-6 text-zinc-500" />
            <h2 className="mt-4 text-sm font-medium text-zinc-200">
              No captures yet
            </h2>
            <p className="mt-2 max-w-md text-xs leading-5 text-zinc-500">
              The backend has not stored any captures yet. Create a capture
              through the backend workflow, then refresh this page.
            </p>
          </div>
        </Card>
      ) : (
        <CaptureBrowser captures={captures} />
      )}
    </div>
  );
}
