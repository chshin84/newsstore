"""잡 헬스 하트비트 — 각 엔트리포인트 run을 감싸 job_health/{job}에 실행 상태를 남긴다.

대시보드(web/dashboard.html)가 이걸 읽어 🟢/🔴로 표시한다 — 조용한 실패·정지·미실행을 즉시 surface.
실패 모드별 거동:
  - 예외로 죽으면        → last_status="fail" + 에러 요약(catch 후 re-raise).
  - 정상 완료           → last_status="ok" + detail(수집 카운트 등).
  - 하드 kill(타임아웃·OOM) → 'fail' 기록이 안 남아 last_status="running"이 고착 → 대시보드가 '멈춤(정지)'으로 잡는다.
  - 아예 못 실행(모듈 없음 등) → job_health 문서가 stale/부재 → 대시보드가 '미실행'으로 잡는다.

detail은 컨텍스트가 채운다: `with job_health(store, "collector") as h: ...; h["detail"] = "..."`.
"""
from __future__ import annotations
from contextlib import contextmanager
from datetime import datetime, timezone

# 런의 성공/실패 ≠ 개별 항목(피드/쿼리/엔드포인트)의 건강. 런은 '시스템 장애'(프록시·인증·
# 네트워크 다운으로 평소 멀쩡하던 다수가 갑자기 실패)에서만 fail 처리한다. 한두 개·만성
# 죽은 항목이 죽어도 런은 정상(ok)이고, 그건 로그·대시보드로 surface한다. RSS 전용이던
# 것을 2026-07-23 수집 파이프라인 통합에서 세 소스(RSS·네이버·FMP) 공통으로 승격.
FAIL_RATE_ALERT = 0.5
CHRONIC_DEAD_STREAK = 5       # 연속 실패 이상이면 '만성 죽음' — 시스템 장애 판정에서 제외(이미 아는 죽음)
MIN_ATTEMPTED_FOR_ALERT = 10  # 정상 시도가 이 수 미만이면 실패율 알람 없음(소수 배치 우연 전멸 오판 방지)


class JobDegraded(Exception):
    """세 소스 중 하나 이상이 시스템 장애 수준으로 판정됐거나 임베딩이 실패했음을 알리는 예외.
    job_health(...) 블록 안에서 raise해야 last_status='fail'이 정확히 기록된다."""


def classify_systemic_failure(summary: dict, store) -> tuple[list[str], set[str]]:
    """summary({id: count|-1})와 store.get_feed_state로 '만성 죽음'과 '새로운 실패'를 가른다.
    반환: (new_failed 정렬 리스트, chronic id 집합). 시스템 장애 판정은 이 결과 +
    FAIL_RATE_ALERT/MIN_ATTEMPTED_FOR_ALERT를 조합해 호출부가 내린다(collector.py의
    FAIL_RATE_ALERT 로직을 세 소스 공통으로 일반화)."""
    failed = [k for k, v in summary.items() if v == -1]
    chronic = {k for k in failed
               if (store.get_feed_state(k).get("consecutive_failures") or 0) >= CHRONIC_DEAD_STREAK}
    new_failed = sorted(k for k in failed if k not in chronic)
    return new_failed, chronic


@contextmanager
def job_health(store, job: str):
    now = datetime.now(timezone.utc)
    store.set_job_health(job, last_run_at=now, last_status="running", fetched_at=now)
    ctx = {"detail": ""}
    try:
        yield ctx
    except BaseException as e:               # SystemExit·KeyboardInterrupt 포함 — 죽음은 다 기록
        end = datetime.now(timezone.utc)
        d = (ctx.get("detail") or "").strip()
        store.set_job_health(job, last_status="fail", last_finished_at=end,
                             detail=(d + f" | ERROR: {str(e)[:280]}").strip(" |"),
                             fetched_at=end)
        raise
    else:
        end = datetime.now(timezone.utc)
        store.set_job_health(job, last_status="ok", last_finished_at=end,
                             last_success_at=end, detail=(ctx.get("detail") or "").strip(),
                             fetched_at=end)
