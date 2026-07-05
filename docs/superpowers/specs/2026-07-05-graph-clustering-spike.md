# Spec W1 — 그래프 커뮤니티 검출 클러스터링 스파이크 (측정 전용)

작성: 2026-07-05 · 구간 소유권 = `scripts/*` + `src/newsstore/enrich/clustering_spike*.py`(신규) + `tests/test_clustering_spike*.py` + 분석 의존성 파일(`requirements*.txt`/이미지). **프로덕션 클러스터링 경로(`clustering.py`)·리포트·store·web 무변경.** 이건 측정 스파이크지 채택이 아니다.

## 왜 (측정된 필요 — 구조적 실패 조준)
과거 과병합은 임의 실패가 아니라 **구조적**이다. "코사인 ≥ 임계면 엣지를 잇고 연결요소를 클러스터로"는 single-linkage와 같고, "A~B, B~C지만 A는 C와 무관"인데 B를 다리 삼아 사가가 사슬로 붙는 chaining을 낳는다(이란↔코스피 블롭). 모듈러리티·밀도 기반 그래프 커뮤니티 검출은 **엣지 밀도(안쪽이 바깥쪽보다 촘촘한가)로 사슬을 끊는다** — 이 특정 실패를 직접 겨냥한다. 다만 오답노트 교훈("드라이버는 임베딩+게이트였지 채택 라이브러리가 아니다")대로, **눈먼 교체가 아니라 측정으로 이기는지 확인**한 뒤에만 채택한다.

## 무엇을 재나 (방법 3 + 베이스라인)
같은 임베딩 공간(centroid_sum 768, 패리티)·같은 골든에서 나란히 채점:
- **베이스라인**: 현 `cluster_articles`(프로덕션 로직).
- **Leiden**(`leidenalg`+`python-igraph`): kNN 그래프 위 모듈러리티 커뮤니티. 임베딩 클러스터링의 현 표준(scanpy).
- **HDBSCAN**(`hdbscan`): 밀도 기반, 임계·군집수 불요, 옅은 점은 noise=싱글톤. BERTopic 엔진.
- (선택·시간 남으면) correlation-clustering 관점 메모만 — LLM 동일/상이 엣지에 이론적으로 맞는 프레임이나 구현은 이 스파이크 밖.

## 채점 (불변식 — 매직넘버 없음)
`tests/clustering_metrics.py:bcubed()` 재사용. 각 방법을 **B-cubed (P, R, F1)**로 재고, 핵심은 **'자명해 격파' 불변식** — 전부병합(P 폭락)·전부분리(R 폭락) 두 자명해를 **F1로 모두 이겨야** 가치 있음(all-one과 동률이면 가치 0). 수렴(recall)과 분리(precision) 골든을 짝지어 본다(한쪽 지표는 과병합을 보상함 — 오답노트 교훈). 임계·k·min_cluster_size 같은 파라미터는 박지 말고 **불변식(자명해 격파·베이스라인 대비)**으로 평가, 필요한 스윕은 스크립트가 스스로 돈다.

## 판별력 있는 골든 확보 (critical — 이게 없으면 측정 무의미)
- 이 레포의 `test_clustering_golden.py` 합성 코퍼스는 **직교 벡터**라 모든 방법이 완벽 분리 → **방법 판별 불가**(discriminating power 0). 스파이크엔 부적합.
- 판별력 있는 실측 골든(이란+코스피, 현 F1=0.821)은 **news-analytics eval 하네스**에 있다(GEMINI_API_KEY·실 임베딩 fixture 의존). 스파이크는 먼저 **이 라벨 골든(id→true_label + 저장된 768 임베딩)을 fixture로 확보**해야 한다 — news-analytics에서 포팅하거나, 저장 스토리에서 사람이 라벨한 소규모 세트를 만든다.
- **골든을 확보 못 하면**: 그 자체를 결과로 보고한다("판별 측정 불가 — 골든 X 필요"). 억지 합성으로 가짜 우열을 내지 말 것(FAIL-LOUD).

## 산출 (스파이크 = 결정 + 증거, 배선 아님)
- `scripts/graph_cluster_spike.py`(측정 엔트리, Docker) + 순수 로직 테스트(fake 주입 결정론). saga_split_audit의 `load_stories`·`cosine`·패리티 fail-loud를 재사용.
- 사람 읽는 리포트(stdout): 방법별 B-cubed P/R/F1, 자명해 격파 여부, 베이스라인 대비 승패, kNN k·모듈러리티 파라미터.
- **처방**: adopt(어느 방법이 베이스라인을 유의하게 이김) / reject(못 이김 → "드라이버는 임베딩·게이트" 증거로 기록) / blocked(골든 없음). 어느 쪽이든 오답노트에 남길 교훈을 리턴.

## 리스크/주의 (주입 gotchas)
- **신규 무거운 의존성**: `igraph`·`leidenalg`·`hdbscan`·`numpy`가 현 이미지에 전무(C 확장 컴파일). **먼저 Docker 이미지에 설치되는지 실증**(measure-first) — 안 되면 그것부터 보고. 프로덕션 이미지 오염 없게 분석 전용 경로/이미지로.
- **임베딩 패리티(critical)**: 코사인·그래프 엣지는 `len(vec)==768` fail-loud(차원 불일치 zip 무음절단=가짜 유사도 — solved 교훈). centroid_sum(정규화 안 됨)은 코사인 크기불변이라 그대로 쓰되, HDBSCAN/유클리드 거리를 쓰면 정규화 필요(방법별 거리 계약 명시).
- **스트리밍 vs 배치**: 프로덕션 수집은 스트리밍(River DBSTREAM), Leiden·HDBSCAN은 배치. 스파이크는 배치 측정만 — 채택 시 온라인화 비용은 별도 후속(범위 밖, 명시).
- **비침습**: stories 읽기 전용, 프로덕션 문서·경로 무변경. LLM 콜 최소(측정 보조만, 프로덕션 콜 아님).
- **mock↔실 None**(`x or []`), datetime 3축 직렬화, Docker 전용 테스트(`MSYS_NO_PATHCONV=1 docker compose run --rm test`).

## 범위 밖
프로덕션 클러스터러 교체·배선(스파이크가 이기면 별도 스펙). 온라인/스트리밍화. 섹터 자동감지(그래프 군집의 2차 응용 — 먼저 사가에서 이기는지부터). correlation clustering 구현.

<!-- 3렌즈 리뷰: critical 1 + major 3. (critical)레벨 불일치 — 베이스라인/골든/F1=0.821은 기사→스토리(article_id)인데 스펙은 Leiden/HDBSCAN을 centroid_sum(스토리 노드)에 돌린다 → bcubed 교집합 비어 나란히 채점 불성립(그래프 노드가 기사인지 스토리인지 미명시). (major)골든 조달 모순(load_stories는 true_label 없음). (major)'유의하게 이김' 미정의 + 도전자만 파라미터 스윕-후-최고선택=다중비교 편향(베이스라인은 고정 1점). (major·핵심)why가 베이스라인을 순수 single-linkage로 오기술 — 실제 cluster_articles는 MAX-linkage+top-k+gray-band LLM 게이트+보수적 미합류로 체이닝을 이미 겨냥, 인용 통증(이란↔코스피 블롭)은 '과거'이고 완화 후 잔존 증거 없음. 현재 측정된 통증은 과병합이 아니라 과소병합(saga-aware 랭킹으로 이미 대응). → 지금 빌드는 이미 완화된 문제를 정당화할 위험(골드플레이팅). 지식 답(Leiden/HDBSCAN/correlation clustering 존재)은 전달, 빌드는 측정된 잔여 통증 확인까지 보류 권고. 사용자 판단. -->
<!-- spec-review: escalated -->
