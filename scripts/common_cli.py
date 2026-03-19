from __future__ import annotations

from datetime import datetime, timedelta

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


def parse_flexible_date(value: str) -> datetime:
    raw = value.strip().lower()
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
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
    for fmt in ("%Y-%m-%d", "%Y%m%d", "%Y.%m.%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            pass
    raise ValueError(f"지원하지 않는 날짜 형식입니다: {value}")


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
