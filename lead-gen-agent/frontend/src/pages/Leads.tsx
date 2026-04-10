import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { TierBadge } from "../components/TierBadge";
import type { Tier } from "../api/client";

const PAGE_SIZE = 100;
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
      await api.exportLeads({
        tier: tierFilter === "All" ? undefined : tierFilter,
        min_score: minScore,
        format: fmt,
      });
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">All Leads</h1>
          <p className="text-sm text-slate-500 mt-1">
            {count} lead{count !== 1 ? "s" : ""} across all runs
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => handleExport("csv")}
            disabled={exporting || leads.length === 0}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-300 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            Export CSV
          </button>
          <button
            onClick={() => handleExport("json")}
            disabled={exporting || leads.length === 0}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-300 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            Export JSON
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 mb-4">
        {(["All", "Hot", "Warm", "Cold"] as TierFilter[]).map((t) => (
          <button
            key={t}
            onClick={() => { setTierFilter(t); setOffset(0); }}
            className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
              tierFilter === t
                ? "bg-slate-700 text-white"
                : "text-slate-500 hover:text-slate-300 hover:bg-slate-800 bg-slate-900 border border-slate-800"
            }`}
          >
            {t}
          </button>
        ))}

        <div className="flex items-center gap-2 ml-auto">
          <span className="text-xs text-slate-500">Min score:</span>
          <select
            value={minScore ?? ""}
            onChange={(e) => {
              setMinScore(e.target.value ? Number(e.target.value) : undefined);
              setOffset(0);
            }}
            className="bg-slate-800 border border-slate-700 text-slate-300 text-xs rounded-lg px-2 py-1.5 focus:outline-none focus:border-indigo-500"
          >
            <option value="">Any</option>
            <option value="40">40+</option>
            <option value="60">60+</option>
            <option value="70">70+</option>
            <option value="80">80+</option>
          </select>
        </div>
      </div>

      {/* Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
        {isLoading ? (
          <div className="p-6 animate-pulse space-y-2">
            {[...Array(8)].map((_, i) => (
              <div key={i} className="h-12 bg-slate-800 rounded" />
            ))}
          </div>
        ) : leads.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <div className="w-12 h-12 rounded-full bg-slate-800 flex items-center justify-center mb-3">
              <svg className="w-6 h-6 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </div>
            <p className="text-slate-400 font-medium">No leads found</p>
            <p className="text-sm text-slate-600 mt-1">Try adjusting your filters or start a new run</p>
          </div>
        ) : (
          <>
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-800">
                  <th className="px-5 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Name</th>
                  <th className="px-5 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Title</th>
                  <th className="px-5 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Company</th>
                  <th className="px-5 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Score</th>
                  <th className="px-5 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Tier</th>
                  <th className="px-5 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Email</th>
                  <th className="px-5 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Location</th>
                  <th className="px-5 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {leads.map((lead) => (
                  <tr key={lead.id} className="hover:bg-slate-800/40 transition-colors group">
                    <td className="px-5 py-3 text-sm font-medium text-slate-200">{lead.name ?? "—"}</td>
                    <td className="px-5 py-3 text-sm text-slate-400 max-w-[160px]">
                      <span className="truncate block">{lead.title ?? "—"}</span>
                    </td>
                    <td className="px-5 py-3 text-sm text-slate-400">{lead.company ?? "—"}</td>
                    <td className="px-5 py-3">
                      <div className="flex items-center gap-1.5">
                        <div className="w-10 h-1.5 bg-slate-800 rounded-full overflow-hidden">
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
                          <span className="truncate max-w-[150px]">{lead.email}</span>
                        </span>
                      ) : (
                        <span className="text-slate-700">—</span>
                      )}
                    </td>
                    <td className="px-5 py-3 text-xs text-slate-500">{lead.location ?? "—"}</td>
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
            {(count > PAGE_SIZE) && (
              <div className="flex items-center justify-between px-5 py-3 border-t border-slate-800">
                <button
                  onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                  disabled={offset === 0}
                  className="text-xs text-slate-400 hover:text-slate-200 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                >
                  ← Previous
                </button>
                <span className="text-xs text-slate-500">
                  {offset + 1}–{Math.min(offset + PAGE_SIZE, count)} of {count}
                </span>
                <button
                  onClick={() => setOffset(offset + PAGE_SIZE)}
                  disabled={offset + PAGE_SIZE >= count}
                  className="text-xs text-slate-400 hover:text-slate-200 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                >
                  Next →
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
