# tests/test_embedding_service.py
import numpy as np
import pytest

from core.exceptions import EmbeddingError
from rag.embedding_service import EmbeddingService, blob_to_vector, vector_to_blob


class FakeClient:
    def __init__(self, result=None, error=None):
        self.result, self.error, self.calls = result, error, []

    def embed(self, model, input):
        self.calls.append((model, input))
        if self.error:
            raise self.error
        return self.result


def test_embed_returns_float32_vector_and_passes_model():
    client = FakeClient({"embeddings": [[0.5, 1.0, 2.0]]})
    vec = EmbeddingService(client, model="m").embed("hello")
    assert vec.dtype == np.float32 and vec.tolist() == [0.5, 1.0, 2.0]
    assert client.calls == [("m", "hello")]


def test_transport_error_is_wrapped():
    with pytest.raises(EmbeddingError):
        EmbeddingService(FakeClient(error=ConnectionError("down"))).embed("x")


@pytest.mark.parametrize("bad", [{}, {"embeddings": []}, {"embeddings": [[]]}, {"embeddings": [[[1.0]]]}])
def test_invalid_response_shapes_raise_embedding_error(bad):
    with pytest.raises(EmbeddingError):
        EmbeddingService(FakeClient(bad)).embed("x")


def test_empty_text_is_a_programming_error():
    with pytest.raises(ValueError):
        EmbeddingService(FakeClient({"embeddings": [[1.0]]})).embed("   ")


def test_blob_roundtrip():
    original = np.array([0.25, -1.5, 3.0], dtype=np.float32)
    assert np.array_equal(blob_to_vector(vector_to_blob(original)), original)
