# Phase 4 — 스토리 리포트 리더 (헤드라인·리드·아티클 생성 + 발생시각 + 전일대비 + UI) — 설계

_작성: 2026-06-29 · 상태: 설계(검토중) · 성격: 분석 레이어 Phase 4(UI + 생성 백엔드). 상위 설계: `docs/analysis-design.md` §8 · 작업 순서: `docs/roadmap.md` · 계약: `docs/firestore-contract.md` · 토대: Phase 1 렌즈 · Phase 2 델타(`developments[].delta_time`) · Phase 3 score(`risk`/`impact`). 디자인 확정 목업: `docs/superpowers/specs/assets/phase4-report-mockup.html`_

## 1. 목표 / 범위
**스토리를 "기사 더미"가 아니라 합성된 보고서로 보여준다.** 기사는 메인이 아니라 타임라인 조각의 *부품(출처)*으로 강등하고, 각 섹션(렌즈)별 메인 스토리를 골라 **헤드라인 + 리드 + bullet 합성 아티클 + 발생/보도 2-타임스탬프 타임라인**으로 렌더한다.

사용자 확정(2026-06-29, 목업 반복 5회):
- **네비** = 가로 셀렉터(디폴트), 섹션별 메인 스토리 1장, `delta×impact` 순.
- **스토리 = 보고서**: `headline`(delta×impact 반영) + `lead`(now-brief 1~2문장) + `article`(조금 더 긴 bullet 합성, 추론 포함).
- **시간 2축**: `발생`(사건 실제 시각, 추출) vs `보도`(기사 시각). 둘 다 표기 + `보도순/발생순` 정렬 토글. **지연막대(방식 C)는 폐기**.
- **번역/원문 토글**: 번역=AI 한국어 합성 / 원문=원본 기사 펼침(원어 + `language` 태그). v1 추가 번역 콜 없음.
- **impact/risk에 전일대비 delta**(`▲/▼`) + 신규 스토리 `NEW`.
- **스토리는 섹션 비배타**(멀티렌즈 → 여러 섹션 동시 등장). **기사는 스토리에 단일 멤버십**(현 클러스터링 유지, 소프트 멤버십은 후속).
- **팔레트** = Warm Light(밝은 따뜻 배경, 파랑→테라코타).

**포함**: ① 생성 패스 `run_enrich --mode article`(새 모듈 `enrich/article.py`) — `headline`/`lead`/`article`/`developments[].event_time` LLM 1콜 + 결정론 validator + fail-soft. ② 전일대비 reference 스냅샷(`risk_ref`/`impact_ref`/`score_ref_at`) — 생성 패스가 유지(24h 롤링). ③ `delta×impact` 셀렉터 정렬(UI 도출, 새 점수 없음). ④ store 메서드(`get_stories_for_article`/`save_story_article`) + `ports.py` Protocol. ⑤ `web/index.html` 스토리 탭 재설계(셀렉터·보고서·2축 타임라인·토글·delta 배지·Warm Light). ⑥ `firestore-contract.md`/`analysis-design.md §8` 갱신.

**제외(후속)**: 영문 본문 → 한국어 *진짜* 번역 패스(v1은 AI 합성이 한국어, 원문은 원어 노출). · 기사 멀티-스토리 소프트 멤버십. · 렌즈 risk 집계 정렬 렌더의 고급화(v1은 섹션=렌즈, risk순). · 응용 레이어(아키타입). · 0~3 스케일·게이트 캘리브레이션(Phase 3 후속과 공유, §15 🔴).

## 2. 핵심 제약 (Phase 1~3 컨벤션 상속)
- **뉴스-온리·advisory·$0 목표**: 가격 데이터 없음. 생성물은 LLM advisory. 비용은 `$0 유지가 목표`(roadmap §1), `$3/일`은 상한. flash-lite 1콜/스토리, **incremental 게이트**(`count > articled_count`)가 콜 수를 통제 — 새 멤버 붙은 스토리만 재생성.
- **비파괴(additive·merge only)**: 생성 패스는 *자기 필드만* `set(..., merge=True)`로 쓴다. raw/cluster/summary/lenses/score 필드와 cross-field batch·read-modify-write 없음(요약·렌즈·점수 패스와 동일 패턴). 부분 실패가 기존 필드를 고아화할 경로가 구조적으로 없다.
- **fail-soft(스토리 단위)**: LLM 장애·빈 결과·validator 실패 → 그 스토리만 스킵(다음 런 재시도), 패스 안 죽임. LLMError·예기치 못한 예외 모두 로그(코드 버그는 traceback — FAIL-LOUD).
- **결정론 우선 검증**: LLM 출력은 결정론 validator가 먼저 거른다(필수키·타입·길이 상한·매직넘버 금지). 품질은 후속 캘리브레이션.
- **UI fail-soft 강등(불변식)**: 생성 필드(`headline`/`lead`/`article`/`event_time`/`risk_ref`)가 없어도 UI는 폴백으로 정상 렌더한다 — `headline`→`title`, `lead`→`summary`, `article`→없으면 생략, `event_time`→`time`(=보도), delta 없으면 `NEW`도 배지도 미표시. `stories` 비면 빈 목록. (Phase 3 `firestore-contract.md` §불변식 계승.)

## 3. 데이터 모델 — `stories` 추가 필드 (additive·비파괴)
생성 패스(`--mode article`)가 write, UI가 read. 모두 결측 시 §2 폴백.

| 필드 | 타입 | 의미 | 소유 |
|---|---|---|---|
| `headline` | str | 표시 헤드라인 — `delta×impact` 반영(가장 신선한 전개를 전면, §7). `title`(클러스터 캐노니컬, 요약 패스 소유)과 별개. UI 폴백 `title`. | article 패스 |
| `lead` | str | now-brief 1~2문장(핵심+왜 중요). UI 폴백 `summary`. | article 패스 |
| `article` | list[str] | bullet 합성(조금 더 긴, 추론 포함). 마지막 bullet은 "변수/리스크" 허용. `MAX_BULLETS` 상한. UI 폴백: 없으면 생략. | article 패스 |
| `articled_count` | int | 이 멤버수까지 생성함(incremental 가드 — `summary_count`/`scored_count`/`lensed_count` 컨벤션). | article 패스 |
| `articled_at` | datetime | 생성 시각. | article 패스 |
| `risk_ref`·`impact_ref` | int 0~3 | 전일대비 기준 스냅샷(24h 롤링, §6). delta = `risk - risk_ref`. | article 패스 |
| `score_ref_at` | datetime | 위 스냅샷을 마지막 갱신한 시각. | article 패스 |
| `developments[].event_time` | datetime\|null | 그 전개의 **사건 실제 시각**(추출, §5). null이면 UI가 `time`(보도)로 폴백. | article 패스(by index merge) |

- `developments[]`의 기존 키(`text`·`time`·`delta_time`·`source_count`)는 **요약 패스 소유** — article 패스는 `event_time`만 *인덱스로 병합*(전체 배열 덮어쓰기 아님, §4). `time`=보도(published_at), `event_time`=발생(추출).

## 4. 생성 패스 `run_enrich --mode article` (신규 `enrich/article.py`)
**왜 별도 패스(요약 확장 아님)**: `headline`이 `delta×impact`를 반영하려면 `impact`(Phase 3 score)가 있어야 하는데, score는 요약 *이후* 실행된다(scorer 입력=요약 산출). 따라서 생성은 **score 다음 마지막 패스**로 두어 `delta_time`(요약/델타)·`impact`(score) 모두 확보. 순서: `cluster → summary(+delta_time) → score(risk/impact) → article`.

```
스토리(get_stories_for_article: open·last_seen>=cutoff·count>articled_count)         (incremental)
  ↓ 입력 구성 — title·summary·developments(text·time·delta_time)·risk·impact·lenses + 멤버 발췌(grounding)
  ↓ LLM 1콜(flash-lite) → {headline, lead, article[], events:[{dev_idx,event_time}]}
  ↓ 결정론 validator — 필수키·타입·길이상한·event_time ISO 파싱(실패→null), dev_idx 범위 밖 드롭
  ↓ event_time을 developments에 인덱스로 병합(요약이 만든 배열 위에 event_time만; 길이/순서 불일치 시 무시)
  ↓ 전일대비 ref 갱신(§6)
출력: stories.{headline, lead, article, developments(+event_time), risk_ref, impact_ref,
              score_ref_at, articled_count, articled_at}   (merge·비파괴)
```
- **헤드라인 grounding(§7)**: 프롬프트가 "가장 최신(`delta_time` 최대) 전개를 전면에 둔 헤드라인"을 요구. `impact` 결측(미채점 신규)이면 delta-only로 폴백(헤드라인=최신 전개, fail-soft).
- **입력 상한**: 멤버 발췌는 요약 패스와 동일하게 최신 `ARTICLE_MAX_MEMBERS`건·발췌 길이 통제(토큰). 입력이 비면(summary·developments·members 모두 없음) → None(스킵).
- **fail-soft**: 위 §2. validator None → 스킵.

## 5. 발생시각(`event_time`) 추출 — best-effort, 폴백 안전
- LLM이 각 전개에 대해 **사건이 실제 일어난 시각**을 추출(본문의 "어제", "현지시각 09:30", 실적발표 시각 등). 출력 `events:[{dev_idx, event_time(ISO8601|null)}]`.
- **결정론 검증**: ISO 파싱 성공 + (선택) `time`±N일 범위 sanity → 통과, 아니면 **null**(드롭). `dev_idx`는 `0<=idx<len(developments)`만.
- **폴백 불변식**: `event_time` null → UI는 `time`(보도시각)으로 표기하고 "발생" 칩을 흐리게/생략. **즉 추출 실패가 화면을 깨지 않는다("있으면 보너스", 사용자 합의).**
- v1 비용: 별도 콜 아님(아티클 콜에 동봉). 정확도는 후속 캘리브레이션(§15).

## 6. 전일대비 delta — 24h 롤링 reference 스냅샷
score 패스를 건드리지 않고(안정성), **article 패스가 ref를 유지**한다(article은 매 런 `risk`/`impact`를 읽음).
- `get_stories_for_article`가 현재 `risk`·`impact`·`risk_ref`·`impact_ref`·`score_ref_at`·`first_seen`을 반환.
- 갱신 규칙(결정론): `score_ref_at` 없거나 now−`score_ref_at` ≥ `REF_WINDOW`(기본 24h) → **현재 `risk`/`impact`를 ref로 스냅샷**, `score_ref_at=now`. 아니면 ref 유지. (10분 주기 패스가 ref를 매번 덮어쓰지 않게 — 하루 1회만 전진.)
- UI: `delta_risk = risk - risk_ref`(있을 때만), `▲n`/`▼n`/(0이면 미표시). **NEW** = `risk_ref` 없음 **또는** `first_seen`이 `REF_WINDOW` 이내(전일 비교 불가). 매직넘버 금지(`REF_WINDOW` 상수).
- 정직: 이건 "전일"의 *근사*(24h-전 스냅샷)다. 정확한 캘린더-일 경계·tz는 후속(YAGNI). 사용자 합의 "시간변화 측정 가능".

## 7. `delta×impact` — 정렬축 + 헤드라인 규칙
- **셀렉터 정렬(UI 도출, 새 점수 없음)**: 스토리 정렬키 = `impact`(0~3) 가중 × `delta` 신선도. `delta` 신선도 = 가장 최근 `delta_time`(없으면 `last_seen`)의 recency(예: `exp(-age/τ)` 또는 단순 역순). **구현은 UI 결정론 함수**(SSOT=하나의 `storyRank(s)` 순수함수, 마커 슬라이스 테스트). 동점은 `last_seen` desc.
- **헤드라인 텍스트**: 가장 신선한 전개(`max delta_time`)를 전면에, `impact`가 클수록 단정적 톤. LLM이 작성(프롬프트 규칙), 결정론은 형식만 검증.
- **섹션 = 렌즈**: 셀렉터는 렌즈별 그룹의 메인 스토리(그 렌즈 내 `delta×impact` 최댓값). 스토리가 여러 렌즈면 여러 섹션에 등장(비배타). 렌즈 순서 = 렌즈 risk 집계(소속 열린 스토리 risk 집계, analysis-design §7) desc → v1은 단순화(섹션 내 최대 risk).

## 8. 번역/원문 (v1, 추가 콜 0)
- **번역(기본)**: AI 합성(headline/lead/article/development text)은 **항상 한국어 생성**(프롬프트 한국어). 화면 기본값.
- **원문**: 토글 시 각 전개의 **원본 멤버 기사**(원어 title/body)를 펼친다. 출처칩에 `language`(en/ko…) 표기, ko 아니면 "(원문)" 라벨. (한국 소스 멤버는 원문=한국어.)
- **데이터**: 신규 필드 없음 — 멤버 `title`/`body`/`language`(기존) 사용. UI 상태(번역/원문)만.
- **후속**: 영문 멤버 본문의 한국어 번역 필드 생성(별도 패스·비용) — v1 제외.

## 9. UI 재설계 — `web/index.html` 스토리 탭 (Warm Light)
확정 목업(`assets/phase4-report-mockup.html`)이 시각 기준. 기존 피드 탭·라우팅·소스색·`groupItemsByDevelopment`·`pickDisplayItems` 순수함수는 **보존**(회귀 금지).
- **팔레트**: Warm Light(`--bg:#fdfcf8` 등, 파랑→테라코타). 기존 `:root` 토큰 교체(피드 탭도 함께 따뜻하게 — 일관).
- **셀렉터**(가로): 섹션별 메인 스토리 카드 — 렌즈 라벨·건수·`shead`·impact/risk 점 + delta 배지/NEW. 기존 `.strip`/`.scard` 진화(가로 스크롤·snav 재사용). 정렬 = `storyRank`(§7).
- **보고서**(선택 스토리): `headline`(폴백 title) → meta(최신 relTime·발생폭·impact/risk+delta) → **번역/원문 토글** → 합성 박스(`lead` 굵게 + `article` bullet; 보라 없음, 따뜻 크림) → **전개 타임라인**(`보도순/발생순` 토글; 각 노드 `발생`(event_time, 폴백 time)·`보도`(time)·신선/지연 배지·전개텍스트·출처칩=부품). 기존 `renderDetail`/`groupItemsByDevelopment` 확장(노드에 2-타임스탬프·event_time).
- **순수함수(테스트 슬라이스)**: `storyRank(s)`(§7), `deltaBadge(cur, ref)`→{dir,n}|NEW|null, `nodeTimes(dev)`→{event, report, lagLabel}. `=== STORIES-LOGIC-START/END ===` 마커 안에 추가(node test가 검증, DOM/외부스코프 금지).
- **드리프트 가드**: UI가 읽는 필드명(`headline`/`lead`/`article`/`risk`/`impact`/`risk_ref`/`developments[].event_time`)을 `firestore-contract.md`에 등록 — 이름이 조용히 어긋나면 빈/폴백으로 강등(계약 테스트).

## 10. Store 계약 (store 추상화 준수 — `store.db` 직접접근 금지, `get_all` 배치)
- `get_stories_for_article(cutoff) -> list[dict]`: `status=open`·`last_seen>=cutoff`·`count>articled_count`(incremental). 반환 `{id, title, count, lenses, summary, developments, risk, impact, risk_ref, impact_ref, score_ref_at, first_seen}`(생성·헤드라인·delta·ref 갱신에 필요한 필드 — 추가 읽기 0). `get_stories_for_scoring` 미러.
- `save_story_article(story_id, *, headline, lead, article, developments, risk_ref, impact_ref, score_ref_at, count, now) -> None`: 위 필드 + `articled_count=count` + `articled_at=now` merge(비파괴, read 없음, cross-field batch 없음). `save_story_score` 미러. `developments`는 event_time 병합된 전체 배열(요약이 만든 키 보존 — §3·§4).
- 멤버 발췌는 기존 `get_story_members` 재사용(신규 멤버 읽기 메서드 금지 — SSOT).
- `ports.py` `Store` Protocol에 두 메서드 시그니처 추가.

## 11. Firestore 계약 (`firestore-contract.md` §stories 추가)
§3 표의 필드를 additive·merge로 추가. writer=newsstore(article 패스), reader=web UI. 드리프트 가드·fail-soft 강등 불변식(§2·§9)을 계약 테스트로 강제. `developments[].event_time`은 `delta_time`과 같은 "추가 타임스탬프(비파괴, 레거시 폴백)" 패턴.

## 12. 에러처리 / 드리프트 (FAIL-LOUD)
- LLM None/retry/timeout = 기존 `GeminiClient.generate_json` 재사용. 결정론 validator 먼저(필수키 headline/lead/article + 타입·길이 상한). 실패→스토리 스킵+로그.
- **event_time 드리프트**: ISO 파싱 실패·`dev_idx` 범위 밖 → 그 항목만 null/드롭(전체 전개 보존). 매직넘버 금지(`REF_WINDOW`·`MAX_BULLETS`·`ARTICLE_MAX_MEMBERS` 상수).
- **incremental 멱등**: `count>articled_count` 가드로 변화 없으면 스킵(재생성·비용 차단). 렌즈·요약·점수 패스와 동일.
- **developments 병합 레이스**: 요약 패스가 article 이후 developments를 갱신하면 event_time이 일시 소실 → 다음 article 런(count 변화 시)에 복구. additive·fail-soft, 손상 없음.

## 13. 비용
flash-lite 1콜/스토리(아티클+이벤트추출 동봉). incremental 게이트로 *새 멤버 붙은* 스토리만. 점수 패스와 동급 콜 수 → 하루 예산($0 목표, $3 상한) 내. 셀렉터 정렬·delta·번역토글은 **LLM 0콜**(UI 도출). Now Brief 글로벌 합성은 **제거**(사용자: per-story 리드로 대체) → analysis-design §8의 글로벌 Now Brief 콜도 불필요.

## 14. 테스트 (TDD)
- **validator 단위**(fake): 필수키(headline/lead/article) 결측·비-str·article 비-list → None. 정상 → 길이상한·`MAX_BULLETS` 적용. event: dev_idx 범위 밖 드롭, event_time 비-ISO → null. 매직넘버 불변식.
- **ref 스냅샷 단위**: `score_ref_at` 없음 → 스냅샷+NEW 경로. <24h → 유지. ≥24h → 전진. `deltaBadge` 순수함수(▲/▼/0/NEW).
- **article_story 단위**(fake LLM): 입력 폴백(summary/dev 우선 → 멤버 폴백 → 빈 입력 None). impact 결측 → delta-only 헤드라인 경로. event_time 병합(인덱스 정합/불일치). LLM 장애 → None(fail-soft).
- **run_article_pass 통합(에뮬레이터)**: ① 생성·저장 라운드트립 ② incremental(둘째 런 스킵, 새 멤버 후 재생성) ③ 비파괴(merge가 summary/lenses/score/cluster 보존) ④ fail-soft(LLM 장애 스토리만 스킵) ⑤ event_time이 developments 기존 키 보존.
- **UI 순수함수(node, 마커 슬라이스)**: `storyRank`(impact×delta 정렬·동점 last_seen), `deltaBadge`, `nodeTimes`(event_time 폴백 time). 기존 `groupItemsByDevelopment`/`pickDisplayItems` 회귀.
- **계약(에뮬레이터)**: `save_story_article`→`get_stories_for_article` 라운드트립 + 비파괴 + incremental 필터 + 드리프트(필드명) 가드.
- 실행: `MSYS_NO_PATHCONV=1 docker compose run --rm test` → FAIL=0. UI: node 순수함수 테스트.

## 15. 범위 밖 / 후속 (Phase 표시)
- **🔴 캘리브레이션(사용자 결정, provisional 동작)**: `article` bullet 톤·길이, 헤드라인 `delta×impact` 가중 τ, `REF_WINDOW`(24h), event_time sanity 범위, 0~3 스케일 의미(Phase 3와 공유). 라이브 데이터로 조정.
- **영문→한국어 번역 패스**(별도 비용) · **기사 멀티-스토리 소프트 멤버십** · **렌즈 risk 집계 정렬 고급화** · **응용 레이어(아키타입)**.
- **운영**: 새 Cloud Run Job `newsstore-article`(#?) + 스케줄러. 렌즈/스코어 10분 스케줄러(사용자 동의)와 함께 배선(operations.md). 이미지 재빌드 시 `--mode article` 포함.

## 16. 3렌즈 리뷰 (2026-06-29)
_독립 리뷰어(grounding·consistency·adversarial) 디스패치 후 반영 — 아래 채움._

<!-- spec-review: pending -->
