import { GitBranch, Search } from "lucide-react";
import { Badge } from "@/components/ui/badge";

export function Topbar() {
  return (
    <header className="flex h-16 items-center justify-between border-b border-zinc-800 bg-[#09090b]/95 px-6 backdrop-blur">
      <div className="flex items-center gap-3">
        <div className="relative hidden w-72 sm:block">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-600" />

          <input
            placeholder="Search captures..."
            className="h-9 w-full rounded-md border border-zinc-800 bg-zinc-950 pl-9 pr-16 text-sm text-zinc-200 outline-none placeholder:text-zinc-600 focus:border-zinc-600"
          />

          <kbd className="absolute right-2 top-1/2 -translate-y-1/2 rounded border border-zinc-800 bg-zinc-900 px-1.5 py-0.5 text-[10px] text-zinc-500">
            ⌘ K
          </kbd>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <Badge
          variant="outline"
          className="gap-1.5 border-zinc-800 bg-zinc-950 text-zinc-400"
        >
          <span className="h-1.5 w-1.5 rounded-full bg-green-500" />
          API Online
        </Badge>

        <div className="hidden items-center gap-2 border-l border-zinc-800 pl-3 text-xs text-zinc-500 sm:flex">
          <GitBranch className="h-3.5 w-3.5" />
          feature/frontend
        </div>
      </div>
    </header>
  );
}