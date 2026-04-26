import { parseNumLike } from "./credit";

export type NiceIndicator = Record<string, string | undefined> & {
  계정명: string;
  NICE계정코드: string;
  볼드표시: "Y" | "N";
};

export type NiceData = {
  cmpCd: string;
  cmpNm: string;
  kind: "CFS" | "OFS";
  kind_label?: string;
  periods: string[];
  indicators: NiceIndicator[];
};

/** 한국어 계정명 우선 매칭 (코드는 보조). NICE indicator JSON에서 행 1개 또는 null. */
export function pickIndicator(
  data: NiceData | null | undefined,
  names: string[],
): NiceIndicator | null {
  if (!data) return null;
  for (const name of names) {
    const found = data.indicators.find((i) => (i.계정명 ?? "").trim() === name);
    if (found) return found;
  }
  return null;
}

export type SeriesPoint = { period: string; value: number | null };

/** indicator + periods → series for charting (period label은 'YYYY.MM' 잘라 표시). */
export function toSeries(
  ind: NiceIndicator | null | undefined,
  periods: string[],
): SeriesPoint[] {
  if (!ind) return periods.map((p) => ({ period: shortPeriod(p), value: null }));
  return periods.map((p) => ({
    period: shortPeriod(p),
    value: parseNumLike(ind[p]),
  }));
}

function shortPeriod(p: string): string {
  // "2024.12.31 (K-IFRS)" → "2024.12"
  const m = p.match(/^(\d{4})\.(\d{2})/);
  return m ? `${m[1]}.${m[2]}` : p;
}

/** Build dual-series for 매출/EBIT/EBITDA. */
export function financialSeries(data: NiceData | null | undefined) {
  if (!data) return null;
  return {
    revenue: toSeries(pickIndicator(data, ["매출액"]), data.periods),
    ebit: toSeries(pickIndicator(data, ["EBIT(조정영업이익)", "영업이익"]), data.periods),
    ebitda: toSeries(pickIndicator(data, ["EBITDA"]), data.periods),
    fcf: toSeries(pickIndicator(data, ["잉여현금흐름(FCF)", "FCF"]), data.periods),
    debtRatio: toSeries(pickIndicator(data, ["부채비율(%)"]), data.periods),
    debtDependency: toSeries(pickIndicator(data, ["총차입금의존도(%)", "차입금의존도(%)"]), data.periods),
    icr: toSeries(pickIndicator(data, ["EBITDA/금융비용(배)", "이자보상배율(배)"]), data.periods),
  };
}
