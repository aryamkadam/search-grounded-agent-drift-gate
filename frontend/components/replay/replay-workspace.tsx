"use client";

import { useMemo, useState } from "react";
import {
  AlertCircle,
  ExternalLink,
  History,
  Search,
  Database,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { captures, demoComparison } from "@/lib/mock-data";

function formatDate(timestamp: string) {
  return new Intl.DateTimeFormat("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(timestamp));
}

export function ReplayWorkspace() {
  const [captureId, setCaptureId] = useState("cap_001");

  const capture = useMemo(
    () => captures.find((item) => item.id === captureId),
    [captureId]
  );

  const isComparisonCapture =
    captureId === demoComparison.oldCaptureId ||
    captureId === demoComparison.newCaptureId;

  const evidence = isComparisonCapture
    ? demoComparison.evidenceChanges.filter((item) =>
        captureId === demoComparison.oldCaptureId
          ? item.changeType === "removed"
          : item.changeType === "added"
      )
    : [];

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
          Inspect a previously captured search observation without issuing a
          new search request.
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
              onChange={(event) => setCaptureId(event.target.value)}
              className="h-11 w-full appearance-none rounded-md border border-zinc-800 bg-zinc-950 pl-10 pr-3 text-sm text-zinc-200 outline-none focus:border-zinc-600"
            >
              {captures.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.id} — {item.query}
                </option>
              ))}
            </select>
          </div>

          {capture ? (
            <div className="grid gap-4 border-t border-zinc-800 pt-4 sm:grid-cols-2">
              <div>
                <p className="text-[10px] uppercase tracking-wider text-zinc-500">
                  Search query
                </p>
                <p className="mt-2 text-sm text-zinc-200">{capture.query}</p>
              </div>

              <div>
                <p className="text-[10px] uppercase tracking-wider text-zinc-500">
                  Capture ID
                </p>
                <p className="mt-2 text-sm text-zinc-200">{capture.id}</p>
              </div>

              <div>
                <p className="text-[10px] uppercase tracking-wider text-zinc-500">
                  Captured at
                </p>
                <p className="mt-2 text-sm text-zinc-200">
                  {formatDate(capture.timestamp)}
                </p>
              </div>

              <div>
                <p className="text-[10px] uppercase tracking-wider text-zinc-500">
                  Evidence records available / reported
                </p>
                <p className="mt-2 text-sm text-zinc-200">
                  {evidence.length} / {capture.evidenceCount}
                </p>
              </div>
            </div>
          ) : (
            <p className="text-sm text-zinc-500">
              The selected capture could not be found.
            </p>
          )}
        </div>
      </Card>

      <Card className="overflow-hidden border-zinc-800 bg-zinc-950">
        <div className="flex flex-col gap-3 border-b border-zinc-800 px-6 py-5 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-zinc-800 bg-zinc-900">
              <Database className="h-4 w-4 text-zinc-400" />
            </div>

            <div>
              <h2 className="text-sm font-semibold uppercase tracking-wider text-zinc-100">
                Stored Evidence
              </h2>
              <p className="mt-1 text-xs text-zinc-500">
                Only evidence records available in the demo comparison are shown here.
                This is not the complete stored capture snapshot.
              </p>
            </div>
          </div>

          <Badge
            variant="outline"
            className="w-fit border-amber-900/60 bg-amber-950/20 text-amber-400"
          >
            PARTIAL DEMO DATA
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
                    {item.surface.replace("_", " ")}
                  </Badge>
                </div>

                <p className="text-xs leading-5 text-zinc-400">
                  {item.snippet || "No snippet is available for this item."}
                </p>

                <div className="flex flex-wrap items-center justify-between gap-3">
                  <span className="text-xs text-zinc-500">
  {item.source || "Unknown source"}
  {item.rank !== undefined ? ` · Rank #${item.rank}` : ""}
</span>

                  <a
                    href={item.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-xs text-zinc-400 hover:text-zinc-100"
                  >
                    View source
                    <ExternalLink className="h-3 w-3" />
                  </a>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <div className="flex flex-col items-center gap-3 px-6 py-12 text-center">
            <AlertCircle className="h-6 w-6 text-zinc-600" />
            <p className="text-sm font-medium text-zinc-300">
              No replay evidence available
            </p>
            <p className="max-w-md text-xs leading-5 text-zinc-500">
              This demo does not contain a complete stored evidence snapshot
              for the selected capture. The backend must supply that snapshot
              for a full replay.
            </p>
          </div>
        )}
      </Card>
    </div>
  );
}