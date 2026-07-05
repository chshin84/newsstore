// 플랜 B — 스토리 뷰 순수 로직 검증(node 단독, 브라우저/에뮬레이터 불필요).
// web/index.html의 STORIES-LOGIC 마커 블록을 '문자열 슬라이스'(취약한 JS 정규식 파싱 X)해 eval →
// 실제 배포되는 코드를 그대로 검증(복붙 드리프트 불가 — 단일 출처). 실행: node tests/web/stories_logic.test.mjs
import { readFileSync } from "node:fs";
import assert from "node:assert/strict";

const html = readFileSync(new URL("../../web/index.html", import.meta.url), "utf8");
const START = "// === STORIES-LOGIC-START";
const END = "// === STORIES-LOGIC-END";
const i = html.indexOf(START), j = html.indexOf(END);
assert.ok(i !== -1 && j !== -1 && j > i, "STORIES-LOGIC 마커가 index.html에 있어야 한다(드리프트 가드)");
const block = html.slice(i, j);
const { toMs, groupItemsByDevelopment, pickDisplayItems,
        storyRank, deltaBadge, isNew, nodeTimes, IMPACT_PRIOR, groupStoriesByLens, dedupeMains,
        displayHead, displayLead,
        excessBand, landingRows, breadthBadge, storyHasV2, storiesV2Empty } =
  new Function(block + "\nreturn { toMs, groupItemsByDevelopment, pickDisplayItems, storyRank, deltaBadge, isNew, nodeTimes, IMPACT_PRIOR, groupStoriesByLens, dedupeMains, displayHead, displayLead, excessBand, landingRows, breadthBadge, storyHasV2, storiesV2Empty };")();

let pass = 0, fail = 0;
const test = (name, fn) => { try { fn(); pass++; } catch (e) { fail++; console.error("FAIL:", name, "\n ", e.message); } };

const H = (h) => new Date(Date.UTC(2026, 5, 13, h, 0, 0));     // 시각 헬퍼
const item = (h, src) => ({ title: `t${h}`, source: src || "S", published_at: h == null ? null : H(h) });
const dev = (h, text) => ({ text: text || `d${h}`, time: H(h), source_count: 1 });

// --- toMs ---
test("toMs: Date/number/Timestamp/null", () => {
  assert.equal(toMs(null), null);
  assert.equal(toMs(123), 123);
  assert.equal(toMs(H(3)), H(3).getTime());
  assert.equal(toMs({ toDate: () => H(4) }), H(4).getTime());
});

// --- groupItemsByDevelopment ---
test("모든 비-null item이 정확히 1버킷(보존)", () => {
  const devs = [dev(2), dev(6), dev(0)];
  const items = [item(1), item(3), item(7), item(5), item(0)];
  const g = groupItemsByDevelopment(devs, items);
  const total = g.reduce((n, x) => n + x.items.length, 0);
  assert.equal(total, items.length);
});
test("그룹은 time DESC, 각 그룹 내부도 published_at DESC", () => {
  const g = groupItemsByDevelopment([dev(0), dev(6), dev(2)], [item(7), item(3), item(5), item(1)]);
  const times = g.filter(x => x.dev).map(x => toMs(x.dev.time));
  assert.deepEqual(times, [...times].sort((a, b) => b - a));   // DESC
  for (const grp of g) {
    const ms = grp.items.map(it => toMs(it.published_at));
    assert.deepEqual(ms, [...ms].sort((a, b) => b - a));
  }
});
test("경계 동률(item.ms == dev.ms) → 그 전개로(>=)", () => {
  const g = groupItemsByDevelopment([dev(6), dev(2)], [item(2)]);
  const g2 = g.find(x => toMs(x.dev.time) === H(2).getTime());
  assert.equal(g2.items.length, 1);                            // 2시는 dev(2)로
});
test("모든 전개보다 과거인 item → 가장 이른 전개", () => {
  const g = groupItemsByDevelopment([dev(6), dev(4)], [item(1)]);
  const earliest = g[g.length - 1];                            // dev(4)
  assert.equal(toMs(earliest.dev.time), H(4).getTime());
  assert.equal(earliest.items.length, 1);
});
test("가장 최신 item → 최신 전개", () => {
  const g = groupItemsByDevelopment([dev(6), dev(2)], [item(9)]);
  assert.equal(toMs(g[0].dev.time), H(6).getTime());
  assert.equal(g[0].items.length, 1);
});
test("developments 비면 단일 버킷(degrade)", () => {
  const g = groupItemsByDevelopment([], [item(1), item(3)]);
  assert.equal(g.length, 1);
  assert.equal(g[0].dev, null);
  assert.equal(g[0].items.length, 2);
});
test("items 비어도 throw 없이 빈 그룹", () => {
  const g = groupItemsByDevelopment([dev(2), dev(6)], []);
  assert.equal(g.length, 2);
  assert.ok(g.every(x => x.items.length === 0));
});
test("null published_at item·null time dev 제외", () => {
  const g = groupItemsByDevelopment([dev(2), { text: "x", time: null }], [item(3), item(null)]);
  const total = g.reduce((n, x) => n + x.items.length, 0);
  assert.equal(total, 1);                                      // null item 빠짐
  assert.equal(g.length, 1);                                  // null-time dev 빠짐
});

// --- pickDisplayItems ---
test("서로 다른 source 우선 ≤2 + moreCount", () => {
  const items = [item(5, "A"), item(4, "A"), item(3, "B"), item(2, "C")];
  const { shown, moreCount } = pickDisplayItems(items, 2);
  assert.equal(shown.length, 2);
  assert.deepEqual(shown.map(x => x.source), ["A", "B"]);     // A 다음 같은 A 건너뛰고 B
  assert.equal(moreCount, 2);
});
test("source가 1종뿐이면 같은 source로 채움", () => {
  const items = [item(5, "A"), item(4, "A"), item(3, "A")];
  const { shown, moreCount } = pickDisplayItems(items, 2);
  assert.equal(shown.length, 2);
  assert.equal(moreCount, 1);
});
test("항목이 max 이하면 moreCount=0", () => {
  const { shown, moreCount } = pickDisplayItems([item(1, "A")], 2);
  assert.equal(shown.length, 1);
  assert.equal(moreCount, 0);
});

const NOW = Date.UTC(2026, 5, 29, 12, 0, 0);
// --- storyRank ---
test("impact 높을수록·신선할수록 rank↑, 미채점은 IMPACT_PRIOR(0 아님)", () => {
  const hi = storyRank({ impact: 3, last_seen: new Date(NOW) }, NOW);
  const lo = storyRank({ impact: 1, last_seen: new Date(NOW) }, NOW);
  const un = storyRank({ impact: null, last_seen: new Date(NOW) }, NOW);  // 미채점
  assert.ok(hi > lo, "impact 3 > 1");
  assert.ok(un > 0, "미채점도 0 아님(매몰 방지)");
  assert.ok(Math.abs(un - storyRank({ impact: IMPACT_PRIOR, last_seen: new Date(NOW) }, NOW)) < 1e-9);
});
test("같은 impact면 더 신선한 쪽 rank↑", () => {
  const fresh = storyRank({ impact: 2, last_seen: new Date(NOW) }, NOW);
  const old = storyRank({ impact: 2, last_seen: new Date(NOW - 48 * 3600000) }, NOW);
  assert.ok(fresh > old);
});
// --- deltaBadge ---
test("delta: ref 있으면 ▲▼, 없으면 null, 0이면 null", () => {
  assert.deepEqual(deltaBadge(3, 2), { dir: "up", n: 1 });
  assert.deepEqual(deltaBadge(1, 2), { dir: "down", n: 1 });
  assert.equal(deltaBadge(2, 2), null);
  assert.equal(deltaBadge(3, null), null);     // ref 없음 → 화살표 생략
  assert.equal(deltaBadge(null, 2), null);
});
test("delta: score_ref_at 신선도 게이트 — 24h 지난 stale ref는 화살표 생략", () => {
  assert.equal(deltaBadge(3, 2, new Date(NOW - 25 * 3600000), NOW), null);          // stale
  assert.deepEqual(deltaBadge(3, 2, new Date(NOW - 3600000), NOW), { dir: "up", n: 1 }); // fresh
  assert.deepEqual(deltaBadge(3, 2), { dir: "up", n: 1 });     // refAt 미전달(레거시) → best-effort 유지
});
// --- displayHead/displayLead (계약 §stories 폴백 강등: headline→title, lead→summary) ---
test("폴백 강등: headline→title, lead→summary", () => {
  assert.equal(displayHead({ headline: "H", title: "T" }), "H");
  assert.equal(displayHead({ title: "T" }), "T");              // article 패스 미실행 강등
  assert.equal(displayHead({}), "");
  assert.equal(displayLead({ lead: "L", summary: "S" }), "L");
  assert.equal(displayLead({ summary: "S" }), "S");            // summary 폴백
  assert.equal(displayLead(null), "");
});
// --- isNew ---
test("isNew: first_seen이 REF_WINDOW 이내", () => {
  assert.equal(isNew(new Date(NOW - 3600000), NOW), true);    // 1h 전 → NEW
  assert.equal(isNew(new Date(NOW - 48 * 3600000), NOW), false);
  assert.equal(isNew(null, NOW), false);
});
// --- nodeTimes ---
test("nodeTimes: event_time 있으면 그것, 없으면 time(보도)로 폴백", () => {
  const ev = new Date(NOW - 7200000), rep = new Date(NOW);
  const a = nodeTimes({ time: rep, event_time: ev });
  assert.equal(a.event, ev.getTime()); assert.equal(a.report, rep.getTime());
  assert.equal(a.eventIsActual, true);
  const b = nodeTimes({ time: rep, event_time: null });
  assert.equal(b.event, rep.getTime()); assert.equal(b.eventIsActual, false);
});

// --- groupStoriesByLens (§7 섹션=렌즈) ---
test("groupStoriesByLens: 비배타 멤버십 + 렌즈 maxRisk 정렬 + 메인=storyRank 최대", () => {
  const ls = new Date(NOW);
  const s1 = { id: "a", lenses: ["kr_equity"], impact: 3, risk: 0, last_seen: ls };
  const s2 = { id: "b", lenses: ["us_rates"], impact: 1, risk: 3, last_seen: ls };
  const s3 = { id: "c", lenses: ["kr_equity", "crypto"], impact: 1, risk: 1, last_seen: ls };
  const g = groupStoriesByLens([s1, s2, s3], NOW);
  assert.equal(g[0].lensId, "us_rates");                       // maxRisk 3이 최상단
  const kre = g.find(x => x.lensId === "kr_equity");
  const cry = g.find(x => x.lensId === "crypto");
  assert.ok(kre.stories.some(s => s.id === "c") && cry.stories.some(s => s.id === "c")); // 비배타
  assert.equal(kre.main.id, "a");                              // 메인 = storyRank 최대(impact3)
  assert.equal(kre.maxRisk, 1);                                // max(0,1)
});
test("groupStoriesByLens: 렌즈 없는 스토리는 _etc 버킷(드롭 금지)", () => {
  const g = groupStoriesByLens([{ id: "x", lenses: [], impact: 2, last_seen: new Date(NOW) }], NOW);
  assert.equal(g.length, 1);
  assert.equal(g[0].lensId, "_etc");
  assert.equal(g[0].main.id, "x");
});
// --- dedupeMains (같은 스토리가 여러 렌즈 대표로 중복 노출되는 것 방지) ---
test("dedupeMains: 다중 렌즈 스토리가 대표 카드로 중복되지 않음", () => {
  const ls = new Date(NOW);
  // a는 세 렌즈 모두에서 1위(impact·risk 최고), b는 L1에만 속함
  const a = { id: "a", lenses: ["L1", "L2", "L3"], impact: 3, risk: 3, last_seen: ls };
  const b = { id: "b", lenses: ["L1"], impact: 1, risk: 1, last_seen: ls };
  const ded = dedupeMains(groupStoriesByLens([a, b], NOW));
  const mains = ded.map(g => g.main.id);
  assert.equal(new Set(mains).size, mains.length, "대표 스토리에 중복 없음");
  assert.equal(mains.filter(id => id === "a").length, 1, "a는 한 번만 대표");
});
test("dedupeMains: 대표가 겹치면 그 렌즈는 다음 스토리로, 없으면 카드 생략", () => {
  const ls = new Date(NOW);
  const a = { id: "a", lenses: ["L1", "L2"], impact: 3, risk: 3, last_seen: ls };  // L1·L2 1위
  const c = { id: "c", lenses: ["L2"], impact: 2, risk: 1, last_seen: ls };        // L2의 2위
  const ded = dedupeMains(groupStoriesByLens([a, c], NOW));
  const byLens = Object.fromEntries(ded.map(g => [g.lensId, g.main.id]));
  assert.equal(byLens["L1"], "a");        // L1 대표=a
  assert.equal(byLens["L2"], "c");        // L2는 a가 이미 쓰여 다음 스토리 c로
});

// --- WV2/WV4: 스토리 v2 (개체 착지 · 브레드스 · 빈상태) ---
test("excessBand: 방향+버킷 밴드(정밀 % 노출 금지 — 거짓정밀 억제)", () => {
  assert.equal(excessBand(0.4).dir, "flat");                 // |x|<1 → 지수와 비슷
  assert.equal(excessBand(0.4).text, "지수와 비슷");
  assert.equal(excessBand(2).dir, "up");
  assert.equal(excessBand(2).text, "지수 대비 소폭 초과");     // 1~3
  assert.equal(excessBand(5).text, "지수 대비 뚜렷이 초과");   // 3~8
  assert.equal(excessBand(12).text, "지수 대비 큰폭 초과");    // 8+
  assert.equal(excessBand(-5).dir, "down");
  assert.equal(excessBand(-5).text, "지수 대비 뚜렷이 하회");
  assert.equal(excessBand(null), null);                      // 수치 아님 → 생략(graceful)
  assert.equal(excessBand("x"), null);
  // 불변식: 밴드 텍스트에 원시 정밀 숫자가 새어나오지 않는다(3.7 같은 소수 금지)
  for (const v of [3.7, -11.23, 6.5]) assert.ok(!/\d/.test(excessBand(v).text), "밴드에 raw 숫자 금지");
});

test("landingRows: resolved면 실제 종목, 미해결이면 자산군만 + 자산군 dedup", () => {
  const landing = { asset_class_fallback: "국내주식", tickers: [
    { ticker: "005930", label: "삼성전자", excess_pct: 4.2, window_days: 20, resolved: true },
    { label: "국내주식", resolved: false },
    { label: "국내주식", resolved: false },   // 중복 자산군 → 1회로
  ] };
  const rows = landingRows(landing);
  assert.equal(rows.length, 2);                              // 종목 1 + 자산군 1(dedup)
  assert.equal(rows[0].resolved, true);
  assert.equal(rows[0].label, "삼성전자");
  assert.equal(rows[0].windowDays, 20);
  assert.equal(rows[0].band.text, "지수 대비 뚜렷이 초과");
  assert.equal(rows[1].resolved, false);
  assert.equal(rows[1].ticker, "");                          // 미해결 → 종목 감춤
  assert.equal(rows[1].band, null);                          // 미해결 → 밴드 없음
});

test("landingRows: 미해결 라벨 없으면 asset_class_fallback, 그것도 없으면 '자산군' · 부재 방어", () => {
  assert.deepEqual(landingRows(null), []);
  assert.deepEqual(landingRows({}), []);
  assert.deepEqual(landingRows({ tickers: "x" }), []);       // 계약 위반 방어
  const r = landingRows({ asset_class_fallback: "원자재", tickers: [{ resolved: false }] });
  assert.equal(r[0].label, "원자재");
  const r2 = landingRows({ tickers: [{ resolved: false }] });
  assert.equal(r2[0].label, "자산군");
});

test("breadthBadge: 자산군/스팬 있으면 배지, 둘 다 없으면 생략(graceful)", () => {
  const b = breadthBadge({ span: "3자산군", asset_classes: ["주식", "FX", "금리"],
    price_confirmed: true, uncovered: ["원자재"], unverified: true });
  assert.equal(b.assetClasses.length, 3);
  assert.equal(b.priceConfirmed, true);
  assert.deepEqual(b.uncovered, ["원자재"]);
  assert.equal(b.unverified, true);
  assert.equal(breadthBadge(null), null);
  assert.equal(breadthBadge({}), null);                      // span도 자산군도 없음 → 생략
  assert.equal(breadthBadge({ asset_classes: [] }), null);
  assert.ok(breadthBadge({ span: "단일" }));                 // span만 있어도 배지
});

test("storiesV2Empty: 어느 스토리에도 landing/breadth 없으면 true(빈상태 안내 트리거)", () => {
  assert.equal(storiesV2Empty([]), true);
  assert.equal(storiesV2Empty([{ id: "a" }, { id: "b" }]), true);
  assert.equal(storiesV2Empty([{ id: "a", breadth: { span: "2자산군" } }]), false);
  assert.equal(storiesV2Empty([{ id: "a",
    landing: { tickers: [{ ticker: "X", resolved: true, excess_pct: 3 }] } }]), false);
  assert.equal(storyHasV2({ id: "a", landing: { tickers: [] } }), false);   // 빈 tickers는 증강 아님
});

console.log(`\nstories_logic: ${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
