#!/usr/bin/env python3
import argparse
import json
import sys
from datetime import timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common_cli import (
    airport_label,
    cabin_label,
    format_price,
    normalize_airport,
    parse_date_range_text,
    parse_flexible_date,
    pretty_date,
    recommendation_line,
)


def build_dates(start_date, end_date):
    days = []
    current = start_date
    while current <= end_date:
        days.append(current)
        current += timedelta(days=1)
    return days


def main():
    parser = argparse.ArgumentParser(description="Search Korean domestic flights across date ranges")
    parser.add_argument("--origin", required=True, help="예: GMP 또는 김포")
    parser.add_argument("--destination", required=True, help="예: CJU 또는 제주")
    parser.add_argument("--start-date", help="예: 2026-03-25, 내일")
    parser.add_argument("--end-date", help="예: 2026-03-30")
    parser.add_argument("--date-range", help="예: 내일부터 3일, 이번주말, 2026-03-25~2026-03-30")
    parser.add_argument("--return-offset", type=int, default=0)
    parser.add_argument("--adults", type=int, default=1)
    parser.add_argument("--cabin", default="ECONOMY", choices=["ECONOMY", "BUSINESS", "FIRST"])
    parser.add_argument("--human", action="store_true")
    args = parser.parse_args()

    try:
        origin = normalize_airport(args.origin)
        destination = normalize_airport(args.destination)
        if args.date_range:
            start_dt, end_dt = parse_date_range_text(args.date_range)
        elif args.start_date and args.end_date:
            start_dt = parse_flexible_date(args.start_date)
            end_dt = parse_flexible_date(args.end_date)
        else:
            raise ValueError("start/end-date 또는 --date-range 중 하나를 제공해야 합니다.")
    except ValueError as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False, indent=2))
        sys.exit(1)

    if end_dt < start_dt:
        print(json.dumps({"status": "error", "message": "end-date must be after or equal to start-date"}, ensure_ascii=False, indent=2))
        sys.exit(1)

    dates = build_dates(start_dt, end_dt)
    if len(dates) > 30:
        print(json.dumps({"status": "error", "message": "date range must be 30 days or less"}, ensure_ascii=False, indent=2))
        sys.exit(1)

    workspace = Path(__file__).resolve().parents[3]
    repo_path = workspace / "tmp" / "Scraping-flight-information"
    if not repo_path.exists():
        print(json.dumps({"status": "error", "message": "Source repository clone not found.", "expected": str(repo_path)}, ensure_ascii=False, indent=2))
        sys.exit(1)

    sys.path.insert(0, str(repo_path))

    try:
        from scraping.parallel import ParallelSearcher
    except Exception as exc:
        print(json.dumps({"status": "error", "message": "Failed to import parallel searcher.", "details": str(exc)}, ensure_ascii=False, indent=2))
        sys.exit(1)

    logs = []

    def progress(msg):
        logs.append(str(msg))

    searcher = ParallelSearcher()
    raw = searcher.search_date_range(
        origin=origin,
        destination=destination,
        dates=[d.strftime("%Y%m%d") for d in dates],
        return_offset=args.return_offset,
        adults=args.adults,
        cabin_class=args.cabin,
        progress_callback=progress,
    )

    normalized = []
    for d in dates:
        key = d.strftime("%Y%m%d")
        price, airline = raw.get(key, (0, "N/A"))
        normalized.append({
            "departure_date": pretty_date(d),
            "return_date": pretty_date(d + timedelta(days=args.return_offset)) if args.return_offset > 0 else None,
            "price": price,
            "airline": airline,
        })

    available = [item for item in normalized if item["price"] and item["price"] > 0]
    available.sort(key=lambda x: x["price"])
    cheapest = available[0] if available else None
    second_price = available[1]["price"] if len(available) > 1 else None

    summary = {
        "headline": (
            f"{airport_label(origin)} → {airport_label(destination)} 날짜범위 최저가 {format_price(cheapest['price'])}"
            if cheapest else
            f"{airport_label(origin)} → {airport_label(destination)} 날짜범위 검색 결과가 없습니다."
        ),
        "range": f"{pretty_date(start_dt)} ~ {pretty_date(end_dt)}",
        "trip_type": "왕복 범위검색" if args.return_offset > 0 else "편도 범위검색",
        "best_date": cheapest,
        "top_dates": available[:5],
        "recommendation": recommendation_line(
            f"{cheapest['departure_date']}{f'~{cheapest['return_date']}' if cheapest and cheapest['return_date'] else ''}",
            cheapest["price"],
            second_price,
        ) if cheapest else None,
    }

    if args.human:
        lines = [summary["headline"]]
        lines.append(f"범위: {summary['range']}")
        lines.append(f"조건: 성인 {args.adults}명 · {cabin_label(args.cabin)}")
        if args.return_offset > 0:
            lines.append(f"왕복 기준: 출발일 + {args.return_offset}일 귀국")
        if cheapest:
            if cheapest["return_date"]:
                lines.append(f"최저가 날짜: {cheapest['departure_date']} ~ {cheapest['return_date']} · {format_price(cheapest['price'])} · {cheapest['airline']}")
            else:
                lines.append(f"최저가 날짜: {cheapest['departure_date']} · {format_price(cheapest['price'])} · {cheapest['airline']}")
        if summary.get("recommendation"):
            lines.append(summary["recommendation"])
        if summary["top_dates"]:
            lines.append("상위 날짜:")
            for idx, item in enumerate(summary["top_dates"], start=1):
                if item["return_date"]:
                    lines.append(f"{idx}. {item['departure_date']} ~ {item['return_date']} · {format_price(item['price'])} · {item['airline']}")
                else:
                    lines.append(f"{idx}. {item['departure_date']} · {format_price(item['price'])} · {item['airline']}")
        print("\n".join(lines))
        return

    print(json.dumps({
        "status": "success",
        "query": {
            "origin": origin,
            "destination": destination,
            "start_date": pretty_date(start_dt),
            "end_date": pretty_date(end_dt),
            "return_offset": args.return_offset,
            "adults": args.adults,
            "cabin": args.cabin,
        },
        "summary": summary,
        "results": normalized,
        "logs": logs,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
