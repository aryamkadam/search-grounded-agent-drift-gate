import Link from "next/link";
import { notFound } from "next/navigation";
import {
  AlertCircle,
  ArrowLeft,
  Calendar,
  ChevronRight,
  ExternalLink,
  Globe2,
  Laptop,
  MapPin,
  Search,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";

type JsonRecord = Record<string, unknown>;

interface DisplayEvidence {
  key: string;
  label: string;
  title: string;
  url?: string;
  displayedLink?: string;
  snippet?: string;
  source?: string;
  identityKey?: string;
  position?: number;
}

const SURFACE_LABELS: Record<string, string> = {
  organic: "Organic",
  organic_results: "Organic",
  news: "News",
  news_results: "News",
  ai_overview: "AI Overview",
  shopping: "Shopping",
  shopping_results: "Shopping",
  local: "Local",
  local_results: "Local",
  knowledge: "Knowledge",
  knowledge_graph: "Knowledge",
  perspectives: "Perspectives",
  related_questions: "Related questions",
  inline_images: "Images",
  inline_videos: "Videos",
};

const EVIDENCE_COLLECTIONS = [
  "organic_results",
  "news_results",
  "ai_overview",
  "shopping_results",
  "local_results",
  "knowledge_graph",
  "perspectives",
  "related_questions",
  "inline_images",
  "inline_videos",
];

function isRecord(value: unknown): value is JsonRecord {
  return (
    typeof value === "object" &&
    value !== null &&
    !Array.isArray(value)
  );
}

function firstString(...values: unknown[]): string | undefined {
  return values.find(
    (value): value is string =>
      typeof value === "string" && value.trim().length > 0
  );
}

function labelForSurface(key: string): string {
  return (
    SURFACE_LABELS[key] ??
    key.replace(/_/g, " ").replace(/\b\w/g, (letter) =>
      letter.toUpperCase()
    )
  );
}

function getSurfaceStyle(key: string): string {
  switch (key) {
    case "ai_overview":
      return "border-violet-900/60 bg-violet-950/20 text-violet-300";

    case "news":
    case "news_results":
      return "border-blue-900/60 bg-blue-950/20 text-blue-300";

    case "shopping":
    case "shopping_results":
      return "border-amber-900/60 bg-amber-950/20 text-amber-300";

    case "local":
    case "local_results":
      return "border-emerald-900/60 bg-emerald-950/20 text-emerald-300";

    default:
      return "border-zinc-800 bg-zinc-950 text-zinc-400";
  }
}

function formatDate(timestamp: string | undefined): string {
  if (!timestamp) return "Unknown";

  const date = new Date(timestamp);

  if (Number.isNaN(date.getTime())) return timestamp;

  return new Intl.DateTimeFormat("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function readEvidence(normalized: JsonRecord): DisplayEvidence[] {
  const result: DisplayEvidence[] = [];

  function addCollection(
    key: string,
    value: unknown,
    overrideLabel?: string
  ) {
    if (value === null || value === undefined) return;

    const label = overrideLabel ?? labelForSurface(key);

    let entries: unknown[];

    if (Array.isArray(value)) {
      entries = value;
    } else if (isRecord(value)) {
      entries = [value];
    } else if (typeof value === "string" && value.trim()) {
      entries = [{ text: value }];
    } else {
      return;
    }

    for (const [index, entry] of entries.entries()) {
      if (!isRecord(entry)) {
        if (typeof entry !== "string" || !entry.trim()) continue;

        result.push({
          key,
          label,
          title: `${label} item ${index + 1}`,
          snippet: entry,
        });

        continue;
      }

      const url = firstString(
        entry.url,
        entry.link,
        entry.source_url
      );

      result.push({
        key:
          firstString(entry.surface) ??
          key,
        label,
        title:
          firstString(
            entry.title,
            entry.heading,
            entry.name,
            entry.question,
            entry.displayed_link
          ) ?? `${label} item ${index + 1}`,
        url,
        displayedLink: firstString(entry.displayed_link),
        snippet: firstString(
          entry.snippet,
          entry.description,
          entry.text,
          entry.content,
          entry.answer
        ),
        source: firstString(entry.source),
        identityKey: firstString(entry.identity_key),
        position:
          typeof entry.position === "number"
            ? entry.position
            : typeof entry.rank === "number"
              ? entry.rank
              : undefined,
      });
    }
  }

  for (const key of EVIDENCE_COLLECTIONS) {
    addCollection(key, normalized[key]);
  }

  // Also show provider-specific surfaces when they are stored as
  // collections under normalized_evidence.additional_surfaces.
  const additional = normalized.additional_surfaces;

  if (isRecord(additional)) {
    for (const [key, value] of Object.entries(additional)) {
      addCollection(key, value);
    }
  }

  return result;
}


function getPresentSurfaces(
  normalized: JsonRecord,
  evidence: DisplayEvidence[]
): string[] {
  const metadata = normalized.surfaces;
  const result: string[] = [];

  function addSurface(key: string) {
    const label = labelForSurface(key);

    // Avoid duplicate badges such as "organic" and "organic_results".
    if (!result.some((existing) => labelForSurface(existing) === label)) {
      result.push(key);
    }
  }

  if (isRecord(metadata)) {
    for (const [key, value] of Object.entries(metadata)) {
      if (!isRecord(value)) continue;

      const isPresent =
        value.state === "present" ||
        (typeof value.item_count === "number" &&
          value.item_count > 0);

      if (isPresent) {
        addSurface(key);
      }
    }
  }

  // Include surfaces represented by actual normalized evidence too.
  for (const item of evidence) {
    addSurface(item.key);
  }

  return result;
}


function getEvidenceCount(
  normalized: JsonRecord,
  evidence: DisplayEvidence[]
): number {
  const metadata = normalized.surfaces;

  if (isRecord(metadata)) {
    const entries = Object.values(metadata).filter(isRecord);
    const hasCounts = entries.some(
      (item) => typeof item.item_count === "number"
    );

    if (hasCounts) {
      return entries.reduce(
        (total, item) =>
          total +
          (typeof item.item_count === "number"
            ? item.item_count
            : 0),
        0
      );
    }
  }

  return evidence.length;
}

interface CaptureDetailPageProps {
  params: Promise<{ id: string }>;
}

export default async function CaptureDetailPage({
  params,
}: CaptureDetailPageProps) {
  const { id } = await params;
  const baseUrl = process.env.NEXT_PUBLIC_API_URL?.replace(/\/+$/, "");

  let response: Response | null = null;
  let requestError: string | null = null;

  if (!baseUrl) {
    requestError =
      "NEXT_PUBLIC_API_URL is missing. Check frontend/.env.local.";
  } else {
    try {
      response = await fetch(
        `${baseUrl}/v1/captures/${encodeURIComponent(id)}`,
        { cache: "no-store" }
      );
    } catch {
      requestError =
        "Could not connect to the backend. Check that it is running and its IP address is still correct.";
    }
  }

  if (response?.status === 404) {
    notFound();
  }

  let capture: JsonRecord | null = null;

  if (response) {
    const payload: unknown = await response.json().catch(() => null);

    if (!response.ok) {
      requestError =
        isRecord(payload) && typeof payload.detail === "string"
          ? payload.detail
          : `The capture request failed with HTTP ${response.status}.`;
    } else if (isRecord(payload)) {
      capture = payload;
    } else {
      requestError = "The backend returned an invalid capture response.";
    }
  }

  if (requestError || !capture) {
    return (
      <div className="space-y-6">
        <Link
          href="/captures"
          className="inline-flex items-center gap-2 text-xs text-zinc-500 hover:text-zinc-200"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to captures
        </Link>

        <Card className="border-red-900/50 bg-[#111113]">
          <div className="flex flex-col items-center gap-3 p-10 text-center">
            <AlertCircle className="h-6 w-6 text-red-400" />

            <h1 className="text-lg font-semibold text-zinc-200">
              Could not load capture
            </h1>

            <p className="max-w-xl text-sm leading-6 text-zinc-400">
              {requestError ?? "The backend did not return a capture."}
            </p>

            <p className="text-xs text-zinc-600">
              Capture ID: {id}
            </p>

            <Link
              href="/captures"
              className="mt-2 rounded-md border border-zinc-700 px-4 py-2 text-xs text-zinc-200 hover:bg-zinc-900"
            >
              Return to captures
            </Link>
          </div>
        </Card>
      </div>
    );
  }

  const context = isRecord(capture.search_context)
    ? capture.search_context
    : {};

  const normalized = isRecord(capture.normalized_evidence)
    ? capture.normalized_evidence
    : {};

  const captureId =
    firstString(capture.capture_id, capture.id) ?? id;
  const query = firstString(context.query, capture.query) ?? "Unknown query";
  const timestamp = firstString(capture.captured_at, capture.timestamp);
  const countryCode = firstString(
  context.country,
  capture.country
)?.toUpperCase();

const countryName = countryCode
  ? new Intl.DisplayNames(["en"], { type: "region" }).of(countryCode)
  : undefined;

const location =
  firstString(context.location, capture.location) ??
  countryName ??
  "Unknown";
  const language =
    firstString(context.language, context.hl) ?? "Unknown";
  const device = firstString(context.device) ?? "Unknown";

  const evidence = readEvidence(normalized);
  const surfaces = getPresentSurfaces(normalized, evidence);
  const evidenceCount = getEvidenceCount(normalized, evidence);

  return (
    <div className="space-y-8">
      <Link
        href="/captures"
        className="inline-flex items-center gap-2 text-xs text-zinc-500 transition hover:text-zinc-200"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        Back to captures
      </Link>

      <section>
        <div className="flex flex-wrap items-center gap-2">
          <Badge
            variant="outline"
            className="border-zinc-800 bg-zinc-950 text-zinc-400"
          >
            CAPTURE
          </Badge>

          <span className="text-xs text-zinc-700">/</span>

          <span className="break-all font-mono text-xs text-zinc-500">
            {captureId}
          </span>
        </div>

        <h1 className="mt-4 max-w-4xl break-words text-2xl font-semibold tracking-tight text-zinc-100 md:text-3xl">
          {query}
        </h1>

        <p className="mt-3 max-w-3xl text-sm leading-6 text-zinc-500">
          Stored search context and normalized evidence retrieved from the
          backend. This page displays the data returned for this capture;
          offline agent replay is not yet implemented.
        </p>
      </section>

      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Card className="border-zinc-800 bg-[#111113]">
          <div className="p-4">
            <Calendar className="h-4 w-4 text-zinc-600" />
            <p className="mt-3 text-[11px] uppercase tracking-wider text-zinc-600">
              Captured
            </p>
            <p className="mt-1 text-sm text-zinc-300">
              {formatDate(timestamp)}
            </p>
          </div>
        </Card>

        <Card className="border-zinc-800 bg-[#111113]">
          <div className="p-4">
            <MapPin className="h-4 w-4 text-zinc-600" />
            <p className="mt-3 text-[11px] uppercase tracking-wider text-zinc-600">
              Location / Country
            </p>
            <p className="mt-1 text-sm text-zinc-300">{location}</p>
          </div>
        </Card>

        <Card className="border-zinc-800 bg-[#111113]">
          <div className="p-4">
            <Globe2 className="h-4 w-4 text-zinc-600" />
            <p className="mt-3 text-[11px] uppercase tracking-wider text-zinc-600">
              Language
            </p>
            <p className="mt-1 text-sm text-zinc-300">{language}</p>
          </div>
        </Card>

        <Card className="border-zinc-800 bg-[#111113]">
          <div className="p-4">
            <Laptop className="h-4 w-4 text-zinc-600" />
            <p className="mt-3 text-[11px] uppercase tracking-wider text-zinc-600">
              Device
            </p>
            <p className="mt-1 text-sm capitalize text-zinc-300">
              {device}
            </p>
          </div>
        </Card>
      </section>

      <section>
        <div className="mb-4">
          <h2 className="text-sm font-semibold text-zinc-200">
            Search surfaces
          </h2>
          <p className="mt-1 text-xs text-zinc-600">
            Surfaces identified in the stored evidence metadata.
          </p>
        </div>

        {surfaces.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {surfaces.map((surface) => (
              <Badge
                key={surface}
                variant="outline"
                className={`px-3 py-1.5 ${getSurfaceStyle(surface)}`}
              >
                {labelForSurface(surface)}
              </Badge>
            ))}
          </div>
        ) : (
          <p className="text-sm text-zinc-500">
            No present search surfaces were reported.
          </p>
        )}
      </section>

      <section>
        <div className="mb-4 flex items-end justify-between gap-4">
          <div>
            <h2 className="text-sm font-semibold text-zinc-200">
              Evidence snapshot
            </h2>
            <p className="mt-1 text-xs text-zinc-600">
              {evidenceCount} evidence items reported by the stored capture.
            </p>
          </div>

          <span className="hidden text-xs text-zinc-600 sm:block">
            Stored evidence
          </span>
        </div>

        {evidence.length > 0 ? (
          <div className="space-y-2">
            {evidence.map((item, index) => (
              <Card
                key={`${item.key}-${item.identityKey ?? item.url ?? index}-${index}`}
                className="border-zinc-800 bg-[#111113]"
              >
                <div className="flex gap-4 p-5">
                  <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md border border-zinc-800 bg-zinc-950 font-mono text-[10px] text-zinc-500">
                    {String(index + 1).padStart(2, "0")}
                  </div>

                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge
                        variant="outline"
                        className={`text-[10px] ${getSurfaceStyle(item.key)}`}
                      >
                        {item.label}
                      </Badge>

                      {typeof item.position === "number" && (
                        <span className="text-[10px] text-zinc-600">
                          Position {item.position}
                        </span>
                      )}
                    </div>

                    <h3 className="mt-3 break-words text-sm font-medium text-zinc-200">
                      {item.title}
                    </h3>

                    {item.displayedLink && (
                      <p className="mt-1 break-all text-xs text-zinc-500">
                        {item.displayedLink}
                      </p>
                    )}

                    {item.snippet && (
                      <p className="mt-2 break-words text-xs leading-5 text-zinc-500">
                        {item.snippet}
                      </p>
                    )}

                    {item.source && (
                      <p className="mt-2 text-[11px] text-zinc-600">
                        Source: {item.source}
                      </p>
                    )}

                    {item.identityKey && (
                      <p className="mt-2 break-all font-mono text-[10px] text-zinc-600">
                        {item.identityKey}
                      </p>
                    )}

                    {item.url && (
                      <a
                        href={item.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="mt-3 inline-flex items-center gap-1.5 text-xs text-zinc-400 hover:text-zinc-100"
                      >
                        Open source
                        <ExternalLink className="h-3 w-3" />
                      </a>
                    )}
                  </div>
                </div>
              </Card>
            ))}
          </div>
        ) : (
          <Card className="border-zinc-800 bg-[#111113]">
            <div className="p-10 text-center">
              <Search className="mx-auto h-5 w-5 text-zinc-600" />
              <h3 className="mt-3 text-sm font-medium text-zinc-300">
                No displayable evidence items
              </h3>
              <p className="mt-2 text-xs leading-5 text-zinc-600">
                The capture was retrieved successfully, but the backend
                returned no evidence items in the recognized collections.
                The reported evidence count is {evidenceCount}.
              </p>
            </div>
          </Card>
        )}
      </section>

      <Card className="border-zinc-800 bg-[#111113]">
        <div className="flex flex-col gap-4 p-5 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="flex items-center gap-2">
              <Search className="h-4 w-4 text-zinc-500" />
              <h2 className="text-sm font-medium text-zinc-200">
                Ready to compare?
              </h2>
            </div>

            <p className="mt-1 text-xs text-zinc-600">
              Compare this stored capture against another compatible capture
              to evaluate evidence drift.
            </p>
          </div>

          <Link
            href={`/compare?old=${encodeURIComponent(captureId)}`}
            className="inline-flex items-center justify-center gap-2 rounded-md border border-zinc-700 bg-zinc-900 px-4 py-2 text-xs font-medium text-zinc-200 transition hover:bg-zinc-800"
          >
            Compare capture
            <ChevronRight className="h-3.5 w-3.5" />
          </Link>
        </div>
      </Card>
    </div>
  );
}