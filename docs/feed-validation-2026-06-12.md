# 피드 레지스트리 라이브 검증 — 2026-06-12

ultracode 병렬 워크플로(에이전트 30개, 피드당 1개)로 `config/feeds.yaml` 전체를 라이브 fetch(curl) → 파싱 → 건강도 판정.
환경: home (기본 SSL 검증), 호스트 curl 직접 호출.

## 종합

| 결과 | 수 | 피드 |
|------|----|------|
| ✅ OK   | 23 | infomax ×5, mk_stock, bz_news/markets/movers/crypto, coindesk, cointelegraph, fxstreet, fed, bbg ×4, gn ×3, trump_truth, axios |
| ⚠️ WARN | 7  | hankyung, bz_commod, forexlive, forexlive_cb, investing_fx, ecb, investing_bond |
| ❌ FAIL | 0  | — |

**30개 전부 도달 가능(HTTP 200), 전부 신선(대부분 수 시간 이내).** 깨진 피드 없음.
WARN은 "안 됨"이 아니라 *메타데이터/품질 보정 권고*입니다. 우선순위순으로:

---

## 조치 권고 (우선순위순)

### 1. 🔴 URL 리브랜딩 — ForexLive → InvestingLive (실질 수정 필요)
`forexlive.com`이 `investinglive.com`으로 사명 변경되어 **301 리다이렉트** 중. 지금은 `follow_redirects=True` 덕에 동작하지만 등록 URL/source가 stale.

| feed_id | 현재 URL | 변경 권고 |
|---------|----------|-----------|
| `forexlive`    | `https://www.forexlive.com/feed/news`        | `https://investinglive.com/feed/news` |
| `forexlive_cb` | `https://www.forexlive.com/feed/centralbank` | `https://investinglive.com/feed/centralbank` |

→ source 표기도 `ForexLive` → `InvestingLive`. 피드 본문(full)은 정상.

### 2. 🟡 body_mode 불일치 — per-item 본문 없음 (summary로 등록됐으나 제목만 제공)
아래 4개는 아이템에 `<description>`/summary가 없어 `body_mode: summary` 소비자가 빈 본문을 받음. **`headline`으로 낮추는 것** 권고(또는 본문을 원문 크롤로 보강).

| feed_id | item수 | 권고 |
|---------|--------|------|
| `hankyung`       | 50 | `summary` → `headline` |
| `investing_fx`   | 10 | `summary` → `headline` |
| `ecb`            | 15 | `summary` → `headline` (링크에 `//` 중복은 cosmetic) |
| `investing_bond` | 10 | `summary` → `headline` |

### 3. 🟡 토픽 순도 / 기타
- **`bz_commod`** (WARN): 채널은 'Commodities'인데 PR/와이어·일반 시황이 다수, 금속/유가/곡물 직접 뉴스는 적음. 유지하되 저순도 태깅 또는 PRNewswire 필터 권고.
- **`axios`** (OK): `www.axios.com/feeds/feed.rss` → `api.axios.com/feed/` 리다이렉트. 컬렉터가 리다이렉트 따라가야 함(현재 설정 OK).
- **`bbg_markets`** (OK): 현재 `headline`인데 description이 채워져 있어 `summary`로 **업그레이드 여지** 있음.

---

## 전체 결과 (30개)

| feed_id | 상태 | HTTP | items | freshness | body_ok | 메모 |
|---------|------|------|-------|-----------|---------|------|
| infomax_bond_fx | OK | 200 | 20 | ~1h | ✓ | 1개 아이템 본문이 저작권 보일러플레이트 |
| infomax_stock | OK | 200 | 20 | ~1h | ✓ | |
| infomax_overseas | OK | 200 | 20 | ~7h | ✓ | |
| infomax_intl | OK | 200 | 20 | ~1h | ✓ | |
| infomax_policy | OK | 200 | 20 | ~3h | ✓ | |
| hankyung | WARN | 200 | 50 | ~1h | ✗ | per-item 본문 없음 → headline |
| mk_stock | OK | 200 | 50 | ~1m | ✓ | |
| bz_news | OK | 200 | 15 | 당일 | ✓ | |
| bz_markets | OK | 200 | 15 | ~0h | ✓ | |
| bz_movers | OK | 200 | 15 | ~2h | ✓ | |
| bz_crypto | OK | 200 | 15 | ~2h | ✓ | |
| bz_commod | WARN | 200 | 15 | ~2h | ✓ | 토픽 순도 낮음 |
| coindesk | OK | 200 | 25 | ~2h | ✓ | |
| cointelegraph | OK | 200 | 30 | 수h | ✓ | |
| forexlive | WARN | 200 | 25 | ~2h | ✓ | URL 리브랜딩 → investinglive |
| forexlive_cb | WARN | 200 | 25 | ~30m | ✓ | URL 리브랜딩 → investinglive |
| fxstreet | OK | 200 | 30 | 당일 | ✓ | |
| investing_fx | WARN | 200 | 10 | 수h | ✗ | per-item 본문 없음 → headline |
| fed | OK | 200 | 20 | ~1d | ✓ | description이 title 중복(허용) |
| ecb | WARN | 200 | 15 | ~2h | ✗ | per-item 본문 없음 → headline |
| investing_bond | WARN | 200 | 10 | ~2h | ✗ | per-item 본문 없음 → headline |
| bbg_markets | OK | 200 | 30 | ~1h | ✓ | summary 승격 여지 |
| bbg_technology | OK | 200 | 30 | ~30m | ✓ | 미세 토픽 드리프트 |
| bbg_economics | OK | 200 | 30 | ~1h | ✓ | |
| bbg_korea | OK | 200 | 29 | ~3h | ✓ | flipboard 경유 정상 |
| gn_macro_reuters | OK | 200 | 100 | ~3h | ✓ | |
| gn_rumor | OK | 200 | 38 | ~17m | ✓ | |
| gn_kr_chips | OK | 200 | 23 | ~1h | ✓ | |
| trump_truth | OK | 200 | 100 | ~2h | ✓ | |
| axios | OK | 200 | 100 | ~2h | ✓ | api.axios.com 리다이렉트 |

_검증: 에이전트 30, 토큰 ~554k, 소요 ~169s._
