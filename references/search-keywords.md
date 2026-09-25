# 항공권 검색 키워드 사전

`korea-flights` CLI가 이해하는 자연어 입력 키워드 모음이다. 원본
`Scraping-flight-information` 저장소의 공항 목록·GUI 필터 패널·검색
정규화 로직에서 이식했다. 대소문자를 구분하지 않으며, 한글·영문 별칭과
3자리 코드를 섞어 쓸 수 있다.

## 국내선 공항 키워드

| 코드 | 한글 별칭 | 영문 별칭 |
|------|-----------|-----------|
| `GMP` | 김포 | gimpo |
| `CJU` | 제주, 제주도 | jeju |
| `PUS` | 부산, 김해 | busan |
| `TAE` | 대구 | daegu |
| `CJJ` | 청주 | cheongju |
| `KWJ` | 광주 | gwangju |
| `RSU` | 여수 | yeosu |
| `USN` | 울산 | ulsan |
| `HIN` | 사천, 진주 | sacheon |
| `KPO` | 포항, 포항경주 | pohang |
| `YNY` | 양양 | yangyang |
| `MWX` | 무안 | muan |
| `ICN` | 인천 | incheon |
| `SEL` | 서울(묶음 코드) | seoul |

## 국제선 공항/도시 키워드

| 코드 | 의미 | 한글 별칭 | 영문 별칭 |
|------|------|-----------|-----------|
| `NRT` | 도쿄 나리타 | 나리타 | narita |
| `HND` | 도쿄 하네다 | 하네다 | haneda |
| `TYO` | 도쿄(도시 코드) | 도쿄 | tokyo |
| `KIX` | 오사카 간사이 | 간사이 | kansai |
| `OSA` | 오사카(도시 코드) | 오사카 | osaka |
| `FUK` | 후쿠오카 | 후쿠오카 | fukuoka |
| `CTS` | 삿포로 | 삿포로 | sapporo |
| `OKA` | 오키나와 | 오키나와 | okinawa |
| `NGO` | 나고야 | 나고야 | nagoya |
| `TPE` | 타이베이(대만) | 타이베이, 타이페이, 대만 | taipei, taiwan |
| `HAN` | 하노이 | 하노이 | hanoi |
| `CEB` | 세부 | 세부 | cebu |
| `BKK` | 방콕 | 방콕 | bangkok |
| `SIN` | 싱가포르 | 싱가포르 | singapore |
| `HKG` | 홍콩 | 홍콩 | hong kong |
| `SGN` | 호치민 | 호치민 | ho chi minh |
| `DAD` | 다낭 | 다낭 | da nang, danang |
| `DPS` | 발리 | 발리 | bali |

별칭표에 없는 3자리 영문 코드도 그대로 통과된다. 예: `korea-flights search
--origin ICN --destination CTS --departure 내일 --human`

도시 코드는 노선에 따라 공항으로 풀린다. 국내선은 공항 코드를 유지하고
(`GMP`/`ICN`을 `SEL`로 합치지 않음), 국제선은 도시 매핑을 적용한다
(`ICN`→`SEL`, `NRT`→`TYO`, `KIX`→`OSA`). 원본
`scraping/interpark/urls.py`의 `resolve_interpark_location` 규칙과 동일하다.

## 날짜 키워드

기준은 `Asia/Seoul` 오늘이다.

- 상대일: `오늘`, `내일`, `모레`, `글피`, `today`, `tomorrow`, `N일 뒤`, `N주 뒤`
- 요일: `월`~`일`, `월요일`~`일요일`, `이번주 금요일`, `다음주 월요일`
- 주말: `주말`, `이번주말`, `다음주말`
- 월일: `8월 25일`, `8/25`, `8.25`
- 절대일: `2026-08-25`, `20260825`, `2026/08/25`, `2026.08.25`
- 범위: `--date-range "다음주말"`, `--date-range "내일부터 7일"`,
  `--date-range "2026-08-01~2026-08-10"`, `--start-date`/`--end-date` 조합

## 시간 키워드 (`--time-pref`)

| 키워드 | 의미 |
|--------|------|
| `새벽` | 00~05시 |
| `아침`/`오전` | 06~10/11시 |
| `점심` | 11~13시 |
| `오후` | 12~17시 |
| `저녁` | 18~21시 |
| `밤`/`야간` | 20~23시 |
| `늦은` | 18~23시 |
| `출발 10시 이후` | 가는편 하한 |
| `복귀 18시 이후` | 오는편 하한 (`귀환`, `오는편`도 인식) |
| `너무 이른 비행 제외 7시` | 해당 시각 이전 출발 제외 |
| `늦은 시간 선호`, `오전 선호`, `오후 선호`, `저녁 선호` | 정렬 가중치 |

정밀 지정은 `--depart-after 10:00`, `--return-after 18:00`,
`--exclude-early-before 07:00`, `--prefer late|morning|afternoon|evening`을 쓴다.

## 항공사/경유/가격 필터 키워드 (원본 GUI 필터 패널 이식)

| CLI 옵션 | 값 | 원본 대응 |
|----------|----|-----------|
| `--airline` | `all`, `LCC`, `FSC` | 항공사 분류 필터 |
| `--nonstop-only` | 플래그 | 직항만 체크박스 |
| `--max-stops N` | 0 이상 정수 | 최대 경유 횟수 |
| `--min-price`, `--max-price` | 원 단위 정수 | 가격 범위 (만원 단위 입력의 원 단위 환산) |
| `--child`, `--infant` | 0~9 | 소아/유아 승객 수 |
| `--force-refresh` | 플래그 | 강제 재조회 (`Ctrl+Shift+Enter`) |

LCC에는 진에어, 제주항공, 티웨이항공, 에어부산, 에어서울, 이스타항공,
피치항공, 젯스타, 스쿠트, 에어아시아, 비엣젯 등이, FSC에는 대한항공,
아시아나항공, JAL, ANA, 캐세이퍼시픽, 싱가포르항공 등이 들어간다. 원본
`core/airports.py`의 `AIRLINE_CATEGORIES`와 동일한 표다. 가격 필터는
카드사 혜택가가 있을 때 더 낮은 값(실질가) 기준으로 판정한다. 결과의
`airline_category`와 `effective_price` 필드에서 확인 가능하다.

## 자연어 예시 → CLI

- 김포에서 제주 가는 내일 최저가 찾아줘
  `korea-flights search --origin 김포 --destination 제주 --departure 내일 --human`
- 인천에서 삿포로 직항만 찾아줘
  `korea-flights search --origin ICN --destination CTS --departure 내일 --nonstop-only --human`
- 다음주말 도쿄/오사카/후쿠오카 중 어디가 제일 싼지 비교해줘
  `korea-flights matrix --origin ICN --destinations NRT,KIX,FUK --date-range "다음주말" --human`
- 김포 제주 왕복 2박 기준 날짜별 최저가, 저녁 출발로 찾아줘
  `korea-flights range --origin 김포 --destination 제주 --start-date 2026-08-01 --end-date 2026-08-10 --return-offset 2 --time-pref "저녁" --human`
- LCC만, 20만원 이하로 방콕 찾아줘
  `korea-flights search --origin ICN --destination BKK --departure "다음주 금요일" --airline LCC --max-price 200000 --human`
- 소아 1명 포함 타이베이 왕복 강제재조회
  `korea-flights search --origin ICN --destination TPE --departure 2026-09-10 --return-date 2026-09-13 --child 1 --force-refresh --human`
