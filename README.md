# korea-domestic-flights-skill

대한민국 **국내선 전용 항공권 검색 / 비교 / 가격 감시** OpenClaw 스킬입니다.

이 저장소는 Playwright 기반 로컬 검색 엔진 [`twbeatles/Scraping-flight-information`](https://github.com/twbeatles/Scraping-flight-information)을 OpenClaw에서 바로 쓰기 쉽게 감싼 스킬 패키지입니다. 자연어 날짜(`오늘`, `내일`, `이번주말`, `내일부터 3일`), 한글 공항명(`김포`, `제주`, `부산`)을 받아 **편도/왕복 검색**, **날짜 범위 최저가 탐색**, **여러 목적지 비교**, **목표가 가격 감시**까지 처리합니다.

> 이 스킬은 **대한민국 국내선 전용**입니다. 국제선 검색에는 맞지 않습니다.

---

## What this skill is good at

이 스킬이 특히 강한 작업은 아래입니다.

- `김포-제주 내일 최저가 보여줘`
- `이번 주말 김포 출발 국내선 어디가 제일 싼지 비교해줘`
- `부산/제주/여수 중 다음주말 최적 조합 찾아줘`
- `내일부터 3일 안에 갈 수 있는 제주 왕복 중 제일 싼 거 찾아줘`
- `7만원 이하로 내려가면 알려줘`
- `너무 이른 비행 빼고 저녁 출발 위주로 추천해줘`

특히 다음 요소가 실사용에서 편합니다.

- 한국어 공항명 입력 지원
- 자연어 날짜/날짜 범위 해석
- 시간대 선호 반영(오전/오후/저녁, 출발 N시 이후 등)
- 채팅 친화 요약 출력
- 반복 조회용 가격 감시 규칙 저장
- JSON 출력 기반 상위 자동화 연동

---

## Current feature set

현재 버전 기준 지원 범위:

- 국내선 편도 검색
- 국내선 왕복 검색
- 날짜 범위 최저가 탐색
- 여러 목적지 비교
- 목적지 × 날짜 범위 최적 조합 검색
- 자연어 날짜 해석
- 한글 공항명 해석
- 시간 선호/제외 조건 반영
- 채팅형 브리핑 래퍼 (`scripts/chat_search.py`)
- 가격 감시 규칙 저장 / 목록 / 삭제 / 점검
- 중복 알림 억제(dedupe)
- 다중 목적지 감시
- 알림 메시지 템플릿 커스터마이즈
- JSON 기반 브리핑/cron 연동
- Windows 작업 스케줄러 등록 보조 스크립트

---

## Repository layout

```text
korea-domestic-flights-skill/
├── README.md
├── SKILL.md
├── references/
│   ├── domestic-airports.md
│   └── price-alerts-schema.md
└── scripts/
    ├── chat_search.py
    ├── common_cli.py
    ├── price_alerts.py
    ├── register_price_alerts_task.ps1
    ├── search_date_range.py
    ├── search_destination_date_matrix.py
    ├── search_domestic.py
    └── search_multi_destination.py
```

---

## Environment / requirements

실사용 전 아래 조건을 확인하는 편이 좋습니다.

- OpenClaw 환경 또는 Python CLI 실행 환경
- Playwright 기반 upstream 검색 로직이 동작 가능한 로컬 환경
- 국내선 항공권 검색에 필요한 브라우저 자동화 의존성 설치
- 반복 감시 시 JSON 파일을 저장할 수 있는 로컬 파일 시스템
- Windows 자동 스케줄링을 쓸 경우 PowerShell + 작업 스케줄러 접근 권한

이 저장소 자체는 **OpenClaw 스킬 래퍼**이고, 실제 항공권 탐색은 homepage로 연결된 upstream 저장소의 로직을 재사용합니다.

---

## Recommended usage flow

가장 추천하는 흐름은 아래 순서입니다.

1. 먼저 `chat_search.py`로 사람이 읽기 쉬운 요약을 본다.
2. 조건이 넓으면 여러 목적지/날짜 범위를 한 번에 비교한다.
3. 시간 제약이 있으면 `--time-pref`, `--depart-after`, `--return-after` 등을 추가한다.
4. 반복 확인이 필요하면 `price_alerts.py add`로 규칙을 저장한다.
5. 주기 점검은 `price_alerts.py check` 또는 작업 스케줄러/cron에서 돌린다.
6. 상위 레이어에서 후처리하려면 `--json` 출력으로 연결한다.

---

## Quick start

### 1) 단일 목적지 채팅형 검색

```bash
python scripts/chat_search.py --origin 김포 --destination 제주 --when 내일
```

### 2) 여러 목적지 비교

```bash
python scripts/chat_search.py --origin 김포 --destinations 제주,부산,여수 --when 다음주말
```

### 3) 날짜 범위 + 왕복 오프셋 검색

```bash
python scripts/chat_search.py --origin 김포 --destinations 제주,부산 --when "내일부터 2일" --return-offset 1
```

### 4) JSON 출력으로 자동화 연동

```bash
python scripts/chat_search.py --origin 김포 --destination 제주 --when 내일 --json
```

---

## Practical search examples

### 편도 최저가

```bash
python scripts/chat_search.py --origin 김포 --destination 제주 --when 내일
```

### 왕복 검색

```bash
python scripts/chat_search.py --origin 김포 --destination 제주 --departure 2026-03-28 --return-date 2026-03-30
```

### 날짜 범위 최저가

```bash
python scripts/chat_search.py --origin 김포 --destination 제주 --when "내일부터 3일"
```

### 여러 목적지 중 최적 조합

```bash
python scripts/chat_search.py --origin 김포 --destinations 제주,부산,여수 --when 이번주말
```

### 너무 이른 비행 제외

```bash
python scripts/chat_search.py --origin 김포 --destination 제주 --when 내일 --exclude-early-before 8
```

### 저녁/늦은 시간대 선호

```bash
python scripts/chat_search.py --origin 김포 --destination 제주 --when 내일 --prefer evening
python scripts/chat_search.py --origin 김포 --destination 제주 --when 내일 --prefer late
```

### 자연어 시간 선호 사용

```bash
python scripts/chat_search.py --origin 김포 --destination 제주 --when 내일 --time-pref "출발 10시 이후, 너무 이른 비행 제외 8시, 늦은 시간 선호"
```

### 귀환 시간 제약 포함

```bash
python scripts/chat_search.py --origin 김포 --destination 제주 --departure 2026-03-28 --return-date 2026-03-29 --return-after 18
```

---

## Search options that matter in real use

`chat_search.py --help` 기준 주요 옵션:

- `--origin`: 출발지 공항명 또는 코드
- `--destination`: 단일 목적지
- `--destinations`: 쉼표 구분 여러 목적지
- `--when`: 자연어 날짜/날짜 범위
- `--departure`: 출발일 직접 지정
- `--return-date`: 왕복 귀국일 직접 지정
- `--return-offset`: 날짜 범위 검색 시 출발일 기준 귀국일 오프셋
- `--adults`: 성인 수
- `--cabin`: `ECONOMY`, `BUSINESS`, `FIRST`
- `--time-pref`: 자연어 시간 선호
- `--depart-after`: 출발 최소 시각
- `--return-after`: 귀국 최소 시각
- `--exclude-early-before`: 너무 이른 비행 제외 기준 시각
- `--prefer`: `late`, `morning`, `afternoon`, `evening`
- `--json`: 구조화 결과 출력

추천은 다음처럼 나뉩니다.

- **대화형 요청**: `--when`, `--time-pref` 중심
- **정밀 자동화**: `--departure`, `--return-date`, `--depart-after`, `--return-after` 중심

---

## Price alert workflow

가격 감시 쪽은 `scripts/price_alerts.py`를 사용합니다.

### 1) 단일 목적지 감시 등록

```bash
python scripts/price_alerts.py add --origin 김포 --destination 제주 --departure 내일 --target-price 70000 --label "김포-제주 내일 특가"
```

### 2) 날짜 범위 감시 등록

```bash
python scripts/price_alerts.py add --origin 김포 --destination 제주 --date-range "내일부터 3일" --target-price 80000 --label "김포-제주 3일 범위 감시"
```

### 3) 다중 목적지 감시 등록

```bash
python scripts/price_alerts.py add --origin 김포 --destinations 제주,부산,여수 --departure 내일 --target-price 90000 --label "김포 출발 내일 다중 목적지 감시"
```

### 4) 커스텀 메시지 템플릿 등록

```bash
python scripts/price_alerts.py add --origin 김포 --destinations 제주,부산 --date-range "내일부터 3일" --target-price 85000 --message-template "[특가감시] {best_destination_label} {departure_date} {observed_price} / 기준 {target_price}"
```

### 5) 저장된 규칙 확인

```bash
python scripts/price_alerts.py list
```

### 6) 규칙 점검

```bash
python scripts/price_alerts.py check
```

### 7) dedupe 무시하고 강제 확인

```bash
python scripts/price_alerts.py check --no-dedupe
```

### 8) 마지막 결과를 현재 템플릿으로 렌더링

```bash
python scripts/price_alerts.py render --rule-id <RULE_ID>
```

### 9) 규칙 삭제

```bash
python scripts/price_alerts.py remove --rule-id <RULE_ID>
```

---

## Dedupe behavior

실사용에서는 같은 결과를 계속 보내는 게 제일 거슬립니다. 이 스킬은 두 단계 dedupe를 둡니다.

### 저장 dedupe

동일 조건 + 동일 목표가 규칙은 fingerprint 기준으로 중복 저장하지 않습니다.

### 발송 dedupe

같은 규칙에서 아래 조합이 같으면 재알림을 억제합니다.

- 최저가
- 항공사
- 출발/도착 시각
- 날짜
- 목적지

즉, 가격이나 대표 항공편이 실제로 바뀌었을 때만 다시 알려주기 좋습니다.

---

## Message template variables

커스텀 알림 메시지에서 자주 쓰는 변수:

- `{label}`
- `{route}`
- `{origin_label}`
- `{destinations_label}`
- `{best_destination_label}`
- `{target_price}`
- `{observed_price}`
- `{difference_krw}`
- `{departure_date}`
- `{return_date}`
- `{date_text}`
- `{airline}`
- `{departure_time}`
- `{arrival_time}`
- `{cabin_label}`
- `{status_line}`

스키마/필드 의미가 더 필요하면 `references/price-alerts-schema.md`를 보면 됩니다.

---

## Example output

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

이런 식으로 채팅에서 바로 붙여 쓰기 좋은 요약을 우선 주고, 필요하면 JSON 결과를 상위 레이어에서 다시 가공하면 됩니다.

---

## Automation / scheduling

가격 감시 점검은 결국 아래 명령 하나로 주기 실행하면 됩니다.

```bash
python scripts/price_alerts.py check
```

즉 다음과 같은 상위 시스템과 연결하기 쉽습니다.

- OpenClaw cron/브리핑
- Windows 작업 스케줄러
- 텔레그램 알림 파이프라인
- 자체 JSON 후처리 스크립트

Windows에서는 보조 스크립트도 포함돼 있습니다.

```powershell
powershell -ExecutionPolicy Bypass -File scripts/register_price_alerts_task.ps1 -IntervalMinutes 30
```

---

## Limitations

이 스킬을 쓸 때 알아두면 좋은 제약:

- 국제선 검색은 범위 밖입니다.
- 실제 검색 품질은 upstream Playwright 환경에 영향을 받습니다.
- 사이트 응답 구조가 바뀌면 검색/감시 결과가 흔들릴 수 있습니다.
- 항공권 가격은 매우 자주 바뀌므로, README의 예시 값은 재현 보장이 없습니다.
- 장시간 자동 감시는 브라우저 자동화 의존성과 네트워크 상태의 영향을 받습니다.

---

## Deployment / release notes

현재 GitHub 최신 릴리스: **v0.6.0**

배포 시 확인하면 좋은 흐름:

1. 대표 질의를 실제로 조회한다.
2. 단일 목적지 / 다중 목적지 / 날짜 범위 / 시간 선호 케이스를 각각 확인한다.
3. `price_alerts.py add/list/check/render` 흐름을 점검한다.
4. OpenClaw에서 실제 스킬 호출 문맥으로 한 번 더 확인한다.
5. 태그/릴리스 생성 후 배포 채널(예: ClawHub)을 동기화한다.

README에서 버전별 큰 변화는 아래처럼 요약해두는 게 좋습니다.

- `v0.4.x`: 국내선 검색/감시 기본 흐름 구축
- `v0.5.x`: 자연어/채팅형 검색과 날짜 범위 비교 강화
- `v0.6.0`: 시간대 필터, 늦은 시간 선호, 왕복 귀환 시간 조건 등 실사용 옵션 보강

---

## Related repositories

- Search engine homepage: <https://github.com/twbeatles/Scraping-flight-information>
- GitHub Releases: <https://github.com/twbeatles/korea-domestic-flights-skill/releases>

이 저장소는 OpenClaw 스킬 패키징/사용 관점의 문서를 담고, 실제 검색 엔진 진화는 upstream 저장소를 함께 보는 편이 이해가 빠릅니다.

