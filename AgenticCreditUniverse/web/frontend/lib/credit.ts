/**
 * 신용등급 / 전망 / 포매팅 유틸 — DESIGN-GUIDE §6, §9, §15 단일 출처.
 */

export const RATING_ORDER = [
  "AAA",
  "AA+", "AA", "AA-",
  "A+", "A", "A-",
  "BBB+", "BBB", "BBB-",
  "BB+", "BB", "BB-",
  "B+", "B", "B-",
  "CCC", "CC", "C", "D",
] as const;
export type Rating = (typeof RATING_ORDER)[number];

export type Tier = "high" | "mid" | "low" | "nr";

export function ratingTier(r?: string | null): Tier {
  if (!r) return "nr";
  const s = r.toUpperCase();
  if (s.startsWith("BBB")) return "mid";
  if (s.startsWith("B") || s.startsWith("C") || s.startsWith("D")) return "low";
  if (s.startsWith("A")) return "high";
  return "nr";
}

export type RatingBucket =
  | "tier-1" // AA- 이상 (장기) / A1 (단기)
  | "tier-2" // A+ / A2+
  | "tier-3" // A (=A0) / A2 / A20
  | "tier-4" // A- / A2-
  | "tier-5" // BBB+ / A3+
  | "tier-6" // BBB (=BBB0) / A3 / A30
  | "tier-7" // BBB- / A3-
  | "tier-8" // BB+ 이하 / B / C / D
  | "nr";    // 미부여

/**
 * 등급 문자열 → 8-bucket. 한국 신평 관행에서 단기등급(A1/A2±/A3±)도
 * 동일 hue 라인에 매핑한다.
 *  - A1            → tier-1 (≈ AA-↑)
 *  - A2+ / A2 / A2-→ tier-2 / 3 / 4 (≈ A+ / A0 / A-)
 *  - A3+ / A3 / A3-→ tier-5 / 6 / 7 (≈ BBB+ / BBB0 / BBB-)
 *  - B, C, D       → tier-8
 *
 * "A0" / "BBB0" / "A20" 처럼 한국 표기에서 흔한 0 접미사도 평탄 등급으로 처리.
 */
export function ratingBucket(r?: string | null): RatingBucket {
  if (!r) return "nr";
  const s = r.toUpperCase().trim();

  // 장기 — AAA / AA± 묶음
  if (s === "AAA" || s === "AA+" || s === "AA" || s === "AA-") return "tier-1";
  // 단기 — A1
  if (s === "A1" || s === "A1+") return "tier-1";

  // 장기 A± / 단기 A2±
  if (s === "A+" || s === "A2+") return "tier-2";
  if (s === "A" || s === "A0" || s === "A2" || s === "A20") return "tier-3";
  if (s === "A-" || s === "A2-") return "tier-4";

  // 장기 BBB± / 단기 A3±
  if (s === "BBB+" || s === "A3+") return "tier-5";
  if (s === "BBB" || s === "BBB0" || s === "A3" || s === "A30") return "tier-6";
  if (s === "BBB-" || s === "A3-") return "tier-7";

  // 그 외 (BB+ 이하, B, C, D, 단기 B/C/D 포함)
  return "tier-8";
}

export function ratingColorVar(r?: string | null): string {
  const b = ratingBucket(r);
  if (b === "nr") return "var(--muted-foreground)";
  return `var(--rating-${b})`;
}

export function isInvestmentGrade(r?: string | null): boolean {
  return ratingTier(r) !== "low" && ratingTier(r) !== "nr";
}

/** 단기등급 → 동일 hue의 장기등급으로 정규화 (정렬·비교용). */
const SHORT_TO_LONG: Record<string, Rating> = {
  "A1+": "AA",
  "A1": "AA-",
  "A2+": "A+",
  "A2": "A",
  "A20": "A",
  "A2-": "A-",
  "A3+": "BBB+",
  "A3": "BBB",
  "A30": "BBB",
  "A3-": "BBB-",
};

export function normalizeRating(r?: string | null): Rating | null {
  if (!r) return null;
  const s = r.toUpperCase().trim();
  if ((SHORT_TO_LONG as Record<string, Rating>)[s]) return SHORT_TO_LONG[s]!;
  if (s === "A0") return "A";
  if (s === "BBB0") return "BBB";
  return RATING_ORDER.includes(s as Rating) ? (s as Rating) : null;
}

export function compareRating(a?: string | null, b?: string | null): number {
  const an = normalizeRating(a);
  const bn = normalizeRating(b);
  const ai = an ? RATING_ORDER.indexOf(an) : -1;
  const bi = bn ? RATING_ORDER.indexOf(bn) : -1;
  if (ai === -1 && bi === -1) return 0;
  if (ai === -1) return 1;
  if (bi === -1) return -1;
  return ai - bi;
}

/** Excel watch column "P" / "S" / "N" → semantic key. 한글 라벨도 허용. */
export type WatchKey = "positive" | "stable" | "negative";
export function parseWatch(v?: string | null): WatchKey | null {
  if (!v) return null;
  const s = String(v).trim().toUpperCase();
  if (s === "P" || s === "POS" || s === "POSITIVE" || s === "긍정적") return "positive";
  if (s === "S" || s === "STA" || s === "STABLE" || s === "안정적") return "stable";
  if (s === "N" || s === "NEG" || s === "NEGATIVE" || s === "부정적") return "negative";
  return null;
}

export const WATCH_LABEL: Record<WatchKey, string> = {
  positive: "긍정적",
  stable: "안정적",
  negative: "부정적",
};

/** 전망 비교 — 양수: curr 가 더 긍정적. positive > stable > negative. */
const WATCH_RANK: Record<WatchKey, number> = { positive: 2, stable: 1, negative: 0 };
export function compareWatch(a?: string | null, b?: string | null): number {
  const ak = parseWatch(a);
  const bk = parseWatch(b);
  if (!ak || !bk) return 0;
  return WATCH_RANK[bk] - WATCH_RANK[ak];
}

export const WATCH_COLOR: Record<WatchKey, string> = {
  positive: "var(--watch-positive)",
  stable: "var(--watch-stable)",
  negative: "var(--watch-negative)",
};

export type Universe = "O" | "△" | "X";

/** 단위: 억원. 10000 이상은 조원 환산. */
export function formatBillionKRW(v?: number | null): string {
  if (v == null || Number.isNaN(v)) return "—";
  return Math.abs(v) >= 10000 ? `${(v / 10000).toFixed(1)}조원` : `${v.toLocaleString("ko-KR")}억원`;
}

export function formatPercent(v?: number | null, digits = 1): string {
  return v == null || Number.isNaN(v) ? "—" : `${v.toFixed(digits)}%`;
}

export function formatMultiple(v?: number | null, digits = 1): string {
  return v == null || Number.isNaN(v) ? "—" : `${v.toFixed(digits)}x`;
}

export function formatDelta(v?: number | null, digits = 1): string {
  if (v == null || Number.isNaN(v)) return "—";
  const sign = v > 0 ? "+" : "";
  return `${sign}${v.toFixed(digits)}%`;
}

/** "12,345" / "12345.6" 같은 NICE 문자열 → number (NaN 시 null). */
export function parseNumLike(raw: unknown): number | null {
  if (raw == null) return null;
  if (typeof raw === "number") return Number.isNaN(raw) ? null : raw;
  const s = String(raw).replace(/,/g, "").trim();
  if (!s || s === "-") return null;
  const n = Number(s);
  return Number.isNaN(n) ? null : n;
}

/** Movement string from Excel Col 14 (▲/▽/-/null/""). */
export function classifyMovement(m?: string | null): "up" | "down" | "flat" | "none" {
  if (!m) return "none";
  const s = m.trim();
  if (s === "▲") return "up";
  if (s === "▽" || s === "▼") return "down";
  if (s === "-") return "flat";
  return "none";
}
