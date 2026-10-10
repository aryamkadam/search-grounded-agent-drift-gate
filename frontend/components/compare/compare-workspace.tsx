"use client";

import { useMemo, useState } from "react";

import {
  AlertTriangle,
  Layers3,
  ArrowRight,
  Calendar,
  Check,
  ChevronDown,
  GitCompareArrows,
  ExternalLink,
  MinusCircle,
  PlusCircle,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";

import { captures, demoComparison } from "@/lib/mock-data";

interface CompareWorkspaceProps {
  initialOldId?: string;
  initialNewId?: string;
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

export function CompareWorkspace({
  initialOldId = "cap_001",
  initialNewId = "cap_009",
}: CompareWorkspaceProps) {
  const [oldId, setOldId] = useState(initialOldId);
  const [newId, setNewId] = useState(initialNewId);

  const oldCapture = useMemo(
    () => captures.find((capture) => capture.id === oldId),
    [oldId]
  );

  const newCapture = useMemo(
    () => captures.find((capture) => capture.id === newId),
    [newId]
  );

  const sameQuery =
    oldCapture &&
    newCapture &&
    oldCapture.query === newCapture.query;
      const surfaceChanges = demoComparison.surfaceChanges;
  const evidenceChanges = demoComparison.evidenceChanges;
  const claimImpacts = demoComparison.claimImpacts;

  const affectedClaims = claimImpacts.filter(
    (claim) => claim.status !== "supported"
  ).length;

  const evidenceDelta =
    evidenceChanges.filter((item) => item.changeType === "added").length -
    evidenceChanges.filter((item) => item.changeType === "removed").length;

  const gateStatus = !sameQuery
    ? "NOT RUN"
    : affectedClaims > 0
      ? "FAIL"
      : "PASS";

  return (
    <div className="space-y-8">
      {/* Page heading */}
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
          Compare two captured search observations to determine whether
          the evidence available to an AI agent has changed.
        </p>
      </section>

      {/* Capture selectors */}
      <section>
        <div className="grid gap-4 lg:grid-cols-[1fr_auto_1fr] lg:items-center">
          {/* Old capture */}
          <Card className="border-zinc-800 bg-[#111113]">
            <div className="p-5">
              <div className="mb-4 flex items-center justify-between">
                <Badge
                  variant="outline"
                  className="border-zinc-800 bg-zinc-950 text-zinc-500"
                >
                  OLD CAPTURE
                </Badge>

                <span className="text-[10px] uppercase tracking-wider text-zinc-600">
                  Baseline
                </span>
              </div>

              <label
                htmlFor="old-capture"
                className="mb-2 block text-xs text-zinc-600"
              >
                Search observation
              </label>

              <div className="relative">
                <select
                  id="old-capture"
                  value={oldId}
                  onChange={(event) => setOldId(event.target.value)}
                  className="h-11 w-full appearance-none rounded-md border border-zinc-800 bg-zinc-950 px-3 pr-10 text-sm text-zinc-200 outline-none transition focus:border-zinc-600"
                >
                  {captures.map((capture) => (
                    <option
                      key={capture.id}
                      value={capture.id}
                    >
                      {capture.query} —{" "}
                      {formatDate(capture.timestamp)}
                    </option>
                  ))}
                </select>

                <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-600" />
              </div>

              {oldCapture && (
                <div className="mt-4 border-t border-zinc-800 pt-4">
                  <p className="line-clamp-2 text-sm text-zinc-300">
                    {oldCapture.query}
                  </p>

                  <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-zinc-600">
                    <Calendar className="h-3 w-3" />

                    {formatDate(oldCapture.timestamp)}

                    <span>•</span>

                    <span>
                      {oldCapture.evidenceCount} evidence
                    </span>
                  </div>
                </div>
              )}
            </div>
          </Card>

          {/* Compare indicator */}
          <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-full border border-zinc-800 bg-zinc-950">
            <ArrowRight className="h-4 w-4 text-zinc-600" />
          </div>

          {/* New capture */}
          <Card className="border-zinc-800 bg-[#111113]">
            <div className="p-5">
              <div className="mb-4 flex items-center justify-between">
                <Badge
                  variant="outline"
                  className="border-blue-900/60 bg-blue-950/20 text-blue-300"
                >
                  NEW CAPTURE
                </Badge>

                <span className="text-[10px] uppercase tracking-wider text-zinc-600">
                  Candidate
                </span>
              </div>

              <label
                htmlFor="new-capture"
                className="mb-2 block text-xs text-zinc-600"
              >
                Search observation
              </label>

              <div className="relative">
                <select
                  id="new-capture"
                  value={newId}
                  onChange={(event) => setNewId(event.target.value)}
                  className="h-11 w-full appearance-none rounded-md border border-zinc-800 bg-zinc-950 px-3 pr-10 text-sm text-zinc-200 outline-none transition focus:border-zinc-600"
                >
                  {captures.map((capture) => (
                    <option
                      key={capture.id}
                      value={capture.id}
                    >
                      {capture.query} —{" "}
                      {formatDate(capture.timestamp)}
                    </option>
                  ))}
                </select>

                <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-600" />
              </div>

              {newCapture && (
                <div className="mt-4 border-t border-zinc-800 pt-4">
                  <p className="line-clamp-2 text-sm text-zinc-300">
                    {newCapture.query}
                  </p>

                  <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-zinc-600">
                    <Calendar className="h-3 w-3" />

                    {formatDate(newCapture.timestamp)}

                    <span>•</span>

                    <span>
                      {newCapture.evidenceCount} evidence
                    </span>
                  </div>
                </div>
              )}
            </div>
          </Card>
        </div>

        {/* Validation */}
        <div className="mt-4">
          {sameQuery ? (
            <div className="flex items-center gap-2 text-xs text-zinc-600">
              <Check className="h-3.5 w-3.5 text-green-500" />

              Both captures represent the same search query.
            </div>
          ) : (
            <div className="rounded-md border border-amber-900/50 bg-amber-950/10 px-4 py-3 text-xs text-amber-400">
              Select two captures of the same search query to perform a
              meaningful evidence comparison.
            </div>
          )}
        </div>
      </section>

      {/* Drift Status Hero */}
      <Card className="overflow-hidden border-zinc-800 bg-zinc-950">
        <div className="border-b border-zinc-800 px-6 py-5">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div className="flex items-start gap-4">
              <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full border border-red-500/30 bg-red-500/10">
                <AlertTriangle className="h-5 w-5 text-red-400" />
              </div>

              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <h2 className="text-lg font-semibold text-zinc-100">
                    {!sameQuery
  ? "Comparison Not Run"
  : affectedClaims > 0
    ? "Material Drift Detected"
    : "No Claim Impact Detected"}
                  </h2>

                  <span className="rounded-full border border-red-500/30 bg-red-500/10 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider text-red-400">
                    High severity
                  </span>
                </div>

                <p className="mt-1 max-w-2xl text-sm leading-6 text-zinc-400">
                  Search evidence changed materially between these two captures.
                  At least one agent claim may no longer be supported by the
                  evidence available in the new search.
                </p>
              </div>
            </div>

            <div className="shrink-0">
              <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-center">
                <p className="text-[10px] font-medium uppercase tracking-widest text-zinc-500">
                  Drift Gate
                </p>

                <p className="mt-1 text-sm font-semibold text-red-400">
                  {gateStatus}
                </p>
              </div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 divide-x divide-zinc-800 sm:grid-cols-4">
          <div className="px-6 py-5">
            <p className="text-xs uppercase tracking-wider text-zinc-500">
              Surface Changes
            </p>

            <p className="mt-2 text-2xl font-semibold text-zinc-100">
              {surfaceChanges.length}
            </p>

            <p className="mt-1 text-xs text-zinc-500">
              search surfaces changed
            </p>
          </div>

          <div className="px-6 py-5">
            <p className="text-xs uppercase tracking-wider text-zinc-500">
              Evidence Changes
            </p>

            <p className="mt-2 text-2xl font-semibold text-zinc-100">
              {evidenceChanges.length}
            </p>

            <p className="mt-1 text-xs text-zinc-500">
              additions or removals
            </p>
          </div>

          <div className="px-6 py-5">
            <p className="text-xs uppercase tracking-wider text-zinc-500">
              {affectedClaims} / {claimImpacts.length}
            </p>

            <p className="mt-2 text-2xl font-semibold text-zinc-100">
              1 / 2
            </p>

            <p className="mt-1 text-xs text-zinc-500">
              agent claims impacted
            </p>
          </div>

          <div className="px-6 py-5">
            <p className="text-xs uppercase tracking-wider text-zinc-500">
              {evidenceDelta > 0 ? "+" : ""}{evidenceDelta}
            </p>

            <p className="mt-2 text-2xl font-semibold text-red-400">
              -1
            </p>

            <p className="mt-1 text-xs text-zinc-500">
              net evidence change
            </p>
          </div>
        </div>
      </Card>


      {/* Surface Changes */}
      <Card className="overflow-hidden border-zinc-800 bg-zinc-950">
        <div className="border-b border-zinc-800 px-6 py-5">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-zinc-800 bg-zinc-900">
              <Layers3 className="h-4 w-4 text-zinc-400" />
            </div>

            <div>
              <h2 className="text-sm font-semibold uppercase tracking-wider text-zinc-100">
                Surface Changes
              </h2>

              <p className="mt-1 text-xs text-zinc-500">
                Changes detected across the search surfaces available to the agent.
              </p>
            </div>
          </div>
        </div>

        <div className="divide-y divide-zinc-800">
          {demoComparison.surfaceChanges.map((surface) => (
            <div
              key={surface.surface}
              className="px-6 py-5"
            >
              <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
                <div className="flex items-center gap-3">
                  <div className="h-2 w-2 rounded-full bg-red-400" />

                  <div>
                    <p className="text-sm font-medium text-zinc-100">
                      {surface.surface}
                    </p>

                    <p className="mt-1 text-xs text-zinc-500">
                      Search surface
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-8">
                  <div>
                    <p className="text-[10px] uppercase tracking-wider text-zinc-500">
                      Added
                    </p>

                    <p className="mt-1 text-sm font-semibold text-emerald-400">
                      +{surface.added}
                    </p>
                  </div>

                  <div>
                    <p className="text-[10px] uppercase tracking-wider text-zinc-500">
                      Removed
                    </p>

                    <p className="mt-1 text-sm font-semibold text-red-400">
                      -{surface.removed}
                    </p>
                  </div>

                  <div>
                    <p className="text-[10px] uppercase tracking-wider text-zinc-500">
                      Changed
                    </p>

                    <p className="mt-1 text-sm font-semibold text-amber-400">
                      ~{surface.modified}
                    </p>
                  </div>
                </div>

                <div className="rounded-full border border-red-500/20 bg-red-500/5 px-3 py-1.5">
                  <span className="text-[10px] font-medium uppercase tracking-wider text-red-400">
                    Material Change
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </Card>

{/* Evidence Diff */}
<Card className="overflow-hidden border-zinc-800 bg-zinc-950">
  <div className="border-b border-zinc-800 px-6 py-5">
    <div className="flex items-center gap-3">
      <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-zinc-800 bg-zinc-900">
        <GitCompareArrows className="h-4 w-4 text-zinc-400" />
      </div>

      <div>
        <h2 className="text-sm font-semibold uppercase tracking-wider text-zinc-100">
          Evidence Diff
        </h2>

        <p className="mt-1 text-xs text-zinc-500">
          Sources added or removed between the two search captures.
        </p>
      </div>
    </div>
  </div>

  <div className="grid gap-0 lg:grid-cols-2 lg:divide-x lg:divide-zinc-800">
    {/* Removed evidence */}
    <div>
      <div className="flex items-center justify-between border-b border-zinc-800 px-6 py-4">
        <div className="flex items-center gap-2">
          <MinusCircle className="h-4 w-4 text-red-400" />
          <h3 className="text-sm font-medium text-zinc-100">
            Removed Evidence
          </h3>
        </div>

        <Badge
          variant="outline"
          className="border-red-900/60 bg-red-950/20 text-red-400"
        >
          REMOVED
        </Badge>
      </div>

      <div className="divide-y divide-zinc-800">
        {demoComparison.evidenceChanges
          .filter((evidence) => evidence.changeType === "removed")
          .map((evidence) => (
            <div key={evidence.id} className="space-y-3 p-6">
              <div className="flex items-start justify-between gap-3">
                <h4 className="text-sm font-medium leading-5 text-zinc-100">
                  {evidence.title}
                </h4>

                <span className="shrink-0 rounded border border-zinc-800 px-2 py-1 text-[10px] text-zinc-500">
                  Rank #{evidence.rank}
                </span>
              </div>

              <p className="text-xs text-zinc-400">
                {evidence.snippet}
              </p>

              <div className="flex flex-wrap items-center justify-between gap-3">
                <span className="text-xs text-zinc-500">
                  {evidence.source}
                </span>

                <a
                  href={evidence.url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 text-xs text-zinc-400 transition hover:text-zinc-100"
                >
                  View source
                  <ExternalLink className="h-3 w-3" />
                </a>
              </div>

              <div className="rounded-md border border-red-900/30 bg-red-950/10 px-3 py-2">
                <p className="text-xs text-red-300">
                  This source was present in the previous capture.
                </p>
              </div>
            </div>
          ))}

        {demoComparison.evidenceChanges.filter(
          (evidence) => evidence.changeType === "removed"
        ).length === 0 && (
          <p className="p-6 text-sm text-zinc-500">
            No removed evidence in this comparison.
          </p>
        )}
      </div>
    </div>

    {/* Added evidence */}
    <div>
      <div className="flex items-center justify-between border-b border-zinc-800 px-6 py-4">
        <div className="flex items-center gap-2">
          <PlusCircle className="h-4 w-4 text-emerald-400" />
          <h3 className="text-sm font-medium text-zinc-100">
            Added Evidence
          </h3>
        </div>

        <Badge
          variant="outline"
          className="border-emerald-900/60 bg-emerald-950/20 text-emerald-400"
        >
          ADDED
        </Badge>
      </div>

      <div className="divide-y divide-zinc-800">
        {demoComparison.evidenceChanges
          .filter((evidence) => evidence.changeType === "added")
          .map((evidence) => (
            <div key={evidence.id} className="space-y-3 p-6">
              <div className="flex items-start justify-between gap-3">
                <h4 className="text-sm font-medium leading-5 text-zinc-100">
                  {evidence.title}
                </h4>

                <span className="shrink-0 rounded border border-zinc-800 px-2 py-1 text-[10px] text-zinc-500">
                  Rank #{evidence.rank}
                </span>
              </div>

              <p className="text-xs text-zinc-400">
                {evidence.snippet}
              </p>

              <div className="flex flex-wrap items-center justify-between gap-3">
                <span className="text-xs text-zinc-500">
                  {evidence.source}
                </span>

                <a
                  href={evidence.url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 text-xs text-zinc-400 transition hover:text-zinc-100"
                >
                  View source
                  <ExternalLink className="h-3 w-3" />
                </a>
              </div>

              <div className="rounded-md border border-emerald-900/30 bg-emerald-950/10 px-3 py-2">
                <p className="text-xs text-emerald-300">
                  This source appears in the new capture.
                </p>
              </div>
            </div>
          ))}

        {demoComparison.evidenceChanges.filter(
          (evidence) => evidence.changeType === "added"
        ).length === 0 && (
          <p className="p-6 text-sm text-zinc-500">
            No added evidence in this comparison.
          </p>
        )}
      </div>
    </div>
  </div>
</Card>

      {/* Claim Impact */}
      <Card className="overflow-hidden border-zinc-800 bg-zinc-950">
        <div className="border-b border-zinc-800 px-6 py-5">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-zinc-800 bg-zinc-900">
              <AlertTriangle className="h-4 w-4 text-amber-400" />
            </div>

            <div>
              <h2 className="text-sm font-semibold uppercase tracking-wider text-zinc-100">
                Claim Impact
              </h2>
              <p className="mt-1 text-xs text-zinc-500">
                How evidence changes affect claims made by the AI agent.
              </p>
            </div>
          </div>
        </div>

        <div className="divide-y divide-zinc-800">
          {demoComparison.claimImpacts.map((impact) => {
            const isWeakened = impact.status === "weakened";
            const isSupported = impact.status === "supported";

            return (
              <div key={impact.id} className="space-y-4 p-6">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div className="flex items-start gap-3">
                    <span className="mt-1 text-xs text-zinc-600">
                      {impact.id}
                    </span>

                    <p className="text-sm leading-6 text-zinc-200">
                      {impact.claim}
                    </p>
                  </div>

                  <Badge
                    variant="outline"
                    className={
                      isWeakened
                        ? "border-amber-900/60 bg-amber-950/20 text-amber-400"
                        : isSupported
                          ? "border-emerald-900/60 bg-emerald-950/20 text-emerald-400"
                          : "border-zinc-700 bg-zinc-900 text-zinc-400"
                    }
                  >
                    {impact.status.replace("_", " ")}
                  </Badge>
                </div>

                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-4">
                    <p className="text-[10px] font-medium uppercase tracking-wider text-zinc-500">
                      Previous evidence
                    </p>

                    {impact.oldEvidence.length > 0 ? (
                      <div className="mt-3 flex flex-wrap gap-2">
                        {impact.oldEvidence.map((evidenceId) => (
                          <span
                            key={evidenceId}
                            className="rounded border border-zinc-700 px-2 py-1 text-xs text-zinc-300"
                          >
                            {evidenceId}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <p className="mt-3 text-xs text-zinc-500">
                        No previous evidence linked.
                      </p>
                    )}
                  </div>

                  <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-4">
                    <p className="text-[10px] font-medium uppercase tracking-wider text-zinc-500">
                      Current evidence
                    </p>

                    {impact.newEvidence.length > 0 ? (
                      <div className="mt-3 flex flex-wrap gap-2">
                        {impact.newEvidence.map((evidenceId) => (
                          <span
                            key={evidenceId}
                            className="rounded border border-zinc-700 px-2 py-1 text-xs text-zinc-300"
                          >
                            {evidenceId}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <p className="mt-3 text-xs text-amber-400">
                        No current evidence linked to this claim.
                      </p>
                    )}
                  </div>
                </div>

                <div
                  className={`rounded-md border px-4 py-3 ${
                    isWeakened
                      ? "border-amber-900/30 bg-amber-950/10"
                      : "border-zinc-800 bg-zinc-900/30"
                  }`}
                >
                  <p className="text-xs leading-5 text-zinc-300">
                    {isWeakened
                      ? "The previous evidence is no longer linked to this claim in the new capture. Review the claim before relying on it."
                      : isSupported
                        ? "Evidence remains linked to this claim in the new capture. This does not independently guarantee that the claim is true."
                        : "Review the available evidence before deciding whether this claim remains reliable."}
                  </p>
                </div>
              </div>
            );
          })}

          {demoComparison.claimImpacts.length === 0 && (
            <p className="p-6 text-sm text-zinc-500">
              No claim impacts are available for this comparison.
            </p>
          )}
        </div>
      </Card>


    </div>
  );
}
