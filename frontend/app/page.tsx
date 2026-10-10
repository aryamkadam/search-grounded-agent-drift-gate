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

function asRecord(value: unknown): JsonRecord | null {
  if (typeof value === "object" && value !== null && !Array.isArray(value)) {
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

function mapCapture(value: unknown): CaptureSummary | null {
  const record = asRecord(value);

  if (!record) {
    return null;
  }

  const id = getString(record.capture_id);

  if (!id) {
    return null;
  }

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

export default function Home() {
  const [captures, setCaptures] = useState<CaptureSummary[]>([]);
  const [totalCaptures, setTotalCaptures] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [retryKey, setRetryKey] = useState(0);

  useEffect(() => {
    let cancelled = false;

    const timer = window.setTimeout(() => {
      async function loadCaptures() {
        const baseUrl = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");

        if (!baseUrl) {
          if (!cancelled) {
            setError(
              "NEXT_PUBLIC_API_URL is missing from frontend/.env.local.",
            );
            setLoading(false);
          }
          return;
        }

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
            throw new Error("The captures API returned an unexpected response.");
          }

          const mapped = body.items
            .map(mapCapture)
            .filter((item): item is CaptureSummary => item !== null);

          const total =
            typeof body.total === "number" && Number.isFinite(body.total)
              ? body.total
              : mapped.length;

          if (!cancelled) {
            setCaptures(mapped);
            setTotalCaptures(total);
            setError(null);
          }
        } catch (err) {
          if (!cancelled) {
            setError(
              err instanceof Error
                ? err.message
                : "Unable to load captures from the backend.",
            );
            setCaptures([]);
            setTotalCaptures(null);
          }
        } finally {
          if (!cancelled) {
            setLoading(false);
          }
        }
      }

      void loadCaptures();
    }, 0);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [retryKey]);

  const stats = [
    {
      label: "Total Captures",
      value: loading ? "…" : (totalCaptures?.toString() ?? "—"),
      description: error ? "Live count unavailable" : "Stored search observations",
      icon: Search,
    },
    {
      label: "Comparisons",
      value: "—",
      description: "Evaluation history count unavailable",
      icon: GitCompareArrows,
    },
    {
      label: "Drift Events",
      value: "—",
      description: "Requires evaluation history",
      icon: AlertTriangle,
    },
    {
      label: "Gate Failures",
      value: "—",
      description: "Requires evaluation history",
      icon: ShieldAlert,
    },
  ];

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
              error
                ? "border-red-900/60 bg-red-950/20 text-red-400"
                : loading
                  ? "border-zinc-800 bg-zinc-950 text-zinc-400"
                  : "border-green-900/60 bg-green-950/20 text-green-400"
            }`}
          >
            {error
              ? "API unavailable"
              : loading
                ? "Connecting to API…"
                : "Live capture API"}
          </Badge>
        </div>
      </section>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {stats.map((stat) => {
          const Icon = stat.icon;

          return (
            <Card
              key={stat.label}
              className="border-zinc-800 bg-[#111113]"
            >
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

      {error && (
        <Card className="border-red-900/40 bg-[#111113]">
          <CardContent className="flex flex-col gap-3 p-5 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-sm font-medium text-red-400">
                Could not load live captures
              </p>
              <p className="mt-1 break-words text-xs text-zinc-500">
                {error}
              </p>
            </div>

            <button
              type="button"
              onClick={() => {
                setLoading(true);
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
            {loading ? (
              <div className="flex items-center gap-2 px-6 py-8 text-sm text-zinc-500">
                <LoaderCircle className="h-4 w-4 animate-spin" />
                Loading captures…
              </div>
            ) : error ? (
              <p className="px-6 py-8 text-sm text-zinc-500">
                Recent captures cannot be shown until the backend connection
                is restored.
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

                      <p className="mt-1 truncate font-mono text-[10px] text-zinc-700">
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
                Evaluation overview
              </h2>
            </div>
          </CardHeader>

          <CardContent>
            <div className="rounded-lg border border-zinc-800 bg-zinc-950/60 p-4">
              <p className="text-sm font-medium text-zinc-200">
                Evaluation history unavailable
              </p>

              <p className="mt-2 text-xs leading-5 text-zinc-500">
                The current backend exposes evaluation creation and retrieval
                by ID, but not an endpoint that lists all evaluations. Summary
                counts and latest drift cannot be calculated accurately yet.
              </p>

              <Link
                href="/compare"
                className="mt-5 flex w-full items-center justify-center gap-2 rounded-md border border-zinc-700 bg-zinc-900 px-3 py-2 text-xs font-medium text-zinc-200 transition hover:bg-zinc-800"
              >
                <GitCompareArrows className="h-3.5 w-3.5" />
                Run a comparison
              </Link>
            </div>

            <div className="mt-4 flex items-center gap-2 text-xs text-zinc-600">
              <CheckCircle2 className="h-3.5 w-3.5 text-green-500" />
              {error ? "Backend connection needs attention" : loading
                ? "Checking capture API connection"
                : "Capture list loaded from backend"}
            </div>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}