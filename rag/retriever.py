"""Offline-first hybrid retrieval engine for the FarmConnect AI knowledge base.

This is the "R" in RAG. It reads every Markdown document under
``knowledge_base/``, splits each one into heading-level (and, for long
sections, paragraph-level) chunks, and builds two complementary retrievers:

1. **BM25 over an inverted index** — the classic lexical ranker, but backed by
   postings lists so a query only ever touches the chunks that actually contain
   its terms. This is what lets the engine stay fast when the knowledge base
   grows to 400+ documents and well over a million words: search cost scales
   with the query, not with the size of the corpus.

2. **scikit-learn TF-IDF cosine similarity** — an optional semantic layer that
   catches paraphrases and related wording BM25 alone can miss ("my corn is
   sick" -> the maize disease section). It shares the exact same tokeniser,
   synonym map and stemmer as BM25, so both rankers speak one vocabulary.

The two scores are fused (Reciprocal Rank Fusion + normalised blend) into a
single ranking, and the engine reports a **confidence** for every search so the
assistant can honestly say how sure it is.

Zero-dependency fallback
------------------------
scikit-learn is *optional*. If it is not importable, the engine transparently
runs pure-Python BM25 only — no numpy, no internet, nothing to install — so the
assistant stays genuinely offline-first on a low-end, phone-tethered laptop.

Startup cache
-------------
The whole index (chunks + postings + the TF-IDF matrix) is pickled to
``rag/.cache/``. On the next start it is loaded in a fraction of a second and
rebuilt only when the Markdown files actually change (detected by a fingerprint
of every file's path, size and modification time). Building 400+ documents from
scratch happens once, not on every server boot.

Public API
----------
    kb = get_kb()                      # cached singleton, builds/loads the index
    hits = kb.search("why are my maize leaves yellow", k=6)
    hits, sources, meta = kb.search_grouped("...", k=6, max_docs=4)
    # meta -> {"confidence": 0.0-1.0, "band": "high|medium|low", ...}

Each :class:`Chunk` knows which document and section it came from, so the
assistant can cite its sources and never has to invent anything.
"""
from __future__ import annotations

import hashlib
import math
import pickle
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

# --- Optional semantic layer (scikit-learn) --------------------------------
# Imported defensively: the engine must still work with only the standard
# library so the site stays offline-first with zero third-party installs.
try:  # pragma: no cover - exercised implicitly by whichever path is installed
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import linear_kernel
    _SKLEARN_OK = True
except Exception:  # ImportError or any transitive failure
    _SKLEARN_OK = False

KB_DIR = Path(__file__).parent / "knowledge_base"
CACHE_DIR = Path(__file__).parent / ".cache"
CACHE_FILE = CACHE_DIR / "kb_index.pkl"
# Bump whenever the on-disk structure or the chunking/tokenising logic changes,
# so a stale cache is rebuilt instead of silently used.
CACHE_VERSION = 4

# Long sections are sub-split into windows of about this many words so that
# retrieval granularity (and citation precision) stays good even when a single
# document section runs very long.
MAX_CHUNK_WORDS = 240
CHUNK_OVERLAP_WORDS = 40

# ---------------------------------------------------------------------------
# Tokenisation
# ---------------------------------------------------------------------------
# A compact English stop-word list. Removing these focuses scoring on the
# meaningful farming vocabulary ("maize", "blight", "spacing"...).
_STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "if", "then", "else", "of", "for",
    "to", "in", "on", "at", "by", "is", "are", "was", "were", "be", "been",
    "being", "it", "its", "this", "that", "these", "those", "as", "with",
    "from", "into", "about", "how", "what", "when", "where", "which", "who",
    "why", "can", "do", "does", "my", "your", "our", "their", "i", "you",
    "we", "they", "he", "she", "them", "me", "us", "should", "would", "could",
    "will", "shall", "may", "might", "must", "have", "has", "had", "not",
    "no", "yes", "there", "here", "so", "than", "too", "very", "just", "also",
    "any", "some", "all", "more", "most", "much", "many", "up", "out", "get",
}

# Common farmer phrasings mapped to the vocabulary the knowledge base uses.
# This lets a question like "my corn has bugs" find the maize + pest docs.
# Both BM25 and the TF-IDF layer run on the output of this map, so an expansion
# added here immediately helps *both* rankers.
_SYNONYMS = {
    "corn": "maize", "mealie": "maize", "mealies": "maize",
    "peanut": "groundnut", "peanuts": "groundnut", "groundnuts": "groundnut",
    "cassava": "cassava", "manioc": "cassava", "yuca": "cassava",
    "bug": "pest", "bugs": "pest", "insect": "pest", "insects": "pest",
    "worm": "armyworm", "worms": "armyworm", "caterpillar": "armyworm",
    "sick": "disease", "dying": "disease", "diseased": "disease",
    "rotting": "rot", "rotten": "rot",
    "spray": "pesticide", "sprays": "pesticide", "chemical": "pesticide",
    "chemicals": "pesticide", "poison": "pesticide",
    "fertilizer": "fertiliser", "fertilizers": "fertiliser",
    "fertilisers": "fertiliser", "manure": "fertiliser", "compost": "fertiliser",
    "water": "irrigation", "watering": "irrigation", "irrigate": "irrigation",
    "rain": "rainfall", "rains": "rainfall",
    "cow": "cattle", "cows": "cattle", "bull": "cattle", "calf": "cattle",
    "chicken": "poultry", "chickens": "poultry", "hen": "poultry",
    "hens": "poultry", "cockerel": "poultry", "broiler": "poultry",
    "layer": "poultry", "layers": "poultry",
    "goat": "goats", "sheep": "sheep", "pig": "pigs", "pigs": "pigs",
    "price": "pricing", "prices": "pricing", "cost": "pricing",
    "sell": "market", "selling": "market", "buyer": "market", "buyers": "market",
    "store": "storage", "storing": "storage", "silo": "storage",
    "harvesting": "harvest", "harvested": "harvest",
    "planting": "planting", "sowing": "planting", "sow": "planting",
    "yellow": "yellowing", "yellowed": "yellowing",
    "leaves": "leaf", "leafs": "leaf",
    "wilting": "wilt", "wilted": "wilt",
    "drought": "drought", "dry": "drought", "flooding": "flood", "floods": "flood",
    "soil": "soil", "ground": "soil", "land": "soil",
    "seeds": "seed", "seedling": "seed", "seedlings": "seed",
}

_WORD_RE = re.compile(r"[a-z][a-z0-9]+")


def _stem(word: str) -> str:
    """A deliberately light suffix stripper — enough to match plurals and a few
    verb forms without pulling in a heavy stemming library."""
    for suf in ("ational", "ings", "ing", "edly", "ed", "ies", "es", "s"):
        if word.endswith(suf) and len(word) - len(suf) >= 3:
            if suf == "ies":
                return word[: -len(suf)] + "y"
            return word[: -len(suf)]
    return word


def tokenize(text: str) -> list[str]:
    """Lower-case, split on words, expand synonyms, drop stop-words, stem."""
    tokens: list[str] = []
    for raw in _WORD_RE.findall(text.lower()):
        raw = _SYNONYMS.get(raw, raw)
        if raw in _STOPWORDS:
            continue
        tokens.append(_stem(raw))
    return tokens


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------
@dataclass
class Chunk:
    """One retrievable section of the knowledge base."""
    doc_id: str          # e.g. "crops/maize.md"
    category: str        # e.g. "crops"
    doc_title: str       # e.g. "Maize (Corn)"
    heading: str         # e.g. "Disease Management" ("" for the doc intro)
    text: str            # the section body (with its heading line)
    tokens: list[str] = field(default_factory=list, repr=False)
    part: int = 0        # sub-chunk index when a long section was split
    idx: int = -1        # this chunk's stable position in KnowledgeBase.chunks
    score: float = 0.0   # transient relevance score from the most recent search

    @property
    def title(self) -> str:
        return f"{self.doc_title} — {self.heading}" if self.heading else self.doc_title

    def snippet(self, limit: int = 320) -> str:
        body = re.sub(r"\s+", " ", self.text).strip()
        return body if len(body) <= limit else body[:limit].rsplit(" ", 1)[0] + "…"


# Split a document into (heading, body) sections at H2 (##) boundaries.
_H1_RE = re.compile(r"^#\s+(.*)$", re.MULTILINE)
_SECTION_RE = re.compile(r"^##\s+(.*)$", re.MULTILINE)


def _split_sections(md: str) -> tuple[str, list[tuple[str, str]]]:
    """Return (doc_title, [(heading, body_including_heading), ...])."""
    m = _H1_RE.search(md)
    doc_title = m.group(1).strip() if m else ""

    sections: list[tuple[str, str]] = []
    parts = _SECTION_RE.split(md)
    # re.split with one capture group yields: [pre, head1, body1, head2, body2, ...]
    intro = parts[0]
    intro_body = _H1_RE.sub("", intro).strip()
    if intro_body:
        sections.append(("", intro_body))
    for i in range(1, len(parts), 2):
        heading = parts[i].strip()
        body = parts[i + 1].strip() if i + 1 < len(parts) else ""
        sections.append((heading, f"## {heading}\n{body}".strip()))
    return doc_title, sections


def _window_long_body(body: str) -> list[str]:
    """Split an over-long section body into overlapping word windows.

    Keeps each retrievable chunk small enough to stay precise, while the
    overlap stops a fact that straddles a window boundary from being lost.
    Short sections (the common case) are returned unchanged as a single window.
    """
    words = body.split()
    if len(words) <= MAX_CHUNK_WORDS:
        return [body]
    windows: list[str] = []
    step = MAX_CHUNK_WORDS - CHUNK_OVERLAP_WORDS
    for start in range(0, len(words), step):
        windows.append(" ".join(words[start:start + MAX_CHUNK_WORDS]))
        if start + MAX_CHUNK_WORDS >= len(words):
            break
    return windows


def _fingerprint(kb_dir: Path) -> str:
    """A cheap, stable signature of the knowledge base's current state.

    Combines every Markdown file's relative path, byte size and modification
    time. If any file is added, removed, or edited, the digest changes and the
    index is rebuilt; otherwise the cached index is reused verbatim.
    """
    h = hashlib.sha256()
    h.update(f"v{CACHE_VERSION}|".encode())
    for path in sorted(kb_dir.rglob("*.md")):
        try:
            st = path.stat()
        except OSError:
            continue
        rel = path.relative_to(kb_dir).as_posix()
        h.update(f"{rel}|{st.st_size}|{int(st.st_mtime_ns)}\n".encode())
    return h.hexdigest()


# ---------------------------------------------------------------------------
# The index
# ---------------------------------------------------------------------------
class KnowledgeBase:
    """Hybrid (BM25 + optional TF-IDF) index over the Markdown knowledge base."""

    K1 = 1.5   # BM25 term-frequency saturation
    B = 0.75   # BM25 length normalisation

    def __init__(self, kb_dir: Path | str = KB_DIR, use_cache: bool = True):
        self.kb_dir = Path(kb_dir)
        self.chunks: list[Chunk] = []
        self._postings: dict[str, list[tuple[int, int]]] = {}  # term -> [(chunk_idx, tf)]
        self._doc_len: list[int] = []
        self._df: Counter = Counter()
        self._avg_len: float = 0.0
        self._n_docs: int = 0
        self.doc_titles: dict[str, str] = {}
        self._doc_meta_tokens: dict[str, set[str]] = {}  # doc_id -> title/topic tokens
        self._crop_vocab: set[str] = set()               # crop/animal entity names
        self.fingerprint: str = ""
        # Semantic layer (populated only when scikit-learn is available).
        self._vectorizer = None
        self._tfidf_matrix = None
        self.hybrid: bool = False

        if not (use_cache and self._load_cache()):
            self._build()
            if use_cache:
                self._save_cache()

    # -- cache --------------------------------------------------------------
    def _load_cache(self) -> bool:
        if not CACHE_FILE.exists():
            return False
        current = _fingerprint(self.kb_dir)
        try:
            with CACHE_FILE.open("rb") as fh:
                blob = pickle.load(fh)
        except Exception:
            return False
        if blob.get("version") != CACHE_VERSION or blob.get("fingerprint") != current:
            return False
        try:
            self.chunks = blob["chunks"]
            self._postings = blob["postings"]
            self._doc_len = blob["doc_len"]
            self._df = blob["df"]
            self._avg_len = blob["avg_len"]
            self._n_docs = blob["n_docs"]
            self.doc_titles = blob["doc_titles"]
            self.fingerprint = current
            # The TF-IDF artefacts are only present/usable when sklearn is here.
            if _SKLEARN_OK and blob.get("tfidf") is not None:
                self._vectorizer = blob["tfidf"]["vectorizer"]
                self._tfidf_matrix = blob["tfidf"]["matrix"]
                self.hybrid = True
            elif _SKLEARN_OK:
                # Cache had no semantic layer but we can build one now.
                self._build_tfidf()
            self._index_doc_meta()
        except Exception:
            return False
        return True

    def _save_cache(self) -> None:
        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            tfidf = None
            if self.hybrid and self._vectorizer is not None:
                tfidf = {"vectorizer": self._vectorizer, "matrix": self._tfidf_matrix}
            blob = {
                "version": CACHE_VERSION,
                "fingerprint": self.fingerprint,
                "chunks": self.chunks,
                "postings": self._postings,
                "doc_len": self._doc_len,
                "df": self._df,
                "avg_len": self._avg_len,
                "n_docs": self._n_docs,
                "doc_titles": self.doc_titles,
                "tfidf": tfidf,
            }
            tmp = CACHE_FILE.with_suffix(".tmp")
            with tmp.open("wb") as fh:
                pickle.dump(blob, fh, protocol=pickle.HIGHEST_PROTOCOL)
            tmp.replace(CACHE_FILE)
        except Exception:
            pass  # a failed cache write must never break retrieval

    # -- index construction -------------------------------------------------
    def _build(self) -> None:
        if not self.kb_dir.exists():
            return
        for path in sorted(self.kb_dir.rglob("*.md")):
            rel = path.relative_to(self.kb_dir).as_posix()
            category = rel.split("/")[0] if "/" in rel else "general"
            try:
                md = path.read_text(encoding="utf-8")
            except Exception:
                continue
            doc_title, sections = _split_sections(md)
            doc_title = doc_title or path.stem.replace("_", " ").title()
            self.doc_titles[rel] = doc_title
            for heading, body in sections:
                if not body.strip():
                    continue
                for part_i, window in enumerate(_window_long_body(body)):
                    # Title/heading are woven into the token stream (and weighted
                    # by repetition) so that "maize disease" strongly favours the
                    # maize doc's disease section: a title/heading match is a much
                    # stronger relevance signal than the same word buried in
                    # another doc's body.
                    enriched = " ".join([
                        doc_title, doc_title,        # title counts ~2x
                        category,
                        heading, heading, heading,   # heading counts ~3x
                        window,
                    ])
                    tokens = tokenize(enriched)
                    if not tokens:
                        continue
                    self.chunks.append(
                        Chunk(rel, category, doc_title, heading, window, tokens, part_i)
                    )

        self._index_bm25()
        self._index_doc_meta()
        if _SKLEARN_OK:
            self._build_tfidf()
        self.fingerprint = _fingerprint(self.kb_dir)

    def _index_doc_meta(self) -> None:
        """Token sets for each document's title, filename and category.

        A query term that matches one of these is a strong *topic* signal — if
        a farmer names a crop, pest or disease, the document about it is almost
        always what they want — so it earns a ranking boost during fusion.
        """
        self._doc_meta_tokens = {}
        for doc_id, title in self.doc_titles.items():
            stem = doc_id.rsplit("/", 1)[-1].rsplit(".", 1)[0].replace("_", " ")
            category = doc_id.split("/")[0]
            self._doc_meta_tokens[doc_id] = set(tokenize(f"{title} {stem} {category}"))

        # Crop / animal ENTITY vocabulary, built from the crop and livestock
        # filenames. When a query names one of these (e.g. "maize"), documents
        # about a *different* entity (e.g. a tomato disease) are demoted, so the
        # crop the farmer actually asked about wins even when a rival document
        # shares generic symptom words like "yellow" or "leaf".
        _generic = {"keeping", "health", "biosecurity", "scale", "small",
                    "smallholder", "smallholders", "and", "for", "the"}
        crop_vocab: set[str] = set()
        for doc_id in self.doc_titles:
            if doc_id.split("/")[0] in ("crops", "livestock"):
                stem = doc_id.rsplit("/", 1)[-1].rsplit(".", 1)[0].replace("_", " ")
                crop_vocab |= set(tokenize(stem))
        self._crop_vocab = crop_vocab - _generic

    def _index_bm25(self) -> None:
        """Build the inverted index (postings lists) and length statistics."""
        self._n_docs = len(self.chunks)
        self._doc_len = [0] * self._n_docs
        postings: dict[str, list[tuple[int, int]]] = defaultdict(list)
        total_len = 0
        for idx, c in enumerate(self.chunks):
            c.idx = idx
            tf = Counter(c.tokens)
            self._doc_len[idx] = len(c.tokens)
            total_len += len(c.tokens)
            for term, f in tf.items():
                postings[term].append((idx, f))
                self._df[term] += 1
        self._postings = dict(postings)
        self._avg_len = (total_len / self._n_docs) if self._n_docs else 0.0

    def _build_tfidf(self) -> None:
        """Fit the TF-IDF semantic layer over the (already tokenised) chunks.

        Both rankers consume the identical token stream, so they agree on
        vocabulary, synonyms and stemming. Uni- and bi-grams give TF-IDF a
        little phrase awareness ("late blight", "fall armyworm").
        """
        if not _SKLEARN_OK or not self.chunks:
            return
        corpus = [" ".join(c.tokens) for c in self.chunks]
        try:
            self._vectorizer = TfidfVectorizer(
                analyzer="word",
                token_pattern=r"\S+",     # tokens are already clean, split on space
                ngram_range=(1, 2),
                sublinear_tf=True,
                min_df=1,
                norm="l2",
            )
            self._tfidf_matrix = self._vectorizer.fit_transform(corpus)
            self.hybrid = True
        except Exception:
            self._vectorizer = None
            self._tfidf_matrix = None
            self.hybrid = False

    # -- scoring ------------------------------------------------------------
    def _idf(self, term: str) -> float:
        n = self._df.get(term, 0)
        if n == 0:
            return 0.0
        return max(0.0, math.log((self._n_docs - n + 0.5) / (n + 0.5) + 1.0))

    def _bm25_scores(self, q_terms: list[str]) -> dict[int, float]:
        """BM25 score for every chunk that contains at least one query term.

        Thanks to the inverted index this only visits matching chunks, so cost
        scales with the query and the postings, not with the whole corpus.
        """
        q_weight = Counter(q_terms)
        scores: dict[int, float] = defaultdict(float)
        for term, qn in q_weight.items():
            idf = self._idf(term)
            if idf <= 0:
                continue
            for idx, f in self._postings.get(term, ()):  # postings for this term
                dl = self._doc_len[idx]
                denom = f + self.K1 * (1 - self.B + self.B * dl / (self._avg_len or 1))
                scores[idx] += idf * (f * (self.K1 + 1)) / (denom or 1) * qn
        return scores

    def _tfidf_scores(self, query: str, candidates: set[int] | None = None) -> dict[int, float]:
        """Cosine similarity of the query against chunk TF-IDF vectors."""
        if not self.hybrid or self._vectorizer is None:
            return {}
        q_str = " ".join(tokenize(query))
        if not q_str:
            return {}
        try:
            q_vec = self._vectorizer.transform([q_str])
            sims = linear_kernel(q_vec, self._tfidf_matrix).ravel()  # already l2-normed
        except Exception:
            return {}
        if candidates is None:
            return {i: float(s) for i, s in enumerate(sims) if s > 0}
        return {i: float(sims[i]) for i in candidates if sims[i] > 0}

    @staticmethod
    def _normalise(scores: dict[int, float]) -> dict[int, float]:
        if not scores:
            return {}
        top = max(scores.values())
        if top <= 0:
            return {i: 0.0 for i in scores}
        return {i: v / top for i, v in scores.items()}

    def search_scored(self, query: str, k: int = 6) -> list[tuple[float, Chunk]]:
        """Return up to k (fused_score, chunk) pairs, ranked best-first."""
        q_terms = tokenize(query)
        if not self.chunks or (not q_terms and not self.hybrid):
            return []

        bm25 = self._bm25_scores(q_terms)
        # Consider TF-IDF's own top matches too, not only BM25 candidates, so a
        # purely semantic hit (no shared keyword) can still surface.
        tfidf_all = self._tfidf_scores(query) if self.hybrid else {}
        tfidf_top = dict(sorted(tfidf_all.items(), key=lambda kv: kv[1], reverse=True)[:50])

        candidates = set(bm25) | set(tfidf_top)
        if not candidates:
            return []

        bm25_n = self._normalise({i: bm25.get(i, 0.0) for i in candidates})
        tfidf_n = self._normalise({i: tfidf_all.get(i, 0.0) for i in candidates})

        # Rank positions for Reciprocal Rank Fusion — robust to the two rankers
        # living on different score scales.
        def _ranks(scores: dict[int, float]) -> dict[int, int]:
            order = sorted(scores, key=lambda i: scores[i], reverse=True)
            return {idx: r for r, idx in enumerate(order, 1)}

        bm25_rank = _ranks(bm25) if bm25 else {}
        tfidf_rank = _ranks(tfidf_all) if tfidf_all else {}
        RRF_K = 60
        q_set = set(q_terms)
        # Which crop/animal entities (if any) did the farmer name?
        q_crops = q_set & self._crop_vocab

        fused: dict[int, float] = {}
        for i in candidates:
            blend = 0.5 * bm25_n.get(i, 0.0) + 0.5 * tfidf_n.get(i, 0.0)
            rrf = 0.0
            if i in bm25_rank:
                rrf += 1.0 / (RRF_K + bm25_rank[i])
            if i in tfidf_rank:
                rrf += 1.0 / (RRF_K + tfidf_rank[i])

            meta_tok = self._doc_meta_tokens.get(self.chunks[i].doc_id, set())
            # Modest generic topic boost: a query word appearing in the doc's
            # title/topic, weighted by rarity (IDF).
            matched_meta = q_set.intersection(meta_tok)
            title_bonus = 0.12 * sum(self._idf(t) for t in matched_meta)

            # Crop focusing: when the query names a crop/animal, strongly prefer
            # documents about THAT entity and demote documents that are about a
            # DIFFERENT named entity. This is the signal that keeps "maize leaves
            # yellowing" on the maize docs instead of a tomato disease that
            # merely shares the words "yellow" and "leaf".
            if q_crops:
                doc_crops = meta_tok & self._crop_vocab
                if doc_crops & q_crops:
                    title_bonus += 0.9        # about the crop the farmer named
                elif doc_crops:
                    title_bonus -= 0.7        # about a different crop -> demote

            # Blend of normalised magnitudes + rank fusion + topic focus. When
            # TF-IDF is unavailable this cleanly degrades to boosted BM25.
            fused[i] = blend + rrf + title_bonus

        ranked = sorted(candidates, key=lambda i: fused[i], reverse=True)[:k]
        out: list[tuple[float, Chunk]] = []
        for i in ranked:
            c = self.chunks[i]
            c.score = round(fused[i], 6)
            out.append((fused[i], c))
        return out

    def search(self, query: str, k: int = 6) -> list[Chunk]:
        """Return the k best-matching chunks for a natural-language query."""
        return [c for _, c in self.search_scored(query, k=k)]

    def _confidence(self, query: str, scored: list[tuple[float, Chunk]]) -> dict:
        """A calibrated, bounded confidence signal for the top result.

        Blends two honest signals:
          * coverage  — the share of meaningful query terms that actually appear
                        in the retrieved passages (did we even find the words?);
          * semantic  — the top TF-IDF cosine similarity when available, else a
                        saturating function of the raw BM25 strength.
        Reported as a 0-1 number plus a high/medium/low band the assistant uses
        to phrase how sure it is (per the response-confidence guidelines).
        """
        if not scored:
            return {"confidence": 0.0, "band": "none", "coverage": 0.0,
                    "semantic": 0.0, "matched_terms": [], "missing_terms": []}

        q_terms = set(tokenize(query))
        found: set[str] = set()
        for _, c in scored[:4]:
            found |= (set(c.tokens) & q_terms)
        coverage = (len(found) / len(q_terms)) if q_terms else 0.0

        if self.hybrid:
            semantic = self._top_cosine(query, scored[0][1])
        else:
            # Map raw BM25 of the best hit through a soft saturating curve.
            raw = scored[0][0]
            semantic = raw / (raw + 1.5)

        confidence = max(0.0, min(1.0, 0.55 * coverage + 0.45 * semantic))
        band = "high" if confidence >= 0.6 else "medium" if confidence >= 0.32 else "low"
        return {
            "confidence": round(confidence, 3),
            "band": band,
            "coverage": round(coverage, 3),
            "semantic": round(semantic, 3),
            "matched_terms": sorted(found),
            "missing_terms": sorted(q_terms - found),
        }

    def _top_cosine(self, query: str, top_chunk: Chunk) -> float:
        idx = top_chunk.idx
        if idx < 0 or self._vectorizer is None or self._tfidf_matrix is None:
            return 0.0
        q_str = " ".join(tokenize(query))
        if not q_str:
            return 0.0
        try:
            q_vec = self._vectorizer.transform([q_str])
            sim = linear_kernel(q_vec, self._tfidf_matrix[idx])
            return float(sim.ravel()[0])
        except Exception:
            return 0.0

    def search_grouped(self, query: str, k: int = 6, max_docs: int = 4):
        """Search, then return chunks, a de-duplicated source list, and meta.

        Returns (chunks, sources, meta):
          * sources — distinct documents behind the top chunks, for citations;
          * meta    — {"confidence", "band", "coverage", "semantic",
                       "matched_terms", "missing_terms", "hybrid"}.
        """
        scored = self.search_scored(query, k=k)
        hits = [c for _, c in scored]
        sources: list[dict] = []
        seen: set[str] = set()
        for c in hits:
            if c.doc_id not in seen:
                seen.add(c.doc_id)
                sources.append({
                    "doc_id": c.doc_id,
                    "title": c.doc_title,
                    "category": c.category,
                })
            if len(sources) >= max_docs:
                break
        meta = self._confidence(query, scored)
        meta["hybrid"] = self.hybrid
        return hits, sources, meta

    @property
    def stats(self) -> dict:
        cats: dict[str, int] = defaultdict(int)
        for doc_id in self.doc_titles:
            cats[doc_id.split("/")[0]] += 1
        return {
            "documents": len(self.doc_titles),
            "chunks": len(self.chunks),
            "categories": dict(sorted(cats.items())),
            "hybrid": self.hybrid,
            "retriever": "BM25 + TF-IDF (hybrid)" if self.hybrid else "BM25 (lexical)",
        }


# Module-level singleton so the index is built/loaded once per process.
_KB: KnowledgeBase | None = None


def get_kb() -> KnowledgeBase:
    global _KB
    if _KB is None:
        _KB = KnowledgeBase()
    return _KB


def reload_kb() -> KnowledgeBase:
    """Force a rebuild (e.g. after new documents are added at runtime)."""
    global _KB
    _KB = KnowledgeBase()
    return _KB
