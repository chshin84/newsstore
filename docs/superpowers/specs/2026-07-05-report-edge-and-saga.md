# Spec A — 리포트 엣지화(divergence 배지 + conviction) + 사가 분리 측정 (백엔드/분석)

작성: 2026-07-05 · v2(3렌즈 리뷰 반영 재작성) · 구간 소유권 = `src/newsstore/enrich/*` + `config/*` + `scripts/*` + 관련 테스트
(웹은 Spec B 소유 — 이 스펙은 `web/index.html`을 만지지 않는다. 계약 필드만 발행.)

## 이 재작성이 바꾼 것 (리뷰 반영)
- **divergence 헤드라인화 철회**(critical). lean=극개수 프록시는 약해 헤드라인 근거로 부족 → **배지(재료)로만** 저장, LLM엔 이미 배포된 가격 사실 주입(교차검증)으로 충분. 개수 프록시는 '판정 아닌 재료'로 명시.
- **사가 LLM 그룹핑 구현 연기**(critical: 과병합 재현 위험·비결정론·측정 없음) → 대신 **비침습 측정 스크립트**만. 측정이 처방(클러스터 재캘 vs LLM 사가)을 고른 뒤 별도 스펙. **`sagas` 필드는 계약에서 제거.**
- model_for 신규 usage 불필요(divergence·conviction 결정론·LLM 0콜) → models.yaml/USAGES 안 건드림.
- conviction 임계를 **단조 불변식**으로(매직넘버 회피).

## 배경/맥락 (서브에이전트 주입 필수)
- 코드 원칙: `docs/coding-principles.md`. gotchas: `docs/solved_problems.md`(**과병합=치명적**이라 클러스터는 precision-favor gray-band로 의도적 타이트; mock↔실client None 차이 `x or []`; 매직넘버 금지=불변식; datetime 직렬화 크래셔).
- Docker 전용 테스트: `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest -q`. 로컬 python 없음.
- 리포트 파이프: `run_enrich --mode report` → frames.py(선행) → report.py. `report.py`에 이미 있음: `_review`(frame·price_ctx 출처), 1회 재작업, 과인용 가드, `price_context`, dev_arc 시간순 arc + 서사 v1.1.
- 데이터 위치(grounding 실측): frame 문서 = AXES(risks/premiums/watchpoints) 극. `prices/{key}` = close·percent_change·series. `get_stories_for_report`(firestore_store)는 id/title/summary/lenses/risk/impact/count/developments/last_seen 반환(entities·asset_hint 미포함 — 측정 스크립트는 별도로 items/스토리 문서를 직접 조회하거나 오프라인 재임베딩).
- 이미 배포(건드리지 말 것): 자산-only 리포트, fold-in, 가격 교차검증(price_ctx 주입·리뷰어 출처③).

## 📜 스키마 계약 (Spec B가 렌더 — 이름·타입 고정)
`reports/{lens}` 문서에 **추가**(기존 필드 불변):
```
divergence?: {                   # 뉴스 센티먼트(약한 프록시) vs 실제 가격. '재료' 배지 — 판정 아님.
  kind: "over_fear" | "over_hope" | "aligned" | "none",
  price_key: string,             # 예: "usdkrw"
  price_pct: number,             # 전일 등락%
  note: string                   # 한 줄 재료 설명(단정 금지 어투)
}                                # 가격 매핑 없는 렌즈는 필드 생략
conviction: {                    # 이 리포트 판단의 근거 강도(거친 신호)
  level: "high" | "medium" | "low",
  basis: string                  # 근거 한 줄(인용 수·프레임 극 지지·리뷰 통과 방식)
}
```
**`sagas`는 이번 계약에 없음(연기).** `_backdrop`·`_skips`·`rising`·`frames/*` 불변.

## 작업 (TDD — 실패 테스트 먼저, 불변식으로 검증)

### A1. divergence 배지 (헤드라인화 X, 재료로만)
- **결정론 계산**: frame lean = `len(premiums) − len(risks)`(**약한 개수 프록시임을 note/코드주석에 명시**). 가격 방향은 **단일일 percent_change가 아니라 최근 추세**를 우선 — 프레임 lean이 누적 센티먼트라 단일일과 시점 스케일이 안 맞음(리뷰 지적). `prices/{price_key}.series` 최근 N일(예 3~5일) 방향(첫↔끝)을 가격 방향으로 쓰고, percent_change는 보조. (series 없으면 percent_change 폴백.)
- **deadband ε**(config `NEWSSTORE_DIVERGENCE_DEADBAND`, 기본 0.3): 추세 변화가 `< ε` = 무반응.
  - lean<0(공포우세) & pct ≥ −ε(안 빠짐: 상승/무반응) → `over_fear` (뉴스 공포인데 가격이 안 반영)
  - lean>0(기대우세) & pct ≤ +ε(안 오름) → `over_hope`
  - 부호 정합(공포+하락 / 기대+상승, 각 ε 밖) → `aligned`
  - lean==0 또는 가격 없음 → `none`(또는 필드 생략)
- **저장만**(divergence 필드). **헤드라인화·프롬프트 강조 주입 안 함** — 가격 사실은 이미 price_ctx로 주입 중. divergence는 UI 배지·참고용. note는 "…재료(단정 아님)" 어투.
- 불변식 테스트: (lean 부호, pct, ε) 조합별 kind 정확. deadband 경계(±ε) 정확. 가격 없으면 필드 없음. note 없음이 아닌 실제 케이스.

### A2. conviction 등급 (단조 불변식)
- **실이득(왜 필요)**: 신뢰도 캘리브레이션 — 독자가 근거 약한 리포트를 **디스카운트**하고 강한 것에 무게. 낮은 등급 = "이 판단은 근거가 얇으니 덜 믿어라"(#9). UI는 그 신호를 시각화만(Spec B). 소비 동작이 명확하므로 장식이 아님.
- **신호**(전부 결정론, `_one` 시점에 캡처 — 저장된 review dict만으론 1차/재작업 구분 불가하니 반드시 `_one` 제어흐름에서 계산): c=triggered 섹션의 고유 인용 story_id 수 · p=유효 pole_id 가진 triggered 항목 수(프레임 극 지지) · r=리뷰 통과 방식(1차통과=2 / 재작업통과=1 / 배지(passed=False)=0). (**r은 거친 프록시** — 재작업통과가 반드시 덜 근거된 건 아님을 basis에 명시; 단조 등급의 한 입력일 뿐.)
- **등급 규칙(단조 — c·p·r 어느 것이 늘어도 등급이 내려가지 않음)**:
  - c==0 → `low`(인용 없으면 강제).
  - `high` iff r==2 AND p≥1 AND c≥2 · `medium` iff (r≥1 AND c≥1) 이고 high 아님 · 그 외 `low`.
  - (경계값 c≥2는 문서화된 앵커. 핵심 계약은 **단조성**이지 정확한 컷이 아님 — 거친 신호임을 basis에 명시.)
- **저장**: conviction. UI 표시는 Spec B.
- 불변식 테스트: **단조성**(c/p/r 각각 +1 해도 level이 낮아지지 않음) · c==0→low · (r2,p1,c2)→high.

### A3. 사가 분리 측정 스크립트 (구현 연기 — 측정만, 비침습)
`scripts/saga_split_audit.py` — 프로덕션 리포트 경로 무변경. 목적: "같은 사가가 얼마나·어디서 갈리나 + 클러스터 재캘 vs LLM 사가 중 처방 진단".
- **🔴 임베딩 공간 패리티(critical — 없으면 코사인 대조 무의미)**: 코사인을 gray-band 병합 임계(0.65 계열)와 비교하려면 **프로덕션 클러스터가 쓴 것과 같은 임베딩 공간**이어야 한다. 재임베딩은 반드시 프로덕션과 동일 파라미터: **gemini-embedding-001, `output_dimensionality=768`(기본 3072 아님), 동일 task_type, 동일 입력 텍스트 정의(클러스터가 쓰는 제목+요약과 같게)** — `enrich/embedder.py`/`gemini.py`의 실제 embed 설정을 그대로 재사용. **차원 검증 fail-loud**: `len(vec)==768` 단언(불일치 시 zip 무음 절단/가짜 코사인 방지, solved 교훈). 가능하면 **재임베딩 대신 프로덕션 저장 임베딩 재사용**(있으면). 재임베딩은 실 임베딩 API 콜(대상 스토리 수만큼) — 비용 명시.
- **후보 쌍(결정론)**: 최근 리포트 스토리 집합에서 (지배 개체 공유: entities/asset_hint/제목 키워드) ∧ (시간 근접: developments delta_time / last_seen 간격) ∧ (임베딩 코사인, 위 패리티 준수).
- **출력**: 분리율(후보/스토리) · 코사인 분포 · **코사인 vs 병합 임계 대조** · 렌즈별 · 예시(엔화 초읽기↔반등).
- **정밀도(선택)**: 후보 ~50쌍 오프라인 LLM 1패스 "같은 사가?" 라벨(스크립트 내, 프로덕션 콜 아님) + 손 골든 ~20쌍(엔화 등).
- **판정 게이트(정량 정의)**: 후보 쌍 코사인 **중앙값이 병합 임계 이상**이면 → 클러스터 재캘 처방(임계 바로 아래서 갈린 것) / 코사인이 임계보다 확연히 낮은데(예 중앙값 < 임계−0.1) 골든/LLM이 같은 사가로 확인 → 의미 기반 LLM 사가 처방 / 후보 쌍 수가 스토리 대비 무시할 수준(예 <5%) → 사가 불필요. (임계값은 산출 데이터로 확정 — 지금은 방향만.)
- 테스트: 후보 축소 로직(개체 공유·시간 근접 판정)·차원 단언(768) 단위 테스트. LLM/임베딩은 주입(fake)로 결정론.
- **주의**: store **읽기 전용 조회**(프로덕션 store 코드 무변경). 결과는 사람이 읽는 리포트(로그/파일) — 프로덕션 문서에 안 씀.

## 통합/배포 (오케스트레이터가 머지 후)
- 전체 `pytest -q` GREEN. processor 재빌드 → enrich 6잡 갱신 → report 실행. 가격 매핑 렌즈에 divergence·conviction 필드 확인(라이브). 측정 스크립트는 오케스트레이터가 별도 실행해 분리율 리포트 확보(배포 아님).

## 범위 밖 (하지 말 것)
- 웹 렌더(Spec B). 클러스터링(lv1) 코드/데이터 변경. 임베딩 재생성(프로덕션). 사가 LLM **구현**(측정 후 별도 스펙). 국고채/ECOS·5분봉·내부 종목 테이블. divergence 헤드라인화. models.yaml/USAGES 변경.

## 리스크/주의 (리뷰가 짚은 것 — 방어 명시)
- divergence lean은 **약한 개수 프록시**(강도·watchpoints 무시) → 그래서 **배지/재료로만**, 헤드라인·프롬프트 강조 금지. 오탐이 메인 생성을 오염 못하게.
- conviction 등급은 거친 신호 — 정확한 컷이 아니라 **단조성**이 계약. basis에 근거 노출.
- 측정 스크립트는 비침습(프로덕션 무변경). 사가 실제 병합은 측정이 처방을 고른 뒤.

<!-- 3렌즈 재리뷰(v2): v1 critical 2건 해소 확인. 신규 critical(A3 임베딩 패리티)=768 차원 고정+fail-loud로 수정. major(divergence 시점 스케일→series 추세, conviction 실이득 명시) 반영. -->
<!-- spec-review: passed -->
