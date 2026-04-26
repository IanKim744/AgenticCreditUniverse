"use client";

import { useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { financialSeries, type NiceData } from "@/lib/nice";
import { cn } from "@/lib/utils";

interface Props {
  id: string;
  cfs: NiceData | null;
  ofs: NiceData | null;
}

const TOOLTIP_STYLE = {
  borderRadius: 8,
  border: "1px solid var(--border)",
  fontSize: 12,
  backgroundColor: "var(--popover)",
  color: "var(--popover-foreground)",
};

export function Section2Financials({ id, cfs, ofs }: Props) {
  return (
    <section id={id} className="space-y-4 scroll-mt-32">
      <h2 className="text-lg font-semibold">재무 추이 (NICE)</h2>
      <Tabs defaultValue="cfs">
        <TabsList>
          <TabsTrigger value="cfs">연결 (CFS)</TabsTrigger>
          <TabsTrigger value="ofs" disabled={!ofs}>
            별도 (OFS) {!ofs && "· 미수집"}
          </TabsTrigger>
        </TabsList>
        <TabsContent value="cfs" className="space-y-4 pt-4">
          <FinancialPanel data={cfs} />
        </TabsContent>
        <TabsContent value="ofs" className="space-y-4 pt-4">
          <FinancialPanel data={ofs} />
        </TabsContent>
      </Tabs>
    </section>
  );
}

function FinancialPanel({ data }: { data: NiceData | null }) {
  const [showTable, setShowTable] = useState(true);
  if (!data) {
    return (
      <div className="rounded-lg border bg-card p-8 text-center text-sm text-muted-foreground">
        데이터 없음
      </div>
    );
  }
  const series = financialSeries(data);
  if (!series) return null;

  // 매출/EBIT/EBITDA 합쳐 한 차트
  const profitability = series.revenue.map((p, i) => ({
    period: p.period,
    매출액: p.value,
    EBIT: series.ebit[i]?.value ?? null,
    EBITDA: series.ebitda[i]?.value ?? null,
  }));
  // 부채비율(좌) / 차입금의존도(우)
  const leverage = series.debtRatio.map((p, i) => ({
    period: p.period,
    부채비율: p.value,
    차입금의존도: series.debtDependency[i]?.value ?? null,
  }));
  // FCF
  const fcf = series.fcf.map((p) => ({ period: p.period, value: p.value }));
  // ICR
  const icr = series.icr.map((p) => ({ period: p.period, value: p.value }));

  return (
    <>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <ChartCard title="매출 · EBIT · EBITDA (억원)">
          <LineChart data={profitability}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis dataKey="period" tickLine={false} axisLine={false} fontSize={11} angle={-30} textAnchor="end" height={50} />
            <YAxis tickLine={false} axisLine={false} fontSize={11} />
            <Tooltip contentStyle={TOOLTIP_STYLE} />
            <Line
              type="monotone"
              dataKey="매출액"
              stroke="var(--chart-1)"
              strokeWidth={2}
              dot={false}
            />
            <Line
              type="monotone"
              dataKey="EBIT"
              stroke="var(--chart-2)"
              strokeWidth={2}
              dot={false}
            />
            <Line
              type="monotone"
              dataKey="EBITDA"
              stroke="var(--chart-3)"
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        </ChartCard>

        <ChartCard title="부채비율 / 차입금의존도 (%)">
          <LineChart data={leverage}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis dataKey="period" tickLine={false} axisLine={false} fontSize={11} angle={-30} textAnchor="end" height={50} />
            <YAxis tickLine={false} axisLine={false} fontSize={11} />
            <Tooltip contentStyle={TOOLTIP_STYLE} />
            <Line
              type="monotone"
              dataKey="부채비율"
              stroke="var(--chart-1)"
              strokeWidth={2}
              dot={false}
            />
            <Line
              type="monotone"
              dataKey="차입금의존도"
              stroke="var(--chart-2)"
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        </ChartCard>

        <ChartCard title="잉여현금흐름 FCF (억원)">
          <BarChart data={fcf}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis dataKey="period" tickLine={false} axisLine={false} fontSize={11} angle={-30} textAnchor="end" height={50} />
            <YAxis tickLine={false} axisLine={false} fontSize={11} />
            <ReferenceLine y={0} stroke="var(--border)" />
            <Tooltip contentStyle={TOOLTIP_STYLE} />
            <Bar dataKey="value" radius={[4, 4, 0, 0]}>
              {fcf.map((p, i) => (
                <Cell
                  key={i}
                  fill={(p.value ?? 0) >= 0 ? "var(--chart-2)" : "var(--watch-negative)"}
                />
              ))}
            </Bar>
          </BarChart>
        </ChartCard>

        <ChartCard title="이자보상배율 EBITDA/금융비용 (배)">
          <LineChart data={icr}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis dataKey="period" tickLine={false} axisLine={false} fontSize={11} angle={-30} textAnchor="end" height={50} />
            <YAxis tickLine={false} axisLine={false} fontSize={11} />
            <Tooltip contentStyle={TOOLTIP_STYLE} />
            <Line
              type="monotone"
              dataKey="value"
              stroke="var(--chart-1)"
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        </ChartCard>
      </div>

      <details
        open
        className="rounded-lg border bg-card p-4"
        style={{ boxShadow: "var(--shadow-card)" }}
        onToggle={(e) => setShowTable((e.target as HTMLDetailsElement).open)}
      >
        <summary className="cursor-pointer text-sm font-medium">
          주요 재무지표
        </summary>
        {showTable && <IndicatorTable data={data} />}
      </details>
    </>
  );
}

function ChartCard({
  title,
  children,
}: {
  title: string;
  children: React.ReactElement;
}) {
  return (
    <div
      className="rounded-lg border bg-card p-4"
      style={{ boxShadow: "var(--shadow-card)" }}
    >
      <div className="mb-2 text-sm font-medium">{title}</div>
      <div className="h-48 lg:h-56">
        <ResponsiveContainer width="100%" height="100%">
          {children}
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function IndicatorTable({ data }: { data: NiceData }) {
  return (
    <div className="mt-3 overflow-x-auto">
      <table className="w-full text-xs tabular-nums">
        <thead>
          <tr className="border-b text-left text-muted-foreground">
            <th className="py-1.5 pr-3 font-medium">계정명</th>
            {data.periods.map((p) => (
              <th key={p} className="py-1.5 px-2 font-medium text-right">
                {p.slice(0, 7)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.indicators.map((ind) => (
            <tr key={ind.NICE계정코드} className="border-b last:border-b-0">
              <td
                className={cn(
                  "py-1.5 pr-3",
                  ind.볼드표시 === "Y" && "font-medium",
                )}
              >
                {ind.계정명}
              </td>
              {data.periods.map((p) => (
                <td key={p} className="py-1.5 px-2 text-right text-muted-foreground">
                  {ind[p] ?? "—"}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
