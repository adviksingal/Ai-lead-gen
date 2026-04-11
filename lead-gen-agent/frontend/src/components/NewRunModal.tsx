import { useState, type FormEvent } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";

interface Props {
  onClose: () => void;
}

type Step = 1 | 2;

export function NewRunModal({ onClose }: Props) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [step, setStep] = useState<Step>(1);

  // Step 1
  const [industry, setIndustry] = useState("B2B SaaS");
  const [titlesRaw, setTitlesRaw] = useState("VP of Sales, Head of Sales, CRO");
  const [location, setLocation] = useState("UK");

  // Step 2
  const [keywordsRaw, setKeywordsRaw] = useState("");
  const [limit, setLimit] = useState(25);
  const [senderName, setSenderName] = useState("Alex");
  const [senderCompany, setSenderCompany] = useState("");
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

  const handleNext = (e: FormEvent) => {
    e.preventDefault();
    setStep(2);
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const titles = titlesRaw.split(",").map((t) => t.trim()).filter(Boolean);
    const keywords = keywordsRaw.split(",").map((k) => k.trim()).filter(Boolean);
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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
      <div className="bg-[#0f1624] border border-white/[0.1] rounded-2xl shadow-2xl w-full max-w-md mx-4">
        {/* Header */}
        <div className="flex items-center justify-between px-6 pt-6 pb-4">
          <div>
            <h2 className="text-base font-semibold text-white">
              {step === 1 ? "Who are you looking for?" : "Run settings"}
            </h2>
            <div className="flex items-center gap-2 mt-2">
              {[1, 2].map((s) => (
                <div
                  key={s}
                  className={`h-1 rounded-full transition-all ${
                    s === step ? "w-8 bg-indigo-500" : s < step ? "w-4 bg-indigo-700" : "w-4 bg-white/10"
                  }`}
                />
              ))}
              <span className="text-[11px] text-slate-600 ml-1">Step {step} of 2</span>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 flex items-center justify-center rounded-lg text-slate-500 hover:text-slate-300 hover:bg-white/[0.06] transition-colors"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="mx-6 h-px bg-white/[0.06] mb-5" />

        {/* Step 1 */}
        {step === 1 && (
          <form onSubmit={handleNext} className="px-6 pb-6 space-y-4">
            <div>
              <label className="block text-[11px] font-medium text-slate-400 uppercase tracking-wider mb-2">
                Industry
              </label>
              <input
                type="text"
                value={industry}
                onChange={(e) => setIndustry(e.target.value)}
                placeholder="e.g. B2B SaaS, Fintech, Healthcare IT"
                required
                className="w-full bg-white/[0.04] border border-white/[0.08] rounded-lg px-3.5 py-2.5 text-[13px] text-white placeholder-slate-600 focus:outline-none focus:border-indigo-500/60 focus:bg-white/[0.06] transition-all"
              />
            </div>

            <div>
              <label className="block text-[11px] font-medium text-slate-400 uppercase tracking-wider mb-2">
                Target job titles <span className="text-slate-600 normal-case">(comma-separated)</span>
              </label>
              <input
                type="text"
                value={titlesRaw}
                onChange={(e) => setTitlesRaw(e.target.value)}
                placeholder="VP Sales, Head of Sales, CRO, Sales Director"
                required
                className="w-full bg-white/[0.04] border border-white/[0.08] rounded-lg px-3.5 py-2.5 text-[13px] text-white placeholder-slate-600 focus:outline-none focus:border-indigo-500/60 focus:bg-white/[0.06] transition-all"
              />
              {titlesRaw && (
                <div className="flex flex-wrap gap-1.5 mt-2">
                  {titlesRaw.split(",").map((t) => t.trim()).filter(Boolean).map((t) => (
                    <span key={t} className="px-2 py-0.5 text-[11px] bg-indigo-600/20 text-indigo-300 rounded-md border border-indigo-500/20">
                      {t}
                    </span>
                  ))}
                </div>
              )}
            </div>

            <div>
              <label className="block text-[11px] font-medium text-slate-400 uppercase tracking-wider mb-2">
                Location <span className="text-slate-600 normal-case">(optional)</span>
              </label>
              <input
                type="text"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                placeholder="UK, USA, EMEA, London..."
                className="w-full bg-white/[0.04] border border-white/[0.08] rounded-lg px-3.5 py-2.5 text-[13px] text-white placeholder-slate-600 focus:outline-none focus:border-indigo-500/60 focus:bg-white/[0.06] transition-all"
              />
            </div>

            <button
              type="submit"
              className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-[13px] font-semibold rounded-lg transition-colors shadow-lg shadow-indigo-900/30 mt-2"
            >
              Continue →
            </button>
          </form>
        )}

        {/* Step 2 */}
        {step === 2 && (
          <form onSubmit={handleSubmit} className="px-6 pb-6 space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-[11px] font-medium text-slate-400 uppercase tracking-wider mb-2">
                  Lead limit
                </label>
                <input
                  type="number"
                  value={limit}
                  onChange={(e) => setLimit(Math.min(100, Math.max(1, Number(e.target.value))))}
                  min={1} max={100}
                  className="w-full bg-white/[0.04] border border-white/[0.08] rounded-lg px-3.5 py-2.5 text-[13px] text-white focus:outline-none focus:border-indigo-500/60 transition-all"
                />
              </div>
              <div>
                <label className="block text-[11px] font-medium text-slate-400 uppercase tracking-wider mb-2">
                  Your name
                </label>
                <input
                  type="text"
                  value={senderName}
                  onChange={(e) => setSenderName(e.target.value)}
                  placeholder="Alex"
                  className="w-full bg-white/[0.04] border border-white/[0.08] rounded-lg px-3.5 py-2.5 text-[13px] text-white placeholder-slate-600 focus:outline-none focus:border-indigo-500/60 transition-all"
                />
              </div>
            </div>

            <div>
              <label className="block text-[11px] font-medium text-slate-400 uppercase tracking-wider mb-2">
                Your company <span className="text-slate-600 normal-case">(for email personalisation)</span>
              </label>
              <input
                type="text"
                value={senderCompany}
                onChange={(e) => setSenderCompany(e.target.value)}
                placeholder="Acme Inc"
                className="w-full bg-white/[0.04] border border-white/[0.08] rounded-lg px-3.5 py-2.5 text-[13px] text-white placeholder-slate-600 focus:outline-none focus:border-indigo-500/60 transition-all"
              />
            </div>

            <div>
              <label className="block text-[11px] font-medium text-slate-400 uppercase tracking-wider mb-2">
                Keywords <span className="text-slate-600 normal-case">(optional)</span>
              </label>
              <input
                type="text"
                value={keywordsRaw}
                onChange={(e) => setKeywordsRaw(e.target.value)}
                placeholder="Series A, revenue operations, outbound..."
                className="w-full bg-white/[0.04] border border-white/[0.08] rounded-lg px-3.5 py-2.5 text-[13px] text-white placeholder-slate-600 focus:outline-none focus:border-indigo-500/60 transition-all"
              />
            </div>

            <label className="flex items-center gap-3 cursor-pointer group py-1">
              <input
                type="checkbox"
                checked={skipOutreach}
                onChange={(e) => setSkipOutreach(e.target.checked)}
                className="w-4 h-4 rounded border-white/20 bg-white/[0.04] text-indigo-600 focus:ring-indigo-500"
              />
              <span className="text-[13px] text-slate-400">Skip outreach email generation</span>
            </label>

            {mutation.isError && (
              <p className="text-[12px] text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
                {(mutation.error as Error).message}
              </p>
            )}

            {/* Summary */}
            <div className="bg-white/[0.03] border border-white/[0.06] rounded-lg px-4 py-3 text-[12px] text-slate-400 space-y-1">
              <p><span className="text-slate-300">Industry:</span> {industry}</p>
              <p><span className="text-slate-300">Titles:</span> {titlesRaw}</p>
              {location && <p><span className="text-slate-300">Location:</span> {location}</p>}
              <p><span className="text-slate-300">Leads:</span> up to {limit}</p>
            </div>

            <div className="flex gap-2 pt-1">
              <button
                type="button"
                onClick={() => setStep(1)}
                className="flex-1 py-2.5 text-[13px] font-medium text-slate-400 bg-white/[0.04] hover:bg-white/[0.08] rounded-lg border border-white/[0.06] transition-colors"
              >
                ← Back
              </button>
              <button
                type="submit"
                disabled={mutation.isPending}
                className="flex-[2] py-2.5 text-[13px] font-semibold text-white bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg transition-colors shadow-lg shadow-indigo-900/30 flex items-center justify-center gap-2"
              >
                {mutation.isPending ? (
                  <>
                    <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                    Starting...
                  </>
                ) : (
                  "Start finding leads"
                )}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
