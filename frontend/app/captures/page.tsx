import { Archive } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { CaptureBrowser } from "@/components/captures/capture-browser";
import { captures } from "@/lib/mock-data";

export default function CapturesPage() {
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

          <Badge
            variant="outline"
            className="w-fit border-zinc-800 bg-zinc-950 px-3 py-1.5 text-zinc-400"
          >
            {captures.length} captures
          </Badge>
        </div>
      </section>

      <CaptureBrowser captures={captures} />
    </div>
  );
}