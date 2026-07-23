# 수집 파이프라인 통합 설계 — RSS·네이버·FMP 병렬화 + 임베딩 분리

## 배경

지금 뉴스 수집은 서로 독립된 3개 Cloud Run Job으로 나뉘어 있다.

| Job | 스케줄러 | 내용 |
|---|---|---|
| `newsstore-collector` | `newsstore-5min`(5분) | RSS 85개 피드 수집 + 그 안에서 바로 임베딩 패스 |
| `newsstore-naver-news` | `newsstore-naver-15min`(15분) | 네이버 검색 뉴스 45개 키워드 수집 |
| `newsstore-fmp-news` | `newsstore-fmp-daily`(2026-07-22에 하루 1회→15분으로 변경 — 이 세션에서 `gcloud scheduler jobs update`로 직접 확인한 라이브 인프라 상태. 저장소 커밋·문서는 이 변경을 반영하지 않아 코드만 보면 하루 1회로 보이니, 계획 단계에서 다시 gcloud로 재확인할 것) | FMP 뉴스 6개 엔드포인트 수집 |

이번 세션 중 두 가지가 이미 드러났다.

1. **`is_due`(피드별 최소 재수집 간격) 체크가 지금은 전부 무의미하다.** `config/feeds.yaml` 85개 피드가 전부 `poll_minutes: 15`로 동일하고, Job 자체 트리거 주기(RSS 5분, 네이버·FMP 15분)와 맞춰보면 RSS는 3번 중 2번, 네이버·FMP는 이미 자기 스케줄과 정확히 일치해 사실상 상시 통과되는 체크였다. 이 부분은 이번 세션에서 이미 코드를 정리·검증했다(아래 "이미 완료된 선행 작업" 참고 — RSS·네이버 쪽은 완료, FMP는 이 문서 작성 이후 별도로 완료함).
2. **RSS·네이버·FMP가 서로 완전히 독립적이라 낭비와 사각지대가 있다.** 셋을 순차로 돌리면 벽시계 시간이 세 개를 더한 만큼 걸리고(각자 Cloud Run 프로비저닝 오버헤드도 3번), `job_health`(대시보드가 보는 잡 상태)는 RSS(`collector`)만 기록해 네이버·FMP는 잡 레벨 건강 확인이 아예 안 됐으며, "정상 소스 다수가 갑자기 실패하면 시스템 장애로 본다"는 감지(`FAIL_RATE_ALERT`)도 RSS에만 있었다.

## 목표

세 수집기를 하나의 Job 안에서 **병렬로 동시 실행**하고, 셋 다 끝난 뒤 **임베딩 패스를 한 번만** 돌리는 구조로 통합한다. 각 소스는 3분 예산을 넘으면 fail-loud로 스스로 멈추게 하고, 잡 레벨 건강 기록·시스템 장애 감지를 세 소스에 동일하게 적용한다.

## 이미 완료된 선행 작업

`is_due`(피드별 재수집 간격 체크)가 지금 설정 기준으로 아무 실익이 없다는 게 확인되어, 이 병합 작업의 기반으로 다음을 먼저 정리·검증했다(전체 테스트 스위트 154개 통과 확인 완료).

- `collector.py`: `is_due()` 함수·`collect_once`의 `force` 파라미터 제거 — 이제 호출될 때마다 모든 피드를 시도한다.
- `feeds.py`/`config/feeds.yaml`: `FeedConfig.poll_minutes` 필드와 85개 피드의 `poll_minutes: 15` 항목 제거(Pydantic `extra="forbid"`라 남아있으면 fail-loud로 즉시 드러난다).
- `naver_news.py`/`config/naver_news.yaml`: `is_due` 참조·`DEFAULT_POLL_MINUTES`·`run_naver_pass`의 `poll_minutes` 파라미터·설정 제거.
- `fmp_news.py`/`config/fmp_news.yaml`: `is_due` 참조·`run_fmp_news_pass`의 `poll_minutes` 파라미터·설정 제거(블랙아웃 파라미터는 그대로 유지).
- `run_collect.py`: `--force` CLI 옵션 제거. `run_naver_news.py`/`run_fmp_news.py`: 호출부에서 `poll_minutes` 인자 제거.
- 위 변경에 맞춰 `tests/test_collector.py`·`test_naver_news.py`·`test_fmp_news.py`·`test_registry_valid.py`·`test_models.py`·`test_config.py`를 갱신(스킵 검증 테스트는 삭제하거나 "항상 재시도" 의미로 재작성).

이 정리는 **병합과 독립적으로 이미 완결된 상태**다 — 아래 "새 아키텍처"에서 `run_collect.py`·`run_naver_news.py`·`run_fmp_news.py`를 삭제하는 것은 이 정리 자체를 무효화하는 게 아니라, 정리된 함수(`collect_once`·`run_naver_pass`·`run_fmp_news_pass`)를 그대로 새 오케스트레이터가 가져다 쓰고 옛 엔트리포인트 파일만 걷어내는 것이다.

## 새 아키텍처

### Job 토폴로지

`newsstore-collector`·`newsstore-naver-news`·`newsstore-fmp-news` 3개 Job과 `newsstore-5min`·`newsstore-naver-15min`·`newsstore-fmp-daily` 3개 스케줄러를 새 것으로 교체한다.

- **새 Job**: `newsstore-collect-all` (이미지는 기존과 동일한 collector 이미지, CMD만 새 엔트리포인트)
- **새 스케줄러**: `newsstore-collect-all-15min` (`*/15 * * * *`, UTC) 1개
- `newsstore-backfill-embed`(수동 임베딩 백필)는 이 변경과 무관하므로 그대로 둔다.
- **삭제 시점(REVERSIBLE 원칙)**: 기존 3개 Job·스케줄러는 새 Job이 배포되는 즉시 삭제하지 않는다. 새 Job을 최소 며칠(예: 1주) 무사히 운영하는 걸 확인한 뒤 삭제한다 — 그 전까지는 기존 스케줄러를 **일시정지**(`gcloud scheduler jobs pause`)만 해둔다. Cloud Run Job·Scheduler 자체는 삭제해도 이번 세션에서 실제로 반복 검증한 대로 `gcloud` 명령 몇 줄로 재생성 가능하지만(완전한 단방향 문은 아님), 정지 상태로 잠깐 더 보존하는 비용이 거의 0이므로 이 여유를 그냥 두는 게 안전하다.

### 새 엔트리포인트 — `run_collect_all.py`

기존 `collect_once`·`run_naver_pass`·`run_fmp_news_pass` 함수는 그대로 재사용한다(RSS·네이버는 이미 완료된 정리 그대로, FMP는 위 선행 작업에서 `is_due`/`poll_minutes`를 제거한 버전) — 이 병합 자체가 세 함수의 내부 로직을 추가로 바꾸지는 않고, `deadline` 파라미터 추가만 얹는다(아래 참고). 오케스트레이션은 다음 순서:

1. `ThreadPoolExecutor(max_workers=3)`에 세 함수를 각각 submit(RSS/네이버/FMP 클라이언트는 각자 독립적인 `httpx.Client` 인스턴스 사용 — 지금도 그렇다).
2. 각 future를 `result(timeout=200초)`로 기다린다(백스톱, 아래 "3분 강제종료" 참고 — 1단 내부 데드라인 180초보다 20초 여유를 둔 값으로, 1단이 정상 발동할 시간을 먼저 준다).
3. 세 결과(성공/타임아웃/기타 예외)를 전부 모은 뒤(하나가 실패해도 나머지를 기다리는 걸 막지 않음), **그제서야** `embed_pass`를 한 번 호출한다. 임베딩은 RSS 코드 경로에서 완전히 분리되어 이 오케스트레이터의 최상위 로직에만 존재한다.
4. 세 소스 + 임베딩 결과를 종합해 시스템 장애 여부를 판정하고, `job_health("collect_all")` 기록·exit code 결정을 **`job_health` 컨텍스트 블록이 닫히기 전에** 수행한다(이유는 아래 "`job_health` 정확한 실패 기록" 참고 — 지금 RSS 단독 코드도 이 순서가 아니라서 실제로는 시스템 장애가 나도 `job_health`엔 `ok`로 남는 기존 결함이 있고, 이번에 세 소스로 확장하며 같이 고친다).

### 3분 강제종료 + fail-loud (2단 방어) — 무엇을 보장하고 무엇을 보장 못 하는지

파이썬 스레드는 외부에서 안전하게 강제 종료할 수 없다(OS 프로세스와 다름). `ThreadPoolExecutor`의 워커 스레드는 기본적으로 non-daemon이라 인터프리터가 살아있는 워커 스레드를 자동으로 join하려 든다 — 그래서 이 방어는 "3분이면 Job의 실제 종료 시각이 앞당겨진다"를 보장하지 않는다. **정확히 보장하는 것과 안 하는 것을 구분해서 설계한다.**

- **1단(내부 자체 체크) — 이게 실질적 방어선이다**: `collect_once`·`run_naver_pass`·`run_fmp_news_pass` 각각에 `deadline: datetime` 파라미터를 추가한다. 각자의 for문(피드/쿼리/엔드포인트) 안에서 매 반복 시작 시 `now >= deadline`이면: `log.error(...)`로 즉시 fail-loud 기록 → 남은 항목은 스킵 → 전용 예외 `CollectorTimeoutError`를 raise하고 **함수 자체가 정상적으로 리턴(스레드가 실제로 끝남)**한다. 이 시점까지 이미 처리된 항목은 각 루프 안에서 그때그때 Firestore에 저장돼 있으므로(현재도 그렇다) 데이터 손실은 없다. **여러 항목에 걸쳐 누적되는 저하(예: 개별 호출은 정상 응답하지만 하나하나가 평소보다 느려짐)는 이 1단이 실제로 잡아 스레드를 정상 종료시키므로, 전체 Job은 여전히 15분 주기·600초 타임아웃 안에서 잘 끝난다.**
- **2단(오케스트레이터 백스톱) — 이건 "우리 로직이 안 멈추는 것"만 보장한다**: 만약 단일 HTTP 호출 하나가 자체 타임아웃도 없이 완전히 멈추면(아래 근거로 이 경우는 실제로는 드물다), 1단의 반복 경계 체크 자체가 그 한 호출이 끝날 때까지 평가되지 않는다. 이런 극단적 경우에 대비해 `future.result(timeout=200초)`를 건다 — 이게 발동하면 fail-loud로 기록하고, **오케스트레이터는 그 결과를 기다리지 않고 다음 단계(나머지 소스 결과 처리·임베딩·job_health 기록)로 진행한다.** 다만 멈춘 스레드 자체는 여전히 백그라운드에서 살아있고, **Job 프로세스의 실제 종료는 여전히 Cloud Run Job의 task-timeout(600초)에 의존한다** — 2단은 벽시계 시간이나 비용을 줄여주는 장치가 아니라, "우리 쪽 상태 기록과 나머지 소스 처리가 그 하나의 멈춘 호출 때문에 같이 묶여서 안 멈추게" 해주는 장치다.
- **단일 호출이 완전히 멈추는 극단적 경우가 실제로 드문 근거**: 코드 확인 결과 네이버·FMP 클라이언트는 `httpx.Client(timeout=30.0)`로 명시돼 있고, RSS `ssl_config.make_client()`는 기본 `timeout=90.0`(사내 프록시 지연 대비), 본문 스크래핑은 `ARTICLE_TIMEOUT_S=6.0`이다. 즉 개별 HTTP 호출은 최대 90초(RSS 최악값) 안에 반드시 응답하거나 예외로 끝난다 — "완전히 멈춘다"는 시나리오는 이 타임아웃들이 다 무력화되는 아주 드문 상황(예: 소켓 레벨에서 응답도 예외도 없이 걸림)에 한정된다. 다만 RSS의 90초 타임아웃은 한 피드에서만 걸려도 1단의 180초 예산 중 절반을 혼자 먹을 수 있어 완전히 무관하지는 않다.
- **격리는 유지**: 한 소스가 타임아웃으로 fail-loud 처리돼도 나머지 두 소스와 임베딩은 정상 진행한다. "조용히 넘어가지 않는다"(fail-loud)와 "한 소스 실패가 전체를 막지 않는다"(격리)는 별개이며 둘 다 만족해야 한다.

### `job_health` 정확한 실패 기록 (기존 결함 발견 + 수정)

실제 `_health.py`를 확인한 결과, `job_health` 컨텍스트 매니저는 **`with` 블록 밖으로 예외가 전파될 때만** `last_status="fail"`을 기록한다(정상 리턴하면 무조건 `last_status="ok"`). 그런데 현재 `run_collect.py`는 시스템 장애 판정(`FAIL_RATE_ALERT` 등)과 그에 따른 `return 1`을 **`with make_store() as store, job_health(store, "collector") as h:` 블록이 닫힌 뒤**(78~90행)에 수행한다 — 즉 **오늘 이미, RSS 단독 코드에서도 시스템 장애로 exit 1이 나는 실행조차 `job_health`엔 `last_status="ok"`로 남는다**(detail 문자열엔 `failed=N`이 남지만 대시보드가 보는 배지 필드는 안 바뀐다). 이번 병합이 내세우는 대표 동기(잡 레벨 건강을 세 소스에 균등 적용)가 이 패턴을 그대로 답습하면 실제로는 작동하지 않는다.

**수정**: `run_collect_all.py`는 세 소스 + 임베딩 결과를 다 모은 뒤, 시스템 장애 판정을 **`with job_health(...)` 블록이 닫히기 전에** 수행한다. 장애로 판정되면 판정 사유를 담은 전용 예외(예: `JobDegraded(detail)`)를 그 블록 안에서 raise한다 — `job_health`의 `except BaseException` 분기가 이를 잡아 `last_status="fail"`을 정확히 기록하고 그대로 재전파한다. 엔트리포인트 최상위 `main()`이 이 예외를 한 번 더 잡아 로그를 남기고 `return 1`한다. 이렇게 하면 job_health 기록과 exit code가 항상 같은 판정을 가리키게 된다.

### Firestore 클라이언트 동시 사용 — 설계 결정과 대안

세 함수가 같은 `store`(하나의 `google.cloud.firestore.Client`)를 스레드 3개에서 동시에 쓴다. 이 클라이언트의 스레드 안전성이 공식적으로 명확히 보증돼 있지 않으므로, 이걸 "테스트해보고 확인"에만 맡기지 않고 명시적 계획을 둔다.

- **1차 시도**: 공유 클라이언트 그대로 사용 — grpc 기반 client는 일반적으로 스레드 간 공유가 가능하도록 설계돼 있고(연결 풀링이 내부적으로 처리됨), 이 레포의 기존 코드도 이미 여러 곳(배치 쓰기 등)에서 같은 클라이언트를 재사용한다.
- **검증**: 플랜 단계에서 에뮬레이터 기준 "3개 스레드가 동시에 서로 다른 컬렉션에 upsert"하는 통합 테스트를 먼저 돌려 확인한다.
- **대안(1차가 실패할 경우)**: 각 함수가 이미 `store` 파라미터를 주입받는 구조이므로, `run_collect_all.py`에서 스레드마다 독립된 `FirestoreStore(firestore.Client(...))` 인스턴스를 만들어 넘기는 것으로 전환 비용 낮게 바꿀 수 있다(httpx 클라이언트를 이미 그렇게 각자 독립적으로 쓰고 있는 것과 같은 패턴). 이 전환 경로를 미리 설계에 적어둠으로써, 검증에서 문제가 발견돼도 플랜이 막히지 않게 한다.

### `job_health`·시스템 장애 감지 통일

- 지금 `job_health`는 RSS(`collector`)만 기록하고 네이버·FMP는 잡 레벨 건강 기록이 없다. 통합 후 `job_health("collect_all")` 하나에 세 소스 + 임베딩 상태를 모두 담은 detail 문자열을 기록한다(예: `rss=ok naver=ok fmp=timeout embed=ok`). 이건 조건부가 아니라 이번 병합의 확정 요구사항이다(`_health.py`에 다중 소스 detail 조립을 돕는 헬퍼를 추가하거나, `run_collect_all.py`에서 문자열을 직접 조립 — 구현 방식은 플랜에서 정한다).
- RSS에만 있던 시스템 장애 감지(`FAIL_RATE_ALERT`/`CHRONIC_DEAD_STREAK`/`MIN_ATTEMPTED_FOR_ALERT`)를 네이버·FMP에도 동일하게 적용해, 세 소스 중 하나라도 시스템 장애 수준으로 판단되면 Job 전체가 `job_health` fail + exit 1로 기록된다(현재 네이버·FMP는 개별 항목이 전부 실패해도 무조건 exit 0이었다). **이건 "3분 타임아웃+fail-loud"라는 원 요청보다 스코프가 넓은 추가 결정이지만, Job을 하나로 합치는 순간 "세 소스의 건강을 한 군데서 본다"는 요구가 자연히 따라오므로 같이 반영하기로 한다.**

## 트레이드오프 — 병합이 만드는 새 리스크

3개 독립 Job → 1개 통합 Job은 이득(벽시계 시간·프로비저닝 오버헤드 절감, 건강 기록 통일)만 있는 게 아니라 새로운 리스크도 만든다는 걸 명시해둔다.

- **단일장애점(SPOF) 확대**: 지금은 RSS가 죽어도 네이버·FMP는 무관하게 산다. 병합 후에는 `run_collect_all.py` 자체의 결함(예: 공통 설정 로딩 실패, import 에러)이나 위에서 설명한 스레드 문제가 세 소스 + 임베딩 전체를 동시에 막을 수 있다. 이 트레이드오프를 감수하고 병합하는 이유는 벽시계 시간·운영 단순화 이득이 이 리스크보다 크다고 판단했기 때문이며, 위의 "삭제 시점" 정책(즉시 삭제 대신 정지 후 유예)이 배포 직후 리스크를 완화하는 안전판 역할을 한다.

## 실측 근거 — 3분 예산의 여유

이번 세션 중 실제 로그로 확인한 소요시간(정상 상황):

- FMP: 최근 4회 실행 전부 5~8초
- 네이버: 29개 쿼리 처리에 약 13초(45개 전체면 대략 20초 안팎)
- RSS+임베딩(당시 배포본, `is_due`로 일부 스킵 중이던 상태): 5회 실행이 13~79초

셋 다 3분(180초)에 비해 여러 배의 여유가 있다 — 3분 타임아웃은 평소 발동을 기대하는 값이 아니라 소스 장애·네트워크 저하 같은 비정상 상황에 대비한 저비용 보험이다. 이 수치들은 이번 세션의 라이브 로그 관측치라 저장소 코드로 재검증할 수 있는 성격이 아니다(다음 실측 시 값이 달라질 수 있음을 감안).

## 변경 파일 요약

- 신설: `src/newsstore/entrypoints/run_collect_all.py`
- 삭제: `src/newsstore/entrypoints/run_collect.py`, `run_naver_news.py`, `run_fmp_news.py`(이 세 파일에 대한 이번 세션의 정리 작업은 무효화되는 게 아니라, 그 결과물인 `collect_once`/`run_naver_pass`/`run_fmp_news_pass` 함수가 새 오케스트레이터로 그대로 이관되는 것 — 파일만 없어짐)
- 수정: `collector.py`·`naver_news.py`·`fmp_news.py`(`deadline` 파라미터 추가), `_health.py`(다중 소스 detail 조립 지원 — 확정 작업), `run_collect.py`의 `FAIL_RATE_ALERT`류 상수·판정 로직을 `run_collect_all.py`로 이관하고 네이버·FMP 결과에도 적용
- 삭제 대상 인프라: Cloud Run Job 3개, Cloud Scheduler 3개(즉시 삭제 아님 — 위 "삭제 시점" 참고)
- 신설 인프라: Cloud Run Job 1개(`newsstore-collect-all`), Cloud Scheduler 1개

## 테스트 방향 (플랜 단계에서 구체화)

- 각 콜렉터의 `deadline` 초과 시 `CollectorTimeoutError` 발생 + 그 이전 처리분은 저장돼 있는지(기존 emulator 기반 테스트 패턴 재사용).
- 오케스트레이터: 한 소스가 예외를 던져도 나머지 결과 처리 + `embed_pass` 호출이 이루어지는지(1단 격리).
- **오케스트레이터 2단 백스톱**: 한 소스의 future가 `result(timeout=...)` 자체에서 타임아웃 나는 경로(1단 체크가 발동하지 않는 상황을 흉내)에서도 나머지 소스 처리 + 임베딩 + `job_health` 기록이 정상 진행되는지.
- `job_health`가 시스템 장애 판정 시 실제로 `last_status="fail"`을 기록하는지(블록 안에서 예외 raise 경로 검증 — 위 "정확한 실패 기록" 수정의 회귀 테스트).
- 시스템 장애 감지(`FAIL_RATE_ALERT`류)가 네이버·FMP 결과에도 동일하게 동작하는지.
- Firestore 클라이언트를 3개 스레드가 동시에 쓰는 경로에 대한 최소 통합 테스트(에뮬레이터 기준 동시 upsert) — 실패 시 위 "대안"(스레드별 독립 클라이언트)으로 전환.

## 스코프 밖

- `run_backfill_embed.py`(수동 백필) 변경 없음.
- 임베딩 자체의 cap·동시성 로직(이번 세션에서 이미 cap=5000으로 조정 완료) 변경 없음.
- FMP 블랙아웃 시간대(KST 7~9시) 자체의 로직 변경 없음 — `run_fmp_news_pass` 호출 시 그대로 파라미터 전달.
- FMP 각 엔드포인트(6개)의 1단 체크 해상도가 낮다는 점(엔드포인트 6개뿐이라 반복 경계 체크 기회가 적음)은 알려진 한계로 받아들인다 — FMP 전체가 정상 상황에서 5~8초에 끝나는 걸 감안하면 이 해상도로도 충분하다고 판단.

<!-- spec-review: passed -->
