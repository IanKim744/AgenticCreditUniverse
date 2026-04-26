import { cn } from "@/lib/utils";

const STYLE: Record<string, { color: string }> = {
  O: { color: "var(--watch-positive)" },
  "△": { color: "var(--rating-bbb)" },
  X: { color: "var(--watch-negative)" },
};

export function UniverseChip({
  value,
  className,
}: {
  value?: string | null;
  className?: string;
}) {
  if (!value) {
    return <span className="text-xs text-muted-foreground">—</span>;
  }
  const s = STYLE[value] ?? { color: "var(--muted-foreground)" };
  return (
    <span
      className={cn(
        "inline-flex items-center justify-center rounded-md w-6 h-6 text-sm font-medium tabular-nums",
        className,
      )}
      style={{
        backgroundColor: `color-mix(in oklab, ${s.color} 14%, transparent)`,
        border: `1px solid color-mix(in oklab, ${s.color} 28%, transparent)`,
        color: s.color,
      }}
    >
      {value}
    </span>
  );
}

export function MovementChip({ value }: { value?: string | null }) {
  if (!value || value === "") {
    return <span className="text-xs text-muted-foreground">—</span>;
  }
  let color = "var(--muted-foreground)";
  if (value === "▲") color = "var(--watch-positive)";
  else if (value === "▽" || value === "▼") color = "var(--watch-negative)";
  return (
    <span className="inline-flex items-center text-sm tabular-nums" style={{ color }}>
      {value}
    </span>
  );
}
