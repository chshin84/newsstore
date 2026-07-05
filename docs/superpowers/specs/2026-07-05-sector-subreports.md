# Spec A — 주도 섹터 서브리포트 (한국·미국, 풀 프로세스) [#8b]

작성: 2026-07-05 · 구간 소유권 = `src/newsstore/enrich/*` + `config/*` + `tests/*`. **web/index.html 금지**(Spec B가 병렬 소유 — 섹터 리포트는 report_groups로 자동 렌더).

## 왜 (측정된 필요)
Broad us_equity/kr_equity 리포트는 하위섹터 참사를 놓친다 — Micron·SanDisk 메모리 폭락이 "미국 주식" 한 덩어리에 묻힘. 사용자: "기사로 보는 것 ≠ 분석, 쪼개서 보고 합쳐야." → **한국·미국 주도 섹터별 서브리포트를 각 리포트와 동일 풀 프로세스(프레임→섹션)로** 생성. 기존 주식 리포트를 **대체가 아니라 보완**(broad = 전체, 섹터 = 심층).

## 배경/맥락 (서브에이전트 주입)
- gotchas: 과병합=치명(클러스터 불변), 매직넘버=불변식, mock↔실 None(`x or []`), datetime 직렬화(3축만). Docker 전용 테스트, 로컬 python 없음.
- 파이프(grounding): `run_enrich --mode report` → frames.run_frame_pass(lens_ids) 선행 → report.run_report_pass(lens_ids, context_lens_ids, price_ctx, price_by_lens). 리포트는 렌즈별로 `get_stories_for_report(lens_id)` 스토리를 top-K→섹션. `report_lens_ids(t)`=standing만. `report_groups(t)`=meta로 발행 → 프론트 사이드바·렌더가 이걸로 그룹 순회(web 무변경으로 섹터 자동 노출).
- 스토리 lenses에 country(us_equity/kr_equity)와 sector(sector_tech/financials/energy/healthcare/industrials)가 공존(예 [sector_tech, us_equity, watch_nvidia]). 즉 (country, sector)는 **두 렌즈 교집합**으로 도출 — 신규 taxonomy 없이.
- 이미 배포(불변): report=자산only+fold-in, 시간적 인과, 가격 교차검증, divergence/conviction, 사가-인지 랭킹. topics.yaml sector_* 렌즈 존재.

## 설계 (v1)

### 1. 주도 섹터 선발 (결정론)
- country ∈ {us, kr} 각각, sector_* 각각에 대해 **교집합 스토리 집합**(country_equity ∈ lenses ∧ sector ∈ lenses) 규모를 결정론 신호로 스코어: 스토리 impact 합 또는 story_rank 합(밀도×임팩트).
- 각 country에서 **상위 N개(예 N=2) (country,sector) 조합**을 주도 섹터로 선발. 임계·N은 불변식/env(매직넘버 회피, 예 min 스토리 수 미만 조합은 스킵).
- (신규 country-split 렌즈 taxonomy는 만들지 않는다 — 교집합 필터로 도출.)

### 2. 섹터 프레임 + 리포트 (풀 프로세스 재사용)
- 선발된 각 (country,sector) 조합에 **합성 키** `sec_{country}_{sector}`(예 sec_us_tech).
- 그 조합의 스토리 = country_equity ∧ sector 교집합. 이 스토리 집합으로 **기존 frame_pass·report_pass 재사용**(별도 로직 신설 최소화 — 렌즈 단위 대신 '스토리 집합'을 받게 소폭 일반화하거나, 조합키를 임시 렌즈처럼 취급).
- 산출: `frames/sec_{country}_{sector}`(standing 프레임·RAS·age-gate 동일), `reports/sec_{country}_{sector}`(헤드라인·리드·섹션·conviction 동일). **가격 교차검증은 v1 생략**(섹터 ETF price_key 없음) — divergence 필드 없음, conviction·시간인과·과인용가드는 그대로.
- 사가-인지 랭킹·context fold-in 등 기존 처리 자동 상속(같은 report_pass면).

### 3. 발행 (프론트 자동 렌더)
- `meta/report_groups`에 **"주도 섹터"(또는 주식 하위)** 그룹으로 sec_* 조합을 추가 → 프론트 사이드바·리포트 루프가 web 변경 없이 렌더. 라벨=예 "미국 · 반도체/테크".
- 기존 broad us_equity/kr_equity 그룹은 **유지**(보완). 리포트 순서에 섹터 그룹 위치 정의.

## 통합/배포 (오케스트레이터가 머지 후)
- 전체 pytest GREEN. processor 재빌드→report 실행. 라이브: sec_us_tech 등 섹터 리포트 생성 확인, 프론트에 섹터 그룹 자동 노출(Spec B와 통합 후). Micron류 메모리 참사가 섹터 리포트에 잡히나 스팟체크.

## 범위 밖
- web 렌더(Spec B). 리포트 섹션 구조 재편(#4). country-split taxonomy 신설(교집합으로 도출). 섹터 ETF 가격(price_key)·divergence(v2). 클러스터 변경.

## 리스크/주의
- **비용**: 섹터 조합 수 × (프레임+리포트 콜). N을 작게(country당 2~3) + min-스토리 게이트로 상한. 4×/일 곱해짐 — 정당화(심층 분석 가치) vs 비용 명시.
- 교집합 스토리가 적으면(섹터 희박) 빈/약한 리포트 — REPORT_MIN_STORIES 가드 재사용.
- 조합키를 렌즈처럼 다룰 때 기존 렌즈 계약(price_key_for·report_group 등)과 충돌 없게 — sec_* 는 별도 처리 경로.
- 선발이 매직넘버 컷으로 흐르지 않게(불변식: 스토리 밀도 순 상위 N, min 게이트).
- report.py/frames.py를 소폭 일반화할 때 기존 자산 리포트 회귀 0(테스트 불변).

<!-- 3렌즈 리뷰: critical 2 — (1)비용 정당화 없음(원칙7, Micron 일화뿐) (2)broad와 섹터 스토리 중복(섹터⊂broad, 같은 내용 2번, B5 다이제스트제거와 자기모순). major 다수(lens_id 멤버십필터로 sec_* 재사용 broken·report_groups meta 런타임 sec_* 못담음·라벨 raw노출·비결정 태깅 위 선발). 재프레임: 별도 섹터리포트(중복) 대신 broad 주식리포트를 섹터-인지로 부각(#4로 흡수). → 드롭 권고, 사용자 판단. -->
<!-- spec-review: escalated -->
