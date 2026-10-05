import {
  AlertTriangle,
  ArrowUpRight,
  CheckCircle2,
  GitCompareArrows,
  Search,
  ShieldAlert,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";

const stats = [
  {
    label: "Total Captures",
    value: "128",
    description: "Search observations recorded",
    icon: Search,
  },
  {
    label: "Comparisons",
    value: "42",
    description: "Capture pairs analyzed",
    icon: GitCompareArrows,
  },
  {
    label: "Drift Events",
    value: "7",
    description: "Material changes detected",
    icon: AlertTriangle,
  },
  {
    label: "Gate Failures",
    value: "3",
    description: "Runs requiring review",
    icon: ShieldAlert,
  },
];

const recentRuns = [
  {
    query: "best AI coding tools for developers in 2026",
    status: "DRIFT",
    claims: 2,
    time: "2 min ago",
  },
  {
    query: "OpenAI latest model",
    status: "PASS",
    claims: 0,
    time: "18 min ago",
  },
  {
    query: "best laptops for developers",
    status: "DRIFT",
    claims: 1,
    time: "1 hr ago",
  },
];

export default function Home() {
  return (
    <div className="space-y-8">
      {/* Page heading */}
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
            className="w-fit border-zinc-800 bg-zinc-950 px-3 py-1.5 text-zinc-400"
          >
            ● Demo environment
          </Badge>
        </div>
      </section>

      {/* Stats */}
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

      {/* Main content */}
      <section className="grid gap-6 xl:grid-cols-[1.6fr_1fr]">
        {/* Recent runs */}
        <Card className="border-zinc-800 bg-[#111113]">
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-zinc-200">
                Recent runs
              </h2>
              <p className="mt-1 text-xs text-zinc-500">
                Latest search observations and drift checks
              </p>
            </div>

            <button className="flex items-center gap-1 text-xs text-zinc-500 transition hover:text-zinc-200">
              View all
              <ArrowUpRight className="h-3 w-3" />
            </button>
          </CardHeader>

          <CardContent className="p-0">
            <div className="divide-y divide-zinc-800">
              {recentRuns.map((run) => (
                <div
                  key={run.query}
                  className="flex flex-col gap-3 px-6 py-4 transition hover:bg-zinc-950/60 sm:flex-row sm:items-center sm:justify-between"
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm text-zinc-200">
                      {run.query}
                    </p>

                    <p className="mt-1 text-xs text-zinc-600">
                      {run.time}
                    </p>
                  </div>

                  <div className="flex items-center gap-4">
                    <span className="text-xs text-zinc-600">
                      {run.claims} claims affected
                    </span>

                    <Badge
                      variant="outline"
                      className={
                        run.status === "DRIFT"
                          ? "border-red-900/60 bg-red-950/20 text-red-400"
                          : "border-green-900/60 bg-green-950/20 text-green-400"
                      }
                    >
                      {run.status}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Latest drift */}
        <Card className="border-red-900/40 bg-[#111113]">
          <CardHeader>
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-red-400" />

              <h2 className="text-sm font-semibold text-zinc-200">
                Latest drift
              </h2>
            </div>
          </CardHeader>

          <CardContent>
            <div className="rounded-lg border border-red-900/40 bg-red-950/10 p-4">
              <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-red-400">
                Material drift detected
              </p>

              <p className="mt-3 text-sm font-medium text-zinc-200">
                best AI coding tools for developers in 2026
              </p>

              <div className="mt-4 grid grid-cols-2 gap-3">
                <div>
                  <p className="text-2xl font-semibold">2</p>
                  <p className="text-xs text-zinc-600">
                    claims affected
                  </p>
                </div>

                <div>
                  <p className="text-2xl font-semibold">4</p>
                  <p className="text-xs text-zinc-600">
                    evidence changes
                  </p>
                </div>
              </div>

              <button className="mt-5 flex w-full items-center justify-center gap-2 rounded-md border border-zinc-700 bg-zinc-900 px-3 py-2 text-xs font-medium text-zinc-200 transition hover:bg-zinc-800">
                <GitCompareArrows className="h-3.5 w-3.5" />
                View comparison
              </button>
            </div>

            <div className="mt-4 flex items-center gap-2 text-xs text-zinc-600">
              <CheckCircle2 className="h-3.5 w-3.5 text-green-500" />
              Capture pipeline operational
            </div>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}