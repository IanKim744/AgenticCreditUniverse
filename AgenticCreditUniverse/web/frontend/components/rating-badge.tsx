import { cn } from "@/lib/utils";
import { ratingColorVar } from "@/lib/credit";

type Size = "sm" | "md" | "lg";

const SIZE: Record<Size, string> = {
  sm: "px-2 py-0.5 text-xs",
  md: "px-2.5 py-1 text-sm",
  lg: "px-4 py-1.5 text-lg",
};

interface Props {
  rating?: string | null;
  size?: Size;
  className?: string;
}

export function RatingBadge({ rating, size = "sm", className }: Props) {
  if (!rating) {
    return (
      <span className="text-xs text-muted-foreground tabular-nums">—</span>
    );
  }
  const color = ratingColorVar(rating);
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md font-medium tabular-nums",
        SIZE[size],
        className,
      )}
      style={{
        backgroundColor: `color-mix(in oklab, ${color} 14%, transparent)`,
        border: `1px solid color-mix(in oklab, ${color} 28%, transparent)`,
        color,
      }}
    >
      {rating}
    </span>
  );
}
