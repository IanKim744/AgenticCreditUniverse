"use client";

import {
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
  type ColumnDef,
  type SortingState,
} from "@tanstack/react-table";
import Link from "next/link";
import { ArrowUp, ArrowDown, ChevronDown, ChevronUp } from "lucide-react";
import { useCallback, useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { RatingBadge } from "@/components/rating-badge";
import { WatchBadge } from "@/components/watch-badge";
import { RatingDeltaIcon } from "@/components/rating-delta-icon";
import { UniverseChip, MovementChip } from "@/components/universe-chip";
import { parseWatch, compareRating } from "@/lib/credit";
import { cn } from "@/lib/utils";
import type { CompanyRow } from "@/lib/api";
import type { ColumnId } from "./types";

interface Props {
  rows: CompanyRow[];
  period: { current: string; previous: string };
  hiddenColumns: Set<ColumnId>;
}

const ROW_MIN_HEIGHT = 44;

export function MatrixTable({ rows, period, hiddenColumns }: Props) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [expanded, setExpanded] = useState<Set<string>>(() => new Set());
  const toggleExpand = useCallback((slug: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(slug)) next.delete(slug);
      else next.add(slug);
      return next;
    });
  }, []);

  const allColumns = useMemo<ColumnDef<CompanyRow>[]>(
    () => [
      {
        id: "issuer",
        header: "발행기관",
        size: 220,
        accessorFn: (r) => r.issuer,
        cell: ({ row }) => {
          const r = row.original;
          if (r.unresolved) {
            return (
              <span className="text-muted-foreground">
                {r.issuer}
                <span className="ml-2 text-[10px] text-muted-foreground/70">
                  데이터 미수집
                </span>
              </span>
            );
          }
          return (
            <Link
              href={`/company/${encodeURIComponent(r.slug)}`}
              className="block min-w-0 truncate font-medium hover:underline"
              title={r.issuer + (r.stock_code ? ` (${r.stock_code})` : "")}
            >
              {r.issuer}
              {r.stock_code && (
                <span className="ml-2 font-mono text-xs text-muted-foreground">
                  {r.stock_code}
                </span>
              )}
            </Link>
          );
        },
        meta: { sticky: true } as never,
      },
      {
        id: "group_name",
        header: "그룹사",
        size: 100,
        accessorFn: (r) => r.group_name,
        cell: ({ getValue }) =>
          (getValue<string | null>() as string | null) || (
            <span className="text-xs text-muted-foreground">—</span>
          ),
      },
      {
        id: "industry",
        header: "업종",
        size: 120,
        accessorFn: (r) => r.industry,
        cell: ({ getValue }) =>
          (getValue<string | null>() as string | null) || (
            <span className="text-xs text-muted-foreground">—</span>
          ),
      },
      {
        id: "watch_industry",
        header: "유의업종",
        size: 80,
        accessorFn: (r) => r.industry_2026,
        cell: ({ getValue }) =>
          getValue<string | null>() === "O" ? (
            <span
              className="inline-flex h-5 w-5 items-center justify-center rounded-full text-sm leading-none"
              style={{
                color: "var(--watch-negative)",
                backgroundColor:
                  "color-mix(in oklab, var(--watch-negative) 12%, transparent)",
              }}
              aria-label="유의업종"
              title="유의업종"
            >
              ○
            </span>
          ) : (
            <span className="text-xs text-muted-foreground">—</span>
          ),
      },
      {
        id: "prev_grade",
        header: `${period.previous} 등급/전망`,
        size: 170,
        accessorFn: (r) => r.rating_prev,
        sortingFn: (a, b) =>
          compareRating(a.original.rating_prev, b.original.rating_prev),
        cell: ({ row }) => (
          <div className="flex items-center gap-1.5">
            <RatingBadge rating={row.original.rating_prev} />
            <WatchBadge watch={parseWatch(row.original.watch_prev)} />
          </div>
        ),
      },
      {
        id: "curr_grade",
        header: `${period.current} 등급/전망`,
        size: 200,
        accessorFn: (r) => r.rating_curr,
        sortingFn: (a, b) =>
          compareRating(a.original.rating_curr, b.original.rating_curr),
        cell: ({ row }) => (
          <div className="flex items-center gap-1.5">
            <RatingBadge rating={row.original.rating_curr} />
            <WatchBadge watch={parseWatch(row.original.watch_curr)} />
            <RatingDeltaIcon
              prev={row.original.rating_prev}
              curr={row.original.rating_curr}
              prevWatch={row.original.watch_prev}
              currWatch={row.original.watch_curr}
            />
          </div>
        ),
        meta: { auto: true } as never,
      },
      {
        id: "universe_prev",
        header: `${period.previous} 유니버스`,
        size: 110,
        accessorFn: (r) => r.universe_prev,
        cell: ({ row }) => <UniverseChip value={row.original.universe_prev} />,
      },
      {
        id: "universe_curr_ai",
        header: `${period.current} 유니버스 (AI)`,
        size: 130,
        accessorFn: (r) => r.universe_curr_ai,
        cell: ({ row }) => <UniverseChip value={row.original.universe_curr_ai} />,
        meta: { auto: true } as never,
      },
      {
        id: "reviewer_final",
        header: "심사역 최종 판단",
        size: 130,
        accessorFn: (r) => r.reviewer_final,
        cell: ({ row }) => <UniverseChip value={row.original.reviewer_final} />,
      },
      {
        id: "movement",
        header: "의견변동",
        size: 90,
        accessorFn: (r) => r.movement,
        cell: ({ row }) => <MovementChip value={row.original.movement} />,
        meta: { auto: true } as never,
      },
      {
        id: "comment_preview",
        header: `${period.current} 코멘트`,
        size: 360,
        accessorFn: (r) => r.comment_preview,
        cell: ({ row }) => {
          const r = row.original;
          const preview = r.comment_preview;
          const full = r.comment_curr;
          if (!preview) return <span className="text-xs text-muted-foreground">—</span>;
          const isExp = expanded.has(r.slug);
          const hasMore = !!full && full.length > (preview.length - 1);
          return (
            <div className="flex w-full items-start gap-1.5 py-1.5">
              <span
                className={cn(
                  "flex-1 text-xs text-muted-foreground leading-relaxed",
                  isExp ? "whitespace-pre-wrap break-words" : "line-clamp-1",
                )}
                title={!isExp ? preview : undefined}
              >
                {isExp ? (full ?? preview) : preview}
              </span>
              {hasMore && (
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    toggleExpand(r.slug);
                  }}
                  aria-label={isExp ? "코멘트 접기" : "코멘트 펼치기"}
                  className="shrink-0 rounded p-0.5 text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
                >
                  {isExp ? (
                    <ChevronUp className="h-3.5 w-3.5" />
                  ) : (
                    <ChevronDown className="h-3.5 w-3.5" />
                  )}
                </button>
              )}
            </div>
          );
        },
        meta: { auto: true } as never,
      },
      {
        id: "manager",
        header: "담당",
        size: 80,
        accessorFn: (r) => r.manager,
        cell: ({ getValue }) =>
          (getValue<string | null>() as string | null) || (
            <span className="text-xs text-muted-foreground">—</span>
          ),
      },
      {
        id: "review",
        header: "검수여부",
        size: 100,
        accessorFn: (r) => r.review_status,
        cell: ({ row }) =>
          row.original.review_status === "done" ? (
            <Badge
              className="font-medium"
              style={{
                backgroundColor:
                  "color-mix(in oklab, var(--state-success) 14%, transparent)",
                border:
                  "1px solid color-mix(in oklab, var(--state-success) 28%, transparent)",
                color: "var(--state-success)",
              }}
            >
              검수완료
            </Badge>
          ) : (
            <Badge variant="outline" className="text-muted-foreground font-medium">
              미검수
            </Badge>
          ),
      },
      {
        id: "last_updated_utc",
        header: "마지막 갱신",
        size: 110,
        accessorFn: (r) => r.last_updated_utc,
        cell: ({ getValue }) => {
          const v = getValue<string | null>();
          if (!v) return <span className="text-xs text-muted-foreground">—</span>;
          return (
            <span className="text-xs text-muted-foreground tabular-nums">
              {relativeTime(v)}
            </span>
          );
        },
      },
    ],
    [period, expanded, toggleExpand],
  );

  const columns = useMemo(
    () => allColumns.filter((c) => !hiddenColumns.has(c.id as ColumnId)),
    [allColumns, hiddenColumns],
  );

  const table = useReactTable({
    data: rows,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  // 22행 규모 → 가상화 미사용. 모든 행 직접 렌더 (sub-pixel/scrollMargin/transform 좌표 변환 버그 차단).
  // 향후 1000+ 행이 되면 virtualization 재도입 검토.
  const totalWidth = columns.reduce((sum, c) => sum + (c.size ?? 100), 0);

  return (
    <div className="border-t" style={{ minWidth: totalWidth, position: "relative" }}>
      {/* Sticky 헤더 — 외부 scroll container 의 top:0 에 안착.
          KPI/Distribution/CountBar 가 위로 스크롤된 뒤 viewport top 에 매트릭스 헤더가 보이게 됨. */}
      <div
        className="sticky top-0 z-20 flex border-b bg-background text-xs font-medium text-muted-foreground"
        style={{ height: 40 }}
      >
          {table.getHeaderGroups().flatMap((hg) =>
            hg.headers.map((h) => {
              const meta = h.column.columnDef.meta as
                | { sticky?: boolean; auto?: boolean }
                | undefined;
              const sortDir = h.column.getIsSorted();
              return (
                <button
                  key={h.id}
                  type="button"
                  onClick={h.column.getToggleSortingHandler()}
                  className={cn(
                    "flex items-center gap-1 px-3 text-left whitespace-nowrap border-r border-b last:border-r-0",
                    "hover:text-foreground transition-colors cursor-pointer",
                    meta?.sticky && "sticky left-0 z-10 bg-background",
                    meta?.auto && "bg-muted/40",
                  )}
                  style={{ width: h.column.getSize(), height: 40 }}
                >
                  {flexRender(h.column.columnDef.header, h.getContext())}
                  {sortDir === "asc" && <ArrowUp className="h-3 w-3" />}
                  {sortDir === "desc" && <ArrowDown className="h-3 w-3" />}
                </button>
              );
            }),
          )}
        </div>

        {/* Body — 모든 행을 직접 렌더 (가상화 없음). 자연 흐름 → 위치 계산 버그 0. */}
        <div>
          {table.getRowModel().rows.map((row) => {
            const r = row.original;
            return (
              <div
                key={row.id}
                className={cn(
                  "group flex items-stretch border-b text-sm",
                  "transition-colors hover:bg-row-hover",
                  r.unresolved && "opacity-60",
                )}
                style={{ minHeight: ROW_MIN_HEIGHT }}
              >
                {row.getVisibleCells().map((c) => {
                  const meta = c.column.columnDef.meta as
                    | { sticky?: boolean; auto?: boolean }
                    | undefined;
                  return (
                    <div
                      key={c.id}
                      className={cn(
                        "flex items-center px-3 border-r last:border-r-0 transition-colors",
                        meta?.sticky && "sticky left-0 z-10 bg-background group-hover:bg-row-hover",
                        meta?.auto && "bg-muted/40 group-hover:bg-muted/60",
                      )}
                      style={{ width: c.column.getSize() }}
                    >
                      {flexRender(c.column.columnDef.cell, c.getContext())}
                    </div>
                  );
                })}
              </div>
            );
          })}
        </div>
    </div>
  );
}

function relativeTime(iso: string): string {
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return "—";
  const diff = Math.floor((Date.now() - t) / 1000);
  if (diff < 60) return "방금";
  if (diff < 3600) return `${Math.floor(diff / 60)}분 전`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}시간 전`;
  return `${Math.floor(diff / 86400)}일 전`;
}
