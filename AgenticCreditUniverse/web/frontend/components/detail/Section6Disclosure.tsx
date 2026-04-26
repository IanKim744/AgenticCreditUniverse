"use client";

import { useEffect, useState } from "react";
import { Check, Copy, ExternalLink, Loader2, Maximize2, Minus, Plus } from "lucide-react";
import DOMPurify from "isomorphic-dompurify";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface Props {
  id: string;
  slug: string;
  metadata: {
    report?: { report_nm?: string; rcept_no?: string; rcept_dt?: string };
    business_section?: { status?: string };
    notes_section?: { status?: string; variant?: string };
  } | null;
  reportUrl: string | null;
  available: boolean;
}

const ALLOWED_TAGS = [
  "table", "thead", "tbody", "tfoot", "tr", "td", "th", "colgroup", "col", "caption",
  "p", "strong", "em", "b", "i", "u", "span", "div", "section", "article",
  "h1", "h2", "h3", "h4", "h5", "h6",
  "ul", "ol", "li", "br", "hr", "blockquote", "pre", "code",
];
const ALLOWED_ATTR = ["colspan", "rowspan", "align", "valign", "class", "width", "height"];

const FONT_MIN = 10;
const FONT_MAX = 24;
const FONT_STEP = 2;
const FONT_DEFAULT = 14;

const DART_TAG_MAP: Record<string, string> = {
  "TABLE-GROUP": "div",
  TABLE: "table",
  COLGROUP: "colgroup",
  COL: "col",
  THEAD: "thead",
  TBODY: "tbody",
  TFOOT: "tfoot",
  TR: "tr",
  TH: "th",
  TD: "td",
  TE: "td",
  TITLE: "div",
};

function decodeEscapedDartTags(raw: string): string {
  return raw.replace(
    /&lt;(\/?)([A-Z][A-Z0-9-]*)((?:[^&]|&(?!gt;))*?)\/?&gt;/g,
    (match, slash: string, tag: string, attrs: string) => {
      const mapped = DART_TAG_MAP[tag.toUpperCase()];
      if (!mapped) return match;
      return `<${slash}${mapped}${attrs}>`;
    },
  );
}

export function Section6Disclosure({ id, slug, metadata, reportUrl, available }: Props) {
  return (
    <section id={id} className="space-y-3 scroll-mt-32">
      <h2 className="text-lg font-semibold">DART 공시</h2>
      <details
        open
        className="rounded-lg border bg-card p-4"
        style={{ boxShadow: "var(--shadow-card)" }}
      >
        <summary className="cursor-pointer text-sm font-medium">
          {metadata?.report?.report_nm ?? "사업보고서"}
        </summary>
        <div className="mt-3 space-y-3">
          {metadata?.report && (
            <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground tabular-nums">
              <span>공시일자 {fmtDate(metadata.report.rcept_dt)}</span>
              {reportUrl && (
                <a
                  href={reportUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-primary hover:underline"
                >
                  DART 원공시
                  <ExternalLink className="h-3 w-3" />
                </a>
              )}
            </div>
          )}

          {available ? (
            <div className="space-y-6">
              <div>
                <h3 className="mb-2 text-sm font-medium">사업의 내용</h3>
                <DartViewer slug={slug} kind="business" label="사업의 내용" />
              </div>
              <div>
                <h3 className="mb-2 text-sm font-medium">
                  연결 주석
                  {metadata?.notes_section?.variant === "separate" && " (별도)"}
                </h3>
                <DartViewer
                  slug={slug}
                  kind="notes"
                  label={
                    metadata?.notes_section?.variant === "separate"
                      ? "연결 주석 (별도)"
                      : "연결 주석"
                  }
                />
              </div>
            </div>
          ) : (
            <p className="py-6 text-center text-sm text-muted-foreground">
              DART 자료 미수집
            </p>
          )}
        </div>
      </details>
    </section>
  );
}

const DART_ARTICLE_CLASSES =
  "dart-html prose prose-sm max-w-none p-4 \
prose-headings:font-semibold prose-headings:tracking-tight \
prose-table:my-2 prose-table:text-[0.85em] \
[&_table]:my-2 [&_table]:!w-auto [&_table]:border-collapse \
[&_th]:border [&_th]:border-border [&_th]:bg-muted/40 \
[&_th]:px-1.5 [&_th]:py-1 [&_th]:text-[0.85em] [&_th]:font-medium \
[&_th]:text-left [&_th]:align-middle \
[&_th]:[word-break:keep-all] [&_th]:break-words \
[&_td]:border [&_td]:border-border \
[&_td]:px-1.5 [&_td]:py-1 [&_td]:text-[0.85em] [&_td]:align-top \
[&_td]:tabular-nums \
[&_td]:[word-break:keep-all] [&_td]:break-words \
[&_td[align='right']]:text-right [&_td[align='RIGHT']]:text-right \
[&_td[align='center']]:text-center [&_td[align='CENTER']]:text-center \
[&_p]:my-1.5 [&_p]:leading-relaxed \
[&_p:empty]:hidden \
[&_p+table]:!mt-1 [&_table+p]:!mt-2 \
[&_h3]:!mt-4 [&_h3]:!mb-2";

function DartContent({
  html,
  text,
  fontSize,
}: {
  html: string | null;
  text: string | null;
  fontSize: number;
}) {
  if (html) {
    return (
      <article
        className={DART_ARTICLE_CLASSES}
        style={{ fontSize: `${fontSize}px` }}
        dangerouslySetInnerHTML={{ __html: html }}
      />
    );
  }
  return (
    <pre
      className="whitespace-pre-wrap p-4 leading-relaxed font-sans text-muted-foreground"
      style={{ fontSize: `${fontSize}px` }}
    >
      {text}
    </pre>
  );
}

function DartToolbar({
  fontSize,
  setFontSize,
  onExpand,
  label,
}: {
  fontSize: number;
  setFontSize: (updater: (prev: number) => number) => void;
  onExpand?: () => void;
  label: string;
}) {
  const btnBase =
    "inline-flex h-7 w-7 items-center justify-center text-muted-foreground transition-colors hover:bg-background hover:text-foreground disabled:opacity-40 disabled:hover:bg-transparent disabled:hover:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring";
  return (
    <div className="absolute right-2 top-2 z-10 flex items-center divide-x divide-border overflow-hidden rounded-md border bg-background/85 backdrop-blur-sm">
      <button
        type="button"
        onClick={() => setFontSize((s) => Math.max(FONT_MIN, s - FONT_STEP))}
        disabled={fontSize <= FONT_MIN}
        className={btnBase}
        title="글자 작게"
      >
        <Minus className="h-3.5 w-3.5" />
        <span className="sr-only">글자 작게</span>
      </button>
      <button
        type="button"
        onClick={() => setFontSize((s) => Math.min(FONT_MAX, s + FONT_STEP))}
        disabled={fontSize >= FONT_MAX}
        className={btnBase}
        title="글자 크게"
      >
        <Plus className="h-3.5 w-3.5" />
        <span className="sr-only">글자 크게</span>
      </button>
      {onExpand && (
        <button
          type="button"
          onClick={onExpand}
          className={btnBase}
          title="전체화면으로 보기"
        >
          <Maximize2 className="h-3.5 w-3.5" />
          <span className="sr-only">{label} 전체화면으로 보기</span>
        </button>
      )}
    </div>
  );
}

function DartViewer({
  slug,
  kind,
  label,
}: {
  slug: string;
  kind: "business" | "notes";
  label: string;
}) {
  const [html, setHtml] = useState<string | null>(null);
  const [text, setText] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(false);
  const [fontSize, setFontSize] = useState(FONT_DEFAULT);
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    let plain = "";
    if (html) {
      plain = new DOMParser().parseFromString(html, "text/html").body.textContent ?? "";
    } else if (text) {
      plain = text;
    }
    if (!plain.trim()) return;
    try {
      await navigator.clipboard.writeText(plain);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // clipboard API 미지원 / 권한 거부 — silent fail
    }
  };

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setHtml(null);
    setText(null);
    setError(null);
    (async () => {
      const base = `/api/companies/${encodeURIComponent(slug)}/dart/${kind}`;
      try {
        const r = await fetch(`${base}.html`);
        if (r.ok) {
          const raw = await r.text();
          const decoded = decodeEscapedDartTags(raw);
          const safe = DOMPurify.sanitize(decoded, {
            ALLOWED_TAGS,
            ALLOWED_ATTR,
          });
          if (!cancelled) setHtml(safe);
          return;
        }
      } catch (_) {
        // fall through
      }
      try {
        const r2 = await fetch(`${base}.txt`);
        if (!r2.ok) throw new Error(`${r2.status}`);
        const t = await r2.text();
        if (!cancelled) setText(t);
      } catch (e) {
        if (!cancelled) setError(String(e));
      }
    })().finally(() => {
      if (!cancelled) setLoading(false);
    });
    return () => {
      cancelled = true;
    };
  }, [slug, kind]);

  if (loading) {
    return (
      <div className="flex items-center gap-2 py-6 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        불러오는 중…
      </div>
    );
  }
  if (error && !html && !text) {
    return <p className="py-4 text-sm text-muted-foreground">데이터 없음 ({error})</p>;
  }
  const copyBtnClass =
    "absolute bottom-3 right-3 z-10 inline-flex h-7 items-center gap-1.5 rounded-md border bg-background/85 px-2 text-xs text-muted-foreground backdrop-blur-sm transition-colors hover:bg-background hover:text-foreground disabled:opacity-40 disabled:hover:bg-background/85 disabled:hover:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring";

  return (
    <>
      <div className="relative">
        <DartToolbar
          fontSize={fontSize}
          setFontSize={setFontSize}
          onExpand={() => setExpanded(true)}
          label={label}
        />
        <button
          type="button"
          onClick={handleCopy}
          disabled={!html && !text}
          className={copyBtnClass}
          title="본문 전체 복사"
        >
          {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
          {copied ? "복사됨" : "전체복사"}
        </button>
        <div className="h-[60vh] overflow-auto rounded-md border bg-muted/20">
          <DartContent html={html} text={text} fontSize={fontSize} />
        </div>
      </div>

      <Dialog open={expanded} onOpenChange={setExpanded}>
        <DialogContent
          className="flex h-[95vh] w-[95vw] max-w-[95vw] flex-col gap-3 p-4 sm:max-w-[95vw]"
        >
          <DialogHeader className="shrink-0">
            <DialogTitle className="text-base">{label}</DialogTitle>
          </DialogHeader>
          <div className="relative min-h-0 flex-1 overflow-auto rounded-md border bg-muted/20">
            <DartToolbar
              fontSize={fontSize}
              setFontSize={setFontSize}
              label={label}
            />
            <button
              type="button"
              onClick={handleCopy}
              disabled={!html && !text}
              className={copyBtnClass}
              title="본문 전체 복사"
            >
              {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
              {copied ? "복사됨" : "전체복사"}
            </button>
            <DartContent html={html} text={text} fontSize={fontSize} />
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}

function fmtDate(s?: string): string {
  if (!s) return "—";
  if (s.length === 8) return `${s.slice(0, 4)}-${s.slice(4, 6)}-${s.slice(6, 8)}`;
  return s;
}
