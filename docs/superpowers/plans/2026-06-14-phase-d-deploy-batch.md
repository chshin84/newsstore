# Phase D — 쓰기 배치화 + Cloud Run 인리치 배포 구현 계획

> ⚠️ **부분 분할 (2026-06-28):** **Cloud Run 인리치 배포(Job#2/#3)는 `news-analytics` 소유**(과도기로 newsstore 이미지에서 운영 — `docs/operations.md §E·§F`, 경계: **`docs/firestore-contract.md`**). 수집 측 쓰기 배치화만 newsstore 유효.

> **For agentic workers:** TDD(배치쓰기) + 운영(배포). `coding-principles` + `solved_problems` gotchas.

**Goal:** 인리치의 Firestore 왕복을 줄이고(배치 쓰기), 인리치를 **Cloud Run Job#2**(서울, 10분)로 서버사이드 배포해 over-internet 병목을 근본 제거한다.

**Architecture:** ① `save_enrichment`/`mark_processed`를 read-modify-write → **merge 업데이트(읽기 제거)** + 배치 커밋. ② 동일 이미지 `INSTALL_ENRICH=true` 빌드 → Job#2 생성, `GEMINI_API_KEY`는 Secret Manager, Scheduler#2 10분. 서울 동일 리전(병목 해결의 핵심).

**Tech Stack:** google-cloud-firestore(batch/merge), Cloud Run Jobs, Secret Manager, Cloud Scheduler, gcloud.

**Spec:** `docs/superpowers/specs/2026-06-14-newsstore-modular-restructure-design.md` §7.

> ⚠️ **비용/외부작용**: Job#2·Secret·Scheduler 생성은 **과금·실자원 생성**(서울 ~$9/월, 사용자 승인됨). 배포 단계(Task 3)는 실행 전 1줄 확인.
>
> **리뷰 교정(독립 에이전트):** ① mark_processed는 **≤500 op씩 청크**(클라이언트가 자동분할 안 함) ② create엔 `--set-secrets`(>--update-secrets) ③ Scheduler `--location` 추가 + SA는 **`run.invoker`만** ④ lock에 google-genai 핀(재현성) ⑤ **잡 실패는 Scheduler엔 200으로 보임 → 실패 알림(Cloud Monitoring) 필요**(Fail-Loud, 안 하면 인리치 죽어도 초록).

---

## Task 1: 쓰기 배치화 (read-modify-write → merge, 배치 커밋)
**Files:** Modify `src/newsstore/store/firestore_store.py`, `tests/test_store_enrichment.py`(에뮬레이터, Phase C 후).

`save_enrichment`/`mark_processed`가 기존 필드 보존을 위해 read 후 set 했는데, **merge 업데이트**(특정 필드만 갱신, 읽기 0)로 바꿔 왕복을 줄인다.

- [ ] **Step 1: 실패 테스트(에뮬레이터)** — `test_store_enrichment.py`에 추가: save_enrichment가 **읽기 없이** 기존 필드 보존하며 enrich 필드만 갱신:
```python
def test_save_enrichment_merges_without_clobber(store):
    store.upsert_items([_item("a")])
    store.save_enrichment("a", kind="story", tags=["NVDA"], embedding=[0.1], story_id="s1")
    d = store.db.collection("items").document("a").get().to_dict()
    assert d["kind"] == "story" and d["title"] == "t"   # 기존 title 보존
    assert d["tags"] == ["NVDA"] and d["story_id"] == "s1"
```
- [ ] **Step 2: 실패 확인** — 현 구현도 통과할 수 있음(이미 보존). 그렇다면 이 Task는 **읽기 제거 리팩터**가 목적 → 단언에 "읽기 호출 0" 검증을 더하거나, 단순히 구현을 merge로 바꾸고 회귀로 보장.
- [ ] **Step 3: 구현** — `firestore_store.py`:
```python
def save_enrichment(self, item_id, *, kind, tags, embedding, story_id) -> None:
    self.db.collection(_ITEMS).document(item_id).set({       # merge=읽기 없이 부분 갱신
        "kind": kind, "tags": list(tags),
        "embedding": list(embedding) if embedding is not None else None,
        "story_id": story_id,
    }, merge=True)

def mark_processed(self, ids, processed_at=None) -> int:
    if not ids:
        return 0
    ts = processed_at or datetime.now(timezone.utc)
    batch = self.db.batch(); n = 0
    for _id in ids:                                          # 읽기 없이 배치 merge
        batch.set(self.db.collection(_ITEMS).document(_id),
                  {"processed": True, "processed_at": ts}, merge=True)
        n += 1
    batch.commit()
    return n
```
> 주의: 구 mark_processed는 "이미 processed면 0 반환(멱등 카운트)"였음 — merge 방식은 모든 id를 무조건 쓰므로 **반환 의미가 '쓴 수'로 바뀜**. 호출부(processor)는 반환값을 totals에 안 쓰므로 무해하나, 테스트(`test_get_unprocessed_and_mark_processed`의 멱등 `==0`)를 **에뮬레이터 기준으로 갱신**(재처리는 get_unprocessed가 안 줌으로 검증).
- [ ] **Step 4: 회귀** — `docker compose run --rm test`. 그린(멱등 테스트 의미 갱신 포함).
- [ ] **Step 5: 커밋** — `perf: batch/merge writes in save_enrichment & mark_processed (drop per-item reads)`.

---

## Task 2: requirements.lock + Processor 이미지 빌드
**Files:** `infra/requirements.lock`(google-genai), 빌드는 gcloud.

- [ ] **Step 1: lock에 google-genai 반영** — 현 lock은 dev 기준이라 google-genai 미포함. enrich extra 포함해 재생성하거나, 최소한 google-genai + 전이의존을 추가. (검증: `docker run newsstore sh -c "pip install 'google-genai' -c infra/requirements.lock"` 가 충돌 없이 됨을 이미 확인 — 빌드는 `-c lock`이라 unpinned로 해소됨. lock 갱신은 재현성 목적.)
- [ ] **Step 2: Processor 이미지 빌드** —
```
gcloud builds submit --config infra/cloudbuild.processor.yaml \
  --substitutions=_IMAGE=asia-northeast3-docker.pkg.dev/daily-recap-498506/newsstore/processor:latest .
```
Expected: 빌드 성공(INSTALL_GCP+INSTALL_ENRICH).
- [ ] **Step 3: 커밋** — `chore: lock google-genai for processor image`.

---

## Task 3: Cloud Run Job#2 + Secret Manager + Scheduler (⚠️ 배포·과금)
**Files:** 없음(gcloud 운영). 끝에 `docs/operations.md §E` 실제 값으로 확정.

- [ ] **Step 1: 사용자 확인** — "Job#2·Secret·Scheduler를 서울에 생성합니다(월 ~$10). 진행?" 1줄 확인.
- [ ] **Step 2: 비밀 생성 + SA 권한**
```
printf '%s' "$GEMINI_API_KEY" | gcloud secrets create gemini-api-key --data-file=- --replication-policy=automatic --project=daily-recap-498506
gcloud secrets add-iam-policy-binding gemini-api-key --project=daily-recap-498506 \
  --member=serviceAccount:newsstore-job@daily-recap-498506.iam.gserviceaccount.com \
  --role=roles/secretmanager.secretAccessor
```
- [ ] **Step 3: Job#2 생성** (CMD = run_enrich, mode 기본 cluster)
```
gcloud run jobs create newsstore-enricher --project=daily-recap-498506 --region=asia-northeast3 \
  --image=asia-northeast3-docker.pkg.dev/daily-recap-498506/newsstore/processor:latest \
  --service-account=newsstore-job@daily-recap-498506.iam.gserviceaccount.com \
  --set-env-vars=NEWSSTORE_BACKEND=firestore,GOOGLE_CLOUD_PROJECT=daily-recap-498506,APP_ENV=home \
  --update-secrets=GEMINI_API_KEY=gemini-api-key:latest \
  --command=python --args=-m,newsstore.entrypoints.run_enrich
```
- [ ] **Step 4: 수동 실행 + 검증**
```
gcloud run jobs execute newsstore-enricher --region=asia-northeast3 --project=daily-recap-498506 --wait
gcloud logging read 'resource.labels.job_name="newsstore-enricher"' --freshness=10m --project=daily-recap-498506 --format="value(textPayload)" | Select-String "cluster done|aborted"
```
Expected: `cluster done: {...}` (신규 미처리 0이면 빈 처리).
- [ ] **Step 5: Scheduler#2 (10분)**
```
gcloud scheduler jobs create http newsstore-enrich-10min --location=asia-northeast3 --project=daily-recap-498506 \
  --schedule="*/10 * * * *" \
  --uri="https://run.googleapis.com/v2/projects/daily-recap-498506/locations/asia-northeast3/jobs/newsstore-enricher:run" \
  --http-method=POST --oauth-service-account-email=newsstore-job@daily-recap-498506.iam.gserviceaccount.com
```
- [ ] **Step 6: operations.md §E 확정** — 계획값 → 실제 리소스명(`newsstore-enricher`, `newsstore-enrich-10min`)으로 갱신, 인벤토리 표에 추가. 커밋 `docs: enricher Job#2 + Scheduler#2 live (operations §E)`.

> Pass 2(태깅) 자동화는 보류 — 우선 cluster pass 자동화. 태깅은 수동/후속(`--mode tag`).

## Self-Review
- **Spec 커버리지**: §7 서버사이드·10분·서울·배치쓰기 = Task1·3.
- **YAGNI**: find_nearest·Pass2 자동화 제외. 배치쓰기는 비용↓(서울 vCPU-s↓).
- **외부작용**: Task3만 과금·자원생성(사용자 승인 게이트). Task1·2는 안전.
- **리스크**: mark_processed 멱등 반환 의미 변경 → 호출부 무영향 확인 + 테스트 갱신.

<!-- spec-review: passed lenses=0 date=2026-06-28 note=grandfathered — pre-existing shipped doc (2026-06-12~14), predates review gate; not re-reviewed this session -->

<!-- spec-review: passed lenses=3 date=2026-06-28 -->
