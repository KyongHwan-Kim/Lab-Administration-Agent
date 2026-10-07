import io

from fastapi import HTTPException, UploadFile, status
from PIL import Image, ImageOps
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_IMAGES = 30


async def read_image_files(files: list[UploadFile] | None) -> list[bytes]:
    images: list[bytes] = []
    for upload in files or []:
        if not upload.filename:
            continue
        content = await upload.read()
        if not content:
            continue
        if len(content) > MAX_IMAGE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이미지는 각 10MB 이하여야 합니다.",
            )
        if not _is_image(content):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="JPEG, PNG, WEBP 이미지만 업로드할 수 있습니다.",
            )
        images.append(content)
    return images


def _is_image(content: bytes) -> bool:
    try:
        with Image.open(io.BytesIO(content)) as image:
            image.verify()
        return True
    except Exception:
        return False


def _prepare_image(content: bytes) -> Image.Image:
    image = ImageOps.exif_transpose(Image.open(io.BytesIO(content)))
    if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
        rgba = image.convert("RGBA")
        background = Image.new("RGB", rgba.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.split()[-1])
        return background
    if image.mode != "RGB":
        return image.convert("RGB")
    return image


def build_column_pdf(images: list[bytes], columns: int = 1) -> bytes:
    prepared = _validated_images(images)
    if columns <= 1:
        return _build_stacked_pdf(prepared)
    return _build_row_pdf(prepared, columns)


def build_evidence_pdf(delivery: list[bytes], receipt: list[bytes]) -> bytes:
    prepared = _validated_images([*delivery, *receipt])
    return _build_variable_rows([prepared], pagesize=landscape(A4))


def _validated_images(images: list[bytes]) -> list[Image.Image]:
    if not images:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="업로드할 이미지를 선택해 주세요.")
    if len(images) > MAX_IMAGES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"이미지는 한 번에 {MAX_IMAGES}장까지 올릴 수 있습니다.",
        )
    return [_prepare_image(content) for content in images]


def _build_stacked_pdf(images: list[Image.Image]) -> bytes:
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    page_width, page_height = A4
    margin = 36
    gap = 14
    max_width = page_width - margin * 2
    max_height = page_height - margin * 2
    cursor_y = page_height - margin

    for image in images:
        draw_width = max_width
        draw_height = image.height * (draw_width / image.width)
        if draw_height > max_height:
            draw_height = max_height
            draw_width = image.width * (draw_height / image.height)
        if cursor_y - draw_height < margin:
            pdf.showPage()
            cursor_y = page_height - margin
        x = margin + (max_width - draw_width) / 2
        pdf.drawImage(ImageReader(_jpeg(image, draw_width, draw_height)), x, cursor_y - draw_height, width=draw_width, height=draw_height)
        cursor_y -= draw_height + gap

    pdf.save()
    return buffer.getvalue()


def _build_row_pdf(images: list[Image.Image], columns: int) -> bytes:
    columns = max(1, min(columns, 4, len(images)))
    margin = 28
    gap = 8
    min_row_height = 72
    page_width, page_height = A4
    inner_width = page_width - margin * 2
    inner_height = page_height - margin * 2
    cell_width = (inner_width - gap * (columns - 1)) / columns
    rows = [images[index : index + columns] for index in range(0, len(images), columns)]
    natural_heights = [_row_height(row, cell_width) for row in rows]

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    start = 0
    while start < len(rows):
        count = _rows_that_fit(natural_heights[start:], inner_height, gap, min_row_height)
        chosen = rows[start : start + count]
        heights = natural_heights[start : start + count]
        total = sum(heights) + gap * (count - 1)
        scale = min(1.0, inner_height / total) if total else 1.0
        cursor_y = page_height - margin
        for row, height in zip(chosen, heights, strict=True):
            row_height = height * scale
            _draw_row(pdf, row, margin, cursor_y, cell_width, row_height, gap)
            cursor_y -= row_height + gap
        start += count
        if start < len(rows):
            pdf.showPage()

    pdf.save()
    return buffer.getvalue()


def _build_variable_rows(rows: list[list[Image.Image]], pagesize: tuple[float, float] = A4) -> bytes:
    margin = 28
    gap = 8
    min_row_height = 72
    page_width, page_height = pagesize
    inner_width = page_width - margin * 2
    inner_height = page_height - margin * 2

    def cell_width(count: int) -> float:
        return (inner_width - gap * (count - 1)) / count

    natural_heights = [_row_height(row, cell_width(len(row))) for row in rows]
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=pagesize)
    start = 0
    while start < len(rows):
        count = _rows_that_fit(natural_heights[start:], inner_height, gap, min_row_height)
        chosen = rows[start : start + count]
        heights = natural_heights[start : start + count]
        total = sum(heights) + gap * (count - 1)
        scale = min(1.0, inner_height / total) if total else 1.0
        cursor_y = page_height - margin
        for row, height in zip(chosen, heights, strict=True):
            _draw_row(pdf, row, margin, cursor_y, cell_width(len(row)), height * scale, gap)
            cursor_y -= height * scale + gap
        start += count
        if start < len(rows):
            pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def _row_height(images: list[Image.Image], cell_width: float) -> float:
    return max(image.height * (cell_width / image.width) for image in images)


def _rows_that_fit(heights: list[float], inner_height: float, gap: float, min_row_height: float) -> int:
    fitted = 1
    for count in range(1, len(heights) + 1):
        total = sum(heights[:count]) + gap * (count - 1)
        scale = min(1.0, inner_height / total) if total else 1.0
        if count > 1 and min(height * scale for height in heights[:count]) < min_row_height:
            break
        fitted = count
    return fitted


def _draw_row(
    pdf: canvas.Canvas,
    images: list[Image.Image],
    x: float,
    top: float,
    cell_width: float,
    row_height: float,
    gap: float,
) -> None:
    for index, image in enumerate(images):
        scale = min(cell_width / image.width, row_height / image.height)
        draw_width = image.width * scale
        draw_height = image.height * scale
        cell_x = x + index * (cell_width + gap)
        draw_x = cell_x + (cell_width - draw_width) / 2
        draw_y = top - row_height + (row_height - draw_height) / 2
        pdf.drawImage(
            ImageReader(_jpeg(image, draw_width, draw_height)),
            draw_x,
            draw_y,
            width=draw_width,
            height=draw_height,
        )


def _jpeg(image: Image.Image, draw_width: float, draw_height: float) -> io.BytesIO:
    pixel_width = max(1, round(draw_width * 2))
    pixel_height = max(1, round(draw_height * 2))
    if image.width > pixel_width or image.height > pixel_height:
        image = image.resize((pixel_width, pixel_height), Image.Resampling.LANCZOS)
    encoded = io.BytesIO()
    image.save(encoded, format="JPEG", quality=85)
    encoded.seek(0)
    return encoded
