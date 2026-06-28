# newsstore — 세션 핸드오프 (2026-06-28): 뉴스 소스 대확장

> 이 문서는 2026-06-28 세션의 **경험·결정·교훈** 보존용이다. 현재 상태·실행법은 `README.md`/`docs/operations.md`, 재사용 함정은 `docs/solved_problems.md` 참조.

## 0. TL;DR
뉴스 **소스 레이어**를 대폭 확장해 **main 머지 + 프로덕션 배포 + 라이브**까지 완료.
- **활성 피드 34 → 82 (+48, 약 2.4배)**, **활성 소스 15 → 26 (+11)**.
- 신규 소스: BIS·EIA·LibertyStreet·VoxEU·NBER·BankUnderground·CalculatedRisk·Damodaran·Klement·**WSJ·FT**.
- 코드: `FeedConfig.tier`(primary/analysis/wire) + 수집기 브라우저 User-Agent(`fetcher.py`) + `scripts/probe_feeds.py` + SSOT 가드 테스트.
- PR #1 MERGED. 전체 테스트 118 passed.

## 1. 무엇을 왜
가격 정보는 별도 루트로 빠지므로 뉴스 소스를 **1차/분석(중앙은행·리서치)에 가중**해 확장. 인포맥스/한경/매경 섹션 대거 추가 + 무료 리서치·중앙은행 발언(BIS cbspeeches)·에너지 데이터(EIA)·주요 와이어(WSJ/FT) 신규. 설계는 `docs/superpowers/specs/2026-06-28-feed-source-expansion-design.md`(확정), 플랜은 `docs/superpowers/plans/2026-06-28-feed-source-expansion.md`.

## 2. 핵심 교훈 — 피드 도달성은 IP별로 다르다 (양방향)
**프로빙 환경 ≠ 프로덕션 환경.** Docker 프로빙은 **로컬 호스트 IP**로 나가고 수집기는 **Cloud Run(서울) IP**로 나간다 → 사이트의 IP/UA 차단 결과가 다르다.
- **mk.co.kr(매경)**: Docker `403` ↔ Cloud Run `200`(라이브 수집 확인). → 프로빙 403만 보고 버리면 **멀쩡한 소스를 잃는다.**
- **bls.gov·opec.org**: Cloud Run에서도 `403`(데이터센터 IP 차단, fxstreet 동류). → 진짜 제외 대상.

**규칙**: 프로빙의 `403`/타임아웃은 **비권위**(경로 권위는 `404`만), **최종 판정은 배포 스모크 로그**. 수집기는 브라우저 UA 전송으로 UA 차단 일부 회피(IP 차단은 못 푼다). (이 교훈 `solved_problems.md` 핵심 gotchas에 등재됨.)

## 3. 작업 흐름에서 배운 것
- **검증 우선**: 프로빙 결과를 맹신하지 말 것. mk false-negative는 *라이브 사이트에 매경 기사가 있다*는 반증으로 잡았다.
- **비파괴**: 실패 피드는 삭제가 아니라 **사유+날짜 주석**으로. 되살리기/추적 쉬움.
- **배포 절차**(`operations.md §A`): `feeds.yaml`은 이미지에 COPY → 재빌드(`cloudbuild.yaml`) → `run jobs update --image` → `execute --wait` → 로그 확인. gcloud 풀경로 `C:\Users\ho381\AppData\Local\Google\Cloud SDK\...\gcloud.cmd`. `meta/sources`는 매 수집런이 `distinct_sources(feeds)`로 갱신 → 사이트 소스 필터 자동 반영(하드코딩 아님).

## 4. 미해결 / 후속 (급하지 않음)
- **올바른 URL 찾으면 회수 가능한 채널**(현재 잘못된 URL/404로 주석 제외): IMF Blog · CFR(Setser, Follow the Money) · IEA · Kitco · BIS 발행물(cbspeeches는 라이브) · KCIF(국제금융센터) · 한국은행. feeds.yaml 주석에 실패 사유 기록됨.
- **이메일/X 전용 엘리트 소스**(RSS 없음 — Apollo Daily Spark/Torsten Slok, Fed whisperer 등): 미래 ingest 메커니즘 필요. 스펙 §4.9 범위 밖.
- **bbg_industries/green** body_mode=headline 미프로빙 — desc 있으면 summary 승격 검토.
- 원격 `feat/feed-source-expansion` 브랜치 삭제(GitHub, PR #1에서 한 번에).

## 5. 스코프 경계 (중요 — 다른 세션과의 분리)
CLAUDE.md 갱신대로 **newsstore = 수집·저장·호스팅(UI)** 만. **인리치/분석(LLM 태깅·임베딩·클러스터·스토리·risk/impact·아키타입)은 별개 repo `news-analytics` 소유**(다른 세션), Firestore 스키마로만 결합(계약 SSOT `docs/firestore-contract.md`).
- 이 세션에서 만든 **`docs/superpowers/specs/2026-06-28-newsstore-topic-lens-redesign-design.md`(토픽 렌즈 마스터 설계)**는 *그 분석 작업의 스냅샷*이다. 상단에 "메서드 부분은 다른 세션 소유, 단독 구현 근거로 쓰지 말 것" 배너를 박아뒀다. 향후 news-analytics로 이전될 가능성.

## 6. 동시 세션 주의
이 작업 동안 **다른 세션이 같은 워킹트리를 동시 편집**했다(README·operations·roadmap·CLAUDE·일부 spec). → `git status`에 **남의 미커밋 변경**이 보일 수 있다. **남의 WIP을 커밋하지 말 것** — 본인이 만진 파일만 명시적으로 `git add`.
