# Spec IMP-backend — 관측성 + 가격 그루핑 (넓은 스윕 · 6렌즈 반영)

작성: 2026-07-06 · 개정(6렌즈 반영) · 구간 소유권 = `src/newsstore/enrich/clustering.py`·`signals_pass.py`·`report.py`·`frames.py` + `config/prices.yaml` + `src/newsstore/collect/prices.py` + `tests/test_*.py`. **web/index.html·processor.py 금지**. additive/비파괴, **판정 로직 무변경**.

## 왜 (넓은 스윕 27→15, 주제=관측부재가 지배적 병)
프로덕션 경로에 결정 로그가 없어 "측정 먼저"가 불가. 값싼 관측성부터 심어 조용한 실패를 데이터로 드러낸다. IB4(conviction 사가접기)·IB5-확장은 리뷰 지적으로 이연/축소(측정 먼저·계약 보존).

## IB1. 온라인 gray-band 판정 텔레메트리 [S] — 리뷰 반영(평문·assign 내부·shape 불변)
- **`clustering.py` `EventClusterer.assign` 내부**(결정 분기 ~302-315·no-candidate ~299)에서, 반환 직전에 각 결정을 **평문 구조화 로그**(`log.info`에 key=value: 후보수·top1_cos·gate[det_hi|grayband|below_lo|no_cand]·llm[merge|split|na]·fallback)로 발행. **반환 shape(str|None) 무변경·processor 무변경·LLM콜0·의존성0**(jsonPayload 인프라 불필요 — Cloud Logging grep으로 집계). hot path지만 로그 1줄이라 벽시간 영향 무시. 과병합 vs 과소병합을 실측 가능케.

## IB2. WB4 게이트 퍼널 — 빈 조사큐 FAIL-LOUD [S]
- `signals_pass.py` `_scan`(~110)·`run_signals_pass`(~105-152)가 unexplained 후보의 **단계별 탈락 카운터**(표본부족·거래량미확인[주식전용 분리]·서사커버리지있음·z미달)를 `totals` dict에 additive + `log.info` 이중화(doc은 매런 덮어써지니 로그 누적 트렌드). 로직 무변경. 조사큐 0 이유(조용한 장 vs 과게이팅)를 드러냄.

## IB3. 리포트·프레임 실패 렌즈 메타 발행 [S] — 리뷰 반영(lens_id zip)
- `report.py` `run_report_pass`: `_one`이 실패 시 **failed 사유(silent-stale만: LLM에러 ~565·결정론 검증실패 ~569)를 lens_id와 함께** 반환하거나, 호출부(~607-609)에서 `units`와 zip해 실패 렌즈를 귀속(현 bare "failed"는 lens_id 없음 — zip 필요). `_skips` 옆에 데이터 발행(~619). **리뷰 기각은 제외**(fresh doc+conviction 배지로 이미 표면화). `frames.py` `run_frame_pass` continue(~263·270·273)도 동일. UI(범위밖)가 stale 원인 귀속.

## IB5. 가격 group·order 필드 + VIX·달러지수 [S] — 리뷰 반영(그룹 명시·주입지점·order)
- **group·order (frozen 계약, IMP-web 소비)**: `config/prices.yaml` 각 심볼에 **명시 `group`**(지수·금리·환율·원자재·변동성 — 주석 SSOT를 데이터로, VIX=변동성·달러지수=환율로 명시 매핑) 추가. **`prices.py load_price_symbols`(~41)가 `r.get("group")`을 읽어** `PriceSymbol`(frozen dataclass에 `group:str|None=None` 말미 default)에 실음 — 위치인자 생성·기존 테스트 후방호환. **order = load 시 yaml 등장 순서(enumerate)** 를 PriceSymbol/저장 dict에 실어 web이 무순서 Firestore에서도 순서 복원. `run_price_pass` 저장 dict에 group·order 병합. **frozen: 가격 doc `group`(str)·`order`(int).**
- **VIX·달러지수**: `^VIX`(group=변동성)·달러지수(group=환율)를 prices.yaml 등재. **채택 전 실측 스팟체크**(달러지수 `DX-Y.NYB`/`DX=F`는 ^KS200류 값불량 위험) — 값 검증 실패 시 제외. **주의(리뷰)**: 스팟체크는 등재시점만 보증 → 운영 stale은 별도(가격 신선도 검문=직전 정합성 번들 소관, 여기선 등재만).

## 범위 밖 (이연 — 측정 먼저·리뷰 반영)
**IB4 conviction 사가접기(드롭)** — c 축소가 high→medium 강등·계약변경·빈도 미측정(측정 먼저 위반). 요약→게이트 주입·top-k 회복·KOSPI 벤치마크·유니버스 확장 — 과병합 치명·B-cubed 골든 필요(IB1 텔레메트리 실측 후). web 렌더(IMP-web).

## 리스크/주의 (주입 gotchas)
- **판정 로직 무변경**(IB1·IB2·IB3): 로그·발행만. 반환 shape 불변(IB1). 매직넘버 금지(카운터·불변식).
- **비파괴/additive**: PriceSymbol `group·order` 말미 default(위치인자·frozen 후방호환). 기존 문서·계약 shape 불변. mock↔실 None(`x or []`), datetime 3축. Docker 전용 테스트.
- **frozen 계약**: 가격 doc `group`(지수/금리/환율/원자재/변동성 문자열 그대로)·`order`(int) → IMP-web 소비. VIX/달러 스팟체크 실패 시 제외(억지 등재 금지).
- 머지·배포는 오케스트레이터(브랜치까지만).

<!-- 6렌즈 반영: (high)IB1 jsonPayload 불가+processor shape확장 위반 → assign 내부 평문 로그·shape 불변·processor 제외. (drop)IB4 conviction 사가접기 → high→medium 강등·계약변경·측정먼저 위반으로 이연. IB5 그룹 명시(VIX=변동성·달러=환율)·load_price_symbols 주입·order 필드·달러 stale 주의. IB3 lens_id zip. IB2 견고 유지. -->
<!-- spec-review: passed -->
