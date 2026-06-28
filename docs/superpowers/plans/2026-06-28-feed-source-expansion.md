# 뉴스 소스 확장 (Feed Volume-up) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 확정 스펙(`docs/superpowers/specs/2026-06-28-feed-source-expansion-design.md`)대로 `config/feeds.yaml`을 전문가 카탈로그로 확장하고 `FeedConfig.tier`를 추가한다.

**Architecture:** 설정 확장 + 모델 필드 1개. 코드 로직(수집기·파서) 무변경. 각 피드는 등록 검증(오프라인) + 라이브 프로빙(Docker)으로 실증 후 등재(증거 후 주장·비파괴).

**Tech Stack:** Python 3, pydantic(FeedConfig), PyYAML, pytest, Docker Compose(Firestore 에뮬레이터), 기존 `collect/fetcher.py`·`collect/parser.py`.

## Global Constraints

- **Docker 전용** — 테스트: `MSYS_NO_PATHCONV=1 docker compose run --rm test`.
- **feeds.yaml = SSOT** — 사이트 소스 목록은 `distinct_sources()`로 도출(§9.3 드리프트 가드).
- **`FeedConfig`는 `extra="forbid"`** — 새 필드는 모델 선등록 후 yaml 사용(Fail-Loud). **Task 1이 반드시 먼저.**
- **body_mode ∈ {full, summary, headline, calendar}**; **tier ∈ {primary, analysis, wire}**.
- **poll_minutes(§9.2 속도 규칙)**: wire/마켓 5–15 · 섹션뉴스 30 · 일간 리서치/CB 360 · 주간데이터 720.
- **infomax만 `tz_offset: 9`**(naive KST). 그 외 생략.
- **프로빙 게이트**: 추측 URL 금지 — HTTP 200 + RSS 파싱 + entries>0 통과만 등재. 실패는 사유 주석 후 제외(비파괴).
- **배포는 사용자 게이트**(이미지 COPY → 재빌드+Job 갱신, `docs/operations.md`).
- **매직넘버 금지** — 등록 테스트는 floor·enum·유니크 불변식만.
- **범위 밖**: EDGAR/DART 구조화 공시(별도 핸들링 후속) · 이메일/X 전용 소스 · tier 소비(다른 세션).

---

### Task 1: `FeedConfig`에 `tier` 필드 추가  (**선행 — 반드시 먼저**)

**Files:**
- Modify: `src/newsstore/collect/feeds.py` (FeedConfig)
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: `FeedConfig.tier: Literal["primary","analysis","wire"] = "wire"`. 미선언이면 `extra="forbid"`가 오타로 거부하므로 모델 선등록 필수 → Tasks 2–9의 yaml `tier:`가 이 필드에 의존.

- [ ] **Step 1: 실패 테스트 작성** (`tests/test_config.py` 추가)

```python
def test_tier_defaults_to_wire_and_accepts_known_values():
    from newsstore.collect.feeds import FeedConfig
    assert FeedConfig(feed_id="a", url="https://e/a", source="S").tier == "wire"
    assert FeedConfig(feed_id="b", url="https://e/b", source="S", tier="primary").tier == "primary"

def test_tier_rejects_unknown_value():
    import pytest
    from newsstore.collect.feeds import FeedConfig
    with pytest.raises(Exception):
        FeedConfig(feed_id="a", url="https://e/a", source="S", tier="bogus")
```

- [ ] **Step 2: 실패 확인**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/test_config.py -k tier -v`
Expected: FAIL (`tier` 없음 / unknown 미거부)

- [ ] **Step 3: 구현** (`feeds.py`, `tz_offset` 줄 아래에 추가; 파일 상단에 `from typing import Literal`)

```python
    tier: Literal["primary", "analysis", "wire"] = "wire"   # 소스 신뢰도(spec §9.2)
```

- [ ] **Step 4: 통과 확인**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/test_config.py -v`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add src/newsstore/collect/feeds.py tests/test_config.py
git commit -m "feat(feeds): add source tier field (primary/analysis/wire)"
```

---

### Task 2: 인포맥스 +6 (tz_offset:9, summary)

**Files:** Modify `config/feeds.yaml`
**Interfaces:** feed_id `infomax_ib`,`infomax_feature`,`infomax_column`,`infomax_contrib_ext`,`infomax_contrib`,`infomax_realestate`.

- [ ] **Step 1: 인포맥스 블록에 추가**

```yaml
  - {feed_id: infomax_ib,          url: "https://news.einfomax.co.kr/rss/S1N7.xml",  source: 인포맥스, asset_hint: "kr_corp,ib", language: ko, poll_minutes: 60, body_mode: summary, tz_offset: 9, tier: analysis}
  - {feed_id: infomax_feature,     url: "https://news.einfomax.co.kr/rss/S1N13.xml", source: 인포맥스, asset_hint: kr_market, language: ko, poll_minutes: 60, body_mode: summary, tz_offset: 9, tier: analysis}
  - {feed_id: infomax_column,      url: "https://news.einfomax.co.kr/rss/S1N9.xml",  source: 인포맥스, asset_hint: opinion, language: ko, poll_minutes: 60, body_mode: summary, tz_offset: 9, tier: analysis}
  - {feed_id: infomax_contrib_ext, url: "https://news.einfomax.co.kr/rss/S1N12.xml", source: 인포맥스, asset_hint: research, language: ko, poll_minutes: 360, body_mode: summary, tz_offset: 9, tier: analysis}
  - {feed_id: infomax_contrib,     url: "https://news.einfomax.co.kr/rss/S1N19.xml", source: 인포맥스, asset_hint: research, language: ko, poll_minutes: 360, body_mode: summary, tz_offset: 9, tier: analysis}
  - {feed_id: infomax_realestate,  url: "https://news.einfomax.co.kr/rss/S1N17.xml", source: 인포맥스, asset_hint: kr_realestate, language: ko, poll_minutes: 60, body_mode: summary, tz_offset: 9, tier: wire}
```

- [ ] **Step 2: 등록 검증** — `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/test_registry_valid.py tests/test_config.py -v` → PASS
- [ ] **Step 3: 커밋** — `git add config/feeds.yaml && git commit -m "feat(feeds): infomax IB/feature/column/contrib/realestate"`

---

### Task 3: 한국경제 +5 (headline)

**Files:** Modify `config/feeds.yaml`
**Interfaces:** feed_id `hk_economy`,`hk_realestate`,`hk_it`,`hk_intl`,`hk_society`.

- [ ] **Step 1: 한경 블록에 추가**

```yaml
  - {feed_id: hk_economy,    url: "https://www.hankyung.com/feed/economy",       source: 한국경제, asset_hint: kr_macro, language: ko, poll_minutes: 30, body_mode: headline, tier: wire}
  - {feed_id: hk_realestate, url: "https://www.hankyung.com/feed/realestate",    source: 한국경제, asset_hint: kr_realestate, language: ko, poll_minutes: 30, body_mode: headline, tier: wire}
  - {feed_id: hk_it,         url: "https://www.hankyung.com/feed/it",            source: 한국경제, asset_hint: kr_tech, language: ko, poll_minutes: 30, body_mode: headline, tier: wire}
  - {feed_id: hk_intl,       url: "https://www.hankyung.com/feed/international", source: 한국경제, asset_hint: global, language: ko, poll_minutes: 30, body_mode: headline, tier: wire}
  - {feed_id: hk_society,    url: "https://www.hankyung.com/feed/society",       source: 한국경제, asset_hint: kr_social, language: ko, poll_minutes: 30, body_mode: headline, tier: wire}
```

- [ ] **Step 2: 등록 검증** → PASS
- [ ] **Step 3: 커밋** — `git commit -am "feat(feeds): hankyung economy/realestate/it/intl/society"`

---

### Task 4: 매일경제 +6 (summary)

**Files:** Modify `config/feeds.yaml`
**Interfaces:** feed_id `mk_economy`,`mk_politics`,`mk_society`,`mk_intl`,`mk_corp`,`mk_realestate`.

- [ ] **Step 1: 매경 블록에 추가**

```yaml
  - {feed_id: mk_economy,    url: "https://www.mk.co.kr/rss/30100041/", source: 매일경제, asset_hint: kr_macro, language: ko, poll_minutes: 30, body_mode: summary, tier: wire}
  - {feed_id: mk_politics,   url: "https://www.mk.co.kr/rss/30200030/", source: 매일경제, asset_hint: kr_politics, language: ko, poll_minutes: 30, body_mode: summary, tier: wire}
  - {feed_id: mk_society,    url: "https://www.mk.co.kr/rss/50400012/", source: 매일경제, asset_hint: kr_social, language: ko, poll_minutes: 30, body_mode: summary, tier: wire}
  - {feed_id: mk_intl,       url: "https://www.mk.co.kr/rss/30300018/", source: 매일경제, asset_hint: global, language: ko, poll_minutes: 30, body_mode: summary, tier: wire}
  - {feed_id: mk_corp,       url: "https://www.mk.co.kr/rss/50100032/", source: 매일경제, asset_hint: kr_corp, language: ko, poll_minutes: 30, body_mode: summary, tier: wire}
  - {feed_id: mk_realestate, url: "https://www.mk.co.kr/rss/50300009/", source: 매일경제, asset_hint: kr_realestate, language: ko, poll_minutes: 30, body_mode: summary, tier: wire}
```

- [ ] **Step 2: 등록 검증** → PASS
- [ ] **Step 3: 커밋** — `git commit -am "feat(feeds): mk economy/politics/society/intl/corp/realestate"`

---

### Task 5: 블룸버그 +2

**Files:** Modify `config/feeds.yaml`
**Interfaces:** feed_id `bbg_industries`,`bbg_green`. (body_mode는 Task 10 프로빙에서 확정 — 일단 headline.)

- [ ] **Step 1: Bloomberg 블록에 추가**

```yaml
  - {feed_id: bbg_industries, url: "https://feeds.bloomberg.com/industries/news.rss", source: Bloomberg, asset_hint: industries, poll_minutes: 30, body_mode: headline, tier: wire}
  - {feed_id: bbg_green,      url: "https://feeds.bloomberg.com/green/news.rss",      source: Bloomberg, asset_hint: "esg,energy", poll_minutes: 30, body_mode: headline, tier: wire}
```

- [ ] **Step 2: 등록 검증** → PASS
- [ ] **Step 3: 커밋** — `git commit -am "feat(feeds): bloomberg industries + green"`

---

### Task 6: 벤징가 +12 (summary)

**Files:** Modify `config/feeds.yaml`
**Interfaces:** feed_id `bz_largecap`,`bz_smallcap`,`bz_insider`,`bz_tech`,`bz_ai`,`bz_etf`,`bz_rumors`,`bz_offerings`,`bz_ideas`,`bz_sotd`,`bz_afterhours`,`bz_bonds`.

- [ ] **Step 1: Benzinga 블록에 추가**

```yaml
  - {feed_id: bz_largecap,   url: "https://www.benzinga.com/news/large-cap/feed",        source: Benzinga, asset_hint: us_stock, poll_minutes: 15, body_mode: summary, tier: wire}
  - {feed_id: bz_smallcap,   url: "https://www.benzinga.com/topic/small-cap/feed",       source: Benzinga, asset_hint: us_stock, poll_minutes: 30, body_mode: summary, tier: wire}
  - {feed_id: bz_insider,    url: "https://www.benzinga.com/news/insider-trades/feed",   source: Benzinga, asset_hint: us_stock, poll_minutes: 30, body_mode: summary, tier: wire}
  - {feed_id: bz_tech,       url: "https://www.benzinga.com/tech/feed",                  source: Benzinga, asset_hint: tech,     poll_minutes: 15, body_mode: summary, tier: wire}
  - {feed_id: bz_ai,         url: "https://www.benzinga.com/topic/ai/feed",              source: Benzinga, asset_hint: tech,     poll_minutes: 30, body_mode: summary, tier: wire}
  - {feed_id: bz_etf,        url: "https://www.benzinga.com/etfs/feed",                  source: Benzinga, asset_hint: etf,      poll_minutes: 30, body_mode: summary, tier: wire}
  - {feed_id: bz_rumors,     url: "https://www.benzinga.com/news/rumors/feed",           source: Benzinga, asset_hint: rumor,    poll_minutes: 30, body_mode: summary, tier: wire}
  - {feed_id: bz_offerings,  url: "https://www.benzinga.com/news/offerings/feed",        source: Benzinga, asset_hint: us_stock, poll_minutes: 30, body_mode: summary, tier: wire}
  - {feed_id: bz_ideas,      url: "https://www.benzinga.com/trading-ideas/feed",         source: Benzinga, asset_hint: us_stock, poll_minutes: 30, body_mode: summary, tier: wire}
  - {feed_id: bz_sotd,       url: "https://www.benzinga.com/topic/stock-of-the-day/feed", source: Benzinga, asset_hint: us_stock, poll_minutes: 60, body_mode: summary, tier: wire}
  - {feed_id: bz_afterhours, url: "https://www.benzinga.com/after-hours-center/feed",    source: Benzinga, asset_hint: us_stock, poll_minutes: 60, body_mode: summary, tier: wire}
  - {feed_id: bz_bonds,      url: "https://www.benzinga.com/markets/bonds/feed",         source: Benzinga, asset_hint: us_bond,  poll_minutes: 60, body_mode: summary, tier: wire}
```

- [ ] **Step 2: 등록 검증** → PASS
- [ ] **Step 3: 커밋** — `git commit -am "feat(feeds): 12 benzinga sections"`

---

### Task 7: 중앙은행·1차 데이터 (primary; spec §4.6 A·B)

**Files:** Modify `config/feeds.yaml` (신규 "── 중앙은행·1차 데이터 ──" 블록)
**Interfaces:** feed_id `bis_cbspeeches`,`bis_pub`,`fed_speeches`,`fed_fomc`,`eia_today`,`bls_news`. (정확 URL은 Task 10 프로빙 게이트.)

- [ ] **Step 1: 블록 추가**

```yaml
  # ── 중앙은행·1차 데이터 (primary; URL은 프로빙으로 확정) ──
  - {feed_id: bis_cbspeeches, url: "https://www.bis.org/doclist/cbspeeches.rss", source: BIS, asset_hint: global_policy, poll_minutes: 360, body_mode: summary, tier: primary}
  - {feed_id: bis_pub,        url: "https://www.bis.org/doclist/all_rss.xml",    source: BIS, asset_hint: global_policy, poll_minutes: 720, body_mode: headline, tier: primary}
  - {feed_id: fed_speeches,   url: "https://www.federalreserve.gov/feeds/speeches.xml",        source: Fed, asset_hint: us_policy, poll_minutes: 360, body_mode: summary, tier: primary}
  - {feed_id: fed_fomc,       url: "https://www.federalreserve.gov/feeds/press_monetary.xml", source: Fed, asset_hint: us_policy, poll_minutes: 360, body_mode: summary, tier: primary}
  - {feed_id: eia_today,      url: "https://www.eia.gov/rss/todayinenergy.xml",  source: EIA, asset_hint: energy, poll_minutes: 360, body_mode: summary, tier: primary}
  - {feed_id: bls_news,       url: "https://www.bls.gov/feed/news_release.rss",  source: BLS, asset_hint: us_macro, poll_minutes: 720, body_mode: headline, tier: primary}
```

- [ ] **Step 2: 등록 검증** → PASS
- [ ] **Step 3: 커밋** — `git commit -am "feat(feeds): central-bank speeches (BIS/Fed) + EIA/BLS primary sources"`

---

### Task 8: 독립 리서치·애널리스트 (analysis; spec §4.6 E)

**Files:** Modify `config/feeds.yaml` (신규 "── 무료 리서치 ──" 블록)
**Interfaces:** feed_id `fed_liberty`,`imf_blog`,`voxeu`,`nber_wp`,`boe_underground`,`cfr_setser`,`calculated_risk`,`damodaran`,`klement`. 전부 프로빙 게이트(실패는 주석 제외).

- [ ] **Step 1: 블록 추가**

```yaml
  # ── 무료 리서치 (analysis; 프로빙으로 확정, 실패는 주석 제외) ──
  - {feed_id: fed_liberty,     url: "https://libertystreeteconomics.newyorkfed.org/feed/", source: LibertyStreet, asset_hint: us_policy, poll_minutes: 360, body_mode: summary, tier: analysis}
  - {feed_id: imf_blog,        url: "https://www.imf.org/en/Blogs/rss",                    source: IMF, asset_hint: global_macro, poll_minutes: 360, body_mode: summary, tier: analysis}
  - {feed_id: voxeu,           url: "https://cepr.org/rss/voxeu.xml",                      source: VoxEU, asset_hint: global_macro, poll_minutes: 360, body_mode: summary, tier: analysis}
  - {feed_id: nber_wp,         url: "https://www.nber.org/rss/new.xml",                    source: NBER, asset_hint: research, poll_minutes: 720, body_mode: headline, tier: analysis}
  - {feed_id: boe_underground, url: "https://bankunderground.co.uk/feed/",                 source: BankUnderground, asset_hint: uk_policy, poll_minutes: 720, body_mode: summary, tier: analysis}
  - {feed_id: cfr_setser,      url: "https://www.cfr.org/blog/follow-money/rss.xml",       source: CFR, asset_hint: flows, poll_minutes: 360, body_mode: summary, tier: analysis}
  - {feed_id: calculated_risk, url: "https://www.calculatedriskblog.com/feeds/posts/default", source: CalculatedRisk, asset_hint: us_macro, poll_minutes: 360, body_mode: summary, tier: analysis}
  - {feed_id: damodaran,       url: "https://aswathdamodaran.blogspot.com/feeds/posts/default", source: Damodaran, asset_hint: equity, poll_minutes: 720, body_mode: summary, tier: analysis}
  - {feed_id: klement,         url: "https://klementoninvesting.substack.com/feed",        source: Klement, asset_hint: macro, poll_minutes: 720, body_mode: summary, tier: analysis}
```

- [ ] **Step 2: 등록 검증** → PASS
- [ ] **Step 3: 커밋** — `git commit -am "feat(feeds): research/analyst candidates (Liberty St/IMF/VoxEU/NBER/BoE/CFR/CR/Damodaran/Klement)"`

---

### Task 9: 에너지·금속 + 한국 기관 (프로빙 비중↑; spec §4.6 C·F)

**Files:** Modify `config/feeds.yaml` (신규 "── 에너지·원자재 ──", "── 한국 기관 ──" 블록)
**Interfaces:** feed_id `iea_news`,`opec_press`,`kitco_metals`,`kcif_flash`,`bok_press`. **RSS 경로 불확실** 다수 → Task 10에서 다수 가지치기 예상.

- [ ] **Step 1: 블록 추가** (불확실 후보 — 프로빙으로 살아남는 것만 유지)

```yaml
  # ── 에너지·원자재 (사용자 신규 토픽; 프로빙) ──
  - {feed_id: iea_news,     url: "https://www.iea.org/rss/news",                                  source: IEA, asset_hint: energy, poll_minutes: 360, body_mode: headline, tier: primary}
  - {feed_id: opec_press,   url: "https://www.opec.org/opec_web/en/press_room/rss.xml",           source: OPEC, asset_hint: energy, poll_minutes: 720, body_mode: headline, tier: primary}
  - {feed_id: kitco_metals, url: "https://www.kitco.com/news/category/mining/rss",                source: Kitco, asset_hint: metals, poll_minutes: 60, body_mode: summary, tier: wire}
  # ── 한국 기관 (RSS 경로 불확실 — 프로빙, 미제공 시 주석 제외) ──
  - {feed_id: kcif_flash,   url: "https://www.kcif.or.kr/rss/newsflash.xml",  source: KCIF, asset_hint: global_macro, poll_minutes: 360, body_mode: summary, tier: analysis}
  - {feed_id: bok_press,    url: "https://www.bok.or.kr/portal/bbs/B0000338/rss.do", source: 한국은행, asset_hint: kr_policy, poll_minutes: 360, body_mode: headline, tier: primary}
```

- [ ] **Step 2: 등록 검증** → PASS (형식만; 도달성은 Task 10)
- [ ] **Step 3: 커밋** — `git commit -am "feat(feeds): energy/metals (IEA/OPEC/Kitco) + KR institutions (KCIF/BOK) pending probe"`

---

### Task 9b: 주요 페이월 와이어 (WSJ/FT — 공개 RSS, 헤드라인/요약만)

**Files:** Modify `config/feeds.yaml` (신규 "── 주요 와이어(페이월; 공개 RSS만) ──" 블록)
**Interfaces:** feed_id `wsj_markets`,`wsj_world`,`wsj_business`,`wsj_tech`,`wsj_opinion`,`ft_home`,`ft_markets`,`ft_economy`. **전문은 페이월 — 공개 RSS의 헤드라인/요약만 수용, 스크래핑 금지(spec §9.1.6).** body_mode는 Task 10 프로빙에서 description 유무로 확정. FT는 RSS 제한적 → 다수 가지치기 예상.

- [ ] **Step 1: 블록 추가**

```yaml
  # ── 주요 와이어 (페이월; 공개 RSS 헤드라인/요약만, 스크래핑 금지) ──
  - {feed_id: wsj_markets,  url: "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",   source: WSJ, asset_hint: us_market, poll_minutes: 15, body_mode: summary, tier: wire}
  - {feed_id: wsj_world,    url: "https://feeds.a.dj.com/rss/RSSWorldNews.xml",      source: WSJ, asset_hint: global, poll_minutes: 30, body_mode: summary, tier: wire}
  - {feed_id: wsj_business, url: "https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml",  source: WSJ, asset_hint: us_stock, poll_minutes: 30, body_mode: summary, tier: wire}
  - {feed_id: wsj_tech,     url: "https://feeds.a.dj.com/rss/RSSWSJD.xml",           source: WSJ, asset_hint: tech, poll_minutes: 30, body_mode: summary, tier: wire}
  - {feed_id: wsj_opinion,  url: "https://feeds.a.dj.com/rss/RSSOpinion.xml",        source: WSJ, asset_hint: opinion, poll_minutes: 60, body_mode: summary, tier: analysis}
  - {feed_id: ft_home,      url: "https://www.ft.com/rss/home",                      source: FT, asset_hint: global, poll_minutes: 30, body_mode: headline, tier: wire}
  - {feed_id: ft_markets,   url: "https://www.ft.com/markets?format=rss",            source: FT, asset_hint: global_market, poll_minutes: 30, body_mode: headline, tier: wire}
  - {feed_id: ft_economy,   url: "https://www.ft.com/global-economy?format=rss",     source: FT, asset_hint: macro, poll_minutes: 30, body_mode: headline, tier: wire}
```

- [ ] **Step 2: 등록 검증** — `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/test_registry_valid.py -v` → PASS
- [ ] **Step 3: 커밋** — `git commit -am "feat(feeds): WSJ/FT major wires (public RSS, headline/summary only)"`

---

### Task 10: 라이브 프로빙 — 도달성·본문 검증 + 가지치기 (Docker)

**Files:** Create `scripts/probe_feeds.py`; Modify `config/feeds.yaml`(프로빙 실패 주석 + body_mode 보정).
**Interfaces:** Consumes `newsstore.collect.feeds.load_feeds`, `newsstore.collect.fetcher.fetch_feed`, `newsstore.collect.parser.parse_feed`. Produces 콘솔 리포트 `feed_id | entries | has_body`.

- [ ] **Step 1: 프로빙 스크립트 작성** — `scripts/probe_feeds.py`

```python
"""신규 피드 라이브 프로빙. Docker(KR IP) 1회 실행, 저장 없음.
사용: python scripts/probe_feeds.py <feed_id> [...]  (인자 없으면 전체)"""
from __future__ import annotations
import sys
from datetime import datetime, timezone
import httpx
from newsstore.collect.feeds import load_feeds
from newsstore.collect.fetcher import fetch_feed   # collector.py와 동일 fetch
from newsstore.collect.parser import parse_feed    # parse_feed(raw, feed, fetched_at)

def main(ids: list[str]) -> int:
    feeds = {f.feed_id: f for f in load_feeds("config/feeds.yaml")}
    targets = ids or list(feeds)
    now = datetime.now(timezone.utc)
    bad = 0
    with httpx.Client(timeout=20.0, follow_redirects=True) as client:
        for fid in targets:
            f = feeds.get(fid)
            if not f:
                print(f"{fid:18} MISSING"); bad += 1; continue
            try:
                res = fetch_feed(client, f, None, None)   # (client, feed, etag, last_modified)
                if res.status != 200:
                    print(f"{fid:18} HTTP {res.status}"); bad += 1; continue
                items = parse_feed(res.content, f, fetched_at=now)
                n = len(items)
                has_body = any((it.body or "").strip() for it in items)
                print(f"{fid:18} entries={n:3} has_body={has_body}")
                if n == 0:
                    bad += 1
            except Exception as e:
                print(f"{fid:18} ERROR {type(e).__name__}: {e}"); bad += 1
    print(f"\n{bad} feed(s) need attention")
    return 0 if bad == 0 else 1

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

> 시그니처는 `collect/collector.py`가 쓰는 그대로다: `fetch_feed(client, feed, etag, last_modified)` → `res.status`/`res.content`(필드는 `collect/fetcher.py` 참조), `parse_feed(res.content, feed, fetched_at)` → `RawItem` 리스트(`.body` 보유). `httpx`는 이미 의존성(collector가 사용) — 새 의존성 없음.

- [ ] **Step 2: 신규 피드 전체 프로빙**

Run: `MSYS_NO_PATHCONV=1 docker compose run --rm test python scripts/probe_feeds.py` (인자 없이 전체)
Expected: Task 2–9 신규 feed_id가 리포트됨. **entries=0/ERROR(특히 한국 기관·IEA/OPEC/리서치 후보)는 도달 실패.**

- [ ] **Step 3: 결과 반영** — 실패 피드를 사유와 함께 주석 처리(삭제 아님), description 풍부한데 headline인 것 summary 승격. 예:
```yaml
  # bok_press 프로빙 실패(404) 2026-06-28 — RSS 경로 재확인 필요, 제외
```
- [ ] **Step 4: 회귀** — `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/test_registry_valid.py tests/test_config.py -v` → PASS
- [ ] **Step 5: 커밋** — `git add scripts/probe_feeds.py config/feeds.yaml && git commit -m "test(feeds): live-probe new feeds; prune unreachable, fix body_mode"`

---

### Task 11: SSOT 드리프트 가드 (spec §9.3)

**Files:** Test `tests/test_registry_valid.py`; 조사 대상 `web/index.html`.
**Interfaces:** Consumes `distinct_sources(load_feeds(...))`.

- [ ] **Step 1: 신규 소스가 SSOT에 도출되는지 테스트** (`tests/test_registry_valid.py` 추가)

```python
def test_distinct_sources_is_ssot_for_registry():
    from newsstore.collect.feeds import load_feeds, distinct_sources
    feeds = load_feeds("config/feeds.yaml")
    srcs = distinct_sources(feeds)
    # SSOT 불변식: 사이트 소스 목록 = 레지스트리의 모든 소스(누락·추가 없음)
    assert set(srcs) == {f.source for f in feeds}
    # 프로빙에 안 흔들리는 신뢰 family가 노출(BIS 등 프로빙 위험군은 제외)
    for s in ["Benzinga", "매일경제", "한국경제"]:
        assert s in srcs
```

- [ ] **Step 2: 실행** — `MSYS_NO_PATHCONV=1 docker compose run --rm test pytest tests/test_registry_valid.py -v` → PASS
- [ ] **Step 3: 사이트 도출 확인(조사)** — `web/index.html`에서 소스 필터 목록이 **하드코딩인지 Firestore/meta에서 도출인지** 확인:

Run: `grep -n "source" web/index.html | head -40`
- 도출(예: `meta/sources` 문서 또는 items에서 distinct)이면 OK — 신규 소스 자동 노출.
- **하드코딩 배열이면**(원칙2 위반) → `docs/unsolved_problems.md`에 "index.html 소스 하드코딩 드리프트"로 기록(이 plan에서 비파괴로 *수정하지 말고 플래그* — 사이트 변경은 별도 Hosting 배포라 분리). 메인 세션에 보고.

- [ ] **Step 4: 커밋** — `git add tests/ && git commit -m "test(feeds): SSOT guard — new sources derive via distinct_sources"`

---

### Task 12: 배포 (사용자 게이트 — 승인 후에만)

**Files:** 없음(이미지 재빌드 + Job 갱신). 절차 `docs/operations.md`.

- [ ] **Step 1: 사용자 승인 확인** — 명시 전 진행 금지.
- [ ] **Step 2: 재빌드 + `gcloud run jobs update --image` + execute**(풀경로 gcloud, `docs/operations.md`).
- [ ] **Step 3: 라이브 스모크** — 1패스 후 신규 소스 items가 Firestore/사이트에 유입되는지 확인(증거 후 주장).
- [ ] **Step 4: 인벤토리 갱신** — `docs/operations.md` 피드 수·신규 소스 반영.

---

## Self-Review

- **Spec 커버리지:** §3 tier(T1)·§4.1 인포맥스(T2)·§4.2 한경(T3)·§4.3 매경(T4)·§4.4 블룸버그(T5)·§4.5 벤징가(T6)·§4.6 A·B 중앙은행/데이터(T7)·§4.6 E 리서치(T8)·§4.6 C·F 에너지/한국(T9)·§5 프로빙(T10)·§9.3 SSOT 가드(T11)·§6 배포(T12) 전부 매핑. **§4.6 D(EDGAR/DART)는 의도적 제외**(구조화 공시 = 별도 핸들링, spec §4.9·§7 범위 밖) — Global Constraints에 명시.
- **Placeholder:** 없음 — 모든 yaml 줄이 실제 값. T10 프로빙 스크립트는 실제 `fetch_feed`/`parse_feed` 시그니처 사용(검증됨). 불확실 URL은 "프로빙 게이트"로 명시 처리(추측 등재 아님).
- **타입 일관성:** `tier`는 T1 `Literal["primary","analysis","wire"]`로 정의, T2–T9가 그 값만 사용. feed_id 전부 유니크(load_feeds 강제). poll_minutes는 §9.2 등급 준수.
- **불변식:** 등록 테스트는 floor·enum·유니크만(매직넘버 없음).
- **태스크 순서 의존(명시):** Task 1(`tier` 필드)이 **반드시 먼저** — 이후 Tasks 2–9의 yaml `tier:`가 `extra="forbid"`를 통과한다. 실행은 Task 번호 순서.

<!-- spec-review: passed lenses=3 date=2026-06-28 note=probe-script+test fixed to real fetch_feed/parse_feed sigs; 're-review tier-missing' finding is false-positive (Task 1 adds field, ordered first) -->
