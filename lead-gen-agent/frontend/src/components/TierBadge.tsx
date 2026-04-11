import type { Tier } from "../api/client";

const styles: Record<Tier, string> = {
  Hot: "bg-red-500/10 text-red-400 border-red-500/20",
  Warm: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  Cold: "bg-blue-500/10 text-blue-400 border-blue-500/20",
};

interface TierBadgeProps {
  tier: Tier | null | undefined;
  showDot?: boolean;
  size?: "sm" | "md";
}

export function TierBadge({ tier, showDot = true, size = "sm" }: TierBadgeProps) {
  if (!tier) return null;
  return (
    <span
      className={`inline-flex items-center gap-1 border rounded-full font-medium ${styles[tier]} ${
        size === "sm" ? "px-1.5 py-0.5 text-[10px]" : "px-2.5 py-1 text-xs"
      }`}
    >
      {showDot && <span className={`w-1 h-1 rounded-full ${tier === "Hot" ? "bg-red-400" : tier === "Warm" ? "bg-amber-400" : "bg-blue-400"}`} />}
      {tier}
    </span>
  );
}
