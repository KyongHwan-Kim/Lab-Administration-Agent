from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.modules.overtime.pdf import build_column_pdf, build_evidence_pdf, read_image_files
from app.modules.overtime.service import (
    assign_entry,
    attach_entry_pdf,
    attach_sheet_receipt,
    create_entry,
    create_receipt_entries,
    create_work_log,
    delete_entry,
    entry_pdf_path,
    entry_receipt_filename,
    list_work_logs,
    project_table,
    save_usage_memo,
    save_work_log,
    sheet_receipt_path,
    unassigned_table,
    update_entry,
    update_work_log,
    work_log_file,
    work_log_form,
)
from app.modules.projects.schemas import AttendeeOptions, ExternalOut, ExternalWrite
from app.modules.projects.service import list_attendee_options, list_managed_projects, save_external_attendee
from app.modules.users.models import User

router = APIRouter()


class EntryFields(BaseModel):
    values: dict[str, str] = Field(default_factory=dict)


class WorkLogBody(BaseModel):
    values: dict[str, str] = Field(default_factory=dict)
    source_key: str = Field(min_length=1, max_length=80)


class WorkLogCreateBody(BaseModel):
    gid: str = Field(min_length=1, max_length=32)


class WorkRowBody(BaseModel):
    year: str = ""
    month: str = ""
    day: str = ""
    worker: str = ""
    time: str = ""


class WorkLogDocumentBody(BaseModel):
    project_number: str = ""
    principal_investigator: str = ""
    funding_agency: str = ""
    program_name: str = ""
    research_title: str = ""
    content: str = ""
    place: str = ""
    rows: list[WorkRowBody] = Field(default_factory=list)


class AssignBody(BaseModel):
    gid: str = Field(min_length=1, max_length=32)


class MemoBody(BaseModel):
    row_key: str = Field(min_length=1, max_length=64)
    memo: str = ""


@router.get("/projects")
def get_projects(_: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict[str, str | int]]:
    return list_managed_projects(db)


@router.get("/projects/{gid}")
async def get_project(
    gid: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return await project_table(db, user, gid)


@router.put("/projects/{gid}/memos")
def put_memo(
    gid: str,
    body: MemoBody,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    return {"memo": save_usage_memo(db, gid, body.row_key, body.memo)}


@router.get("/projects/{gid}/attendees", response_model=AttendeeOptions)
def get_attendees(
    gid: str,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AttendeeOptions:
    return list_attendee_options(db, gid)


@router.post("/externals", response_model=ExternalOut)
def post_external(
    body: ExternalWrite,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExternalOut:
    return save_external_attendee(db, body)


@router.get("/unassigned")
def get_unassigned(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return unassigned_table(db, user)


@router.post("/receipts", status_code=201)
async def post_receipts(
    delivery: list[UploadFile] | None = File(None),
    receipt: list[UploadFile] | None = File(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return {"items": await create_receipt_entries(db, user, delivery, receipt)}


@router.post("/projects/{gid}/entries", status_code=201)
async def post_entry(
    gid: str,
    payload: str = Form(...),
    delivery: list[UploadFile] | None = File(None),
    receipt: list[UploadFile] | None = File(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return await create_entry(db, user, gid, payload, delivery, receipt)


@router.patch("/entries/{entry_id}")
def patch_entry(
    entry_id: int,
    body: EntryFields,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return update_entry(db, user, entry_id, body.values)


@router.post("/entries/{entry_id}/assign")
async def post_assign(
    entry_id: int,
    body: AssignBody,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return await assign_entry(db, user, entry_id, body.gid)


@router.delete("/entries/{entry_id}", status_code=204)
def remove_entry(
    entry_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    delete_entry(db, user, entry_id)


@router.post("/entries/{entry_id}/pdf")
async def post_entry_pdf(
    entry_id: int,
    file: list[UploadFile] | None = File(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return await attach_entry_pdf(db, user, entry_id, file)


@router.get("/entries/{entry_id}/pdf")
def download_entry_pdf(
    entry_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    path = entry_pdf_path(db, entry_id)
    return _pdf_response(path, entry_receipt_filename(db, entry_id))


@router.post("/projects/{gid}/receipts")
async def post_sheet_receipt(
    gid: str,
    row_key: str = Form(...),
    file: list[UploadFile] | None = File(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return await attach_sheet_receipt(db, user, gid, row_key, file)


@router.get("/projects/{gid}/receipts/{row_key}")
def download_sheet_receipt(
    gid: str,
    row_key: str,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    return _pdf_response(sheet_receipt_path(db, gid, row_key), "영수증.pdf")


@router.get("/work-logs")
def get_work_logs(_: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return {"items": list_work_logs(db)}


@router.post("/work-logs", status_code=201)
def post_work_log(
    body: WorkLogCreateBody,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return create_work_log(db, user, body.gid)


@router.get("/work-logs/{log_id}/form")
def get_work_log_form(
    log_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return work_log_form(db, log_id)


@router.patch("/work-logs/{log_id}")
def patch_work_log(
    log_id: int,
    body: WorkLogDocumentBody,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return update_work_log(db, log_id, body.model_dump())


@router.get("/work-logs/{log_id}")
def download_saved_work_log(
    log_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    path, filename = work_log_file(db, log_id)
    return _pdf_response(path, filename)


@router.post("/projects/{gid}/work-log")
def download_work_log(
    gid: str,
    body: WorkLogBody,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    pdf, filename = save_work_log(db, user, gid, body.values, body.source_key)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": _pdf_disposition(filename)},
    )


@router.post("/pdf")
async def compose_pdf(
    _: User = Depends(get_current_user),
    delivery: list[UploadFile] | None = File(None),
    receipt: list[UploadFile] | None = File(None),
) -> Response:
    pdf = build_evidence_pdf(await read_image_files(delivery), await read_image_files(receipt))
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": _pdf_disposition("증빙.pdf")},
    )


def _pdf_response(path, filename: str) -> Response:
    return Response(
        content=path.read_bytes(),
        media_type="application/pdf",
        headers={"Content-Disposition": _pdf_disposition(filename)},
    )


def _pdf_disposition(filename: str) -> str:
    encoded = quote(filename)
    return f"attachment; filename=evidence.pdf; filename*=UTF-8''{encoded}"
