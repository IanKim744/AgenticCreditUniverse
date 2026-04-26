import { cn } from "@/lib/utils";
import { WATCH_COLOR, WATCH_LABEL, type WatchKey } from "@/lib/credit";

type Size = "sm" | "md";

interface Props {
  watch?: WatchKey | null;
  size?: Size;
  className?: string;
}

export function WatchBadge({ watch, size = "sm", className }: Props) {
  if (!watch) return null;
  const color = WATCH_COLOR[watch];
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full font-medium tabular-nums",
        size === "md" ? "px-2.5 py-1 text-sm" : "px-2 py-0.5 text-xs",
        className,
      )}
      style={{
        backgroundColor: `color-mix(in oklab, ${color} 14%, transparent)`,
        border: `1px solid color-mix(in oklab, ${color} 28%, transparent)`,
        color,
      }}
    >
      {WATCH_LABEL[watch]}
    </span>
  );
}
