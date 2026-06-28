# Step-2 인리치먼트 — Plan 2: Store 확장 (stories + item enrichment) 구현 계획

> ⚠️ **부분 분할 (2026-06-28):** 이 문서가 추가한 **인리치 store 메서드(`save_enrichment`·`stories` CRUD·요약)는 `news-analytics` 경계**다 — 분리 시 `ports.py`에서 분할 대상. 그 부분의 SSOT는 **`docs/firestore-contract.md`**. 수집 store 메서드만 newsstore 유효.

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development.
> **SDD 시 각 서브에이전트에 `coding-principles` + `solved_problems`의 '핵심 gotchas'를 주입**(`docs/subagent-context.md`). unsolved는 주입 X.

**Goal:** Store 계층에 Step-2용 영속성 추가 — 기사 enrichment 쓰기(kind/tags/embedding/story_id) + `stories`(centroid 증분 sum/count) + 열린 스토리 조회/마감.

**Architecture:** 기존 `Store` Protocol(`base.py`)에 5개 메서드 추가, `SqliteStore`·`FirestoreStore` 양쪽 구현. 벡터·시각은 *입력*으로 받음(클러스터 판단은 Plan 1 `assign`이 함). sqlite는 JSON 컬럼, firestore는 네이티브 배열. mock-firestore + sqlite로 테스트.

**Tech Stack:** Python 3.12, sqlite3/google-cloud-firestore(mock-firestore 테스트), pytest, Docker(`docker compose run --rm test`).

**Spec:** `docs/superpowers/specs/2026-06-13-newsstore-step2-enrichment-design.md` §4 데이터모델, §7 클러스터, §11 Store 확장.

**테스트:** `docker compose run --rm test pytest -q <파일>` (전체 `docker compose run --rm test`).

---

## Protocol 메서드 (이 Plan에서 추가)
```python
def save_enrichment(self, item_id, *, kind, tags, embedding, story_id) -> None
def get_open_stories(self, cutoff: datetime) -> list[dict]      # [{"id":str,"centroid":list[float]}]
def create_story(self, story_id, *, title, vec, member_id, entities, now) -> None
def append_to_story(self, story_id, *, vec, member_id, entities, now) -> None
def close_stale_stories(self, cutoff: datetime) -> int
```

## File Structure
- Modify `src/newsstore/store/base.py` — Protocol에 5개 추가.
- Modify `src/newsstore/store/sqlite_store.py` — stories 테이블 + items enrichment 컬럼 + 구현.
- Modify `src/newsstore/store/firestore_store.py` — stories 컬렉션 + 구현.
- Create `tests/test_store_stories.py` — stories 양쪽 스토어 테스트.
- Create `tests/test_store_enrichment.py` — save_enrichment 양쪽 테스트.

---

## Task 1: stories — create / append (centroid 증분), 양쪽 스토어

**Files:** Modify `base.py`, `sqlite_store.py`, `firestore_store.py`; Create `tests/test_store_stories.py`.

- [ ] **Step 1: 실패 테스트** — `tests/test_store_stories.py`:
```python
from datetime import datetime, timezone
from mockfirestore import MockFirestore
from newsstore.store.sqlite_store import SqliteStore
from newsstore.store.firestore_store import FirestoreStore

NOW = datetime(2026, 6, 13, 7, 0, tzinfo=timezone.utc)

def _sql(tmp_path): return SqliteStore(tmp_path / "db.sqlite")
def _fs(): return FirestoreStore(MockFirestore())

def _check_create_append(s):
    s.create_story("st1", title="Iran deal", vec=[2.0, 0.0], member_id="a",
                   entities=["geopolitics"], now=NOW)
    s.append_to_story("st1", vec=[0.0, 2.0], member_id="b",
                      entities=["oil"], now=NOW)
    # centroid = (sum [2,2]) / count 2 = [1,1]
    open_now = s.get_open_stories(cutoff=NOW)
    st = [x for x in open_now if x["id"] == "st1"][0]
    assert st["centroid"] == [1.0, 1.0]

def test_sqlite_create_append(tmp_path):
    _check_create_append(_sql(tmp_path))

def test_firestore_create_append():
    _check_create_append(_fs())
```

- [ ] **Step 2: 실패 확인**
Run: `docker compose run --rm test pytest -q tests/test_store_stories.py`
Expected: FAIL — `AttributeError: ... has no attribute 'create_story'`.

- [ ] **Step 3: 구현**

`base.py` — Protocol에 추가(`mark_processed` 아래, `set_meta` 위 등 클래스 내부):
```python
    def get_open_stories(self, cutoff) -> list[dict]:
        """status=open이고 last_seen>=cutoff인 스토리: [{'id','centroid'}]. centroid=sum/count."""
        ...
    def create_story(self, story_id, *, title, vec, member_id, entities, now) -> None:
        """새 스토리: centroid_sum=vec, count=1, member_ids=[member_id], status=open."""
        ...
    def append_to_story(self, story_id, *, vec, member_id, entities, now) -> None:
        """centroid_sum+=vec, count+=1, member_ids+=member_id, entities∪=, last_seen=now."""
        ...
```

`sqlite_store.py` — `_SCHEMA`의 meta 테이블 줄 아래에 추가:
```python
CREATE TABLE IF NOT EXISTS stories (
  id TEXT PRIMARY KEY, title TEXT, centroid_sum TEXT, count INTEGER,
  member_ids TEXT, entities TEXT, first_seen TEXT, last_seen TEXT, status TEXT
);
```
그리고 `set_meta` 메서드 아래에 추가:
```python
    def create_story(self, story_id, *, title, vec, member_id, entities, now) -> None:
        self.conn.execute(
            "INSERT INTO stories (id,title,centroid_sum,count,member_ids,entities,first_seen,last_seen,status) "
            "VALUES (?,?,?,?,?,?,?,?, 'open')",
            (story_id, title, json.dumps(list(vec)), 1, json.dumps([member_id]),
             json.dumps(list(entities)), now.isoformat(), now.isoformat()))
        self.conn.commit()

    def append_to_story(self, story_id, *, vec, member_id, entities, now) -> None:
        row = self.conn.execute(
            "SELECT centroid_sum,count,member_ids,entities FROM stories WHERE id=?",
            (story_id,)).fetchone()
        csum = [a + b for a, b in zip(json.loads(row["centroid_sum"]), vec)]
        members = json.loads(row["member_ids"]) + [member_id]
        ents = list(dict.fromkeys(json.loads(row["entities"]) + list(entities)))
        self.conn.execute(
            "UPDATE stories SET centroid_sum=?, count=?, member_ids=?, entities=?, last_seen=? WHERE id=?",
            (json.dumps(csum), row["count"] + 1, json.dumps(members), json.dumps(ents),
             now.isoformat(), story_id))
        self.conn.commit()

    def get_open_stories(self, cutoff) -> list[dict]:
        out = []
        for r in self.conn.execute(
                "SELECT id,centroid_sum,count,last_seen FROM stories WHERE status='open'"):
            if datetime.fromisoformat(r["last_seen"]) >= cutoff:
                csum = json.loads(r["centroid_sum"]); c = r["count"]
                out.append({"id": r["id"], "centroid": [x / c for x in csum]})
        return out
```

`firestore_store.py` — `set_meta` 아래에 추가:
```python
    def create_story(self, story_id, *, title, vec, member_id, entities, now) -> None:
        self.db.collection("stories").document(story_id).set({
            "title": title, "centroid_sum": list(vec), "count": 1,
            "member_ids": [member_id], "entities": list(entities),
            "first_seen": now, "last_seen": now, "status": "open",
        })

    def append_to_story(self, story_id, *, vec, member_id, entities, now) -> None:
        ref = self.db.collection("stories").document(story_id)
        d = ref.get().to_dict() or {}
        csum = [a + b for a, b in zip(d.get("centroid_sum", []), vec)]
        members = list(d.get("member_ids", [])) + [member_id]
        ents = list(dict.fromkeys(list(d.get("entities", [])) + list(entities)))
        d.update({"centroid_sum": csum, "count": d.get("count", 0) + 1,
                  "member_ids": members, "entities": ents, "last_seen": now})
        ref.set(d)

    def get_open_stories(self, cutoff) -> list[dict]:
        out = []
        for snap in self.db.collection("stories").where("status", "==", "open").stream():
            d = snap.to_dict() or {}
            if d.get("last_seen") and d["last_seen"] >= cutoff:
                c = d.get("count", 1) or 1
                out.append({"id": snap.id, "centroid": [x / c for x in d.get("centroid_sum", [])]})
        return out
```

- [ ] **Step 4: 통과 확인**
Run: `docker compose run --rm test pytest -q tests/test_store_stories.py`
Expected: PASS (2 passed).

- [ ] **Step 5: 커밋**
```bash
git add src/newsstore/store/base.py src/newsstore/store/sqlite_store.py src/newsstore/store/firestore_store.py tests/test_store_stories.py
git commit -m "feat: stories storage — create/append (centroid sum/count) + get_open_stories"
```

---

## Task 2: close_stale_stories (양쪽 스토어)

**Files:** Modify `base.py`, `sqlite_store.py`, `firestore_store.py`, `tests/test_store_stories.py`.

- [ ] **Step 1: 실패 테스트 추가** — `tests/test_store_stories.py`에 추가:
```python
from datetime import timedelta

def _check_close(s):
    s.create_story("old", title="t", vec=[1.0], member_id="a", entities=[], now=NOW)
    s.create_story("new", title="t", vec=[1.0], member_id="b", entities=[],
                   now=NOW + timedelta(hours=30))
    # cutoff = NOW+24h → 'old'(last_seen=NOW)는 stale, 'new'(NOW+30h)는 유효
    closed = s.close_stale_stories(cutoff=NOW + timedelta(hours=24))
    assert closed == 1
    open_ids = {x["id"] for x in s.get_open_stories(cutoff=NOW - timedelta(hours=1))}
    assert open_ids == {"new"}

def test_sqlite_close_stale(tmp_path):
    _check_close(_sql(tmp_path))

def test_firestore_close_stale():
    _check_close(_fs())
```

- [ ] **Step 2: 실패 확인**
Run: `docker compose run --rm test pytest -q tests/test_store_stories.py::test_sqlite_close_stale`
Expected: FAIL — `AttributeError: ...close_stale_stories`.

- [ ] **Step 3: 구현**

`base.py` Protocol에 추가:
```python
    def close_stale_stories(self, cutoff) -> int:
        """last_seen<cutoff인 open 스토리를 closed로. 변경 수 반환."""
        ...
```

`sqlite_store.py`에 추가:
```python
    def close_stale_stories(self, cutoff) -> int:
        n = 0
        for r in self.conn.execute("SELECT id,last_seen FROM stories WHERE status='open'"):
            if datetime.fromisoformat(r["last_seen"]) < cutoff:
                self.conn.execute("UPDATE stories SET status='closed' WHERE id=?", (r["id"],))
                n += 1
        self.conn.commit()
        return n
```

`firestore_store.py`에 추가:
```python
    def close_stale_stories(self, cutoff) -> int:
        n = 0
        col = self.db.collection("stories")
        for snap in col.where("status", "==", "open").stream():
            d = snap.to_dict() or {}
            if d.get("last_seen") and d["last_seen"] < cutoff:
                d["status"] = "closed"
                col.document(snap.id).set(d)
                n += 1
        return n
```

- [ ] **Step 4: 통과 확인**
Run: `docker compose run --rm test pytest -q tests/test_store_stories.py`
Expected: PASS (4 passed).

- [ ] **Step 5: 커밋**
```bash
git add src/newsstore/store/base.py src/newsstore/store/sqlite_store.py src/newsstore/store/firestore_store.py tests/test_store_stories.py
git commit -m "feat: close_stale_stories (idle stories -> closed)"
```

---

## Task 3: item save_enrichment (kind/tags/embedding/story_id), 양쪽 스토어

**Files:** Modify `base.py`, `sqlite_store.py`(컬럼 마이그레이션), `firestore_store.py`; Create `tests/test_store_enrichment.py`.

- [ ] **Step 1: 실패 테스트** — `tests/test_store_enrichment.py`:
```python
import json
from datetime import datetime, timezone
from mockfirestore import MockFirestore
from newsstore.models import RawItem
from newsstore.store.sqlite_store import SqliteStore
from newsstore.store.firestore_store import FirestoreStore

NOW = datetime(2026, 6, 13, 7, 0, tzinfo=timezone.utc)

def _item(i="a"):
    return RawItem(id=i, feed_id="f1", source="S", url=f"https://e/{i}", title="t", body="b", fetched_at=NOW)

def test_sqlite_save_enrichment(tmp_path):
    s = SqliteStore(tmp_path / "db.sqlite")
    s.upsert_items([_item("a")])
    s.save_enrichment("a", kind="story", tags=["NVDA", "rates"], embedding=[0.1, 0.2], story_id="st1")
    row = s.conn.execute(
        "SELECT kind,tags,embedding,story_id FROM raw_items WHERE id='a'").fetchone()
    assert row["kind"] == "story"
    assert json.loads(row["tags"]) == ["NVDA", "rates"]
    assert json.loads(row["embedding"]) == [0.1, 0.2]
    assert row["story_id"] == "st1"

def test_firestore_save_enrichment_preserves_fields():
    s = FirestoreStore(MockFirestore())
    s.upsert_items([_item("a")])
    s.save_enrichment("a", kind="spam", tags=[], embedding=None, story_id=None)
    d = s.db.collection("items").document("a").get().to_dict()
    assert d["kind"] == "spam" and d["title"] == "t"   # 기존 필드 보존
```

- [ ] **Step 2: 실패 확인**
Run: `docker compose run --rm test pytest -q tests/test_store_enrichment.py`
Expected: FAIL — `AttributeError: ...save_enrichment`.

- [ ] **Step 3: 구현**

`base.py` Protocol에 추가:
```python
    def save_enrichment(self, item_id, *, kind, tags, embedding, story_id) -> None:
        """기사에 Step-2 인리치 필드 기록(kind/tags/embedding/story_id). 기존 필드 보존."""
        ...
```

`sqlite_store.py` — `_migrate()`의 `if version < 1:` 블록 뒤(또는 `_migrate` 끝, commit 전)에 enrichment 컬럼 추가:
```python
    # Step-2 enrichment 컬럼 (없으면 추가)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(raw_items)")}
    for col, decl in [("kind", "TEXT"), ("tags", "TEXT"), ("embedding", "TEXT"), ("story_id", "TEXT")]:
        if col not in cols:
            conn.execute(f"ALTER TABLE raw_items ADD COLUMN {col} {decl}")
```
그리고 메서드 추가:
```python
    def save_enrichment(self, item_id, *, kind, tags, embedding, story_id) -> None:
        self.conn.execute(
            "UPDATE raw_items SET kind=?, tags=?, embedding=?, story_id=? WHERE id=?",
            (kind, json.dumps(list(tags)),
             json.dumps(list(embedding)) if embedding is not None else None,
             story_id, item_id))
        self.conn.commit()
```

`firestore_store.py`에 추가(read-modify-write, 기존 필드 보존):
```python
    def save_enrichment(self, item_id, *, kind, tags, embedding, story_id) -> None:
        ref = self.db.collection(_ITEMS).document(item_id)
        d = ref.get().to_dict() or {}
        d.update({"kind": kind, "tags": list(tags),
                  "embedding": list(embedding) if embedding is not None else None,
                  "story_id": story_id})
        ref.set(d)
```

- [ ] **Step 4: 통과 + 전체 회귀 확인**
Run: `docker compose run --rm test pytest -q tests/test_store_enrichment.py`
Expected: PASS (2 passed).
Run: `docker compose run --rm test`
Expected: 65 + stories(4) + enrichment(2) = **71 passed**, 회귀 0.

- [ ] **Step 5: 커밋**
```bash
git add src/newsstore/store/base.py src/newsstore/store/sqlite_store.py src/newsstore/store/firestore_store.py tests/test_store_enrichment.py
git commit -m "feat: save_enrichment (kind/tags/embedding/story_id) + sqlite items migration"
```

---

## Self-Review (작성자 체크)
- **Spec 커버리지**: §4 stories/items 필드 = Task1·3 · §7 get_open_stories/close = Task1·2 · §11 Store 확장 = 전체.
- **플레이스홀더**: 없음(전 스텝 실제 코드·명령·기대값).
- **타입 일관**: `create_story/append_to_story(*, title,vec,member_id,entities,now)` · `get_open_stories(cutoff)->[{'id','centroid'}]` · `save_enrichment(item_id,*,kind,tags,embedding,story_id)` 전 태스크/스토어 일관. centroid=sum/count 양쪽 동일.
- 주의: mock-firestore `where("status","==","open")` 단일 필터(인덱스/체이닝 회피), 시간창은 in-process 필터. last_seen은 firestore=datetime / sqlite=ISO.

## 다음 Plan
- **Plan 3** — Gemini Flash 태깅(10배치)+리뷰어 + Gemini 임베딩(Tier3 키), 모킹 테스트.
- **Plan 4** — Processor 오케스트레이션(Plan 1 assign + Plan 2 store + Plan 3 LLM 결합) + Cloud Run Job #2 + Scheduler.

<!-- spec-review: passed lenses=0 date=2026-06-28 note=grandfathered — pre-existing shipped doc (2026-06-12~14), predates review gate; not re-reviewed this session -->
