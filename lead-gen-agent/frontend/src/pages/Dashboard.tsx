import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api, timeAgo } from "../api/client";
import { TierBadge } from "../components/TierBadge";
import { RunStatusBadge } from "../components/RunStatusBadge";
import { NewRunModal } from "../components/NewRunModal";

function StatCard({
  label,
  value,
  sub,
  accent,
}: {
  label: string;
  value: string | number;
  sub?: string;
  accent?: string;
}) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
      <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">{label}</p>
      <p className={`text-3xl font-bold mt-1 ${accent ?? "text-white"}`}>{value ?? "—"}</p>
      {sub && <p className="text-xs text-slate-500 mt-1">{sub}</p>}
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
    queryFn: () => api.getRuns(10),
    refetchInterval: 10_000,
  });

  const recentRuns = runsData?.runs ?? [];
  const hasRunning = recentRuns.some((r) => r.status === "running");

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-start justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white">Dashboard</h1>
          <p className="text-sm text-slate-500 mt-1">
            AI-powered B2B lead generation — find, enrich, score, and email cold leads.
          </p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg transition-colors shadow-lg shadow-indigo-900/30"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          New Run
        </button>
      </div>

      {/* Stats */}
      {statsLoading ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8 animate-pulse">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="bg-slate-900 border border-slate-800 rounded-xl h-24" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <StatCard label="Total Leads" value={stats?.total_leads ?? 0} sub={`${stats?.total_runs ?? 0} runs`} />
          <StatCard
            label="Hot Leads"
            value={stats?.hot_leads ?? 0}
            sub={`${stats?.warm_leads ?? 0} warm · ${stats?.cold_leads ?? 0} cold`}
            accent="text-red-400"
          />
          <StatCard
            label="With Email"
            value={stats?.leads_with_email ?? 0}
            sub={`${stats?.leads_with_verified_email ?? 0} verified`}
            accent="text-green-400"
          />
          <StatCard
            label="Avg Score"
            value={stats?.average_score != null ? `${stats.average_score}` : "—"}
            sub={`${stats?.leads_with_outreach ?? 0} with outreach`}
            accent="text-indigo-400"
          />
        </div>
      )}

      {/* Tier breakdown */}
      {stats && stats.total_leads > 0 && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 mb-6">
          <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-3">Lead Breakdown</p>
          <div className="flex gap-1 rounded-full overflow-hidden h-2">
            {stats.hot_leads > 0 && (
              <div
                className="bg-red-500 rounded-full"
                style={{ width: `${(stats.hot_leads / stats.total_leads) * 100}%` }}
                title={`Hot: ${stats.hot_leads}`}
              />
            )}
            {stats.warm_leads > 0 && (
              <div
                className="bg-amber-500"
                style={{ width: `${(stats.warm_leads / stats.total_leads) * 100}%` }}
                title={`Warm: ${stats.warm_leads}`}
              />
            )}
            {stats.cold_leads > 0 && (
              <div
                className="bg-blue-500 rounded-full"
                style={{ width: `${(stats.cold_leads / stats.total_leads) * 100}%` }}
                title={`Cold: ${stats.cold_leads}`}
              />
            )}
          </div>
          <div className="flex gap-4 mt-2 text-xs text-slate-500">
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-red-500" /> Hot {stats.hot_leads}
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-amber-500" /> Warm {stats.warm_leads}
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-blue-500" /> Cold {stats.cold_leads}
            </span>
          </div>
        </div>
      )}

      {/* Recent runs */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-semibold text-white">Recent Runs</h2>
            {hasRunning && (
              <span className="flex items-center gap-1 text-xs text-yellow-400 bg-yellow-500/10 border border-yellow-500/20 px-2 py-0.5 rounded-full">
                <span className="w-1.5 h-1.5 rounded-full bg-yellow-400 animate-pulse" />
                Live
              </span>
            )}
          </div>
          <Link to="/runs" className="text-xs text-indigo-400 hover:text-indigo-300 transition-colors">
            View all →
          </Link>
        </div>

        {runsLoading ? (
          <div className="p-5 space-y-3 animate-pulse">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-10 bg-slate-800 rounded-lg" />
            ))}
          </div>
        ) : recentRuns.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <div className="w-12 h-12 rounded-full bg-slate-800 flex items-center justify-center mb-3">
              <svg className="w-6 h-6 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <p className="text-sm text-slate-500">No runs yet</p>
            <p className="text-xs text-slate-600 mt-1">Click "New Run" to start finding leads</p>
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-800">
                <th className="px-5 py-3 text-left text-xs font-medium text-slate-500">Industry</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-slate-500">Titles</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-slate-500">Status</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-slate-500">Leads</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-slate-500">Started</th>
                <th className="px-5 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {recentRuns.map((run) => (
                <tr key={run.id} className="hover:bg-slate-800/50 transition-colors">
                  <td className="px-5 py-3 text-sm font-medium text-slate-200">
                    {run.config?.industry ?? "—"}
                  </td>
                  <td className="px-5 py-3 text-sm text-slate-400 max-w-[200px]">
                    <span className="truncate block">
                      {run.config?.titles?.slice(0, 2).join(", ") ?? "—"}
                      {(run.config?.titles?.length ?? 0) > 2 && ` +${run.config.titles.length - 2}`}
                    </span>
                  </td>
                  <td className="px-5 py-3">
                    <RunStatusBadge status={run.status} />
                  </td>
                  <td className="px-5 py-3 text-sm text-slate-400">
                    {run.summary?.total_leads != null ? (
                      <div className="flex items-center gap-2">
                        <span>{run.summary.total_leads}</span>
                        {run.summary.hot > 0 && (
                          <TierBadge tier="Hot" showDot={false} />
                        )}
                      </div>
                    ) : run.status === "running" ? (
                      <span className="text-slate-600">—</span>
                    ) : "—"}
                  </td>
                  <td className="px-5 py-3 text-xs text-slate-500">{timeAgo(run.created_at)}</td>
                  <td className="px-5 py-3">
                    <Link
                      to={`/runs/${run.id}`}
                      className="text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
                    >
                      View →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showModal && <NewRunModal onClose={() => setShowModal(false)} />}
    </div>
  );
}
