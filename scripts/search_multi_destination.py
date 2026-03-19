#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common_cli import (
    airport_label,
    cabin_label,
    bullet_rank_lines,
    format_price,
    normalize_airport,
    parse_flexible_date,
    pretty_date,
    recommendation_line,
    unique_codes,
)


def main():
    parser = argparse.ArgumentParser(description="Compare Korean domestic flight fares across multiple destinations")
    parser.add_argument("--origin", required=True)
    parser.add_argument("--destinations", required=True, help="Comma-separated destinations, e.g. CJU,PUS,RSU or 제주,부산,여수")
    parser.add_argument("--departure", required=True)
    parser.add_argument("--return-date")
    parser.add_argument("--adults", type=int, default=1)
    parser.add_argument("--cabin", default="ECONOMY", choices=["ECONOMY", "BUSINESS", "FIRST"])
    parser.add_argument("--human", action="store_true")
    args = parser.parse_args()

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

    try:
        origin = normalize_airport(args.origin)
        destinations = unique_codes([normalize_airport(x.strip()) for x in args.destinations.split(",") if x.strip()])
        departure = pretty_date(parse_flexible_date(args.departure))
        return_date = pretty_date(parse_flexible_date(args.return_date)) if args.return_date else None
    except ValueError as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False, indent=2))
        sys.exit(1)

    logs = []

    def progress(msg):
        logs.append(str(msg))

    searcher = ParallelSearcher()
    raw = searcher.search_multiple_destinations(
        origin=origin,
        destinations=destinations,
        departure_date=departure.replace("-", ""),
        return_date=return_date.replace("-", "") if return_date else None,
        adults=args.adults,
        cabin_class=args.cabin,
        progress_callback=progress,
    )

    normalized = []
    for dest in destinations:
        results = raw.get(dest, []) or []
        cheapest = min(results, key=lambda x: x.price) if results else None
        normalized.append({
            "destination": dest,
            "destination_label": airport_label(dest),
            "count": len(results),
            "cheapest_price": cheapest.price if cheapest else 0,
            "airline": cheapest.airline if cheapest else "",
            "departure_time": cheapest.departure_time if cheapest else "",
            "arrival_time": cheapest.arrival_time if cheapest else "",
        })

    ranked = sorted(normalized, key=lambda x: x["cheapest_price"] if x["cheapest_price"] > 0 else 10**12)
    best = ranked[0] if ranked and ranked[0]["cheapest_price"] > 0 else None
    second_price = ranked[1]["cheapest_price"] if len(ranked) > 1 and ranked[1]["cheapest_price"] > 0 else None

    summary = {
        "headline": (
            f"{airport_label(origin)} 출발 다중 목적지 최저가 {format_price(best['cheapest_price'])}"
            if best else
            f"{airport_label(origin)} 출발 다중 목적지 검색 결과가 없습니다."
        ),
        "best_option": best,
        "ranked_destinations": ranked,
        "recommendation": recommendation_line(best["destination_label"], best["cheapest_price"], second_price) if best else None,
    }

    if args.human:
        lines = [summary["headline"]]
        lines.append(f"조건: 출발 {airport_label(origin)} · 출발일 {departure} · 성인 {args.adults}명 · {cabin_label(args.cabin)}")
        if return_date:
            lines.append(f"왕복 일정: {departure} ~ {return_date}")
        if best:
            lines.append(f"최적 목적지: {best['destination_label']} · {format_price(best['cheapest_price'])} · {best['airline']} · {best['departure_time']}→{best['arrival_time']}")
        if summary.get("recommendation"):
            lines.append(summary["recommendation"])
        if ranked:
            lines.append("목적지 비교:")
            lines.extend(bullet_rank_lines(ranked, "destination_label", "cheapest_price", lambda item: f"{item['airline']} · {item['departure_time']}→{item['arrival_time']}", limit=5))
        print("\n".join(lines))
        return

    print(json.dumps({
        "status": "success",
        "query": {
            "origin": origin,
            "destinations": destinations,
            "departure": departure,
            "return_date": return_date,
            "adults": args.adults,
            "cabin": args.cabin,
        },
        "summary": summary,
        "results": ranked,
        "logs": logs,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
