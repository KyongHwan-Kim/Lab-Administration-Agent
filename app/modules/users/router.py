from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_admin
from app.modules.auth.router import to_user_out
from app.modules.auth.schemas import UserOut
from app.modules.users.models import User
from app.modules.users.schemas import (
    BulkCreateRequest,
    BulkCreateResponse,
    CreateUserRequest,
    PasswordChangeRequest,
    ProfileUpdateRequest,
)
from app.modules.users.service import (
    change_password,
    create_user,
    create_users,
    delete_signature,
    get_user,
    list_users,
    save_signature,
    signature_file,
    update_profile,
)

router = APIRouter()


@router.get("", response_model=list[UserOut])
def get_users(_: User = Depends(require_admin), db: Session = Depends(get_db)) -> list[UserOut]:
    return [to_user_out(user) for user in list_users(db)]


@router.post("", response_model=UserOut, status_code=201)
def post_user(
    body: CreateUserRequest,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> UserOut:
    return to_user_out(create_user(db, body))


@router.post("/bulk", response_model=BulkCreateResponse)
def post_users(
    body: BulkCreateRequest,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> BulkCreateResponse:
    created, errors = create_users(db, body.users)
    return BulkCreateResponse(created=created, errors=errors)


@router.post("/me/signature", response_model=UserOut)
async def post_my_signature(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserOut:
    return to_user_out(await save_signature(db, user, file))


@router.get("/me/signature")
def get_my_signature(user: User = Depends(get_current_user)) -> FileResponse:
    return _signature_response(user)


@router.delete("/me/signature", response_model=UserOut)
def delete_my_signature(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> UserOut:
    return to_user_out(delete_signature(db, user))


@router.patch("/me", response_model=UserOut)
def patch_me(
    body: ProfileUpdateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserOut:
    return to_user_out(update_profile(db, user, body))


@router.patch("/me/password", response_model=UserOut)
def patch_my_password(
    body: PasswordChangeRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserOut:
    return to_user_out(change_password(db, user, body))


@router.post("/{user_id}/signature", response_model=UserOut)
async def post_user_signature(
    user_id: int,
    file: UploadFile = File(...),
    actor: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserOut:
    target = _editable_user(db, actor, user_id)
    return to_user_out(await save_signature(db, target, file))


@router.get("/{user_id}/signature")
def get_user_signature(
    user_id: int,
    actor: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    target = _visible_user(db, actor, user_id)
    return _signature_response(target)


@router.delete("/{user_id}/signature", response_model=UserOut)
def delete_user_signature(
    user_id: int,
    actor: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserOut:
    target = _editable_user(db, actor, user_id)
    return to_user_out(delete_signature(db, target))


def _editable_user(db: Session, actor: User, user_id: int) -> User:
    if not actor.is_admin and actor.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="본인 서명만 등록할 수 있습니다.")
    return get_user(db, user_id)


def _visible_user(db: Session, actor: User, user_id: int) -> User:
    if not actor.is_admin and actor.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="서명을 볼 수 없습니다.")
    return get_user(db, user_id)


def _signature_response(user: User) -> FileResponse:
    return FileResponse(signature_file(user), media_type="image/png")
