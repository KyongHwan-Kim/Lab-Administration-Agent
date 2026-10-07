from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_admin
from app.modules.projects.schemas import CardWrite, MemberUpdate, MemberWrite, ProjectOut, ProjectWrite
from app.modules.projects.service import (
    add_card,
    add_member,
    create_project,
    delete_card,
    delete_member,
    delete_project,
    list_projects,
    update_card,
    update_member,
    update_project,
)
from app.modules.users.models import User

router = APIRouter()


@router.get("", response_model=list[ProjectOut])
def get_projects(_: User = Depends(require_admin), db: Session = Depends(get_db)) -> list[ProjectOut]:
    return list_projects(db)


@router.post("", response_model=ProjectOut, status_code=201)
def post_project(
    body: ProjectWrite,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ProjectOut:
    return create_project(db, body)


@router.patch("/{project_id}", response_model=ProjectOut)
def patch_project(
    project_id: int,
    body: ProjectWrite,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ProjectOut:
    return update_project(db, project_id, body)


@router.delete("/{project_id}", status_code=204)
def remove_project(
    project_id: int,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> None:
    delete_project(db, project_id)


@router.post("/{project_id}/members", response_model=ProjectOut)
def post_member(
    project_id: int,
    body: MemberWrite,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ProjectOut:
    return add_member(db, project_id, body)


@router.patch("/{project_id}/members/{member_id}", response_model=ProjectOut)
def patch_member(
    project_id: int,
    member_id: int,
    body: MemberUpdate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ProjectOut:
    return update_member(db, project_id, member_id, body)


@router.delete("/{project_id}/members/{member_id}", response_model=ProjectOut)
def remove_member(
    project_id: int,
    member_id: int,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ProjectOut:
    return delete_member(db, project_id, member_id)


@router.post("/{project_id}/cards", response_model=ProjectOut)
def post_card(
    project_id: int,
    body: CardWrite,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ProjectOut:
    return add_card(db, project_id, body)


@router.patch("/{project_id}/cards/{card_id}", response_model=ProjectOut)
def patch_card(
    project_id: int,
    card_id: int,
    body: CardWrite,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ProjectOut:
    return update_card(db, project_id, card_id, body)


@router.delete("/{project_id}/cards/{card_id}", response_model=ProjectOut)
def remove_card(
    project_id: int,
    card_id: int,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ProjectOut:
    return delete_card(db, project_id, card_id)
