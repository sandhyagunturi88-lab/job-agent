"""Shared embedding client (used by the worker to index JDs and by the API to
embed retrieval queries — both sides MUST use the same model and dimensions).

Anthropic has no embeddings API; Voyage AI is its recommended embeddings
partner, behind VOYAGE_API_KEY. Without a key, a deterministic local embedder
keeps everything runnable: stable pseudo-embeddings from a SHA-256 stream —
meaningless semantically, but unit-norm, reproducible, and shaped exactly like
the real thing.
"""

import hashlib
import math
import struct
from typing import Literal, Protocol

import httpx

EMBEDDING_DIM = 1024  # voyage-3 native dimension; supabase migrations use vector(1024)

InputType = Literal["document", "query"]


class Embedder(Protocol):
    def embed(self, texts: list[str], input_type: InputType = "document") -> list[list[float]]: ...

    async def aembed(
        self, texts: list[str], input_type: InputType = "document"
    ) -> list[list[float]]: ...


class DeterministicEmbedder:
    def embed(self, texts: list[str], input_type: InputType = "document") -> list[list[float]]:
        return [self._one(t) for t in texts]

    async def aembed(
        self, texts: list[str], input_type: InputType = "document"
    ) -> list[list[float]]:
        return self.embed(texts, input_type)

    @staticmethod
    def _one(text: str) -> list[float]:
        values: list[float] = []
        counter = 0
        while len(values) < EMBEDDING_DIM:
            digest = hashlib.sha256(f"{counter}:{text}".encode()).digest()
            # 8 float32s per 32-byte digest, scaled to [-1, 1]
            for i in range(0, 32, 4):
                (n,) = struct.unpack(">I", digest[i : i + 4])
                values.append((n / 0x7FFFFFFF) - 1.0)
            counter += 1
        values = values[:EMBEDDING_DIM]
        norm = math.sqrt(sum(v * v for v in values)) or 1.0
        return [v / norm for v in values]


class VoyageEmbedder:
    ENDPOINT = "https://api.voyageai.com/v1/embeddings"

    def __init__(self, api_key: str, model: str, client: httpx.AsyncClient | None = None) -> None:
        self.api_key = api_key
        self.model = model
        self.client = client  # optional shared async client (worker injects one)

    def _payload(self, texts: list[str], input_type: InputType) -> dict:
        return {"model": self.model, "input": texts, "input_type": input_type}

    @staticmethod
    def _parse(data: dict) -> list[list[float]]:
        return [item["embedding"] for item in sorted(data["data"], key=lambda d: d["index"])]

    def embed(self, texts: list[str], input_type: InputType = "document") -> list[list[float]]:
        response = httpx.post(
            self.ENDPOINT,
            headers={"Authorization": f"Bearer {self.api_key}"},
            json=self._payload(texts, input_type),
            timeout=60,
        )
        response.raise_for_status()
        return self._parse(response.json())

    async def aembed(
        self, texts: list[str], input_type: InputType = "document"
    ) -> list[list[float]]:
        client = self.client or httpx.AsyncClient(timeout=60)
        response = await client.post(
            self.ENDPOINT,
            headers={"Authorization": f"Bearer {self.api_key}"},
            json=self._payload(texts, input_type),
        )
        response.raise_for_status()
        return self._parse(response.json())


def make_embedder(
    voyage_api_key: str, voyage_model: str = "voyage-3", client: httpx.AsyncClient | None = None
) -> Embedder:
    if voyage_api_key:
        return VoyageEmbedder(voyage_api_key, voyage_model, client)
    return DeterministicEmbedder()
