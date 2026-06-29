# 핸드오프 — Phase 4 (스토리 리포트 리더)

> ⚠️ **이 핸드오프의 핵심은 이미 메모리에 반영됨**(`~/.claude/.../memory/phase4-story-report.md`).
> **읽고 나면 이 파일(`docs/HANDOFF-phase4.md`)은 삭제하세요.** (임시 인수인계용 — 영구 기록은 메모리·spec·계약문서.)

작성: 2026-06-29 (사용자 퇴근, 자율 완수). 모든 코드 **main에 머지·푸시 완료.**

## ✅ 완료 (코드·테스트·머지)
Phase 4 = 스토리를 "기사 더미"가 아니라 **합성 보고서**로. 가로 셀렉터(섹션별 메인, delta×impact 순) → `headline` + `lead` + bullet `article` + **발생/보도 2-타임스탬프 타임라인** + 전일대비 ▲▼·NEW + 번역/원문 토글. Warm Light 팔레트.

- **Group A** — summary 패스가 같은 LLM 콜로 `developments[].event_time`(발생시각) 추출(단독 writer).
- **Group B** — `run_enrich --mode article` 신규 패스(`enrich/article.py`): `headline`/`lead`/`article` + 전일대비 ref. **developments 불간섭(자기 필드만 merge=비파괴 by construction).** store `get_stories_for_article`/`save_story_article` + ports + 배선.
- **Group C** — `web/index.html`: 순수함수(`storyRank`/`deltaBadge`/`isNew`/`nodeTimes`) + 셀렉터·보고서 렌더 + Warm Light.
- **Group D** — `firestore-contract.md`·`analysis-design.md §8` 계약 갱신.
- **검증**: 전체 `docker compose run --rm test` → **207 passed, 1 skipped**. UI 로직 `node stories_logic.test.mjs` → **17 passed**(docker node). spec 3렌즈 리뷰 통과(critical 비파괴 위반 구조적 제거).

## 🔴 남은 일 (당신 몫 — 배포는 회사망 SSL·외부동작이라 무인 제외)
1. **배포** (집에서, 또는 `deploy-office.ps1`):
   - 이미지 재빌드(이미 `--mode article` 포함됨) → `processor:latest` 푸시.
   - **새 Cloud Run Job `newsstore-article`** 생성(`--mode article`, `--service-account=newsstore-job@daily-recap-498506...`).
   - **Hosting REST로 `web/index.html` 재배포**(UI 변경 반영, `x-goog-user-project` 헤더 필수).
   - 상세 절차: `docs/operations.md`.
2. **스케줄러** — 렌즈/스코어 **10분**(사용자 동의했으나 미생성) + article 스케줄러. score 다음에 article이 돌게 순서.
3. **🔴 캘리브레이션**(provisional 동작 중): 0~3 스케일 의미·게이트 임계·`REF_WINDOW`(24h)·헤드라인 delta 가중·`EVENT_SANITY_DAYS`(14). 라이브 데이터로 조정.
4. **라이브 검증**: scorer risk/impact 분포, 렌즈 커버리지(이전 측정 28%→76%), article 생성 품질.

## 이어가는 법 (집/Web 세션)
`git pull` 후 "Phase 4 배포해줘" 또는 "캘리브레이션 시작". spec·plan·계약이 self-contained라 새 세션이 바로 잇는다. 목업: `docs/superpowers/specs/assets/phase4-report-mockup.html`.
