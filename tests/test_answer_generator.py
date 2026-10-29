# tests/test_answer_generator.py
import pytest

from core.exceptions import GenerationError
from models.chunk import Chunk, ScoredChunk
from services.answer_generator import AnswerGenerator

CHUNKS = [ScoredChunk(Chunk(1, "a.txt", "OLED pixels emit light."), 0.9),
          ScoredChunk(Chunk(2, "b.txt", "QLED uses a backlight."), 0.8)]


class FakeClient:
    def __init__(self, content=None, error=None):
        self.content, self.error, self.calls = content, error, []

    def chat(self, model, messages, options):
        self.calls.append((model, messages, options))
        if self.error:
            raise self.error
        return {"message": {"content": self.content}}


def test_returns_stripped_text_and_builds_grounded_prompt():
    client = FakeClient("  OLED lights each pixel.  ")
    gen = AnswerGenerator(client, model="m", temperature=0.1, num_predict=50)
    assert gen.generate("What is OLED?", CHUNKS, "en") == "OLED lights each pixel."
    model, messages, options = client.calls[0]
    system = messages[0]["content"]
    assert model == "m" and options == {"temperature": 0.1, "num_predict": 50}
    assert "OLED pixels emit light." in system and "QLED uses a backlight." in system
    assert "Source A:" in system and "Source B:" in system
    assert "Reply in English." in system
    assert messages[1] == {"role": "user", "content": "What is OLED?"}


def test_language_rule_for_arabic_and_unknown():
    client = FakeClient("x")
    gen = AnswerGenerator(client)
    gen.generate("q", CHUNKS, "ar")
    gen.generate("q", CHUNKS, "unknown")
    assert "Reply in Arabic." in client.calls[0][1][0]["content"]
    assert "same language as the customer's question" in client.calls[1][1][0]["content"]


def test_no_answer_token_means_insufficient_evidence():
    assert AnswerGenerator(FakeClient("NO_ANSWER")).generate("q", CHUNKS) is None
    assert AnswerGenerator(FakeClient("no_answer.")).generate("q", CHUNKS) is None


def test_no_chunks_means_no_call_and_none():
    client = FakeClient("x")
    assert AnswerGenerator(client).generate("q", []) is None
    assert client.calls == []


def test_client_errors_become_generation_error():
    with pytest.raises(GenerationError):
        AnswerGenerator(FakeClient(error=TimeoutError("slow"))).generate("q", CHUNKS)


def test_empty_answer_is_an_error():
    with pytest.raises(GenerationError):
        AnswerGenerator(FakeClient("   ")).generate("q", CHUNKS)
