"""Atomic write to Excel Col 18 (심사역 최종 판단), preserving Col 14 formula."""
from __future__ import annotations

import os
import shutil
import time
from pathlib import Path

import openpyxl

REVIEWER_FINAL_COL = 18  # 1-based


def write_reviewer_final(
    excel_path: Path,
    backup_dir: Path,
    excel_row: int,
    value: str | None,
) -> Path:
    """
    Set Col 18 to `value` (or clear if None).
    - data_only=False keeps Col 14 formulas intact.
    - Backup is taken before write.
    - Atomic via temp file + os.replace.
    Returns backup path.
    """
    if not excel_path.exists():
        raise FileNotFoundError(excel_path)
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup = backup_dir / f"{excel_path.stem}.{int(time.time())}.bak.xlsx"
    shutil.copy2(excel_path, backup)

    wb = openpyxl.load_workbook(excel_path, data_only=False)  # KEEP formulas
    try:
        ws = wb.active
        cell = ws.cell(row=excel_row, column=REVIEWER_FINAL_COL)
        cell.value = value if value else None
        tmp = excel_path.with_suffix(excel_path.suffix + ".tmp")
        wb.save(tmp)
    finally:
        wb.close()
    os.replace(tmp, excel_path)
    return backup
