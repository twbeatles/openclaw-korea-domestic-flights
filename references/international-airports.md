# 주요 국제 공항 / 도시 코드 예시

이 목록은 자주 쓰는 국제선 예시만 담고 있다. 별칭 테이블에 없는 경우에도 raw 3자리 uppercase 공항/도시 코드는 그대로 입력할 수 있다.
전체 키워드 사전은 `references/search-keywords.md`를 본다.

- `ICN` — 인천
- `NRT` — 도쿄 나리타
- `HND` — 도쿄 하네다
- `TYO` — 도쿄(도시 코드)
- `KIX` — 오사카 간사이
- `OSA` — 오사카(도시 코드)
- `FUK` — 후쿠오카
- `CTS` — 삿포로
- `OKA` — 오키나와
- `NGO` — 나고야
- `TPE` — 타이베이(대만)
- `HAN` — 하노이
- `CEB` — 세부
- `BKK` — 방콕
- `SIN` — 싱가포르
- `HKG` — 홍콩
- `SGN` — 호치민
- `DAD` — 다낭
- `DPS` — 발리

## 한글/영문 별칭 예시

- `나리타`, `narita` → `NRT`
- `하네다`, `haneda` → `HND`
- `도쿄`, `tokyo` → `TYO`
- `간사이` → `KIX`
- `오사카`, `osaka` → `OSA`
- `후쿠오카`, `fukuoka` → `FUK`
- `삿포로`, `sapporo` → `CTS`
- `오키나와`, `okinawa` → `OKA`
- `나고야`, `nagoya` → `NGO`
- `타이베이`, `타이페이`, `대만`, `taipei` → `TPE`
- `하노이`, `hanoi` → `HAN`
- `세부`, `cebu` → `CEB`
- `방콕`, `bangkok` → `BKK`
- `싱가포르`, `singapore` → `SIN`
- `홍콩`, `hong kong` → `HKG`
- `호치민`, `ho chi minh` → `SGN`
- `다낭`, `danang` → `DAD`
- `발리`, `bali` → `DPS`

## 항공사 분류 필터 (원본 GUI 필터 이식)

- `--airline LCC` — 진에어, 제주항공, 티웨이항공, 에어부산 등 저비용항공사만
- `--airline FSC` — 대한항공, 아시아나항공, JAL, ANA 등 대형항공사만
- `--nonstop-only` — 직항만
- `--max-stops 1` — 경유 1회까지 허용
- `--min-price`/`--max-price` — 혜택가 적용 실질가 기준 예산 범위

## CLI 예시

- `korea-flights search --origin ICN --destination NRT --departure 내일 --scope international --human`
- `korea-flights search --origin SEL --destination TYO --departure 내일 --human`
- `korea-flights search --origin ICN --destination CTS --departure 내일 --nonstop-only --human`
- `korea-flights search --origin ICN --destination KIX --departure 내일 --airline LCC --max-price 200000 --human`
- `korea-flights range --origin ICN --destination KIX --date-range "다음주말" --scope international --human`
- `korea-flights matrix --origin ICN --destinations NRT,KIX,FUK --date-range "내일부터 3일" --scope international --human`

기존 `scripts/search_flights.py`, `scripts/search_date_range.py`, `scripts/search_destination_date_matrix.py`는 호환용 forwarder로만 유지된다. 새 자동화와 문서는 `korea-flights` 패키지 CLI를 기준으로 작성한다.
