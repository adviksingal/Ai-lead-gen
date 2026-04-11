import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api, formatDate } from "../api/client";
import { TierBadge } from "../components/TierBadge";

function CopyButton({ text, label = "Copy" }: { text: string; label?: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      onClick={async () => {
        await navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      }}
      className="flex items-center gap-1.5 px-3 py-1.5 text-[12px] text-slate-300 bg-white/[0.05] hover:bg-white/[0.09] border border-white/[0.08] rounded-lg transition-all"
    >
      {copied ? (
        <svg className="w-3.5 h-3.5 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
        </svg>
      ) : (
        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
        </svg>
      )}
      {copied ? "Copied!" : label}
    </button>
  );
}

function ScoreBar({ score }: { score: number }) {
  const color = score >= 70 ? "bg-red-500" : score >= 40 ? "bg-amber-500" : "bg-blue-500";
  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <span className="text-[11px] text-slate-500 uppercase tracking-wider">ICP Score</span>
        <span className="text-2xl font-bold text-white">{score}<span className="text-lg text-slate-600">/100</span></span>
      </div>
      <div className="h-2 bg-white/[0.06] rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all ${color}`} style={{ width: `${score}%` }} />
      </div>
    </div>
  );
}

export function LeadDetail() {
  const { id } = useParams<{ id: string }>();

  const { data: lead, isLoading } = useQuery({
    queryKey: ["lead", id],
    queryFn: () => api.getLead(id!),
    enabled: !!id,
  });

  if (isLoading) {
    return (
      <div className="p-8 animate-pulse space-y-4 max-w-5xl">
        <div className="h-6 w-32 bg-white/[0.06] rounded" />
        <div className="h-36 bg-white/[0.06] rounded-xl" />
        <div className="grid grid-cols-2 gap-4">
          <div className="h-64 bg-white/[0.06] rounded-xl" />
          <div className="h-64 bg-white/[0.06] rounded-xl" />
        </div>
      </div>
    );
  }

  if (!lead) {
    return (
      <div className="p-8 text-center text-slate-500">
        Lead not found. <Link to="/leads" className="text-indigo-400 hover:underline">Back to leads</Link>
      </div>
    );
  }

  const emailFull = lead.email_subject && lead.email_body
    ? `Subject: ${lead.email_subject}\n\n${lead.email_body}`
    : null;

  return (
    <div className="p-8 max-w-5xl">
      {/* Back */}
      <Link
        to={`/runs/${lead.run_id}`}
        className="inline-flex items-center gap-1.5 text-[12px] text-slate-500 hover:text-slate-300 transition-colors mb-6"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
        </svg>
        Back to run
      </Link>

      {/* Profile card */}
      <div className="bg-[#0f1624] border border-white/[0.07] rounded-xl p-6 mb-4">
        <div className="flex items-start justify-between gap-6">
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-1">
              <h1 className="text-xl font-bold text-white">{lead.name}</h1>
              <TierBadge tier={lead.tier} size="md" />
            </div>
            <p className="text-[14px] text-slate-400 mb-0.5">
              {lead.title}
              {lead.company && (
                <span> at <span className="text-slate-200 font-medium">{lead.company}</span></span>
              )}
            </p>
            {lead.location && (
              <p className="text-[13px] text-slate-500 flex items-center gap-1">
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                </svg>
                {lead.location}
              </p>
            )}

            {/* Links */}
            <div className="flex items-center gap-3 mt-4">
              {lead.email && (
                <div className="flex items-center gap-2">
                  <span className={`text-[13px] font-medium ${lead.email_verified === 1 ? "text-green-400" : "text-slate-300"}`}>
                    {lead.email}
                  </span>
                  {lead.email_verified === 1 && (
                    <span className="text-[10px] text-green-400 bg-green-500/10 border border-green-500/20 px-1.5 py-0.5 rounded">
                      verified
                    </span>
                  )}
                  <CopyButton text={lead.email} label="Copy email" />
                </div>
              )}
              {lead.linkedin_url && (
                <a href={lead.linkedin_url} target="_blank" rel="noreferrer"
                  className="flex items-center gap-1.5 text-[12px] text-slate-500 hover:text-indigo-400 transition-colors">
                  <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
                  </svg>
                  LinkedIn
                </a>
              )}
              {lead.website && (
                <a href={lead.website} target="_blank" rel="noreferrer"
                  className="flex items-center gap-1.5 text-[12px] text-slate-500 hover:text-slate-300 transition-colors">
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
                  </svg>
                  Website
                </a>
              )}
            </div>
          </div>

          {/* Score */}
          {lead.score != null && (
            <div className="flex-shrink-0 w-52 bg-white/[0.03] rounded-xl p-4 border border-white/[0.06]">
              <ScoreBar score={lead.score} />
              {lead.score_reasoning && (
                <p className="text-[11px] text-slate-500 mt-3 leading-relaxed">{lead.score_reasoning}</p>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Two-column: intel + email */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Left column */}
        <div className="space-y-4">
          {lead.company_summary && (
            <div className="bg-[#0f1624] border border-white/[0.07] rounded-xl p-5">
              <p className="text-[11px] text-slate-500 uppercase tracking-wider mb-3">Company</p>
              <p className="text-[13px] text-slate-300 leading-relaxed">{lead.company_summary}</p>
            </div>
          )}
          {lead.pain_points?.length > 0 && (
            <div className="bg-[#0f1624] border border-white/[0.07] rounded-xl p-5">
              <p className="text-[11px] text-slate-500 uppercase tracking-wider mb-3">Pain Points</p>
              <ul className="space-y-2.5">
                {lead.pain_points.map((p, i) => (
                  <li key={i} className="flex items-start gap-2.5 text-[13px] text-slate-300">
                    <span className="mt-0.5 w-4 h-4 flex-shrink-0 rounded-full bg-red-500/10 text-red-400 flex items-center justify-center text-[10px] font-bold border border-red-500/20">!</span>
                    {p}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {lead.tech_signals?.length > 0 && (
            <div className="bg-[#0f1624] border border-white/[0.07] rounded-xl p-5">
              <p className="text-[11px] text-slate-500 uppercase tracking-wider mb-3">Tech Signals</p>
              <ul className="space-y-2.5">
                {lead.tech_signals.map((t, i) => (
                  <li key={i} className="flex items-start gap-2.5 text-[13px] text-slate-300">
                    <span className="mt-0.5 w-4 h-4 flex-shrink-0 rounded-full bg-indigo-500/10 text-indigo-400 flex items-center justify-center border border-indigo-500/20">
                      <svg className="w-2.5 h-2.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                      </svg>
                    </span>
                    {t}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Right: email */}
        <div>
          {lead.email_subject && lead.email_body ? (
            <div className="bg-[#0f1624] border border-white/[0.07] rounded-xl p-5 h-full">
              <div className="flex items-center justify-between mb-4">
                <p className="text-[11px] text-slate-500 uppercase tracking-wider">Outreach Email</p>
                {emailFull && <CopyButton text={emailFull} label="Copy all" />}
              </div>

              <div className="bg-[#080d17] border border-white/[0.06] rounded-xl overflow-hidden">
                {/* Email header bar */}
                <div className="px-4 py-3 border-b border-white/[0.06] space-y-2">
                  <div className="flex items-start gap-2">
                    <span className="text-[11px] text-slate-600 w-14 flex-shrink-0 pt-0.5">Subject</span>
                    <span className="text-[13px] font-medium text-slate-200">{lead.email_subject}</span>
                  </div>
                  {lead.email && (
                    <div className="flex items-center gap-2">
                      <span className="text-[11px] text-slate-600 w-14 flex-shrink-0">To</span>
                      <span className="text-[13px] text-slate-400">{lead.name} &lt;{lead.email}&gt;</span>
                    </div>
                  )}
                </div>
                {/* Email body */}
                <div className="p-4">
                  <p className="text-[13px] text-slate-300 whitespace-pre-line leading-relaxed">
                    {lead.email_body}
                  </p>
                </div>
              </div>

              {lead.outreach_at && (
                <p className="text-[11px] text-slate-600 mt-3">Generated {formatDate(lead.outreach_at)}</p>
              )}
            </div>
          ) : (
            <div className="bg-[#0f1624] border border-white/[0.07] rounded-xl p-5 flex flex-col items-center justify-center text-center h-full min-h-[200px]">
              <div className="w-10 h-10 rounded-xl bg-white/[0.04] flex items-center justify-center mb-3">
                <svg className="w-5 h-5 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
              </div>
              <p className="text-[13px] text-slate-500">No outreach email</p>
              <p className="text-[11px] text-slate-600 mt-1">
                {lead.tier === "Cold" ? "Cold leads are skipped for outreach" : "Not yet generated"}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
