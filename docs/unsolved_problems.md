# 미해결 / 대기 — 열린 백로그 (unsolved_problems)

열린 이슈 + 사용자 결정 대기. **현재 상태(무엇이 됐나/라이브)는 여기 두지 않는다 — 메모리 `project-status`.** 여긴 *열린 일*만.
범례: 🔴 사용자 결정 필요 · 🟡 방향 정해짐·구현 대기 · 🔵 향후/선택.

> ⚠️ **서브에이전트(worker) 주입 금지.** 오케스트레이터/사용자용 백로그다. 격리된 worker가 받으면 🔴(결정 대기)를 "구현하라"로 오인 → 임의 구현 사고. 주입해야 하면 "참고·구현 금지" 명시 + 🔴는 사용자 승인 게이트 뒤.

## 🔴 결정 필요 (자율 구현 금지)
- **GRAY_BAND 재캘리브레이션** — 클러스터 gray-band(현 0.55~0.75)·합류 임계(sim≥0.75)가 타 코퍼스 측정값 차용. newsstore 실데이터로 골든셋 재캘리브레이션 필요.
- **score 스케일 캘리브레이션** — risk/impact 0~3의 의미·게이트 임계(MIN 멤버수)·`REF_WINDOW`·헤드라인 delta 가중·`EVENT_SANITY_DAYS`가 provisional. 라이브 분포 보고 사용자 튜닝.
- **Step-2 태그 통제 어휘 범위** — 티커 유니버스 / 엔티티(연준·ECB·BOJ·재무부·OPEC…) / 토픽(금리·인플레·채권·FX·크립토·실적·M&A·지정학…) 어디까지. "이란 전쟁" 류 *사건*은 태그 아닌 스토리(클러스터)로.
- **스토리 open/close 시간창** — 새 기사를 어느 기간 "열린 스토리"와 비교(예 24~48h), 언제 close.
- **tag 패스 거취** — `--mode tag`가 `tagger.tag_stories`(부재) 호출 → 데드경로. 제거할지, 스토리 태깅을 살릴지(별 Scheduler/주기 포함) 결정.

## 🟡 구현 대기
- **C1~C3 프로덕션 재배포** — sports kind·store 견고성·렌즈UI 코드가 main에 있으나 프로덕션 이미지 미반영. processor/web 재배포해야 라이브.
- **requirements.lock 재핀** — google-cloud-firestore·google-genai 비핀(unpinned) → 재현 빌드 불가. enrich extra 포함해 lock 재생성(httpx<1.0 등 핀 충돌 해소).
- **operations.md 런북 보강** — §E/§F가 실제 배포와 드리프트: 런북은 `newsstore-processor`/`newsstore-enrich-hourly` 생성을 기술하나 실제는 `newsstore-enricher`/`newsstore-enrich-10min`, 그리고 **lenser·scorer·article Job·Scheduler가 미기재**(실제론 6 Job+6 Scheduler 라이브). 실제 이름·모드로 정정 + 누락 패스 절차 추가. `deploy-office.ps1`도 3잡 갱신 추가.
- **잡 실패 알림** — Scheduler가 `:run` 호출 후 200만 받음 → 잡이 죽어도 초록(Fail-Loud 위반). Cloud Monitoring 알림(job 실패 카운트>0, 6잡 전부).
- **store-level 테스트 갭** — `save_story_article`/`get_stories_for_article`(Phase 4) 에뮬레이터 계약 테스트 0건. 라운드트립+비파괴+incremental 테스트 추가.
- **web 자동갱신 드리프트** — 제목이 "5분마다 갱신" 표기하나 onSnapshot/타이머 부재(최초 1회 로드). 자동갱신 구현 or 표기 정정. 스토리탭 재로드 버튼 없음.
- **복합 인덱스 확인·커버** — 실 Firestore READY 확인(`gcloud firestore indexes composite list`) + 새 쿼리(stories status/lenses/score) 인덱스 필요 여부.
- **tier 저장 전파** — `feeds.yaml` `tier` 필드가 검증만 되고 RawItem/저장·`meta` 발행에 미전파(`firestore-contract` 공유설정 처방).
- **Step-2 잔여(low)** — ① `assign`의 open_stories TypedDict화 ② classify 제목·본문 접합 false-positive(본문 파이프라인 확대 전 수정 권장).

## 🟡 사소·정리
- `body_mode: calendar` 선언만·미구현(무음 summary 폴백, `collect/parser.py`) → 구현/선언제거/`NotImplementedError` 택1.
- `taxonomy.yaml` topics `energy` ↔ 설계 `energy/oil` 명칭 드리프트 — 어휘 확정.
- `load_taxonomy` 미지 키·빈 축 무음 통과 → 경고/assert로 fail-loud.
- 요약 패스가 `count<2` 단일 스토리도 요약(사이트는 count≥2만 표시 → 콜 낭비) → `get_stories_needing_summary` 필터에 count≥2.
- `topics.yaml` `sectors_surface_top_n` 동적 top-N 노출 미구현.

## 🔵 향후 / 선택
- **응용 레이어** — 리포트 탭(설계=메모리 `report-tab-design`) · 아키타입 시장뷰·시나리오·국면. 분석 레이어 위에 얹힘.
- **보안 강화** — Firebase App Check / apiKey HTTP 리퍼러 제한(읽기 quota 남용 차단). 무료티어라 당장 불필요.
- **서비스 단위 src 분할** — `src/newsstore/{collector,enrichment,store}`.
