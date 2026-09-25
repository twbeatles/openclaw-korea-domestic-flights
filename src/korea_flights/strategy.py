from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Protocol

from .airlines import apply_airline_filters
from .airports import airport_label, normalize_airport, resolve_route_scope, unique_codes
from .dates import build_dates, compact_date, parse_date_range_text, parse_flexible_date, pretty_date, verify_date_order, verify_return_offset
from .diagnostics import build_refine_diagnostics, choose_fallback_plan
from .formatting import build_matrix_summary, build_range_summary, build_single_summary
from .results import make_broad_row, normalize_result_payload, priced_rows, unverified_broad_rows, verified_priced_rows
from .source import FlightSourceAdapter
from .timeprefs import TimePreference, build_time_preference, filter_and_rank_by_time_preference


@dataclass
class StrategyLimits:
    max_days: int = 45
    max_combos: int = 120
    refine_budget: int = 8
    fallback_budget: int = 6


@dataclass
class SearchFilters:
    """Option-level filters ported from the source repo GUI filter panel.

    - airline: all | LCC | FSC (항공사 분류 필터)
    - nonstop_only: 직항만
    - max_stops: 허용 최대 경유 횟수
    - min_price/max_price: 실질가(혜택가 적용) 예산 범위
    """

    airline: str | None = None
    nonstop_only: bool = False
    max_stops: int | None = None
    min_price: int | None = None
    max_price: int | None = None

    def active(self) -> bool:
        return bool(
            (self.airline and self.airline.upper() != "ALL")
            or self.nonstop_only
            or self.max_stops is not None
            or self.min_price is not None
            or self.max_price is not None
        )

    def describe(self) -> str | None:
        parts: list[str] = []
        if self.airline and self.airline.upper() != "ALL":
            parts.append(f"항공사 {self.airline.upper()}")
        if self.nonstop_only:
            parts.append("직항만")
        if self.max_stops is not None:
            parts.append(f"최대 경유 {self.max_stops}회")
        if self.min_price is not None or self.max_price is not None:
            low = f"{self.min_price:,}원" if self.min_price is not None else "0원"
            high = f"{self.max_price:,}원" if self.max_price is not None else "제한 없음"
            parts.append(f"가격 {low}~{high}")
        return " · ".join(parts) if parts else None

    def to_dict(self) -> dict:
        return {
            "airline": self.airline,
            "nonstop_only": self.nonstop_only,
            "max_stops": self.max_stops,
            "min_price": self.min_price,
            "max_price": self.max_price,
        }


def build_search_filters(
    *,
    airline: str | None = None,
    nonstop_only: bool = False,
    max_stops: int | None = None,
    min_price: int | None = None,
    max_price: int | None = None,
) -> SearchFilters:
    # Eager validation so bad CLI values fail fast even on empty results.
    apply_airline_filters(
        [],
        airline=airline,
        nonstop_only=nonstop_only,
        max_stops=max_stops,
        min_price=min_price,
        max_price=max_price,
    )
    return SearchFilters(
        airline=airline,
        nonstop_only=nonstop_only,
        max_stops=max_stops,
        min_price=min_price,
        max_price=max_price,
    )


class FlightSource(Protocol):
    """Structural interface for search backends (real adapter and test doubles)."""

    def search(
        self,
        *,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: str | None = ...,
        adults: int = ...,
        child: int = ...,
        infant: int = ...,
        cabin_class: str = ...,
        max_results: int = ...,
        background_mode: bool = ...,
        force_refresh: bool = ...,
        progress_callback: Any = ...,
    ) -> Any: ...
    def broad_date_range(
        self,
        *,
        origin: str,
        destination: str,
        dates: Any,
        return_offset: int = ...,
        adults: int = ...,
        child: int = ...,
        infant: int = ...,
        cabin_class: str = ...,
        progress_callback: Any = ...,
    ) -> Any: ...


class HybridStrategyEngine:
    """Search strategy pipeline shared by single, range, and matrix commands."""

    pipeline = ["broad_scan", "candidate_scoring", "detailed_refine", "diagnostic_fallback", "final_ranking"]

    def __init__(
        self,
        *,
        repo_path: str | None = None,
        limits: StrategyLimits | None = None,
        source_adapter: FlightSource | None = None,
    ):
        self.repo_path = repo_path
        self.limits = limits or StrategyLimits()
        self.source = source_adapter or FlightSourceAdapter(repo_path=repo_path)

    def _search_call(self, **kwargs) -> Any:
        try:
            return self.source.search(**kwargs)
        except TypeError as exc:
            message = str(exc)
            if any(key in message for key in ("child", "infant", "force_refresh")):
                for key in ("child", "infant", "force_refresh"):
                    kwargs.pop(key, None)
                return self.source.search(**kwargs)
            raise

    def _broad_call(self, **kwargs) -> Any:
        try:
            return self.source.broad_date_range(**kwargs)
        except TypeError as exc:
            message = str(exc)
            if any(key in message for key in ("child", "infant")):
                for key in ("child", "infant"):
                    kwargs.pop(key, None)
                return self.source.broad_date_range(**kwargs)
            raise

    def search_single(
        self,
        *,
        origin: str,
        destination: str,
        departure: str,
        return_date: str | None = None,
        scope: str = "auto",
        adults: int = 1,
        child: int = 0,
        infant: int = 0,
        cabin: str = "ECONOMY",
        max_results: int = 20,
        force_refresh: bool = False,
        airline: str | None = None,
        nonstop_only: bool = False,
        max_stops: int | None = None,
        min_price: int | None = None,
        max_price: int | None = None,
        time_pref: str | None = None,
        depart_after: str | None = None,
        return_after: str | None = None,
        exclude_early_before: str | None = None,
        prefer: str | None = None,
    ) -> dict:
        origin_code = normalize_airport(origin)
        destination_code = normalize_airport(destination)
        route_scope = resolve_route_scope(origin_code, [destination_code], scope)
        departure_date = pretty_date(parse_flexible_date(departure))
        parsed_return = pretty_date(parse_flexible_date(return_date)) if return_date else None
        verify_date_order(departure_date, parsed_return)
        filters = build_search_filters(
            airline=airline,
            nonstop_only=nonstop_only,
            max_stops=max_stops,
            min_price=min_price,
            max_price=max_price,
        )
        pref = build_time_preference(
            time_pref=time_pref,
            depart_after=depart_after,
            return_after=return_after,
            exclude_early_before=exclude_early_before,
            prefer=prefer,
        )
        logs: list[str] = []
        results = self._search_call(
            origin=origin_code,
            destination=destination_code,
            departure_date=departure_date,
            return_date=parsed_return,
            adults=adults,
            child=child,
            infant=infant,
            cabin_class=cabin,
            max_results=max_results,
            background_mode=False,
            force_refresh=force_refresh,
            progress_callback=lambda msg: logs.append(str(msg)),
        )
        normalized = [normalize_result_payload(item) for item in results]
        airline_rows = apply_airline_filters(
            normalized,
            airline=filters.airline,
            nonstop_only=filters.nonstop_only,
            max_stops=filters.max_stops,
            min_price=filters.min_price,
            max_price=filters.max_price,
        )
        filtered, ranked_by_pref = filter_and_rank_by_time_preference(airline_rows, pref)
        ranked = ranked_by_pref if pref.active() and ranked_by_pref else filtered
        query = {
            "origin": origin_code,
            "destination": destination_code,
            "departure": departure_date,
            "return_date": parsed_return,
            "scope": scope,
            "route_scope": route_scope,
            "adults": adults,
            "child": child,
            "infant": infant,
            "cabin": cabin,
            "force_refresh": force_refresh,
            "filters": filters.to_dict(),
            "filter_summary": filters.describe(),
            "time_preference": pref.describe(),
        }
        summary = build_single_summary(query, ranked, route_scope)
        return {
            "status": "success",
            "query": query,
            "summary": summary,
            "results": ranked,
            "strategy_metadata": {
                "pipeline": ["direct_search", "airline_filter", "time_filter", "final_ranking"],
                "broad_count": 0,
                "refined_count": len(normalized),
                "fallback_count": 0,
                "filter_active": filters.active(),
                "filtered_out_count": len(normalized) - len(airline_rows),
                "verified_results_required": pref.active(),
                "verified_result_count": len(ranked),
            },
            "diagnostics": None,
            "logs": logs,
        }

    def search_range(
        self,
        *,
        origin: str,
        destination: str,
        start_date: str | None = None,
        end_date: str | None = None,
        date_range: str | None = None,
        return_offset: int = 0,
        scope: str = "auto",
        adults: int = 1,
        child: int = 0,
        infant: int = 0,
        cabin: str = "ECONOMY",
        force_refresh: bool = False,
        airline: str | None = None,
        nonstop_only: bool = False,
        max_stops: int | None = None,
        min_price: int | None = None,
        max_price: int | None = None,
        time_pref: str | None = None,
        depart_after: str | None = None,
        return_after: str | None = None,
        exclude_early_before: str | None = None,
        prefer: str | None = None,
    ) -> dict:
        origin_code = normalize_airport(origin)
        destination_code = normalize_airport(destination)
        route_scope = resolve_route_scope(origin_code, [destination_code], scope)
        start_dt, end_dt = self._resolve_dates(start_date, end_date, date_range)
        dates = build_dates(start_dt, end_dt)
        verify_return_offset(return_offset)
        if len(dates) > self.limits.max_days:
            raise ValueError(f"date range must be {self.limits.max_days} days or less")
        filters = build_search_filters(
            airline=airline,
            nonstop_only=nonstop_only,
            max_stops=max_stops,
            min_price=min_price,
            max_price=max_price,
        )
        pref = build_time_preference(
            time_pref=time_pref,
            depart_after=depart_after,
            return_after=return_after,
            exclude_early_before=exclude_early_before,
            prefer=prefer,
        )
        logs: list[str] = []
        broad_rows = self._broad_rows_for_destination(
            origin_code, destination_code, dates, return_offset, adults, child, infant, cabin, logs
        )
        scored = self.score_candidates(broad_rows, dates=dates, destinations=[destination_code], time_pref=pref)
        self._apply_candidate_scores(broad_rows, scored, key_fields=("departure_date",))
        detailed_map, diagnostics, fallback_rows = self._refine_rows(
            origin_code, scored, pref, filters, adults, child, infant, cabin, force_refresh, logs,
            key_fields=("departure_date",),
        )
        final_rows = [detailed_map.get((row["departure_date"],), row) for row in broad_rows]
        if filters.active():
            final_rows = apply_airline_filters(
                final_rows,
                airline=filters.airline,
                nonstop_only=filters.nonstop_only,
                max_stops=filters.max_stops,
                min_price=filters.min_price,
                max_price=filters.max_price,
            )
        ranked = verified_priced_rows(final_rows, time_pref_active=pref.active())
        unverified = unverified_broad_rows(final_rows) if pref.active() else []
        metadata = self._strategy_metadata(broad_rows, detailed_map, fallback_rows, ranked, unverified, diagnostics, pref)
        metadata["filters"] = filters.to_dict()
        metadata["filter_active"] = filters.active()
        query = {
            "origin": origin_code,
            "destination": destination_code,
            "start_date": pretty_date(start_dt),
            "end_date": pretty_date(end_dt),
            "return_offset": return_offset,
            "scope": scope,
            "route_scope": route_scope,
            "adults": adults,
            "child": child,
            "infant": infant,
            "cabin": cabin,
            "force_refresh": force_refresh,
            "filters": filters.to_dict(),
            "filter_summary": filters.describe(),
            "time_preference": pref.describe(),
        }
        summary = build_range_summary(query, final_rows, ranked, metadata, diagnostics)
        return {
            "status": "success",
            "query": query,
            "summary": summary,
            "results": ranked,
            "strategy_metadata": metadata,
            "diagnostics": diagnostics,
            "logs": logs,
        }

    def search_matrix(
        self,
        *,
        origin: str,
        destinations: list[str],
        start_date: str | None = None,
        end_date: str | None = None,
        date_range: str | None = None,
        departure: str | None = None,
        return_date: str | None = None,
        return_offset: int = 0,
        scope: str = "auto",
        adults: int = 1,
        child: int = 0,
        infant: int = 0,
        cabin: str = "ECONOMY",
        force_refresh: bool = False,
        airline: str | None = None,
        nonstop_only: bool = False,
        max_stops: int | None = None,
        min_price: int | None = None,
        max_price: int | None = None,
        time_pref: str | None = None,
        depart_after: str | None = None,
        return_after: str | None = None,
        exclude_early_before: str | None = None,
        prefer: str | None = None,
    ) -> dict:
        origin_code = normalize_airport(origin)
        destination_codes = unique_codes([normalize_airport(item) for item in destinations])
        route_scope = resolve_route_scope(origin_code, destination_codes, scope)
        if departure and not start_date and not date_range:
            start_date = departure
            end_date = departure
        start_dt, end_dt = self._resolve_dates(start_date, end_date, date_range)
        dates = build_dates(start_dt, end_dt)
        if return_date and len(dates) == 1:
            parsed_return = pretty_date(parse_flexible_date(return_date))
            return_offset = (parse_flexible_date(parsed_return) - start_dt).days
        verify_return_offset(return_offset)
        combos = len(dates) * len(destination_codes)
        if combos > self.limits.max_combos:
            raise ValueError(f"검색 조합 수는 {self.limits.max_combos}개 이하로 제한됩니다.")
        filters = build_search_filters(
            airline=airline,
            nonstop_only=nonstop_only,
            max_stops=max_stops,
            min_price=min_price,
            max_price=max_price,
        )
        pref = build_time_preference(
            time_pref=time_pref,
            depart_after=depart_after,
            return_after=return_after,
            exclude_early_before=exclude_early_before,
            prefer=prefer,
        )
        logs: list[str] = []
        broad_rows: list[dict] = []
        for destination_code in destination_codes:
            broad_rows.extend(
                self._broad_rows_for_destination(
                    origin_code, destination_code, dates, return_offset, adults, child, infant, cabin, logs
                )
            )
        scored = self.score_candidates(broad_rows, dates=dates, destinations=destination_codes, time_pref=pref)
        self._apply_candidate_scores(broad_rows, scored, key_fields=("destination", "departure_date"))
        detailed_map, diagnostics, fallback_rows = self._refine_rows(
            origin_code, scored, pref, filters, adults, child, infant, cabin, force_refresh, logs,
            key_fields=("destination", "departure_date"),
        )
        final_rows = [detailed_map.get((row["destination"], row["departure_date"]), row) for row in broad_rows]
        if filters.active():
            final_rows = apply_airline_filters(
                final_rows,
                airline=filters.airline,
                nonstop_only=filters.nonstop_only,
                max_stops=filters.max_stops,
                min_price=filters.min_price,
                max_price=filters.max_price,
            )
        ranked = verified_priced_rows(final_rows, time_pref_active=pref.active())
        unverified = unverified_broad_rows(final_rows) if pref.active() else []
        metadata = self._strategy_metadata(broad_rows, detailed_map, fallback_rows, ranked, unverified, diagnostics, pref)
        metadata["filters"] = filters.to_dict()
        metadata["filter_active"] = filters.active()
        query = {
            "origin": origin_code,
            "destinations": destination_codes,
            "start_date": pretty_date(start_dt),
            "end_date": pretty_date(end_dt),
            "return_offset": return_offset,
            "scope": scope,
            "route_scope": route_scope,
            "adults": adults,
            "child": child,
            "infant": infant,
            "cabin": cabin,
            "force_refresh": force_refresh,
            "filters": filters.to_dict(),
            "filter_summary": filters.describe(),
            "time_preference": pref.describe(),
        }
        summary = build_matrix_summary(query, final_rows, ranked, metadata, diagnostics)
        return {
            "status": "success",
            "query": query,
            "summary": summary,
            "results": ranked,
            "strategy_metadata": metadata,
            "diagnostics": diagnostics,
            "logs": logs,
        }

    def score_candidates(
        self,
        rows: list[dict],
        *,
        dates: list[Any],
        destinations: list[str],
        time_pref: TimePreference,
    ) -> list[dict]:
        available = [dict(row) for row in rows if int(row.get("price", 0) or 0) > 0]
        available.sort(key=lambda row: (int(row.get("price", 0) or 0), row.get("destination") or "", row.get("departure_date") or ""))
        if not available:
            return []
        date_labels = [pretty_date(date) for date in dates]
        top_by_dest: set[tuple[str | None, str]] = set()
        for destination in destinations:
            first = next((row for row in available if row.get("destination") == destination or len(destinations) == 1), None)
            if first:
                top_by_dest.add((first.get("destination"), first["departure_date"]))
        anchors = {date_labels[0], date_labels[-1], date_labels[len(date_labels) // 2]}
        top_indexes = {date_labels.index(row["departure_date"]) for row in available[: min(4, len(available))] if row["departure_date"] in date_labels}
        scored: list[dict] = []
        for rank, row in enumerate(available, start=1):
            idx = date_labels.index(row["departure_date"]) if row["departure_date"] in date_labels else -1
            reasons = [f"price_rank:{rank}"]
            score = 1000.0 / rank
            if (row.get("destination"), row["departure_date"]) in top_by_dest:
                score += 80
                reasons.append("destination_coverage")
            if row["departure_date"] in anchors:
                score += 25
                reasons.append("range_anchor")
            if any(abs(idx - top_idx) == 1 for top_idx in top_indexes):
                score += 20
                reasons.append("neighbor_of_low_price")
            if time_pref.active():
                score += 30
                reasons.append("time_pref_requires_detail")
            score += float(row.get("confidence") or 0) * 10
            row["strategy_score"] = round(score, 3)
            row["strategy_reasons"] = reasons
            row["candidate_reason"] = reasons[0]
            scored.append(row)
        scored.sort(key=lambda row: (-float(row.get("strategy_score", 0)), int(row.get("price", 0) or 10**12)))
        return scored

    def _apply_candidate_scores(self, rows: list[dict], scored: list[dict], *, key_fields: tuple[str, ...]) -> None:
        scored_by_key = {tuple(row.get(field) for field in key_fields): row for row in scored}
        for row in rows:
            scored_row = scored_by_key.get(tuple(row.get(field) for field in key_fields))
            if not scored_row:
                continue
            row["strategy_score"] = scored_row.get("strategy_score", 0)
            row["strategy_reasons"] = scored_row.get("strategy_reasons", [])
            row["candidate_reason"] = scored_row.get("candidate_reason", "broad_rank")

    def _resolve_dates(self, start_date: str | None, end_date: str | None, date_range: str | None):
        if date_range:
            return parse_date_range_text(date_range)
        if start_date and end_date:
            return parse_flexible_date(start_date), parse_flexible_date(end_date)
        raise ValueError("start/end-date 또는 --date-range 중 하나를 제공해야 합니다.")

    def _broad_rows_for_destination(
        self,
        origin: str,
        destination: str,
        dates: list[Any],
        return_offset: int,
        adults: int,
        child: int,
        infant: int,
        cabin: str,
        logs: list[str],
    ) -> list[dict]:
        raw = self._broad_call(
            origin=origin,
            destination=destination,
            dates=[compact_date(date) for date in dates],
            return_offset=return_offset,
            adults=adults,
            child=child,
            infant=infant,
            cabin_class=cabin,
            progress_callback=lambda msg: logs.append(str(msg)),
        )
        rows = []
        for date in dates:
            key = compact_date(date)
            dep = pretty_date(date)
            ret = pretty_date(date + timedelta(days=return_offset)) if return_offset > 0 else None
            price, airline = raw.get(key, (0, "N/A"))
            rows.append(
                make_broad_row(
                    destination=destination,
                    destination_label=airport_label(destination),
                    departure_date=dep,
                    return_date=ret,
                    price=int(price or 0),
                    airline=airline or "",
                )
            )
        return rows

    def _refine_rows(
        self,
        origin: str,
        scored_rows: list[dict],
        time_pref: TimePreference,
        filters: SearchFilters,
        adults: int,
        child: int,
        infant: int,
        cabin: str,
        force_refresh: bool,
        logs: list[str],
        *,
        key_fields: tuple[str, ...],
    ) -> tuple[dict[tuple, dict], dict | None, list[dict]]:
        selected = scored_rows[: self.limits.refine_budget]
        detailed: dict[tuple, dict] = {}
        for row in selected:
            key = tuple(row[field] for field in key_fields)
            detailed[key] = self._refine_one(
                origin, row, time_pref, filters, adults, child, infant, cabin, force_refresh, logs, stage="refine"
            )
        diagnostics = build_refine_diagnostics(
            scored_rows,
            detailed.values(),
            key_fn=lambda row: tuple(row[field] for field in key_fields),
            label_fn=lambda row: " ".join(str(row.get(field, "")) for field in key_fields),
        )
        fallback_rows: list[dict] = []
        fallback_plan = choose_fallback_plan(
            diagnostics,
            minimum_target=max(2, math.ceil(len(scored_rows) * 0.2)),
            hard_cap=self.limits.fallback_budget,
            pad=2,
        )
        if fallback_plan["triggered"]:
            attempted = set(detailed)
            for row in scored_rows:
                key = tuple(row[field] for field in key_fields)
                if key in attempted:
                    continue
                fallback_rows.append(row)
                if len(fallback_rows) >= min(self.limits.fallback_budget, int(fallback_plan.get("limit") or 0)):
                    break
            for row in fallback_rows:
                key = tuple(row[field] for field in key_fields)
                detailed[key] = self._refine_one(
                    origin, row, time_pref, filters, adults, child, infant, cabin, force_refresh, logs, stage="fallback"
                )
            diagnostics = build_refine_diagnostics(
                scored_rows,
                detailed.values(),
                key_fn=lambda row: tuple(row[field] for field in key_fields),
                label_fn=lambda row: " ".join(str(row.get(field, "")) for field in key_fields),
            )
        diagnostics["fallback_decision"] = fallback_plan
        diagnostics["fallback_refined_count"] = len(fallback_rows)
        return detailed, diagnostics, fallback_rows

    def _refine_one(
        self,
        origin: str,
        row: dict,
        time_pref: TimePreference,
        filters: SearchFilters,
        adults: int,
        child: int,
        infant: int,
        cabin: str,
        force_refresh: bool,
        logs: list[str],
        *,
        stage: str,
    ) -> dict:
        destination = str(row.get("destination") or "")
        results = self._search_call(
            origin=origin,
            destination=destination,
            departure_date=row["departure_date"],
            return_date=row.get("return_date"),
            adults=adults,
            child=child,
            infant=infant,
            cabin_class=cabin,
            max_results=20,
            background_mode=False,
            force_refresh=force_refresh,
            progress_callback=lambda msg: logs.append(f"[{stage} {destination} {row['departure_date']}] {msg}"),
        )
        raw_results = [normalize_result_payload(item) for item in results]
        airline_rows = apply_airline_filters(
            raw_results,
            airline=filters.airline,
            nonstop_only=filters.nonstop_only,
            max_stops=filters.max_stops,
            min_price=filters.min_price,
            max_price=filters.max_price,
        )
        if filters.active() and raw_results and not airline_rows:
            reason = "airline_filter_no_match"
            detail = {
                "raw_option_count": len(raw_results),
                "priced_option_count": sum(1 for item in raw_results if int(item.get("price", 0) or 0) > 0),
                "departure_time_count": sum(1 for item in raw_results if str(item.get("departure_time") or "").strip()),
                "return_time_count": sum(1 for item in raw_results if str(item.get("return_departure_time") or "").strip()),
                "has_return_time_constraint": bool(
                    row.get("return_date") and (time_pref.return_min is not None or time_pref.return_max is not None)
                ),
                "hint": "항공사/경유/가격 조건 미충족",
            }
            cheapest = None
            filtered: list[dict] = []
            candidate_pool: list[dict] = []
        else:
            filtered, ranked = filter_and_rank_by_time_preference(airline_rows, time_pref)
            candidate_pool = ranked if time_pref.active() else priced_rows(airline_rows)
            cheapest = candidate_pool[0] if candidate_pool else None
            reason, detail = self._diagnose_refine_failure(
                airline_rows,
                filtered if time_pref.active() else candidate_pool,
                int(row.get("price", 0) or 0),
                bool(row.get("return_date") and (time_pref.return_min is not None or time_pref.return_max is not None)),
            )
        payload = normalize_result_payload(cheapest)
        payload.update(
            {
                "destination": destination,
                "destination_label": row.get("destination_label"),
                "departure_date": row.get("departure_date"),
                "return_date": row.get("return_date"),
                "search_stage": stage,
                "time_pref_match": bool(cheapest),
                "raw_option_count": len(raw_results),
                "priced_option_count": detail.get("priced_option_count", 0),
                "departure_time_count": detail.get("departure_time_count", 0),
                "return_time_count": detail.get("return_time_count", 0),
                "has_return_time_constraint": detail.get("has_return_time_constraint", False),
                "time_pref_valid_count": len(filtered if time_pref.active() else (candidate_pool if cheapest is not None else [])),
                "broad_price": row.get("price", 0),
                "diagnostic_reason": reason,
                "diagnostic_detail": detail,
                "strategy_score": row.get("strategy_score", 0),
                "strategy_reasons": row.get("strategy_reasons", []),
            }
        )
        return payload

    def _diagnose_refine_failure(self, raw_results: list[dict], filtered: list[dict], broad_price: int, has_return_time_constraint: bool):
        raw_count = len(raw_results)
        priced_count = sum(1 for item in raw_results if int(item.get("price", 0) or 0) > 0)
        depart_count = sum(1 for item in raw_results if str(item.get("departure_time") or "").strip())
        return_count = sum(1 for item in raw_results if str(item.get("return_departure_time") or "").strip())
        detail = {
            "raw_option_count": raw_count,
            "priced_option_count": priced_count,
            "departure_time_count": depart_count,
            "return_time_count": return_count,
            "has_return_time_constraint": bool(has_return_time_constraint),
        }
        if raw_count > 0:
            detail["price_coverage_ratio"] = round(priced_count / raw_count, 3)
            detail["departure_time_coverage_ratio"] = round(depart_count / raw_count, 3)
            detail["return_time_coverage_ratio"] = round(return_count / raw_count, 3)
        if filtered:
            return "detailed_match_with_time_pref", {**detail, "hint": "시간 조건 일치"}
        if not raw_results:
            return ("detail_empty_after_broad_hit" if broad_price > 0 else "detail_empty_no_broad_signal"), {**detail, "hint": "상세 빈결과"}
        if priced_count <= 0:
            return "detail_missing_price_data", {**detail, "hint": "가격 정보 없음"}
        if 0 < priced_count < raw_count:
            return "detail_sparse_price_data", {**detail, "hint": "가격 정보 일부 누락"}
        if depart_count <= 0:
            return "detail_missing_departure_times", {**detail, "hint": "출발 시간 정보 부족"}
        if has_return_time_constraint and return_count <= 0:
            return "detail_missing_return_times", {**detail, "hint": "복귀 시간 정보 부족"}
        if broad_price > 0:
            return "broad_candidate_time_rejected", {**detail, "hint": "시간 조건 미충족"}
        return "detailed_no_usable_time_filter_match", {**detail, "hint": "usable match 없음"}

    def _strategy_metadata(
        self,
        broad_rows: list[dict],
        detailed_map: dict[tuple, dict],
        fallback_rows: list[dict],
        ranked: list[dict],
        unverified: list[dict],
        diagnostics: dict | None,
        pref: TimePreference,
    ) -> dict:
        return {
            "pipeline": self.pipeline,
            "broad_count": len(broad_rows),
            "broad_available": len([row for row in broad_rows if int(row.get("price", 0) or 0) > 0]),
            "refined_count": len(detailed_map),
            "fallback_count": len(fallback_rows),
            "fallback_triggered": bool((diagnostics or {}).get("fallback_decision", {}).get("triggered")),
            "candidate_scores": [
                {
                    "destination": row.get("destination"),
                    "departure_date": row.get("departure_date"),
                    "price": row.get("price"),
                    "score": row.get("strategy_score"),
                    "reasons": row.get("strategy_reasons", []),
                }
                for row in sorted(broad_rows, key=lambda item: -float(item.get("strategy_score", 0) or 0))[:10]
            ],
            "verified_results_required": pref.active(),
            "verified_result_count": len(ranked),
            "unverified_broad_result_count": len(unverified),
            "unverified_candidates": unverified[:7],
            "limits": {
                "max_days": self.limits.max_days,
                "max_combos": self.limits.max_combos,
                "refine_budget": self.limits.refine_budget,
                "fallback_budget": self.limits.fallback_budget,
            },
        }
