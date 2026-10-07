"""구글 시트 사용 내역을 SQL 한 파일로 정리하고 DB에 넣습니다.

파일은 data/sheet_rows.sql 입니다. data 디렉터리는 저장소와 이미지에 포함되지 않습니다.

사용법:
  python -m app.modules.overtime.sheet_dump export
  python -m app.modules.overtime.sheet_dump load
"""

import asyncio
import hashlib
import json
import sys
from pathlib import Path

from sqlalchemy import text

from app.core.database import SessionLocal
from app.modules.overtime.sheets import list_projects, load_sheet

DUMP_SQL = Path(__file__).resolve().parents[3] / "data" / "sheet_rows.sql"
DUMP_COLUMNS = [
    "순번",
    "영수증 제출",
    "사용일자",
    "사용금액",
    "연구비항목",
    "사용목적",
    "사용시각",
    "사용처",
    "회의시간",
    "회의지역",
    "회의장소",
    "총인원",
    "회의참석자",
    "회의목적",
    "회의내용",
    "참석인원",
    "글자수",
]


def clean_cell(value: str) -> str:
    text_value = str(value or "").replace("\r\n", "\n").replace("\r", "\n")
    lines = [" ".join(line.split()) for line in text_value.split("\n")]
    return "\n".join(line for line in lines if line).strip()


def normalize_row(values: dict[str, str]) -> dict[str, str]:
    cleaned = {column: "" for column in DUMP_COLUMNS}
    for column in DUMP_COLUMNS:
        if column == "글자수":
            continue
        cleaned[column] = clean_cell(values.get(column, ""))
    if not cleaned["총인원"]:
        cleaned["총인원"] = clean_cell(values.get("참석인원", ""))
    if not cleaned["참석인원"]:
        cleaned["참석인원"] = cleaned["총인원"]
    cleaned["글자수"] = str(len(cleaned["회의내용"]))
    return cleaned


def row_key(values: dict[str, str]) -> str:
    parts = [values.get(name, "").strip() for name in ("순번", "사용일자", "사용금액", "사용시각", "사용처", "연구비항목")]
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:32]


def _quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def write_dump(projects: list[dict]) -> int:
    statements = ["DELETE FROM sheet_rows;"]
    count = 0
    for project in projects:
        gid = str(project["gid"])
        name = str(project["name"])
        for row in project["rows"]:
            payload = json.dumps(row["values"], ensure_ascii=False, separators=(",", ":"))
            statements.append(
                "INSERT INTO sheet_rows (project_gid, project_name, row_key, data, created_at) VALUES ("
                f"{_quote(gid)}, {_quote(name)}, {_quote(str(row['row_key']))}, "
                f"{_quote(payload)}::json, CURRENT_TIMESTAMP);"
            )
            count += 1
    DUMP_SQL.parent.mkdir(parents=True, exist_ok=True)
    DUMP_SQL.write_text("\n".join(statements) + "\n", encoding="utf-8")
    print(f"합계 {count}건 -> {DUMP_SQL.name}")
    return count


def _statements(sql: str):
    chunk: list[str] = []
    quoted = False
    index = 0
    while index < len(sql):
        char = sql[index]
        if char == "'":
            chunk.append(char)
            if quoted and index + 1 < len(sql) and sql[index + 1] == "'":
                chunk.append("'")
                index += 2
                continue
            quoted = not quoted
            index += 1
            continue
        if char == ";" and not quoted:
            statement = "".join(chunk).strip()
            if statement:
                yield statement
            chunk = []
            index += 1
            continue
        chunk.append(char)
        index += 1
    tail = "".join(chunk).strip()
    if tail:
        yield tail


async def export_sheets() -> int:
    projects = await list_projects()
    dumped = []
    for project in projects:
        gid = str(project["gid"])
        name = str(project["name"]).strip()
        table = await load_sheet(gid, name)
        seen: set[str] = set()
        rows = []
        for source in table.rows:
            values = normalize_row(source)
            key = row_key(values)
            suffix = 2
            while key in seen:
                key = f"{row_key(values)}-{suffix}"
                suffix += 1
            seen.add(key)
            rows.append({"row_key": key, "values": values})
        dumped.append({"gid": gid, "name": name, "rows": rows})
        print(f"{name}: {len(rows)}건")
    return write_dump(dumped)


def load_sheets() -> int:
    if not DUMP_SQL.is_file():
        raise SystemExit("data/sheet_rows.sql 이 없습니다. 먼저 export 를 실행해 주세요.")
    sql = DUMP_SQL.read_text(encoding="utf-8")
    db = SessionLocal()
    inserted = 0
    try:
        for statement in _statements(sql):
            db.execute(text(statement))
            if statement.upper().startswith("INSERT"):
                inserted += 1
        db.commit()
    finally:
        db.close()
    print(f"DB에 {inserted}건을 넣었습니다.")
    return inserted


def main() -> None:
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    if command == "export":
        asyncio.run(export_sheets())
        return
    if command == "load":
        load_sheets()
        return
    raise SystemExit("사용법: python -m app.modules.overtime.sheet_dump export|load")


if __name__ == "__main__":
    main()
