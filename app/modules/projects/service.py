from pathlib import Path
import re

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.overtime.models import OvertimeEntry, SheetReceipt, SheetRow, WorkLog
from app.modules.overtime.sheets import FALLBACK_SHEETS
from app.modules.projects.models import ExternalAttendee, Project, ProjectCard, ProjectMember
from app.modules.projects.schemas import (
    AttendeeOptions,
    CardOut,
    CardWrite,
    ExternalOut,
    ExternalWrite,
    MemberOut,
    MemberUpdate,
    MemberWrite,
    ProjectOut,
    ProjectWrite,
)
from app.modules.users.models import User


def list_managed_projects(db: Session) -> list[dict[str, str | int]]:
    projects = db.query(Project).order_by(Project.id).all()
    return [{"id": project.id, "gid": project.entry_key, "name": project.name} for project in projects]


def list_attendee_options(db: Session, gid: str) -> AttendeeOptions:
    project = find_project_by_key(db, gid)
    return AttendeeOptions(
        members=[_member_out(member) for member in project.members if not _is_admin_member(member)],
        externals=[_external_out(row) for row in db.query(ExternalAttendee).order_by(ExternalAttendee.id).all()],
    )


def save_external_attendee(db: Session, body: ExternalWrite) -> ExternalOut:
    affiliation = _clean_person_field(body.affiliation, "소속")
    position = _clean_person_field(body.position, "직급")
    name = _clean_person_field(body.name, "성함")
    existing = _find_external(db, affiliation, position, name)
    if existing is not None:
        return _external_out(existing)
    row = ExternalAttendee(affiliation=affiliation, position=position, name=name)
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = _find_external(db, affiliation, position, name)
        if existing is None:
            raise
        return _external_out(existing)
    db.refresh(row)
    return _external_out(row)


def find_project_by_key(db: Session, key: str) -> Project:
    if key.startswith("local-") and key.removeprefix("local-").isdigit():
        project = db.get(Project, int(key.removeprefix("local-")))
    else:
        project = db.query(Project).filter(Project.sheet_gid == key).one_or_none()
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="프로젝트를 찾을 수 없습니다.")
    return project


def list_projects(db: Session) -> list[ProjectOut]:
    return [_to_out(project) for project in db.query(Project).order_by(Project.id).all()]


def create_project(db: Session, body: ProjectWrite) -> ProjectOut:
    project = Project(name=_clean_name(db, body.name), **_profile(body))
    db.add(project)
    db.commit()
    db.refresh(project)
    return _to_out(project)


def update_project(db: Session, project_id: int, body: ProjectWrite) -> ProjectOut:
    project = _get_project(db, project_id)
    project.name = _clean_name(db, body.name, project.id)
    for key, value in _profile(body).items():
        setattr(project, key, value)
    db.query(OvertimeEntry).filter(OvertimeEntry.project_gid == project.entry_key).update(
        {OvertimeEntry.project_name: project.name}
    )
    db.query(WorkLog).filter(WorkLog.project_gid == project.entry_key).update({WorkLog.project_name: project.name})
    db.query(SheetRow).filter(SheetRow.project_gid == project.entry_key).update({SheetRow.project_name: project.name})
    db.commit()
    db.refresh(project)
    return _to_out(project)


def delete_project(db: Session, project_id: int) -> None:
    project = _get_project(db, project_id)
    entries = db.query(OvertimeEntry).filter(OvertimeEntry.project_gid == project.entry_key).all()
    receipts = db.query(SheetReceipt).filter(SheetReceipt.project_gid == project.entry_key).all()
    logs = db.query(WorkLog).filter(WorkLog.project_gid == project.entry_key).all()
    for receipt in receipts:
        path = Path(receipt.pdf_path)
        if path.is_file():
            path.unlink()
        db.delete(receipt)
    for log in logs:
        path = Path(log.pdf_path)
        if path.is_file():
            path.unlink()
        db.delete(log)
    for entry in entries:
        if entry.pdf_path:
            path = Path(entry.pdf_path)
            if path.is_file():
                path.unlink()
        db.delete(entry)
    db.query(SheetRow).filter(SheetRow.project_gid == project.entry_key).delete()
    db.delete(project)
    db.commit()


def drop_admin_members(db: Session) -> None:
    admin_ids = [user.id for user in db.query(User).filter(User.is_admin.is_(True)).all()]
    if not admin_ids:
        return
    db.query(ProjectMember).filter(ProjectMember.user_id.in_(admin_ids)).delete(synchronize_session=False)
    db.commit()


def add_member(db: Session, project_id: int, body: MemberWrite) -> ProjectOut:
    project = _get_project(db, project_id)
    _ensure_participant(db, body.user_id)
    if any(member.user_id == body.user_id for member in project.members):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 참여 중인 사용자입니다.")
    project.members.append(ProjectMember(user_id=body.user_id, role=body.role.strip()))
    db.commit()
    db.refresh(project)
    return _to_out(project)


def update_member(db: Session, project_id: int, member_id: int, body: MemberUpdate) -> ProjectOut:
    project = _get_project(db, project_id)
    member = _get_member(project, member_id)
    if body.user_id is not None and body.user_id != member.user_id:
        _ensure_participant(db, body.user_id)
        if any(item.user_id == body.user_id for item in project.members):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 참여 중인 사용자입니다.")
        member.user_id = body.user_id
    if body.role is not None:
        member.role = body.role.strip()
    db.commit()
    db.refresh(project)
    return _to_out(project)


def delete_member(db: Session, project_id: int, member_id: int) -> ProjectOut:
    project = _get_project(db, project_id)
    member = _get_member(project, member_id)
    db.delete(member)
    db.commit()
    db.refresh(project)
    return _to_out(project)


def add_card(db: Session, project_id: int, body: CardWrite) -> ProjectOut:
    project = _get_project(db, project_id)
    label, number, number_key = _clean_card(body.label, body.number)
    _ensure_card_key(db, number_key)
    project.cards.append(ProjectCard(label=label, number=number, number_key=number_key))
    db.commit()
    db.refresh(project)
    return _to_out(project)


def update_card(db: Session, project_id: int, card_id: int, body: CardWrite) -> ProjectOut:
    project = _get_project(db, project_id)
    card = _get_card(project, card_id)
    label, number, number_key = _clean_card(body.label, body.number)
    _ensure_card_key(db, number_key, card.id)
    card.label = label
    card.number = number
    card.number_key = number_key
    db.commit()
    db.refresh(project)
    return _to_out(project)


def delete_card(db: Session, project_id: int, card_id: int) -> ProjectOut:
    project = _get_project(db, project_id)
    db.delete(_get_card(project, card_id))
    db.commit()
    db.refresh(project)
    return _to_out(project)


def match_card_project(db: Session, card_number: str, matched_project: str = "") -> Project | None:
    if len(card_digits(card_number)) < 4:
        return None
    matched = [card for card in db.query(ProjectCard).all() if card_numbers_match(card_number, card.number_key)]
    projects = {card.project_id: card.project for card in matched if card.project is not None}
    if len(projects) == 1:
        return next(iter(projects.values()))
    named = matched_project.strip()
    if not named:
        return None
    chosen = [project for project in projects.values() if project.name == named]
    if len(chosen) == 1:
        return chosen[0]
    return None


def register_projects(db: Session) -> None:
    if db.query(Project).first() is not None:
        return
    for gid, name in FALLBACK_SHEETS:
        db.add(Project(name=name, sheet_gid=gid))
    db.commit()


def _get_project(db: Session, project_id: int) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="프로젝트를 찾을 수 없습니다.")
    return project


def _get_card(project: Project, card_id: int) -> ProjectCard:
    card = next((item for item in project.cards if item.id == card_id), None)
    if card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="카드를 찾을 수 없습니다.")
    return card


def _clean_card(label: str, number: str) -> tuple[str, str, str]:
    cleaned_label = label.strip()
    number_key = card_digits(number)
    if len(cleaned_label) > 80:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="카드 이름은 80자 이하여야 합니다.")
    if len(number_key) < 4:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="카드 끝자리 4자리 이상을 입력해 주세요.")
    if len(number_key) > 8:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="카드 번호 전체가 아니라 끝자리만 입력해 주세요.")
    return cleaned_label, number_key, number_key


def _ensure_card_key(db: Session, number_key: str, current_id: int | None = None) -> None:
    for other in db.query(ProjectCard).all():
        if other.id == current_id:
            continue
        other_key = card_digits(other.number_key)
        if other_key == number_key or other_key.endswith(number_key) or number_key.endswith(other_key):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이 끝자리는 이미 등록된 카드와 구분되지 않습니다.")


def card_digits(value: str) -> str:
    return re.sub(r"\D", "", value)


def card_numbers_match(observed: str, registered: str) -> bool:
    left = card_digits(observed)
    right = card_digits(registered)
    if len(left) < 4 or len(right) < 4:
        return False
    return left.endswith(right)


def _get_member(project: Project, member_id: int) -> ProjectMember:
    member = next((item for item in project.members if item.id == member_id), None)
    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="참여 인원을 찾을 수 없습니다.")
    return member


def _ensure_user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다.")
    return user


def _ensure_participant(db: Session, user_id: int) -> User:
    user = _ensure_user(db, user_id)
    if user.is_admin:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="관리자는 참여 인원으로 지정할 수 없습니다.")
    return user


def _is_admin_member(member: ProjectMember) -> bool:
    return member.user is not None and member.user.is_admin


def _profile(body: ProjectWrite) -> dict[str, str]:
    return {
        "project_number": _optional(body.project_number, 100, "과제번호"),
        "principal_investigator": _optional(body.principal_investigator, 200, "연구책임자"),
        "funding_agency": _optional(body.funding_agency, 200, "연구지원기관"),
        "program_name": _optional(body.program_name, 200, "사업명"),
        "research_title": _optional(body.research_title, 200, "연구과제명"),
    }


def _optional(value: str, limit: int, label: str) -> str:
    text = value.strip()
    if len(text) > limit:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{label}은(는) {limit}자 이하여야 합니다.")
    return text


def _clean_name(db: Session, name: str, current_id: int | None = None) -> str:
    cleaned = name.strip()
    if not cleaned:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="프로젝트 이름을 입력해 주세요.")
    exists = db.query(Project).filter(Project.name == cleaned).one_or_none()
    if exists is not None and exists.id != current_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 있는 프로젝트 이름입니다.")
    return cleaned


def _find_external(db: Session, affiliation: str, position: str, name: str) -> ExternalAttendee | None:
    return (
        db.query(ExternalAttendee)
        .filter(
            ExternalAttendee.affiliation == affiliation,
            ExternalAttendee.position == position,
            ExternalAttendee.name == name,
        )
        .one_or_none()
    )


def _clean_person_field(value: str, label: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{label}을 입력해 주세요.")
    if len(cleaned) > 100:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{label}은 100자 이하여야 합니다.")
    return cleaned


def _member_out(member: ProjectMember) -> MemberOut:
    return MemberOut(
        id=member.id,
        user_id=member.user_id,
        username=member.user.username if member.user is not None else "",
        name=member.user.label if member.user is not None else "",
        role=member.role or "",
    )


def _external_out(row: ExternalAttendee) -> ExternalOut:
    return ExternalOut(id=row.id, affiliation=row.affiliation, position=row.position, name=row.name)


def _to_out(project: Project) -> ProjectOut:
    return ProjectOut(
        id=project.id,
        name=project.name,
        project_number=project.project_number or "",
        principal_investigator=project.principal_investigator or "",
        funding_agency=project.funding_agency or "",
        program_name=project.program_name or "",
        research_title=project.research_title or "",
        members=[_member_out(member) for member in project.members if not _is_admin_member(member)],
        cards=[_card_out(card) for card in project.cards],
    )


def _card_out(card: ProjectCard) -> CardOut:
    return CardOut(id=card.id, label=card.label or "", number=card.number)
