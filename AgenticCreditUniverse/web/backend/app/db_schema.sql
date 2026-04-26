-- 크레딧 유니버스 인덱스 (rebuild on backend startup)
-- 매 빌드마다 DROP + CREATE — 998행 풀 빌드는 < 200ms.

CREATE TABLE companies (
  slug              TEXT PRIMARY KEY,            -- master.json key 또는 unresolved::row::norm_issuer
  excel_row         INTEGER NOT NULL,            -- 1-based (header=1)
  issuer            TEXT,                        -- Col 1
  request_class     TEXT,                        -- Col 2
  industry_2026     TEXT,                        -- Col 3 (헤더에 \n 있음)
  industry          TEXT,                        -- Col 4
  rating_prev       TEXT,                        -- Col 5  25.2H 신용등급
  watch_prev        TEXT,                        -- Col 6  25.2H 등급전망 (P/S/N)
  rating_curr       TEXT,                        -- Col 7  26.1H 신용등급
  watch_curr        TEXT,                        -- Col 8  26.1H 등급전망
  universe_prev     TEXT,                        -- Col 9  25.2H 유니버스 (O/△/X)
  universe_curr_ai  TEXT,                        -- Col 10 26.1H 유니버스 = AI 판단
  manager           TEXT,                        -- Col 11 담당
  comment_prev      TEXT,                        -- Col 12 25.2H 검토 코멘트
  comment_curr      TEXT,                        -- Col 13 26.1H 검토 코멘트
  movement          TEXT,                        -- Col 14 EVALUATED ▲/▽/-/""
  group_name        TEXT,                        -- Col 15 그룹사
  ai_judgment       TEXT,                        -- Col 16 AI 판단
  ai_rationale      TEXT,                        -- Col 17 AI 판단 사유
  reviewer_final    TEXT,                        -- Col 18 심사역 최종 판단 (UI 쓰기 대상)
  -- master.json 보강
  stock_code        TEXT,
  corp_code         TEXT,
  cmp_cd            TEXT,
  official_name     TEXT,
  group_master      TEXT,
  unresolved        INTEGER NOT NULL DEFAULT 0,  -- 1 = master 매핑 없음
  last_updated_utc  TEXT,                        -- max(mtime) of comments/nice/dart/news
  created_at        TEXT NOT NULL
);

CREATE INDEX idx_companies_unresolved ON companies(unresolved);
CREATE INDEX idx_companies_universe   ON companies(universe_curr_ai, reviewer_final);
CREATE INDEX idx_companies_issuer     ON companies(issuer);

CREATE TABLE review_status (
  slug          TEXT PRIMARY KEY,
  status        TEXT NOT NULL CHECK (status IN ('done','none')),
  universe      TEXT,                            -- O/△/X
  agree_with_ai INTEGER,                         -- 0/1
  note          TEXT,
  reviewed_by   TEXT,
  reviewed_at   TEXT
);

CREATE TABLE period_config (
  k TEXT PRIMARY KEY,
  v TEXT NOT NULL                                -- JSON string
);
