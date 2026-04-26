import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface Props {
  id: string;
  period: { current: string; previous: string };
  commentCurr: string | null;
  commentPrev: string | null;
}

export function Section4AIComment({ id, period, commentCurr, commentPrev }: Props) {
  return (
    <section id={id} className="space-y-3 scroll-mt-32">
      <h2 className="text-lg font-semibold">AI 코멘트</h2>

      <div
        className="rounded-lg border bg-card p-5 border-l-2 border-l-primary"
        style={{ boxShadow: "var(--shadow-card)" }}
      >
        <div className="mb-2 flex items-center gap-2">
          <span className="text-[10px] font-medium uppercase tracking-wide text-primary">
            AI 생성
          </span>
          <span className="text-xs text-muted-foreground">
            · 당기 {period.current} 검토 코멘트
          </span>
        </div>
        {commentCurr ? (
          <div className="prose prose-sm max-w-none text-sm leading-relaxed [&_p]:my-2">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{commentCurr}</ReactMarkdown>
          </div>
        ) : (
          <p className="py-6 text-center text-sm text-muted-foreground">
            아직 생성된 코멘트가 없습니다.
          </p>
        )}
      </div>

      {commentPrev && (
        <details
          className="rounded-lg border bg-card p-5"
          style={{ boxShadow: "var(--shadow-card)" }}
        >
          <summary className="cursor-pointer text-sm font-medium text-muted-foreground">
            전기 {period.previous} 코멘트 (펼치기)
          </summary>
          <div className="prose prose-sm mt-3 max-w-none text-sm leading-relaxed text-muted-foreground [&_p]:my-2">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{commentPrev}</ReactMarkdown>
          </div>
        </details>
      )}
    </section>
  );
}
