import csv
import io
import re
import time
from dataclasses import dataclass

import httpx
from fastapi import HTTPException, status

from app.core.config import settings

_SHEET_RE = re.compile(
    r'items\.push\(\{name:\s*"(?P<name>(?:\\.|[^"\\])*)".*?gid:\s*"(?P<gid>\d+)"',
    re.DOTALL,
)

FALLBACK_SHEETS: list[tuple[str, str]] = [
    ("0", "K-Sensor"),
    ("1047653147", "HMI"),
    ("463611148", "초연결지능"),
    ("567403221", "가전AX"),
    ("1994646511", "ITRC"),
    ("1235852105", "ITRC간접비"),
    ("1445657603", "Digital Twin"),
    ("644125894", "트러스트AI"),
]

_cache: dict[str, tuple[float, object]] = {}


@dataclass
class SheetTable:
    gid: str
    name: str
    columns: list[str]
    notes: list[str]
    common_notes: list[str]
    rows: list[dict[str, str]]


def _cached(key: str) -> object | None:
    hit = _cache.get(key)
    if hit is None:
        return None
    stored_at, value = hit
    if time.monotonic() - stored_at > settings.sheet_cache_seconds:
        return None
    return value


def _store(key: str, value: object) -> object:
    _cache[key] = (time.monotonic(), value)
    return value


async def _fetch_text(url: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=40, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.text
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="스프레드시트를 불러오지 못했습니다. 공유 설정을 확인해 주세요.",
        ) from exc


_GUIDE_START = re.compile(r"^(?:★|[-－]|\d+\.)")


def common_guide_lines(rows: list[list[str]]) -> list[str]:
    """작성 안내에서 과제 공통 문장만 고릅니다. 카드, 잔액, 참여 인원 칸은 뺍니다."""
    lines: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for index, raw in enumerate(row):
            text = re.sub(r"\s+", " ", raw).strip()
            if not text or text in seen:
                continue
            shared_column = index == 1 and _GUIDE_START.match(text) is not None
            writing_tip = text.startswith("작성") or "글자수" in text
            if shared_column or writing_tip:
                lines.append(text)
                seen.add(text)
    return lines


def parse_sheet_csv(text: str) -> tuple[list[str], list[str], list[str], list[dict[str, str]]]:
    rows = list(csv.reader(io.StringIO(text)))
    header_idx = None
    for index, row in enumerate(rows):
        if any(cell.strip() == "사용일자" for cell in row):
            header_idx = index
            break
    if header_idx is None:
        return [], [], [], []

    header = rows[header_idx]
    indexes = [i for i, cell in enumerate(header) if cell.strip()]
    columns = [header[i].strip() for i in indexes]

    notes: list[str] = []
    for row in rows[:header_idx]:
        cells = [cell.strip() for cell in row if cell.strip()]
        if cells:
            notes.append(" · ".join(cells))
    common_notes = common_guide_lines(rows[:header_idx])

    data: list[dict[str, str]] = []
    for row in rows[header_idx + 1 :]:
        values = {
            columns[pos]: (row[col].strip() if col < len(row) else "")
            for pos, col in enumerate(indexes)
        }
        if not values.get("사용일자"):
            continue
        if values.get("영수증 제출") == "예시":
            continue
        data.append(values)
    return columns, notes, common_notes, data


async def list_projects() -> list[dict[str, str]]:
    cached = _cached("projects")
    if isinstance(cached, list):
        return cached

    html = await _fetch_text(
        f"https://docs.google.com/spreadsheets/d/{settings.sheet_id}/htmlview"
    )
    found = [(match.group("gid"), match.group("name")) for match in _SHEET_RE.finditer(html)]
    sheets = found or FALLBACK_SHEETS
    projects = [{"gid": gid, "name": name} for gid, name in sheets]
    return _store("projects", projects)  # type: ignore[return-value]


async def load_sheet(gid: str, name: str) -> SheetTable:
    cache_key = f"sheet:{gid}"
    cached = _cached(cache_key)
    if isinstance(cached, SheetTable):
        cached.name = name
        return cached

    csv_text = await _fetch_text(
        f"https://docs.google.com/spreadsheets/d/{settings.sheet_id}/export?format=csv&gid={gid}"
    )
    columns, notes, common_notes, rows = parse_sheet_csv(csv_text)
    if not columns:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="시트에서 표 헤더를 찾지 못했습니다.",
        )
    table = SheetTable(gid=gid, name=name, columns=columns, notes=notes, common_notes=common_notes, rows=rows)
    return _store(cache_key, table)  # type: ignore[return-value]
