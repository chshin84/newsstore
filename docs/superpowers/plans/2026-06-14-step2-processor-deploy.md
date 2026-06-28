# Step-2 인리치먼트 — Plan 4: Processor 오케스트레이션 + 배포

> 🔀 **DEPRECATED (분할 · 2026-06-28):** 이 문서가 다루는 인리치/분석은 별개 repo **`news-analytics`** 소유다. newsstore에선 히스토리로만 보존한다. 경계·계약과 소유권 인덱스는 **`docs/firestore-contract.md`** 참조.

> **상태(2026-06-14): 로직·엔트리포인트 구현·테스트 완료. 배포는 사용자 게이트(키·이미지 빌드).**

**Goal:** Plan 1(classify/assign)·Plan 2(store)·Plan 3(tagger/embedder)를 엮는 Processor를 만들고, Cloud Run Job #2로 5분/시간 주기 배포한다.

## 구현 완료 (TDD, 96 passed)
- **`src/newsstore/enrich/processor.py::process_once`** — `get_unprocessed` 배치 → `classify_kind`(비파괴 kind) → story만 `tag_items`+`embed_items` → `assign`(centroid, 매 항목 열린스토리 재조회로 배치 내 합류) → `create_story`/`append_to_story` → `save_enrichment`(kind/tags/embedding/story_id) → `mark_processed` → `close_stale_stories`. 통계 반환. **실 SqliteStore + fake LLM 클라이언트로 end-to-end 테스트**(`tests/test_processor.py`): 스팸/다이제스트 임베딩 제외, 유사기사 합류·직교기사 분리, 빈 큐 no-op.
- **`src/newsstore/process.py::main`** — 엔트리포인트. `make_store`(backend 토글) + `GeminiClient`(env `GEMINI_API_KEY`, 없으면 fail-loud exit 2) + `load_taxonomy`. 배치 상한(`NEWSSTORE_MAX_BATCHES`, 비용 상한) 루프, `LLMError`는 exit 1로 표면화.
- **`infra/Dockerfile`** — `INSTALL_ENRICH` build-arg(google-genai). **`infra/cloudbuild.processor.yaml`** — processor 이미지 빌드.
- **`docs/operations.md` §E** — Job #2 + Secret Manager + Scheduler #2 절차.

## 사용자 게이트 (라이브 — 자동화 불가)
1. **`infra/requirements.lock`에 google-genai 추가**(재생성). lock이 constraints라 미포함이면 빌드 실패. httpx<1.0 등 기존 핀과 충돌 시 해소.
2. **라이브 스모크**: 로컬에서 `GEMINI_API_KEY` 주입해 소량(3~5건) 실태깅·실임베딩 검증(임베딩 차원 768 확인 = `embedder.EMBED_DIM` 일치).
3. **배포**: operations.md §E (비밀 생성 → 이미지 빌드 → Job#2 생성 → 실행 → Scheduler#2).
4. **복합 인덱스**: 스토리/태그 쿼리 필요 시 §D.

## 잔여 (Phase 2 — 사이트, 별개)
- **뷰 read 계약**: base.py에 `get_items_by_kind(kind='story', ...)` / `list_stories(status, since)` 추가(양쪽 스토어 + Protocol 드리프트 테스트) → web/index.html이 backend `kind`/`stories`를 쿼리(클라이언트 JUNK 필터 제거, SSOT 해소). spec §4·unsolved 백로그.
- **member_ids published_at 정렬·중복 방지**(타임라인 계약), firestore 원자성(Increment/transaction)·N+1 — unsolved 백로그(동시성/스케일 확장 시).

## Self-Review
- Spec §3 파이프라인 ①~⑤ = `process_once` 전 단계 커버. §12 step5(클러스터 배선)·step6(Job배포) = 본 Plan.
- disciplined-coder: 비용 상한(배치/MAX_BATCHES)·비밀 분리(Secret Manager·fail-loud)·구조화 에러(LLMError→exit) 반영.
- 비파괴: 전 아이템 mark_processed(저장 보존), spam/digest도 kind 기록.

<!-- spec-review: passed lenses=0 date=2026-06-28 note=grandfathered — pre-existing shipped doc (2026-06-12~14), predates review gate; not re-reviewed this session -->
