---
name: korea-flights
description: Search, compare, optimize, and monitor Korean domestic and international flights with a package-backed OpenClaw skill. Use for 항공권 최저가 조회, 김포-제주/인천-나리타 검색, 편도/왕복, 날짜 범위 최저가, 목적지+날짜 매트릭스, 시간대 선호, 직항만/LCC/FSC 필터, 경유/가격대 필터, 운임 브리핑, and 목표가 이하 가격 감시.
---

# Korea Flights

This is the OpenClaw AgentSkill entry for the `korea-flights` package. The repository path may still be installed as `openclaw-korea-domestic-flights` for legacy compatibility, but new automation should use the `korea-flights` CLI.

## Runtime Model

- Package import: `korea_flights`
- Console command: `korea-flights`
- Source adapter: local `Scraping-flight-information` clone
- Main engine: `korea_flights.strategy.HybridStrategyEngine`
- Airline filters: `korea_flights.airlines` (LCC/FSC 분류, 직항만, 경유수, 가격대 — 원본 GUI 필터 패널 이식)
- Search pipeline: `broad_scan -> candidate_scoring -> detailed_refine -> diagnostic_fallback -> final_ranking`
- Packaging contract: `pyproject.toml` wheel/sdist, no PyInstaller `.spec` file

The package does not vendor the scraping runtime. It locates the source repo by `--repo-path`, `KDF_SOURCE_REPO`, `SCRAPING_FLIGHT_INFORMATION_REPO`, or nearby `tmp/Scraping-flight-information` / `Scraping-flight-information` folders.

## Preferred Commands

Check wiring first:

```bash
korea-flights doctor --repo-path D:\twbeatles-repos\Scraping-flight-information
```

Single route:

```bash
korea-flights search --origin 김포 --destination 제주 --departure 내일 --human
korea-flights search --origin ICN --destination NRT --departure 내일 --scope international --json
```

Single route with filters ported from the source repo (직항만, LCC, 가격 상한, 소아 동반, 강제재조회):

```bash
korea-flights search --origin ICN --destination CTS --departure 내일 --nonstop-only --human
korea-flights search --origin ICN --destination KIX --departure 내일 --airline LCC --max-price 200000 --human
korea-flights search --origin ICN --destination TPE --departure 2026-09-10 --return-date 2026-09-13 --child 1 --force-refresh --human
```

Date range:

```bash
korea-flights range --origin ICN --destination KIX --date-range "다음주말" --scope international --human
korea-flights range --origin 김포 --destination 제주 --start-date 2026-06-01 --end-date 2026-06-15 --return-offset 2 --time-pref "복귀 18시 이후" --refine-budget 10 --fallback-budget 6 --json
```

Destination/date matrix:

```bash
korea-flights matrix --origin ICN --destinations NRT,KIX,FUK --date-range "내일부터 7일" --scope international --human
korea-flights matrix --origin 김포 --destinations 제주,부산,여수 --date-range "다음주말" --return-offset 2 --human
```

Price alerts:

```bash
korea-flights alert add --origin 김포 --destination 제주 --date-range "다음주말" --return-offset 2 --target-price 150000 --time-pref "복귀 18시 이후"
korea-flights alert add --origin ICN --destination CTS --departure 내일 --target-price 200000 --nonstop-only --airline LCC
korea-flights alert list
korea-flights alert check --no-dedupe
```

Optional live smoke:

```bash
korea-flights live-smoke --repo-path D:\twbeatles-repos\Scraping-flight-information --json
```

## JSON Contract

Search commands return:

- `status`
- `query` (includes `child`, `infant`, `force_refresh`, `filters`, `filter_summary`)
- `summary`
- `results`
- `strategy_metadata` (includes `filter_active`, `filtered_out_count`, `filters` for range/matrix)
- `diagnostics`
- `logs`

Preserve upstream result fields when present: `duration`, `return_duration`, `stops`, `return_stops`, `flight_number`, `benefit_price`, `benefit_label`, `source`, `extraction_source`, `confidence`.
Every normalized result also carries `airline_category` (`LCC`/`FSC`/`OTHER`) and `effective_price` (min of price/benefit_price, mirroring upstream `effective_flight_price`).

## Strategy Notes

- Default date range cap: 45 days (`--max-days`)
- Default matrix cap: 120 combos (`--max-combos`)
- Detailed candidate budget: `--refine-budget`
- Diagnostic fallback budget: `--fallback-budget`
- Airline/stop/price filters apply to flight options first, then the time preference. A refine round with options but zero filter matches reports `airline_filter_no_match` in diagnostics.
- If a time preference is active, final recommendations only use detailed results that pass the time condition. Broad-only rows are exposed as `unverified_candidates`.

## Search Keywords

Full keyword dictionary: `references/search-keywords.md` (airport aliases KR/EN, date keywords, time buckets, filter keywords, natural-language examples).

- Airports: `김포`/`GMP`, `삿포로`/`CTS`, `타이베이`/`TPE`, `도쿄`/`TYO` 등. Unknown 3-letter codes pass through as-is.
- Dates (`Asia/Seoul`): `오늘`, `내일`, `모레`, `다음주말`, `내일부터 7일`, `2026-08-25`.
- Times: `저녁`, `출발 10시 이후`, `복귀 18시 이후`, `늦은 시간 선호` (+ `--depart-after`, `--return-after`, `--prefer`).
- Filters: `--airline LCC|FSC`, `--nonstop-only`, `--max-stops`, `--min-price`/`--max-price` (effective-price basis), `--child`/`--infant`, `--force-refresh`.

## Legacy Compatibility

Existing scripts under `scripts/` remain as thin forwarders. Prefer the package CLI for new work:

- `scripts/search_flights.py` -> `korea-flights search`
- `scripts/search_date_range.py` -> `korea-flights range`
- `scripts/search_destination_date_matrix.py` -> `korea-flights matrix`
- `scripts/search_multi_destination.py` -> `korea-flights matrix`
- `scripts/chat_search.py` -> legacy dispatcher into package CLI
- `scripts/price_alerts.py` -> `korea-flights alert`

## Validation

Use these local gates after changes:

```bash
python -m compileall src scripts tests
python -m pytest -q
python scripts/regression_smoke_check.py
python scripts/hybrid_smoke_check.py
python -m build
```

The wheel includes `SKILL.md` and `references/*.md` as data files so installed skill metadata stays aligned with the repository docs.
