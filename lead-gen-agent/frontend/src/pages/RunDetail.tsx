import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api, timeAgo } from "../api/client";
import { RunStatusBadge } from "../components/RunStatusBadge";
import { LeadCard } from "../components/LeadCard";
import type { Tier } from "../api/client";

type TierFilter = "All" | Tier;
const PAGE_SIZE = 50;

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
    try { await api.exportLeads({ run_id: id, format: fmt }); }
    finally { setExporting(false); }
  };

  if (runLoading) {
    return (
      <div className="p-8 animate-pulse space-y-4">
        <div className="h-6 w-32 bg-white/[0.06] rounded" />
        <div className="h-24 bg-white/[0.06] rounded-xl" />
      </div>
    );
  }

  if (!run) {
    return (
      <div className="p-8 text-center text-slate-500">
        Run not found. <Link to="/runs" className="text-indigo-400 hover:underline">Back to runs</Link>
      </div>
    );
  }

  const tierCounts = run.summary;

  return (
    <div className="p-8">
      {/* Back */}
      <Link to="/runs" className="inline-flex items-center gap-1.5 text-[12px] text-slate-500 hover:text-slate-300 transition-colors mb-6">
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
        </svg>
        All Runs
      </Link>

      {/* Run header */}
      <div className="bg-[#0f1624] border border-white/[0.07] rounded-xl p-6 mb-4">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-xl font-bold text-white">{run.config?.industry ?? "Run"}</h1>
              <RunStatusBadge status={run.status} />
            </div>
            <div className="flex flex-wrap gap-x-4 gap-y-1 text-[13px] text-slate-500">
              {run.config?.titles?.length > 0 && (
                <span className="flex items-center gap-1">
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                  </svg>
                  {run.config.titles.join(" · ")}
                </span>
              )}
              {run.config?.location && (
                <span className="flex items-center gap-1">
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                  </svg>
                  {run.config.location}
                </span>
              )}
              <span className="text-slate-600">{timeAgo(run.created_at)}</span>
            </div>
          </div>

          {run.status === "done" && (
            <div className="flex items-center gap-2 flex-shrink-0">
              <button
                onClick={() => handleExport("csv")}
                disabled={exporting}
                className="flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium text-slate-300 bg-white/[0.05] hover:bg-white/[0.09] border border-white/[0.08] rounded-lg transition-colors disabled:opacity-50"
              >
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                CSV
              </button>
              <button
                onClick={() => handleExport("json")}
                disabled={exporting}
                className="flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium text-slate-300 bg-white/[0.05] hover:bg-white/[0.09] border border-white/[0.08] rounded-lg transition-colors disabled:opacity-50"
              >
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                JSON
              </button>
            </div>
          )}
        </div>

        {/* Summary stats */}
        {tierCounts && (
          <div className="grid grid-cols-4 gap-3 mt-5 pt-5 border-t border-white/[0.06]">
            {[
              { label: "Total", value: tierCounts.total_leads, color: "text-white" },
              { label: "Hot", value: tierCounts.hot, color: "text-red-400" },
              { label: "Warm", value: tierCounts.warm, color: "text-amber-400" },
              { label: "Cold", value: tierCounts.cold, color: "text-blue-400" },
            ].map((s) => (
              <div key={s.label} className="text-center">
                <p className={`text-2xl font-bold ${s.color}`}>{s.value}</p>
                <p className="text-[11px] text-slate-600 mt-0.5">{s.label}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Running state */}
      {run.status === "running" && (
        <div className="bg-yellow-500/5 border border-yellow-500/20 rounded-xl p-8 text-center mb-4">
          <div className="flex items-center justify-center gap-3 mb-3">
            <svg className="w-5 h-5 text-yellow-400 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            <p className="text-yellow-400 font-semibold">Finding and enriching leads...</p>
          </div>
          <p className="text-[13px] text-slate-500">
            Searching the web · Scraping company sites · Scoring with Claude AI · Writing personalised emails
          </p>
          <p className="text-[11px] text-slate-600 mt-2">This page refreshes automatically every 3 seconds</p>
        </div>
      )}

      {run.status === "failed" && (
        <div className="bg-red-500/5 border border-red-500/20 rounded-xl p-6 text-center mb-4">
          <p className="text-red-400 font-medium">Run failed</p>
          <p className="text-[13px] text-slate-500 mt-1">Check your ANTHROPIC_API_KEY and search provider configuration.</p>
        </div>
      )}

      {/* Leads grid */}
      {run.status === "done" && (
        <>
          {/* Tier filter */}
          <div className="flex items-center gap-1.5 mb-4">
            {(["All", "Hot", "Warm", "Cold"] as TierFilter[]).map((t) => (
              <button
                key={t}
                onClick={() => { setTierFilter(t); setOffset(0); }}
                className={`px-3 py-1.5 text-[12px] font-medium rounded-lg transition-all border ${
                  tierFilter === t
                    ? "bg-white/10 text-white border-white/20"
                    : "text-slate-500 border-transparent hover:text-slate-300 hover:bg-white/[0.04]"
                }`}
              >
                {t}
                {tierCounts && t !== "All" && (
                  <span className={`ml-1.5 ${tierFilter === t ? "text-slate-300" : "text-slate-600"}`}>
                    {t === "Hot" ? tierCounts.hot : t === "Warm" ? tierCounts.warm : tierCounts.cold}
                  </span>
                )}
              </button>
            ))}
            <span className="ml-auto text-[12px] text-slate-600">{total} leads</span>
          </div>

          {leadsLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3 animate-pulse">
              {[...Array(6)].map((_, i) => <div key={i} className="h-44 bg-white/[0.04] rounded-xl" />)}
            </div>
          ) : leads.length === 0 ? (
            <div className="py-16 text-center text-slate-500 text-sm">No leads for this filter.</div>
          ) : (
            <>
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                {leads.map((lead) => <LeadCard key={lead.id} lead={lead} />)}
              </div>

              {(leadsData?.has_more || offset > 0) && (
                <div className="flex items-center justify-between mt-6">
                  <button
                    onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                    disabled={offset === 0}
                    className="text-[12px] text-slate-400 hover:text-slate-200 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                  >
                    ← Previous
                  </button>
                  <span className="text-[12px] text-slate-600">
                    {offset + 1}–{Math.min(offset + PAGE_SIZE, total)} of {total}
                  </span>
                  <button
                    onClick={() => setOffset(offset + PAGE_SIZE)}
                    disabled={!leadsData?.has_more}
                    className="text-[12px] text-slate-400 hover:text-slate-200 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                  >
                    Next →
                  </button>
                </div>
              )}
            </>
          )}
        </>
      )}
    </div>
  );
}
