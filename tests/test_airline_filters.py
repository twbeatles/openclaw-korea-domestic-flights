"""Tests for the Scraping-flight-information feature port.

Covers: airline categories (LCC/FSC), option filters (nonstop/max-stops/
price range), extended airport aliases, child/infant/force-refresh
plumbing, and alert-rule filter round-trips.
"""
from __future__ import annotations

from argparse import Namespace

import pytest

from korea_flights.airlines import (
    apply_airline_filters,
    effective_price,
    filter_by_airline_category,
    filter_max_stops,
    filter_nonstop_only,
    filter_price_range,
    get_airline_category,
)
from korea_flights.airports import normalize_airport
from korea_flights.alerts import describe_rule, load_store, make_rule
from korea_flights.cli import build_parser
from korea_flights.results import normalize_result_payload
from korea_flights.strategy import HybridStrategyEngine, build_search_filters


class FakeAdapter:
    """Test double speaking the new source-adapter signature."""

    def __init__(self):
        self.calls: list[dict] = []

    def broad_date_range(self, *, origin, destination, dates, return_offset=0,
                         adults=1, child=0, infant=0, cabin_class="ECONOMY",
                         progress_callback=None):
        self.calls.append({"child": child, "infant": infant, "cabin_class": cabin_class})
        prices = {
            "20260325": (120000, "대한항공"),
            "20260326": (90000, "진에어"),
            "20260327": (95000, "제주항공"),
        }
        return {date: prices.get(date, (0, "N/A")) for date in dates}

    def search(self, *, origin, destination, departure_date, return_date=None,
               adults=1, child=0, infant=0, cabin_class="ECONOMY", max_results=1000,
               background_mode=False, force_refresh=False, progress_callback=None):
        self.calls.append(
            {"child": child, "infant": infant, "force_refresh": force_refresh,
             "departure_date": departure_date}
        )
        if departure_date == "2026-03-26":
            return [
                {"airline": "진에어", "price": 90000, "departure_time": "19:10",
                 "arrival_time": "20:10", "stops": 0, "benefit_price": 87000,
                 "benefit_label": "카드혜택", "source": "Interpark",
                 "extraction_source": "domestic_api", "confidence": 0.9},
                {"airline": "대한항공", "price": 150000, "departure_time": "09:00",
                 "arrival_time": "10:00", "stops": 1, "source": "Interpark",
                 "extraction_source": "domestic_api", "confidence": 0.8},
            ]
        return []


def test_airline_category_matches_source_table():
    assert get_airline_category("진에어") == "LCC"
    assert get_airline_category("제주항공") == "LCC"
    assert get_airline_category("대한항공") == "FSC"
    assert get_airline_category("JAL") == "FSC"
    assert get_airline_category("알 수 없는 항공사") == "OTHER"
    assert get_airline_category("") == "OTHER"


def test_effective_price_prefers_benefit():
    assert effective_price({"price": 90000, "benefit_price": 87000}) == 87000
    assert effective_price({"price": 90000, "benefit_price": 0}) == 90000
    assert effective_price({"price": 0, "benefit_price": 87000}) == 87000


def test_option_filters_compose():
    rows = [
        {"airline": "진에어", "price": 90000, "stops": 0},
        {"airline": "대한항공", "price": 150000, "stops": 1},
        {"airline": "제주항공", "price": 95000, "stops": 0},
    ]
    assert [r["airline"] for r in filter_by_airline_category(rows, "LCC")] == ["진에어", "제주항공"]
    assert [r["airline"] for r in filter_nonstop_only(rows, True)] == ["진에어", "제주항공"]
    assert [r["airline"] for r in filter_max_stops(rows, 0)] == ["진에어", "제주항공"]
    assert [r["airline"] for r in filter_price_range(rows, max_price=100000)] == ["진에어", "제주항공"]
    combined = apply_airline_filters(rows, airline="LCC", nonstop_only=True, max_price=92000)
    assert [r["airline"] for r in combined] == ["진에어"]
    with pytest.raises(ValueError):
        filter_by_airline_category(rows, "UNKNOWN")
    with pytest.raises(ValueError):
        filter_max_stops(rows, -1)
    with pytest.raises(ValueError):
        filter_price_range(rows, min_price=200000, max_price=100000)


def test_result_payload_carries_category_and_effective_price():
    payload = normalize_result_payload({"airline": "진에어", "price": 90000, "benefit_price": 87000})
    assert payload["airline_category"] == "LCC"
    assert payload["effective_price"] == 87000


def test_extended_airport_aliases():
    assert normalize_airport("삿포로") == "CTS"
    assert normalize_airport("sapporo") == "CTS"
    assert normalize_airport("타이베이") == "TPE"
    assert normalize_airport("대만") == "TPE"
    assert normalize_airport("오키나와") == "OKA"
    assert normalize_airport("나고야") == "NGO"
    assert normalize_airport("하노이") == "HAN"
    assert normalize_airport("세부") == "CEB"
    assert normalize_airport("인천") == "ICN"


def test_build_search_filters_validates_eagerly():
    filters = build_search_filters(airline="LCC", nonstop_only=True, max_stops=0, max_price=200000)
    assert filters.active()
    assert "LCC" in (filters.describe() or "")
    assert not build_search_filters().active()
    with pytest.raises(ValueError):
        build_search_filters(airline="UNKNOWN")


def test_search_single_applies_filters_and_passengers():
    adapter = FakeAdapter()
    engine = HybridStrategyEngine(source_adapter=adapter)
    payload = engine.search_single(
        origin="GMP", destination="CJU", departure="2026-03-26",
        child=1, force_refresh=True, airline="LCC", nonstop_only=True,
    )
    assert payload["status"] == "success"
    assert payload["query"]["child"] == 1
    assert payload["query"]["force_refresh"] is True
    assert payload["query"]["filters"]["airline"] == "LCC"
    assert payload["strategy_metadata"]["filter_active"] is True
    assert [r["airline"] for r in payload["results"]] == ["진에어"]
    assert payload["results"][0]["airline_category"] == "LCC"
    assert adapter.calls and adapter.calls[0]["child"] == 1
    assert adapter.calls[0]["force_refresh"] is True


def test_search_single_reports_airline_filter_no_match():
    adapter = FakeAdapter()
    engine = HybridStrategyEngine(source_adapter=adapter)
    payload = engine.search_range(
        origin="GMP", destination="CJU",
        start_date="2026-03-26", end_date="2026-03-26",
        airline="FSC", nonstop_only=True,
    )
    assert payload["status"] == "success"
    assert payload["results"] == []
    assert payload["summary"]["best_date"] is None
    counts = (payload["diagnostics"] or {}).get("counts", {})
    assert "airline_filter_no_match" in counts


def test_cli_exposes_new_options():
    parser = build_parser()
    for command in ("search", "range", "matrix"):
        text = parser.format_help()
        assert command in text
    args = parser.parse_args(
        ["search", "--origin", "GMP", "--destination", "CJU", "--departure", "내일",
         "--child", "1", "--force-refresh", "--airline", "LCC", "--nonstop-only",
         "--max-stops", "0", "--max-price", "200000"]
    )
    assert args.child == 1
    assert args.force_refresh is True
    assert args.airline == "LCC"
    assert args.nonstop_only is True
    assert args.max_stops == 0
    assert args.max_price == 200000


def test_alert_rule_round_trip_with_filters(tmp_path):
    store = tmp_path / "alerts.json"
    args = Namespace(
        origin="ICN", destination="CTS", destinations=None, departure="2026-09-10",
        return_date=None, date_range=None, return_offset=0, scope="international",
        adults=1, child=1, infant=0, cabin="ECONOMY", target_price=200000,
        airline="LCC", nonstop_only=True, max_stops=0, min_price=None, max_price=250000,
        time_pref=None, depart_after=None, return_after=None, exclude_early_before=None,
        prefer=None, rule_id="kf-test", label=None, message_template=None, notes=None,
        repo_path=None,
    )
    rule = make_rule(args)
    assert rule["query"]["child"] == 1
    assert rule["query"]["filters"]["airline"] == "LCC"
    assert rule["query"]["filters"]["nonstop_only"] is True
    text = describe_rule(rule)
    assert "소아 1명" in text
    assert "LCC" in text
    data = load_store(store)
    data["rules"].append(rule)
    assert load_store(store)["rules"] == []  # unsaved store stays empty
    from korea_flights.alerts import save_store
    save_store(store, data)
    reloaded = load_store(store)
    assert reloaded["rules"][0]["query"]["filters"]["airline"] == "LCC"
