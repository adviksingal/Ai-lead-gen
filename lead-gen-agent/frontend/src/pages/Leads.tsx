import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { LeadCard } from "../components/LeadCard";
import type { Tier } from "../api/client";

const PAGE_SIZE = 50;
type TierFilter = "All" | Tier;

export function Leads() {
  const [tierFilter, setTierFilter] = useState<TierFilter>("All");
  const [minScore, setMinScore] = useState<number | undefined>(undefined);
  const [offset, setOffset] = useState(0);
  const [exporting, setExporting] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["leads", tierFilter, minScore, offset],
    queryFn: () =>
      api.getLeads({
        tier: tierFilter === "All" ? undefined : tierFilter,
        min_score: minScore,
        limit: PAGE_SIZE,
        offset,
      }),
    staleTime: 5_000,
  });

  const leads = data?.leads ?? [];
  const count = data?.count ?? 0;

  const handleExport = async (fmt: "csv" | "json") => {
    setExporting(true);
    try {
      await api.exportLeads({ tier: tierFilter === "All" ? undefined : tierFilter, min_score: minScore, format: fmt });
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-white">All Leads</h1>
          <p className="text-[13px] text-slate-500 mt-0.5">{count} lead{count !== 1 ? "s" : ""} across all runs</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => handleExport("csv")}
            disabled={exporting || leads.length === 0}
            className="flex items-center gap-1.5 px-3 py-1.5 text-[12px] text-slate-300 bg-white/[0.05] hover:bg-white/[0.09] border border-white/[0.08] rounded-lg transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            Export CSV
          </button>
          <button
            onClick={() => handleExport("json")}
            disabled={exporting || leads.length === 0}
            className="flex items-center gap-1.5 px-3 py-1.5 text-[12px] text-slate-300 bg-white/[0.05] hover:bg-white/[0.09] border border-white/[0.08] rounded-lg transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            Export JSON
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-2 mb-5">
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
          </button>
        ))}
        <div className="flex items-center gap-2 ml-auto">
          <span className="text-[12px] text-slate-600">Min score:</span>
          <select
            value={minScore ?? ""}
            onChange={(e) => { setMinScore(e.target.value ? Number(e.target.value) : undefined); setOffset(0); }}
            className="bg-white/[0.05] border border-white/[0.08] text-slate-300 text-[12px] rounded-lg px-2 py-1.5 focus:outline-none focus:border-indigo-500/60"
          >
            <option value="">Any</option>
            <option value="40">40+</option>
            <option value="60">60+</option>
            <option value="70">70+</option>
            <option value="80">80+</option>
          </select>
        </div>
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3 animate-pulse">
          {[...Array(6)].map((_, i) => <div key={i} className="h-44 bg-white/[0.04] rounded-xl" />)}
        </div>
      ) : leads.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <div className="w-12 h-12 rounded-xl bg-white/[0.04] flex items-center justify-center mb-3 border border-white/[0.06]">
            <svg className="w-6 h-6 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </div>
          <p className="text-slate-400 font-medium text-sm">No leads found</p>
          <p className="text-[12px] text-slate-600 mt-1">Try adjusting your filters or start a new run</p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
            {leads.map((lead) => <LeadCard key={lead.id} lead={lead} />)}
          </div>

          {count > PAGE_SIZE && (
            <div className="flex items-center justify-between mt-6">
              <button
                onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                disabled={offset === 0}
                className="text-[12px] text-slate-400 hover:text-slate-200 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              >
                ← Previous
              </button>
              <span className="text-[12px] text-slate-600">
                {offset + 1}–{Math.min(offset + PAGE_SIZE, count)} of {count}
              </span>
              <button
                onClick={() => setOffset(offset + PAGE_SIZE)}
                disabled={offset + PAGE_SIZE >= count}
                className="text-[12px] text-slate-400 hover:text-slate-200 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              >
                Next →
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
