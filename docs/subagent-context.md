# 서브에이전트 컨텍스트 주입 (SDD / ultracode)

서브에이전트(Agent tool, Workflow `agent()`)는 **격리 컨텍스트**에서 돈다 — 메인 세션의 `CLAUDE.md`·대화를 자동 상속하지 않는다. "알고 들어가게" 하려면 **명시적으로 주입**해야 한다.

## 무엇을 주입하나 (차등)
| 아티팩트 | 주입? | 방식 |
|---|---|---|
| `coding-principles.md` | ✅ **항상** (작고 ROI 높음·정적 불변식) | 아래 배선 |
| `solved_problems.md`의 **핵심 gotchas** 섹션 | ✅ **항상** | 아래 배선 |
| `solved_problems.md` 전체 아카이브 | ⛔ **통째 X** | 작업이 닿는 영역 항목만 **발췌** 주입 |
| 백로그·🔴 결정 (GitHub Issues) | ⛔ **worker엔 X** | 사용자·오케스트레이터 전용. 🔴는 사용자 승인 게이트 뒤 |

이유: 전체 로그를 모든 병렬 worker에 밀면 토큰 낭비 + 무관 항목이 핵심을 묻어 **adherence 저하**(lost-in-the-middle). 서브에이전트의 lean-context 이점도 깎인다. **관련성 > 분량.**

## 배선 2가지

### (1) 커스텀 에이전트 정의 — 항상 적용 (반복 dispatch에 적합)
`.claude/agents/<name>.md` 본문(=시스템 프롬프트)에 원칙·gotchas를 인라인:
```markdown
---
name: newsstore-impl
description: newsstore 구현 서브에이전트
tools: ["*"]
---
구현 전 반드시 따른다:
- 코드 원칙: (coding-principles.md 핵심 인라인 — SSOT·fail-loud·TDD·Docker-only·비밀분리…)
- 재발 방지 gotchas: (solved_problems.md '핵심 gotchas' 인라인)
```
→ 이 `subagent_type`으로 dispatch하면 자동 적용.

### (2) dispatch 프롬프트에 직접 주입 — ultracode/일회성
```js
const PREAMBLE =
  "[원칙] SSOT·fail-loud·TDD·Docker-only·비파괴·비밀분리.\n" +
  "[gotchas] Docker-only(compose run test) · Firestore to_dict()||{} · PS $h/$H 충돌 · " +
  "Firebase REST x-goog-user-project 헤더 · 인라인주석금지 · 프로덕션 약화금지 · 하드코딩금지(SSOT).\n\n";
agent(PREAMBLE + taskPrompt, { schema, phase });   // Workflow
// 또는 Agent tool prompt 앞에 PREAMBLE 삽입
```

## 금지 / 주의
- **🔴(사용자 결정) 항목을 worker가 자동 구현 → 사고.** 사용자 승인 게이트 필수(원칙 4: 구조가 실수를 막는다).
- **solved 로그를 "현재 규칙"으로 오인 → staleness.** "당시 사실" 프레이밍 유지(예: 이미 제거된 fxstreet를 되살리지 말 것).
- 일반화 가능한 교훈은 `coding-principles.md`로 **승격**하고 solved엔 중복하지 말 것(SSOT).
