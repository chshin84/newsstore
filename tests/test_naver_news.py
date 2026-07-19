from datetime import datetime, timezone
import pytest
from newsstore.collect.naver_news import (
    map_row, _parse_pubdate, _publisher, load_naver_config, run_naver_pass, DEFAULT_POLL_MINUTES)

NOW = datetime(2026, 7, 19, tzinfo=timezone.utc)


# --- 매핑: 태그·엔티티 제거, url 폴백, 드롭 ---

def test_map_row_strips_tags_and_entities():
    row = {"title": "&quot;오라클 강등&quot;, <b>증시</b> 경고",
           "originallink": "https://businessplus.kr/a/1",
           "link": "https://n.news.naver.com/x",
           "description": "뉴욕 <b>증시</b>의 S&amp;P500지수는 최고치에서 2% 하락",
           "pubDate": "Sun, 19 Jul 2026 18:50:00 +0900"}
    item = map_row(row, "증시", "kr_stock", NOW)
    assert item.title == '"오라클 강등", 증시 경고'
    assert item.body == "뉴욕 증시의 S&P500지수는 최고치에서 2% 하락"
    assert item.url == "https://businessplus.kr/a/1"   # originallink 우선
    assert item.source == "businessplus.kr"            # 미등록 도메인 → 도메인 그대로(본 뉴스)
    assert item.feed_id == "naver:증시"
    assert item.asset_hint == "kr_stock"
    assert item.language == "ko"
    assert item.symbol == ""


def test_publisher_derives_from_originallink_domain():
    assert _publisher("https://www.mk.co.kr/news/1") == "매일경제"      # 매핑 + www 제거
    assert _publisher("https://biz.chosun.com/x") == "조선비즈"         # 서브도메인 완전일치 우선
    assert _publisher("https://view.asiae.co.kr/a") == "아시아경제"     # view. 제거 후 매핑
    assert _publisher("https://unknown-outlet.co.kr/a") == "unknown-outlet.co.kr"  # 미등록 → 도메인
    assert _publisher("https://n.news.naver.com/y") == "네이버"          # 네이버 호스팅 → 네이버
    assert _publisher("") == "네이버"                                    # 빈 url → 네이버


def test_map_row_maps_known_publisher():
    row = {"title": "t", "originallink": "https://www.hankyung.com/article/1",
           "link": "", "description": "d", "pubDate": ""}
    assert map_row(row, "증시", "kr_stock", NOW).source == "한국경제"


def test_map_row_url_falls_back_to_link():
    row = {"title": "제목", "originallink": "", "link": "https://n.news.naver.com/y",
           "description": "본문", "pubDate": ""}
    item = map_row(row, "코스피", "kr_stock", NOW)
    assert item.url == "https://n.news.naver.com/y"


def test_map_row_drops_when_no_url_and_no_title():
    row = {"title": "", "originallink": "", "link": "", "description": "본문만 있음"}
    assert map_row(row, "증시", "kr_stock", NOW) is None


def test_map_row_id_is_stable_for_same_url():
    row = {"title": "t", "originallink": "https://x/1", "link": "", "description": "d",
           "pubDate": ""}
    a = map_row(row, "증시", "kr_stock", NOW)
    b = map_row(row, "코스피", "kr_stock", NOW)   # 다른 쿼리라도 같은 url → 같은 id(교차쿼리 dedup)
    assert a.id == b.id


# --- pubDate 파싱 ---

def test_parse_pubdate_rfc822_kst_to_utc():
    # +0900 → UTC는 -9h
    assert _parse_pubdate("Sun, 19 Jul 2026 18:50:00 +0900") == \
        datetime(2026, 7, 19, 9, 50, tzinfo=timezone.utc)


def test_parse_pubdate_bad_returns_none():
    assert _parse_pubdate("") is None
    assert _parse_pubdate("nonsense") is None


# --- config 로드 ---

def test_load_config_defaults_and_queries(tmp_path):
    p = tmp_path / "naver.yaml"
    p.write_text("queries:\n  - {q: 증시, asset_hint: kr_stock}\n", encoding="utf-8")
    cfg = load_naver_config(p)
    assert cfg["queries"] == [{"q": "증시", "asset_hint": "kr_stock"}]
    assert cfg["poll_minutes"] == DEFAULT_POLL_MINUTES and cfg["display"] == 100


def test_load_config_empty_queries_fails(tmp_path):
    p = tmp_path / "bad.yaml"
    p.write_text("queries: []\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_naver_config(p)


# --- 오케스트레이션: 수집·건강·격리·dedup ---

class FakeStore:
    def __init__(self): self.state = {}; self.saved = []
    def get_feed_state(self, fid): return dict(self.state.get(fid, {}))
    def set_feed_state(self, fid, **f): self.state.setdefault(fid, {}).update(f)
    def upsert_items_batched(self, items):
        ids = {i.id for i in items} - {i.id for i in self.saved}
        self.saved.extend(i for i in items if i.id in ids)
        return len(ids)


def _row(u):
    return {"title": "t", "originallink": u, "link": "",
            "description": "본문", "pubDate": "Sun, 19 Jul 2026 18:50:00 +0900"}


def test_pass_collects_and_marks_health():
    store = FakeStore()
    def fetch(query): return [_row(f"https://x/{n}") for n in range(3)]
    summary = run_naver_pass(store, fetch, [{"q": "증시", "asset_hint": "kr_stock"}],
                             now=NOW, delay_s=0)
    assert summary["naver:증시"] == 3
    assert store.state["naver:증시"]["consecutive_failures"] == 0
    assert store.state["naver:증시"]["last_success"] == NOW


def test_pass_idempotent_rescan():
    # poll_minutes=0 → 항상 due. 2차 패스가 dedup 경로에 도달해 멱등 불변식 검증.
    store = FakeStore()
    def fetch(query): return [_row("https://x/1")]
    run_naver_pass(store, fetch, [{"q": "증시", "asset_hint": "kr_stock"}],
                   now=NOW, poll_minutes=0, delay_s=0)
    s2 = run_naver_pass(store, fetch, [{"q": "증시", "asset_hint": "kr_stock"}],
                        now=NOW, poll_minutes=0, delay_s=0)
    assert s2["naver:증시"] == 0        # 재적재 무-write(불변식)


def test_pass_isolates_query_failure():
    store = FakeStore()
    def fetch(query):
        if query == "코스피":
            raise RuntimeError("connection reset")
        return [_row("https://ok/1")]
    summary = run_naver_pass(store, fetch,
                             [{"q": "증시", "asset_hint": "kr_stock"},
                              {"q": "코스피", "asset_hint": "kr_stock"}],
                             now=NOW, delay_s=0)
    assert summary["naver:증시"] == 1 and summary["naver:코스피"] == -1
    assert store.state["naver:코스피"]["consecutive_failures"] == 1


def test_pass_respects_poll_not_due():
    store = FakeStore()
    store.state["naver:증시"] = {"last_fetched": NOW}
    def fetch(query): raise AssertionError("should not fetch")
    later = datetime(2026, 7, 19, 0, 10, tzinfo=timezone.utc)   # 10분 < poll 30 → 스킵
    summary = run_naver_pass(store, fetch, [{"q": "증시", "asset_hint": "kr_stock"}],
                             now=later, poll_minutes=30, delay_s=0)
    assert "naver:증시" not in summary


def test_pass_handles_none_fetch_result():
    # 실제 SDK가 빈 결과에 None을 줄 수 있음 — `or []` 가드가 AttributeError를 막는다.
    store = FakeStore()
    def fetch(query): return None
    summary = run_naver_pass(store, fetch, [{"q": "증시", "asset_hint": "kr_stock"}],
                             now=NOW, delay_s=0)
    assert summary["naver:증시"] == 0
