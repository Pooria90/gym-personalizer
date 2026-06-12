"""Offline tests for RailtracksRetriever: chunk → Exercise mapping rules with
a stub runtime, plus a full ingest → retrieve round trip against
InMemoryVectorBackend with a deterministic fake embedder (no network)."""

import math
import zlib
from uuid import uuid4

from railtracks.retrieval import (
    Chunk,
    RetrievalResult,
    RetrievalRuntime,
    RetrievedChunk,
    VectorStore,
)
from railtracks.retrieval.chunking import RecursiveCharacterChunker
from railtracks.retrieval.embedding import TextEmbeddings
from railtracks.retrieval.embedding.base import Embedding
from railtracks.retrieval.embedding.models import EmbeddingMetrics
from railtracks.retrieval.stores import InMemoryVectorBackend

from gym_pt.retrieval import ExerciseCatalogLoader, ExerciseRetriever
from gym_pt.retrieval.railtracks_backend import RailtracksRetriever


def _retrieved(metadata: dict, rank: int) -> RetrievedChunk:
    chunk = Chunk(content="irrelevant", document_id=uuid4(), metadata=metadata)
    return RetrievedChunk(chunk=chunk, score=1.0 - rank * 0.1, rank=rank)


class StubRuntime:
    """Stands in for RetrievalRuntime; returns canned chunks."""

    def __init__(self, chunks: list[RetrievedChunk]):
        self.chunks = chunks
        self.calls: list[tuple[str, int]] = []

    async def retrieve(self, query: str, top_k: int = 5) -> RetrievalResult:
        self.calls.append((query, top_k))
        return RetrievalResult(query=query, chunks=self.chunks[:top_k])


class TestCatalogMapping:
    async def test_maps_hits_to_full_exercises_in_rank_order(self, exercise_factory):
        catalog = {e.id: e for e in (exercise_factory("A"), exercise_factory("B"))}
        runtime = StubRuntime(
            [_retrieved({"exercise_id": "B"}, 1), _retrieved({"exercise_id": "A"}, 2)]
        )
        retriever = RailtracksRetriever(runtime, catalog)

        result = await retriever.search("anything")
        assert [e.id for e in result] == ["B", "A"]
        assert all(e.instructions for e in result)  # full objects, not stubs

    async def test_satisfies_protocol(self, exercise_factory):
        retriever = RailtracksRetriever(StubRuntime([]), {})
        assert isinstance(retriever, ExerciseRetriever)

    async def test_deduplicates_repeated_ids(self, exercise_factory):
        catalog = {"A": exercise_factory("A")}
        runtime = StubRuntime(
            [_retrieved({"exercise_id": "A"}, r) for r in (1, 2, 3)]
        )
        result = await RailtracksRetriever(runtime, catalog).search("q")
        assert len(result) == 1

    async def test_drops_ids_missing_from_catalog(self, exercise_factory):
        catalog = {"A": exercise_factory("A")}
        runtime = StubRuntime(
            [
                _retrieved({"exercise_id": "GONE"}, 1),
                _retrieved({}, 2),  # no exercise_id key at all
                _retrieved({"exercise_id": "A"}, 3),
            ]
        )
        result = await RailtracksRetriever(runtime, catalog).search("q")
        assert [e.id for e in result] == ["A"]

    async def test_max_results_passed_as_top_k(self, exercise_factory):
        runtime = StubRuntime([])
        await RailtracksRetriever(runtime, {}).search("q", max_results=7)
        assert runtime.calls == [("q", 7)]


class FakeEmbedding(Embedding):
    """Deterministic bag-of-words embedding — overlapping vocabulary scores
    higher, which is all the round-trip test needs."""

    default_batch_size = 32
    _DIM = 64

    async def aembed(self, texts: list[str]) -> TextEmbeddings:
        return TextEmbeddings(
            vectors=[self._vector(t) for t in texts],
            metrics=EmbeddingMetrics(model="fake-bow", vector_count=len(texts)),
        )

    def _vector(self, text: str) -> list[float]:
        v = [0.0] * self._DIM
        for token in text.lower().split():
            v[zlib.crc32(token.encode()) % self._DIM] += 1.0
        norm = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / norm for x in v]


class TestOfflineRoundTrip:
    async def test_ingest_then_retrieve_returns_relevant_exercise(self, tiny_dataset):
        path, catalog = tiny_dataset
        runtime = RetrievalRuntime(
            chunker=RecursiveCharacterChunker(chunk_size=6000, overlap=0),
            embedder=FakeEmbedding(),
            store=VectorStore(InMemoryVectorBackend()),
        )

        stats = await runtime.ingest_all(loader=ExerciseCatalogLoader(path))
        assert stats.documents_failed == 0
        assert stats.chunks_embedded == len(catalog)  # one exercise = one chunk

        retriever = RailtracksRetriever(runtime, catalog)
        result = await retriever.search(
            "squat down keeping your back straight barbell quadriceps",
            max_results=2,
        )
        assert result and result[0].id == "Barbell_Squat"

    async def test_reingest_skips_unchanged_exercises(self, tiny_dataset):
        path, catalog = tiny_dataset
        runtime = RetrievalRuntime(
            chunker=RecursiveCharacterChunker(chunk_size=6000, overlap=0),
            embedder=FakeEmbedding(),
            store=VectorStore(InMemoryVectorBackend()),
        )
        await runtime.ingest_all(loader=ExerciseCatalogLoader(path))
        stats = await runtime.ingest_all(loader=ExerciseCatalogLoader(path))
        assert stats.documents_skipped == len(catalog)
        assert stats.chunks_embedded == 0
