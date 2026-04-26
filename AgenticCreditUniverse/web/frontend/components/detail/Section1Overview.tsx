import { ArrowRight } from "lucide-react";
import { RatingBadge } from "@/components/rating-badge";
import { WatchBadge } from "@/components/watch-badge";
import { UniverseChip } from "@/components/universe-chip";
import { RatingDeltaIcon } from "@/components/rating-delta-icon";
import { parseWatch } from "@/lib/credit";

interface Props {
  id: string;
  data: {
    period: { current: string; previous: string };
    excel: {
      rating_prev: string | null;
      watch_prev: string | null;
      rating_curr: string | null;
      watch_curr: string | null;
      universe_prev: string | null;
      universe_curr_ai: string | null;
    };
    comment?: { judgment_stage1: string; judgment_stage1_reason: string } | null;
    stage2?: {
      final: string;
      stage1: string;
      prior_25_2h: string | null;
      movement: string;
      adjusted: boolean;
      rationale: string;
    } | null;
    inversion?: { rationale: string; high_grade_company: string; low_grade_company: string } | null;
  };
}

export function Section1Overview({ id, data }: Props) {
  const { period, excel, comment, stage2, inversion } = data;
  return (
    <section id={id} className="space-y-4 scroll-mt-32">
      <h2 className="text-lg font-semibold">개요</h2>
      <div className="grid grid-cols-1 sm:grid-cols-[1fr_auto_1fr] gap-3 items-stretch">
        <PeriodCard
          label={`전기 ${period.previous}`}
          rating={excel.rating_prev}
          watch={excel.watch_prev}
          universe={excel.universe_prev}
        />
        <div className="flex items-center justify-center px-1">
          <ArrowRight
            aria-label="당기"
            className="h-5 w-5 text-muted-foreground"
          />
        </div>
        <PeriodCard
          label={`당기 ${period.current}`}
          rating={excel.rating_curr}
          watch={excel.watch_curr}
          universe={excel.universe_curr_ai}
          compareTo={excel.rating_prev}
          compareWatchTo={excel.watch_prev}
          highlight
        />
      </div>
      {(comment || stage2) && (
        <div
          className="rounded-lg border bg-card p-4"
          style={{ boxShadow: "var(--shadow-card)" }}
        >
          <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground mb-2">
            AI 판단 요약
          </div>
          <div className="space-y-2 text-sm">
            {comment && (
              <p>
                <span className="text-muted-foreground">1차 종목별 판단:</span>{" "}
                <UniverseChip value={comment.judgment_stage1} />{" "}
                <span className="ml-2 text-muted-foreground">
                  {comment.judgment_stage1_reason}
                </span>
              </p>
            )}
            {stage2 && (
              <p>
                <span className="text-muted-foreground">2차 풀 검수:</span>{" "}
                <UniverseChip value={stage2.final} />{" "}
                <span className="ml-2 text-muted-foreground">
                  {labelMovement(stage2.movement)}
                </span>
                {stage2.adjusted && (
                  <span className="ml-2 inline-flex items-center gap-0.5 rounded-md bg-amber-500/10 px-1.5 py-0.5 text-[10px] font-medium text-amber-700">
                    ⚙ 가드레일 적용
                  </span>
                )}
              </p>
            )}
            {stage2?.rationale && (
              <p className="text-sm text-muted-foreground leading-relaxed">
                {stage2.rationale}
              </p>
            )}
          </div>
        </div>
      )}
      {inversion && (
        <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-3 text-sm">
          <div className="font-medium text-amber-800">등급 역전 케이스</div>
          <p className="mt-1 text-xs text-amber-700">{inversion.rationale}</p>
        </div>
      )}
    </section>
  );
}

function PeriodCard({
  label,
  rating,
  watch,
  universe,
  compareTo,
  compareWatchTo,
  highlight = false,
}: {
  label: string;
  rating: string | null;
  watch: string | null;
  universe: string | null;
  compareTo?: string | null;
  compareWatchTo?: string | null;
  highlight?: boolean;
}) {
  return (
    <div
      className="rounded-lg border bg-card p-4 flex flex-col justify-between min-h-[96px]"
      style={{
        boxShadow: highlight ? "var(--shadow-card)" : undefined,
        borderColor: highlight ? "var(--primary)" : undefined,
      }}
    >
      <div className="text-xs font-medium text-muted-foreground">{label}</div>
      <div className="flex flex-wrap items-center gap-2 mt-2">
        <RatingBadge rating={rating} size="md" />
        <WatchBadge watch={parseWatch(watch)} size="md" />
        {(compareTo || compareWatchTo) && (
          <RatingDeltaIcon
            prev={compareTo}
            curr={rating}
            prevWatch={compareWatchTo}
            currWatch={watch}
            size="lg"
          />
        )}
        <span className="text-xs text-muted-foreground">·</span>
        <UniverseChip value={universe} />
      </div>
    </div>
  );
}

function labelMovement(m: string): string {
  switch (m) {
    case "stay":
      return "유지";
    case "upgrade":
      return "상향";
    case "downgrade":
      return "하향";
    case "new":
      return "신규";
    default:
      return m;
  }
}
