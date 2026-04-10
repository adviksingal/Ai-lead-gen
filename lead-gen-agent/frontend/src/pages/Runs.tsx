import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api, timeAgo } from "../api/client";
import { RunStatusBadge } from "../components/RunStatusBadge";
import { TierBadge } from "../components/TierBadge";
import { NewRunModal } from "../components/NewRunModal";

export function Runs() {
  const [showModal, setShowModal] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["runs"],
    queryFn: () => api.getRuns(100),
    refetchInterval: 5_000,
  });

  const runs = data?.runs ?? [];
  const hasRunning = runs.some((r) => r.status === "running");

  return (
    <div className="p-8">
      <div className="flex items-start justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white">Runs</h1>
          <p className="text-sm text-slate-500 mt-1">
            {runs.length} total run{runs.length !== 1 ? "s" : ""}
            {hasRunning && (
              <span className="ml-2 text-yellow-400">· {runs.filter(r => r.status === "running").length} running</span>
            )}
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

      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
        {isLoading ? (
          <div className="p-6 space-y-3 animate-pulse">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-12 bg-slate-800 rounded-lg" />
            ))}
          </div>
        ) : runs.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20">
            <div className="w-14 h-14 rounded-full bg-slate-800 flex items-center justify-center mb-4">
              <svg className="w-7 h-7 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
            </div>
            <p className="text-slate-400 font-medium">No runs yet</p>
            <p className="text-sm text-slate-600 mt-1">Start your first lead generation run</p>
            <button
              onClick={() => setShowModal(true)}
              className="mt-4 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg transition-colors"
            >
              Start Run
            </button>
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-800">
                <th className="px-5 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Industry</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Titles</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Location</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Status</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Results</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Started</th>
                <th className="px-5 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {runs.map((run) => (
                <tr key={run.id} className="hover:bg-slate-800/40 transition-colors group">
                  <td className="px-5 py-4">
                    <span className="text-sm font-medium text-slate-200">{run.config?.industry ?? "—"}</span>
                  </td>
                  <td className="px-5 py-4 max-w-[220px]">
                    <span className="text-sm text-slate-400 truncate block">
                      {run.config?.titles?.slice(0, 2).join(", ") ?? "—"}
                      {(run.config?.titles?.length ?? 0) > 2 && (
                        <span className="text-slate-600"> +{run.config.titles.length - 2}</span>
                      )}
                    </span>
                  </td>
                  <td className="px-5 py-4 text-sm text-slate-400">
                    {run.config?.location || <span className="text-slate-600">—</span>}
                  </td>
                  <td className="px-5 py-4">
                    <RunStatusBadge status={run.status} />
                  </td>
                  <td className="px-5 py-4">
                    {run.summary ? (
                      <div className="flex items-center gap-2 text-sm">
                        <span className="text-slate-300 font-medium">{run.summary.total_leads}</span>
                        <div className="flex gap-1">
                          {run.summary.hot > 0 && <TierBadge tier="Hot" />}
                          {run.summary.warm > 0 && <TierBadge tier="Warm" />}
                        </div>
                      </div>
                    ) : run.status === "running" ? (
                      <span className="text-xs text-yellow-400 animate-pulse">Processing...</span>
                    ) : (
                      <span className="text-slate-600">—</span>
                    )}
                  </td>
                  <td className="px-5 py-4 text-xs text-slate-500">{timeAgo(run.created_at)}</td>
                  <td className="px-5 py-4">
                    <Link
                      to={`/runs/${run.id}`}
                      className="text-xs text-indigo-400 hover:text-indigo-300 transition-colors opacity-0 group-hover:opacity-100"
                    >
                      View leads →
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
