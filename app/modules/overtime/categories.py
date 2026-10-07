from enum import Enum

from fastapi import HTTPException, status


class ExpenseCategory(str, Enum):
    OVERTIME = "초과근무"
    MEETING = "회의비"


def normalize_expense_category(value: str | None, *, required: bool) -> str:
    text = "" if value is None else str(value).strip()
    if not text:
        if required:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="연구비항목을 선택해 주세요.")
        return ""
    allowed = {item.value for item in ExpenseCategory}
    if text not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="연구비항목은 초과근무 또는 회의비만 선택할 수 있습니다.",
        )
    return text
