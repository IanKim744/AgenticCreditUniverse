from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from ..auth import require_session
from ..deps import get_db
from ..excel_writer import write_reviewer_final
from ..schemas import ReviewIn
from ..settings import Settings, get_settings

router = APIRouter(prefix="/api/companies", tags=["review"])


_UNIVERSE_RANK = {"O": 3, "△": 2, "X": 1}


def _compute_movement(prev: str | None, decision: str | None) -> str | None:
    """전기 ↔ 당기 결정 비교. build_index._compute_movement 와 동일 로직."""
    if not prev or not decision:
        return None
    p = _UNIVERSE_RANK.get(prev.strip())
    c = _UNIVERSE_RANK.get(decision.strip())
    if p is None or c is None:
        return None
    if c > p:
        return "▲"
    if c < p:
        return "▽"
    return "-"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _upsert_review_file(path: Path, slug: str, payload: dict[str, Any] | None) -> None:
    data: dict[str, Any] = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
    if payload is None:
        data.pop(slug, None)
    else:
        data[slug] = payload
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _ensure_company(con: sqlite3.Connection, slug: str) -> sqlite3.Row:
    row = con.execute(
        "SELECT slug, excel_row, unresolved FROM companies WHERE slug=?", (slug,)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found")
    if row["unresolved"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="unresolved_cannot_review")
    return row


@router.post("/{slug}/review")
def post_review(
    slug: str,
    body: ReviewIn,
    sess: dict = Depends(require_session),
    s: Settings = Depends(get_settings),
    con: sqlite3.Connection = Depends(get_db),
) -> dict[str, Any]:
    row = _ensure_company(con, slug)
    user = sess["u"]
    now = _now_iso()
    universe = body.universe

    # 1) Excel write
    write_reviewer_final(s.excel_path, s.excel_backup_dir, row["excel_row"], universe)

    # 2) review_status.json upsert
    payload = {
        "status": "done",
        "universe": universe,
        "agree_with_ai": bool(body.agree_with_ai),
        "note": body.note,
        "reviewed_by": user,
        "reviewed_at": now,
    }
    _upsert_review_file(s.review_status_path, slug, payload)

    # 3) SQLite mirror — reviewer_final + movement 동시 갱신
    cur_row = con.execute(
        "SELECT universe_prev, universe_curr_ai FROM companies WHERE slug=?", (slug,)
    ).fetchone()
    new_movement = _compute_movement(
        cur_row["universe_prev"] if cur_row else None,
        universe or (cur_row["universe_curr_ai"] if cur_row else None),
    )
    con.execute(
        "UPDATE companies SET reviewer_final=?, movement=? WHERE slug=?",
        (universe, new_movement, slug),
    )
    con.execute(
        """INSERT INTO review_status (slug, status, universe, agree_with_ai, note, reviewed_by, reviewed_at)
           VALUES (?,?,?,?,?,?,?)
           ON CONFLICT(slug) DO UPDATE SET
             status=excluded.status,
             universe=excluded.universe,
             agree_with_ai=excluded.agree_with_ai,
             note=excluded.note,
             reviewed_by=excluded.reviewed_by,
             reviewed_at=excluded.reviewed_at""",
        (slug, "done", universe, int(bool(body.agree_with_ai)), body.note, user, now),
    )
    con.commit()
    return {"ok": True, "review_status": payload}


@router.delete("/{slug}/review")
def delete_review(
    slug: str,
    _sess: dict = Depends(require_session),
    s: Settings = Depends(get_settings),
    con: sqlite3.Connection = Depends(get_db),
) -> dict[str, Any]:
    row = _ensure_company(con, slug)

    write_reviewer_final(s.excel_path, s.excel_backup_dir, row["excel_row"], None)
    _upsert_review_file(s.review_status_path, slug, None)
    # 검수 해제 시 의견변동은 AI 판단 vs 전기로 폴백
    cur_row = con.execute(
        "SELECT universe_prev, universe_curr_ai FROM companies WHERE slug=?", (slug,)
    ).fetchone()
    new_movement = _compute_movement(
        cur_row["universe_prev"] if cur_row else None,
        cur_row["universe_curr_ai"] if cur_row else None,
    )
    con.execute(
        "UPDATE companies SET reviewer_final=NULL, movement=? WHERE slug=?",
        (new_movement, slug),
    )
    con.execute("DELETE FROM review_status WHERE slug=?", (slug,))
    con.commit()
    return {"ok": True, "review_status": {"status": "none"}}
