"""리포트 패스 순수 로직 — top-K(storyRank·섹터 층화 cap)·급부상 선정."""
from datetime import datetime, timezone, timedelta
from newsstore.enrich.report import (story_rank, select_top_k, select_rising,
                                     REPORT_MAX_STORIES, SECTOR_STRATIFY_CAP,
                                     REPORT_MIN_STORIES)

NOW = datetime(2026, 7, 4, 7, 0, tzinfo=timezone.utc)


def _s(sid, *, impact=2, hours_ago=1, lenses=("kr_equity",), sector=None, ndev=1):
    devs = [{"text": f"d{i}", "time": NOW - timedelta(hours=hours_ago),
             "delta_time": NOW - timedelta(hours=hours_ago)} for i in range(ndev)]
    ls = list(lenses) + ([sector] if sector else [])
    return {"id": sid, "title": sid, "summary": "x", "impact": impact,
            "lenses": ls, "count": 3, "developments": devs}


def test_story_rank_mirrors_ui_impact_times_freshness():
    fresh = story_rank(_s("a", impact=2, hours_ago=0), NOW)
    old = story_rank(_s("b", impact=2, hours_ago=48), NOW)
    unscored = story_rank({"id": "c", "impact": None, "developments": [],
                           "last_seen": NOW}, NOW)
    assert fresh > old and unscored > 0                 # 미채점 prior(IMPACT_PRIOR=1, 0 매몰 금지)


def test_select_top_k_caps_and_ranks():
    stories = [_s(f"s{i}", impact=(3 if i < 5 else 1)) for i in range(30)]
    top = select_top_k(stories, NOW, stratify=False)
    assert len(top) == REPORT_MAX_STORIES
    assert top[0]["impact"] == 3                        # 랭킹 상위 우선


def test_select_top_k_sector_stratify_cap():
    # 반도체(sector_tech) 20건이 전부 impact 3 — cap 없으면 top-15 독식
    tech = [_s(f"t{i}", impact=3, sector="sector_tech") for i in range(20)]
    fin = [_s(f"f{i}", impact=1, sector="sector_financials") for i in range(3)]
    top = select_top_k(tech + fin, NOW, stratify=True)
    n_tech = sum(1 for s in top if "sector_tech" in s["lenses"])
    assert n_tech == SECTOR_STRATIFY_CAP                # 같은 섹터 최대 N건(cap — fill 아님)
    assert any("sector_financials" in s["lenses"] for s in top)


def test_select_rising_density_and_exclusion():
    hot = _s("hot", ndev=5)                             # 24h 델타 5건 — 밀도 최고
    cold = _s("cold", ndev=1)
    in_topk = _s("taken", ndev=4)
    rising = select_rising([hot, cold, in_topk], top_k_ids={"taken"}, now=NOW)
    assert [s["id"] for s in rising][0] == "hot"
    assert all(s["id"] != "taken" for s in rising)      # 타 리포트 top-K 등장분 제외


def test_min_stories_constant():
    assert REPORT_MIN_STORIES >= 2                      # 사이트 표시 기준(count>=2)과 동일 발상
