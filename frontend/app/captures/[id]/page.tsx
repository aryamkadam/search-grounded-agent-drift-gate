import Link from "next/link";
import { notFound } from "next/navigation";
import {
  ArrowLeft,
  Calendar,
  ChevronRight,
  ExternalLink,
  Globe2,
  Laptop,
  MapPin,
  Search,
  Sparkles,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";

import { captures, surfaceLabels } from "@/lib/mock-data";
import type { SearchSurface } from "@/lib/types";

interface CaptureDetailPageProps {
  params: Promise<{
    id: string;
  }>;
}

function getSurfaceStyle(surface: SearchSurface) {
  switch (surface) {
    case "ai_overview":
      return "border-violet-900/60 bg-violet-950/20 text-violet-300";

    case "news":
      return "border-blue-900/60 bg-blue-950/20 text-blue-300";

    case "shopping":
      return "border-amber-900/60 bg-amber-950/20 text-amber-300";

    case "local":
      return "border-emerald-900/60 bg-emerald-950/20 text-emerald-300";

    default:
      return "border-zinc-800 bg-zinc-950 text-zinc-400";
  }
}

function formatDate(timestamp: string) {
  return new Intl.DateTimeFormat("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(timestamp));
}

export default async function CaptureDetailPage({
  params,
}: CaptureDetailPageProps) {
  const { id } = await params;

  const capture = captures.find((item) => item.id === id);

  if (!capture) {
    notFound();
  }

  return (
    <div className="space-y-8">
      {/* Back navigation */}
      <Link
        href="/captures"
        className="inline-flex items-center gap-2 text-xs text-zinc-500 transition hover:text-zinc-200"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        Back to captures
      </Link>

      {/* Header */}
      <section>
        <div className="flex flex-wrap items-center gap-2">
          <Badge
            variant="outline"
            className="border-zinc-800 bg-zinc-950 text-zinc-400"
          >
            CAPTURE
          </Badge>

          <span className="text-xs text-zinc-700">/</span>

          <span className="font-mono text-xs text-zinc-600">
            {capture.id}
          </span>
        </div>

        <h1 className="mt-4 max-w-4xl text-2xl font-semibold tracking-tight text-zinc-100 md:text-3xl">
          {capture.query}
        </h1>

        <p className="mt-3 max-w-3xl text-sm leading-6 text-zinc-500">
          The search evidence recorded during this agent run. This
          snapshot can later be compared against a newer capture or
          replayed without contacting the live search service.
        </p>
      </section>

      {/* Capture metadata */}
      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Card className="border-zinc-800 bg-[#111113]">
          <div className="p-4">
            <Calendar className="h-4 w-4 text-zinc-600" />

            <p className="mt-3 text-[11px] uppercase tracking-wider text-zinc-600">
              Captured
            </p>

            <p className="mt-1 text-sm text-zinc-300">
              {formatDate(capture.timestamp)}
            </p>
          </div>
        </Card>

        <Card className="border-zinc-800 bg-[#111113]">
          <div className="p-4">
            <MapPin className="h-4 w-4 text-zinc-600" />

            <p className="mt-3 text-[11px] uppercase tracking-wider text-zinc-600">
              Location
            </p>

            <p className="mt-1 text-sm text-zinc-300">
              {capture.location ?? "Unknown"}
            </p>
          </div>
        </Card>

        <Card className="border-zinc-800 bg-[#111113]">
          <div className="p-4">
            <Globe2 className="h-4 w-4 text-zinc-600" />

            <p className="mt-3 text-[11px] uppercase tracking-wider text-zinc-600">
              Language
            </p>

            <p className="mt-1 text-sm text-zinc-300">
              {capture.language ?? "Unknown"}
            </p>
          </div>
        </Card>

        <Card className="border-zinc-800 bg-[#111113]">
          <div className="p-4">
            <Laptop className="h-4 w-4 text-zinc-600" />

            <p className="mt-3 text-[11px] uppercase tracking-wider text-zinc-600">
              Device
            </p>

            <p className="mt-1 text-sm capitalize text-zinc-300">
              {capture.device ?? "Unknown"}
            </p>
          </div>
        </Card>
      </section>

      {/* Search surfaces */}
      <section>
        <div className="mb-4">
          <h2 className="text-sm font-semibold text-zinc-200">
            Search surfaces
          </h2>

          <p className="mt-1 text-xs text-zinc-600">
            Search surfaces preserved in this capture.
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          {capture.surfaces.map((surface) => (
            <Badge
              key={surface}
              variant="outline"
              className={`px-3 py-1.5 ${getSurfaceStyle(surface)}`}
            >
              {surfaceLabels[surface]}
            </Badge>
          ))}
        </div>
      </section>

      {/* Evidence */}
      <section>
        <div className="mb-4 flex items-end justify-between">
          <div>
            <h2 className="text-sm font-semibold text-zinc-200">
              Evidence snapshot
            </h2>

            <p className="mt-1 text-xs text-zinc-600">
              {capture.evidenceCount} evidence items preserved.
            </p>
          </div>

          <span className="hidden text-xs text-zinc-600 sm:block">
            Immutable capture
          </span>
        </div>

        <div className="space-y-2">
          {Array.from({
            length: Math.min(capture.evidenceCount, 6),
          }).map((_, index) => {
            const surface =
              capture.surfaces[index % capture.surfaces.length];

            return (
              <Card
                key={`${capture.id}-evidence-${index}`}
                className="border-zinc-800 bg-[#111113]"
              >
                <div className="flex gap-4 p-5">
                  {/* Number */}
                  <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md border border-zinc-800 bg-zinc-950 font-mono text-[10px] text-zinc-500">
                    {String(index + 1).padStart(2, "0")}
                  </div>

                  {/* Evidence information */}
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge
                        variant="outline"
                        className={`text-[10px] ${getSurfaceStyle(surface)}`}
                      >
                        {surfaceLabels[surface]}
                      </Badge>

                      {surface === "ai_overview" && (
                        <span className="flex items-center gap-1 text-[10px] text-violet-400">
                          <Sparkles className="h-3 w-3" />
                          AI-generated surface
                        </span>
                      )}
                    </div>

                    <h3 className="mt-3 text-sm font-medium text-zinc-200">
                      Evidence source {index + 1}
                    </h3>

                    <p className="mt-1 text-xs leading-5 text-zinc-600">
                      Structured search evidence preserved from the
                      original capture. The backend will later replace
                      this demo content with actual SerpApi evidence.
                    </p>
                  </div>

                  {/* External link placeholder */}
                  <button
                    type="button"
                    className="hidden shrink-0 self-start rounded-md p-2 text-zinc-700 transition hover:bg-zinc-900 hover:text-zinc-300 sm:block"
                    aria-label="Open evidence"
                  >
                    <ExternalLink className="h-3.5 w-3.5" />
                  </button>
                </div>
              </Card>
            );
          })}
        </div>
      </section>

      {/* Compare action */}
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
              Compare this capture with a newer observation to detect
              search evidence drift.
            </p>
          </div>

          <Link
            href={`/compare?old=${capture.id}`}
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