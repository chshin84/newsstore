// 가격 탭 순수 로직 — index.html PRICE-LOGIC 마커 슬라이스(node 단독).
import { readFileSync } from "node:fs";
import assert from "node:assert/strict";

const html = readFileSync(new URL("../../web/index.html", import.meta.url), "utf8");
const START = "// === PRICE-LOGIC-START", END = "// === PRICE-LOGIC-END";
const i = html.indexOf(START), j = html.indexOf(END);
assert.ok(i !== -1 && j !== -1 && j > i, "PRICE-LOGIC 마커 필요(드리프트 가드)");
const { pctClass, pctBucket, fearScore, sentimentLean, isDivergent, divergenceMag,
        marketSummary, mostDivergent, groupPricesByLens } =
  new Function(html.slice(i, j) +
    "\nreturn { pctClass, pctBucket, fearScore, sentimentLean, isDivergent, divergenceMag, marketSummary, mostDivergent, groupPricesByLens };")();

let pass = 0, fail = 0;
const test = (n, f) => { try { f(); pass++; } catch (e) { fail++; console.error("FAIL:", n, "\n ", e.message); } };

test("pctClass/pctBucket: 부호·크기 버킷", () => {
  assert.equal(pctClass(1.2), "up"); assert.equal(pctClass(-0.3), "down"); assert.equal(pctClass(0), "flat");
  assert.equal(pctClass(null), "flat");
  assert.equal(pctBucket(2.0), "strong"); assert.equal(pctBucket(-0.8), "mild"); assert.equal(pctBucket(0.1), "flat");
});

test("fearScore/sentimentLean: 프레임 극 카운트", () => {
  const f = { risks: [{}, {}, {}], premiums: [{}], watchpoints: [] };
  assert.equal(fearScore(f), 3);              // risks 수
  assert.equal(sentimentLean(f), -2);         // premiums(1) - risks(3) = 공포우세
  assert.equal(fearScore(null), 0); assert.equal(sentimentLean(undefined), 0);
});

test("isDivergent: 공포우세인데 가격↑ 또는 기대우세인데 가격↓", () => {
  const fear = { risks: [{}, {}], premiums: [], watchpoints: [] };     // lean<0
  const hope = { risks: [], premiums: [{}, {}], watchpoints: [] };     // lean>0
  assert.equal(isDivergent(fear, 1.5), true);   // 공포인데 상승 → 발산(과소반응 재료)
  assert.equal(isDivergent(fear, -1.5), false); // 공포+하락 → 정합
  assert.equal(isDivergent(hope, -1.2), true);  // 기대인데 하락 → 발산
  assert.equal(isDivergent(fear, 0), false);    // 보합 → 발산 아님
  assert.equal(isDivergent({ risks: [{}], premiums: [{}], watchpoints: [] }, 2), false); // lean=0 뭉갬
});

test("divergenceMag: |lean|×|pct| (발산 시만)", () => {
  const fear = { risks: [{}, {}, {}], premiums: [], watchpoints: [] };  // lean=-3
  assert.equal(divergenceMag(fear, 2), 6);      // 3×2
  assert.equal(divergenceMag(fear, -2), 0);     // 정합 → 0
});

test("marketSummary: 등락 집계", () => {
  const prices = { a: { percent_change: -1 }, b: { percent_change: -0.5 }, c: { percent_change: 2 } };
  const s = marketSummary(prices);
  assert.equal(s.total, 3); assert.equal(s.down, 2); assert.equal(s.up, 1);
  assert.ok(Math.abs(s.avgPct - (0.5 / 3)) < 1e-9);   // (-1-0.5+2)/3
});

test("mostDivergent: 발산도 최대 자산", () => {
  const prices = { kospi: { percent_change: 1, lens: "kr_equity" }, btc: { percent_change: 3, lens: "crypto" } };
  const frames = { kr_equity: { risks: [{}], premiums: [], watchpoints: [] },   // mag 1×1=1
                   crypto: { risks: [{}, {}], premiums: [], watchpoints: [] } };  // mag 2×3=6
  assert.equal(mostDivergent(prices, frames)?.key, "btc");
  assert.equal(mostDivergent({}, {}), null);
});

test("groupPricesByLens: 렌즈별 묶기 + 공포 desc 정렬", () => {
  const prices = { kospi: { lens: "kr_equity", label: "코스피" }, kosdaq: { lens: "kr_equity", label: "코스닥" },
                   btc: { lens: "crypto", label: "비트코인" } };
  const frames = { kr_equity: { risks: [{}, {}], premiums: [], watchpoints: [] },
                   crypto: { risks: [{}, {}, {}], premiums: [], watchpoints: [] } };
  const g = groupPricesByLens(prices, frames);
  assert.equal(g[0].lens, "crypto");            // 공포 3 > 2 → 위로
  assert.equal(g.find(x => x.lens === "kr_equity").items.length, 2);  // kospi+kosdaq 묶임
});

console.log(`\nprice_logic: ${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
