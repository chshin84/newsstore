"""사건 클러스터링 — 임베딩 + top-k 후보 + gray-band LLM 판정.

news-analytics @249aa3d에서 이식(2026-06-29). `_default_embedder`/`_default_base_cluster`
(river·sentence-transformers, `DBSTREAM_PARAMS`)는 newsstore 주입 경로에선 미사용 — eval/미래용 보존.

설계 요지(측정으로 도달):
- **배치**(`cluster_articles`): 싱글톤 베이스 → 글로벌 응집(article max-linkage, top-k 후보) →
  sim>=hi 합류 / <lo 신규 / 그 사이는 주입 LLM 'SAME?' 판정(부재·예산초과 → 보수적 미합류).
- **온라인**(`EventClusterer.assign`): 1건을 open_stories(`centroid_sum` 코사인)에 같은 규칙으로 배정.
- **의존은 주입 경계 뒤**: 무거운 임베더는 함수 내부 지연 임포트. 유닛 tier는 embed·llm·
  base를 주입해 모델 다운로드 없이 결정론으로 돈다.

평가: B-cubed F1의 '자명해(전부 병합·전부 분리) 격파' 불변식(매직넘버 없음) — 측정 P=1.000 R=0.696 F1=0.821.
"""
from __future__ import annotations

import logging
import math
from dataclasses import is_dataclass
from typing import Callable, Iterable, Sequence

# Vendored from news-analytics @249aa3d (2026-06-29). config.py 상수 인라인.
# gray-band 경계 [lo, hi]: sim>=hi 결정론 합류 / sim<lo 결정론 신규 / 그 사이만 LLM 판정.
# (이란+코스피 골든셋 + gemini-embedding-001/768로 측정된 값 — newsstore 코퍼스 재캘리브레이션은 후속.)
GRAY_BAND: tuple[float, float] = (0.55, 0.75)
LLM_CALL_CAP_RATIO: float = 0.2          # 배치 런당 LLM 콜 상한(docs 대비 비율)
TOP_K: int = 8                            # 후보 top-k(머지 판정 대상)
DBSTREAM_PARAMS: dict = {"clustering_threshold": 1.0, "fading_factor": 0.01,
                         "cleanup_interval": 2.0, "intersection_factor": 0.3,
                         "minimum_weight": 1.0}

logger = logging.getLogger("newsstore.enrich.clustering")

Vector = Sequence[float]
Embedder = Callable[[list[str]], list[Vector]]
BaseClusterer = Callable[[list[Vector]], list[int]]


# ── 입력 정규화 ──────────────────────────────────────────────────────────────

class _Doc:
    """dict 또는 contracts.Article를 통일된 뷰로(머지 레이어 내부 표현)."""

    __slots__ = ("id", "title", "body", "tags", "embedding")

    def __init__(self, id: str, title: str, body: str, tags: tuple[str, ...],
                 embedding: list[float] | None) -> None:
        self.id = id
        self.title = title
        self.body = body
        self.tags = tags
        self.embedding = embedding

    @property
    def text(self) -> str:
        return f"{self.title}\n{self.body}".strip()


def _get(article, key: str, default=None):
    if isinstance(article, dict):
        return article.get(key, default)
    return getattr(article, key, default)


def _normalize(article) -> _Doc:
    if not isinstance(article, dict) and not is_dataclass(article):
        raise TypeError(f"기사는 dict 또는 dataclass여야 함: {type(article)!r}")
    raw_id = _get(article, "id")
    if raw_id is None or str(raw_id) == "":
        raise ValueError("기사에 id가 없음(FAIL-LOUD: 'None'으로 뭉개지 않는다)")
    emb = _get(article, "embedding")
    emb = [float(x) for x in emb] if emb is not None else None
    tags = tuple(_get(article, "tags") or ())
    return _Doc(
        id=str(raw_id),
        title=str(_get(article, "title") or ""),
        body=str(_get(article, "body") or ""),
        tags=tags,
        embedding=emb,
    )


# ── 벡터 산술 ────────────────────────────────────────────────────────────────

def _cosine(a: Vector, b: Vector) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


# ── union-find ───────────────────────────────────────────────────────────────

class _UF:
    def __init__(self, items: Iterable[int]) -> None:
        self._parent = {x: x for x in items}

    def find(self, x: int) -> int:
        root = x
        while self._parent[root] != root:
            root = self._parent[root]
        while self._parent[x] != root:
            self._parent[x], x = root, self._parent[x]
        return root

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self._parent[max(ra, rb)] = min(ra, rb)

    def connected(self, a: int, b: int) -> bool:
        return self.find(a) == self.find(b)


# ── LLM gray-band 판정 ──────────────────────────────────────────────────────

def _llm_same_event(llm, doc_a: _Doc, doc_b: _Doc) -> bool:
    prompt = (
        "두 뉴스가 **같은 사건·전개(스토리라인)**에 속하나? 같은 핵심 사건/위기의 서로 다른 "
        "국면·측면·후속·여파면 SAME(예: 한 휴전 협상의 군사·외교·경제·여파 기사들은 모두 SAME). "
        "핵심 사건이 다르거나 주제만 겹칠 뿐 무관하면 DIFFERENT. 첫 줄에 SAME 또는 DIFFERENT만.\n\n"
        f"[A] {doc_a.title}\n{doc_a.body[:500]}\n\n"
        f"[B] {doc_b.title}\n{doc_b.body[:500]}\n"
    )
    resp = llm.complete(prompt) or ""          # 실 SDK None 가드(테스트-운영 계약 차이)
    return resp.strip().upper().startswith("SAME")


# ── 지연 임포트 기본 의존(실/eval 경로) ──────────────────────────────────────

_EMBED_MODEL = None  # 모듈 캐시(콜드스타트 1회)


def _default_embedder() -> Embedder:
    """다국어 문장 임베더(LaBSE) — EN/KO 교차언어 정렬이 강해 동일사건 교차언어 수렴에 유리."""
    global _EMBED_MODEL
    if _EMBED_MODEL is None:
        from sentence_transformers import SentenceTransformer
        _EMBED_MODEL = SentenceTransformer("sentence-transformers/LaBSE")
    model = _EMBED_MODEL

    def embed(texts: list[str]) -> list[Vector]:
        return [list(map(float, v))
                for v in model.encode(texts, normalize_embeddings=True)]

    return embed


def _singleton_base(vectors: list[Vector]) -> list[int]:
    """배치 기본 베이스 — 각 기사를 독립 마이크로클러스터로 시작.

    측정 근거: River DBSTREAM을 배치 베이스로 쓰면 서로 다른 사가를 한 거대 블롭으로 묶어버려
    (코스피 120인데 micro 1이 216건=이란 혼입) 분리를 원천 차단했다. 배치 수렴/분리는 머지
    레이어(article max-linkage + gray-band LLM)가 책임지므로 베이스는 싱글톤이 가장 안전·예측가능."""
    return list(range(len(vectors)))


def _default_base_cluster(vectors: list[Vector]) -> list[int]:
    """온라인 베이스(River DBSTREAM) — 런타임 `assign`(1건 인입 incremental)용 엔진(후속).

    배치 `cluster_articles`는 위 `_singleton_base`를 기본으로 쓴다(DBSTREAM 배치 과병합 회피).
    River는 온라인 경로에서 near-dup 마이크로클러스터를 유지하는 데 쓴다.
    """
    from river import cluster

    model = cluster.DBSTREAM(**DBSTREAM_PARAMS)
    labels: list[int] = []
    for v in vectors:
        x = {i: float(val) for i, val in enumerate(v)}
        model.learn_one(x)
        labels.append(int(model.predict_one(x)))
    return labels


# ── 임베딩 확보 ──────────────────────────────────────────────────────────────

def _embed_text(doc: _Doc) -> str:
    """임베딩 입력은 **제목 기준**(사건 정체성은 헤드라인에 응축된다).

    측정 근거: 이 코퍼스의 본문은 잦은 절단('Full story available on …')·한 줄 스텁이라
    임베딩을 사건에서 표류시킨다 — 호르무즈 우회 투자 기사(스텁 본문)가 title+body에서
    클러스터까지 cos 0.43으로 이탈해 미수렴을 유발(title-only는 1수렴). 본문은 LLM gray-band
    판정엔 그대로 쓰고(아래 `_llm_same_event`), **임베딩에서만** 제외한다."""
    return doc.title or doc.body


def _embeddings(docs: list[_Doc], embed: Embedder | None) -> list[Vector]:
    """기사에 임베딩이 있으면 그대로, 없으면 주입(또는 기본) 임베더로 채운다."""
    missing = [d for d in docs if d.embedding is None]
    if missing:
        embed = embed or _default_embedder()
        filled = embed([_embed_text(d) for d in missing])
        if filled is None or len(filled) != len(missing):
            raise ValueError("임베더가 입력 수와 다른 벡터를 반환함")
        for d, v in zip(missing, filled):
            d.embedding = [float(x) for x in v]
    dims = {len(d.embedding) for d in docs}
    if len(dims) > 1:                               # 주입/실 임베딩 차원 혼선 — zip 절단 대신 폭발
        raise ValueError(f"임베딩 차원 불일치(FAIL-LOUD): {sorted(dims)}")
    return [d.embedding for d in docs]


# ── 공개 API ─────────────────────────────────────────────────────────────────

def cluster_articles(
    articles,
    *,
    embed: Embedder | None = None,
    llm=None,
    base_cluster: BaseClusterer | None = None,
    gray_band: tuple[float, float] = GRAY_BAND,
    call_cap_ratio: float = LLM_CALL_CAP_RATIO,
    top_k: int = TOP_K,
) -> dict[str, str]:
    """기사들을 사건 단위로 재클러스터해 `{article_id: cluster_id}`를 돌려준다(오프라인/배치).

    embed·llm·base_cluster는 주입(미주입 시 실 기본값). 같은 사건은 하나의 cluster_id로 수렴.
    """
    docs = [_normalize(a) for a in articles]
    if not docs:
        return {}

    ids = [d.id for d in docs]
    if len(set(ids)) != len(ids):                   # 중복 id는 출력에서 조용히 덮어써짐 → 폭발
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        raise ValueError(f"중복 article id(FAIL-LOUD): {dupes[:5]}")

    vectors = _embeddings(docs, embed)

    if base_cluster is None:
        labels = _singleton_base(vectors)
    else:
        labels = list(base_cluster(vectors))

    if len(labels) != len(docs):
        raise ValueError("베이스 클러스터러가 입력 수와 다른 라벨을 반환함")

    return _merge(docs, vectors, labels, llm, gray_band, call_cap_ratio, top_k)


class EventClusterer:
    """온라인 사건 클러스터러 — 1건 인입을 기존 open_stories에 배정(런타임 모델·contracts.Clusterer).

    배치 `cluster_articles`와 **같은 gray-band 규칙**을 1건에 적용한다: 최상위 후보(스토리
    `centroid_sum` 코사인) sim>=hi 결정론 합류 / sim<lo 결정론 신규 / gray-band는 주입 LLM
    'SAME?'(부재·DIFFERENT·장애 → 보수적 신규). 신규는 **None** 반환(어댑터가 story id 생성).
    deps(embed·llm)는 **생성자 주입**. 후보 top-k 사전선별(벡터 인덱스)은 소비 측 어댑터가
    하고 여기엔 후보 스토리만 넘어와도 된다.
    """

    def __init__(self, embed: Embedder, llm=None,
                 gray_band: tuple[float, float] = GRAY_BAND) -> None:
        self._embed = embed
        self._llm = llm
        self._lo, self._hi = gray_band

    def assign(self, article, open_stories) -> str | None:
        emb = getattr(article, "embedding", None)
        if emb is not None:
            vec: Vector = [float(x) for x in emb]
        else:                                           # 임베딩 입력=제목 기준(_embed_text와 일치)
            text = (getattr(article, "title", "") or getattr(article, "body", "") or "")
            out = self._embed([text])
            if not out or out[0] is None:               # 임베더 계약 위반 → 폭발(FAIL-LOUD)
                raise ValueError("임베더가 빈/None 결과를 반환함")
            vec = [float(x) for x in out[0]]

        cands = []
        for s in open_stories:
            cs = getattr(s, "centroid_sum", None)
            if not cs:
                continue
            if len(cs) != len(vec):                     # 차원 불일치 → zip 절단 대신 폭발(FAIL-LOUD)
                raise ValueError(f"임베딩 차원 불일치: article {len(vec)} vs story {len(cs)}")
            cands.append((_cosine(vec, cs), s))
        if not cands:
            return None                                 # 후보 없음 → 신규
        best_cos, best = max(cands, key=lambda t: (t[0], t[1].id))   # 결정론 tiebreak

        if best_cos >= self._hi:
            return best.id                              # 결정론 합류
        if best_cos < self._lo:
            return None                                 # 결정론 신규
        if self._llm is not None:                       # gray-band — LLM 전용 게이트
            a = _Doc(str(getattr(article, "id", "")), getattr(article, "title", "") or "",
                     getattr(article, "body", "") or "", (), None)
            b = _Doc(best.id, best.title or "", "", (), None)
            try:
                if _llm_same_event(self._llm, a, b):
                    return best.id
            except Exception as exc:                    # 외부 LLM 장애 → 보수적 신규(Fail-soft)
                logger.warning("assign gray-band LLM 호출 실패 → 보수적 신규: %s", exc)
        return None                                     # 부재/DIFFERENT/장애 → 신규


def _merge(docs, vectors, labels, llm, gray_band, call_cap_ratio, top_k) -> dict[str, str]:
    """글로벌 응집(agglomerative) 머지 — 후보쌍을 코사인 내림차순으로 single-linkage 병합.

    sim>=hi 결정론 합류 / sim<lo 결정론 신규 / gray-band는 주입 LLM 'SAME?' 판정(부재·예산초과·
    장애 → 보수적 미합류). 후보는 각 유닛의 top-k 최근접만(멀리 떨어진 무관 사가 배제). 항상 *가장
    가까운 쌍부터* 병합하므로 처리순서에 무관하고 diffuse 사가도 잘 모은다(assign-style은 순서
    민감해 파편화 — 측정 R=0.07). 배치 재클러스터용. 온라인 1건 배정은 `EventClusterer.assign`."""
    lo, hi = gray_band

    members: dict[int, list[int]] = {}
    for idx, lbl in enumerate(labels):
        members.setdefault(int(lbl), []).append(idx)
    micro_labels = sorted(members)
    memvecs: dict[int, list[Vector]] = {l: [vectors[i] for i in members[l]] for l in micro_labels}
    rep: dict[int, _Doc] = {l: docs[min(members[l], key=lambda i: docs[i].id)] for l in micro_labels}

    # 후보쌍 = 마이크로클러스터 간 MAX-linkage(최대 멤버쌍 코사인). 각 유닛의 top-k만 남겨
    # 멀리 떨어진 무관 사가 쌍을 배제(전체쌍이면 gray-band 콜 폭증·폴백 과병합 — 측정).
    all_pairs: list[tuple[float, int, int]] = []
    for a_pos in range(len(micro_labels)):
        for b_pos in range(a_pos + 1, len(micro_labels)):
            la, lb = micro_labels[a_pos], micro_labels[b_pos]
            mx = max(_cosine(va, vb) for va in memvecs[la] for vb in memvecs[lb])
            all_pairs.append((mx, la, lb))
    nbrs: dict[int, list[tuple[float, int]]] = {l: [] for l in micro_labels}
    for mx, la, lb in all_pairs:
        nbrs[la].append((mx, lb))
        nbrs[lb].append((mx, la))
    candidates: set[tuple[int, int]] = set()
    for l, lst in nbrs.items():
        for mx, other in sorted(lst, key=lambda t: -t[0])[:top_k]:
            candidates.add((min(l, other), max(l, other)))
    pairs = [(mx, la, lb) for mx, la, lb in all_pairs if (min(la, lb), max(la, lb)) in candidates]
    pairs.sort(key=lambda p: (-p[0], p[1], p[2]))

    uf = _UF(micro_labels)
    cap = max(1, int(call_cap_ratio * len(docs)))
    llm_calls = 0
    for cos, la, lb in pairs:
        if uf.connected(la, lb):
            continue
        if cos >= hi:
            uf.union(la, lb)
        elif cos < lo:
            continue
        else:                              # gray-band — LLM 전용 게이트
            if llm is not None and llm_calls < cap:
                llm_calls += 1
                try:
                    merge = _llm_same_event(llm, rep[la], rep[lb])
                except Exception as exc:   # 외부 LLM 장애 → 보수적 미합류(패스 안 죽임)
                    logger.warning("gray-band LLM 호출 실패 → 보수적 미합류(Fail-soft): %s", exc)
                    merge = False
            else:
                merge = False              # 느슨히 풀지 않음(개체 폴백 과병합 측정 확인)
            if merge:
                uf.union(la, lb)

    ratio = llm_calls / len(docs) if docs else 0.0
    logger.info("clustering: docs=%d micro=%d groups=%d llm_calls=%d cap=%d ratio=%.3f",
                len(docs), len(micro_labels), len({uf.find(l) for l in micro_labels}),
                llm_calls, cap, ratio)
    if llm is not None and llm_calls >= cap:
        logger.warning("LLM 콜 상한(%d) 도달 — 잔여 gray-band은 보수적 미합류로 강등(Fail-soft)", cap)

    comp_ids: dict[int, str] = {}
    for l in micro_labels:
        root = uf.find(l)
        cid = min(docs[i].id for i in members[l])
        comp_ids[root] = min(comp_ids[root], cid) if root in comp_ids else cid
    assigned: dict[str, str] = {}
    for l in micro_labels:
        cid = comp_ids[uf.find(l)]
        for i in members[l]:
            assigned[docs[i].id] = cid
    return assigned
