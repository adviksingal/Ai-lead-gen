import { useState, type FormEvent } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";

interface Props {
  onClose: () => void;
}

export function NewRunModal({ onClose }: Props) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [industry, setIndustry] = useState("B2B SaaS");
  const [titlesRaw, setTitlesRaw] = useState("VP of Sales, Head of Sales, CRO");
  const [location, setLocation] = useState("UK");
  const [keywordsRaw, setKeywordsRaw] = useState("");
  const [limit, setLimit] = useState(25);
  const [senderName, setSenderName] = useState("Alex");
  const [senderCompany, setSenderCompany] = useState("YourCo");
  const [skipOutreach, setSkipOutreach] = useState(false);

  const mutation = useMutation({
    mutationFn: api.startRun,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["runs"] });
      queryClient.invalidateQueries({ queryKey: ["stats"] });
      onClose();
      navigate(`/runs/${data.run_id}`);
    },
  });

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const titles = titlesRaw.split(",").map((t) => t.trim()).filter(Boolean);
    const keywords = keywordsRaw.split(",").map((k) => k.trim()).filter(Boolean);
    if (!industry || titles.length === 0) return;

    mutation.mutate({
      industry,
      titles,
      location,
      keywords,
      limit,
      sender_name: senderName,
      sender_company: senderCompany,
      skip_outreach: skipOutreach,
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-slate-900 border border-slate-700 rounded-xl shadow-2xl w-full max-w-lg mx-4 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800">
          <div>
            <h2 className="text-base font-semibold text-white">Start New Run</h2>
            <p className="text-xs text-slate-500 mt-0.5">Configure your lead generation criteria</p>
          </div>
          <button
            onClick={onClose}
            className="text-slate-500 hover:text-slate-300 transition-colors p-1 rounded-lg hover:bg-slate-800"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {/* Industry */}
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">
              Industry <span className="text-red-400">*</span>
            </label>
            <input
              type="text"
              value={industry}
              onChange={(e) => setIndustry(e.target.value)}
              placeholder="e.g. B2B SaaS, Fintech, Healthcare"
              required
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors"
            />
          </div>

          {/* Titles */}
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">
              Target Titles <span className="text-red-400">*</span>
              <span className="text-slate-600 font-normal ml-1">(comma-separated)</span>
            </label>
            <input
              type="text"
              value={titlesRaw}
              onChange={(e) => setTitlesRaw(e.target.value)}
              placeholder="VP of Sales, Head of Sales, CRO"
              required
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors"
            />
          </div>

          {/* Location + Limit */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1.5">Location</label>
              <input
                type="text"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                placeholder="UK, USA, EMEA..."
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1.5">
                Lead Limit <span className="text-slate-600 font-normal">(1–100)</span>
              </label>
              <input
                type="number"
                value={limit}
                onChange={(e) => setLimit(Math.min(100, Math.max(1, Number(e.target.value))))}
                min={1}
                max={100}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors"
              />
            </div>
          </div>

          {/* Keywords */}
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">
              Keywords <span className="text-slate-600 font-normal">(optional, comma-separated)</span>
            </label>
            <input
              type="text"
              value={keywordsRaw}
              onChange={(e) => setKeywordsRaw(e.target.value)}
              placeholder="Series A, revenue operations, outbound..."
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors"
            />
          </div>

          {/* Sender info */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1.5">Your Name</label>
              <input
                type="text"
                value={senderName}
                onChange={(e) => setSenderName(e.target.value)}
                placeholder="Alex"
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1.5">Your Company</label>
              <input
                type="text"
                value={senderCompany}
                onChange={(e) => setSenderCompany(e.target.value)}
                placeholder="Acme Inc"
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors"
              />
            </div>
          </div>

          {/* Skip outreach */}
          <label className="flex items-center gap-2.5 cursor-pointer group">
            <input
              type="checkbox"
              checked={skipOutreach}
              onChange={(e) => setSkipOutreach(e.target.checked)}
              className="w-4 h-4 rounded border-slate-600 bg-slate-800 text-indigo-600 focus:ring-indigo-500"
            />
            <span className="text-sm text-slate-400 group-hover:text-slate-300 transition-colors">
              Skip outreach email generation
            </span>
          </label>

          {/* Error */}
          {mutation.isError && (
            <p className="text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
              {(mutation.error as Error).message}
            </p>
          )}

          {/* Actions */}
          <div className="flex gap-3 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 text-sm font-medium text-slate-400 bg-slate-800 rounded-lg hover:bg-slate-700 hover:text-slate-200 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={mutation.isPending}
              className="flex-1 px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-lg shadow-indigo-900/30"
            >
              {mutation.isPending ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Starting...
                </span>
              ) : (
                "Start Run"
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
