import io
import re
from pathlib import Path

from PIL import Image as PilImage
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

ASSETS = Path(__file__).resolve().parent / "assets"
LETTERHEAD_PATH = ASSETS / "letterhead.jpg"
FONT_PATH = ASSETS / "NanumGothic-Regular.ttf"
FONT_NAME = "NanumGothic"
PAGE_LIMIT = 6
PAGE_W, PAGE_H = A4
MARGIN_X = 34
FOOTER_RESERVE = 128

_DATE = re.compile(r"(20\d{2})\s*[.\-/년]\s*(\d{1,2})\s*[.\-/월]\s*(\d{1,2})")
_SHORT_DATE = re.compile(r"(?:^|\D)(\d{2})\s*[.\-/]\s*(\d{1,2})\s*[.\-/]\s*(\d{1,2})")
_SPLIT_ATTENDEES = re.compile(r"[,，、;\n]+")
_font_ready = False


def render_overtime_log(profile: dict[str, str], values: dict[str, str], signatures: dict[str, Path]) -> bytes:
    return render_document(build_usage_document(profile, values), signatures)


def build_usage_document(profile: dict[str, str], values: dict[str, str]) -> dict:
    year, month, day = _work_date(values.get("사용일자", ""))
    clock = _first_text(values, ("회의시간", "사용시각"))
    rows = [
        {"year": year, "month": month, "day": day, "worker": _display_name(name), "time": clock}
        for name in _workers(values)
        if name.strip()
    ]
    if not rows:
        rows = [{"year": year, "month": month, "day": day, "worker": "", "time": clock}]
    return {
        "project_number": profile.get("project_number", "").strip(),
        "principal_investigator": profile.get("principal_investigator", "").strip(),
        "funding_agency": profile.get("funding_agency", "").strip(),
        "program_name": profile.get("program_name", "").strip(),
        "research_title": profile.get("research_title", "").strip(),
        "content": _first_text(values, ("회의내용", "회의목적", "사용목적")),
        "place": _first_text(values, ("회의장소", "사용처")),
        "rows": rows,
    }


def render_document(document: dict, signatures: dict[str, Path]) -> bytes:
    _register_font()
    rows = list(document.get("rows") or [])
    if not rows:
        rows = [{"year": "", "month": "", "day": "", "worker": "", "time": ""}]
    pages = [rows[index : index + PAGE_LIMIT] for index in range(0, len(rows), PAGE_LIMIT)]
    investigator = str(document.get("principal_investigator", "")).strip()
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    for page_rows in pages:
        _paint_page(
            pdf,
            document,
            page_rows,
            signatures,
            content=str(document.get("content", "")).strip(),
            place=str(document.get("place", "")).strip(),
            investigator=investigator,
            stamp=_find_signature(investigator, signatures),
        )
        pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def _paint_page(pdf, profile, workers, signatures, **fields) -> None:
    pdf.drawImage(ImageReader(str(LETTERHEAD_PATH)), 0, 0, width=PAGE_W, height=PAGE_H, mask="auto")
    left = MARGIN_X
    width = PAGE_W - MARGIN_X * 2
    y = PAGE_H - 30

    pdf.setFillColorRGB(0.15, 0.15, 0.15)
    pdf.setFont(FONT_NAME, 9)
    pdf.drawString(left, y - 8, "| 필수 첨부 양식 |")
    y -= 16
    _rule(pdf, left, y, width)
    y -= 27
    _tracked_title(pdf, "초과근무일지", y, 15, 8)
    y -= 8
    _rule(pdf, left, y, width)
    y -= 12

    label_w = 74
    value_w = (width - label_w * 2) / 2
    info_h = 22
    info_rows = (
        ((True, "과제번호"), profile.get("project_number", ""), (True, "연구책임자"), profile.get("principal_investigator", "")),
        ((False, "연구지원기관"), profile.get("funding_agency", ""), (False, "사업명"), profile.get("program_name", "")),
    )
    for left_label, left_value, right_label, right_value in info_rows:
        _cell(pdf, left, y - info_h, label_w, info_h, fill=True)
        _label(pdf, left_label[1], left, y - info_h, label_w, info_h, required=left_label[0])
        _cell(pdf, left + label_w, y - info_h, value_w, info_h)
        _cell_text(pdf, left_value, left + label_w, y - info_h, value_w, info_h, 9)
        _cell(pdf, left + label_w + value_w, y - info_h, label_w, info_h, fill=True)
        _label(pdf, right_label[1], left + label_w + value_w, y - info_h, label_w, info_h, required=right_label[0])
        _cell(pdf, left + label_w * 2 + value_w, y - info_h, value_w, info_h)
        _cell_text(pdf, right_value, left + label_w * 2 + value_w, y - info_h, value_w, info_h, 9)
        y -= info_h
    _cell(pdf, left, y - info_h, label_w, info_h, fill=True)
    _label(pdf, "연구과제명", left, y - info_h, label_w, info_h)
    _cell(pdf, left + label_w, y - info_h, width - label_w, info_h)
    _cell_text(pdf, profile.get("research_title", ""), left + label_w, y - info_h, width - label_w, info_h, 8.5)
    y -= info_h + 12

    date_w, worker_w, content_w, place_w, time_w = 88, 68, 138, 92, 70
    sign_w = width - (date_w + worker_w + content_w + place_w + time_w)
    columns = (date_w, worker_w, content_w, place_w, time_w, sign_w)
    header_h = 32
    row_h = 26
    headers = (
        (True, "근무일자", "(년-월-일)"),
        (True, "근무자", ""),
        (True, "근무내용", ""),
        (True, "근무장소", ""),
        (True, "시간", ""),
        (True, "근무자", "본인사인"),
    )
    x = left
    for column_w, (required, title, subtitle) in zip(columns, headers, strict=True):
        _cell(pdf, x, y - header_h, column_w, header_h, fill=True)
        _header_label(pdf, title, subtitle, x, y - header_h, column_w, header_h, required=required)
        x += column_w
    y -= header_h

    body_top = y
    content_x = left + date_w + worker_w
    place_x = content_x + content_w
    time_x = place_x + place_w
    sign_x = time_x + time_w
    filled = list(workers[:PAGE_LIMIT])
    slots = filled + [None] * (PAGE_LIMIT - len(filled))
    for row in slots:
        for cell_x, cell_w in ((left, date_w), (left + date_w, worker_w), (time_x, time_w), (sign_x, sign_w)):
            _cell(pdf, cell_x, y - row_h, cell_w, row_h)
        _date_cell(pdf, row, left, y - row_h, date_w, row_h)
        if row:
            _cell_text(pdf, row.get("worker", ""), left + date_w, y - row_h, worker_w, row_h, 9)
            _cell_text(pdf, row.get("time", ""), time_x, y - row_h, time_w, row_h, 8)
            signature = _find_signature(str(row.get("worker", "")), signatures)
            if signature is not None:
                _image_at(pdf, signature, sign_x + 2, y - row_h + 2, sign_w - 4, row_h - 4)
        y -= row_h
    body_h = body_top - y
    _cell(pdf, content_x, y, content_w, body_h)
    _cell(pdf, place_x, y, place_w, body_h)
    _cell_text(pdf, fields["content"], content_x, y, content_w, body_h, 8.5)
    _cell_text(pdf, fields["place"], place_x, y, place_w, body_h, 8.5)
    y -= 12
    note_size = 8
    box_h = 46
    box_bottom = y - box_h
    _cell(pdf, left, box_bottom, width, box_h)
    text_x = left + 6
    line_y = box_bottom + box_h - 14
    _note_line(pdf, text_x, line_y, note_size, "[영수증첨부]", " : 상한 1인 30,000원, 법인신용카드 영수증만 인정")
    _note_line(pdf, text_x, line_y - 12, note_size, "[필수항목]", " *본인사인에는 근무자의 자필사인 기재")
    indent = pdfmetrics.stringWidth("※ [필수항목] ", FONT_NAME, note_size)
    pdf.setFillColorRGB(0, 0, 0)
    pdf.setFont(FONT_NAME, note_size)
    pdf.drawString(text_x + indent, line_y - 24, "*연구책임자의 확인(날인 또는 사인) 기재하여 청구 시 파일 업로드함")
    y = box_bottom - 8

    block_w = 210
    block_x = left + width - block_w
    pdf.setFont(FONT_NAME, 10)
    pdf.setFillColorRGB(0.86, 0.15, 0.15)
    pdf.drawString(block_x, y - 12, "*")
    pdf.setFillColorRGB(0, 0, 0)
    pdf.drawString(block_x + 8, y - 12, "연구책임자")
    name = str(fields["investigator"] or "")
    pdf.drawCentredString(block_x + 118, y - 12, name)
    pdf.drawCentredString(block_x + 180, y - 12, "(인)")
    if fields["stamp"] is not None:
        _image_at(pdf, fields["stamp"], block_x + 156, y - 28, 48, 36)


def _rule(pdf, x: float, y: float, width: float) -> None:
    pdf.setStrokeColorRGB(0.863, 0.149, 0.149)
    pdf.setLineWidth(3)
    pdf.line(x, y, x + width, y)


def _note_line(pdf, x: float, y: float, size: float, label: str, rest: str) -> None:
    prefix = "※ "
    pdf.setFillColorRGB(0, 0, 0)
    pdf.setFont(FONT_NAME, size)
    pdf.drawString(x, y, prefix)
    cursor = x + pdfmetrics.stringWidth(prefix, FONT_NAME, size)
    _bold_text(pdf, cursor, y, label, size)
    cursor += pdfmetrics.stringWidth(label, FONT_NAME, size)
    pdf.setFillColorRGB(0, 0, 0)
    pdf.setFont(FONT_NAME, size)
    pdf.drawString(cursor, y, rest)


def _bold_text(pdf, x: float, y: float, text: str, size: float) -> None:
    pdf.setFillColorRGB(0, 0, 0)
    pdf.setStrokeColorRGB(0, 0, 0)
    pdf.setLineWidth(0.45)
    pdf.setFont(FONT_NAME, size)
    text_object = pdf.beginText(x, y)
    text_object.setTextRenderMode(2)
    text_object.setFont(FONT_NAME, size)
    text_object.textOut(text)
    pdf.drawText(text_object)
    pdf.setLineWidth(0.6)


def _tracked_title(pdf, text: str, baseline: float, size: float, gap: float) -> None:
    pdf.setFillColorRGB(0, 0, 0)
    pdf.setFont(FONT_NAME, size)
    widths = [pdfmetrics.stringWidth(char, FONT_NAME, size) for char in text]
    total = sum(widths) + gap * (len(text) - 1)
    cursor = (PAGE_W - total) / 2
    for char, char_w in zip(text, widths, strict=True):
        pdf.drawString(cursor, baseline, char)
        cursor += char_w + gap


def _cell(pdf, x: float, y: float, width: float, height: float, fill: bool = False) -> None:
    pdf.setStrokeColorRGB(0, 0, 0)
    pdf.setLineWidth(0.6)
    if fill:
        pdf.setFillColorRGB(0.96, 0.96, 0.96)
        pdf.rect(x, y, width, height, stroke=1, fill=1)
    else:
        pdf.rect(x, y, width, height, stroke=1, fill=0)


def _label(pdf, text: str, x: float, y: float, width: float, height: float, required: bool = False) -> None:
    size = 8.5
    pdf.setFont(FONT_NAME, size)
    star_w = pdfmetrics.stringWidth("*", FONT_NAME, size) if required else 0
    text_w = pdfmetrics.stringWidth(text, FONT_NAME, size)
    start = x + (width - star_w - text_w) / 2
    baseline = y + (height - size) / 2
    if required:
        pdf.setFillColorRGB(0.86, 0.15, 0.15)
        pdf.drawString(start, baseline, "*")
    pdf.setFillColorRGB(0, 0, 0)
    pdf.drawString(start + star_w, baseline, text)


def _header_label(pdf, title: str, subtitle: str, x: float, y: float, width: float, height: float, required: bool = False) -> None:
    if subtitle:
        _label(pdf, title, x, y + height / 2 - 1, width, height / 2, required=required)
        pdf.setFillColorRGB(0, 0, 0)
        pdf.setFont(FONT_NAME, 7.5)
        pdf.drawCentredString(x + width / 2, y + 6, subtitle)
        return
    _label(pdf, title, x, y, width, height, required=required)


def _date_cell(pdf, row: dict | None, x: float, y: float, width: float, height: float) -> None:
    part = width / 3
    pdf.setStrokeColorRGB(0, 0, 0)
    pdf.setLineWidth(0.6)
    pdf.line(x + part, y, x + part, y + height)
    pdf.line(x + 2 * part, y, x + 2 * part, y + height)
    if not row:
        return
    pdf.setFillColorRGB(0, 0, 0)
    pdf.setFont(FONT_NAME, 9)
    baseline = y + (height - 9) / 2
    for index, key in enumerate(("year", "month", "day")):
        pdf.drawCentredString(x + part * index + part / 2, baseline, str(row.get(key, "") or ""))


def _cell_text(pdf, value: str, x: float, y: float, width: float, height: float, size: float) -> None:
    text = str(value or "").strip()
    if not text:
        return
    fitted = size
    while fitted > 5 and not _wrapped(text, fitted, width - 6, height - 4):
        fitted -= 0.5
    lines = _wrapped(text, fitted, width - 6, height - 4) or [text]
    leading = fitted * 1.15
    block = leading * len(lines)
    cursor = y + (height + block) / 2 - fitted
    pdf.setFillColorRGB(0, 0, 0)
    pdf.setFont(FONT_NAME, fitted)
    for line in lines:
        pdf.drawCentredString(x + width / 2, cursor, line)
        cursor -= leading


def _wrapped(text: str, size: float, width: float, height: float) -> list[str] | None:
    lines: list[str] = []
    for paragraph in text.splitlines():
        current = ""
        for char in paragraph:
            trial = current + char
            if pdfmetrics.stringWidth(trial, FONT_NAME, size) <= width:
                current = trial
            else:
                if current:
                    lines.append(current)
                current = char
        if current:
            lines.append(current)
    if not lines:
        return []
    if size * 1.15 * len(lines) > height:
        return None
    return lines


def _image_at(pdf, path: Path, x: float, y: float, width: float, height: float) -> None:
    with PilImage.open(path) as image:
        prepared = image.convert("RGBA")
        prepared.load()
    reader = ImageReader(prepared)
    src_w, src_h = prepared.size
    if src_w <= 0 or src_h <= 0 or width <= 0 or height <= 0:
        return
    scale = min(width / src_w, height / src_h)
    draw_w = src_w * scale
    draw_h = src_h * scale
    pdf.drawImage(reader, x + (width - draw_w) / 2, y + (height - draw_h) / 2, draw_w, draw_h, mask="auto")


def _workers(values: dict[str, str]) -> list[str]:
    raw = str(values.get("회의참석자", "") or "")
    names = [part.strip() for part in _SPLIT_ATTENDEES.split(raw) if part.strip()]
    return names or [""]


def _display_name(label: str) -> str:
    parts = label.split()
    if len(parts) >= 3:
        return parts[-1]
    return label


def _first_text(values: dict[str, str], keys: tuple[str, ...]) -> str:
    for key in keys:
        text = str(values.get(key, "") or "").strip()
        if text:
            return text
    return ""


def _work_date(value: str) -> tuple[str, str, str]:
    text = str(value or "").strip()
    match = _DATE.search(text)
    if match:
        year, month, day = match.groups()
        return year, str(int(month)), str(int(day))
    match = _SHORT_DATE.search(text)
    if match:
        year, month, day = match.groups()
        return str(2000 + int(year)), str(int(month)), str(int(day))
    return "", "", ""


def _find_signature(label: str, signatures: dict[str, Path]) -> Path | None:
    text = label.strip()
    if not text:
        return None
    if text in signatures:
        return signatures[text]
    last = text.split()[-1]
    if last in signatures:
        return signatures[last]
    for name, path in signatures.items():
        if text.endswith(name):
            return path
    return None


def _register_font() -> None:
    global _font_ready
    if _font_ready:
        return
    pdfmetrics.registerFont(TTFont(FONT_NAME, str(FONT_PATH)))
    _font_ready = True
