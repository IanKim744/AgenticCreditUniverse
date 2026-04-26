/** Server-side fetch helper — forwards cookies in App Router server components. */
import { cookies } from "next/headers";

const BACKEND = process.env.BACKEND_URL ?? "http://127.0.0.1:8787";

async function authedFetch(path: string, init?: RequestInit) {
  const ck = await cookies();
  const cookieHeader = ck
    .getAll()
    .map((c) => `${c.name}=${c.value}`)
    .join("; ");
  const res = await fetch(`${BACKEND}${path}`, {
    ...init,
    headers: {
      cookie: cookieHeader,
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });
  return res;
}

export async function fetchCompanies() {
  const res = await authedFetch("/api/companies");
  if (!res.ok) {
    throw new Error(`fetchCompanies failed: ${res.status}`);
  }
  return res.json();
}

export async function fetchCompanyDetail(slug: string) {
  const res = await authedFetch(`/api/companies/${encodeURIComponent(slug)}`);
  if (res.status === 404) return null;
  if (!res.ok) {
    throw new Error(`fetchCompanyDetail failed: ${res.status}`);
  }
  return res.json();
}

export async function fetchDartText(slug: string, kind: "business" | "notes") {
  const res = await authedFetch(`/api/companies/${encodeURIComponent(slug)}/dart/${kind}.txt`);
  if (!res.ok) return null;
  return res.text();
}

export type CompanyRow = {
  slug: string;
  issuer: string;
  stock_code: string | null;
  group_name: string | null;
  industry: string | null;
  industry_2026: string | null;
  rating_prev: string | null;
  watch_prev: string | null;
  rating_curr: string | null;
  watch_curr: string | null;
  universe_prev: "O" | "△" | "X" | null;
  universe_curr_ai: "O" | "△" | "X" | null;
  reviewer_final: "O" | "△" | "X" | null;
  movement: string | null;
  comment_preview: string | null;
  comment_curr: string | null;
  manager: string | null;
  review_status: "done" | "none";
  unresolved: boolean;
  last_updated_utc: string | null;
};

export type Kpis = {
  total: number;
  rating_distribution: { high: number; mid: number; low: number; nr: number };
  movement: { up: number; down: number; flat: number };
  review: { done: number; none: number; pct: number };
};

export type CompaniesResponse = {
  period: { current: string; previous: string; previous_previous?: string };
  rows: CompanyRow[];
  kpis: Kpis;
};
