import Link from "next/link";
import { RatingBadge } from "@/components/rating-badge";
import { WatchBadge } from "@/components/watch-badge";
import { MovementChip, UniverseChip } from "@/components/universe-chip";
import { parseWatch } from "@/lib/credit";
import { PrintButton } from "./PrintButton";

interface Props {
  data: {
    master: { official_name: string; stock_code: string | null; group: string | null; industry: string | null; aliases: string[] };
    excel: {
      issuer: string;
      group_name: string | null;
      industry: string | null;
      rating_curr: string | null;
      watch_curr: string | null;
      universe_curr_ai: string | null;
      reviewer_final: string | null;
      movement: string | null;
      manager: string | null;
    };
    period: { current: string; previous: string };
  };
}

export function DetailHeader({ data }: Props) {
  const { excel, master, period } = data;
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <Link
          href="/"
          className="inline-block text-xs text-muted-foreground hover:text-foreground transition-colors print:hidden"
        >
          ← 전체 목록
        </Link>
        <PrintButton />
      </div>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <h1 className="text-2xl font-semibold tracking-tight">{excel.issuer}</h1>
        {master.stock_code && (
          <span className="font-mono text-sm text-muted-foreground">
            {master.stock_code}
          </span>
        )}
        {(excel.group_name || master.group) && (
          <span className="text-sm text-muted-foreground">
            {excel.group_name || master.group}
          </span>
        )}
        {(excel.industry || master.industry) && (
          <span className="text-sm text-muted-foreground">
            · {excel.industry || master.industry}
          </span>
        )}
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <RatingBadge rating={excel.rating_curr} size="md" />
        <WatchBadge watch={parseWatch(excel.watch_curr)} size="md" />
        <span className="text-xs text-muted-foreground">·</span>
        <span className="text-xs text-muted-foreground">{period.current} 유니버스</span>
        <UniverseChip value={excel.universe_curr_ai} />
        <MovementChip value={excel.movement} />
        {excel.reviewer_final && (
          <>
            <span className="text-xs text-muted-foreground">·</span>
            <span className="text-xs text-muted-foreground">심사역 확정</span>
            <UniverseChip value={excel.reviewer_final} />
          </>
        )}
        {excel.manager && (
          <>
            <span className="ml-auto text-xs text-muted-foreground">담당</span>
            <span className="text-xs">{excel.manager}</span>
          </>
        )}
      </div>
    </div>
  );
}
