"use client";

import { useState, useTransition } from "react";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { UniverseChip } from "@/components/universe-chip";
import { cn } from "@/lib/utils";

type Universe = "O" | "△" | "X";

interface Props {
  slug: string;
  ai: Universe | null;
  stage2: {
    final: Universe;
    movement: string;
    adjusted: boolean;
    rationale: string;
  } | null;
  inversion: { rationale: string } | null;
  current: {
    status: "done" | "none";
    universe: Universe | null;
    agree_with_ai: boolean | null;
    note: string | null;
    reviewed_at: string | null;
    reviewed_by: string | null;
  };
}

export function ReviewActionPanel({ slug, ai, stage2, inversion, current }: Props) {
  const initial = (current.universe ?? stage2?.final ?? ai ?? "△") as Universe;
  // SSOT for "AI 판단": Stage 2 풀 검수 우선, 없으면 1차 종목별로 폴백.
  // 둘 다 없으면 동의 체크의 비교 대상이 없으므로 항상 false 로 유지.
  const aiTarget: Universe | null = stage2?.final ?? ai;
  const [universe, setUniverse] = useState<Universe>(initial);
  const [agree, setAgree] = useState<boolean>(
    current.agree_with_ai ?? (aiTarget != null ? initial === aiTarget : false),
  );
  const [note, setNote] = useState(current.note ?? "");
  const [pending, start] = useTransition();
  const [error, setError] = useState<string | null>(null);

  const onConfirm = () => {
    setError(null);
    start(async () => {
      const res = await fetch(`/api/companies/${encodeURIComponent(slug)}/review`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          universe,
          agree_with_ai: agree,
          note: note.trim() || null,
        }),
      });
      if (!res.ok) {
        setError(`확정 실패 (${res.status})`);
        return;
      }
      window.location.reload();
    });
  };

  const onUnconfirm = () => {
    setError(null);
    start(async () => {
      const res = await fetch(`/api/companies/${encodeURIComponent(slug)}/review`, {
        method: "DELETE",
      });
      if (!res.ok) {
        setError(`해제 실패 (${res.status})`);
        return;
      }
      window.location.reload();
    });
  };

  return (
    <div
      className="rounded-lg border bg-card p-4 space-y-3"
      style={{ boxShadow: "var(--shadow-card)" }}
    >
      <div className="flex items-center justify-between">
        <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          검수 액션
        </div>
        {current.status === "done" ? (
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
        )}
      </div>

      <div className="rounded-md bg-muted/40 p-2.5 text-xs">
        <div className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground mb-1.5">
          AI 판단
        </div>
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
          <span className="text-muted-foreground">1차 종목별</span>
          <UniverseChip value={ai} />
          <span className="ml-2 text-muted-foreground">2차 풀 검수</span>
          <UniverseChip value={stage2?.final ?? null} />
          {stage2?.adjusted && (
            <span
              title={stage2.rationale}
              className="ml-1 inline-flex items-center gap-0.5 rounded-md bg-amber-500/10 px-1.5 py-0.5 text-[10px] font-medium text-amber-700"
            >
              ⚙ 가드레일
            </span>
          )}
        </div>
        {stage2?.rationale && (
          <p className="mt-1.5 text-[11px] leading-relaxed text-muted-foreground line-clamp-3">
            {stage2.rationale}
          </p>
        )}
        {inversion && (
          <p className="mt-1.5 rounded bg-amber-500/10 p-1.5 text-[11px] text-amber-700">
            등급 역전: {inversion.rationale}
          </p>
        )}
      </div>

      <div className="space-y-1.5">
        <div className="text-xs font-medium text-muted-foreground">
          유니버스 분류 확정
        </div>
        <div className="flex gap-2">
          {(["O", "△", "X"] as Universe[]).map((v) => (
            <button
              type="button"
              key={v}
              onClick={() => {
                setUniverse(v);
                setAgree(aiTarget != null && v === aiTarget);
              }}
              className={cn(
                "flex-1 rounded-md border py-1.5 text-sm font-medium tabular-nums transition-colors",
                universe === v
                  ? "border-primary bg-primary/5 text-primary"
                  : "border-border text-muted-foreground hover:bg-accent",
              )}
            >
              {v}
            </button>
          ))}
        </div>
      </div>

      <label className="flex items-center gap-2 text-xs cursor-pointer">
        <Checkbox
          checked={agree}
          onCheckedChange={(c) => {
            const v = !!c;
            setAgree(v);
            if (v && aiTarget) setUniverse(aiTarget);
          }}
        />
        <span>AI 판단에 동의</span>
      </label>

      <div className="space-y-1.5">
        <div className="text-xs font-medium text-muted-foreground">
          확정 코멘트 (선택)
        </div>
        <textarea
          value={note}
          onChange={(e) => setNote(e.target.value)}
          rows={2}
          maxLength={500}
          placeholder="AI와 다른 결정을 내린 경우 사유 등"
          className="w-full rounded-md border bg-background px-2.5 py-1.5 text-xs focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring resize-none"
        />
      </div>

      {error && (
        <div className="rounded-md border border-destructive/30 bg-destructive/5 p-2 text-xs text-destructive">
          {error}
        </div>
      )}

      <div className="flex gap-2">
        <Button onClick={onConfirm} disabled={pending} className="flex-1">
          {pending ? (
            <>
              <Loader2 className="h-3.5 w-3.5 animate-spin" /> 처리 중…
            </>
          ) : (
            "검수 확정"
          )}
        </Button>
        {current.status === "done" && (
          <Button
            type="button"
            variant="outline"
            onClick={onUnconfirm}
            disabled={pending}
          >
            확정 해제
          </Button>
        )}
      </div>

      {current.reviewed_at && (
        <div className="border-t pt-2 text-[11px] text-muted-foreground tabular-nums">
          {current.reviewed_by} ·{" "}
          {new Date(current.reviewed_at).toLocaleString("ko-KR", {
            month: "2-digit",
            day: "2-digit",
            hour: "2-digit",
            minute: "2-digit",
          })}{" "}
          · {current.universe}
        </div>
      )}
    </div>
  );
}
