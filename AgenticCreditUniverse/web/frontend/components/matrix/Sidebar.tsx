"use client";

import { ChevronDown, Search } from "lucide-react";
import { useMemo } from "react";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { CompanyRow } from "@/lib/api";
import { ratingBucket, type RatingBucket } from "@/lib/credit";
import {
  ALL_COLUMNS,
  type ColumnId,
  type Filters,
  type MovementKey,
  type ReviewStatus,
  type Universe,
} from "./types";

// 8tier 라벨 — RatingDistChart 와 동일 단일 출처.
const TIER_LABEL: Record<RatingBucket, string> = {
  "tier-1": "AA- 이상",
  "tier-2": "A+",
  "tier-3": "A0",
  "tier-4": "A-",
  "tier-5": "BBB+",
  "tier-6": "BBB0",
  "tier-7": "BBB-",
  "tier-8": "BB+ 이하",
  nr: "미부여 (NR)",
};
const TIER_ORDER: RatingBucket[] = [
  "tier-1",
  "tier-2",
  "tier-3",
  "tier-4",
  "tier-5",
  "tier-6",
  "tier-7",
  "tier-8",
  "nr",
];

interface Props {
  rows: CompanyRow[];
  filters: Filters;
  onChange: (next: Filters) => void;
}

export function Sidebar({ rows, filters, onChange }: Props) {
  const groups = useMemo(
    () => uniqNonEmpty(rows.map((r) => r.group_name)),
    [rows],
  );
  const industries = useMemo(
    () => uniqNonEmpty(rows.map((r) => r.industry)),
    [rows],
  );
  const managers = useMemo(
    () => uniqNonEmpty(rows.map((r) => r.manager)),
    [rows],
  );
  // 데이터에 실제 존재하는 등급 tier 만 필터에 노출 (count 표시).
  const tierCounts = useMemo(() => {
    const c: Record<RatingBucket, number> = {
      "tier-1": 0, "tier-2": 0, "tier-3": 0, "tier-4": 0,
      "tier-5": 0, "tier-6": 0, "tier-7": 0, "tier-8": 0, nr: 0,
    };
    for (const r of rows) c[ratingBucket(r.rating_curr)]++;
    return c;
  }, [rows]);
  const visibleTiers = TIER_ORDER.filter((t) => tierCounts[t] > 0);

  return (
    <aside className="w-72 shrink-0 border-r bg-background flex flex-col h-full min-h-0">
      <ScrollArea className="flex-1 min-h-0">
        <div className="space-y-3 p-5">
          <div className="space-y-1.5">
            <Label className="text-xs font-medium text-muted-foreground">
              검색
            </Label>
            <div className="relative">
              <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
              <Input
                value={filters.query}
                onChange={(e) =>
                  onChange({ ...filters, query: e.target.value })
                }
                placeholder="발행기관·그룹사"
                className="pl-8"
              />
            </div>
          </div>

          <FilterGroup
            label="검수여부"
            options={[
              { v: "done", label: "검수완료" },
              { v: "none", label: "미검수" },
            ]}
            selected={filters.reviewStatuses}
            onToggle={(v) =>
              onChange({
                ...filters,
                reviewStatuses: toggleSet(filters.reviewStatuses, v as ReviewStatus),
              })
            }
          />

          {visibleTiers.length > 0 && (
            <FilterGroup
              label="당기 등급"
              options={visibleTiers.map((t) => ({
                v: t,
                label: `${TIER_LABEL[t]} (${tierCounts[t]})`,
              }))}
              selected={filters.tiers}
              onToggle={(v) =>
                onChange({
                  ...filters,
                  tiers: toggleSet(filters.tiers, v as RatingBucket),
                })
              }
            />
          )}

          <FilterGroup
            label="당기 유니버스 (AI)"
            options={[
              { v: "O", label: "O" },
              { v: "△", label: "△" },
              { v: "X", label: "X" },
              { v: "—", label: "미판단" },
            ]}
            selected={filters.universes}
            onToggle={(v) =>
              onChange({
                ...filters,
                universes: toggleSet(filters.universes, v as Universe | "—"),
              })
            }
          />

          <FilterGroup
            label="의견 변동"
            options={[
              { v: "up", label: "▲ 상향" },
              { v: "down", label: "▽ 하향" },
              { v: "flat", label: "- 유지" },
            ]}
            selected={filters.movements}
            onToggle={(v) =>
              onChange({
                ...filters,
                movements: toggleSet(filters.movements, v as MovementKey),
              })
            }
          />

          {groups.length > 0 && (
            <FilterGroup
              label="그룹사"
              options={groups.map((g) => ({ v: g, label: g }))}
              selected={filters.groups}
              onToggle={(v) =>
                onChange({ ...filters, groups: toggleSet(filters.groups, v) })
              }
            />
          )}

          {industries.length > 0 && (
            <FilterGroup
              label="업종"
              options={industries.map((g) => ({ v: g, label: g }))}
              selected={filters.industries}
              onToggle={(v) =>
                onChange({
                  ...filters,
                  industries: toggleSet(filters.industries, v),
                })
              }
            />
          )}

          {managers.length > 0 && (
            <FilterGroup
              label="담당"
              options={managers.map((g) => ({ v: g, label: g }))}
              selected={filters.managers}
              onToggle={(v) =>
                onChange({
                  ...filters,
                  managers: toggleSet(filters.managers, v),
                })
              }
            />
          )}

          <ColumnVisibilityGroup
            hidden={filters.hiddenColumns}
            onToggle={(id) =>
              onChange({
                ...filters,
                hiddenColumns: toggleSet(filters.hiddenColumns, id),
              })
            }
          />
        </div>
      </ScrollArea>
    </aside>
  );
}

function FilterGroup<T extends string>({
  label,
  options,
  selected,
  onToggle,
  defaultOpen,
}: {
  label: string;
  options: { v: T; label: string }[];
  selected: Set<T>;
  onToggle: (v: T) => void;
  defaultOpen?: boolean;
}) {
  const activeCount = selected.size;
  const open = defaultOpen ?? activeCount > 0;
  return (
    <details
      open={open}
      className="group rounded-md border bg-card/30 px-3 py-2 [&[open]>summary>svg]:rotate-180"
    >
      <summary className="flex cursor-pointer items-center justify-between gap-2 list-none select-none">
        <span className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
          {label}
          {activeCount > 0 && (
            <span
              className="inline-flex h-4 min-w-4 items-center justify-center rounded-sm px-1 text-[10px] font-semibold tabular-nums"
              style={{
                backgroundColor:
                  "color-mix(in oklab, var(--primary) 18%, transparent)",
                color: "var(--primary)",
              }}
            >
              {activeCount}
            </span>
          )}
        </span>
        <ChevronDown className="h-3.5 w-3.5 text-muted-foreground transition-transform" />
      </summary>
      <div className="mt-2 space-y-1.5">
        {options.map((o) => (
          <label
            key={o.v}
            className="flex items-center gap-2 text-sm cursor-pointer hover:text-foreground transition-colors"
          >
            <Checkbox
              checked={selected.has(o.v)}
              onCheckedChange={() => onToggle(o.v)}
            />
            <span className="truncate">{o.label}</span>
          </label>
        ))}
      </div>
    </details>
  );
}

function ColumnVisibilityGroup({
  hidden,
  onToggle,
}: {
  hidden: Set<ColumnId>;
  onToggle: (id: ColumnId) => void;
}) {
  const togglable = ALL_COLUMNS.filter((c) => !c.locked);
  const hiddenCount = togglable.filter((c) => hidden.has(c.id)).length;
  const open = hiddenCount > 0;
  return (
    <details
      open={open}
      className="group rounded-md border bg-card/30 px-3 py-2 [&[open]>summary>svg]:rotate-180"
    >
      <summary className="flex cursor-pointer items-center justify-between gap-2 list-none select-none">
        <span className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
          표시 컬럼
          {hiddenCount > 0 && (
            <span
              className="inline-flex h-4 min-w-4 items-center justify-center rounded-sm px-1 text-[10px] font-semibold tabular-nums"
              style={{
                backgroundColor:
                  "color-mix(in oklab, var(--muted-foreground) 18%, transparent)",
                color: "var(--muted-foreground)",
              }}
              title={`${hiddenCount}개 숨김`}
            >
              −{hiddenCount}
            </span>
          )}
        </span>
        <ChevronDown className="h-3.5 w-3.5 text-muted-foreground transition-transform" />
      </summary>
      <div className="mt-2 space-y-1.5">
        {togglable.map((c) => {
          const checked = !hidden.has(c.id);
          return (
            <label
              key={c.id}
              className="flex items-center gap-2 text-sm cursor-pointer hover:text-foreground transition-colors"
            >
              <Checkbox
                checked={checked}
                onCheckedChange={() => onToggle(c.id)}
              />
              <span className="truncate">{c.label}</span>
            </label>
          );
        })}
      </div>
    </details>
  );
}

function uniqNonEmpty(arr: (string | null)[]): string[] {
  const set = new Set<string>();
  for (const v of arr) {
    if (v && v.trim()) set.add(v.trim());
  }
  return Array.from(set).sort((a, b) => a.localeCompare(b, "ko"));
}

function toggleSet<T>(s: Set<T>, v: T): Set<T> {
  const n = new Set(s);
  if (n.has(v)) n.delete(v);
  else n.add(v);
  return n;
}
