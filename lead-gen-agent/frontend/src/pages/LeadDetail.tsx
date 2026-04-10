import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api, formatDate } from "../api/client";
import { TierBadge } from "../components/TierBadge";

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <button
      onClick={handleCopy}
      className="flex items-center gap-1.5 px-2.5 py-1 text-xs text-slate-400 hover:text-slate-200 bg-slate-800 hover:bg-slate-700 rounded-lg border border-slate-700 transition-colors"
    >
      {copied ? (
        <>
          <svg className="w-3.5 h-3.5 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
          Copied!
        </>
      ) : (
        <>
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
          </svg>
          Copy
        </>
      )}
    </button>
  );
}

function ScoreMeter({ score }: { score: number }) {
  const color =
    score >= 70 ? "bg-red-500" : score >= 40 ? "bg-amber-500" : "bg-blue-500";
  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 h-2 bg-slate-800 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all ${color}`} style={{ width: `${score}%` }} />
      </div>
      <span className="text-lg font-bold text-white w-8 text-right">{score}</span>
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
      <div className="p-8 animate-pulse space-y-4">
        <div className="h-8 w-48 bg-slate-800 rounded" />
        <div className="h-32 bg-slate-800 rounded-xl" />
        <div className="grid grid-cols-2 gap-4">
          <div className="h-64 bg-slate-800 rounded-xl" />
          <div className="h-64 bg-slate-800 rounded-xl" />
        </div>
      </div>
    );
  }

  if (!lead) {
    return (
      <div className="p-8 text-center text-slate-500">
        Lead not found.{" "}
        <Link to="/leads" className="text-indigo-400 hover:underline">
          Back to leads
        </Link>
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
        className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-300 transition-colors mb-6"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
        </svg>
        Back to run
      </Link>

      {/* Profile header */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 mb-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-1">
              <h1 className="text-2xl font-bold text-white">{lead.name}</h1>
              <TierBadge tier={lead.tier} />
            </div>
            <p className="text-slate-400 text-sm">
              {lead.title}
              {lead.company && (
                <>
                  {" "}
                  <span className="text-slate-600">@</span>{" "}
                  <span className="text-slate-300 font-medium">{lead.company}</span>
                </>
              )}
            </p>
            {lead.location && (
              <p className="text-slate-500 text-sm mt-0.5 flex items-center gap-1">
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                {lead.location}
              </p>
            )}
          </div>

          {/* Score */}
          {lead.score != null && (
            <div className="flex-shrink-0 w-48">
              <p className="text-xs text-slate-500 mb-2">ICP Score</p>
              <ScoreMeter score={lead.score} />
              {lead.score_reasoning && (
                <p className="text-xs text-slate-500 mt-2 line-clamp-2">{lead.score_reasoning}</p>
              )}
            </div>
          )}
        </div>

        {/* Links */}
        <div className="flex items-center gap-3 mt-4 pt-4 border-t border-slate-800">
          {lead.email && (
            <div className="flex items-center gap-2 text-sm">
              <svg className="w-4 h-4 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
              <span className={lead.email_verified === 1 ? "text-green-400" : "text-slate-300"}>
                {lead.email}
              </span>
              {lead.email_verified === 1 && (
                <span className="text-xs text-green-400 bg-green-500/10 border border-green-500/20 px-1.5 py-0.5 rounded">verified</span>
              )}
              {lead.email && <CopyButton text={lead.email} />}
            </div>
          )}
          {lead.linkedin_url && (
            <a
              href={lead.linkedin_url}
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-indigo-400 transition-colors"
            >
              <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
                <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
              </svg>
              LinkedIn
            </a>
          )}
          {lead.website && (
            <a
              href={lead.website}
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-300 transition-colors"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
              </svg>
              Website
            </a>
          )}
          {lead.enriched_at && (
            <span className="ml-auto text-xs text-slate-600">
              Enriched {formatDate(lead.enriched_at)}
            </span>
          )}
        </div>
      </div>

      {/* Two-column: Company intel + Outreach email */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Left: company intel */}
        <div className="space-y-4">
          {/* Company summary */}
          {lead.company_summary && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
              <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Company Overview</h2>
              <p className="text-sm text-slate-300 leading-relaxed">{lead.company_summary}</p>
            </div>
          )}

          {/* Pain points */}
          {lead.pain_points?.length > 0 && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
              <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Pain Points</h2>
              <ul className="space-y-2">
                {lead.pain_points.map((p, i) => (
                  <li key={i} className="flex items-start gap-2.5 text-sm text-slate-300">
                    <span className="mt-0.5 w-4 h-4 flex-shrink-0 rounded-full bg-red-500/15 text-red-400 flex items-center justify-center text-[10px] font-bold">
                      !
                    </span>
                    {p}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Tech signals */}
          {lead.tech_signals?.length > 0 && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
              <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Tech Signals</h2>
              <ul className="space-y-2">
                {lead.tech_signals.map((t, i) => (
                  <li key={i} className="flex items-start gap-2.5 text-sm text-slate-300">
                    <span className="mt-0.5 w-4 h-4 flex-shrink-0 rounded-full bg-indigo-500/15 text-indigo-400 flex items-center justify-center">
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

        {/* Right: outreach email */}
        <div>
          {lead.email_subject && lead.email_body ? (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 h-full">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Outreach Email</h2>
                {emailFull && <CopyButton text={emailFull} />}
              </div>

              {/* Email preview */}
              <div className="bg-slate-950 border border-slate-800 rounded-lg p-4">
                <div className="border-b border-slate-800 pb-3 mb-3">
                  <p className="text-xs text-slate-600 mb-0.5">Subject</p>
                  <p className="text-sm font-medium text-slate-200">{lead.email_subject}</p>
                </div>
                {lead.email && (
                  <div className="border-b border-slate-800 pb-3 mb-3">
                    <p className="text-xs text-slate-600 mb-0.5">To</p>
                    <p className="text-sm text-slate-300">
                      {lead.name} &lt;{lead.email}&gt;
                    </p>
                  </div>
                )}
                <div>
                  <p className="text-xs text-slate-600 mb-2">Body</p>
                  <p className="text-sm text-slate-300 whitespace-pre-line leading-relaxed">
                    {lead.email_body}
                  </p>
                </div>
              </div>

              {lead.outreach_at && (
                <p className="text-xs text-slate-600 mt-3">
                  Generated {formatDate(lead.outreach_at)}
                </p>
              )}
            </div>
          ) : (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 h-full flex flex-col items-center justify-center text-center">
              <div className="w-10 h-10 rounded-full bg-slate-800 flex items-center justify-center mb-3">
                <svg className="w-5 h-5 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
              </div>
              <p className="text-sm text-slate-500">No outreach email</p>
              <p className="text-xs text-slate-600 mt-1">
                {lead.tier === "Cold"
                  ? "Cold leads are skipped for outreach"
                  : "Email not yet generated for this lead"}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
