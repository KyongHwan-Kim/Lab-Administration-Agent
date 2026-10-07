import base64
import hashlib
import json
import re
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.overtime.categories import ExpenseCategory, normalize_expense_category
from app.modules.overtime.extract_agent import ExtractionError, UsageExtractAgent
from app.modules.overtime.models import OvertimeEntry, SheetReceipt, UsageMemo, WorkLog
from app.modules.overtime.columns import DRAFT_COLUMNS
from app.modules.overtime.pdf import MAX_IMAGES, build_column_pdf, build_evidence_pdf, read_image_files
from app.modules.overtime.sheets import SheetTable, load_sheet
from app.modules.overtime.work_log import build_usage_document, render_document, render_overtime_log
from app.modules.projects.models import ProjectCard
from app.modules.projects.service import find_project_by_key, match_card_project
from app.modules.users.models import User

AUTO_COLUMNS = {"순번", "글자수"}
APP_FIELDS = ("메모", "추천인원")
MAX_FIELD_LENGTH = 4000
LOCAL_COLUMNS = [
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
    "회의내용",
    "글자수",
]


async def project_table(db: Session, user: User, gid: str) -> dict:
    project = find_project_by_key(db, gid)
    sheet = await _sheet_for(project)
    entries = (
        db.query(OvertimeEntry)
        .filter(OvertimeEntry.project_gid == gid)
        .order_by(OvertimeEntry.id)
        .all()
    )
    linked = {
        receipt.row_key: receipt
        for receipt in db.query(SheetReceipt).filter(SheetReceipt.project_gid == project.entry_key).all()
    }
    memos = {
        item.row_key: item.memo
        for item in db.query(UsageMemo).filter(UsageMemo.project_gid == sheet.gid).all()
    }
    rows = []
    for row in sheet.rows:
        key = sheet_row_key(row)
        receipt = linked.get(key)
        shown = dict(row)
        shown["메모"] = memos.get(key, "")
        shown["추천인원"] = ""
        rows.append(
            {
                "source": "sheet",
                "values": shown,
                "row_key": key,
                "has_pdf": bool(receipt and Path(receipt.pdf_path).is_file()),
            }
        )
    for entry in entries:
        rows.append(
            {
                "source": "app",
                "id": entry.id,
                "values": _present_values(sheet.columns, entry.data),
                "has_pdf": bool(entry.pdf_path),
                "can_delete": _can_manage(user, entry),
                "can_edit": _can_manage(user, entry),
            }
        )
    return {
        "gid": sheet.gid,
        "name": sheet.name,
        "columns": sheet.columns,
        "notes": sheet.notes,
        "common_notes": sheet.common_notes,
        "rows": rows,
    }


async def create_entry(
    db: Session,
    user: User,
    gid: str,
    payload: str,
    delivery: list[UploadFile] | None,
    receipt: list[UploadFile] | None,
) -> dict:
    project = find_project_by_key(db, gid)
    sheet = await _sheet_for(project)
    fields = _parse_payload(payload)
    values = _build_values(db, sheet, fields)
    images = await read_image_files(delivery)
    images.extend(await read_image_files(receipt))

    entry = OvertimeEntry(
        project_gid=sheet.gid,
        project_name=sheet.name,
        data=values,
        created_by=user.id,
    )
    db.add(entry)
    db.flush()
    if images:
        path = settings.pdf_dir / f"{entry.id}.pdf"
        path.write_bytes(build_column_pdf(images))
        entry.pdf_path = str(path)
    db.commit()
    db.refresh(entry)
    return {
        "id": entry.id,
        "values": entry.data,
        "has_pdf": bool(entry.pdf_path),
    }


def unassigned_table(db: Session, user: User) -> dict:
    entries = (
        db.query(OvertimeEntry)
        .filter(OvertimeEntry.project_gid.is_(None))
        .order_by(OvertimeEntry.id)
        .all()
    )
    rows = []
    for entry in entries:
        rows.append(
            {
                "source": "app",
                "id": entry.id,
                "values": _present_values(DRAFT_COLUMNS, entry.data),
                "has_pdf": bool(entry.pdf_path),
                "can_delete": _can_manage(user, entry),
                "can_edit": _can_manage(user, entry),
            }
        )
    return {
        "gid": None,
        "name": "프로젝트 할당 전",
        "columns": DRAFT_COLUMNS,
        "notes": [],
        "common_notes": [],
        "rows": rows,
    }


async def create_receipt_entries(
    db: Session,
    user: User,
    delivery: list[UploadFile] | None,
    receipt: list[UploadFile] | None,
) -> list[dict]:
    delivery_images = await read_image_files(delivery)
    receipt_images = await read_image_files(receipt)
    images = [*delivery_images, *receipt_images]
    if not images:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="업로드할 이미지를 선택해 주세요.")
    if len(images) > MAX_IMAGES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"이미지는 한 번에 {MAX_IMAGES}장까지 올릴 수 있습니다.",
        )
    try:
        cards = [(card.project.name, card.number) for card in db.query(ProjectCard).all() if card.project is not None]
        drafted = await UsageExtractAgent().run(delivery_images, receipt_images, cards)
    except ExtractionError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    evidence = build_evidence_pdf(delivery_images, receipt_images)
    created: list[OvertimeEntry] = []
    for item in drafted:
        project = match_card_project(db, item.card_number, item.matched_project)
        entry = OvertimeEntry(project_gid=None, project_name=None, data=item.values, created_by=user.id)
        if project is not None:
            await _place_extracted(db, entry, project, item.values)
        db.add(entry)
        db.flush()
        path = settings.pdf_dir / f"{entry.id}.pdf"
        path.write_bytes(evidence)
        entry.pdf_path = str(path)
        created.append(entry)
    db.commit()
    for entry in created:
        db.refresh(entry)
    return [{"id": entry.id, "project_name": entry.project_name or "", "values": entry.data} for entry in created]


def update_entry(db: Session, user: User, entry_id: int, fields: dict[str, str]) -> dict:
    entry = db.get(OvertimeEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="항목을 찾을 수 없습니다.")
    if not _can_manage(user, entry):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="본인이 추가한 항목만 수정할 수 있습니다.")
    stored = entry.data or {}
    if entry.project_gid is None:
        current = {column: str(stored.get(column, "")) for column in DRAFT_COLUMNS}
        allowed = set(DRAFT_COLUMNS)
    else:
        current = {str(key): "" if value is None else str(value) for key, value in stored.items()}
        allowed = (set(current) | set(fields)) - AUTO_COLUMNS
    for column, raw in fields.items():
        if column not in allowed or column in APP_FIELDS:
            continue
        current[column] = _clean_field(column, raw)
    for key in APP_FIELDS:
        if key in fields:
            current[key] = _clean_field(key, fields[key])
        elif key in stored:
            current[key] = str(stored.get(key) or "")
    if entry.project_gid is not None:
        if not current.get("사용일자", "").strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="사용일자를 입력해 주세요.")
        if "글자수" in (entry.data or {}) or "회의내용" in current:
            current["글자수"] = str(len(current.get("회의내용", "")))
    if "연구비항목" in current:
        current["연구비항목"] = normalize_expense_category(
            current.get("연구비항목", ""),
            required=entry.project_gid is not None,
        )
    entry.data = current
    db.commit()
    db.refresh(entry)
    return {"id": entry.id, "values": entry.data}


async def _place_extracted(db: Session, entry: OvertimeEntry, project, values: dict[str, str]) -> None:
    sheet = await _sheet_for(project)
    placed = {column: values.get(column, "").strip() for column in sheet.columns if column not in AUTO_COLUMNS}
    if "연구비항목" in placed:
        placed["연구비항목"] = normalize_expense_category(placed.get("연구비항목", ""), required=False)
    if "순번" in sheet.columns:
        placed["순번"] = str(_next_sequence(db, sheet.gid))
    if "글자수" in sheet.columns:
        placed["글자수"] = str(len(placed.get("회의내용", "")))
    entry.project_gid = sheet.gid
    entry.project_name = sheet.name
    stored = {column: placed.get(column, "") for column in sheet.columns}
    for key in APP_FIELDS:
        text = str(values.get(key, "") or "").strip()
        if text:
            stored[key] = text
    entry.data = stored


async def assign_entry(db: Session, user: User, entry_id: int, gid: str) -> dict:
    entry = _own_unassigned(db, user, entry_id)
    project = find_project_by_key(db, gid)
    sheet = await _sheet_for(project)
    stored = entry.data or {}
    fields = {column: str(stored.get(column, "")) for column in sheet.columns}
    for key in APP_FIELDS:
        fields[key] = str(stored.get(key, ""))
    entry.project_gid = sheet.gid
    entry.project_name = sheet.name
    entry.data = _build_values(db, sheet, fields)
    db.commit()
    db.refresh(entry)
    return {"id": entry.id, "values": entry.data}


def delete_entry(db: Session, user: User, entry_id: int) -> None:
    entry = db.get(OvertimeEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="항목을 찾을 수 없습니다.")
    if not user.is_admin and entry.created_by != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="본인이 추가한 항목만 삭제할 수 있습니다.")
    if entry.pdf_path:
        path = Path(entry.pdf_path)
        if path.is_file():
            path.unlink()
    db.delete(entry)
    db.commit()


async def attach_entry_pdf(db: Session, user: User, entry_id: int, files: list[UploadFile] | None) -> dict:
    entry = db.get(OvertimeEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="항목을 찾을 수 없습니다.")
    if not _can_manage(user, entry):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="본인이 추가한 항목만 영수증을 연결할 수 있습니다.")
    pdf = await receipt_pdf_bytes(files)
    path = settings.pdf_dir / f"{entry.id}.pdf"
    path.write_bytes(pdf)
    entry.pdf_path = str(path)
    db.commit()
    return {"has_pdf": True}


async def attach_sheet_receipt(db: Session, user: User, gid: str, row_key: str, files: list[UploadFile] | None) -> dict:
    project = find_project_by_key(db, gid)
    sheet = await _sheet_for(project)
    if row_key not in {sheet_row_key(row) for row in sheet.rows}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="연결할 사용 내역을 찾을 수 없습니다.")
    pdf = await receipt_pdf_bytes(files)
    path = settings.pdf_dir / f"sheet-{_safe_gid(gid)}-{row_key}.pdf"
    path.write_bytes(pdf)
    receipt = (
        db.query(SheetReceipt)
        .filter(SheetReceipt.project_gid == project.entry_key, SheetReceipt.row_key == row_key)
        .one_or_none()
    )
    if receipt is None:
        receipt = SheetReceipt(project_gid=project.entry_key, row_key=row_key, pdf_path=str(path), created_by=user.id)
        db.add(receipt)
    else:
        receipt.pdf_path = str(path)
    db.commit()
    return {"has_pdf": True}


def sheet_receipt_path(db: Session, gid: str, row_key: str) -> Path:
    project = find_project_by_key(db, gid)
    receipt = (
        db.query(SheetReceipt)
        .filter(SheetReceipt.project_gid == project.entry_key, SheetReceipt.row_key == row_key)
        .one_or_none()
    )
    if receipt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="연결된 영수증 PDF가 없습니다.")
    path = Path(receipt.pdf_path)
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="연결된 영수증 PDF가 없습니다.")
    return path


_FULL_USAGE_DATE = re.compile(r"(20\d{2})\s*[.\-/년]\s*(\d{1,2})\s*[.\-/월]\s*(\d{1,2})")
_SHORT_USAGE_DATE = re.compile(r"(?:^|\D)(\d{2})\s*[.\-/]\s*(\d{1,2})\s*[.\-/]\s*(\d{1,2})")


def usage_file_date(value: str | None) -> str:
    text = "" if value is None else str(value).strip()
    match = _FULL_USAGE_DATE.search(text)
    if match:
        year, month, day = match.groups()
        return f"{year[2:]}.{int(month):02d}.{int(day):02d}"
    match = _SHORT_USAGE_DATE.search(text)
    if match:
        year, month, day = match.groups()
        return f"{year}.{int(month):02d}.{int(day):02d}"
    return ""


def receipt_filename(values: dict) -> str:
    category = str(values.get("연구비항목", "")).strip()
    if category == ExpenseCategory.MEETING:
        label = "회의비_영수증"
    elif category == ExpenseCategory.OVERTIME:
        label = "초과근무_영수증"
    else:
        label = "영수증"
    stamp = usage_file_date(values.get("사용일자"))
    return f"[{stamp}] {label}.pdf" if stamp else f"{label}.pdf"


def work_log_filename(values: dict) -> str:
    stamp = usage_file_date(values.get("사용일자"))
    label = "초과근무_간접비"
    return f"[{stamp}] {label}.pdf" if stamp else f"{label}.pdf"


_SOURCE_KEY = re.compile(r"^(?:sheet:[0-9a-f]{32}|entry:\d+)$")


def save_work_log(db: Session, user: User, gid: str, values: dict[str, str], source_key: str) -> tuple[bytes, str]:
    if _SOURCE_KEY.fullmatch(source_key or "") is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="초과근무일지 대상을 확인할 수 없습니다.")
    project = find_project_by_key(db, gid)
    pdf = overtime_log_pdf(db, gid, values)
    filename = work_log_filename(values)
    document = _usage_document(db, gid, values)
    log = (
        db.query(WorkLog)
        .filter(WorkLog.project_gid == project.entry_key, WorkLog.source_key == source_key)
        .one_or_none()
    )
    now = datetime.utcnow()
    if log is None:
        log = WorkLog(
            project_gid=project.entry_key,
            project_name=project.name,
            source_key=source_key,
            filename=filename,
            usage_date=str(values.get("사용일자", "")).strip()[:32],
            store_name=str(values.get("사용처", "")).strip()[:200],
            document=document,
            pdf_path="",
            created_by=user.id,
            created_at=now,
            updated_at=now,
        )
        db.add(log)
        db.flush()
    else:
        log.project_name = project.name
        log.filename = filename
        log.usage_date = str(values.get("사용일자", "")).strip()[:32]
        log.store_name = str(values.get("사용처", "")).strip()[:200]
        log.document = document
        log.updated_at = now
    path = settings.pdf_dir / f"worklog-{log.id}.pdf"
    path.write_bytes(pdf)
    log.pdf_path = str(path)
    db.commit()
    return pdf, filename


def list_work_logs(db: Session) -> list[dict]:
    logs = db.query(WorkLog).order_by(WorkLog.updated_at.desc(), WorkLog.id.desc()).all()
    return [
        {
            "id": log.id,
            "project_gid": log.project_gid,
            "project_name": log.project_name,
            "filename": log.filename,
            "usage_date": log.usage_date,
            "store_name": log.store_name,
            "created_at": _utc_iso(log.updated_at or log.created_at),
        }
        for log in logs
    ]


def work_log_file(db: Session, log_id: int) -> tuple[Path, str]:
    log = _work_log(db, log_id)
    path = Path(log.pdf_path)
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="초과근무일지 파일이 없습니다.")
    return path, log.filename


def work_log_form(db: Session, log_id: int) -> dict:
    log = _work_log(db, log_id)
    return {
        "id": log.id,
        "project_gid": log.project_gid,
        "project_name": log.project_name,
        "filename": log.filename,
        "document": _present_document(db, log.document or {}),
    }


def create_work_log(db: Session, user: User, gid: str) -> dict:
    project = find_project_by_key(db, gid)
    document = build_usage_document(_project_profile(project), {})
    log = WorkLog(
        project_gid=project.entry_key,
        project_name=project.name,
        source_key=f"manual:{uuid.uuid4().hex}",
        filename="초과근무_간접비.pdf",
        usage_date="",
        store_name="",
        document=document,
        pdf_path="",
        created_by=user.id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(log)
    db.flush()
    _write_work_log(db, log, document)
    db.commit()
    db.refresh(log)
    return work_log_form(db, log.id)


def update_work_log(db: Session, log_id: int, document: dict) -> dict:
    log = _work_log(db, log_id)
    cleaned = _clean_document(document)
    log.document = cleaned
    log.usage_date = _document_date(cleaned)
    log.store_name = str(cleaned.get("place", ""))[:200]
    log.filename = _document_filename(cleaned)
    log.updated_at = datetime.utcnow()
    _write_work_log(db, log, cleaned)
    db.commit()
    return work_log_form(db, log.id)


def _work_log(db: Session, log_id: int) -> WorkLog:
    log = db.get(WorkLog, log_id)
    if log is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="초과근무일지를 찾을 수 없습니다.")
    return log


def _usage_document(db: Session, gid: str, values: dict[str, str]) -> dict:
    project = find_project_by_key(db, gid)
    category = str(values.get("연구비항목", "")).strip()
    if category != ExpenseCategory.OVERTIME:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="초과근무 항목만 초과근무일지를 만들 수 있습니다.")
    return build_usage_document(_project_profile(project), values)


def _project_profile(project) -> dict[str, str]:
    return {
        "project_number": project.project_number or "",
        "principal_investigator": project.principal_investigator or "",
        "funding_agency": project.funding_agency or "",
        "program_name": project.program_name or "",
        "research_title": project.research_title or "",
    }


def _write_work_log(db: Session, log: WorkLog, document: dict) -> None:
    path = settings.pdf_dir / f"worklog-{log.id}.pdf"
    path.write_bytes(render_document(document, _signature_map(db)))
    log.pdf_path = str(path)


def _signature_map(db: Session) -> dict[str, Path]:
    signatures: dict[str, Path] = {}
    for account in db.query(User).all():
        if not account.signature_path:
            continue
        path = Path(account.signature_path)
        if path.is_file():
            signatures[account.username] = path
            signatures[account.label] = path
    return signatures


def _present_document(db: Session, document: dict) -> dict:
    signatures = _signature_map(db)
    rows = []
    for row in document.get("rows") or []:
        worker = str(row.get("worker", ""))
        signature = _find_signature_path(worker, signatures)
        rows.append(
            {
                "year": str(row.get("year", "")),
                "month": str(row.get("month", "")),
                "day": str(row.get("day", "")),
                "worker": worker,
                "time": str(row.get("time", "")),
                "signature": _data_url(signature),
            }
        )
    investigator = str(document.get("principal_investigator", ""))
    return {
        "project_number": str(document.get("project_number", "")),
        "principal_investigator": investigator,
        "funding_agency": str(document.get("funding_agency", "")),
        "program_name": str(document.get("program_name", "")),
        "research_title": str(document.get("research_title", "")),
        "content": str(document.get("content", "")),
        "place": str(document.get("place", "")),
        "rows": rows or [{"year": "", "month": "", "day": "", "worker": "", "time": "", "signature": ""}],
        "pi_signature": _data_url(_find_signature_path(investigator, signatures)),
    }


def _clean_document(document: dict) -> dict:
    rows = document.get("rows") if isinstance(document, dict) else None
    if not isinstance(rows, list) or not rows:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="근무 행을 한 줄 이상 남겨 주세요.")
    if len(rows) > 60:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="근무 행은 60줄까지 추가할 수 있습니다.")
    cleaned_rows = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        cleaned_rows.append(
            {
                "year": _clip_cell(row.get("year"), 8),
                "month": _clip_cell(row.get("month"), 4),
                "day": _clip_cell(row.get("day"), 4),
                "worker": _clip_cell(row.get("worker"), 40),
                "time": _clip_cell(row.get("time"), 40),
            }
        )
    if not cleaned_rows:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="근무 행을 한 줄 이상 남겨 주세요.")
    return {
        "project_number": _clip_cell(document.get("project_number"), 100),
        "principal_investigator": _clip_cell(document.get("principal_investigator"), 80),
        "funding_agency": _clip_cell(document.get("funding_agency"), 200),
        "program_name": _clip_cell(document.get("program_name"), 200),
        "research_title": _clip_cell(document.get("research_title"), 200),
        "content": _clip_cell(document.get("content"), 2000),
        "place": _clip_cell(document.get("place"), 200),
        "rows": cleaned_rows,
    }


def _clip_cell(value, limit: int) -> str:
    return str(value or "").strip()[:limit]


def _document_date(document: dict) -> str:
    row = (document.get("rows") or [{}])[0]
    year, month, day = str(row.get("year", "")), str(row.get("month", "")), str(row.get("day", ""))
    if year.isdigit() and month.isdigit() and day.isdigit():
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"[:32]
    return ""


def _document_filename(document: dict) -> str:
    stamp = usage_file_date(_document_date(document))
    return f"[{stamp}] 초과근무_간접비.pdf" if stamp else "초과근무_간접비.pdf"


def _find_signature_path(label: str, signatures: dict[str, Path]) -> Path | None:
    text = label.strip()
    if not text:
        return None
    if text in signatures:
        return signatures[text]
    last = text.split()[-1]
    if last in signatures:
        return signatures[last]
    for name, path in signatures.items():
        if text.endswith(name):
            return path
    return None


def _data_url(path: Path | None) -> str:
    if path is None or not path.is_file():
        return ""
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _utc_iso(value: datetime | None) -> str:
    if value is None:
        return ""
    return value.isoformat(timespec="seconds") + "Z"


def overtime_log_pdf(db: Session, gid: str, values: dict[str, str]) -> bytes:
    project = find_project_by_key(db, gid)
    category = str(values.get("연구비항목", "")).strip()
    if category != ExpenseCategory.OVERTIME:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="초과근무 항목만 초과근무일지를 만들 수 있습니다.")
    signatures: dict[str, Path] = {}
    for account in db.query(User).all():
        if not account.signature_path:
            continue
        path = Path(account.signature_path)
        if path.is_file():
            signatures[account.username] = path
            signatures[account.label] = path
    profile = {
        "project_number": project.project_number or "",
        "principal_investigator": project.principal_investigator or "",
        "funding_agency": project.funding_agency or "",
        "program_name": project.program_name or "",
        "research_title": project.research_title or "",
    }
    return render_overtime_log(profile, values, signatures)


def entry_receipt_filename(db: Session, entry_id: int) -> str:
    entry = db.get(OvertimeEntry, entry_id)
    data = entry.data if entry and isinstance(entry.data, dict) else {}
    return receipt_filename(data)


def entry_pdf_path(db: Session, entry_id: int) -> Path:
    entry = db.get(OvertimeEntry, entry_id)
    if entry is None or not entry.pdf_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="첨부된 PDF가 없습니다.")
    path = Path(entry.pdf_path)
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="첨부된 PDF가 없습니다.")
    return path


async def _sheet_for(project) -> SheetTable:
    if project.sheet_gid:
        return await load_sheet(project.sheet_gid, project.name)
    return SheetTable(gid=project.entry_key, name=project.name, columns=LOCAL_COLUMNS, notes=[], common_notes=[], rows=[])


def sheet_row_key(values: dict) -> str:
    parts = [str(values.get(name, "")).strip() for name in ("순번", "사용일자", "사용금액", "사용시각", "사용처", "연구비항목")]
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:32]


def _safe_gid(gid: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in gid)


async def receipt_pdf_bytes(files: list[UploadFile] | None) -> bytes:
    contents: list[bytes] = []
    for upload in files or []:
        content = await upload.read()
        if not content:
            continue
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="파일은 각 10MB 이하여야 합니다.")
        contents.append(content)
    if not contents:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="연결할 영수증 파일을 선택해 주세요.")
    pdfs = [content for content in contents if content.startswith(b"%PDF")]
    if pdfs:
        if len(contents) != 1:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="PDF는 한 번에 하나만 연결할 수 있습니다.")
        return pdfs[0]
    try:
        return build_column_pdf(contents)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PDF 또는 JPEG, PNG, WEBP 파일만 연결할 수 있습니다.",
        ) from exc


def _clean_field(column: str, raw: str | None) -> str:
    text = "" if raw is None else str(raw).strip()
    if len(text) > MAX_FIELD_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{column}은(는) {MAX_FIELD_LENGTH}자 이하여야 합니다.",
        )
    return text


def _parse_payload(payload: str) -> dict[str, str]:
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="입력 형식이 올바르지 않습니다.") from exc
    if not isinstance(parsed, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="입력 형식이 올바르지 않습니다.")
    return {str(key): "" if value is None else str(value) for key, value in parsed.items()}


def _build_values(db: Session, sheet: SheetTable, fields: dict[str, str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for column in sheet.columns:
        if column in AUTO_COLUMNS:
            continue
        text = fields.get(column, "").strip()
        if len(text) > MAX_FIELD_LENGTH:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{column}은(는) {MAX_FIELD_LENGTH}자 이하여야 합니다.",
            )
        values[column] = text
    if "연구비항목" in values:
        values["연구비항목"] = normalize_expense_category(values.get("연구비항목", ""), required=True)
    if not values.get("사용일자"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="사용일자를 입력해 주세요.")
    if "순번" in sheet.columns:
        values["순번"] = str(_next_sequence(db, sheet.gid))
    if "글자수" in sheet.columns:
        values["글자수"] = str(len(values.get("회의내용", "")))
    stored = {column: values.get(column, "") for column in sheet.columns}
    for key in APP_FIELDS:
        if key in fields:
            stored[key] = _clean_field(key, fields.get(key))
    return stored


def _next_sequence(db: Session, gid: str) -> int:
    numbers: list[int] = []
    entries = db.query(OvertimeEntry).filter(OvertimeEntry.project_gid == gid).all()
    for entry in entries:
        raw = str((entry.data or {}).get("순번", "")).replace(",", "").strip()
        if raw.isdigit():
            numbers.append(int(raw))
    return (max(numbers) if numbers else 0) + 1


def _can_manage(user: User, entry: OvertimeEntry) -> bool:
    return user.is_admin or entry.created_by == user.id


def _own_unassigned(db: Session, user: User, entry_id: int) -> OvertimeEntry:
    entry = db.get(OvertimeEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="항목을 찾을 수 없습니다.")
    if entry.project_gid is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="이미 프로젝트에 할당된 항목입니다.")
    if not _can_manage(user, entry):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="본인이 추가한 항목만 수정할 수 있습니다.")
    return entry


def save_usage_memo(db: Session, gid: str, row_key: str, memo: str) -> str:
    project = find_project_by_key(db, gid)
    sheet_gid = project.sheet_gid or project.entry_key
    text = _clean_field("메모", memo)
    row = (
        db.query(UsageMemo)
        .filter(UsageMemo.project_gid == sheet_gid, UsageMemo.row_key == row_key)
        .one_or_none()
    )
    if not text:
        if row is not None:
            db.delete(row)
    elif row is None:
        db.add(UsageMemo(project_gid=sheet_gid, row_key=row_key, memo=text))
    else:
        row.memo = text
    db.commit()
    return text


def _present_values(columns: list[str], data: dict | None) -> dict[str, str]:
    source = data or {}
    values = {column: "" if source.get(column) is None else str(source.get(column)) for column in columns}
    for key in APP_FIELDS:
        values[key] = "" if source.get(key) is None else str(source.get(key))
    return values
