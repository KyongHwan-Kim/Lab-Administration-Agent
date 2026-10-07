from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class OvertimeEntry(Base):
    __tablename__ = "overtime_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_gid: Mapped[str | None] = mapped_column(String(32), index=True, nullable=True)
    project_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    data: Mapped[dict] = mapped_column(JSON)
    pdf_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class WorkLog(Base):
    __tablename__ = "work_logs"
    __table_args__ = (UniqueConstraint("project_gid", "source_key", name="uq_work_log"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_gid: Mapped[str] = mapped_column(String(32), index=True)
    project_name: Mapped[str] = mapped_column(String(200), default="")
    source_key: Mapped[str] = mapped_column(String(80))
    filename: Mapped[str] = mapped_column(String(200))
    usage_date: Mapped[str] = mapped_column(String(32), default="")
    store_name: Mapped[str] = mapped_column(String(200), default="")
    document: Mapped[dict] = mapped_column(JSON, default=dict)
    pdf_path: Mapped[str] = mapped_column(String(500))
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class UsageMemo(Base):
    __tablename__ = "usage_memos"
    __table_args__ = (UniqueConstraint("project_gid", "row_key", name="uq_usage_memo"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_gid: Mapped[str] = mapped_column(String(32), index=True)
    row_key: Mapped[str] = mapped_column(String(64))
    memo: Mapped[str] = mapped_column(String(4000), default="")


class SheetReceipt(Base):
    __tablename__ = "sheet_receipts"
    __table_args__ = (UniqueConstraint("project_gid", "row_key", name="uq_sheet_receipt"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_gid: Mapped[str] = mapped_column(String(32), index=True)
    row_key: Mapped[str] = mapped_column(String(64))
    pdf_path: Mapped[str] = mapped_column(String(500))
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SheetRow(Base):
    __tablename__ = "sheet_rows"
    __table_args__ = (UniqueConstraint("project_gid", "row_key", name="uq_sheet_row"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_gid: Mapped[str] = mapped_column(String(32), index=True)
    project_name: Mapped[str] = mapped_column(String(200), default="")
    row_key: Mapped[str] = mapped_column(String(64))
    data: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
