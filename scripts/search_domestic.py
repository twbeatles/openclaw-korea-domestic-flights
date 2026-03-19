#!/usr/bin/env python3
import argparse
import json
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common_cli import (
    airport_label,
    cabin_label,
    format_price,
    normalize_airport,
    parse_flexible_date,
    pretty_date,
    recommendation_line,
)


def normalize_result(item):
    if is_dataclass(item):
        data = asdict(item)
    elif hasattr(item, "__dict__"):
        data = dict(item.__dict__)
    else:
        data = {"value": str(item)}

    return {
        "airline": data.get("airline", ""),
        "price": data.get("price", 0),
        "departure_time": data.get("departure_time", ""),
        "arrival_time": data.get("arrival_time", ""),
        "stops": data.get("stops", 0),
        "source": data.get("source", ""),
        "return_departure_time": data.get("return_departure_time", ""),
        "return_arrival_time": data.get("return_arrival_time", ""),
        "return_stops": data.get("return_stops", 0),
        "is_round_trip": data.get("is_round_trip", False),
        "outbound_price": data.get("outbound_price", 0),
        "return_price": data.get("return_price", 0),
        "return_airline": data.get("return_airline", ""),
        "confidence": data.get("confidence", 0),
        "extraction_source": data.get("extraction_source", ""),
    }


def option_text(item):
    if item.get("is_round_trip"):
        return (
            f"{item.get('airline','')}/{item.get('return_airline') or item.get('airline','')}"
            f" · 총 {format_price(item.get('price', 0))}"
            f" · 가는편 {item.get('departure_time','')}→{item.get('arrival_time','')}"
            f" · 오는편 {item.get('return_departure_time','')}→{item.get('return_arrival_time','')}"
        )
    return f"{item.get('airline','')} · {format_price(item.get('price', 0))} · {item.get('departure_time','')}→{item.get('arrival_time','')}"


def build_summary(query, normalized):
    route = f"{airport_label(query['origin'])} → {airport_label(query['destination'])}"
    trip_type = "왕복" if query.get("return_date") else "편도"

    if not normalized:
        return {
            "headline": f"{route} {trip_type} 검색 결과가 없습니다.",
            "route": route,
            "trip_type": trip_type,
            "cheapest_text": None,
            "top_options": [],
            "recommendation": None,
        }

    cheapest = normalized[0]
    second_price = normalized[1].get("price", 0) if len(normalized) > 1 else None
    return {
        "headline": f"{route} {trip_type} 최저가 {format_price(cheapest.get('price', 0))}",
        "route": route,
        "trip_type": trip_type,
        "cheapest_text": option_text(cheapest),
        "top_options": [option_text(item) for item in normalized[:3]],
        "recommendation": recommendation_line(option_text(cheapest), cheapest.get("price", 0), second_price),
    }


def format_human(summary, query, count):
    lines = [summary["headline"]]
    lines.append(f"조건: 성인 {query['adults']}명 · {cabin_label(query['cabin'])} · 결과 {count}건")
    if query.get("return_date"):
        lines.append(f"일정: {query['departure']} ~ {query['return_date']}")
    else:
        lines.append(f"일정: {query['departure']}")

    if summary.get("cheapest_text"):
        lines.append(f"최저가: {summary['cheapest_text']}")
    if summary.get("recommendation"):
        lines.append(summary["recommendation"])

    if summary.get("top_options"):
        lines.append("상위 옵션:")
        for idx, item in enumerate(summary["top_options"], start=1):
            lines.append(f"{idx}. {item}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Search Korean domestic flights")
    parser.add_argument("--origin", required=True, help="예: GMP 또는 김포")
    parser.add_argument("--destination", required=True, help="예: CJU 또는 제주")
    parser.add_argument("--departure", required=True, help="예: 2026-03-25, 20260325, 내일")
    parser.add_argument("--return-date", dest="return_date", help="예: 2026-03-28, 모레")
    parser.add_argument("--adults", type=int, default=1)
    parser.add_argument("--cabin", default="ECONOMY", choices=["ECONOMY", "BUSINESS", "FIRST"])
    parser.add_argument("--max-results", type=int, default=20)
    parser.add_argument("--human", action="store_true")
    args = parser.parse_args()

    workspace = Path(__file__).resolve().parents[3]
    repo_path = workspace / "tmp" / "Scraping-flight-information"

    if not repo_path.exists():
        print(json.dumps({"status": "error", "message": "Source repository clone not found.", "expected": str(repo_path)}, ensure_ascii=False, indent=2))
        sys.exit(1)

    sys.path.insert(0, str(repo_path))

    try:
        from scraping.searcher import FlightSearcher
    except Exception as exc:
        print(json.dumps({"status": "error", "message": "Failed to import flight searcher.", "details": str(exc), "repo": str(repo_path)}, ensure_ascii=False, indent=2))
        sys.exit(1)

    try:
        origin = normalize_airport(args.origin)
        destination = normalize_airport(args.destination)
        departure = pretty_date(parse_flexible_date(args.departure))
        return_date = pretty_date(parse_flexible_date(args.return_date)) if args.return_date else None
    except ValueError as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False, indent=2))
        sys.exit(1)

    logs = []

    def progress(msg):
        logs.append(str(msg))

    query = {
        "origin": origin,
        "destination": destination,
        "departure": departure,
        "return_date": return_date,
        "adults": args.adults,
        "cabin": args.cabin,
        "max_results": args.max_results,
    }

    searcher = FlightSearcher()
    try:
        results = searcher.search(
            origin=query["origin"],
            destination=query["destination"],
            departure_date=query["departure"],
            return_date=query["return_date"],
            adults=query["adults"],
            cabin_class=query["cabin"],
            max_results=query["max_results"],
            progress_callback=progress,
            background_mode=False,
        )

        normalized = [normalize_result(item) for item in results]
        normalized.sort(key=lambda x: x.get("price", 0) if x.get("price", 0) > 0 else 10**12)
        cheapest = normalized[0] if normalized else None
        summary = build_summary(query, normalized)

        if args.human:
            print(format_human(summary, query, len(normalized)))
            return

        print(json.dumps({
            "status": "success",
            "query": query,
            "count": len(normalized),
            "summary": summary,
            "cheapest": cheapest,
            "results": normalized,
            "logs": logs,
        }, ensure_ascii=False, indent=2))
    finally:
        try:
            searcher.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
