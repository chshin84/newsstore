# Phase 4 — 스토리 리포트 리더 (헤드라인·리드·아티클 생성 + 발생시각 + 전일대비 + UI) — 설계

_작성: 2026-06-29 · 상태: 설계(3렌즈 리뷰 반영) · 성격: 분석 레이어 Phase 4(UI + 생성 백엔드). 상위: `docs/analysis-design.md` §8 · 순서: `docs/roadmap.md` · 계약: `docs/firestore-contract.md` · 토대: Phase 1 렌즈 · Phase 2 델타(`developments[].delta_time`) · Phase 3 score(`risk`/`impact`). 확정 목업: `docs/superpowers/specs/assets/phase4-report-mockup.html`_

## 1. 목표 / 범위
**스토리를 "기사 더미"가 아니라 합성된 보고서로 보여준다.** 기사는 메인이 아니라 타임라인 조각의 *부품(출처)*. 섹션(렌즈)별 메인 스토리를 골라 **헤드라인 + 리드 + bullet 합성 아티클 + 발생/보도 2-타임스탬프 타임라인**으로 렌더.

사용자 확정(2026-06-29, 목업 5회 반복): 가로 셀렉터(디폴트)·섹션별 메인 스토리·`delta×impact` 순 / 스토리=보고서(`headline`+`lead`+bullet `article`) / 시간 2축(발생 vs 보도) + 정렬 토글, 지연막대 폐기 / 번역·원문 토글 / impact·risk **전일대비**(▲▼)+신규 `NEW` / 스토리는 섹션 비배타·기사는 스토리 단일멤버십 / Warm Light 팔레트.

**포함**: ① **summary 패스 확장** — 같은 LLM 콜에서 `developments[].event_time`(발생시각) 추출(summary가 developments 단독 소유, §5). ② **생성 패스 `run_enrich --mode article`**(새 모듈 `enrich/article.py`) — `headline`/`lead`/`article` + 전일대비 ref(`risk_ref`/`impact_ref`/`score_ref_at`) LLM 1콜 + 결정론 validator + fail-soft. **article 패스는 `developments`를 절대 쓰지 않는다(자기 필드만 merge — 비파괴 by construction, §4).** ③ store 메서드(`get_stories_for_article`/`save_story_article`) + `ports.py` Protocol. ④ `web/index.html` 스토리 탭 재설계(셀렉터·보고서·2축 타임라인·토글·delta 배지·Warm Light) — UI는 `stories` 문서를 **클라가 직접 read**(신규 read 메서드 불요, §9). ⑤ `firestore-contract.md`/`analysis-design.md §8` 갱신.

**제외(후속)**: 영문 본문 *진짜* 한국어 번역 패스(v1은 AI 합성이 한국어, 원문은 원어 노출) · 기사 멀티-스토리 소프트 멤버십 · 렌즈 risk 집계 정렬 고급화 · 응용 레이어(아키타입) · 0~3 스케일·게이트 캘리브레이션(Phase 3 후속과 공유, §15 🔴).

> **신규 메서드/모드/모듈은 본 spec이 *처방*하는 것**(`--mode article`·`save_story_article`·`get_stories_for_article`·`enrich/article.py`) — 현재 코드에 없음이 정상(plan이 구현). Phase 3에서 `get_stories_for_scoring`이 동일하게 처방→구현된 선례.

## 2. 핵심 제약 (Phase 1~3 컨벤션 상속)
- **뉴스-온리·advisory·$0 목표**: 가격 데이터 없음, 생성물=LLM advisory. 비용 $0 유지 목표(roadmap 도입부 — 무료 RSS + Gemini Flash 무료 한도), `$3/일`은 상한. flash-lite 1콜/스토리, **incremental 게이트**(`count > articled_count`)가 콜 수 통제.
- **비파괴 by construction(핵심 — adversarial critical 반영)**: 각 패스는 **자기 소유 필드만** `set(..., merge=True)`로 쓴다 — read-modify-write·cross-field batch 없음. 특히 **공유 배열 `developments`는 summary 패스 단독 writer**. article 패스는 `developments`를 *읽기만* 하고 자기 필드(`headline`/`lead`/`article`/ref/`articled_*`)만 쓴다. → article·summary 동시 실행이 서로의 필드를 고아화·되돌릴 경로가 *구조적으로 없다*(save_story_score와 동일 안전성).
- **fail-soft(스토리 단위)**: LLM 장애·빈 결과·validator 실패 → 그 스토리만 스킵(다음 런 재시도), 패스 안 죽임. 예외는 로그(코드 버그=traceback, FAIL-LOUD).
- **결정론 우선 검증**: LLM 출력은 결정론 validator가 먼저 거른다(필수키·타입·길이상한·매직넘버 금지).
- **UI fail-soft 강등(불변식)**: 생성 필드 결측에도 UI 정상 렌더 — `headline`→`title`, `lead`→`summary`, `article`→생략, `event_time`→`time`(보도), `risk_ref` 결측→delta 화살표 생략(배지는 점만), `NEW`는 `first_seen`만으로 판정(ref 무관). `stories` 비면 빈 목록.

## 3. 데이터 모델 — `stories` 추가 필드 (additive·비파괴)

| 필드 | 타입 | 의미 | writer |
|---|---|---|---|
| `developments[].event_time` | datetime\|null | 그 전개의 **사건 실제 시각**(추출, §5). null→UI가 `time`(보도)로 폴백. | **summary 패스**(developments 단독 소유) |
| `headline` | str | 표시 헤드라인 — **가장 최신 전개(max `delta_time`) 주도**(§7). `title`(클러스터 캐노니컬)과 별개. UI 폴백 `title`. | article 패스 |
| `lead` | str | now-brief 1~2문장. UI 폴백 `summary`. | article 패스 |
| `article` | list[str] | bullet 합성(조금 더 긴, 추론 포함). 마지막 bullet에 "변수/리스크" 허용. `MAX_BULLETS` 상한. 없으면 UI 생략. | article 패스 |
| `risk_ref`·`impact_ref` | int 0~3 | 전일대비 기준 스냅샷(24h 롤링, §6). | article 패스 |
| `score_ref_at` | datetime | 위 스냅샷 갱신 시각. | article 패스 |
| `articled_count` | int | 이 멤버수까지 생성함(incremental 가드 — `summary_count`/`scored_count`/`lensed_count` 컨벤션 동일). | article 패스 |
| `articled_at` | datetime | 생성 시각. | article 패스 |

- `developments[]` 기존 키(`text`·`time`·`delta_time`·`source_count`)는 summary 소유. **`event_time`도 summary가 같은 콜에서 채운다** → developments는 *단일 writer*, 인덱스 병합·레이스 없음(adversarial #2/#4 해소). `time`=보도(published_at), `event_time`=발생(추출, nullable).
- **상수(provisional, §15 캘리브레이션)**: `REF_WINDOW=24h` · `MAX_BULLETS=6` · `ARTICLE_MAX_MEMBERS=40` · `IMPACT_PRIOR=1`(미채점 정렬 prior, §7). 전부 모듈 상수(매직넘버 금지).

## 4. 생성 패스 `run_enrich --mode article` (신규 `enrich/article.py`)
**순서**: `cluster → summary(+delta_time +event_time) → score(risk/impact) → article`. article을 마지막에 둬 `delta_time`·`event_time`(summary)·`impact`(score)을 모두 확보. (`developments`는 안 쓰고 읽기만 → 순서 의존은 grounding용일 뿐, 늦어도 fail-soft.)
```
스토리(get_stories_for_article: open·last_seen>=cutoff·count>articled_count)            (incremental)
  ↓ 입력 — title·summary·developments(text·time·delta_time·event_time)·risk·impact·lenses + 멤버 발췌(grounding, 최신 ARTICLE_MAX_MEMBERS)
  ↓ LLM 1콜(flash-lite) → {headline, lead, article[]}
  ↓ 결정론 validator — 필수키 headline/lead/article(list[str]) · 길이상한 · MAX_BULLETS
  ↓ 전일대비 ref 갱신(§6, 자기 필드)
출력(merge·비파괴, developments 미포함): stories.{headline, lead, article, risk_ref, impact_ref, score_ref_at, articled_count, articled_at}
```
- **헤드라인 grounding(§7)**: 프롬프트는 "가장 최신(`max delta_time`) 전개를 전면에 둔 헤드라인". **impact는 헤드라인 *텍스트* 입력이 아님** → impact 변동(재채점)이 헤드라인을 stale로 만들지 않음(adversarial #2 해소). impact는 UI 정렬·배지에서만(§7, 라이브).
- 입력이 비면(summary·developments·members 모두 없음) → None(스킵). fail-soft.

## 5. 발생시각(`event_time`) — summary 패스가 추출(단일 writer)
- summary 패스의 기존 LLM 콜에 **각 전개의 사건 실제 시각** 추출을 추가(`build_summary_prompt`/`validate_summary`/`summarize_story` 확장). summary는 이미 멤버 본문을 읽으므로 추가 콜 없음.
- **결정론 검증**: ISO8601 파싱 성공 + `time`±`EVENT_SANITY_DAYS` 범위 sanity → 통과, 아니면 **null**. developments에 `event_time` 키로 박아 저장(summary가 배열 전체를 쓰므로 일관, 별도 병합 없음).
- **폴백 불변식**: null → UI는 `time`(보도)로 표기, "발생" 칩 흐리게/생략. 추출 실패가 화면을 깨지 않음("있으면 보너스", 사용자 합의).

## 6. 전일대비 delta — best-effort 24h 롤링 ref (article 패스 자기 필드)
- `get_stories_for_article`가 현재 `risk`·`impact`·`risk_ref`·`impact_ref`·`score_ref_at`·`first_seen` 반환. article 패스가 ref를 **자기 필드로** 유지(developments 같은 공유 배열 아님 → 비파괴 안전).
- 갱신(결정론): `score_ref_at` 없거나 now−`score_ref_at` ≥ `REF_WINDOW` → 현재 `risk`/`impact`를 ref로 스냅샷, `score_ref_at=now`. 아니면 유지(10분 패스가 매번 안 덮음).
- **UI(라이브 도출, LLM 0콜)**: `NEW` = `first_seen`이 `REF_WINDOW` 이내 — **ref 무관, 순수 first_seen**(adversarial #3 "영원히 NEW" 해소). `delta` = `risk−risk_ref`(ref 있고 `score_ref_at` 신선할 때만 `▲n`/`▼n`, 아니면 **화살표 생략**=graceful degrade). 0이면 미표시.
- 정직: "전일"의 *근사*(24h-전 스냅샷). article이 24h+ 안 돌면 화살표가 낡거나 없음 — best-effort, 깨지지 않음. 정확 캘린더-일·tz는 후속(YAGNI).

## 7. `delta×impact` — 정렬축 + 헤드라인 (UI 라이브 도출)
- **셀렉터 정렬 `storyRank(s)`(UI 순수함수, SSOT 하나)**: `rank = impactWeight × deltaFreshness`. `impactWeight` = `(impact ?? IMPACT_PRIOR)`(미채점 결측 → 0 아닌 중립 prior → **하위 매몰 방지**, adversarial #5 해소). `deltaFreshness` = 가장 최근 `delta_time`(없으면 `last_seen`)의 recency(단조감소). 동점 → `last_seen` desc. **impact는 라이브 필드** → 재채점 즉시 정렬 반영(stale 없음).
- **헤드라인 텍스트**: 가장 신선한 전개 주도(§4) — delta 기반, impact는 텍스트에 안 들어감(정렬·배지 전용). → 점수 변동이 헤드라인을 굳히지 않음.
- **섹션 = 렌즈**: 셀렉터는 렌즈별 그룹의 메인 스토리(그 렌즈 내 `storyRank` 최댓값). 멀티렌즈 스토리는 여러 섹션 등장(비배타). 렌즈 순서 = 섹션 내 최대 risk(v1 단순화; 집계 고급화는 후속).

## 8. 번역/원문 (v1, 추가 콜 0)
- **번역(기본)**: AI 합성(headline/lead/article/development text) **항상 한국어 생성**. 화면 기본값.
- **원문**: 토글 시 각 전개의 **원본 멤버 기사**(원어 title/body) 펼침. 출처칩에 `language` 표기, ko 아니면 "(원문)". 한국 소스 멤버는 원문=한국어.
- **데이터**: 신규 필드 없음 — 멤버 `title`/`body`/`language`(기존). UI 상태만. 영문 본문의 한국어 번역 필드는 후속.

## 9. UI 재설계 — `web/index.html` 스토리 탭 (Warm Light)
확정 목업(`assets/phase4-report-mockup.html`)이 시각 기준. 기존 피드 탭·라우팅·소스색·`groupItemsByDevelopment`·`pickDisplayItems`는 **보존**(회귀 금지).
- **UI read 경로(consistency major 반영)**: 스토리는 **클라이언트가 `stories` 컬렉션을 직접 read**(기존 `loadStories`의 `d.data()` 스프레드) → 신규 필드(`headline`/`lead`/`article`/`risk`/`impact`/`risk_ref`/`developments[].event_time`)가 **자동 포함**. **별도 store read 메서드 불요**(`get_stories_for_article`는 *백엔드 생성 입력 전용*).
- **팔레트**: Warm Light(`--bg:#fdfcf8` 등, 파랑→테라코타). 기존 `:root` 토큰 교체(피드 탭도 함께).
- **셀렉터**(가로): 섹션별 메인 스토리 카드(렌즈·건수·`shead`·impact/risk 점 + delta 배지/NEW). 기존 `.strip`/`.scard`/snav 진화. 정렬 `storyRank`.
- **보고서**(선택): `headline`(폴백 title) → meta(최신 relTime·발생폭·impact/risk+delta) → **번역/원문 토글** → 합성 박스(`lead` 굵게 + `article` bullet, Warm 크림·보라 없음) → **전개 타임라인**(`보도순/발생순` 토글; 노드마다 `발생`(event_time 폴백 time)·`보도`(time)·신선/지연 배지·전개텍스트·출처칩=부품). 기존 `renderDetail` 확장.
- **순수함수(마커 슬라이스 테스트, DOM/외부스코프 금지)**: `storyRank(s)`(§7) · `deltaBadge(cur, ref, refAt, now)`→{dir,n}|null · `isNew(firstSeen, now)`→bool · `nodeTimes(dev)`→{event, report, lagLabel}. `=== STORIES-LOGIC-START/END ===` 안에 추가.
- **드리프트 가드**: UI가 읽는 필드명을 `firestore-contract.md`에 등록 — 어긋나면 폴백 강등(계약 테스트).

## 10. Store 계약 (store 추상화 — `store.db` 직접접근 금지, `get_all` 배치)
- `get_stories_for_article(cutoff) -> list[dict]`(백엔드 전용): `status=open`·`last_seen>=cutoff`·`count>articled_count`. 반환 `{id, title, count, lenses, summary, developments, risk, impact, risk_ref, impact_ref, score_ref_at, first_seen}`(생성·헤드라인·ref 갱신에 필요 — 추가 read 0). `get_stories_for_scoring` 미러.
- `save_story_article(story_id, *, headline, lead, article, risk_ref, impact_ref, score_ref_at, count, now) -> None`: 위 필드 + `articled_count=count` + `articled_at=now` merge. **`developments` 파라미터 없음**(절대 안 씀 — §2·§4 비파괴). `save_story_score` 미러.
- event_time은 summary 패스가 기존 `save_story_summary`(developments 포함)로 저장 — **신규 store 메서드 불요**(SSOT). `summarizer`/`validate_summary`만 확장.
- 멤버 발췌는 기존 `get_story_members` 재사용.
- `ports.py` `Store` Protocol에 `get_stories_for_article`/`save_story_article` 추가.

## 11. Firestore 계약 (`firestore-contract.md` §stories 추가)
§3 표 필드를 additive·merge 추가. writer=newsstore(summary: event_time / article: 나머지), reader=web UI(클라 직접 read). 드리프트 가드·fail-soft 강등 불변식(§2·§9)을 계약 테스트로 강제. `developments[].event_time`은 `delta_time`과 같은 "추가 타임스탬프(비파괴, 레거시 폴백)" 패턴.

## 12. 에러처리 / 드리프트 (FAIL-LOUD)
- LLM None/retry/timeout = 기존 `GeminiClient.generate_json` 재사용. 결정론 validator 먼저(필수키·타입·길이). 실패→스토리 스킵+로그.
- **event_time 드리프트**: ISO 파싱 실패·sanity 밖 → null(전개 보존). 매직넘버 금지(`REF_WINDOW`·`MAX_BULLETS`·`ARTICLE_MAX_MEMBERS`·`IMPACT_PRIOR`·`EVENT_SANITY_DAYS` 상수).
- **incremental 멱등**: `count>articled_count` 가드로 변화 없으면 스킵. 렌즈·요약·점수 패스 동일.
- **공유 배열 안전**: article은 `developments`를 안 쓰므로 summary와의 write 경합 없음(critical 근본 해소). summary가 event_time 포함 배열을 단독으로 쓴다.

## 13. 비용
flash-lite: summary 1콜(+event_time 동봉, 추가 콜 0) · article 1콜/스토리. 둘 다 incremental 게이트(새 멤버 스토리만). 정렬·delta·NEW·번역토글은 **UI 라이브 도출(LLM 0콜)**. 글로벌 Now Brief 합성 **제거**(per-story 리드로 대체) → analysis-design §8 글로벌 합성 콜도 불요. 하루 예산($0 목표/$3 상한) 내.

## 14. 테스트 (TDD)
- **summary 확장 단위**(fake): event_time 추출 — ISO 정상→datetime, 비-ISO/sanity 밖→null, dev별 배정. 기존 summary 회귀(title/summary/developments/delta_time 불변).
- **article validator 단위**(fake): 필수키(headline/lead/article) 결측·비-str·article 비-list→None. 정상→길이상한·`MAX_BULLETS`.
- **ref 스냅샷 단위**: `score_ref_at` 없음→스냅샷. <24h→유지. ≥24h→전진.
- **article_story 단위**(fake LLM): 입력 폴백(summary/dev→멤버→빈입력 None). **developments 미저장 확인**(save_story_article 시그니처에 developments 없음). LLM 장애→None.
- **run_article_pass 통합(에뮬레이터)**: ① 생성·저장 라운드트립 ② incremental(둘째 런 스킵, 새 멤버 후 재생성) ③ **비파괴**: article 저장이 summary/lenses/score/cluster/**developments** 보존(특히 동시성 모사 — summary가 D4 추가한 뒤 article 저장해도 D4·event_time 생존) ④ fail-soft.
- **UI 순수함수(node, 마커 슬라이스)**: `storyRank`(impact×delta, 미채점 IMPACT_PRIOR, 동점 last_seen) · `deltaBadge`(▲▼/null/ref결측) · `isNew`(first_seen) · `nodeTimes`(event_time 폴백 time). 기존 `groupItemsByDevelopment`/`pickDisplayItems` 회귀.
- **계약(에뮬레이터)**: `save_story_article`→`get_stories_for_article` 라운드트립 + 비파괴 + incremental + 드리프트(필드명).
- 실행: `MSYS_NO_PATHCONV=1 docker compose run --rm test` → FAIL=0. UI: node 순수함수.

## 15. 범위 밖 / 후속 (Phase 표시)
- **🔴 캘리브레이션(사용자 결정, provisional)**: `article` 톤·길이·`MAX_BULLETS`, 헤드라인 delta 가중, `REF_WINDOW`, `EVENT_SANITY_DAYS`, `IMPACT_PRIOR`, 0~3 의미(Phase 3 공유). 라이브로 조정.
- 영문→한국어 번역 패스 · 기사 멀티-스토리 소프트 멤버십 · 렌즈 risk 집계 고급화 · 응용 레이어.
- **운영**: 새 Cloud Run Job `newsstore-article` + 스케줄러(렌즈/스코어 10분과 함께 배선, operations.md). 이미지 재빌드 시 `--mode article` 포함. **배포는 무인 실행 제외**(회사망 SSL 워크어라운드·바깥 동작 — 사용자와).

## 16. 3렌즈 리뷰 (2026-06-29)
독립 리뷰어(grounding·consistency·adversarial, 읽기전용 서브에이전트) 디스패치 → 반영:
- **[adversarial, critical]** `developments` 배열을 article 패스가 통째로 덮어써 summary가 추가한 새 전개 손실(비파괴 위반·레이스). → **근본 해소**: `event_time` 추출을 **summary 패스로 이동**(developments 단일 writer), article은 `developments`를 *읽기만* 하고 자기 필드만 merge(save_story_article 시그니처에서 developments 제거). §2·§4·§5·§10·§14.
- **[adversarial, major]** 헤드라인 staleness(재채점 후 재생성 안 됨) → 헤드라인 텍스트를 **delta 주도**로, impact는 UI 정렬·배지(라이브)로만 분리. §4·§7.
- **[adversarial, major]** ref가 article 의존이라 "영원히 NEW"·stale → **NEW를 `first_seen`만으로** 판정(ref 무관), delta는 best-effort(ref 없으면 화살표 생략). §6.
- **[adversarial, major]** event_time 인덱스 병합 순서 어긋남 → summary 단일 writer로 **병합 자체 제거**. §5.
- **[adversarial, major]** 미채점 impact=0 정렬 매몰(콜드스타트) → `storyRank`에서 결측 impact를 `IMPACT_PRIOR`(중립)로. §7.
- **[consistency, major]** UI read 메서드 미명시 → UI는 `stories` 문서를 **클라가 직접 read**(신규 메서드 불요) 명시. §9.
- **[consistency, minor]** 병합 규칙 모호·상수값 부재 → 병합 제거 + 상수 명시(`REF_WINDOW`/`MAX_BULLETS`/`ARTICLE_MAX_MEMBERS`/`IMPACT_PRIOR`). §3.
- **[grounding, critical×3]** `--mode article`·`save_story_article`·`article.py` 미존재 → **오독**(spec이 처방하는 신규 자산, plan이 구현; Phase 3 `get_stories_for_scoring` 선례). §1 주석 명시.
- **[grounding, minor]** roadmap "§1" 인용 오류 → "도입부"로 정정. §2.

decision: **regenerate 반영 완료** — critical(비파괴)을 구조적으로 제거(공유 배열 단일 writer), major 5건 해소, grounding critical은 오독 확인. 설계 폐기 없음.

<!-- spec-review: passed lenses=3 date=2026-06-29 -->
