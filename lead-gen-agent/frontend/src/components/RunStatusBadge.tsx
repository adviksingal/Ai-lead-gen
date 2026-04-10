type Status = "running" | "done" | "failed";

const styles: Record<Status, string> = {
  running: "bg-yellow-500/15 text-yellow-400 border border-yellow-500/25",
  done: "bg-green-500/15 text-green-400 border border-green-500/25",
  failed: "bg-red-500/15 text-red-400 border border-red-500/25",
};

const labels: Record<Status, string> = {
  running: "Running",
  done: "Done",
  failed: "Failed",
};

export function RunStatusBadge({ status }: { status: string }) {
  const s = (status as Status) in styles ? (status as Status) : "failed";
  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium ${styles[s]}`}>
      {s === "running" && (
        <span className="w-1.5 h-1.5 rounded-full bg-yellow-400 animate-pulse" />
      )}
      {s === "done" && (
        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
        </svg>
      )}
      {s === "failed" && (
        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
        </svg>
      )}
      {labels[s]}
    </span>
  );
}
