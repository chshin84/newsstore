// 피드 kind 필터 순수 로직 검증(node 단독, 브라우저/에뮬레이터 불필요).
// web/index.html의 FEED-LOGIC 마커 블록을 '문자열 슬라이스'해 eval → 배포되는 코드를 그대로 검증
// (복붙 드리프트 불가 — 단일 출처). 실행: node tests/web/feed_logic.test.mjs
import { readFileSync } from "node:fs";
import assert from "node:assert/strict";

const html = readFileSync(new URL("../../web/index.html", import.meta.url), "utf8");
const START = "// === FEED-LOGIC-START";
const END = "// === FEED-LOGIC-END";
const i = html.indexOf(START), j = html.indexOf(END);
assert.ok(i !== -1 && j !== -1 && j > i, "FEED-LOGIC 마커가 index.html에 있어야 한다(드리프트 가드)");
const block = html.slice(i, j);
const { keepInFeed } = new Function(block + "\nreturn { keepInFeed };")();

let pass = 0, fail = 0;
const test = (name, fn) => { try { fn(); pass++; } catch (e) { fail++; console.error("FAIL:", name, "\n ", e.message); } };

// spam·digest = 백엔드 kind로 숨김
test("spam → 숨김", () => assert.equal(keepInFeed({ kind: "spam" }), false));
test("digest → 숨김", () => assert.equal(keepInFeed({ kind: "digest" }), false));
// story·미인리치·미지값 = 노출(fail-soft: 분석 멈춰도 raw 뉴스 보임)
test("story → 노출", () => assert.equal(keepInFeed({ kind: "story" }), true));
test("kind 없음(미인리치 fresh) → 노출", () => assert.equal(keepInFeed({ title: "x" }), true));
test("미지 kind → 노출", () => assert.equal(keepInFeed({ kind: "weird" }), true));
// 강건성: null/undefined item도 throw 없이
test("null/undefined item → throw 없이 노출", () => {
  assert.equal(keepInFeed(null), true);
  assert.equal(keepInFeed(undefined), true);
});

console.log(`\nfeed_logic: ${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
