import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api, timeAgo } from "../api/client";
import { TierBadge } from "../components/TierBadge";
import { RunStatusBadge } from "../components/RunStatusBadge";
import type { Tier } from "../api/client";

const PAGE_SIZE = 50;
type TierFilter = "All" | Tier;

export function RunDetail() {
  const { id } = useParams<{ id: string }>();
  const [tierFilter, setTierFilter] = useState<TierFilter>("All");
  const [offset, setOffset] = useState(0);
  const [exporting, setExporting] = useState(false);

  const { data: run, isLoading: runLoading } = useQuery({
    queryKey: ["run", id],
    queryFn: () => api.getRun(id!),
    refetchInterval: (query) => query.state.data?.status === "running" ? 3_000 : false,
    enabled: !!id,
  });

  const { data: leadsData, isLoading: leadsLoading } = useQuery({
    queryKey: ["run-leads", id, tierFilter, offset],
    queryFn: () =>
      api.getRunLeads(id!, {
        limit: PAGE_SIZE,
        offset,
        tier: tierFilter === "All" ? undefined : tierFilter,
      }),
    enabled: !!id && run?.status === "done",
  });

  const leads = leadsData?.leads ?? [];
  const total = leadsData?.total ?? 0;

  const handleExport = async (fmt: "csv" | "json") => {
    if (!id) return;
    setExporting(true);
    try {
      await api.exportLeads({ run_id: id, format: fmt });
    } finally {
      setExporting(false);
    }
  };

  if (runLoading) {
    return (
      <div className="p-8 animate-pulse space-y-4">
        <div className="h-8 w-48 bg-slate-800 rounded" />
        <div className="h-24 bg-slate-800 rounded-xl" />
        <div className="h-64 bg-slate-800 rounded-xl" />
      </div>
    );
  }

  if (!run) {
    return (
      <div className="p-8 text-center text-slate-500">
        Run not found.{" "}
        <Link to="/runs" className="text-indigo-400 hover:underline">
          Back to runs
        </Link>
      </div>
    );
  }

  const tierCounts = run.summary;

  return (
    <div className="p-8">
      {/* Back + header */}
      <div className="mb-6">
        <Link
          to="/runs"
          className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-300 transition-colors mb-4"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
          </svg>
          All Runs
        </Link>

        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-3 mb-1">
              <h1 className="text-2xl font-bold text-white">{run.config?.industry ?? "Run"}</h1>
              <RunStatusBadge status={run.status} />
            </div>
            <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-slate-500">
              {run.config?.titles?.length > 0 && (
                <span>{run.config.titles.join(" · ")}</span>
              )}
              {run.config?.location && <span>📍 {run.config.location}</span>}
              {run.config?.limit && <span>Limit: {run.config.limit}</span>}
              <span className="text-slate-600">{timeAgo(run.created_at)}</span>
            </div>
          </div>

          {run.status === "done" && (
            <div className="flex items-center gap-2 flex-shrink-0">
              <button
                onClick={() => handleExport("csv")}
                disabled={exporting}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-300 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg transition-colors disabled:opacity-50"
              >
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                CSV
              </button>
              <button
                onClick={() => handleExport("json")}
                disabled={exporting}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-300 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg transition-colors disabled:opacity-50"
              >
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                JSON
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Summary cards */}
      {tierCounts && (
        <div className="grid grid-cols-4 gap-3 mb-6">
          {[
            { label: "Total", value: tierCounts.total_leads, color: "text-white" },
            { label: "Hot", value: tierCounts.hot, color: "text-red-400" },
            { label: "Warm", value: tierCounts.warm, color: "text-amber-400" },
            { label: "Cold", value: tierCounts.cold, color: "text-blue-400" },
          ].map((s) => (
            <div key={s.label} className="bg-slate-900 border border-slate-800 rounded-xl p-4 text-center">
              <p className={`text-2xl font-bold ${s.color}`}>{s.value}</p>
              <p className="text-xs text-slate-500 mt-0.5">{s.label}</p>
            </div>
          ))}
        </div>
      )}

      {/* Running state */}
      {run.status === "running" && (
        <div className="bg-yellow-500/5 border border-yellow-500/20 rounded-xl p-6 text-center mb-6">
          <div className="flex items-center justify-center gap-3 mb-2">
            <svg className="w-5 h-5 text-yellow-400 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            <p className="text-yellow-400 font-medium">Run in progress...</p>
          </div>
          <p className="text-sm text-slate-500">Discovering, enriching and scoring leads. This page auto-refreshes every 3 seconds.</p>
        </div>
      )}

      {/* Failed state */}
      {run.status === "failed" && (
        <div className="bg-red-500/5 border border-red-500/20 rounded-xl p-6 text-center mb-6">
          <p className="text-red-400 font-medium">Run failed</p>
          <p className="text-sm text-slate-500 mt-1">Check your API keys and search provider configuration.</p>
        </div>
      )}

      {/* Leads table */}
      {run.status === "done" && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
          {/* Tier filter tabs */}
          <div className="flex items-center gap-1 px-4 py-3 border-b border-slate-800">
            {(["All", "Hot", "Warm", "Cold"] as TierFilter[]).map((t) => (
              <button
                key={t}
                onClick={() => { setTierFilter(t); setOffset(0); }}
                className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
                  tierFilter === t
                    ? "bg-slate-700 text-white"
                    : "text-slate-500 hover:text-slate-300 hover:bg-slate-800"
                }`}
              >
                {t}
                {t !== "All" && tierCounts && (
                  <span className="ml-1.5 text-slate-500">
                    {t === "Hot" ? tierCounts.hot : t === "Warm" ? tierCounts.warm : tierCounts.cold}
                  </span>
                )}
              </button>
            ))}
            <span className="ml-auto text-xs text-slate-600">{total} leads</span>
          </div>

          {leadsLoading ? (
            <div className="p-6 animate-pulse space-y-2">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="h-12 bg-slate-800 rounded" />
              ))}
            </div>
          ) : leads.length === 0 ? (
            <div className="py-12 text-center text-slate-500 text-sm">No leads for this filter.</div>
          ) : (
            <>
              <table className="w-full">
                <thead>
                  <tr className="border-b border-slate-800">
                    <th className="px-5 py-3 text-left text-xs font-medium text-slate-500">Name</th>
                    <th className="px-5 py-3 text-left text-xs font-medium text-slate-500">Title</th>
                    <th className="px-5 py-3 text-left text-xs font-medium text-slate-500">Company</th>
                    <th className="px-5 py-3 text-left text-xs font-medium text-slate-500">Score</th>
                    <th className="px-5 py-3 text-left text-xs font-medium text-slate-500">Tier</th>
                    <th className="px-5 py-3 text-left text-xs font-medium text-slate-500">Email</th>
                    <th className="px-5 py-3" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800">
                  {leads.map((lead) => (
                    <tr key={lead.id} className="hover:bg-slate-800/40 transition-colors group">
                      <td className="px-5 py-3 text-sm font-medium text-slate-200">
                        {lead.name ?? "—"}
                      </td>
                      <td className="px-5 py-3 text-sm text-slate-400 max-w-[180px]">
                        <span className="truncate block">{lead.title ?? "—"}</span>
                      </td>
                      <td className="px-5 py-3 text-sm text-slate-400">{lead.company ?? "—"}</td>
                      <td className="px-5 py-3">
                        <div className="flex items-center gap-1.5">
                          <div className="w-12 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-indigo-500 rounded-full"
                              style={{ width: `${lead.score ?? 0}%` }}
                            />
                          </div>
                          <span className="text-xs text-slate-400 font-medium">{lead.score ?? "—"}</span>
                        </div>
                      </td>
                      <td className="px-5 py-3">
                        <TierBadge tier={lead.tier} />
                      </td>
                      <td className="px-5 py-3 text-xs text-slate-500">
                        {lead.email ? (
                          <span className="flex items-center gap-1">
                            {lead.email_verified === 1 && (
                              <svg className="w-3 h-3 text-green-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                              </svg>
                            )}
                            <span className="truncate max-w-[160px]">{lead.email}</span>
                          </span>
                        ) : (
                          <span className="text-slate-700">—</span>
                        )}
                      </td>
                      <td className="px-5 py-3">
                        <Link
                          to={`/leads/${lead.id}`}
                          className="text-xs text-indigo-400 hover:text-indigo-300 transition-colors opacity-0 group-hover:opacity-100"
                        >
                          View →
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {/* Pagination */}
              {(leadsData?.has_more || offset > 0) && (
                <div className="flex items-center justify-between px-5 py-3 border-t border-slate-800">
                  <button
                    onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                    disabled={offset === 0}
                    className="text-xs text-slate-400 hover:text-slate-200 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                  >
                    ← Previous
                  </button>
                  <span className="text-xs text-slate-500">
                    {offset + 1}–{Math.min(offset + PAGE_SIZE, total)} of {total}
                  </span>
                  <button
                    onClick={() => setOffset(offset + PAGE_SIZE)}
                    disabled={!leadsData?.has_more}
                    className="text-xs text-slate-400 hover:text-slate-200 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                  >
                    Next →
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
