"""소스 여러 개를 스레드로 동시 실행하고 서로 격리한다(2026-07-23 수집 파이프라인 통합 설계).

중요한 한계(설계 문서 그대로): 파이썬 스레드는 외부에서 안전하게 강제 종료할 수 없다.
`future.result(timeout=...)`가 타임아웃 나도 이 함수는 빨리 리턴하지만, 그 시점에 아직 안
끝난 스레드 자체는 백그라운드에서 계속 산다 — ThreadPoolExecutor의 워커 스레드는
non-daemon이라 인터프리터 종료 시(atexit) 결국 join된다. 즉 이 함수는 "우리 로직(나머지
소스 처리·임베딩·job_health 기록)이 그 하나의 멈춘 소스 때문에 같이 멈추지 않게" 해주는
것이지, "Job 프로세스 자체가 빨리 끝난다"는 걸 보장하지 않는다. 프로세스의 실제 종료는
여전히 Cloud Run Job의 task-timeout(600초)에 달려 있다.

Fail-loud: 타임아웃으로 포기한 뒤 그 스레드가 나중에 실제로 끝나거나 예외를 던져도
`future.result()`/`.exception()`을 아무도 다시 안 부르면 파이썬은 그 결과를 조용히
버린다 — 그래서 타임아웃난 future엔 반드시 `add_done_callback`을 걸어 늦게 오는
성공/실패를 로그로라도 남긴다(이번 job_health 기록엔 이미 반영 못 하더라도, 다음
사이클 운영자가 로그로 추적할 수 있게).
"""
from __future__ import annotations
import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

from ..collect.collector import CollectorTimeoutError

log = logging.getLogger("newsstore.entrypoints.parallel")


def _log_late_outcome(name: str):
    def _cb(fut):
        try:
            fut.result()
            log.warning("%s: 오케스트레이터 타임아웃 이후 뒤늦게 정상 완료됨"
                        "(이번 실행의 job_health엔 이미 timeout으로 기록됨)", name)
        except Exception:
            log.error("%s: 오케스트레이터 타임아웃 이후 뒤늦게 예외 발생(fail-loud, "
                     "이번 실행의 job_health엔 이미 timeout으로 기록됨)", name, exc_info=True)
    return _cb


def run_sources_parallel(sources: dict, *, timeout: float) -> dict:
    """sources: {이름: 인자없는 콜러블(호출 시 summary dict 반환)}.
    반환: {이름: (summary_dict, error_marker)} — error_marker는 성공 시 None,
    소스 자신의 deadline 초과(CollectorTimeoutError)면 "deadline",
    오케스트레이터 대기 타임아웃이면 "timeout", 그 외 예외면 "error"."""
    ex = ThreadPoolExecutor(max_workers=max(1, len(sources)))
    futures = {ex.submit(fn): name for name, fn in sources.items()}
    results: dict = {}
    for fut, name in futures.items():
        try:
            results[name] = (fut.result(timeout=timeout), None)
        except FuturesTimeoutError:
            log.error("%s: 오케스트레이터 대기 타임아웃(%.0f초) — fail-loud, 다른 소스는 계속 진행", name, timeout)
            results[name] = ({}, "timeout")
            fut.add_done_callback(_log_late_outcome(name))   # 늦게 끝나도 fail-loud로 남긴다
        except CollectorTimeoutError:
            log.error("%s: 소스 자신의 3분 예산(deadline) 초과로 중단(fail-loud) — "
                     "그 시점까지 처리분은 이미 저장돼 있음", name)
            results[name] = ({}, "deadline")
        except Exception:
            log.exception("%s: 처리 중 예외(격리) — 다른 소스는 계속 진행", name)
            results[name] = ({}, "error")
    ex.shutdown(wait=False)   # 안 끝난 스레드를 기다리지 않고 진행(위 모듈 docstring 참고)
    return results
