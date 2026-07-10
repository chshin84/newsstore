// 리포트 탭 순수 로직 — index.html REPORT-LOGIC 마커 슬라이스(node 단독).
import { readFileSync } from "node:fs";
import assert from "node:assert/strict";

const html = readFileSync(new URL("../../web/index.html", import.meta.url), "utf8");
const START = "// === REPORT-LOGIC-START", END = "// === REPORT-LOGIC-END";
const i = html.indexOf(START), j = html.indexOf(END);
assert.ok(i !== -1 && j !== -1 && j > i, "REPORT-LOGIC 마커 필요(드리프트 가드)");
const { assembleReportDoc, reportStatus, crossLinks, dedupCards,
        divergenceChip, convictionPill, normalizeHeadline, dedupEvidence,
        splitReportSections, leadItems, reportNavLenses,
        moveBand, unexplainedQueue, reportV2Empty, dmetaCaption } =
  new Function(html.slice(i, j) +
    "\nreturn { assembleReportDoc, reportStatus, crossLinks, dedupCards," +
    " divergenceChip, convictionPill, normalizeHeadline, dedupEvidence," +
    " splitReportSections, leadItems, reportNavLenses," +
    " moveBand, unexplainedQueue, reportV2Empty, dmetaCaption };")();

let pass = 0, fail = 0;
const test = (n, f) => { try { f(); pass++; } catch (e) { fail++; console.error("FAIL:", n, "\n ", e.message); } };
const NOW = Date.UTC(2026, 6, 4, 12, 0, 0);
const rep = (topic, over = {}) => ({ topic, headline: "h", lead: "l",
  sections: [{ name: "risk_triggered", items: [{ text: "x", story_ids: ["s1"], pole_id: "r1" }] }],
  generated_at: new Date(NOW - 3600e3), review: { passed: true }, ...over });

test("assembleReportDoc: 급부상 최상단 + 그룹 순서 + 백드롭 서두 (WW4 — rising 항상 맨 위)", () => {
  // m1: groups는 순서 보존 배열([{name, lens_ids}]) — Firestore map 키 정렬 회피
  const groups = [{ name: "리스크", lens_ids: ["risk"] },
                  { name: "주식", lens_ids: ["kr_equity", "us_equity"] }];
  const reports = { risk: rep("risk"), kr_equity: rep("kr_equity"),
                    rising: rep("rising"), _backdrop: { text: "bd" } };
  const doc = assembleReportDoc(groups, reports);
  assert.equal(doc.backdrop, "bd");
  // UI 순서 규칙①(2026-07-05): 급부상 → 그룹 순서(리스크 → 주식)
  assert.deepEqual(doc.sections.map(s => s.lensId), ["rising", "risk", "kr_equity"]);
  assert.equal(doc.sections[0].group, "급부상");        // us_equity 리포트 없음 → 생략(fail-soft)
});

test("assembleReportDoc: rising 없으면 그룹 순서만 (최상단 규칙은 rising 존재 시에만)", () => {
  const groups = [{ name: "리스크", lens_ids: ["risk"] },
                  { name: "주식", lens_ids: ["kr_equity"] }];
  const doc = assembleReportDoc(groups, { risk: rep("risk"), kr_equity: rep("kr_equity") });
  assert.deepEqual(doc.sections.map(s => s.lensId), ["risk", "kr_equity"]);
});

test("splitReportSections: 트리거+주시 상단 유지 · 미발생만 최하단(사용자: 주시 숨기지 마)", () => {
  const sections = [
    { name: "not_triggered", items: [{ text: "n" }] },
    { name: "risk_triggered", items: [{ text: "r" }] },
    { name: "watchpoints", items: [{ text: "w" }] },
    { name: "premium_triggered", items: [{ text: "p" }] },
  ];
  const { top, bottom } = splitReportSections(sections);
  // 상단 = 미발생 제외 전부(원래 순서 보존 — 주시 포함), 하단 = 미발생만
  assert.deepEqual(top.map(s => s.name), ["risk_triggered", "watchpoints", "premium_triggered"]);
  assert.deepEqual(bottom.map(s => s.name), ["not_triggered"]);
});

test("splitReportSections: 미발생만 있어도 하단, 알 수 없는 섹션은 상단(가시 유지) · 빈 입력 방어", () => {
  const { top, bottom } = splitReportSections([
    { name: "not_triggered" }, { name: "mystery" }]);
  assert.deepEqual(top.map(s => s.name), ["mystery"]);
  assert.deepEqual(bottom.map(s => s.name), ["not_triggered"]);
  assert.deepEqual(splitReportSections(null), { top: [], bottom: [] });
});

test("leadItems: 배열→불릿(빈 문자열 제거), 문자열→산문 폴백, null 방어 — WW6 graceful", () => {
  assert.deepEqual(leadItems(["a", "", "  ", "b"]), { mode: "bullets", items: ["a", "b"] });
  assert.deepEqual(leadItems([]), { mode: "bullets", items: [] });
  assert.deepEqual(leadItems("산문 리드"), { mode: "prose", text: "산문 리드" });
  assert.deepEqual(leadItems(null), { mode: "prose", text: "" });
  assert.deepEqual(leadItems(undefined), { mode: "prose", text: "" });
  // 계약 위반 입력(객체) 방어: "[object Object]" 노출 금지 — 배열 속 객체는 드롭, 통째 객체는 빈 산문
  assert.deepEqual(leadItems(["ok", { x: 1 }]), { mode: "bullets", items: ["ok"] });
  assert.deepEqual(leadItems({ x: 1 }), { mode: "prose", text: "" });
});

test("reportNavLenses: docm.sections 순서에서 렌즈 평면화(그룹 헤더 없음) — WW5 SSOT", () => {
  const docm = { sections: [{ lensId: "rising" }, { lensId: "risk" }, { lensId: "kr_equity" }] };
  assert.deepEqual(reportNavLenses(docm), ["rising", "risk", "kr_equity"]);
  assert.deepEqual(reportNavLenses({}), []);
  assert.deepEqual(reportNavLenses(null), []);
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

test("dedupCards: 한 리포트 내 카드 1회, 재인용은 참조 배지 (스코프=단일 리포트 — 참조가 리포트를 벗어나면 안 됨)", () => {
  const order = ["s1", "s2", "s1"];
  const d = dedupCards(order);
  assert.deepEqual(d, [{ id: "s1", first: true }, { id: "s2", first: true },
                       { id: "s1", first: false }]);
});

test("divergenceChip: over_fear/over_hope만 재료칩, aligned/none/부재는 생략(fail-soft)", () => {
  const fear = divergenceChip({ kind: "over_fear", price_key: "EWY", price_pct: -1.2, note: "가격은 덜 빠짐" });
  assert.ok(fear && /과도한 공포/.test(fear.label));
  assert.equal(fear.price_key, "EWY");
  assert.equal(fear.price_pct, -1.2);
  assert.equal(fear.note, "가격은 덜 빠짐");
  assert.ok(/과도한 기대/.test(divergenceChip({ kind: "over_hope" }).label));
  assert.equal(divergenceChip({ kind: "aligned" }), null);   // 정합은 칩 없음
  assert.equal(divergenceChip({ kind: "none" }), null);
  assert.equal(divergenceChip(null), null);                  // A 미발행(옛 문서·가격 없는 렌즈) → 생략
  assert.equal(divergenceChip({}), null);
  // price_pct 부재·비수치 → null(칩은 나오되 % 생략)
  assert.equal(divergenceChip({ kind: "over_fear" }).price_pct, null);
  assert.equal(divergenceChip({ kind: "over_fear", price_pct: "x" }).price_pct, null);
});

test("convictionPill: high/medium/low만 등급, 부재/미지 레벨은 생략(fail-soft)", () => {
  assert.equal(convictionPill({ level: "high", basis: "3개 지표 일치" }).label, "확신 높음");
  assert.equal(convictionPill({ level: "high" }).basis, "");   // basis 부재 → 빈 문자열(툴팁 안전)
  assert.equal(convictionPill({ level: "medium" }).label, "확신 중간");
  assert.equal(convictionPill({ level: "low" }).level, "low");
  assert.equal(convictionPill(null), null);                    // A 미발행 → 생략
  assert.equal(convictionPill({ level: "bogus" }), null);      // 미지 레벨 → 생략(계약 밖 값 방어)
  assert.equal(convictionPill({}), null);
});

test("normalizeHeadline: 대소문자·공백·문장부호 무시 정규화(내용 dedup 키)", () => {
  assert.equal(normalizeHeadline("Fed  Cuts   Rates!"), normalizeHeadline("fed cuts rates"));
  assert.equal(normalizeHeadline("  A, B: C  "), "a b c");   // 문장부호→공백→collapse→trim
  assert.equal(normalizeHeadline("한국 <b>금리</b> 인하"), "한국 금리 인하");   // 태그 제거, 한글 보존
  assert.equal(normalizeHeadline(null), "");
});

test("dedupEvidence: 근접중복 헤드라인 병합 + 출처 다양성 보존 · 빈도컷 없음(특종 생존)", () => {
  const items = [
    { title: "Fed cuts rates", source: "Bloomberg", url: "u1" },
    { title: "FED CUTS RATES!", source: "Reuters", url: "u2" },   // 정규화 동일 → 병합
    { title: "Fed cuts rates", source: "Bloomberg", url: "u3" },  // 또 병합(count 누적)
    { title: "Rare BOK scoop", source: "Bloomberg", url: "u4" },  // 저빈도 특종 — 묻히면 안 됨
  ];
  const { reps, total, unique } = dedupEvidence(items);
  assert.equal(total, 4);
  assert.equal(unique, 2);
  assert.equal(reps.length, 2);
  // 불변식: 고유 정규화 헤드라인이 정확히 1회씩(빈도컷으로 드롭 없음 — 매직넘버 없음)
  const keys = new Set(reps.map(r => normalizeHeadline(r.title)));
  assert.equal(keys.size, 2);
  assert.ok(keys.has(normalizeHeadline("Rare BOK scoop")));       // 블룸버그 전례: 특종 생존
  const fed = reps.find(r => normalizeHeadline(r.title) === normalizeHeadline("fed cuts rates"));
  assert.equal(fed.count, 3);                                     // 3건 병합됐음을 표기
  assert.deepEqual(fed.sources.slice().sort(), ["Bloomberg", "Reuters"]);  // 출처 다양성 보존
  assert.equal(reps[0].title, "Fed cuts rates");                 // 첫 등장 순서 보존
});

test("dedupEvidence: 빈 제목은 병합 금지(정보 손실 방지) · 빈 입력 방어", () => {
  const { reps, unique } = dedupEvidence([
    { title: "", source: "A", url: "a" }, { title: "", source: "B", url: "b" }]);
  assert.equal(unique, 2);                                        // 빈 제목끼리 병합 안 함
  assert.equal(reps.length, 2);
  assert.deepEqual(dedupEvidence(null), { reps: [], total: 0, unique: 0 });
  assert.deepEqual(dedupEvidence([]), { reps: [], total: 0, unique: 0 });
});

// --- WV3/WV4: 리포트 v2 (설명 안 되는 움직임 조사 큐) ---
test("moveBand: z 우선(없으면 pct 폴백) 방향+버킷, 정밀 수치 노출 금지", () => {
  assert.equal(moveBand(1.5, null).dir, "up");
  assert.equal(moveBand(1.5, null).text, "다소 큰 이동");   // |z|<2
  assert.equal(moveBand(2.5, null).text, "큰 이동");        // 2~3
  assert.equal(moveBand(-4, null).dir, "down");
  assert.equal(moveBand(-4, null).text, "매우 큰 이동");    // 3+
  assert.equal(moveBand(null, 5).text, "큰 이동");          // z 없음 → pct 폴백(3~8)
  assert.equal(moveBand(null, 12).text, "매우 큰 이동");    // pct 8+
  assert.equal(moveBand(null, null), null);                // 둘 다 없음 → 생략
  // 불변식: 밴드에 raw 숫자가 새지 않는다
  for (const [z, p] of [[1.7, null], [null, 6.3]]) assert.ok(!/\d/.test(moveBand(z, p).text));
});

test("unexplainedQueue: 백엔드 rank 배열 순서 그대로 소비(재정렬 금지 — SSOT)", () => {
  const sig = { generated_at: NOW, min_sample_ok: true, items: [
    { ticker: "EWY", label: "한국 ETF", kind: "equity", move_z: 3.1, vol_confirmed: true, story_coverage: false, rank: 1 },
    { key: "USDKRW", label: "원달러", kind: "fx", move_z: 2.2, vol_confirmed: null, story_coverage: false, rank: 2 },
    { ticker: "ZZZ", label: "후순위", kind: "equity", move_z: 5.0, vol_confirmed: false, story_coverage: true, rank: 3 },
  ] };
  const q = unexplainedQueue(sig);
  assert.deepEqual(q.items.map(x => x.key), ["EWY", "USDKRW", "ZZZ"]);   // 입력(rank) 순서 보존
  // move_z가 더 큰 ZZZ(5.0)가 뒤에 있어도 재정렬하지 않음 — 백엔드 rank 신뢰
  assert.equal(q.items[0].volConfirmed, true);
  assert.equal(q.items[1].volConfirmed, null);                          // FX → 거래량 표기 생략 seam
  assert.equal(q.items[2].volConfirmed, false);
  assert.equal(q.items[1].move.text, "큰 이동");
  assert.equal(q.minSampleOk, true);
});

test("unexplainedQueue: min_sample_ok=false 전달, 부재/형식오류 graceful null", () => {
  assert.equal(unexplainedQueue({ items: [{ ticker: "A" }], min_sample_ok: false }).minSampleOk, false);
  assert.equal(unexplainedQueue({ items: [{ ticker: "A" }] }).minSampleOk, true);   // 부재 → ok(기본)
  assert.equal(unexplainedQueue(null), null);
  assert.equal(unexplainedQueue({}), null);                             // items 없음
  assert.equal(unexplainedQueue({ items: "x" }), null);                 // 계약 위반 방어
  const q = unexplainedQueue({ items: [{ rank: 1 }] });                 // 라벨 없는 항목
  assert.equal(q.items[0].label, "");                                   // "[object Object]" 노출 없음
  assert.equal(q.items[0].move, null);
});

test("reportV2Empty: 큐 없거나 비면 true(빈상태 안내 트리거)", () => {
  assert.equal(reportV2Empty(null), true);
  assert.equal(reportV2Empty({ items: [] }), true);
  assert.equal(reportV2Empty({ items: [{ key: "A" }] }), false);
});

// --- IW2: dmeta 캡션 vs divergence 모순 해소(배지 유무 분기) ---
test("dmetaCaption: divergence 배지 있으면 '가격 미반영' 단정 생략(모순 제거)", () => {
  const divHtml = `<span class="divchip">과도한 공포 · EWY -1.2%</span>`;
  assert.equal(dmetaCaption(divHtml), "");                   // 배지 존재 → 문구 없음
});

test("dmetaCaption: 배지 없는 카드는 기존 캡션 유지(깨끗한 신호 보존)", () => {
  assert.equal(dmetaCaption(""), " · 가격 미반영(이슈 중심)");   // divHtml="" (배지 없음)
  assert.equal(dmetaCaption(null), " · 가격 미반영(이슈 중심)");
  assert.equal(dmetaCaption(undefined), " · 가격 미반영(이슈 중심)");
});

console.log(`\nreport_logic: ${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
