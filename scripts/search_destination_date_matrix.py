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
    unique_codes,
)


def build_dates(start_date, end_date):
    days = []
    current = start_date
    while current <= end_date:
        days.append(current)
        current += timedelta(days=1)
    return days


def main():
    parser = argparse.ArgumentParser(description="Search combined destination/date ranges for Korean domestic flights")
    parser.add_argument("--origin", required=True)
    parser.add_argument("--destinations", required=True, help="쉼표 구분 목적지 목록")
    parser.add_argument("--start-date")
    parser.add_argument("--end-date")
    parser.add_argument("--date-range", help="예: 내일부터 5일, 2026-03-25~2026-03-30")
    parser.add_argument("--return-offset", type=int, default=0)
    parser.add_argument("--adults", type=int, default=1)
    parser.add_argument("--cabin", default="ECONOMY", choices=["ECONOMY", "BUSINESS", "FIRST"])
    parser.add_argument("--human", action="store_true")
    args = parser.parse_args()

    try:
        origin = normalize_airport(args.origin)
        destinations = unique_codes([normalize_airport(x.strip()) for x in args.destinations.split(",") if x.strip()])
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
    if len(dates) * len(destinations) > 90:
        print(json.dumps({"status": "error", "message": "검색 조합 수는 90개 이하로 제한됩니다."}, ensure_ascii=False, indent=2))
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
    destination_rows = []
    combos = []
    searcher = ParallelSearcher()

    for destination in destinations:
        logs.append(f"matrix search start: {destination}")
        raw = searcher.search_date_range(
            origin=origin,
            destination=destination,
            dates=[d.strftime("%Y%m%d") for d in dates],
            return_offset=args.return_offset,
            adults=args.adults,
            cabin_class=args.cabin,
            progress_callback=lambda msg, dest=destination: logs.append(f"[{dest}] {msg}"),
        )
        rows = []
        for d in dates:
            key = d.strftime("%Y%m%d")
            price, airline = raw.get(key, (0, "N/A"))
            row = {
                "destination": destination,
                "destination_label": airport_label(destination),
                "departure_date": pretty_date(d),
                "return_date": pretty_date(d + timedelta(days=args.return_offset)) if args.return_offset > 0 else None,
                "price": price,
                "airline": airline,
            }
            rows.append(row)
            combos.append(row)
        available_rows = [row for row in rows if row["price"] and row["price"] > 0]
        available_rows.sort(key=lambda x: x["price"])
        destination_rows.append({
            "destination": destination,
            "destination_label": airport_label(destination),
            "best_option": available_rows[0] if available_rows else None,
            "top_dates": available_rows[:3],
        })

    ranked_combos = sorted([row for row in combos if row["price"] and row["price"] > 0], key=lambda x: x["price"])
    best = ranked_combos[0] if ranked_combos else None
    second_price = ranked_combos[1]["price"] if len(ranked_combos) > 1 else None

    destination_rows.sort(key=lambda x: x["best_option"]["price"] if x["best_option"] else 10**12)
    summary = {
        "headline": (
            f"{airport_label(origin)} 출발 최적 조합은 {best['destination_label']} {best['departure_date']} {format_price(best['price'])}"
            if best else
            f"{airport_label(origin)} 출발 목적지+날짜 범위 검색 결과가 없습니다."
        ),
        "range": f"{pretty_date(start_dt)} ~ {pretty_date(end_dt)}",
        "best_combo": best,
        "top_combos": ranked_combos[:7],
        "by_destination": destination_rows,
        "recommendation": recommendation_line(
            f"{best['destination_label']} / {best['departure_date']}{f'~{best['return_date']}' if best and best['return_date'] else ''}",
            best["price"],
            second_price,
        ) if best else None,
    }

    if args.human:
        lines = [summary["headline"]]
        lines.append(f"범위: {summary['range']}")
        lines.append(f"조건: 출발 {airport_label(origin)} · 목적지 {len(destinations)}곳 · 성인 {args.adults}명 · {cabin_label(args.cabin)}")
        if args.return_offset > 0:
            lines.append(f"왕복 기준: 출발일 + {args.return_offset}일 귀국")
        if best:
            date_text = f"{best['departure_date']} ~ {best['return_date']}" if best["return_date"] else best["departure_date"]
            lines.append(f"최적 조합: {best['destination_label']} · {date_text} · {format_price(best['price'])} · {best['airline']}")
        if summary.get("recommendation"):
            lines.append(summary["recommendation"])
        if destination_rows:
            lines.append("목적지별 베스트:")
            for idx, item in enumerate(destination_rows[:5], start=1):
                best_option = item["best_option"]
                if best_option:
                    date_text = f"{best_option['departure_date']} ~ {best_option['return_date']}" if best_option["return_date"] else best_option["departure_date"]
                    lines.append(f"{idx}. {item['destination_label']} · {date_text} · {format_price(best_option['price'])} · {best_option['airline']}")
                else:
                    lines.append(f"{idx}. {item['destination_label']} · 결과 없음")
        if ranked_combos:
            lines.append("전체 상위 조합:")
            for idx, item in enumerate(ranked_combos[:7], start=1):
                date_text = f"{item['departure_date']} ~ {item['return_date']}" if item["return_date"] else item["departure_date"]
                lines.append(f"{idx}. {item['destination_label']} · {date_text} · {format_price(item['price'])} · {item['airline']}")
        print("\n".join(lines))
        return

    print(json.dumps({
        "status": "success",
        "query": {
            "origin": origin,
            "destinations": destinations,
            "start_date": pretty_date(start_dt),
            "end_date": pretty_date(end_dt),
            "return_offset": args.return_offset,
            "adults": args.adults,
            "cabin": args.cabin,
        },
        "summary": summary,
        "results": ranked_combos,
        "matrix": destination_rows,
        "logs": logs,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
