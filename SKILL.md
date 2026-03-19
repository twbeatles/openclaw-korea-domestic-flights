---
name: korea-domestic-flights
description: Search 대한민국 domestic flights using a Playwright-backed local scraper. Use when the user asks for 한국 국내선 항공권 검색, 김포-제주/부산-제주 같은 국내 노선 최저가 확인, 편도/왕복 조회, 날짜별 최저가 비교, 여러 국내 목적지 비교, 국내선 운임 요약, or route/date fare checks. Accept common Korean airport names like 김포, 제주, 부산, 청주 as inputs. Prefer this skill for Korean domestic airfare tasks; do not use it for international flights.
---

# Korea Domestic Flights

Use this skill for **대한민국 국내선 전용 항공권 검색**.

Current scope:
- 국내선 편도 검색
- 국내선 왕복 검색
- 날짜 범위 최저가 탐색
- 다중 목적지 비교
- JSON 출력
- 사람이 읽기 좋은 요약 출력
- 한글 공항명 입력 지원
- `오늘/내일/모레` 같은 간단한 날짜 표현 지원

Do not use it for 국제선.

## Source dependency

This skill wraps the local project clone at:

- `tmp/Scraping-flight-information`

Main reused entry points:
- `scraping.searcher.FlightSearcher`
- `scraping.parallel.ParallelSearcher`

If the clone or its dependencies are missing, searches will fail.

## Scripts

### 1) Single-route domestic search

```bash
python skills/korea-domestic-flights/scripts/search_domestic.py --origin 김포 --destination 제주 --departure 내일 --human
```

Round trip:

```bash
python skills/korea-domestic-flights/scripts/search_domestic.py --origin GMP --destination CJU --departure 2026-03-25 --return-date 2026-03-28 --human
```

### 2) Date-range cheapest-day search

```bash
python skills/korea-domestic-flights/scripts/search_date_range.py --origin 김포 --destination 제주 --start-date 내일 --end-date 2026-03-30 --human
```

Round-trip-style date scan with fixed return offset:

```bash
python skills/korea-domestic-flights/scripts/search_date_range.py --origin 김포 --destination 제주 --start-date 2026-03-25 --end-date 2026-03-30 --return-offset 3 --human
```

### 3) Multi-destination comparison

```bash
python skills/korea-domestic-flights/scripts/search_multi_destination.py --origin 김포 --destinations 제주,부산,여수 --departure 내일 --human
```

Round trip comparison:

```bash
python skills/korea-domestic-flights/scripts/search_multi_destination.py --origin GMP --destinations CJU,PUS,RSU --departure 2026-03-25 --return-date 2026-03-28 --human
```

## Parameters

`search_domestic.py`
- `--origin`: 출발 공항 코드 또는 한글 공항명
- `--destination`: 도착 공항 코드 또는 한글 공항명
- `--departure`: 출발일 (`YYYY-MM-DD`, `YYYYMMDD`, `내일`, `모레` 등)
- `--return-date`: 귀국일 (선택)
- `--adults`: 성인 수, 기본값 `1`
- `--cabin`: `ECONOMY|BUSINESS|FIRST`
- `--max-results`: 최대 결과 수
- `--human`: 짧은 한국어 요약 출력

`search_date_range.py`
- `--origin`: 출발 공항 코드 또는 한글 공항명
- `--destination`: 도착 공항 코드 또는 한글 공항명
- `--start-date`: 범위 시작일
- `--end-date`: 범위 종료일
- `--return-offset`: 왕복 탐색용 귀국 오프셋 일수
- `--adults`: 성인 수
- `--cabin`: `ECONOMY|BUSINESS|FIRST`
- `--human`: 짧은 한국어 요약 출력

`search_multi_destination.py`
- `--origin`: 출발 공항 코드 또는 한글 공항명
- `--destinations`: 쉼표로 구분한 여러 목적지 (코드 또는 한글)
- `--departure`: 출발일
- `--return-date`: 귀국일 (선택)
- `--adults`: 성인 수
- `--cabin`: `ECONOMY|BUSINESS|FIRST`
- `--human`: 짧은 한국어 요약 출력

## Airport codes

For common Korean airport codes and names, read:
- `references/domestic-airports.md`

## Operational notes

- This skill depends on a working Playwright browser environment.
- If browser init fails, install or repair Chromium/Chrome/Edge in the source repo environment.
- The provider site DOM may change; if results suddenly disappear, the upstream scraper may need maintenance.
- For stable chat use, prefer `--human` summaries unless structured JSON is explicitly needed.
- Prefer domestic routes only; if the user asks for ICN-NRT or any overseas route, do not use this skill.
