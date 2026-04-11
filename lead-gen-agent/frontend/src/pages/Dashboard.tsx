import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api, timeAgo } from "../api/client";
import { TierBadge } from "../components/TierBadge";
import { RunStatusBadge } from "../components/RunStatusBadge";
import { NewRunModal } from "../components/NewRunModal";

function Stat({ label, value, sub, color = "text-white" }: { label: string; value: string | number; sub?: string; color?: string }) {
  return (
    <div className="bg-[#0f1624] border border-white/[0.07] rounded-xl p-5">
      <p className="text-[11px] text-slate-500 uppercase tracking-wider mb-2">{label}</p>
      <p className={`text-3xl font-bold ${color}`}>{value}</p>
      {sub && <p className="text-[11px] text-slate-600 mt-1">{sub}</p>}
    </div>
  );
}

function EmptyState({ onStart }: { onStart: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 px-8 text-center">
      {/* Illustration */}
      <div className="relative mb-8">
        <div className="w-20 h-20 rounded-2xl bg-indigo-600/10 border border-indigo-500/20 flex items-center justify-center mx-auto">
          <svg className="w-9 h-9 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
        </div>
        {/* Floating dots */}
        <div className="absolute -top-2 -right-2 w-4 h-4 rounded-full bg-red-500/30 border border-red-500/40" />
        <div className="absolute -bottom-1 -left-3 w-3 h-3 rounded-full bg-amber-500/30 border border-amber-500/40" />
      </div>

      <h2 className="text-xl font-bold text-white mb-2">Find your next best customers</h2>
      <p className="text-slate-500 text-sm max-w-sm leading-relaxed mb-8">
        LeadGen AI automatically discovers B2B leads, enriches them with company data,
        scores them against your ICP, and writes personalised cold emails.
      </p>

      <button
        onClick={onStart}
        className="flex items-center gap-2 px-6 py-3 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold rounded-xl transition-colors shadow-xl shadow-indigo-900/40 text-sm"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
        </svg>
        Start your first run
      </button>

      {/* Feature pills */}
      <div className="flex flex-wrap justify-center gap-2 mt-8">
        {["Auto-discovery", "AI enrichment", "ICP scoring", "Personalised emails", "CSV export"].map((f) => (
          <span key={f} className="px-3 py-1 text-xs text-slate-500 bg-white/[0.03] border border-white/[0.06] rounded-full">
            {f}
          </span>
        ))}
      </div>
    </div>
  );
}

export function Dashboard() {
  const [showModal, setShowModal] = useState(false);

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ["stats"],
    queryFn: api.getStats,
    refetchInterval: 15_000,
  });

  const { data: runsData, isLoading: runsLoading } = useQuery({
    queryKey: ["runs"],
    queryFn: () => api.getRuns(8),
    refetchInterval: 8_000,
  });

  const runs = runsData?.runs ?? [];
  const hasData = (stats?.total_leads ?? 0) > 0;
  const hasRunning = runs.some((r) => r.status === "running");

  return (
    <div className="p-8 max-w-6xl">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-xl font-bold text-white">Dashboard</h1>
          {hasRunning && (
            <p className="text-sm text-yellow-400 mt-0.5 flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-yellow-400 animate-pulse inline-block" />
              {runs.filter(r => r.status === "running").length} run{runs.filter(r => r.status === "running").length > 1 ? "s" : ""} in progress
            </p>
          )}
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold rounded-xl transition-colors shadow-lg shadow-indigo-900/30"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          New Run
        </button>
      </div>

      {/* Empty state */}
      {!statsLoading && !hasData && runs.length === 0 && (
        <EmptyState onStart={() => setShowModal(true)} />
      )}

      {/* Stats (shown when there's data) */}
      {hasData && (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
            {statsLoading ? (
              [...Array(4)].map((_, i) => (
                <div key={i} className="bg-[#0f1624] border border-white/[0.07] rounded-xl h-24 animate-pulse" />
              ))
            ) : (
              <>
                <Stat label="Total Leads" value={stats?.total_leads ?? 0} sub={`across ${stats?.total_runs ?? 0} runs`} />
                <Stat label="Hot Leads" value={stats?.hot_leads ?? 0} sub={`${stats?.warm_leads ?? 0} warm · ${stats?.cold_leads ?? 0} cold`} color="text-red-400" />
                <Stat label="With Email" value={stats?.leads_with_email ?? 0} sub={`${stats?.leads_with_verified_email ?? 0} SMTP verified`} color="text-green-400" />
                <Stat label="Avg ICP Score" value={stats?.average_score != null ? stats.average_score : "—"} sub={`${stats?.leads_with_outreach ?? 0} with outreach draft`} color="text-indigo-400" />
              </>
            )}
          </div>

          {/* Tier bar */}
          {stats && stats.total_leads > 0 && (
            <div className="bg-[#0f1624] border border-white/[0.07] rounded-xl p-5 mb-6">
              <p className="text-[11px] text-slate-500 uppercase tracking-wider mb-3">Lead pipeline</p>
              <div className="flex gap-0.5 h-2 rounded-full overflow-hidden mb-3">
                {stats.hot_leads > 0 && (
                  <div className="bg-red-500 rounded-l-full" style={{ width: `${(stats.hot_leads / stats.total_leads) * 100}%` }} />
                )}
                {stats.warm_leads > 0 && (
                  <div className="bg-amber-500" style={{ width: `${(stats.warm_leads / stats.total_leads) * 100}%` }} />
                )}
                {stats.cold_leads > 0 && (
                  <div className="bg-blue-500 rounded-r-full" style={{ width: `${(stats.cold_leads / stats.total_leads) * 100}%` }} />
                )}
              </div>
              <div className="flex gap-5 text-[12px] text-slate-500">
                <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-red-500 inline-block" /> {stats.hot_leads} Hot</span>
                <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-amber-500 inline-block" /> {stats.warm_leads} Warm</span>
                <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-blue-500 inline-block" /> {stats.cold_leads} Cold</span>
              </div>
            </div>
          )}
        </>
      )}

      {/* Recent runs */}
      {(hasData || runs.length > 0) && (
        <div className="bg-[#0f1624] border border-white/[0.07] rounded-xl overflow-hidden">
          <div className="flex items-center justify-between px-5 py-4 border-b border-white/[0.06]">
            <p className="text-[13px] font-semibold text-white">Recent Runs</p>
            <Link to="/runs" className="text-[12px] text-indigo-400 hover:text-indigo-300 transition-colors">
              View all →
            </Link>
          </div>

          {runsLoading ? (
            <div className="p-5 space-y-2 animate-pulse">
              {[...Array(3)].map((_, i) => <div key={i} className="h-10 bg-white/[0.04] rounded-lg" />)}
            </div>
          ) : (
            <div className="divide-y divide-white/[0.05]">
              {runs.map((run) => (
                <Link
                  key={run.id}
                  to={`/runs/${run.id}`}
                  className="flex items-center gap-4 px-5 py-3.5 hover:bg-white/[0.03] transition-colors group"
                >
                  <RunStatusBadge status={run.status} />
                  <div className="flex-1 min-w-0">
                    <p className="text-[13px] font-medium text-slate-200 truncate">
                      {run.config?.industry ?? "—"}
                      {run.config?.location && <span className="text-slate-500 font-normal"> · {run.config.location}</span>}
                    </p>
                    <p className="text-[11px] text-slate-600 truncate">
                      {run.config?.titles?.slice(0, 2).join(", ")}
                    </p>
                  </div>
                  {run.summary ? (
                    <div className="flex items-center gap-2">
                      <span className="text-[13px] font-medium text-slate-300">{run.summary.total_leads} leads</span>
                      <TierBadge tier="Hot" showDot={false} />
                      <span className="text-[12px] text-red-400">{run.summary.hot}</span>
                    </div>
                  ) : run.status === "running" ? (
                    <span className="text-[12px] text-yellow-400 animate-pulse">Processing...</span>
                  ) : null}
                  <span className="text-[11px] text-slate-600 flex-shrink-0">{timeAgo(run.created_at)}</span>
                  <svg className="w-4 h-4 text-slate-700 group-hover:text-slate-500 transition-colors flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                  </svg>
                </Link>
              ))}
            </div>
          )}
        </div>
      )}

      {showModal && <NewRunModal onClose={() => setShowModal(false)} />}
    </div>
  );
}
