"""Airline classification and result filtering ported from Scraping-flight-information.

Source of truth: ``core/airports.py`` (``AIRLINE_CATEGORIES``,
``get_airline_category``) and the desktop GUI filter panel
(직항만 / LCC·FSC 분류 / 시간대 / 경유수 / 가격 범위).
"""
from __future__ import annotations

from collections.abc import Sequence

AIRLINE_CATEGORIES: dict[str, list[str]] = {
    "LCC": [
        "진에어",
        "제주항공",
        "티웨이항공",
        "에어부산",
        "에어서울",
        "이스타항공",
        "피치항공",
        "젯스타",
        "스쿠트",
        "에어아시아",
        "세부퍼시픽",
        "비엣젯",
        "스프링항공",
        "ZipAir",
        "Air Busan",
        "Jin Air",
        "T'way",
        "Jeju Air",
    ],
    "FSC": [
        "대한항공",
        "아시아나항공",
        "일본항공",
        "전일본공수",
        "JAL",
        "ANA",
        "캐세이퍼시픽",
        "싱가포르항공",
        "타이항공",
        "베트남항공",
        "Korean Air",
        "Asiana",
        "Cathay Pacific",
        "Singapore Airlines",
    ],
}

AIRLINE_CATEGORY_LABELS = {
    "LCC": "저비용항공사",
    "FSC": "대형항공사",
    "OTHER": "기타",
}

VALID_AIRLINE_FILTERS = {"all", "LCC", "FSC"}


def get_airline_category(airline_name: str | None) -> str:
    """Return LCC/FSC/OTHER for a display name (matches source logic)."""
    name = (airline_name or "").strip()
    if not name:
        return "OTHER"
    lowered = name.lower()
    for category, airlines in AIRLINE_CATEGORIES.items():
        for candidate in airlines:
            cand = candidate.lower()
            if cand in lowered or lowered in cand:
                return category
    return "OTHER"


def airline_category_label(category: str | None) -> str:
    return AIRLINE_CATEGORY_LABELS.get((category or "").upper(), category or "")


def effective_price(item: dict) -> int:
    """Comparison price: min(price, benefit_price) when benefit exists.

    Mirrors ``scraping.models.effective_flight_price`` in the source repo.
    """
    price = int(item.get("price", 0) or 0)
    benefit = int(item.get("benefit_price", 0) or 0)
    if benefit > 0:
        if price > 0:
            return min(price, benefit)
        return benefit
    return price


def annotate_airline_category(item: dict) -> dict:
    row = dict(item)
    row["airline_category"] = get_airline_category(str(row.get("airline") or ""))
    row["effective_price"] = effective_price(row)
    return row


def filter_by_airline_category(
    items: Sequence[dict], category: str | None
) -> list[dict]:
    normalized = (category or "all").upper()
    if normalized in {"", "ALL", "전체"}:
        return list(items)
    if normalized not in {"LCC", "FSC"}:
        raise ValueError("--airline 은 all, LCC, FSC 중 하나여야 합니다.")
    return [
        item
        for item in items
        if get_airline_category(str(item.get("airline") or "")) == normalized
    ]


def filter_nonstop_only(items: Sequence[dict], nonstop_only: bool) -> list[dict]:
    if not nonstop_only:
        return list(items)
    return [item for item in items if int(item.get("stops", 0) or 0) == 0]


def filter_max_stops(items: Sequence[dict], max_stops: int | None) -> list[dict]:
    if max_stops is None:
        return list(items)
    if max_stops < 0:
        raise ValueError("--max-stops 는 0 이상이어야 합니다.")
    return [item for item in items if int(item.get("stops", 0) or 0) <= max_stops]


def filter_price_range(
    items: Sequence[dict],
    *,
    min_price: int | None = None,
    max_price: int | None = None,
) -> list[dict]:
    if min_price is not None and min_price < 0:
        raise ValueError("--min-price 는 0 이상이어야 합니다.")
    if max_price is not None and max_price < 0:
        raise ValueError("--max-price 는 0 이상이어야 합니다.")
    if min_price is not None and max_price is not None and min_price > max_price:
        raise ValueError("--min-price 는 --max-price 보다 클 수 없습니다.")
    rows = list(items)
    if min_price is not None:
        rows = [item for item in rows if effective_price(item) >= min_price]
    if max_price is not None:
        rows = [item for item in rows if effective_price(item) <= max_price]
    return rows


def apply_airline_filters(
    items: Sequence[dict],
    *,
    airline: str | None = None,
    nonstop_only: bool = False,
    max_stops: int | None = None,
    min_price: int | None = None,
    max_price: int | None = None,
) -> list[dict]:
    rows = [annotate_airline_category(item) for item in items]
    rows = filter_by_airline_category(rows, airline)
    rows = filter_nonstop_only(rows, nonstop_only)
    rows = filter_max_stops(rows, max_stops)
    rows = filter_price_range(rows, min_price=min_price, max_price=max_price)
    return rows
