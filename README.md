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
- 대한민국 **국내선 목적지+날짜 범위 결합 검색**
- 최저가 및 상위 옵션 요약
- **추천 문장 / 가격 차이 브리핑**
- JSON 출력
- 사람이 읽기 좋은 요약 출력 (`--human`)
- **한글 공항명 입력 지원** (`김포`, `제주`, `부산` 등)
- **간단한 자연어 날짜 입력 지원** (`오늘`, `내일`, `모레`, `글피`, `이번주말`, `다음주말`)
- **채팅 친화 래퍼** 제공 (`chat_search.py`)

현재 버전에서 **아직 미지원**:

- 국제선 검색
- 가격 알림
- 예약 자동화

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
    ├── chat_search.py
    ├── search_domestic.py
    ├── search_date_range.py
    ├── search_multi_destination.py
    └── search_destination_date_matrix.py
```

---

## 핵심 스크립트

### `chat_search.py`
가장 추천하는 진입점.
채팅처럼 간단히 넣어도 적절한 검색기로 자동 분기합니다.

예시:

```bash
python scripts/chat_search.py --origin 김포 --destination 제주 --when 내일
python scripts/chat_search.py --origin 김포 --destinations 제주,부산 --when 다음주말
python scripts/chat_search.py --origin 김포 --destinations 제주,부산 --when "내일부터 2일" --return-offset 1
```

### `search_domestic.py`
단일 목적지 편도/왕복 검색

### `search_date_range.py`
단일 목적지 날짜 범위 최저가 검색

### `search_multi_destination.py`
여러 목적지 한 날짜 비교

### `search_destination_date_matrix.py`
여러 목적지 + 날짜 범위를 동시에 훑어 전체 최적 조합 찾기

---

## 사용 예시

### 1) 채팅 친화 검색

```bash
python scripts/chat_search.py --origin 김포 --destination 제주 --when 내일
```

### 2) 날짜 범위 검색

```bash
python scripts/chat_search.py --origin 김포 --destination 제주 --when "내일부터 3일"
```

### 3) 다중 목적지 비교

```bash
python scripts/chat_search.py --origin 김포 --destinations 제주,부산,여수 --when 내일
```

### 4) 목적지 + 날짜 범위 결합 검색

```bash
python scripts/chat_search.py --origin 김포 --destinations 제주,부산,여수 --when 다음주말
```

### 5) 왕복형 날짜 범위 비교

```bash
python scripts/chat_search.py --origin 김포 --destinations 제주,부산 --when "내일부터 2일" --return-offset 1
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
- `글피`
- `이번주말`
- `다음주말`
- `다음주 금요일`
- `이번주 화요일`
- `내일부터 3일`
- `2026-03-25`
- `20260325`
- `3/25`
- `3월 25일`

---

## 실제 출력 예시

### 실제 질의 스타일 테스트

```bash
python scripts/chat_search.py --origin 김포 --destinations 제주,부산,여수 --when 다음주말
```

예시 출력:

```text
김포(GMP) 출발 최적 조합은 제주(CJU) 2026-03-29 48,000원
범위: 2026-03-28 ~ 2026-03-29
조건: 출발 김포(GMP) · 목적지 3곳 · 성인 1명 · 이코노미
최적 조합: 제주(CJU) · 2026-03-29 · 48,000원 · 제주항공
추천: 이번 조건에서는 제주(CJU) / 2026-03-29이(가) 가장 유리합니다. 2위보다 1,000원 저렴해 가성비가 좋습니다.
목적지별 베스트:
1. 제주(CJU) · 2026-03-29 · 48,000원 · 제주항공
2. 부산(PUS) · 2026-03-28 · 49,000원 · 제주항공
3. 여수(RSU) · 결과 없음
```

---

## 대한민국 국내선 전용 범위

이 스킬은 아래 같은 질의에 맞춰 설계했습니다.

- `김포에서 제주 가는 내일 최저가 찾아줘`
- `부산 제주 왕복 항공권 요약해줘`
- `청주 제주 3일 범위로 최저가 비교해줘`
- `김포 제주 왕복 2박 기준 날짜별 최저가 찾아줘`
- `김포 출발로 제주, 부산, 여수 중 어디가 제일 싼지 비교해줘`
- `김포 출발 제주/부산/여수 다음주말 비교해줘`

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

## 라이선스 / 출처

이 저장소는 태완의 기존 프로젝트 `Scraping-flight-information`을 기반으로 스킬화한 파생 작업입니다.
