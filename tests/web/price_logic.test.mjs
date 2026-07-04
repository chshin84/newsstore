// 가격 탭 순수 로직(값+차트) — index.html PRICE-LOGIC 마커 슬라이스(node 단독).
import { readFileSync } from "node:fs";
import assert from "node:assert/strict";

const html = readFileSync(new URL("../../web/index.html", import.meta.url), "utf8");
const START = "// === PRICE-LOGIC-START", END = "// === PRICE-LOGIC-END";
const i = html.indexOf(START), j = html.indexOf(END);
assert.ok(i !== -1 && j !== -1 && j > i, "PRICE-LOGIC 마커 필요(드리프트 가드)");
const { pctClass, sparkPoints } =
  new Function(html.slice(i, j) + "\nreturn { pctClass, sparkPoints };")();

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

console.log(`\nprice_logic: ${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
