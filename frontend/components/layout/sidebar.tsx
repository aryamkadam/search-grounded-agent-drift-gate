"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  Archive,
  GitCompareArrows,
  Play,
  ShieldCheck,
  Terminal,
} from "lucide-react";

const navigation = [
  {
    label: "Overview",
    href: "/",
    icon: Activity,
  },
  {
    label: "Captures",
    href: "/captures",
    icon: Archive,
  },
  {
    label: "Compare",
    href: "/compare",
    icon: GitCompareArrows,
  },
  {
    label: "Replay",
    href: "/replay",
    icon: Play,
  },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden h-screen w-64 shrink-0 border-r border-zinc-800 bg-[#09090b] md:flex md:flex-col">
      {/* Brand */}
      <div className="flex h-16 items-center border-b border-zinc-800 px-5">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-zinc-100 text-zinc-950">
            <ShieldCheck className="h-4 w-4" />
          </div>

          <div>
            <p className="text-sm font-semibold text-zinc-100">
              Drift Gate
            </p>
            <p className="text-[11px] text-zinc-500">
              Search evidence control
            </p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 px-3 py-5">
        <p className="mb-3 px-2 text-[10px] font-medium uppercase tracking-[0.16em] text-zinc-600">
          Workspace
        </p>

        {navigation.map((item) => {
          const Icon = item.icon;

          const isActive =
            item.href === "/"
              ? pathname === "/"
              : pathname.startsWith(item.href);

          return (
            <Link
              key={item.href}
              href={item.href}
              className={[
                "flex items-center gap-3 rounded-md px-3 py-2.5 text-sm transition-colors",
                isActive
                  ? "bg-zinc-800 text-zinc-100"
                  : "text-zinc-500 hover:bg-zinc-900 hover:text-zinc-200",
              ].join(" ")}
            >
              <Icon className="h-4 w-4" />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>

      {/* Bottom system status */}
      <div className="border-t border-zinc-800 p-4">
        <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-3">
          <div className="mb-2 flex items-center gap-2">
            <Terminal className="h-3.5 w-3.5 text-zinc-500" />
            <span className="text-xs font-medium text-zinc-300">
              System
            </span>
          </div>

          <div className="flex items-center gap-2">
            <span className="h-1.5 w-1.5 rounded-full bg-green-500" />
            <span className="text-[11px] text-zinc-500">
              Backend integration pending
            </span>
          </div>
        </div>
      </div>
    </aside>
  );
}