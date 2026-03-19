# korea-domestic-flights-skill

대한민국 **국내선 항공권 검색 전용** OpenClaw 스킬입니다.

Playwright 기반 로컬 항공권 검색 저장소([`Scraping-flight-information`](https://github.com/twbeatles/Scraping-flight-information))의 검색 로직을 얇게 감싸서, **김포-제주 / 부산-제주 / 청주-제주 / 광주-제주** 같은 대한민국 국내선 노선의 편도·왕복·날짜범위 최저가와 다중 목적지 비교를 빠르게 조회할 수 있게 만든 스킬입니다.

> 핵심 원칙: 이 스킬은 **대한민국 국내선 전용**입니다. 국제선 검색용으로 설계하지 않았습니다.

---

## 지원 범위

현재 버전에서 지원하는 기능:

- 대한민국 **국내선 편도 검색**
- 대한민국 **국내선 왕복 검색**
- 대한민국 **국내선 날짜 범위 최저가 탐색**
- 대한민국 **국내선 다중 목적지 비교**
- 최저가 및 상위 옵션 요약
- JSON 출력
- 사람이 읽기 좋은 요약 출력 (`--human`)
- **한글 공항명 입력 지원** (`김포`, `제주`, `부산` 등)
- **간단한 자연어 날짜 입력 지원** (`오늘`, `내일`, `모레`)

현재 버전에서 **아직 미지원**:

- 국제선 검색
- 가격 알림
- 예약 자동화

---

### 필요 환경

- Python 3.10+
- Playwright 사용 가능 환경
- 기존 항공권 검색 저장소의 의존성 설치 완료
- Chromium/Chrome/Edge 중 하나 사용 가능

예시:

```bash
pip install -r requirements.txt
playwright install chromium
```

---

## 저장소 구조

```text
korea-domestic-flights-skill/
├── README.md
├── SKILL.md
├── references/
│   └── domestic-airports.md
└── scripts/
    ├── common_cli.py
    ├── search_domestic.py
    ├── search_date_range.py
    └── search_multi_destination.py
```

---

## 사용 방법

### 1) 편도 검색

코드 입력:

```bash
python scripts/search_domestic.py --origin GMP --destination CJU --departure 2026-03-25 --human
```

한글 입력:

```bash
python scripts/search_domestic.py --origin 김포 --destination 제주 --departure 내일 --human
```

### 2) 왕복 검색

```bash
python scripts/search_domestic.py --origin 김포 --destination 제주 --departure 2026-03-25 --return-date 2026-03-28 --human
```

### 3) 날짜 범위 최저가 검색

```bash
python scripts/search_date_range.py --origin 김포 --destination 제주 --start-date 내일 --end-date 2026-03-22 --human
```

### 4) 날짜 범위 + 왕복 오프셋 검색

예: 출발일 기준 **2일 뒤 귀국**하는 왕복 최저가 날짜를 찾고 싶을 때

```bash
python scripts/search_date_range.py --origin 김포 --destination 제주 --start-date 2026-03-25 --end-date 2026-03-30 --return-offset 2 --human
```

### 5) 다중 목적지 비교

```bash
python scripts/search_multi_destination.py --origin 김포 --destinations 제주,부산,여수 --departure 내일 --human
```

왕복 비교:

```bash
python scripts/search_multi_destination.py --origin 김포 --destinations 제주,부산 --departure 2026-03-25 --return-date 2026-03-28 --human
```

---

## 자연어 친화 입력

### 공항명 입력 예시

- `김포` → `GMP`
- `제주`, `제주도` → `CJU`
- `부산`, `김해` → `PUS`
- `청주` → `CJJ`
- `광주` → `KWJ`
- `여수` → `RSU`

### 날짜 입력 예시

- `오늘`
- `내일`
- `모레`
- `2026-03-25`
- `20260325`
- `2026/03/25`

---

## 출력 예시

### 편도 `--human`

```text
김포(GMP) → 제주(CJU) 편도 최저가 104,500원
조건: 성인 1명 · 이코노미 · 결과 3건
일정: 2026-03-20
최저가: 에어서울 · 104,500원 · 14:30→15:45
상위 옵션:
1. 에어서울 · 104,500원 · 14:30→15:45
2. 아시아나 · 107,600원 · 14:45→16:00
3. 티웨이 · 108,600원 · 13:45→15:00
```

### 날짜 범위 `--human`

```text
김포(GMP) → 제주(CJU) 날짜범위 최저가 42,500원
범위: 2026-03-20 ~ 2026-03-22
조건: 성인 1명 · 이코노미
최저가 날짜: 2026-03-22 · 42,500원 · 에어서울
상위 날짜:
1. 2026-03-22 · 42,500원 · 에어서울
2. 2026-03-21 · 47,600원 · 아시아나
3. 2026-03-20 · 104,500원 · 에어서울
```

### 다중 목적지 비교 `--human`

```text
김포(GMP) 출발 다중 목적지 최저가 33,500원
조건: 출발 김포(GMP) · 출발일 2026-03-25 · 성인 1명 · 이코노미
최적 목적지: 제주(CJU) · 33,500원 · 에어서울 · 18:40→19:55
목적지 비교:
1. 제주(CJU) · 33,500원 · 에어서울 · 18:40→19:55
2. 부산(PUS) · 50,500원 · 진에어 · 19:10→20:15
```

---

## 대한민국 국내선 전용 범위

이 스킬은 아래 같은 질의에 맞춰 설계했습니다.

- `김포에서 제주 가는 내일 최저가 찾아줘`
- `부산 제주 왕복 항공권 요약해줘`
- `청주 제주 3일 범위로 최저가 비교해줘`
- `김포 제주 왕복 2박 기준 날짜별 최저가 찾아줘`
- `김포 출발로 제주, 부산, 여수 중 어디가 제일 싼지 비교해줘`

반대로 아래는 현재 범위 밖입니다.

- `인천-도쿄 국제선 검색`
- `해외 다구간 여정 검색`
- `항공권 자동 예약`
- `호텔/렌터카 결합 검색`

---

## 한계와 주의점

- 검색 대상 사이트의 DOM 구조가 바뀌면 유지보수가 필요할 수 있습니다.
- Playwright 브라우저 초기화가 실패하면 브라우저 설치 상태를 점검해야 합니다.
- 대상 사이트의 정책, 차단, 로딩 상태에 따라 결과가 달라질 수 있습니다.
- 이 저장소는 **대한민국 국내선 검색에만 초점을 맞춘 스킬**입니다.

---

## 개발 메모

현재 래퍼는 다음 엔트리 포인트를 재사용합니다.

- `scraping.searcher.FlightSearcher`
- `scraping.parallel.ParallelSearcher`

즉, GUI 중심 원본 프로젝트 전체를 옮긴 것이 아니라, **검색 로직만 OpenClaw 스킬 형태로 노출**한 구조입니다.

---

## 라이선스 / 출처

이 저장소는 기존 프로젝트 `Scraping-flight-information`을 기반으로 스킬화한 파생 작업입니다.
