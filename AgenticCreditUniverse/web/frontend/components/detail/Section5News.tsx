import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ExternalLink } from "lucide-react";

interface Citation {
  url: string;
  title: string;
  date?: string | null;
  domain?: string;
}

interface Props {
  id: string;
  reportMd: string | null;
  citations: Citation[];
}

const NOISY_HOSTS = [
  "tistory.com",
  "youtube.com",
  "namu.wiki",
  "catch.co.kr",
  "jobkorea.co.kr",
  "saramin.co.kr",
  "jasoseol.com",
  "prime-career.com",
  "teamblind.com",
  "dcinside.com",
  "fmkorea.com",
  "clien.net",
  "ruliweb.com",
  "ppomppu.co.kr",
  "cafe.daum.net",
  "reddit.com",
  "quora.com",
  "blog.naver.com",
  "cafe.naver.com",
  "m.blog.naver.com",
  "post.naver.com",
  "contents.premium.naver.com",
];

function isNoisyHost(host?: string): boolean {
  if (!host) return false;
  const h = host.toLowerCase();
  return NOISY_HOSTS.some((n) => h === n || h.endsWith("." + n));
}

export function Section5News({ id, reportMd, citations }: Props) {
  const cleaned = reportMd ? stripCitationsSection(stripSpecHeader(reportMd)) : null;
  const visibleCitations = citations.filter((c) => !isNoisyHost(c.domain));
  return (
    <section id={id} className="space-y-4 scroll-mt-32">
      <h2 className="text-lg font-semibold">뉴스 / 리스크</h2>
      {!cleaned ? (
        <div className="rounded-lg border bg-card p-8 text-center text-sm text-muted-foreground">
          뉴스 리포트 미수집
        </div>
      ) : (
        <div
          className="rounded-lg border bg-card p-5"
          style={{ boxShadow: "var(--shadow-card)" }}
        >
          <div className="prose prose-sm max-w-none text-sm leading-relaxed
                          [&_h1]:text-base [&_h1]:font-semibold [&_h1]:mb-3 [&_h1]:mt-0
                          [&_h2]:text-sm  [&_h2]:font-semibold [&_h2]:mt-4 [&_h2]:mb-2
                          [&_h3]:text-sm  [&_h3]:font-semibold [&_h3]:mt-3 [&_h3]:mb-1.5
                          [&_p]:my-2 [&_li]:my-0.5">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{cleaned}</ReactMarkdown>
          </div>
        </div>
      )}
      {visibleCitations.length > 0 && (
        <div
          className="rounded-lg border bg-card p-4"
          style={{ boxShadow: "var(--shadow-card)" }}
        >
          <div className="mb-2 text-sm font-medium">인용 ({visibleCitations.length})</div>
          <ul className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
            {visibleCitations.map((c, i) => (
              <li key={i}>
                <a
                  href={c.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 text-xs hover:text-primary transition-colors"
                >
                  {c.domain && (
                    <img
                      alt=""
                      src={`https://www.google.com/s2/favicons?domain=${c.domain}&sz=16`}
                      className="h-3.5 w-3.5 shrink-0 rounded-sm"
                    />
                  )}
                  <span className="truncate">{c.title || c.url}</span>
                  {c.date && (
                    <span className="shrink-0 text-[10px] text-muted-foreground tabular-nums">
                      {c.date.slice(0, 10)}
                    </span>
                  )}
                  <ExternalLink className="h-3 w-3 shrink-0 text-muted-foreground" />
                </a>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

function stripSpecHeader(md: string): string {
  const lines = md.split("\n");
  const firstH1 = lines.findIndex((l) => /^#\s+/.test(l));
  if (firstH1 < 0) return md.trim();
  if (!/^#\s+리스크\s*분석\s*리포트/.test(lines[firstH1]!)) return md.trim();
  const hrIdx = lines.findIndex((l, i) => i > firstH1 && /^---\s*$/.test(l));
  if (hrIdx >= 0) return lines.slice(hrIdx + 1).join("\n").trim();
  const nextH = lines.findIndex((l, i) => i > firstH1 && /^##?\s+/.test(l));
  return nextH < 0 ? "" : lines.slice(nextH).join("\n").trim();
}

function stripCitationsSection(md: string): string {
  const lines = md.split("\n");
  const idx = lines.findIndex(
    (l) =>
      /^##\s+출처(\s|\(|（|$)/.test(l) ||
      /^##\s+Perplexity\s*citations/i.test(l),
  );
  if (idx < 0) return md;
  let cut = idx;
  for (let i = idx - 1; i >= 0; i--) {
    if (lines[i]!.trim() === "") continue;
    if (/^---\s*$/.test(lines[i]!)) cut = i;
    break;
  }
  return lines.slice(0, cut).join("\n").trim();
}
