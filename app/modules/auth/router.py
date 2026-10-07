from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.modules.auth.schemas import LoginRequest, UserOut
from app.modules.auth.service import authenticate
from app.modules.users.models import User

router = APIRouter()


def to_user_out(user: User) -> UserOut:
    path = Path(user.signature_path) if user.signature_path else None
    return UserOut(
        id=user.id,
        username=user.username,
        name=user.label,
        email=(user.email or "").strip(),
        is_admin=user.is_admin,
        has_signature=bool(path and path.is_file()),
    )


@router.post("/login", response_model=UserOut)
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)) -> UserOut:
    user = authenticate(db, body.username, body.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="아이디 또는 비밀번호가 올바르지 않습니다.",
        )
    request.session["user_id"] = user.id
    return to_user_out(user)


@router.post("/logout")
def logout(request: Request) -> dict[str, bool]:
    request.session.clear()
    return {"ok": True}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> UserOut:
    return to_user_out(user)
