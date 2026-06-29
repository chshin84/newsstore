# newsstore 뉴스 소스 확장 (RSS 볼륨업 + 무료 리서치 + 소스 tier) — 설계

_작성: 2026-06-28 · 성격: **자기완결 독립 스펙** — 뉴스 *소스*만 다룬다._

> **이 스펙의 경계 (다른 세션과의 분리)**
> - **포함**: `config/feeds.yaml` 카탈로그 확장, `FeedConfig`에 `tier` 필드 1개 추가, 라이브 프로빙, 배포.
> - **제외(다른 세션 소유)**: 토픽 렌즈·클러스터링 메서드·델타/milestone·risk/impact 스코어링·UI. 이것들은 별도 세션에서 탐색 중이며 그 결과가 SSOT다. 본 스펙은 **소스 레이어만** 건드린다(코드 로직 무변경).
> - 관련(상위) 문서: `docs/analysis-design.md`(분석 마스터 — 본 스펙이 그 §9 피드 레이어를 대체·소유).

## 1. 목표 / 배경
토픽/델타 같은 후속 기능은 **기사 밀도**가 받쳐줘야 의미가 있다(기사가 적으면 델타가 안 보임). 현재 `config/feeds.yaml`은 각 소스의 일부 섹션만 켜져 있다(예: 인포맥스 5/18 섹션, 한경 1섹션, 매경 1섹션). 가용 섹션을 확장하고, **가격 정보는 별도 루트**이므로 뉴스 소스는 **분석·1차 출처(중앙은행·리서치)에 가중**한다.

## 2. 거버넌스 규칙
1. **볼륨업 = 전 소스**: 인포맥스·한경·매경·Bloomberg·Benzinga의 미추가 섹션 + **무료 리서치** 채널.
2. **소스 tier**: `feeds.yaml`에 `tier` 필드 추가(SSOT) — `primary`(중앙은행·공시·1차) / `analysis`(리서치·심층기획·칼럼) / `wire`(헤드라인·일반 뉴스). 후속 세션의 스코어링·랭킹이 결정론 prior로 소비(본 스펙은 *필드 제공*까지만).
3. **비파괴 검증**: 신규 피드는 **라이브 프로빙(Docker, KR IP)**으로 도달성·본문 유무 실증 후 등재. 실패는 삭제가 아니라 주석으로 남김.
4. **SSOT 유지**: 사이트 소스 목록은 `distinct_sources(feeds)`로 도출 — `web/index.html` 하드코딩 금지. 신규 소스(BIS·EIA·IMF 등)는 자동으로 사이트 필터에 노출.
5. **전문가 커버리지 체크리스트(§4.8) + 자기 빈틈 인식(§4.9)**: 단순 채널 추가가 아니라 *프로 데스크가 커버하는 카테고리* 대비 빈틈을 명시(Fail-Loud). RSS로 못 닫는 빈틈(이메일/X 전용 엘리트 소스)은 채운 척하지 않고 후속으로 남긴다.
6. **선정 기준·필드 표준(§9 확정 규칙)**: 피드는 느낌이 아니라 §9 기준으로 넣고 뺀다(신호밀도·1차성·비중복·빈틈메움·케이던스·정당성·생존성). 필드(poll/body_mode/tier/tz_offset)는 §9.2 표준으로, 방법 개선은 채택/보류를 §9.3에 명시(YAGNI).

## 3. 데이터 / 스키마 변경 (최소)
`src/newsstore/collect/feeds.py`의 `FeedConfig`(pydantic, `extra="forbid"`)에 필드 1개 추가:
```
tier: Literal["primary", "analysis", "wire"] = "wire"
```
- `extra="forbid"`라 미선언 키는 조용히 기본값 안 먹고 즉시 실패 → **모델 선등록 후 yaml에 사용**(Fail-Loud).
- 기존 피드는 기본 `tier="wire"`로 백필(비파괴). 리서치·중앙은행만 `primary`/`analysis` 지정.
- 그 외 스키마(`feed_id·url·source·asset_hint·language·poll_minutes·body_mode·tz_offset`)는 변경 없음.

## 4. 카탈로그 — 확정 픽

### 4.1 인포맥스 (`tz_offset: 9` 필수, `body_mode: summary`, source 인포맥스)
기존 5개(S1N2·S1N15·S1N16·S1N21·S1N23) 유지 + 추가:
| 코드 | 섹션 | asset_hint | tier |
|---|---|---|---|
| S1N7 | IB/기업 | `kr_corp,ib` | analysis |
| S1N13 | 기획기사 | `kr_market` | analysis |
| S1N9 | 칼럼/이슈 | `opinion` | analysis |
| S1N12 | 외부기고 | `research` | analysis |
| S1N19 | 기고 | `research` | analysis |
| S1N17 | 부동산 | `kr_realestate` | wire |
| S1N25 | 보도자료 | `kr_corp` | wire(선택) |

스킵(잡음/무본문): S1N10 시사용어·S1N11 인물동정·S1N14 임시메인·S1N22 ad·S1N24 영상·clickTop·allArticle.

### 4.2 한국경제 (`body_mode: headline` — per-item 본문 없음, source 한국경제)
기존 finance(증권) 유지 + 추가: economy(경제·`kr_macro`)·realestate(부동산·`kr_realestate`)·it(IT·`kr_tech`)·international(국제·`global`)·society(사회·`kr_social`). URL `https://www.hankyung.com/feed/{section}`. 전부 `tier: wire`.

### 4.3 매일경제 (`body_mode: summary`, source 매일경제)
기존 mk_stock(증권 50200011) 유지 + 추가:
| 코드 | 섹션 | asset_hint |
|---|---|---|
| 30100041 | 경제 | `kr_macro` |
| 30200030 | 정치 | `kr_politics` |
| 50400012 | 사회 | `kr_social` |
| 30300018 | 국제 | `global` |
| 50100032 | 기업·경영 | `kr_corp` |
| 50300009 | 부동산 | `kr_realestate` |

URL `https://www.mk.co.kr/rss/{code}/`. 전부 `tier: wire`. 스킵: 헤드라인/전체뉴스(중복)·문화연예·스포츠·게임·영문·MBA.

### 4.4 Bloomberg (source Bloomberg)
기존 9개(markets·technology·economics·korea·business·politics·bview·crypto·wealth) + 추가:
- industries `https://feeds.bloomberg.com/industries/news.rss` (`industries`)
- green `https://feeds.bloomberg.com/green/news.rss` (`esg,energy`)

`body_mode`는 프로빙에서 description 유무로 확정(기본 headline 가정). `tier: wire`.
**카탈로그 SSOT**: `https://www.bloomberg.com/robots.txt` 하단 12개 `.xml` URL을 프로빙해 누락 섹션 확정(gadfly 폐지·bview에 흡수).

### 4.5 Benzinga (`body_mode: summary` — /feed 요약 풍부, source Benzinga)
기존 5개(news·markets·movers·crypto·commodities) + 추가 12개:
`/news/large-cap/feed`(us_stock)·`/topic/small-cap/feed`(us_stock)·`/news/insider-trades/feed`(us_stock)·`/tech/feed`(tech)·`/topic/ai/feed`(tech)·`/etfs/feed`(etf)·`/news/rumors/feed`(rumor)·`/news/offerings/feed`(us_stock)·`/trading-ideas/feed`(us_stock)·`/topic/stock-of-the-day/feed`(us_stock)·`/after-hours-center/feed`(us_stock)·`/markets/bonds/feed`(us_bond). 전부 `tier: wire`.

### 4.6 전문가/1차 채널 (카테고리별 — 프로빙으로 확정)
프로 데스크가 실제로 보는 무료 채널. 셀사이드 리서치 대부분은 게이팅 → 무료로 양질인 **공식 1차 + 독립 애널리스트**에 집중. URL은 호스트 약식 표기(`feeds.yaml`엔 `https://` 풀 URL), **프로빙(HTTP 200 + RSS 파싱) 통과만 등재**.

**(A) 중앙은행 발언·정책 (tier=primary)**
| 소스 | 후보 URL | asset_hint |
|---|---|---|
| **BIS 중앙은행 발언 통합** | `bis.org/doclist/cbspeeches.rss` | global_policy |
| BIS 발행물 | `bis.org/doclist/all_rss.xml` | global_policy |
| Fed 연설 | `federalreserve.gov/feeds/speeches.xml` | us_policy |
| Fed 통화정책 발표(FOMC) | `federalreserve.gov/feeds/press_monetary.xml` | us_policy |
| ECB 연설(기존 press 외) | `ecb.europa.eu/rss/speeches.html`(프로빙) | eu_policy |

> BIS cbspeeches는 글로벌 중앙은행 연설을 한 피드로 모음(고신호). 개별 CB 피드와 **중복 dedup** 주의(§4.9).

**(B) 1차 경제데이터·릴리스 (tier=primary)**
| 소스 | 후보 URL | asset_hint |
|---|---|---|
| EIA Today in Energy | `eia.gov/rss/todayinenergy.xml` | energy |
| EIA Weekly Petroleum / STEO | `eia.gov/tools/rssfeeds/`에서 선택 | energy |
| BLS(고용·CPI 릴리스) | `bls.gov/feed/news_release.rss` | us_macro |
| BEA(GDP·소득) | `bea.gov/news/rss.xml`(프로빙) | us_macro |
| Census(경제지표) | `census.gov/economic-indicators/indicator.xml`(프로빙) | us_macro |

> 릴리스는 캘린더성 — body 얇으면 `body_mode: headline`. 매크로/에너지 렌즈의 1차 신호.

**(C) 에너지·원자재 (사용자 신규 토픽 공급)**
| 소스 | 후보 URL | asset_hint | tier |
|---|---|---|---|
| IEA 뉴스 | `iea.org/rss/news`(프로빙) | energy | primary |
| OPEC 보도 | `opec.org/opec_web/en/press_room/rss.xml`(프로빙) | energy | primary |
| Kitco(금속·광업) | `kitco.com/news/category/mining/rss` | metals | wire |
| Baker Hughes 리그카운트 | RSS 미제공 가능 — 프로빙, 없으면 제외 | energy | primary |

> 귀금속·유가·에너지 렌즈 공급. Baker Hughes는 주간 데이터라 RSS 없을 수 있음 → 미충족 시 노트(§4.9).

**(D) 기업 공시 (tier=primary — 워치리스트 한정)**
| 소스 | 후보 URL | asset_hint |
|---|---|---|
| SEC EDGAR(구조화 공시) | `sec.gov/...` 회사별/유형별 RSS(10분 갱신) | us_filing |
| DART(한국 전자공시) | OpenDART API/RSS(회사·유형별) | kr_filing |

> **고신호·고볼륨** → 전체 firehose 금지, **워치 종목/유형으로 스코프**. 구조화 파싱·노이즈 처리는 후속 세션(§4.9).

**(E) 독립 애널리스트·싱크탱크 (tier=analysis)**
| 소스 | 후보 URL | asset_hint |
|---|---|---|
| NY Fed Liberty Street | `libertystreeteconomics.newyorkfed.org/feed/` | us_policy |
| IMF Blog | `imf.org/en/Blogs/rss` | global_macro |
| VoxEU/CEPR | `cepr.org/rss/voxeu.xml` | global_macro |
| NBER(new WP) | `nber.org/rss/new.xml` | research |
| BoE Bank Underground | `bankunderground.co.uk/feed/` | uk_policy |
| CFR Follow the Money(B.Setser) | `cfr.org/rss-feeds`에서 'Follow the Money' 선택(프로빙) | flows |
| Calculated Risk | `calculatedriskblog.com/feeds/posts/default` | macro |
| A.Damodaran(Musings) | `aswathdamodaran.blogspot.com/feeds/posts/default` | equity |
| Klement on Investing | `klementoninvesting.substack.com/feed` | macro |
| PIIE | `piie.com/rss.xml`(프로빙) | policy |
| Bruegel | `bruegel.org/rss.xml`(프로빙) | policy |
| CSIS · Brookings | `csis.org/rss` · `brookings.edu/feed`(프로빙) | policy |

**(F) 한국 기관 (프로빙 — RSS 경로 불확실, 미제공 시 제외)**
| 소스 | 후보 | asset_hint | tier |
|---|---|---|---|
| KCIF 국제금융속보 | `kcif.or.kr`(RSS 경로 프로빙) | global_macro | analysis |
| 한국은행 보도/경제연구 | `bok.or.kr`(RSS 프로빙) | kr_policy | primary |
| 기재부·금융위 보도 | `moef.go.kr`·`fsc.go.kr`(RSS 프로빙) | kr_policy | primary |
| KDI·KIEP·KCMI·KIF·KIET | 각 기관(RSS 프로빙) | research | analysis |

> 한국 기관은 RSS를 전면에 안 내세움 → 프로빙으로 경로 확인, **미제공 시 제외**(없는 걸 있는 척 안 함). 거래소 KIND·DART는 (D) 공시로.

### 4.7 후속(이 스펙 밖)
Reuters 추가 섹션 카탈로그(현재 Google News 경유 1피드) — 별도 후속.

### 4.8 전문가 커버리지 체크리스트 (빈틈을 Fail-Loud로)
빈틈을 명시해 "다뤄진 척"을 막는다(원칙3·4).

### 4.9 중요 노트 / 판단 (전문가 관점 — 자기 빈틈 인식)
- **RSS로 못 닫는 빈틈(정직히)**: 엘리트 소스 상당수가 **이메일·X(트위터) 전용** — Apollo *Daily Spark*(Torsten Slok)·Fed whisperer(Nick Timiraos) 등. RSS 없음 → **본 스펙 미충족, 미래 ingest(email/X 브리지)로 후속**. 빈칸을 채운 척하지 않는다.
- **공시(EDGAR/DART)**: 고신호지만 firehose는 노이즈·볼륨 폭발 → **워치 종목/유형 스코프만**. 구조화 데이터 파싱은 후속 세션.
- **데이터 릴리스 성격**: 캘린더성(주간/월간), body 얇음 → `headline`/`calendar` mode, 정기 중복 잦음 → dedup.
- **통합 피드 중복**: BIS cbspeeches·Google News 경유 등 **aggregator는 개별 소스와 중복** → 수집기 dedup(기존 link 해시)에 의존, 동일 사건 다중 등장은 후속 세션 클러스터가 처리.
- **주요 페이월 와이어(WSJ·FT)**: 공개 RSS의 **헤드라인/요약만 수용**(전문은 페이월) — **스크래핑 금지**(§9.1.6 정당성). WSJ RSS(`feeds.a.dj.com/rss/...`)는 안정적, FT(`ft.com/...?format=rss`)는 제한적 → 프로빙으로 가지치기. tier=wire(오피니언=analysis).
- **프로빙이 진실의 원천**: 위 URL은 후보. **HTTP 200 + RSS 파싱 + body 유무**를 실증한 것만 등재(증거 후 주장). 실패는 사유를 주석으로(비파괴).
- **tier 판단 기준**: 공식·1차·중앙은행·공시 = `primary`; 리서치·심층·칼럼·애널리스트 = `analysis`; 일반 뉴스 = `wire`. 후속 세션이 `primary>analysis>wire`로 신뢰도 prior.

## 5. 검증 / 프로빙
- **등록 검증(오프라인)**: `tests/test_registry_valid.py`·`test_config.py`의 불변식 재사용 — 유니크 feed_id, `body_mode` enum, url http 시작, `tier` enum. **개수 매직넘버 금지**(floor만).
- **라이브 프로빙(Docker, KR IP)**: 일회성 스크립트로 신규 피드를 기존 파서(`collect/parser.py`)로 fetch → `entries>0` + 본문 유무 리포트. 0건/에러 피드(특히 리서치 후보)는 feeds.yaml에서 주석 처리(비파괴), description 풍부한데 headline인 것은 summary 승격.
- **증거 후 주장**: 프로빙 리포트 로그를 근거로 등재 확정.

## 7. 범위 밖
- 토픽 렌즈·클러스터링·델타·스코어링·UI (다른 세션 소유).
- `tier`의 *소비*(스코어링 prior·랭킹) — 본 스펙은 필드 제공까지. 소비는 후속 세션.
- Reuters 섹션 확장.
- **이메일·X(트위터) 전용 엘리트 소스 ingest**(Apollo Daily Spark·Fed whisperer 등) — RSS 아님, 별도 ingest 메커니즘 후속(§4.9).
- **공시 firehose·구조화 파싱**(EDGAR/DART 전체) — 본 스펙은 워치-스코프 등록까지, 대량 구조화 처리는 후속.

## 8. 구현 메모 (plan화 시)
- Task 순서: `tier` 필드(모델·TDD) → 소스별 yaml 추가(인포맥스/한경/매경/Bloomberg/Benzinga/리서치) → 라이브 프로빙·가지치기 → (사용자 게이트) 배포.
- 각 소스 추가는 등록 검증으로 가드, 커밋 단위 분리.

## 9. 선정 기준 & 방법 (이 카탈로그를 지배하는 확정 규칙)
피드를 "느낌"이 아니라 기준으로 넣고 뺀다. 후속 운영(추가/삭제)도 이 규칙을 따른다 — Claude의 정확성이 아니라 규칙·테스트에 의존(원칙4).

### 9.1 포함/제외 기준
한 피드는 아래 축 중 **하나 이상에서 코퍼스를 개선하고 노이즈를 지배하지 않을 때** 포함:
1. **신호 밀도** — body 있는(summary/full) > headline-only. (headline도 유지하되 tier로 표시.)
2. **1차성** — 공식·1차(중앙은행·공시·데이터) 우선. 파생 aggregator(Google News)는 직접 RSS가 없을 때만.
3. **비중복** — 다른 피드를 단순 재방출하는 것 제외(clickTop·allArticle·인기기사). 정확 중복은 link 해시 dedup, 근사 중복은 후속 클러스터.
4. **빈틈 메움** — §4.8 체크리스트 빈틈(CB발언·에너지·공시)을 메우는 피드를 또 다른 일반 wire보다 우선.
5. **케이던스 적합** — poll_minutes를 소스 속도로(§9.2).
6. **정당성** — 공개 RSS만, 페이월 우회·스크래핑 금지(공식 피드 또는 Google News 경유).
7. **생존성** — 라이브 프로빙(HTTP 200 + 파싱 + entries>0) 통과만. 죽은/빈 피드는 사유 주석 후 제외(비파괴).
8. **지역·언어 균형** — KR + US/글로벌 유지, asset_hint로 렌즈 라우팅.

### 9.2 필드 표준 (ad-hoc 금지)
- **poll_minutes(속도 규칙)**: 실시간 wire/마켓 5–15분 · 섹션 뉴스 30분 · 일간 리서치/중앙은행 360분 · 주간 데이터 720분. 값은 이 등급에서 도출(개별 매직 금지).
- **body_mode**: 프로빙으로 결정 — description 있으면 summary, 없으면 headline. **추측 금지.**
- **tier**: primary(공식·CB·공시·데이터) / analysis(리서치·심층·칼럼·애널리스트) / wire(일반 뉴스). §4.9.
- **tz_offset**: naive-local 피드만(infomax KST=9). 그 외 생략.
- **asset_hint**: 렌즈 라우팅 키, 멀티값은 콤마.

