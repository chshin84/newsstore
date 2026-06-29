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

## ✅ 배포까지 완료 (2026-06-29, 자율 수행)
- 이미지 재빌드(새 digest) → 4개 Job(enricher/summarizer/lenser/scorer) 이미지 갱신.
- **`newsstore-article` Job 생성**(summarizer를 export+`alpha replace`로 정확히 클론 — command/args/env 포함).
- **스케줄러 3개** 생성: `newsstore-lens-10min`(*/10)·`newsstore-score-10min`(3-59/10)·`newsstore-article-10min`(6-59/10) — 윈도 내 lens→score→article 순.
- **Hosting 재배포**(index.html+config.js 둘 다) → 새 UI 라이브, config.js 200 보존 검증.
- 프로덕션 article 실행 → Firestore 스토리에 **headline/lead/article 11건씩 생성 확인**. https://daily-recap-498506.web.app (Ctrl+F5).

## 🔴 남은 일 (당신 몫 — 캘리브레이션만)
1. **🔴 캘리브레이션**(provisional 동작 중): 0~3 스케일 의미·게이트 임계·`REF_WINDOW`(24h)·헤드라인 delta 가중·`EVENT_SANITY_DAYS`(14). 라이브 데이터로 조정.
2. **라이브 모니터링**: article 생성 품질(헤드라인/리드/bullet), scorer risk/impact 분포, 렌즈 커버리지, 일일 비용($3 상한 내).
3. (event_time는 summary가 새 멤버 붙을 때마다 점진 백필 — 기존 스토리는 보도시각 폴백.)

## 이어가는 법 (집/Web 세션)
`git pull` 후 "Phase 4 배포해줘" 또는 "캘리브레이션 시작". spec·plan·계약이 self-contained라 새 세션이 바로 잇는다. 목업: `docs/superpowers/specs/assets/phase4-report-mockup.html`.
