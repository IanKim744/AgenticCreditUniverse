import { ArrowUp, ArrowDown, Minus } from "lucide-react";
import { cn } from "@/lib/utils";

interface Props {
  label: string;
  value?: string | number;
  unit?: string;
  delta?: number;
  deltaLabel?: string;
  hint?: string;
  className?: string;
  children?: React.ReactNode;
}

export function KpiCard({
  label,
  value,
  unit,
  delta,
  deltaLabel,
  hint,
  className,
  children,
}: Props) {
  const deltaColor =
    delta == null
      ? "var(--muted-foreground)"
      : delta > 0
        ? "var(--watch-positive)"
        : delta < 0
          ? "var(--watch-negative)"
          : "var(--muted-foreground)";

  const DeltaIcon =
    delta == null ? Minus : delta > 0 ? ArrowUp : delta < 0 ? ArrowDown : Minus;

  return (
    <div
      className={cn(
        "rounded-lg border bg-card p-4 flex flex-col gap-2 h-full min-h-[100px]",
        className,
      )}
      style={{ boxShadow: "var(--shadow-card)" }}
    >
      <div className="text-xs font-medium text-muted-foreground">{label}</div>
      <div className="flex flex-col gap-1.5 flex-1 justify-center">
        {value !== undefined && (
          <div className="flex items-baseline gap-1.5">
            <span className="text-2xl font-semibold tracking-tight tabular-nums leading-none">
              {value}
            </span>
            {unit && (
              <span className="text-xs text-muted-foreground">{unit}</span>
            )}
          </div>
        )}
        {children && <div className="flex items-center gap-3 text-sm">{children}</div>}
        {delta !== undefined && (
          <div
            className="flex items-center gap-1 text-xs tabular-nums"
            style={{ color: deltaColor }}
          >
            <DeltaIcon className="h-3 w-3" />
            <span>{Math.abs(delta).toFixed(1)}%</span>
            {deltaLabel && (
              <span className="text-muted-foreground">{deltaLabel}</span>
            )}
          </div>
        )}
        {hint && delta === undefined && (
          <div className="text-xs text-muted-foreground">{hint}</div>
        )}
      </div>
    </div>
  );
}
