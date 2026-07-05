# Spec V2-backend — 뉴스×가격 신호 엔진 + 번들 3기능 (Phase 1 적대루프 · 6렌즈 반영)

작성: 2026-07-06 · 개정(6렌즈 리뷰 반영) · 구간 소유권 = `src/newsstore/enrich/signals*.py`(신규) + `src/newsstore/collect/prices.py`(volume·긴 베이스라인) + `config/topics.yaml` + `src/newsstore/enrich/topics.py` + `src/newsstore/entrypoints/*`(v2 패스) + `firestore.rules`(signals 공개read) + `tests/test_*.py`(백엔드만 — `tests/web/*` 금지). **web/index.html 금지**(V2-web 병렬). **기존 report.py/frames.py/story 생성 무변경**(v2=additive).

## 왜
Phase 1(40제시→10라운드 적대→8생존→번들3): 추상 뉴스를 **종목에 착지**, **설명 안 되는 가격이동을 조사 큐**로, **개별 vs 매크로** 구분. 셋 다 뉴스×가격·베이스 직교. **검증 전이므로 conviction 아닌 '조사 트리아지 큐/가설'**(적대 만장일치).

## 프로즌 계약 (V2-web과 SSOT — 구체 스키마 확정)
v2는 additive. 저장 위치·shape 확정(리뷰 critical 해소):
- **스토리 doc 추가 필드**(기존 story 문서에 merge, 비파괴):
  - `landing`: `{ tickers: [{ ticker, label, excess_pct, window_days, resolved: bool }], asset_class_fallback: bool, unverified: true }` — 미해소=asset_class_fallback true·tickers 빈.
  - `breadth`: `{ span: int, asset_classes: [str], price_confirmed: bool, uncovered: [str], unverified: true }` — uncovered=가격계열 없는 자산군('안 움직임' 아님).
- **`signals/unexplained_moves` 단일 doc**(큐): `{ generated_at, items: [{ ticker|key, label, kind: "stock"|"index", move_z, move_pct, vol_confirmed: bool|null, story_coverage: false, rank, unverified: true }], min_sample_ok: bool }` — 정렬(rank)은 **백엔드가 확정**(move_z 내림차순, watch 종목 가중), web은 재정렬 안 함.
- **불변식**: signals/landing/breadth의 모든 산출 doc·필드는 `unverified: true`를 **반드시** 갖는다(테스트로 강제 — 관행 아님, fail-loud).

## 공유 엔진 (SSOT — 세 기능이 이 위에)
- **`signals.move_detector`** — 티커/자산군별 최근 수익률 **+ (주식 한정)거래량**을 **긴 자기 히스토리 대비 백분위·z**로. **베이스라인 = Yahoo range=1y(또는 2y)·interval=1d 별도 페치**(한 콜, 축적/콜드스타트 불필요 — 리뷰 high 해소). 30일 스파크라인과 **분리**(스파크라인은 표시용, 베이스라인은 통계용). 최소표본 게이트(예 유효 거래일 < N이면 min_sample_ok=false로 노출, 정밀 % 억제). 임계=분포 백분위/z 불변식(매직넘버 금지) — **이 임계가 WB4/WB5의 유일한 SSOT**(기능별 재발명 금지).
- **`signals.entity_resolve`** — 스토리 entities → watch 티커. **신규 결정론 함수**(topics.yaml watch 렌즈의 `keywords`→`ticker` 매핑을 읽어 매칭 — `watch_tickers`는 이걸 안 함, 리뷰 지적). 미해소=자산군(렌즈) 폴백(라벨만·landing 콘텐츠 없음 정직 표기).

## WB1. 거래량 배선 (주식 한정 — 리뷰: FX·금리·선물은 무의미/롤노이즈)
- `parse_yahoo_chart`에 volume 추가(`indicators.quote[0].volume`, 같은 콜). **상대거래량 확인은 watch 주식(+주식 지수)만** 사용. FX(KRW=X·JPY=X)·수익률지수(^TNX·^TYX)·선물(CL=F·GC=F·2YY=F)은 **vol_confirmed=null**(거래량 미적용 정직). 선물 롤·주식 캘린더(분기말·만기) 거래량 급등은 확인축으로 신뢰 안 함(가격이 주, 거래량은 주식 보조).

## WB2. 미사용 가격계열 매핑 (신규데이터 0)
- 라이브 미매핑 `us2y·us30y·usdjpy·nasdaq`를 topics.yaml 렌즈 price_key로 매핑. 드리프트 가드(price_key∈prices.yaml) 유지.

## WB3. 개체 착지 (Entity Landing) [스토리 `landing`]
- 스토리 → entity_resolve → watch 티커 → **스토리 창 동안 그 종목의 지수 대비 초과수익(시장 베타 제거)** → `landing`. **회고적 base-rate**(매매신호 아님). 실효는 watch 10종목 언급 스토리에 집중(나머지 폴백=라벨만) — 한계 정직. 일봉 근사·섹터/매크로 교란 잔존 명시.

## WB4. 설명 안 되는 움직임 (Unexplained Move) [signals/unexplained_moves]
- move_detector로 **큰 z 이동 + (주식)거래량 확인**인데 **최근 창 인용 스토리 커버리지 없음** → 큐. **watch 종목 가중**(매크로 상시이동 도배 방지 — 자산군별 임계는 move_detector SSOT 임계 사용, 재발명 아님). min_sample_ok=false면 정밀 순위 억제. 라벨="아직 서사 못 붙인 큰 움직임 → 조사"(‘설명 없음’ 단정 금지).

## WB5. 매크로 브레드스 (Macro Breadth) [스토리 `breadth`]
- 스토리가 몇 자산군을 걸치나 + **가격 확인은 시장 베타 제거 후 초과이동**(리뷰 high: 방향일관 게이트만으론 리스크오프 공동하락을 통과시킴 → 베타 제거로 개별적 브레드스만). deadband+최소앵커. 미계측 자산군(크립토·부동산·한국금리채권·기타원자재)=`uncovered`('안 움직임' 아님).

## 킬스위치·운영 (리뷰: 검증 전 출시 위험)
- v2 신호 패스는 **별 모드/잡**(예 `run_enrich --mode signals`), env 플래그로 on/off(`NEWSSTORE_SIGNALS_ENABLED`). 홍수·오발화 시 즉시 정지 가능(additive라 기존 무영향). firestore.rules에 signals 공개read.

## 범위 밖 (Phase-2/이연)
시그널 성적표(콜드스타트). 리드-래그 실측. 상관 단절. 서사 가속도. 5분봉. web 렌더·토글(V2-web).

## 리스크/주의 (주입 gotchas)
- **매직넘버 금지**: 임계=move_detector 분포 불변식(단일 SSOT). 얇은 표본 정밀% 금지(min_sample 게이트). 긴 베이스라인으로 표본 확보.
- **비파괴/additive**: 기존 문서 계약 불변. story merge=True로 필드 추가. mock↔실 None(`x or []`), datetime 3축. Docker 전용 테스트.
- **정직 불변식**: unverified 플래그 필수(테스트 강제). 미커버=uncovered·미해소=폴백·이동=가설. 오버클레임 금지.
- **거래량 한정**: 주식만 vol_confirmed, 그 외 null.
- **frozen 계약**: 위 스키마 그대로 web이 소비. 머지·배포는 오케스트레이터(브랜치까지만).

<!-- 6렌즈 반영: (high)이동탐지 n≈20 고정→긴 Yahoo 베이스라인 별도페치(콜드스타트 제거). (critical)프로즌 스키마 구체 확정(landing/breadth/unexplained_moves 필드·저장위치·정렬 SSOT). (high)브레드스 베타제거(공동변동 오염 차단). 거래량 주식한정(FX·금리·선물 null). entity_resolve=신규 결정론 함수(watch_tickers 아님). unverified 불변식 강제. 킬스위치+firestore.rules 소유. tests/test_*.py로 소유 명확(web 테스트 배제). 개체착지 실효한계 정직. 전부 엔지니어링 수정(사용자 fork 아님). -->
<!-- spec-review: passed -->
