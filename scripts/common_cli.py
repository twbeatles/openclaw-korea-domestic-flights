from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Iterable, List, Sequence

AIRPORT_NAMES = {
    "GMP": "김포",
    "CJU": "제주",
    "PUS": "부산",
    "TAE": "대구",
    "CJJ": "청주",
    "KWJ": "광주",
    "RSU": "여수",
    "USN": "울산",
    "HIN": "사천",
    "KPO": "포항경주",
    "YNY": "양양",
    "MWX": "무안",
    "SEL": "서울",
}

AIRPORT_ALIASES = {
    "김포": "GMP",
    "제주": "CJU",
    "제주도": "CJU",
    "부산": "PUS",
    "김해": "PUS",
    "대구": "TAE",
    "청주": "CJJ",
    "광주": "KWJ",
    "여수": "RSU",
    "울산": "USN",
    "사천": "HIN",
    "진주": "HIN",
    "포항": "KPO",
    "포항경주": "KPO",
    "양양": "YNY",
    "무안": "MWX",
    "서울": "SEL",
    "gimpo": "GMP",
    "jeju": "CJU",
    "busan": "PUS",
    "daegu": "TAE",
    "cheongju": "CJJ",
    "gwangju": "KWJ",
    "yeosu": "RSU",
    "ulsan": "USN",
    "sacheon": "HIN",
    "pohang": "KPO",
    "yangyang": "YNY",
    "muan": "MWX",
    "seoul": "SEL",
}

WEEKDAY_ALIASES = {
    "월": 0,
    "월요일": 0,
    "화": 1,
    "화요일": 1,
    "수": 2,
    "수요일": 2,
    "목": 3,
    "목요일": 3,
    "금": 4,
    "금요일": 4,
    "토": 5,
    "토요일": 5,
    "일": 6,
    "일요일": 6,
}


def airport_label(code: str) -> str:
    code = (code or "").upper()
    return f"{AIRPORT_NAMES.get(code, code)}({code})" if code else ""


def normalize_airport(value: str) -> str:
    if not value:
        raise ValueError("공항 값이 비어 있습니다.")
    raw = value.strip()
    upper = raw.upper()
    if upper in AIRPORT_NAMES:
        return upper
    lowered = raw.lower()
    if lowered in AIRPORT_ALIASES:
        return AIRPORT_ALIASES[lowered]
    if raw in AIRPORT_ALIASES:
        return AIRPORT_ALIASES[raw]
    raise ValueError(f"지원하지 않는 공항 입력입니다: {value}")


def _base_today() -> datetime:
    return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)


def _parse_month_day(raw: str, today: datetime) -> datetime | None:
    match = re.fullmatch(r"(\d{1,2})[./\-월\s]+(\d{1,2})(?:일)?", raw)
    if not match:
        return None
    month = int(match.group(1))
    day = int(match.group(2))
    year = today.year
    candidate = datetime(year, month, day)
    if candidate < today:
        candidate = datetime(year + 1, month, day)
    return candidate


def _parse_relative_days(raw: str, today: datetime) -> datetime | None:
    match = re.fullmatch(r"(\d+)\s*(?:일 뒤|일후|days? later)", raw)
    if match:
        return today + timedelta(days=int(match.group(1)))
    match = re.fullmatch(r"(\d+)\s*(?:주 뒤|주후)", raw)
    if match:
        return today + timedelta(days=7 * int(match.group(1)))
    return None


def _next_weekday(today: datetime, weekday: int, week_offset: int = 0) -> datetime:
    days_ahead = (weekday - today.weekday()) % 7
    candidate = today + timedelta(days=days_ahead + week_offset * 7)
    if week_offset == 0 and candidate < today:
        candidate += timedelta(days=7)
    return candidate


def _parse_weekday(raw: str, today: datetime) -> datetime | None:
    raw = raw.strip()
    for prefix, offset in (("이번주 ", 0), ("이번 주 ", 0), ("다음주 ", 1), ("다음 주 ", 1), ("오는 ", 0)):
        if raw.startswith(prefix):
            tail = raw[len(prefix):].strip()
            if tail in WEEKDAY_ALIASES:
                return _next_weekday(today, WEEKDAY_ALIASES[tail], offset)
    if raw in WEEKDAY_ALIASES:
        return _next_weekday(today, WEEKDAY_ALIASES[raw], 0)
    if raw in ("주말", "이번주말", "이번 주말"):
        return _next_weekday(today, 5, 0)
    if raw in ("다음주말", "다음 주말"):
        return _next_weekday(today, 5, 1)
    return None


def parse_flexible_date(value: str) -> datetime:
    raw = value.strip().lower()
    today = _base_today()
    mapping = {
        "today": 0,
        "오늘": 0,
        "tomorrow": 1,
        "내일": 1,
        "day after tomorrow": 2,
        "모레": 2,
        "글피": 3,
    }
    if raw in mapping:
        return today + timedelta(days=mapping[raw])
    relative = _parse_relative_days(raw, today)
    if relative:
        return relative
    weekday = _parse_weekday(raw, today)
    if weekday:
        return weekday
    month_day = _parse_month_day(raw.replace("  ", " "), today)
    if month_day:
        return month_day
    for fmt in ("%Y-%m-%d", "%Y%m%d", "%Y.%m.%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            pass
    raise ValueError(f"지원하지 않는 날짜 형식입니다: {value}")


def parse_date_range_text(value: str) -> tuple[datetime, datetime]:
    raw = value.strip().lower()
    today = _base_today()
    m = re.fullmatch(r"(.+?)부터\s*(\d+)일", raw)
    if m:
        start = parse_flexible_date(m.group(1))
        days = int(m.group(2))
        return start, start + timedelta(days=max(days - 1, 0))
    if raw in ("이번주말", "이번 주말", "주말"):
        start = _next_weekday(today, 5, 0)
        return start, start + timedelta(days=1)
    if raw in ("다음주말", "다음 주말"):
        start = _next_weekday(today, 5, 1)
        return start, start + timedelta(days=1)
    parts = re.split(r"\s*(?:~|부터|to|-)\s*", value)
    if len(parts) == 2 and all(part.strip() for part in parts):
        start = parse_flexible_date(parts[0].strip())
        end = parse_flexible_date(parts[1].strip())
        return start, end
    single = parse_flexible_date(value)
    return single, single


def pretty_date(value: datetime) -> str:
    return value.strftime("%Y-%m-%d")


def compact_date(value: datetime) -> str:
    return value.strftime("%Y%m%d")


def cabin_label(code: str) -> str:
    return {
        "ECONOMY": "이코노미",
        "BUSINESS": "비즈니스",
        "FIRST": "일등석",
    }.get((code or "").upper(), code or "")


def format_price(value: int | float | None) -> str:
    return f"{int(value or 0):,}원"


def summarize_price_gap(best_price: int, next_price: int | None) -> str | None:
    if not best_price or not next_price or next_price <= best_price:
        return None
    gap = next_price - best_price
    ratio = round((gap / best_price) * 100)
    return f"2위보다 {gap:,}원 저렴해 가성비가 좋습니다{f' (약 {ratio}% 차이)' if ratio >= 5 else ''}."


def recommendation_line(subject: str, best_price: int, next_price: int | None = None) -> str:
    gap_text = summarize_price_gap(best_price, next_price)
    if gap_text:
        return f"추천: 이번 조건에서는 {subject}이(가) 가장 유리합니다. {gap_text}"
    return f"추천: 이번 조건에서는 {subject}이(가) 가장 무난한 최저가 선택입니다."


def bullet_rank_lines(items: Sequence[dict], label_key: str, price_key: str, detail_builder=None, limit: int = 5) -> List[str]:
    lines: List[str] = []
    for idx, item in enumerate(items[:limit], start=1):
        label = item.get(label_key, "옵션")
        price = item.get(price_key, 0)
        if price and price > 0:
            detail = detail_builder(item) if detail_builder else ""
            suffix = f" · {detail}" if detail else ""
            lines.append(f"{idx}. {label} · {format_price(price)}{suffix}")
        else:
            lines.append(f"{idx}. {label} · 결과 없음")
    return lines


def unique_codes(values: Iterable[str]) -> list[str]:
    seen = set()
    output = []
    for value in values:
        if value not in seen:
            seen.add(value)
            output.append(value)
    return output
