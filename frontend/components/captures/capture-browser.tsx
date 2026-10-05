"use client";

import Link from "next/link";
import {
  Archive,
  ArrowUpRight,
  Calendar,
  ChevronRight,
  Monitor,
  Search,
  Smartphone,
} from "lucide-react";
import { useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";

import type { Capture, SearchSurface } from "@/lib/types";
import { surfaceLabels } from "@/lib/mock-data";

type Filter = "all" | SearchSurface;

interface CaptureBrowserProps {
  captures: Capture[];
}

function formatDate(timestamp: string) {
  return new Intl.DateTimeFormat("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(timestamp));
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

export function CaptureBrowser({
  captures,
}: CaptureBrowserProps) {
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<Filter>("all");

  const filteredCaptures = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();

    return captures.filter((capture) => {
      const matchesQuery =
        !normalizedQuery ||
        capture.query.toLowerCase().includes(normalizedQuery);

      const matchesFilter =
        filter === "all" || capture.surfaces.includes(filter);

      return matchesQuery && matchesFilter;
    });
  }, [captures, filter, query]);

  const filters: { label: string; value: Filter }[] = [
    { label: "All", value: "all" },
    { label: "Organic", value: "organic" },
    { label: "AI Overview", value: "ai_overview" },
    { label: "News", value: "news" },
    { label: "Shopping", value: "shopping" },
    { label: "Local", value: "local" },
  ];

  return (
    <div className="space-y-5">
      {/* Search + filters */}
      <Card className="border-zinc-800 bg-[#111113]">
        <div className="p-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-600" />

            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search captured queries..."
              className="h-10 w-full rounded-md border border-zinc-800 bg-zinc-950 pl-10 pr-4 text-sm text-zinc-200 outline-none placeholder:text-zinc-600 transition focus:border-zinc-600"
            />
          </div>

          <div className="mt-4 flex gap-2 overflow-x-auto pb-1">
            {filters.map((item) => {
              const active = filter === item.value;

              return (
                <button
                  key={item.value}
                  onClick={() => setFilter(item.value)}
                  className={[
                    "whitespace-nowrap rounded-md border px-3 py-1.5 text-xs transition",
                    active
                      ? "border-zinc-600 bg-zinc-800 text-zinc-100"
                      : "border-zinc-800 bg-zinc-950 text-zinc-500 hover:border-zinc-700 hover:text-zinc-300",
                  ].join(" ")}
                >
                  {item.label}
                </button>
              );
            })}
          </div>
        </div>
      </Card>

      {/* Result count */}
      <div className="flex items-center justify-between">
        <p className="text-xs text-zinc-500">
          Showing{" "}
          <span className="font-medium text-zinc-300">
            {filteredCaptures.length}
          </span>{" "}
          of {captures.length} captures
        </p>

        <p className="hidden text-xs text-zinc-600 sm:block">
          Search observations
        </p>
      </div>

      {/* Capture list */}
      <div className="space-y-2">
        {filteredCaptures.map((capture) => (
          <Link
            key={capture.id}
            href={`/captures/${capture.id}`}
            className="group block"
          >
            <Card className="border-zinc-800 bg-[#111113] transition hover:border-zinc-700 hover:bg-zinc-[0f0f11]">
              <div className="flex flex-col gap-5 p-5 lg:flex-row lg:items-center">
                {/* Icon */}
                <div className="hidden h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-zinc-800 bg-zinc-950 sm:flex">
                  <Archive className="h-4 w-4 text-zinc-500" />
                </div>

                {/* Query */}
                <div className="min-w-0 flex-1">
                  <div className="flex items-start gap-2">
                    <h2 className="line-clamp-2 text-sm font-medium text-zinc-200 transition group-hover:text-white">
                      {capture.query}
                    </h2>

                    <ArrowUpRight className="mt-0.5 h-3.5 w-3.5 shrink-0 text-zinc-700 transition group-hover:text-zinc-400" />
                  </div>

                  <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-zinc-600">
                    <span className="flex items-center gap-1.5">
                      <Calendar className="h-3 w-3" />
                      {formatDate(capture.timestamp)}
                    </span>

                    <span>•</span>

                    <span className="flex items-center gap-1.5">
                      {capture.device === "mobile" ? (
                        <Smartphone className="h-3 w-3" />
                      ) : (
                        <Monitor className="h-3 w-3" />
                      )}
                      {capture.device}
                    </span>

                    <span>•</span>

                    <span>{capture.location}</span>
                  </div>
                </div>

                {/* Surfaces */}
                <div className="flex flex-wrap gap-1.5 lg:max-w-xs lg:justify-end">
                  {capture.surfaces.map((surface) => (
                    <Badge
                      key={surface}
                      variant="outline"
                      className={`text-[10px] ${getSurfaceStyle(surface)}`}
                    >
                      {surfaceLabels[surface]}
                    </Badge>
                  ))}
                </div>

                {/* Evidence */}
                <div className="flex shrink-0 items-center justify-between gap-4 border-t border-zinc-800 pt-4 lg:w-28 lg:border-l lg:border-t-0 lg:pl-5 lg:pt-0">
                  <div>
                    <p className="text-sm font-semibold text-zinc-200">
                      {capture.evidenceCount}
                    </p>
                    <p className="text-[10px] text-zinc-600">
                      evidence
                    </p>
                  </div>

                  <ChevronRight className="h-4 w-4 text-zinc-700 transition group-hover:translate-x-0.5 group-hover:text-zinc-400" />
                </div>
              </div>
            </Card>
          </Link>
        ))}

        {/* Empty state */}
        {filteredCaptures.length === 0 && (
          <Card className="border-zinc-800 bg-[#111113]">
            <div className="flex flex-col items-center justify-center px-6 py-20 text-center">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-zinc-800 bg-zinc-950">
                <Search className="h-4 w-4 text-zinc-600" />
              </div>

              <h3 className="mt-4 text-sm font-medium text-zinc-300">
  No captures match these filters
</h3>

<p className="mt-1 max-w-sm text-xs leading-5 text-zinc-600">
  {query ? (
    <>
      No capture containing{" "}
      <span className="text-zinc-400">&quot;{query}&quot;</span>{" "}
      includes the{" "}
      <span className="text-zinc-400">
        {filter === "all" ? "selected" : surfaceLabels[filter]}
      </span>{" "}
      surface.
    </>
  ) : (
    "Try a different search query or remove the active surface filter."
  )}
</p>

              <button
                onClick={() => {
                  setQuery("");
                  setFilter("all");
                }}
                className="mt-4 text-xs text-zinc-400 underline underline-offset-4 hover:text-zinc-200"
              >
                Clear filters
              </button>
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}