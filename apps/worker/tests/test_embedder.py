import asyncio
import math

from jobpilot_schemas.embeddings import EMBEDDING_DIM, DeterministicEmbedder, make_embedder


def test_deterministic_embedder_is_stable_and_unit_norm():
    embedder = DeterministicEmbedder()
    [a1] = embedder.embed(["python engineer"])
    [a2] = embedder.embed(["python engineer"])
    [b] = embedder.embed(["pastry chef"])
    assert a1 == a2  # same text, same vector — stable across runs
    assert a1 != b
    assert len(a1) == EMBEDDING_DIM
    assert math.isclose(sum(x * x for x in a1), 1.0, rel_tol=1e-9)


def test_async_and_sync_paths_agree():
    embedder = DeterministicEmbedder()
    assert asyncio.run(embedder.aembed(["query"], "query")) == embedder.embed(["query"], "query")


def test_factory_falls_back_without_key():
    assert isinstance(make_embedder(""), DeterministicEmbedder)
