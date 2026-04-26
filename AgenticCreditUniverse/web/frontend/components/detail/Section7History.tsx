import { Clock } from "lucide-react";

export function Section7History({
  id,
  history,
}: {
  id: string;
  history: { half: string; rating?: string | null; watch?: string | null; universe?: string | null; reviewer?: string | null; reason?: string | null }[];
}) {
  return (
    <section id={id} className="space-y-3 scroll-mt-32">
      <h2 className="text-lg font-semibold">반기 히스토리</h2>
      <div
        className="rounded-lg border bg-card p-4"
        style={{ boxShadow: "var(--shadow-card)" }}
      >
        {history.length === 0 ? (
          <div className="py-10 text-center">
            <Clock className="mx-auto h-8 w-8 text-muted-foreground/40" />
            <p className="mt-3 text-sm font-medium">이전 반기 데이터 없음</p>
            <p className="mt-1 text-xs text-muted-foreground">
              첫 반기 빌드는 26.1H입니다. 26.2H 롤오버 후 시계열이 누적됩니다.
            </p>
          </div>
        ) : (
          <table className="w-full text-sm tabular-nums">
            <thead>
              <tr className="border-b text-left text-xs text-muted-foreground">
                <th className="py-2 px-2 font-medium">반기</th>
                <th className="py-2 px-2 font-medium">등급</th>
                <th className="py-2 px-2 font-medium">전망</th>
                <th className="py-2 px-2 font-medium">유니버스 (AI)</th>
                <th className="py-2 px-2 font-medium">심사역</th>
                <th className="py-2 px-2 font-medium">변동 사유</th>
              </tr>
            </thead>
            <tbody>
              {history.map((h) => (
                <tr key={h.half} className="border-b last:border-b-0">
                  <td className="py-2 px-2 font-medium">{h.half}</td>
                  <td className="py-2 px-2">{h.rating ?? "—"}</td>
                  <td className="py-2 px-2">{h.watch ?? "—"}</td>
                  <td className="py-2 px-2">{h.universe ?? "—"}</td>
                  <td className="py-2 px-2">{h.reviewer ?? "—"}</td>
                  <td className="py-2 px-2 text-xs text-muted-foreground">
                    {h.reason ?? "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </section>
  );
}
