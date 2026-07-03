// 리포트 탭 순수 로직 — index.html REPORT-LOGIC 마커 슬라이스(node 단독).
import { readFileSync } from "node:fs";
import assert from "node:assert/strict";

const html = readFileSync(new URL("../../web/index.html", import.meta.url), "utf8");
const START = "// === REPORT-LOGIC-START", END = "// === REPORT-LOGIC-END";
const i = html.indexOf(START), j = html.indexOf(END);
assert.ok(i !== -1 && j !== -1 && j > i, "REPORT-LOGIC 마커 필요(드리프트 가드)");
const { assembleReportDoc, reportStatus, crossLinks, dedupCards } =
  new Function(html.slice(i, j) +
    "\nreturn { assembleReportDoc, reportStatus, crossLinks, dedupCards };")();

let pass = 0, fail = 0;
const test = (n, f) => { try { f(); pass++; } catch (e) { fail++; console.error("FAIL:", n, "\n ", e.message); } };
const NOW = Date.UTC(2026, 6, 4, 12, 0, 0);
const rep = (topic, over = {}) => ({ topic, headline: "h", lead: "l",
  sections: [{ name: "risk_triggered", items: [{ text: "x", story_ids: ["s1"], pole_id: "r1" }] }],
  generated_at: new Date(NOW - 3600e3), review: { passed: true }, ...over });

test("assembleReportDoc: 그룹 순서 + 백드롭 서두 + rising 말미", () => {
  // m1: groups는 순서 보존 배열([{name, lens_ids}]) — Firestore map 키 정렬 회피
  const groups = [{ name: "주식", lens_ids: ["kr_equity", "us_equity"] },
                  { name: "코인", lens_ids: ["crypto"] }];
  const reports = { kr_equity: rep("kr_equity"), crypto: rep("crypto"),
                    rising: rep("rising"), _backdrop: { text: "bd" } };
  const doc = assembleReportDoc(groups, reports);
  assert.equal(doc.backdrop, "bd");
  assert.deepEqual(doc.sections.map(s => s.lensId), ["kr_equity", "crypto", "rising"]);
  assert.equal(doc.sections[0].group, "주식");          // us_equity 리포트 없음 → 생략(fail-soft)
});

test("reportStatus: 정상/생성전/갱신지연/오늘스킵 4구분", () => {
  assert.equal(reportStatus(rep("x"), NOW, false), "ok");
  assert.equal(reportStatus(null, NOW, false), "not_generated");             // §4 빈 스킵
  assert.equal(reportStatus(rep("x", { generated_at: new Date(NOW - 26 * 3600e3) }), NOW, false),
               "stale");                                                     // §5(b) 1일 초과
  // M5: 오늘 런이 스토리 부족으로 스킵 + 문서가 낡음 → "갱신 지연" 아닌 "오늘 스토리 부족"
  assert.equal(reportStatus(rep("x", { generated_at: new Date(NOW - 26 * 3600e3) }), NOW, true),
               "skipped_today");
  assert.equal(reportStatus(rep("x"), NOW, true), "ok"); // 신선하면 스킵 표기 불필요
});

test("crossLinks: 같은 스토리 다중 섹션 인용 → 상호 링크", () => {
  const secs = [{ lensId: "kr_equity", report: rep("kr_equity") },
                { lensId: "us_policy", report: rep("us_policy") }];
  const links = crossLinks(secs);                       // s1이 두 섹션에 인용됨
  assert.deepEqual(links["s1"].sort(), ["kr_equity", "us_policy"]);
});

test("dedupCards: 문서 전체에서 카드 1회, 재인용은 참조 배지", () => {
  const order = ["s1", "s2", "s1"];
  const d = dedupCards(order);
  assert.deepEqual(d, [{ id: "s1", first: true }, { id: "s2", first: true },
                       { id: "s1", first: false }]);
});

console.log(`\nreport_logic: ${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
