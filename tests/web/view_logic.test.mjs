// WV1 뷰 라우팅 순수 로직 — index.html VIEW-LOGIC 마커 슬라이스(node 단독).
import { readFileSync } from "node:fs";
import assert from "node:assert/strict";

const html = readFileSync(new URL("../../web/index.html", import.meta.url), "utf8");
const START = "// === VIEW-LOGIC-START", END = "// === VIEW-LOGIC-END";
const i = html.indexOf(START), j = html.indexOf(END);
assert.ok(i !== -1 && j !== -1 && j > i, "VIEW-LOGIC 마커 필요(드리프트 가드)");
const { parseHashView, resolveView, withView, VIEWS } =
  new Function(html.slice(i, j) + "\nreturn { parseHashView, resolveView, withView, VIEWS };")();

let pass = 0, fail = 0;
const test = (n, f) => { try { f(); pass++; } catch (e) { fail++; console.error("FAIL:", n, "\n ", e.message); } };

test("parseHashView: 라우트/뷰 분해 — &v2 토큰이 뷰, 없으면 null", () => {
  assert.deepEqual(parseHashView("#report&v2"), { route: "#report", view: "v2" });
  assert.deepEqual(parseHashView("#report"), { route: "#report", view: null });
  assert.deepEqual(parseHashView("#story-abc&v2"), { route: "#story-abc", view: "v2" });
  assert.deepEqual(parseHashView("#rep-kr_equity&v1"), { route: "#rep-kr_equity", view: "v1" });
  assert.deepEqual(parseHashView(""), { route: "", view: null });
  assert.deepEqual(parseHashView("#report&v2&junk"), { route: "#report", view: "v2" });   // 알 수 없는 토큰 무시
  assert.deepEqual(parseHashView(null), { route: "", view: null });                        // null 방어
});

test("resolveView: URL 명시 > 저장값 > 기본 v1 (딥링크가 저장값을 이겨 수신자 강등 방지)", () => {
  assert.equal(resolveView("v2", "v1"), "v2");    // URL이 저장값을 이김(공유 링크 재현)
  assert.equal(resolveView(null, "v2"), "v2");    // URL 없으면 저장값(새로고침 유지)
  assert.equal(resolveView(null, null), "v1");    // 둘 다 없으면 기본
  assert.equal(resolveView("bogus", "v2"), "v2"); // 잘못된 URL 값 무시 → 저장값
  assert.equal(resolveView(null, "bogus"), "v1"); // 잘못된 저장값 무시 → 기본
});

test("withView: v2만 토큰 부착(v1 기본은 URL 청결·기존 링크 보존)", () => {
  assert.equal(withView("#report", "v2"), "#report&v2");
  assert.equal(withView("#report", "v1"), "#report");
  assert.equal(withView("#report&v2", "v1"), "#report");      // 기존 토큰 제거
  assert.equal(withView("#stories&v2", "v2"), "#stories&v2"); // 멱등(중복 부착 없음)
});

test("라운드트립: withView→parseHashView가 라우트·뷰 보존(딥링크 공유 재현)", () => {
  for (const v of VIEWS) for (const r of ["#report", "#stories"]) {
    const p = parseHashView(withView(r, v));
    assert.equal(p.route, r);
    assert.equal(resolveView(p.view, null), v);   // v1은 토큰이 없어도 resolve가 기본으로 복원
  }
});

console.log(`\nview_logic: ${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
