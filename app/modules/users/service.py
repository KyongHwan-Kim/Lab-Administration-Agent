import io
import re
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from pydantic import ValidationError
from PIL import Image, ImageOps
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.modules.users.models import User
from app.modules.users.schemas import BulkRowError, BulkUserInput, CreateUserRequest, PasswordChangeRequest, ProfileUpdateRequest

MAX_SIGNATURE_BYTES = 5 * 1024 * 1024
MAX_SIGNATURE_WIDTH = 1200
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def list_users(db: Session) -> list[User]:
    return db.query(User).order_by(User.id).all()


def create_user(db: Session, body: CreateUserRequest) -> User:
    username = body.username.strip()
    if not username or any(ch.isspace() for ch in username):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="아이디에 공백을 넣을 수 없습니다.")
    name = body.name.strip()
    email = body.email.strip().lower()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="이름을 입력해 주세요.")
    if _EMAIL.fullmatch(email) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="이메일 형식이 올바르지 않습니다.")
    exists = db.query(User).filter(User.username == username).one_or_none()
    if exists is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 사용 중인 아이디입니다.")
    if db.query(User).filter(User.email == email).one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 사용 중인 이메일입니다.")
    user = User(username=username, name=name, email=email, password_hash=hash_password(body.password), is_admin=False)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_users(db: Session, bodies: list[BulkUserInput]) -> tuple[int, list[BulkRowError]]:
    created = 0
    errors: list[BulkRowError] = []
    for index, body in enumerate(bodies, start=1):
        try:
            create_user(db, CreateUserRequest.model_validate(body.model_dump()))
        except ValidationError:
            errors.append(BulkRowError(row=index, detail="이름, 이메일, 아이디, 비밀번호 형식을 확인해 주세요."))
        except HTTPException as exc:
            errors.append(BulkRowError(row=index, detail=str(exc.detail)))
        else:
            created += 1
    return created, errors


def update_profile(db: Session, user: User, body: ProfileUpdateRequest) -> User:
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="이름을 입력해 주세요.")
    user.name = name
    db.commit()
    db.refresh(user)
    return user


def change_password(db: Session, user: User, body: PasswordChangeRequest) -> User:
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="현재 비밀번호가 올바르지 않습니다.")
    user.password_hash = hash_password(body.new_password)
    db.commit()
    db.refresh(user)
    return user


def get_user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다.")
    return user


def signature_file(user: User) -> Path:
    if not user.signature_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="등록된 서명이 없습니다.")
    path = Path(user.signature_path)
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="등록된 서명이 없습니다.")
    return path


async def save_signature(db: Session, user: User, upload: UploadFile) -> User:
    content = await upload.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="서명 이미지를 선택해 주세요.")
    if len(content) > MAX_SIGNATURE_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="서명 이미지는 5MB 이하여야 합니다.")
    image = _open_signature(content)
    path = settings.signature_dir / f"{user.id}.png"
    image.save(path, format="PNG")
    if user.signature_path and Path(user.signature_path) != path:
        old = Path(user.signature_path)
        if old.is_file():
            old.unlink()
    user.signature_path = str(path)
    db.commit()
    db.refresh(user)
    return user


def delete_signature(db: Session, user: User) -> User:
    if user.signature_path:
        path = Path(user.signature_path)
        if path.is_file():
            path.unlink()
    user.signature_path = None
    db.commit()
    db.refresh(user)
    return user


def _open_signature(content: bytes) -> Image.Image:
    try:
        image = ImageOps.exif_transpose(Image.open(io.BytesIO(content)))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="JPEG, PNG, WEBP 이미지만 등록할 수 있습니다.",
        ) from exc
    if image.mode not in ("RGB", "RGBA"):
        image = image.convert("RGBA" if "transparency" in image.info or image.mode in ("LA", "P") else "RGB")
    if image.width > MAX_SIGNATURE_WIDTH:
        height = max(1, round(image.height * MAX_SIGNATURE_WIDTH / image.width))
        image = image.resize((MAX_SIGNATURE_WIDTH, height), Image.Resampling.LANCZOS)
    return image
