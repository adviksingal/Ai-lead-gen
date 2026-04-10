import type { Tier } from "../api/client";

const styles: Record<Tier, string> = {
  Hot: "bg-red-500/15 text-red-400 border border-red-500/25",
  Warm: "bg-amber-500/15 text-amber-400 border border-amber-500/25",
  Cold: "bg-blue-500/15 text-blue-400 border border-blue-500/25",
};

const dots: Record<Tier, string> = {
  Hot: "bg-red-400",
  Warm: "bg-amber-400",
  Cold: "bg-blue-400",
};

interface TierBadgeProps {
  tier: Tier | null | undefined;
  showDot?: boolean;
}

export function TierBadge({ tier, showDot = true }: TierBadgeProps) {
  if (!tier) return <span className="text-slate-600 text-xs">—</span>;
  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium ${styles[tier]}`}>
      {showDot && <span className={`w-1.5 h-1.5 rounded-full ${dots[tier]}`} />}
      {tier}
    </span>
  );
}
