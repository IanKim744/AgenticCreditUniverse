/**
 * 분포 차트 (도넛 / 가로바) 공용 유틸.
 *
 * 그룹화 규칙: **건수 기반** (PoC 데이터 ~22행에 최적화).
 *  - 2건 이상 카테고리만 개별 막대.
 *  - 1건짜리 카테고리는 모두 "기타 (N개, 각 1건)" 단일 막대로 통합.
 *  - 기타 묶인 카테고리 이름 목록은 `members` 로 보존 → 툴팁에서 노출.
 *
 * 색맹 대응: hue 4축(260·180·80·25) + 명도(채도 톤다운).
 */

export type DistItem = {
  name: string;
  value: number;
  color: string;
  isOther?: boolean;
  members?: string[]; // 기타일 때 묶인 카테고리 이름 목록 (툴팁용)
  pct?: number;       // 0~100 (사전 계산)
};

export type OthersGroup = {
  count: number;       // 묶인 카테고리 수
  value: number;       // 합계 건수
  pct: number;         // 0~100
  members: string[];   // 묶인 카테고리 이름 목록
};

export type DistResult = {
  items: DistItem[];          // 막대로 그릴 항목들 (개별 + 기타가 마지막)
  others: OthersGroup | null; // 통계 요약용 (footer/notice 분기에 사용)
  total: number;              // 전체 건수
  categoryCount: number;      // 원본 전체 카테고리 수
};

const BASE_COLORS = [
  "var(--chart-1)", // hue 260 남색
  "var(--chart-2)", // hue 180 청록
  "var(--chart-3)", // hue 80  노랑
  "var(--chart-4)", // hue 25  적색
] as const;

/** 순위(0-base) → 색상. 1~3위 채도 高, 4~7위 동계열 톤다운, 8위+ 추가 톤다운. */
export function distColor(rank: number): string {
  if (rank < 3) return BASE_COLORS[rank]!;
  if (rank < 7) {
    const baseIdx = (rank - 3) % 4;
    return `color-mix(in oklab, ${BASE_COLORS[baseIdx]} 60%, var(--muted) 40%)`;
  }
  const baseIdx = (rank - 7) % 4;
  return `color-mix(in oklab, ${BASE_COLORS[baseIdx]} 35%, var(--muted) 65%)`;
}

/** 기타 그룹 색상 — 회색 계열, 배경에 가깝게. */
export function othersColor(): string {
  return "color-mix(in oklab, var(--muted-foreground) 25%, var(--background) 75%)";
}

/** 기타 그룹 stroke 색상 — 점선 테두리용. */
export function othersStroke(): string {
  return "color-mix(in oklab, var(--muted-foreground) 50%, var(--background) 50%)";
}

export type BucketOptions = {
  minCount?: number; // 개별 표시 최소 건수, 기본 2
};

export function bucketWithOthers(
  values: (string | null | undefined)[],
  fallback: string,
  opts: BucketOptions = {},
): DistResult {
  const { minCount = 2 } = opts;

  const map = new Map<string, number>();
  for (const v of values) {
    const k = (v ?? "").trim() || fallback;
    map.set(k, (map.get(k) ?? 0) + 1);
  }
  const sorted = Array.from(map, ([name, value]) => ({ name, value })).sort(
    (a, b) => b.value - a.value,
  );
  const total = sorted.reduce((s, d) => s + d.value, 0);
  const categoryCount = sorted.length;

  const keepers = sorted.filter((d) => d.value >= minCount);
  const rest = sorted.filter((d) => d.value < minCount);
  const restValue = rest.reduce((s, d) => s + d.value, 0);
  const restPct = total ? (restValue / total) * 100 : 0;

  const items: DistItem[] = keepers.map((d, i) => ({
    name: d.name,
    value: d.value,
    color: distColor(i),
    pct: total ? (d.value / total) * 100 : 0,
  }));

  let others: OthersGroup | null = null;
  if (rest.length > 0) {
    others = {
      count: rest.length,
      value: restValue,
      pct: restPct,
      members: rest.map((d) => d.name),
    };
    items.push({
      name: `기타 (${rest.length}개)`,
      value: restValue,
      color: othersColor(),
      isOther: true,
      members: others.members,
      pct: restPct,
    });
  }

  return { items, others, total, categoryCount };
}
