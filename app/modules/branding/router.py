import io
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from PIL import Image, ImageOps

from app.core.config import settings
from app.core.deps import require_admin
from app.modules.users.models import User

router = APIRouter()

MAX_LOGO_BYTES = 5 * 1024 * 1024
MAX_LOGO_WIDTH = 1200


def logo_path() -> Path:
    return settings.branding_dir / "logo.png"


@router.get("/logo")
def get_logo() -> FileResponse:
    path = logo_path()
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="등록된 로고가 없습니다.")
    return FileResponse(path, media_type="image/png", headers={"Cache-Control": "no-store"})


@router.post("/logo")
async def post_logo(file: UploadFile = File(...), _: User = Depends(require_admin)) -> dict[str, bool]:
    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="로고 이미지를 선택해 주세요.")
    if len(content) > MAX_LOGO_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="로고 이미지는 5MB 이하여야 합니다.")
    image = _open_logo(content)
    image.save(logo_path(), format="PNG")
    return {"custom": True}


@router.delete("/logo")
def delete_logo(_: User = Depends(require_admin)) -> dict[str, bool]:
    path = logo_path()
    if path.is_file():
        path.unlink()
    return {"custom": False}


def _open_logo(content: bytes) -> Image.Image:
    try:
        image = ImageOps.exif_transpose(Image.open(io.BytesIO(content)))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="JPEG, PNG, WEBP 이미지만 등록할 수 있습니다.",
        ) from exc
    if image.mode not in ("RGB", "RGBA"):
        image = image.convert("RGBA")
    if image.width > MAX_LOGO_WIDTH:
        height = max(1, round(image.height * MAX_LOGO_WIDTH / image.width))
        image = image.resize((MAX_LOGO_WIDTH, height), Image.Resampling.LANCZOS)
    return image
