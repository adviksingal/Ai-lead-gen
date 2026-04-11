import { Link } from "react-router-dom";
import { useState } from "react";
import type { Lead } from "../api/client";
import { TierBadge } from "./TierBadge";

function ScoreRing({ score }: { score: number }) {
  const r = 20;
  const circ = 2 * Math.PI * r;
  const fill = (score / 100) * circ;
  const color = score >= 70 ? "#ef4444" : score >= 40 ? "#f59e0b" : "#3b82f6";

  return (
    <div className="relative w-14 h-14 flex-shrink-0">
      <svg className="w-14 h-14 -rotate-90" viewBox="0 0 48 48">
        <circle cx="24" cy="24" r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="4" />
        <circle
          cx="24" cy="24" r={r}
          fill="none"
          stroke={color}
          strokeWidth="4"
          strokeLinecap="round"
          strokeDasharray={`${fill} ${circ}`}
          style={{ transition: "stroke-dasharray 0.6s ease" }}
        />
      </svg>
      <span className="absolute inset-0 flex items-center justify-center text-[13px] font-bold text-white">
        {score}
      </span>
    </div>
  );
}

function CopyButton({ text, label = "Copy" }: { text: string; label?: string }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <button
      onClick={handleCopy}
      className="px-2 py-1 text-[11px] rounded-md bg-white/[0.05] hover:bg-white/[0.1] text-slate-400 hover:text-slate-200 transition-all border border-white/[0.06] flex items-center gap-1"
    >
      {copied ? (
        <svg className="w-3 h-3 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
        </svg>
      ) : (
        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
        </svg>
      )}
      {copied ? "Copied!" : label}
    </button>
  );
}

interface LeadCardProps {
  lead: Lead;
}

export function LeadCard({ lead }: LeadCardProps) {
  const tierBorder = {
    Hot: "border-red-500/20 hover:border-red-500/40",
    Warm: "border-amber-500/20 hover:border-amber-500/40",
    Cold: "border-blue-500/10 hover:border-blue-500/20",
  }[lead.tier] ?? "border-white/[0.08] hover:border-white/[0.15]";

  const emailBody = lead.email_subject && lead.email_body
    ? `Subject: ${lead.email_subject}\n\n${lead.email_body}`
    : null;

  return (
    <Link
      to={`/leads/${lead.id}`}
      className={`block bg-[#0f1624] border ${tierBorder} rounded-xl p-4 transition-all hover:bg-[#141c2e] group`}
    >
      {/* Top row: score + name/title */}
      <div className="flex items-start gap-3 mb-3">
        {lead.score != null && <ScoreRing score={lead.score} />}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <p className="text-[14px] font-semibold text-white truncate">{lead.name ?? "—"}</p>
            <TierBadge tier={lead.tier} showDot={false} />
          </div>
          <p className="text-[12px] text-slate-400 truncate">{lead.title}</p>
          <p className="text-[12px] text-slate-500 truncate">
            <span className="text-slate-300">{lead.company}</span>
            {lead.location && <span> · {lead.location}</span>}
          </p>
        </div>
      </div>

      {/* Pain points snippet */}
      {lead.pain_points?.length > 0 && (
        <div className="mb-3">
          <p className="text-[11px] text-slate-600 mb-1 uppercase tracking-wider">Pain points</p>
          <p className="text-[12px] text-slate-400 leading-relaxed line-clamp-2">
            {lead.pain_points.slice(0, 2).join(" · ")}
          </p>
        </div>
      )}

      {/* Bottom: email + actions */}
      <div
        className="flex items-center gap-2 pt-3 border-t border-white/[0.05]"
        onClick={(e) => e.preventDefault()}
      >
        {lead.email ? (
          <>
            <div className="flex items-center gap-1.5 flex-1 min-w-0">
              {lead.email_verified === 1 ? (
                <svg className="w-3.5 h-3.5 text-green-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              ) : (
                <svg className="w-3.5 h-3.5 text-slate-600 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
              )}
              <span className="text-[11px] text-slate-400 truncate">{lead.email}</span>
            </div>
            <CopyButton text={lead.email} label="Email" />
            {emailBody && <CopyButton text={emailBody} label="Email draft" />}
          </>
        ) : (
          <span className="text-[11px] text-slate-600">No email found</span>
        )}
        {lead.linkedin_url && (
          <a
            href={lead.linkedin_url}
            target="_blank"
            rel="noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="p-1 rounded-md text-slate-600 hover:text-indigo-400 transition-colors"
            title="LinkedIn"
          >
            <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="currentColor">
              <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
            </svg>
          </a>
        )}
      </div>
    </Link>
  );
}
