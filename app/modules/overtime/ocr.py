import io
import re

import pytesseract
from PIL import Image, ImageOps

from app.modules.overtime.columns import DRAFT_COLUMNS

_DATE = re.compile(r"(20\d{2})\s*(?:[.\-/]|년)\s*(\d{1,2})\s*(?:[.\-/]|월)\s*(\d{1,2})")
_TIME = re.compile(r"(?<!\d)([01]?\d|2[0-3])\s*(?::|시)\s*([0-5]\d)")
_AMOUNT = re.compile(r"(?<!\d)(\d{1,3}(?:,\d{3})+|\d{3,7})(?!\d)")
_AMOUNT_HINTS = ("합계", "총액", "총금액", "결제금액", "결제 금액", "승인금액", "받을금액", "결제완료", "결제 완료")
_SKIP_LINE = ("사업자", "전화", "카드번호", "승인번호", "가맹점번호", "부가세", "공급가")
_STORE_LABELS = ("가맹점명", "가맹점", "상호명", "상호", "매장명", "매장", "업체명", "가게명", "주문가게")
_STORE_SKIP = ("영수증", "신용카드", "체크카드", "합계", "총액", "결제", "승인", "주소", "대표", "메뉴", "주문", "배달")


def recognize_text(content: bytes) -> str:
    image = ImageOps.exif_transpose(Image.open(io.BytesIO(content)))
    image = ImageOps.autocontrast(image.convert("L"))
    if image.width < 1400:
        image = image.resize((image.width * 2, image.height * 2), Image.Resampling.LANCZOS)
    try:
        return pytesseract.image_to_string(image, lang="kor+eng", config="--psm 6")
    except (pytesseract.TesseractNotFoundError, pytesseract.TesseractError) as exc:
        raise RuntimeError("사진에서 글자를 읽지 못했습니다.") from exc


def extract_fields(text: str) -> dict[str, str]:
    values = {column: "" for column in DRAFT_COLUMNS}
    values["영수증 제출"] = "O"
    values["사용일자"] = _date(text)
    values["사용시각"] = _time(text)
    values["사용금액"] = _amount(text)
    values["사용처"] = _store(text)
    return values


def _lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def _date(text: str) -> str:
    match = _DATE.search(text)
    if match is None:
        return ""
    year, month, day = match.groups()
    return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"


def _time(text: str) -> str:
    for line in _lines(text):
        if any(hint in line for hint in ("결제", "승인", "주문", "시각")):
            match = _TIME.search(line)
            if match is not None:
                hour, minute = match.groups()
                return f"{int(hour):02d}:{minute}"
    match = _TIME.search(text)
    if match is None:
        return ""
    hour, minute = match.groups()
    return f"{int(hour):02d}:{minute}"


def _amount(text: str) -> str:
    hinted: list[int] = []
    others: list[int] = []
    for line in _lines(text):
        if any(word in line for word in _SKIP_LINE):
            continue
        numbers = _numbers(line)
        if any(hint in line.replace(" ", "") for hint in _AMOUNT_HINTS):
            hinted.extend(numbers)
        else:
            others.extend(numbers)
    chosen = hinted[-1] if hinted else (max(others) if others else None)
    if chosen is None:
        return ""
    return f"{chosen:,}"


def _numbers(line: str) -> list[int]:
    numbers: list[int] = []
    for match in _AMOUNT.finditer(line):
        raw = match.group(1).replace(",", "")
        if len(raw) == 4 and raw.startswith("20"):
            continue
        value = int(raw)
        if 100 <= value <= 2_000_000:
            numbers.append(value)
    return numbers


def _store(text: str) -> str:
    lines = _lines(text)
    for index, line in enumerate(lines):
        for label in _STORE_LABELS:
            if label not in line:
                continue
            tail = line.split(label, 1)[1]
            tail = re.sub(r"^[\s:：\-]+", "", tail).strip()
            if _usable_store(tail):
                return tail[:40]
            if index + 1 < len(lines) and _usable_store(lines[index + 1]):
                return lines[index + 1][:40]
    for line in lines[:8]:
        if _usable_store(line):
            return line[:40]
    return ""


def _usable_store(line: str) -> bool:
    hangul = re.findall(r"[가-힣]", line)
    if not 2 <= len(hangul) <= 20:
        return False
    if any(word in line for word in (*_STORE_SKIP, *_SKIP_LINE, *_AMOUNT_HINTS)):
        return False
    if _DATE.search(line) or _AMOUNT.search(line):
        return False
    return True
