import asyncio
import math

from worker.embedder import EMBEDDING_DIM, DeterministicEmbedder, make_embedder


def test_deterministic_embedder_is_stable_and_unit_norm():
    embedder = DeterministicEmbedder()
    [a1], [a2], [b] = (
        asyncio.run(embedder.embed(["python engineer"])),
        asyncio.run(embedder.embed(["python engineer"])),
        asyncio.run(embedder.embed(["pastry chef"])),
    )
    assert a1 == a2  # same text, same vector — stable across runs
    assert a1 != b
    assert len(a1) == EMBEDDING_DIM
    assert math.isclose(sum(x * x for x in a1), 1.0, rel_tol=1e-9)


def test_factory_falls_back_without_key():
    assert isinstance(make_embedder(""), DeterministicEmbedder)
