from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.modules.users.models import User


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    project_number: Mapped[str] = mapped_column(String(100), default="")
    principal_investigator: Mapped[str] = mapped_column(String(200), default="")
    funding_agency: Mapped[str] = mapped_column(String(200), default="")
    program_name: Mapped[str] = mapped_column(String(200), default="")
    research_title: Mapped[str] = mapped_column(String(200), default="")
    sheet_gid: Mapped[str | None] = mapped_column(String(32), unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    members: Mapped[list["ProjectMember"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="ProjectMember.id",
    )
    cards: Mapped[list["ProjectCard"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="ProjectCard.id",
    )

    @property
    def entry_key(self) -> str:
        return self.sheet_gid or f"local-{self.id}"


class ProjectMember(Base):
    __tablename__ = "project_members"
    __table_args__ = (UniqueConstraint("project_id", "user_id", name="uq_project_member"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    role: Mapped[str] = mapped_column(String(100), default="")

    project: Mapped[Project] = relationship(back_populates="members")
    user: Mapped[User] = relationship()


class ProjectCard(Base):
    __tablename__ = "project_cards"
    __table_args__ = (UniqueConstraint("number_key", name="uq_project_card_number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    label: Mapped[str] = mapped_column(String(80), default="")
    number: Mapped[str] = mapped_column(String(40))
    number_key: Mapped[str] = mapped_column(String(32))

    project: Mapped[Project] = relationship(back_populates="cards")


class ExternalAttendee(Base):
    __tablename__ = "external_attendees"
    __table_args__ = (UniqueConstraint("affiliation", "position", "name", name="uq_external_attendee"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    affiliation: Mapped[str] = mapped_column(String(100))
    position: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
