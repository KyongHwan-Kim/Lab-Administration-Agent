import base64
import io
import json
import math
import re
from dataclasses import dataclass

import httpx
from PIL import Image, ImageOps

from app.core.config import settings
from app.modules.overtime.columns import DRAFT_COLUMNS

PER_PERSON_WON = 12_000
_OPENAI_URL = "https://api.openai.com/v1/chat/completions"
_DATE = re.compile(r"(20\d{2})\D+(\d{1,2})\D+(\d{1,2})")
_TIME = re.compile(r"(?<!\d)([01]?\d|2[0-3])\s*[:시]\s*([0-5]\d)")

_SYSTEM_PROMPT = """당신은 연구실 초과근무 사용 내역을 정리하는 추출 에이전트입니다.
입력은 배달 내역 사진과 영수증 사진, 그리고 프로젝트에 등록된 카드 목록입니다. 사진에 보이는 내용만 읽고, 추측으로 채우지 마세요.

한 결제(한 주문)당 항목을 하나만 만듭니다. 메뉴 줄마다 항목을 나누지 마세요.
사진이 서로 다른 결제면 항목을 나눕니다.

각 항목에서 다음만 추출합니다.
- usage_date: 결제 또는 주문 날짜. YYYY-MM-DD. 없으면 빈 문자열.
- usage_time: 결제 시각을 우선하고, 없으면 주문 시각. 24시간제 HH:MM. 없으면 빈 문자열.
- amount: 최종 결제 금액(원). 메뉴 단가가 아니라 합계·총결제금액. 모르면 0.
- store_name: 가게 이름(상호). 배달 앱 이름이 아니라 음식점·매장 이름. 주소는 넣지 않습니다.
- meeting_place: 배달 내역 사진의 배달지(수령 장소, 주소, 건물, 동호수). 가게 주소는 넣지 않습니다. 배달 사진이 없으면 빈 문자열.
- card_number: 결제에 사용한 카드 번호. 영수증에 인쇄된 숫자와 * 마스킹을 그대로 적습니다. 공백, 쉼표, 하이픈은 사진 그대로 두어도 됩니다. 카드사 이름만 있고 번호가 없으면 빈 문자열.

카드 끝자리로 프로젝트를 고릅니다.
- 사용자 메시지에 적힌 등록 값은 카드 번호 전체가 아니라 끝자리입니다.
- 영수증에 보이는 카드 번호의 끝자리가 등록된 끝자리와 같으면 같은 카드입니다.
- 그렇게 맞는 카드가 정확히 하나면 matched_project에 그 카드의 프로젝트 이름을 그대로 적습니다.
- 맞는 카드가 없거나 둘 이상이면 matched_project는 빈 문자열입니다. 프로젝트 이름을 추측하지 마세요.

회의시간과 총인원은 계산하지 않습니다. 응답은 지정된 JSON만 출력합니다."""

_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["items"],
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["usage_date", "usage_time", "amount", "store_name", "meeting_place", "card_number", "matched_project"],
                "properties": {
                    "usage_date": {"type": "string"},
                    "usage_time": {"type": "string"},
                    "amount": {"type": "integer"},
                    "store_name": {"type": "string"},
                    "meeting_place": {"type": "string"},
                    "card_number": {"type": "string"},
                    "matched_project": {"type": "string"},
                },
            },
        }
    },
}


class ExtractionError(RuntimeError):
    pass


@dataclass(frozen=True)
class ObservedUsage:
    usage_date: str
    usage_time: str
    amount: int
    store_name: str
    meeting_place: str
    card_number: str
    matched_project: str


@dataclass(frozen=True)
class ExtractedUsage:
    values: dict[str, str]
    card_number: str
    matched_project: str


class UsageExtractAgent:
    """배달 내역과 영수증을 읽고, 회의시간·총인원 규칙을 적용해 사용 내역을 만듭니다."""

    async def run(
        self,
        delivery: list[bytes],
        receipt: list[bytes],
        cards: list[tuple[str, str]],
    ) -> list[ExtractedUsage]:
        observed = await self._read(delivery, receipt, cards)
        drafted = [self._apply_rules(item) for item in observed]
        drafted = [item for item in drafted if _has_content(item.values)]
        if not drafted:
            raise ExtractionError("사진에서 사용 내역을 찾지 못했습니다.")
        return drafted

    async def _read(
        self,
        delivery: list[bytes],
        receipt: list[bytes],
        cards: list[tuple[str, str]],
    ) -> list[ObservedUsage]:
        api_key = settings.openai_api_key.strip()
        if not api_key:
            raise ExtractionError("항목 추출에 필요한 OpenAI API 키가 없습니다. .env 의 OPENAI_API_KEY 를 설정해 주세요.")
        payload = {
            "model": settings.openai_model.strip() or "gpt-4.1-mini",
            "temperature": 0,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": _message_parts(delivery, receipt, cards)},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "usage_extraction", "strict": True, "schema": _SCHEMA},
            },
        }
        try:
            async with httpx.AsyncClient(timeout=90) as client:
                response = await client.post(
                    _OPENAI_URL,
                    headers={"Authorization": f"Bearer {api_key}"},
                    json=payload,
                )
        except httpx.HTTPError as exc:
            raise ExtractionError("항목 추출 서비스에 연결하지 못했습니다.") from exc
        if response.status_code >= 400:
            raise ExtractionError(_api_error(response))
        try:
            content = response.json()["choices"][0]["message"]["content"]
            raw_items = json.loads(content).get("items", [])
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise ExtractionError("항목 추출 결과를 해석하지 못했습니다.") from exc
        return [_observed(item) for item in raw_items if isinstance(item, dict)]

    def _apply_rules(self, item: ObservedUsage) -> ExtractedUsage:
        values = {column: "" for column in DRAFT_COLUMNS}
        values["영수증 제출"] = "O"
        values["사용일자"] = item.usage_date
        values["사용금액"] = f"{item.amount:,}" if item.amount else ""
        values["사용시각"] = item.usage_time
        values["사용처"] = item.store_name
        values["회의시간"] = meeting_window(item.usage_time)
        values["회의장소"] = item.meeting_place
        values["추천인원"] = headcount(item.amount)
        return ExtractedUsage(values=values, card_number=item.card_number, matched_project=item.matched_project)


def meeting_window(usage_time: str) -> str:
    match = re.fullmatch(r"(\d{2}):(\d{2})", usage_time.strip())
    if match is None:
        return ""
    base = int(match.group(1)) * 60 + int(match.group(2))
    start = (base - 120) % (24 * 60)
    end = (base + 120) % (24 * 60)
    return f"{start // 60:02d}:{start % 60:02d}~{end // 60:02d}:{end % 60:02d}"


def headcount(amount: int) -> str:
    if amount <= 0:
        return ""
    count = math.ceil(amount / PER_PERSON_WON)
    return f"{count}명"


def _message_parts(delivery: list[bytes], receipt: list[bytes], cards: list[tuple[str, str]]) -> list[dict]:
    if cards:
        listed = "\n".join(f"- {name}: {number}" for name, number in cards)
        catalog = f"등록된 카드 끝자리입니다. 영수증 카드 번호의 끝자리와 비교해 프로젝트를 고르세요.\n{listed}"
    else:
        catalog = "등록된 카드가 없습니다. card_number만 읽고 matched_project는 빈 문자열로 두세요."
    parts: list[dict] = [
        {
            "type": "text",
            "text": "아래 사진을 역할 라벨대로 읽으세요. 배달 내역은 수령 장소, 영수증은 결제 정보와 카드 번호를 우선합니다.\n" + catalog,
        }
    ]
    if not delivery:
        parts.append({"type": "text", "text": "배달 내역 사진은 없습니다."})
    for index, content in enumerate(delivery, start=1):
        parts.append({"type": "text", "text": f"배달 내역 사진 {index}"})
        parts.append({"type": "image_url", "image_url": {"url": _jpeg_data_url(content), "detail": "high"}})
    if not receipt:
        parts.append({"type": "text", "text": "영수증 사진은 없습니다."})
    for index, content in enumerate(receipt, start=1):
        parts.append({"type": "text", "text": f"영수증 사진 {index}"})
        parts.append({"type": "image_url", "image_url": {"url": _jpeg_data_url(content), "detail": "high"}})
    return parts


def _jpeg_data_url(content: bytes) -> str:
    try:
        image = ImageOps.exif_transpose(Image.open(io.BytesIO(content)))
        image = image.convert("RGB")
    except Exception as exc:
        raise ExtractionError("사진 파일을 열지 못했습니다.") from exc
    image.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=85)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def _observed(item: dict) -> ObservedUsage:
    amount = item.get("amount", 0)
    if isinstance(amount, str):
        digits = re.sub(r"[^\d]", "", amount)
        amount = int(digits) if digits else 0
    if not isinstance(amount, int) or isinstance(amount, bool):
        amount = 0
    if amount < 0 or amount > 100_000_000:
        amount = 0
    return ObservedUsage(
        usage_date=_date(str(item.get("usage_date", ""))),
        usage_time=_clock(str(item.get("usage_time", ""))),
        amount=amount,
        store_name=_clip(str(item.get("store_name", "")), 80),
        meeting_place=_clip(str(item.get("meeting_place", "")), 200),
        card_number=_clip(str(item.get("card_number", "")), 40),
        matched_project=_clip(str(item.get("matched_project", "")), 200),
    )


def _date(value: str) -> str:
    match = _DATE.search(value)
    if match is None:
        return ""
    year, month, day = (int(part) for part in match.groups())
    if not (1 <= month <= 12 and 1 <= day <= 31):
        return ""
    return f"{year:04d}-{month:02d}-{day:02d}"


def _clock(value: str) -> str:
    match = _TIME.search(value)
    if match is None:
        return ""
    hour, minute = match.groups()
    return f"{int(hour):02d}:{minute}"


def _clip(value: str, limit: int) -> str:
    compact = re.sub(r"\s+", " ", value).strip()
    return compact[:limit]


def _has_content(values: dict[str, str]) -> bool:
    return any(values.get(column) for column in ("사용일자", "사용금액", "사용시각", "사용처", "회의장소"))


def _api_error(response: httpx.Response) -> str:
    try:
        message = response.json()["error"]["message"]
    except (KeyError, TypeError, json.JSONDecodeError):
        message = ""
    if response.status_code in {401, 403}:
        return "OpenAI API 키가 올바르지 않습니다."
    if response.status_code == 429:
        return "항목 추출 요청이 한도를 넘었습니다. 잠시 후 다시 시도해 주세요."
    if message:
        return f"항목 추출에 실패했습니다. {message[:180]}"
    return "항목 추출에 실패했습니다."
