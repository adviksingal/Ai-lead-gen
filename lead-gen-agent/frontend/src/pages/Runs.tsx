import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api, timeAgo } from "../api/client";
import { RunStatusBadge } from "../components/RunStatusBadge";
import { NewRunModal } from "../components/NewRunModal";

export function Runs() {
  const [showModal, setShowModal] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["runs"],
    queryFn: () => api.getRuns(100),
    refetchInterval: 5_000,
  });

  const runs = data?.runs ?? [];
  const runningCount = runs.filter((r) => r.status === "running").length;

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-xl font-bold text-white">Runs</h1>
          <p className="text-[13px] text-slate-500 mt-0.5">
            {runs.length} total
            {runningCount > 0 && (
              <span className="ml-2 text-yellow-400">
                · {runningCount} running
              </span>
            )}
          </p>
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

      <div className="bg-[#0f1624] border border-white/[0.07] rounded-xl overflow-hidden">
        {isLoading ? (
          <div className="p-6 space-y-2 animate-pulse">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-14 bg-white/[0.04] rounded-lg" />
            ))}
          </div>
        ) : runs.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <div className="w-14 h-14 rounded-2xl bg-white/[0.04] border border-white/[0.06] flex items-center justify-center mb-4">
              <svg className="w-7 h-7 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <p className="text-slate-400 font-medium">No runs yet</p>
            <p className="text-[12px] text-slate-600 mt-1">Start a run to begin finding leads</p>
            <button
              onClick={() => setShowModal(true)}
              className="mt-5 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold rounded-xl transition-colors"
            >
              Start first run
            </button>
          </div>
        ) : (
          <div className="divide-y divide-white/[0.05]">
            {runs.map((run) => (
              <Link
                key={run.id}
                to={`/runs/${run.id}`}
                className="flex items-center gap-4 px-6 py-4 hover:bg-white/[0.03] transition-colors group"
              >
                {/* Status */}
                <RunStatusBadge status={run.status} />

                {/* Info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="text-[13px] font-semibold text-slate-200">
                      {run.config?.industry ?? "—"}
                    </p>
                    {run.config?.location && (
                      <span className="text-[12px] text-slate-600">· {run.config.location}</span>
                    )}
                  </div>
                  <p className="text-[11px] text-slate-600 truncate mt-0.5">
                    {run.config?.titles?.join(", ") ?? "—"}
                  </p>
                </div>

                {/* Results */}
                <div className="flex items-center gap-3 flex-shrink-0">
                  {run.summary ? (
                    <>
                      <span className="text-[13px] font-medium text-slate-300">
                        {run.summary.total_leads} leads
                      </span>
                      <div className="flex items-center gap-1.5">
                        {run.summary.hot > 0 && (
                          <span className="flex items-center gap-1 text-[12px] text-red-400">
                            <span className="w-1.5 h-1.5 rounded-full bg-red-400 inline-block" />
                            {run.summary.hot}
                          </span>
                        )}
                        {run.summary.warm > 0 && (
                          <span className="flex items-center gap-1 text-[12px] text-amber-400">
                            <span className="w-1.5 h-1.5 rounded-full bg-amber-400 inline-block" />
                            {run.summary.warm}
                          </span>
                        )}
                        {run.summary.cold > 0 && (
                          <span className="flex items-center gap-1 text-[12px] text-blue-400">
                            <span className="w-1.5 h-1.5 rounded-full bg-blue-400 inline-block" />
                            {run.summary.cold}
                          </span>
                        )}
                      </div>
                    </>
                  ) : run.status === "running" ? (
                    <span className="text-[12px] text-yellow-400 animate-pulse">Processing...</span>
                  ) : null}
                </div>

                {/* Time */}
                <span className="text-[11px] text-slate-600 flex-shrink-0 w-16 text-right">
                  {timeAgo(run.created_at)}
                </span>

                {/* Arrow */}
                <svg
                  className="w-4 h-4 text-slate-700 group-hover:text-slate-500 transition-colors flex-shrink-0"
                  fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                </svg>
              </Link>
            ))}
          </div>
        )}
      </div>

      {showModal && <NewRunModal onClose={() => setShowModal(false)} />}
    </div>
  );
}
