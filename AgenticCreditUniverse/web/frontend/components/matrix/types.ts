import type { CompanyRow } from "@/lib/api";
import type { RatingBucket } from "@/lib/credit";

export type ReviewStatus = "done" | "none";
export type Universe = "O" | "△" | "X";
export type MovementKey = "up" | "down" | "flat";

export type ColumnId =
  | "issuer"
  | "group_name"
  | "industry"
  | "watch_industry"
  | "prev_grade"
  | "curr_grade"
  | "universe_prev"
  | "universe_curr_ai"
  | "reviewer_final"
  | "movement"
  | "comment_preview"
  | "manager"
  | "review"
  | "last_updated_utc";

export const ALL_COLUMNS: { id: ColumnId; label: string; locked?: boolean }[] = [
  { id: "issuer",            label: "발행기관", locked: true },
  { id: "group_name",        label: "그룹사" },
  { id: "industry",          label: "업종" },
  { id: "watch_industry",    label: "유의업종" },
  { id: "prev_grade",        label: "전기 등급/전망" },
  { id: "curr_grade",        label: "당기 등급/전망" },
  { id: "universe_prev",     label: "전기 유니버스" },
  { id: "universe_curr_ai",  label: "당기 유니버스 (AI)" },
  { id: "reviewer_final",    label: "심사역 최종 판단" },
  { id: "movement",          label: "의견변동" },
  { id: "comment_preview",   label: "당기 코멘트" },
  { id: "manager",           label: "담당" },
  { id: "review",            label: "검수여부" },
  { id: "last_updated_utc",  label: "마지막 갱신" },
];

export const DEFAULT_HIDDEN_COLUMNS: ColumnId[] = [];

export interface Filters {
  query: string;
  groups: Set<string>;
  industries: Set<string>;
  tiers: Set<RatingBucket>;
  universes: Set<Universe | "—">;
  movements: Set<MovementKey>;
  managers: Set<string>;
  reviewStatuses: Set<ReviewStatus>;
  hiddenColumns: Set<ColumnId>;
}

export const emptyFilters = (): Filters => ({
  query: "",
  groups: new Set(),
  industries: new Set(),
  tiers: new Set(),
  universes: new Set(),
  movements: new Set(),
  managers: new Set(),
  reviewStatuses: new Set(),
  hiddenColumns: new Set(DEFAULT_HIDDEN_COLUMNS),
});

export function applyFilters(rows: CompanyRow[], f: Filters): CompanyRow[] {
  const q = f.query.trim().toLowerCase();
  return rows.filter((r) => {
    if (q) {
      const hay = `${r.issuer ?? ""} ${r.group_name ?? ""}`.toLowerCase();
      if (!hay.includes(q)) return false;
    }
    if (f.groups.size && !f.groups.has(r.group_name ?? "—")) return false;
    if (f.industries.size && !f.industries.has(r.industry ?? "—")) return false;
    if (f.tiers.size) {
      // 8tier 버킷 — ratingBucket() 가 단기등급(A1/A2±/A3±) 도 동급 장기 tier 로 자동 매핑.
      // 따라서 "BBB+" 필터(=tier-5) 클릭 시 장기 BBB+ 와 단기 A3+ 모두 매칭됨.
      const t = ratingBucket(r.rating_curr);
      if (!f.tiers.has(t)) return false;
    }
    if (f.universes.size) {
      const u = (r.universe_curr_ai ?? "—") as Universe | "—";
      if (!f.universes.has(u)) return false;
    }
    if (f.movements.size) {
      const m = classify(r.movement);
      if (!m || !f.movements.has(m)) return false;
    }
    if (f.managers.size && !f.managers.has(r.manager ?? "—")) return false;
    if (f.reviewStatuses.size && !f.reviewStatuses.has(r.review_status)) return false;
    return true;
  });
}

import { ratingBucket, classifyMovement } from "@/lib/credit";

function classify(m: string | null): MovementKey | null {
  const c = classifyMovement(m);
  if (c === "none") return null;
  return c as MovementKey;
}
