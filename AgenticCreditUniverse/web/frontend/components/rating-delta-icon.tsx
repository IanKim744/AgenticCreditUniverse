import { ArrowUp, ArrowDown, Minus } from "lucide-react";
import { compareRating, compareWatch } from "@/lib/credit";
import { cn } from "@/lib/utils";

type Size = "sm" | "lg";

const SIZE_CLASS: Record<Size, string> = {
  sm: "h-3 w-3",
  lg: "h-5 w-5",
};

interface Props {
  prev?: string | null;
  curr?: string | null;
  prevWatch?: string | null;
  currWatch?: string | null;
  size?: Size;
  className?: string;
}

/**
 * 등급/전망 변동 인디케이터. 등급 변화가 우선. 등급이 같으면 전망 변화로
 * 방향 결정 (예: 부정적→안정적 = 상향).
 *  - 모두 미상/유지 → null (호출 측에서 fallback 결정)
 */
export function RatingDeltaIcon({
  prev,
  curr,
  prevWatch,
  currWatch,
  size = "sm",
  className,
}: Props) {
  let direction: "up" | "down" | "flat" | null = null;

  if (prev && curr) {
    const cmp = compareRating(prev, curr);
    if (cmp > 0) direction = "up";
    else if (cmp < 0) direction = "down";
    else direction = "flat";
  }

  // 등급이 같거나 미상이면 전망 변화로 방향 결정
  if (direction === null || direction === "flat") {
    if (prevWatch && currWatch) {
      const wcmp = compareWatch(prevWatch, currWatch);
      if (wcmp > 0) direction = "up";
      else if (wcmp < 0) direction = "down";
      else direction = direction ?? "flat";
    }
  }

  if (direction === null) return null;
  if (direction === "up") {
    return (
      <ArrowUp
        aria-label="상향"
        className={cn(SIZE_CLASS[size], className)}
        style={{ color: "var(--watch-positive)" }}
      />
    );
  }
  if (direction === "down") {
    return (
      <ArrowDown
        aria-label="하향"
        className={cn(SIZE_CLASS[size], className)}
        style={{ color: "var(--watch-negative)" }}
      />
    );
  }
  return (
    <Minus
      aria-label="유지"
      className={cn(SIZE_CLASS[size], "text-muted-foreground", className)}
    />
  );
}
