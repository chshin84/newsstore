// 가격 탭 순수 로직(값+차트) — index.html PRICE-LOGIC 마커 슬라이스(node 단독).
import { readFileSync } from "node:fs";
import assert from "node:assert/strict";

const html = readFileSync(new URL("../../web/index.html", import.meta.url), "utf8");
const START = "// === PRICE-LOGIC-START", END = "// === PRICE-LOGIC-END";
const i = html.indexOf(START), j = html.indexOf(END);
assert.ok(i !== -1 && j !== -1 && j > i, "PRICE-LOGIC 마커 필요(드리프트 가드)");
const { pctClass, sparkPoints, groupPriceCards } =
  new Function(html.slice(i, j) + "\nreturn { pctClass, sparkPoints, groupPriceCards };")();

let pass = 0, fail = 0;
const test = (n, f) => { try { f(); pass++; } catch (e) { fail++; console.error("FAIL:", n, "\n ", e.message); } };

test("pctClass: 부호", () => {
  assert.equal(pctClass(1.2), "up"); assert.equal(pctClass(-0.3), "down");
  assert.equal(pctClass(0), "flat"); assert.equal(pctClass(null), "flat");
});

test("sparkPoints: 시계열 close → 정규화 polyline points", () => {
  const series = [{ t: "d1", c: 100 }, { t: "d2", c: 110 }, { t: "d3", c: 90 }];
  const pts = sparkPoints(series, 200, 40).split(" ").map(s => s.split(",").map(Number));
  assert.equal(pts.length, 3);
  assert.equal(pts[0][0], 0);                         // 첫 x=0
  assert.equal(pts[2][0], 200);                       // 마지막 x=w
  // 정규화: 최대값(110)=맨 위(y=0), 최소값(90)=맨 아래(y=h)
  assert.equal(pts[1][1], 0);                         // 110=max → y=0
  assert.equal(pts[2][1], 40);                        // 90=min → y=h
});

test("sparkPoints: 2점 미만·비수치는 빈 문자열(차트 없음)", () => {
  assert.equal(sparkPoints([{ t: "d", c: 100 }], 200, 40), "");   // 1점 → 차트 불가
  assert.equal(sparkPoints([], 200, 40), "");
  assert.equal(sparkPoints(null, 200, 40), "");
  assert.equal(sparkPoints([{ c: "x" }, { c: "y" }], 200, 40), ""); // 비수치 → 걸러져 0점
});

test("sparkPoints: 평평한 시계열도 유효(0으로 안 나눔)", () => {
  const pts = sparkPoints([{ c: 50 }, { c: 50 }, { c: 50 }], 100, 20);
  assert.ok(pts.length > 0);                          // rng=0 가드(||1) — NaN 없음
  assert.ok(!pts.includes("NaN"));
});

// --- IW1: 자산군 그루핑 + order 정렬 + graceful ---
test("groupPriceCards: group+order → 섹션(라벨=group 그대로), 섹션·카드 order 오름차순", () => {
  const prices = {
    ust10: { group: "금리", order: 21, label: "미 10년" },
    kospi: { group: "지수", order: 11, label: "코스피" },
    ust2:  { group: "금리", order: 20, label: "미 2년" },
    spx:   { group: "지수", order: 10, label: "S&P" },
  };
  const g = groupPriceCards(prices);
  assert.equal(g.grouped, true);
  // 섹션 순서 = 각 group 최소 order(지수=10 < 금리=20) — 웹 하드코딩 없이 order로 도출
  assert.deepEqual(g.sections.map(s => s.label), ["지수", "금리"]);
  // 섹션 내 카드 order 오름차순
  assert.deepEqual(g.sections[0].entries.map(([k]) => k), ["spx", "kospi"]);
  assert.deepEqual(g.sections[1].entries.map(([k]) => k), ["ust2", "ust10"]);
});

test("groupPriceCards: group 부재(구형) → graceful 평면(엔트리 원본 보존, 배포순서 무관)", () => {
  const prices = { a: { label: "A" }, b: { label: "B", order: 3 } };  // group 없음
  const g = groupPriceCards(prices);
  assert.equal(g.grouped, false);
  assert.deepEqual(g.entries.map(([k]) => k), ["a", "b"]);
});

test("groupPriceCards: 일부만 group → 평면(부분 전개 중 혼합 방어), 빈 group 문자열도 평면", () => {
  assert.equal(groupPriceCards({ a: { group: "지수" }, b: { label: "B" } }).grouped, false);
  assert.equal(groupPriceCards({ a: { group: "" } }).grouped, false);   // 빈 문자열은 group 아님
  assert.equal(groupPriceCards({}).grouped, false);                     // 빈 입력
  assert.equal(groupPriceCards(null).grouped, false);
});

test("groupPriceCards: order 부재 카드는 뒤로(Infinity), 동률은 삽입순 유지(안정)", () => {
  const prices = {
    x: { group: "환율", label: "X" },            // order 없음 → 뒤
    y: { group: "환율", order: 5, label: "Y" },
    z: { group: "환율", order: 5, label: "Z" },  // 동률 → 삽입순(y 다음)
  };
  const g = groupPriceCards(prices);
  assert.deepEqual(g.sections[0].entries.map(([k]) => k), ["y", "z", "x"]);
});

console.log(`\nprice_logic: ${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
