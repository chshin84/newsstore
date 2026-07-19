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
