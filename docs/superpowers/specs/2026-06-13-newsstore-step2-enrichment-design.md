# newsstore Step-2 — 인리치먼트(태깅·임베딩·스토리 클러스터) 설계

> 🔀 **분할 (2026-06-28) — 목표 소유: `news-analytics`.** 이 문서의 인리치/분석은 분리 후 별개 repo `news-analytics` 소유다. **단 코드·Job은 아직 newsstore에서 라이브(과도기 — 마이그레이션 미완)** — 운영 런북은 `docs/operations.md §E·§F`, 경계·계약·소유권 인덱스는 `docs/firestore-contract.md`. newsstore에선 이행 참조로 보존(폐기 아님).

_작성: 2026-06-13 · 상태: 결정 완료, 구현 계획 대기 · 스파이크로 핵심 검증됨_

## 1. 목표 / 범위
raw 기사를 **태그(필터용) + 임베딩 + 스토리 클러스터(내러티브 타임라인)**로 가공한다.

- **Phase 1 (이 설계)**: 백엔드 인리치먼트 — raw → `kind`/`tags`/`embedding`/`story_id` + `stories` 컬렉션 생성.
- **Phase 2 (별개)**: 사이트 스토리 타임라인 UI(스크린샷 같은 "속보 N건"). Phase 1이 데이터 채운 뒤.

핵심 통찰: **태그=안정 어휘(필터/라우팅), 스토리=emergent 내러티브(임베딩이 자동 발견).** "이란 전쟁" 같은 *사건*은 태그가 아니라 *스토리*.

## 2. 확정 사항 (결정됨)
- **태깅 LLM**: Gemini Flash (임베딩과 동일 provider·Tier3·다국어·구조화 출력).
- **임베딩**: Gemini `text-multilingual-embedding` (프로덕션은 **`GEMINI_API_KEY` Tier3**, 백엔드 전용 비밀). **기사당 1회**, 병렬.
- **태그 통제 어휘 = 3축**: tickers + entities + topics (§6).
- **클러스터링**: **centroid 온라인, 임계 ≈0.83**. union-find ❌(전이 연쇄 과병합). (스파이크 검증: 묶인 건 전부 진짜 스토리, 30건 ~12초)
- **시간창**: 새 기사를 최근 **48h '열린 스토리'** 중심과 비교, **24h 무활동 시 close**(비교 대상서 제외).
- **선필터**: 스팸 + Bloomberg 다이제스트를 `kind`로 분류해 임베딩·클러스터 **제외**(저장은 보존).

## 3. 아키텍처 / 데이터 흐름
수집(Step-1)과 **분리된 별도 프로세서**(get_unprocessed 큐 소비). 기존 `processed` 계약 위에 얹음 — 수집기는 안 건드림.
```
Cloud Scheduler → Processor Job (Cloud Run Job #2)
  get_unprocessed(batch) →
   ① 선필터  : kind = story | spam | digest        (raw 보존, 분류만)
   ② 태깅    : Gemini Flash 10건 배치 → 통제어휘 tags        (kind=story만)
   ③ 리뷰    : LLM 리뷰어가 태그 스키마·환각 검증 → 통과분
   ④ 임베딩  : Gemini 임베딩(title+body) → 벡터               (kind=story만)
   ⑤ 클러스터: 48h 열린 스토리 centroid와 코사인 → ≥0.83 join / else 새 스토리(LLM 캐노니컬 헤드라인)
   mark_processed
 → items += {kind, tags[], embedding[], story_id, processed=true}
   stories: {title, centroid_sum[], count, member_ids[](타임라인), entities[], first/last_seen, status}
```

## 4. 데이터 모델
**`items`** (추가 필드): `kind`(story|spam|digest), `tags`(array), `embedding`(array<float> 768), `story_id`(string|null), `processed`(bool), `processed_at`.
**`stories/{id}`** (신규): `title`(LLM 캐노니컬), `centroid_sum`(array<float>), `count`(int), `member_ids`(array, published_at 순=타임라인), `entities`(태그 합집합), `first_seen`/`last_seen`(ts), `status`(open|closed).
- **중심핵** = `centroid_sum / count`. join 시 `centroid_sum += vec, count += 1` (전체 재계산 X).
- 뷰는 `items.kind=='story'` 또는 `stories`를 읽음(스팸/다이제스트 기본 숨김).

## 5. 처리 파이프라인 (단계 상세)
1. **선필터(kind)** — 비파괴. 키워드/패턴(이미 web의 JUNK 로직 이식):
   - spam: lead plaintiff / class action / 로펌명 / "$X 투자했다면" 등.
   - digest: 제목 `, More` 끝 / `Balance of Power` / `(Podcast)` / `(Video)`.
2. **태깅(Gemini Flash, 10건 배치)** — 구조화 출력으로 §6 어휘만. 사건명은 태그 아님.
3. **리뷰어(LLM)** — 배치 결과를 스키마·환각 검증(통제어휘 밖 값·과다 티커 거름). 사용자 요청 "10건+리뷰어".
4. **임베딩(Gemini, 병렬)** — title+body(≤500자) 1회. `items.embedding` 저장(재임베딩 X).
5. **클러스터(centroid 온라인)** — §7.

## 6. 통제 어휘 (3축, 시작값·튜닝 가능)
- **tickers**: LLM 추출(예 `NVDA`,`SK하이닉스`→`000660.KS`). v1은 추출+리뷰어 검증(엄격 유니버스 검증은 후속).
- **entities**(고정): Fed, ECB, BOJ, PBOC, BOE, 한국은행, 재무부, OPEC, IMF, SEC, 백악관, … (확장 가능 고정 리스트).
- **topics**(고정 ~20): rates, inflation, bonds, fx, crypto, equities, earnings, m&a, ipo, energy/oil, tech/ai, regulation, jobs, central_bank, recession, trade/tariff, geopolitics, commodities, housing, banking.
> 어휘는 한 곳(예 `config/taxonomy.yaml`)에 정의 = **SSOT**. 코드/프롬프트는 거기서 도출.

## 7. 클러스터링 알고리즘
```
for 새 기사 i (kind=story, 임베딩 있음):
  cand = 최근 48h 내 status=open 스토리들
  best = argmax cos(vec_i, story.centroid)   # centroid = sum/count
  if best.sim ≥ 0.83:  join (member_ids+i, centroid_sum+=vec_i, count++, last_seen=now, entities∪=tags)
  else:                새 스토리(member=[i], centroid=vec_i, title=LLM(i))
주기적으로 last_seen이 24h 지난 open → close.
```
- 후보 비교는 **열린 스토리 centroid만**(수백 개여도 in-process 코사인 가벼움 — 스파이크 0.3s).
- 멤버 2+ 스토리만 타임라인 가치. 단독(singleton)은 일반 기사로 표시.

## 8. 비용 / 스케일
- 실제 신규 ~30–60건/시간(dedup 후). 임베딩 0.37s/건(순차)·병렬+Tier3면 수 초. 클러스터 0.3s.
- 임베딩·Flash 태깅 단가 미미. 결제 $0 기조 유지(Tier3 한도 내).

## 9. 보안
- **`GEMINI_API_KEY`는 백엔드 전용 비밀** — Cloud Run env / Secret Manager. `.env`(gitignore+dockerignore). **클라이언트(index.html)·커밋 금지.** (Firebase 웹 apiKey와 구분)

## 10. 테스트 전략 (Docker-only)
- 선필터·클러스터링(centroid/임계/시간창)·태그 스키마 = **순수 로직 → 단위 테스트**(임베딩·LLM은 모킹/고정 벡터).
- Store 확장(enrichment 쓰기·stories·get_open_stories)은 mock-firestore + sqlite로 Protocol 테스트.
- 실 Gemini/Firestore는 라이브 스모크(소량)로 분리.

## 11. Store Protocol 확장 (구현 계획에서 상세)
신규: 기사 enrichment 저장(`kind/tags/embedding/story_id`+processed), `get_open_stories(window)`, `create_story`/`append_to_story`(centroid 증분). sqlite/firestore 양쪽 구현 + 테스트.

## 12. 롤아웃 (각 단계 독립 검증)
1. 통제어휘(`config/taxonomy.yaml`) + 선필터(kind) — 로직·테스트.
2. Store 확장 + stories 모델 — TDD(mock/sqlite).
3. 태깅(Gemini Flash)+리뷰어 — 모킹 테스트 + 라이브 소량.
4. 임베딩 연결(Tier3 키) — 라이브 소량.
5. 클러스터(centroid) — 고정벡터 테스트 + 라이브.
6. Processor Job 컨테이너 + Cloud Scheduler #2 배포.
7. (Phase 2) 사이트 타임라인 UI.

> 구현은 SDD로, **각 서브에이전트에 `coding-principles` + `solved_problems`의 gotchas 주입**(`docs/subagent-context.md`).

<!-- spec-review: passed lenses=0 date=2026-06-28 note=grandfathered — pre-existing shipped doc (2026-06-12~14), predates review gate; not re-reviewed this session -->

<!-- spec-review: passed lenses=3 date=2026-06-28 -->
