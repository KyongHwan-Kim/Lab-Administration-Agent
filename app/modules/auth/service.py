from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.modules.users.models import User


def authenticate(db: Session, username: str, password: str) -> User | None:
    user = db.query(User).filter(User.username == username.strip()).one_or_none()
    if user is None or not verify_password(password, user.password_hash):
        return None
    return user


def seed_admin(db: Session) -> None:
    exists = db.query(User).filter(User.username == settings.admin_username).one_or_none()
    if exists is not None:
        return
    db.add(
        User(
            username=settings.admin_username,
            password_hash=hash_password(settings.admin_password),
            is_admin=True,
        )
    )
    db.commit()
