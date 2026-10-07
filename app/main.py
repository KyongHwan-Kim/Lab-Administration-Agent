from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.migrate import upgrade_database
from app.modules.auth.router import router as auth_router
from app.modules.branding.router import router as branding_router
from app.modules.auth.service import seed_admin
from app.modules.overtime.router import router as overtime_router
from app.modules.projects.router import router as projects_router
from app.modules.projects.service import drop_admin_members, register_projects
from app.modules.users.router import router as users_router

STATIC_DIR = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def lifespan(_: FastAPI):
    upgrade_database()
    db = SessionLocal()
    try:
        seed_admin(db)
        register_projects(db)
        drop_admin_members(db)
    finally:
        db.close()
    yield


app = FastAPI(title="연구실 행정", lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key, same_site="lax", https_only=False)
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(branding_router, prefix="/api/branding", tags=["branding"])
app.include_router(users_router, prefix="/api/users", tags=["users"])
app.include_router(overtime_router, prefix="/api/overtime", tags=["overtime"])
app.include_router(projects_router, prefix="/api/projects", tags=["projects"])


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/{full_path:path}")
def frontend(full_path: str) -> FileResponse:
    if full_path.startswith("api"):
        raise HTTPException(status_code=404, detail="요청한 주소를 찾을 수 없습니다.")
    index = STATIC_DIR / "index.html"
    if full_path:
        candidate = (STATIC_DIR / full_path).resolve()
        try:
            candidate.relative_to(STATIC_DIR.resolve())
        except ValueError as exc:
            raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.") from exc
        if candidate.is_file():
            return FileResponse(candidate)
    if index.is_file():
        return FileResponse(index)
    raise HTTPException(status_code=404, detail="웹 화면이 아직 빌드되지 않았습니다.")
